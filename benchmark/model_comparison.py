"""ScamShield AI: simple offline classifier comparison (synthetic examples only)."""
import csv
import sys
from pathlib import Path
from time import perf_counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score

# Import the existing project's training dataset.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from scamshield.training_data import SUSPICIOUS, BENIGN

# Separate synthetic test messages: (suspicious, benign).
PAIRS = [
 ('Send OTP WIN MONEY', 'Your OTP is 628390. Never share it.'),
 ('Send your verification code to our agent to get your refund.', 'Your refund is complete. No verification code is needed.'),
 ('Pay a refundable registration deposit before you can join our company.', 'Your interview is confirmed. No registration deposit is required.'),
 ('Your package is held at customs; pay a release charge to this personal account.', 'Your package is at customs. Check its status in the official carrier app.'),
 ('We are investigating you. Keep the camera on and send a clearance deposit.', 'Police awareness session: never send a clearance deposit to a caller.'),
 ('Approve my collect request and type your PIN to get the scholarship.', 'Your scholarship has been credited. Check your bank statement.'),
 ('Your power supply will be cut tonight. Pay via the link we texted.', 'Power supply maintenance is scheduled tonight. No payment is necessary.'),
 ('I am your daughter on a new number. Send money now and do not call.', 'I changed my number. Call my old number to verify before saving this one.'),
 ('Your loan is approved. Send the file release fee to our representative.', 'Your loan application is under review. Check the status in the bank app.'),
 ('Get guaranteed double returns this week; transfer the joining amount today.', 'Investment returns are not guaranteed. Read the risk disclosure first.'),
 ('Download the attached traffic fine APK and grant all permissions.', 'Traffic fine notice: check the official traffic police website yourself.'),
 ('Your card points expire tonight; enter card details on our claim form.', 'Your card points expire tonight. Redeem through your banking app.'),
 ('Move your balance to our secure holding account while we investigate.', 'Review your balance using the official app and contact your bank if needed.'),
 ('Install screen sharing software and read your banking code to our staff.', 'Our IT helpdesk will never request your banking code.'),
 ('To prevent SIM closure, tell us the six digit code you just received.', 'Your SIM renewal date is approaching. Visit the provider store for help.'),
 ('Pay a small courier insurance fee to receive the expensive gift.', 'Your gift parcel is delivered. Thank you for using our service.'),
 ('Urgnt: send 0TP to unlock cash reward.', 'Do not send OTP to strangers who offer cash rewards.'),
 ('Aapka account block hoga, OTP abhi batao.', 'Apna OTP kisi ko mat batao.'),
 ('Paise receive karne ke liye UPI PIN dalo.', 'UPI PIN paise bhejne ke liye hota hai, receive karne ke liye nahi.'),
 ('Police bol rahi hai abhi paisa bhejo warna arrest hoga.', 'Police awareness notice: digital arrest se savdhan rahein.'),
]


def main():
    X = SUSPICIOUS + BENIGN
    y = [1] * len(SUSPICIOUS) + [0] * len(BENIGN)
    test_X = [message for pair in PAIRS for message in pair]
    test_y = [label for _ in PAIRS for label in (1, 0)]
    normalize = lambda text: ' '.join(text.casefold().split())
    assert not set(map(normalize, X)) & set(map(normalize, test_X)), "Training/test overlap"

    models = {
        "Logistic Regression": LogisticRegression(max_iter=300, class_weight="balanced", random_state=42),
        "Linear SVM": LinearSVC(max_iter=10000, class_weight="balanced", random_state=42),
        "Complement Naive Bayes": ComplementNB(alpha=1.0),
    }
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=42)
    print(f"Training: {len(X)} messages | Testing: {len(test_X)} messages (synthetic)")
    print("Classifier-only comparison; not real-world or full-app accuracy.\n")
    headers = ["Model", "Accuracy (%)", "Precision (%)", "Recall (%)", "F1 (%)",
               "Missed scams", "False alarms", "Fit (ms)", "CV F1 (%)"]
    rows = []
    for name, classifier in models.items():
        # Same feature extraction for each model. Fit on training text only.
        model = make_pipeline(TfidfVectorizer(analyzer="char", ngram_range=(3, 5),
                                              max_features=14000), classifier)
        start = perf_counter()
        model.fit(X, y)
        fit_ms = (perf_counter() - start) * 1000
        pred = model.predict(test_X)
        tn, fp, fn, tp = confusion_matrix(test_y, pred, labels=[0, 1]).ravel()
        scores = [metric(test_y, pred) for metric in
                  (accuracy_score, precision_score, recall_score, f1_score)]
        cv_f1 = cross_val_score(model, X, y, cv=cv, scoring="f1").mean()
        row = [name] + [round(s * 100, 2) for s in scores] + [int(fn), int(fp), round(fit_ms, 2), round(cv_f1 * 100, 2)]
        rows.append(row)
        print(name)
        for heading, value in zip(headers[1:], row[1:]):
            print(f"  {heading}: {value}")
        print()

    output = HERE / "model_comparison.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)
    print("Saved Excel-compatible report:", output)
    print("Training time varies by machine. Results do not select a production threshold.")


if __name__ == "__main__":
    main()
