# ScamShield AI — Multimodal Fraud Intelligence & Safety Screening

Track B · Problem Statement 5 · Wisework × Imagenext Internship Hackathon

ScamShield AI is an offline-first, privacy-conscious fraud screening prototype covering **digital arrest, UPI fraud, smishing, vishing transcripts, quishing (QR phishing), phishing URLs, and deceptive emails**. It provides explainable indicators, structured QR/UPI/identity inspection, and actionable next steps without claiming to prove fraud or certify safety.

> **Branch & Attribution Note:**
> - **Original Team Submission (`main` / tag `v2.1.1`):** Multilingual rules engine, 394-row synthetic TF-IDF + Linear SVM, Tesseract OCR, Sarvam STT/TTS, optional Groq hybrid, 11 Indian languages, and Rescue Assistant.
> - **Individual Innovation Upgrade (`dipankar-individual-innovation`, Dipankar Maity):** Incremental commits extending `v2.1.1` with offline QR/UPI decoding, URL-only ML + PhishTank SHA-256 DB, PSL email/identity verification, MeAJOR email phishing ML, live Google Safe Browsing v4, Automatic Analysis, and consolidated 3-tab UI.

---

## Architecture & Algorithms

- **Backend:** FastAPI (`scamshield/main.py`) with zero persistent scan history.
- **Offline Multimodal & Identity Pipeline (`scamshield/engine.py`):**
  1. **Multilingual Rules & Context (`engine.py`, `context_rules.py`, `multilingual_signals.py`, `regional_context.py`):** Regex + compositional rules across 11 Indian languages (`en`, `hi`, `bn`, `kn`, `te`, `or`, `mr`, `ta`, `ml`, `gu`, `pa`) with awareness/OTP-notice guards.
  2. **QR & UPI Quishing (`scamshield/qr_decoder.py`):** Dual offline decoder (`zxing-cpp` + OpenCV `QRCodeDetector`) with 6-stage preprocessing (quiet-zone padding, CLAHE contrast, multi-scale, adaptive/Otsu/inverted thresholding, skew rotation), `upi://pay` parser, cross-modal intent mismatch checks, and explicit `decoded` / `detected_unreadable` / `none` / `error` status handling.
  3. **Offline Email & Identity Verifier (`scamshield/identity_verifier.py`):** Mozilla Public Suffix List (`publicsuffix2`) domain parsing, curated `ORG_DOMAIN_REGISTRY`, safe `.eml` & HTML link/text extraction (no scripts or remote fetches), unverified `SPF`/`DKIM`/`DMARC` header display, and detection of sender mismatches, `Reply-To` mismatches, Punycode/Unicode homographs, misleading subdomains, and deceptive hyperlink labels.
  4. **URL Phishing Classifier + Threat DB (`scamshield/url_classifier.py`):** `TfidfVectorizer(char_wb, 3–5)` + 25 URL-only lexical features + `LogisticRegression` (`148.5 KB`) paired with a local SQLite SHA-256 PhishTank lookup (`verified_threats.db`, `42,314` hashes).
  5. **Specialized Email Phishing Classifier (`scamshield/email_classifier.py`):** Word (`1–2`) + Char (`3–5`) TF-IDF + `LogisticRegression` (`470.0 KB`) trained on cross-source MeAJOR (`trec5+trec6`).
  6. **Baseline Multilingual Text SVM (`training_data.py`):** Retained 394-row char TF-IDF + `LinearSVC` as a secondary weak signal (`Review`-only, margin `0.20`).
- **Online Protection (Consented, Optional):**
  - **Live URL Reputation (`scamshield/live_reputation.py`):** Google Safe Browsing Lookup API v4 (`GOOGLE_SAFE_BROWSING_API_KEY`) with 4s timeout and HTTP 429 handling (never visits suspicious URLs).
  - **Cloud Contextual AI (`scamshield/cloud.py`):** Groq GPT-OSS 120B with GPT-OSS 20B backup (`GROQ_API_KEY`), receiving masked text + structured `offline_evidence` without suppressing confirmed offline findings.
  - **Automatic Fallback:** Retains local assessment whenever keys are absent or providers fail.

---

## API Responsibilities

| Endpoint | Purpose | Network Calls |
|---|---|---|
| `GET /` | Serves consolidated 3-tab UI (`Text & Links`, `Upload File`, `Voice & Audio`) | None |
| `GET /api/health` | Reports version, configured providers, and threat DB age/hash count | None |
| `POST /api/analyze` | Runs offline engine (+ optional consented Safe Browsing & Groq); exposes Swagger schema at `/docs` | Optional (consented) |
| `POST /api/ocr` | Runs `zxing-cpp` + OpenCV QR decoding and Tesseract OCR on PNG/JPEG/WebP | None |
| `POST /api/parse-email` | Safely parses `.eml` headers, body, and `<a href>` links | None |
| `POST /api/transcribe-audio` | Consented audio transcription via Sarvam AI | Optional (consented) |
| `GET/POST /api/voice/*` | Fixed-template spoken safety warnings (cached/Sarvam/browser/basic MP3) | Optional |

---

## Genuine Datasets, Licences & Benchmark Results

| Dataset | Source & Licence | Scale | Usage & Evaluation Results |
|---|---|---|---|
| **UCI PhiUSIIL Phishing URL** | UCI (`CC BY 4.0`) | 235,795 rows / 234,687 dedup URLs | Domain-grouped 80/20 split (`0` domain overlap). Held-out 2,000-URL engine eval: **Acc 0.9015, Prec 0.9762, Rec 0.7840, F1 0.8696** (`2.79 ms`/URL). 500-URL comparison vs `v2.1.1`: Recall **0.0000 → 0.7674**, F1 **0.0000 → 0.8594**. |
| **Zenodo MeAJOR** | Zenodo `18471483` (`CC BY 4.0`) | 108,685 emails (`trec5/6/7`) | Cross-source (`trec5+6` train → `trec7` unseen test, `3,000` emails): Word+Char LogReg **Acc 0.8743, Prec 0.8968, Rec 0.8460, F1 0.8707** (vs `v2.1.1` SVM F1 `0.1553`). |
| **UCI SMS Spam Collection** | UCI (`CC BY 4.0`) | 5,574 genuine SMS | On `4,827` `ham`: `0` `high`, `2` `caution` (**0.04%** FP rate, `0.98 ms`/msg). |
| **PhishTank Online Valid** | `phishtank.org` (Non-commercial/research feed) | 42,467 rows / 42,314 SHA-256 hashes | Local offline threat lookup (`tools/refresh_threat_db.py`). **Redistribution note:** Verify PhishTank commercial/redistribution terms before public non-research distribution, or regenerate locally. |

- **Live Online vs Offline Verification (`benchmark/live_offline_verification.json`):** Verified with live `GROQ_API_KEY` and `GOOGLE_SAFE_BROWSING_API_KEY`: **9/9** scenarios completed in live `hybrid` mode (`7/7` attacks flagged `caution`/`high`, `0/2` benign false positives; `679–2074 ms` live latency vs `4.7–26 ms` offline).

---

## Installation & Running on Windows

1. **Prerequisites:** Python 3.11+ (tested on `3.14.6`) and optional [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (`C:\Program Files\Tesseract-OCR\tesseract.exe`).
2. **Install dependencies:**
   ```cmd
   run.bat setup
   ```
3. **Run Offline Protection (zero API keys required):**
   ```cmd
   run.bat offline
   ```
4. **Run with Optional Online Protection (keys stay in process memory only):**
   ```cmd
   run.bat
   ```
   Open `http://127.0.0.1:8000` (Swagger API docs at `http://127.0.0.1:8000/docs`).

## Verification

```cmd
.venv\Scripts\python.exe -m pytest -v -s
```
See [docs/INDIVIDUAL_INNOVATION.md](docs/INDIVIDUAL_INNOVATION.md) for detailed milestone logs and [LICENSE](LICENSE) (`MIT`).

## Known Limitations
- Absence of warnings (`NO CLEAR SIGNAL`) or absence from PhishTank/Safe Browsing **never proves a message, QR code, or URL is safe**.
- Lexical URL ML cannot detect bare root phishing domains that lack path, brand, or TLD cues without live reputation or email context.
- Automated OCR defaults to English + Hindi (`eng+hin`); select other Indian scripts manually when needed.
- Regional translations beyond English/Hindi still benefit from native-speaker review.
