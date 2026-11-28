import io
import os
import sys
import fitz
import mongomock
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app


def _make_pdf_bytes(text: str = "") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture()
def client():
    mock_mongo = mongomock.MongoClient()
    app = create_app(
        config_overrides={
            "TESTING": True,
            "JWT_SECRET_KEY": "test-secret-key-for-pytest",
            "MONGO_URI": "mongodb://localhost:27017/learnable_ai_test",
            "GEMINI_API_KEY": "",
            "WHISPER_API_URL": "",
        },
        mongo_client_override=mock_mongo,
    )
    with app.test_client() as test_client:
        yield test_client, app


def _register_and_token(client, email="student@example.com", name="Test Student"):
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": name,
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    assert res.status_code == 201
    return res.get_json()["access_token"]


def test_auth_register_login_logout_flow(client):
    c, _ = client
    token = _register_and_token(c, "a@example.com", "Alice Learner")

    # Protected route works with token
    me = c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "a@example.com"

    # Logout revokes token
    out = c.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert out.status_code == 200

    me_after = c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401

    # Login returns fresh token
    login_res = c.post(
        "/api/auth/login",
        json={"email": "a@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.get_json()


def test_accessibility_preferences_persistence(client):
    c, _ = client
    token = _register_and_token(c, "prefs@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    put_res = c.put(
        "/api/accessibility",
        headers=headers,
        json={
            "modes": ["dyslexia", "low_vision"],
            "font_size": 24,
            "font_style": "dyslexia",
            "high_contrast": True,
            "theme": "dark",
            "line_spacing": 2.0,
            "letter_spacing": 0.08,
            "zoom": 120,
            "onboarding_completed": True,
        },
    )
    assert put_res.status_code == 200
    saved = put_res.get_json()["accessibility"]
    assert saved["modes"] == ["dyslexia", "low_vision"]
    assert saved["font_size"] == 24
    assert saved["high_contrast"] is True
    assert saved["theme"] == "dark"
    assert saved["onboarding_completed"] is True


def test_pdf_upload_extraction_validation_and_user_isolation(client):
    c, _ = client
    token1 = _register_and_token(c, "u1@example.com", "User One")
    token2 = _register_and_token(c, "u2@example.com", "User Two")

    # Reject non-PDF
    bad = c.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {token1}"},
        data={"file": (io.BytesIO(b"plain text"), "notes.txt")},
        content_type="multipart/form-data",
    )
    assert bad.status_code == 400

    # Reject fake PDF bytes with .pdf extension
    fake_pdf = c.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {token1}"},
        data={"file": (io.BytesIO(b"not really a pdf"), "fake.pdf")},
        content_type="multipart/form-data",
    )
    assert fake_pdf.status_code == 400

    # Handle empty/scanned PDF gracefully
    empty_pdf_bytes = _make_pdf_bytes("")
    scanned_res = c.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {token1}"},
        data={"file": (io.BytesIO(empty_pdf_bytes), "scanned.pdf")},
        content_type="multipart/form-data",
    )
    assert scanned_res.status_code == 201
    assert scanned_res.get_json()["document"]["status"] == "needs_ocr"
    assert scanned_res.get_json()["document"]["ocr_recommended"] is True

    # Valid text PDF extraction
    pdf_bytes = _make_pdf_bytes(
        "Photosynthesis converts light energy into chemical energy in plants."
    )
    ok_res = c.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {token1}"},
        data={"file": (io.BytesIO(pdf_bytes), "biology.pdf")},
        content_type="multipart/form-data",
    )
    assert ok_res.status_code == 201
    doc = ok_res.get_json()["document"]
    assert doc["status"] == "ready"
    assert "Photosynthesis converts light energy" in doc["extracted_text"]

    # User 2 cannot see or access User 1's document
    u2_list = c.get("/api/documents", headers={"Authorization": f"Bearer {token2}"})
    assert u2_list.status_code == 200
    assert u2_list.get_json()["documents"] == []

    u2_get = c.get(
        f"/api/documents/{doc['id']}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert u2_get.status_code == 404


def test_ai_fails_honestly_when_gemini_key_missing_and_works_when_mocked(client, monkeypatch):
    c, app = client
    token = _register_and_token(c, "ai@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = _make_pdf_bytes("Cellular respiration produces ATP from glucose.")
    up = c.post(
        "/api/documents/upload",
        headers=headers,
        data={"file": (io.BytesIO(pdf_bytes), "bio2.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = up.get_json()["document"]["id"]

    # Missing key must return 503 error, never fake AI text
    no_key_res = c.post(
        "/api/ai/simplify",
        headers=headers,
        json={"document_id": doc_id},
    )
    assert no_key_res.status_code == 503
    assert "GEMINI_API_KEY" in no_key_res.get_json()["error"]

    # Mock GeminiService response
    from services.gemini_service import GeminiService

    monkeypatch.setattr(
        GeminiService,
        "simplify_text",
        lambda self, text, accessibility_modes=None: {
            "simplified_text": "Cells make energy called ATP from sugar.",
            "reading_summary": "This text explains how cells make ATP.",
            "difficult_words": [
                {
                    "word": "ATP",
                    "simple_explanation": "Energy molecule used by cells.",
                    "example": "Muscles use ATP to move.",
                }
            ],
            "key_concepts": ["Cellular respiration", "ATP"],
        },
    )
    app.config["GEMINI_API_KEY"] = "mock-key"

    ok_ai = c.post(
        "/api/ai/simplify",
        headers=headers,
        json={"document_id": doc_id},
    )
    assert ok_ai.status_code == 200
    assert ok_ai.get_json()["simplification"]["simplified_text"].startswith("Cells make")


def test_practice_generation_submission_and_transcripts(client, monkeypatch):
    c, app = client
    token = _register_and_token(c, "prac@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = _make_pdf_bytes("Water boils at 100 degrees Celsius at sea level.")
    up = c.post(
        "/api/documents/upload",
        headers=headers,
        data={"file": (io.BytesIO(pdf_bytes), "physics.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = up.get_json()["document"]["id"]

    from services.gemini_service import GeminiService

    monkeypatch.setattr(
        GeminiService,
        "generate_practice",
        lambda self, **kwargs: {
            "title": "Boiling Point Practice",
            "questions": [
                {
                    "id": "q1",
                    "question_type": "multiple_choice",
                    "difficulty": "easy",
                    "question_text": "At what temperature does water boil at sea level?",
                    "options": ["50°C", "100°C", "150°C", "0°C"],
                    "correct_answer": "100°C",
                    "explanation": "At sea level, water boils at 100 degrees Celsius.",
                }
            ],
        },
    )
    app.config["GEMINI_API_KEY"] = "mock-key"

    gen = c.post(
        "/api/practice/generate",
        headers=headers,
        json={"document_id": doc_id, "question_count": 1},
    )
    assert gen.status_code == 201
    ps_id = gen.get_json()["practice_set"]["id"]

    sub = c.post(
        "/api/practice/submit",
        headers=headers,
        json={"practice_set_id": ps_id, "answers": {"q1": "100°C"}},
    )
    assert sub.status_code == 201
    assert sub.get_json()["attempt"]["score_percent"] == 100

    # Transcript save + edit + honest 501 when Whisper not configured
    audio_unconf = c.post(
        "/api/transcripts/transcribe",
        headers=headers,
        data={"file": (io.BytesIO(b"RIFFdata"), "lecture.wav")},
        content_type="multipart/form-data",
    )
    assert audio_unconf.status_code == 501

    save_tr = c.post(
        "/api/transcripts",
        headers=headers,
        json={"title": "Lecture 1", "text": "Today we study thermodynamics."},
    )
    assert save_tr.status_code == 201
    tid = save_tr.get_json()["transcript"]["id"]

    edit_tr = c.put(
        f"/api/transcripts/{tid}",
        headers=headers,
        json={"text": "Today we studied thermodynamics and heat."},
    )
    assert edit_tr.status_code == 200
    assert "heat" in edit_tr.get_json()["transcript"]["text"]
