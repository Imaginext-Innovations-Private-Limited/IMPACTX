
import re
import joblib
from pathlib import Path
from urllib.parse import unquote
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ml" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Illustrative labeled examples, not confirmed real-world attacks.
TRAINING_DATA = [
    ("/", "GET", "web", "benign"),
    ("/health", "GET", "web", "benign"),
    ("/search", "GET", "web", "benign"),
    ("/login", "GET", "web", "benign"),
    ("/products", "GET", "web", "benign"),
    ("/about", "GET", "web", "benign"),
    ("/contact", "GET", "web", "benign"),
    ("/search?q=shoes", "GET", "web", "benign"),
    ("/images/logo.png", "GET", "web", "benign"),
    ("/profile", "GET", "web", "benign"),
    ("/cart", "GET", "web", "benign"),
    ("/account/settings", "GET", "web", "benign"),
    ("/search?q=books", "GET", "web", "benign"),
    ("/products?page=2", "GET", "web", "benign"),
    ("/help", "GET", "web", "benign"),
    ("/assets/style.css", "GET", "web", "benign"),
    ("/orders", "GET", "web", "benign"),
    ("/search?q=computer", "GET", "web", "benign"),
    ("/login", "POST", "web", "benign"),
    ("/health", "GET", "web", "benign"),

    ("/../../etc/passwd", "GET", "web", "suspicious"),
    ("/.env", "GET", "web", "suspicious"),
    ("/wp-admin", "GET", "web", "suspicious"),
    ("/phpmyadmin", "GET", "web", "suspicious"),
    ("/search?q=union+select", "GET", "web", "suspicious"),
    ("/?cmd=whoami", "GET", "web", "suspicious"),
    ("/download?file=../../../etc/passwd", "GET", "web", "suspicious"),
    ("/admin/.env", "GET", "web", "suspicious"),
    ("/cgi-bin/test", "GET", "web", "suspicious"),
    ("/search?q=%3Cscript%3E", "GET", "web", "suspicious"),
    ("/.git/config", "GET", "web", "suspicious"),
    ("/server-status", "GET", "web", "suspicious"),
    ("/search?q=OR+1%3D1", "GET", "web", "suspicious"),
    ("/file?name=../../secret", "GET", "web", "suspicious"),
    ("/backup.sql", "GET", "web", "suspicious"),
    ("/admin/config", "GET", "web", "suspicious"),
    ("/?exec=id", "GET", "web", "suspicious"),
    ("/api/../../private", "GET", "web", "suspicious"),
    ("/.ssh/authorized_keys", "GET", "web", "suspicious"),
    ("/search?q=%27%20OR%201%3D1", "GET", "web", "suspicious"),
]


def make_text(path, method, domain):
    decoded = unquote(str(path)).lower()
    text = f"domain={domain} method={method} path={decoded}"

    # Explicit features help the model recognize common patterns.
    indicators = {
        "feat_traversal": ".." in decoded,
        "feat_env": ".env" in decoded,
        "feat_git": ".git" in decoded,
        "feat_sensitive_file": any(
            marker in decoded
            for marker in ("etc/passwd", "authorized_keys", "backup.sql")
        ),
        "feat_sql": any(
            marker in decoded
            for marker in ("union", "select", "or 1=1")
        ),
        "feat_script": any(
            marker in decoded
            for marker in ("<script", "%3cscript", "javascript:")
        ),
        "feat_command": any(
            marker in decoded
            for marker in ("cmd=", "exec=", "whoami", "cat%20")
        ),
        "feat_admin_probe": any(
            marker in decoded
            for marker in ("wp-admin", "phpmyadmin", "cgi-bin")
        ),
    }

    return text + " " + " ".join(
        name for name, found in indicators.items() if found
    )


def main():
    texts = [
        make_text(path, method, domain)
        for path, method, domain, label in TRAINING_DATA
    ]
    labels = [label for _, _, _, label in TRAINING_DATA]

    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.25,
        random_state=42,
        stratify=labels,
    )

    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("classifier", LogisticRegression(
            max_iter=1000, class_weight="balanced"
        )),
    ])

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    print("Prototype model evaluation")
    print("Training examples:", len(X_train))
    print("Test examples:", len(X_test))
    print(classification_report(
        y_test, predictions, zero_division=0
    ))
    print("Confusion matrix (label order: benign, suspicious):")
    print(confusion_matrix(
        y_test, predictions, labels=["benign", "suspicious"]
    ))

    model_path = MODEL_DIR / "honeypot_classifier.joblib"
    joblib.dump(model, model_path)
    print("Model saved to:", model_path)


if __name__ == "__main__":
    main()
