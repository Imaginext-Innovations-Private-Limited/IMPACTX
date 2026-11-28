# ScamShield AI — Individual Innovation (External Hackathon)

**Branch:** `dipankar-individual-innovation` (branched from verified `v2.1.1` tag, commit `4394a81`)  
**Author:** Dipankar Maity

## 1. Problem Identified in v2.1.1
ScamShield AI v2.1.1 provides strong regex + contextual + weak-SVM screening for text/OCR/voice transcripts across 11 Indian languages, but has key gaps for multimodal and URL-based fraud:
1. **No QR / Quishing detection:** Screenshot OCR (`/api/ocr`) uses Tesseract to extract visible text, completely missing QR codes (`upi://pay?...`, phishing URLs, APK links) embedded in payment or KYC screenshots.
2. **No UPI QR payload parsing:** Cannot parse `upi://pay` URI fields (`pa`, `pn`, `am`, `cu`, `tn`, `mode`, `mam`) or detect **cross-modal intent mismatches** (e.g., message claims "receive ₹3,000 cashback / refund" while QR encodes an outgoing `upi://pay` or external phishing URL).
3. **Heuristic-only URL checks:** `_url_findings()` in `scamshield/engine.py` relies on a fixed `SUSPICIOUS_TLDS` / `BRANDS` / `OFFICIAL_DOMAINS` list without an ML phishing URL classifier trained on genuine labelled data or a local verified-threat lookup database.
4. **Synthetic-only training data:** The bundled 394-row text dataset (`training_data.py`) is synthetic; genuine labelled datasets are needed for URL classification and real-world evaluation.

## 2. Proposed Innovations
1. **Offline QR Decoding & Payload Classification (`scamshield/qr_decoder.py`):** OpenCV `QRCodeDetector` with Pillow/NumPy preprocessing fallbacks (grayscale, upscale, Otsu/adaptive thresholding), `upi://pay` parser, and payload classifier.
2. **Cross-Modal Intent Verification:** Compare surrounding message/OCR text intent (e.g., receive/refund/cashback/KYC/parcel) against decoded QR payload (`upi://pay`, external URL, APK, raw text).
3. **Offline Phishing URL Classifier + Local Threat Lookup (`scamshield/url_classifier.py`):**
   - Lightweight `scikit-learn` classifier trained **strictly on URL-only lexical/surface features** from deduplicated UCI PhiUSIIL (no HTML/DOM/network-fetch features).
   - Local SQLite verified-threat lookup database built from PhishTank (`online-valid.csv.gz`), storing normalized URL/host SHA-256 hashes (never claiming an unlisted URL is safe).
4. **Evidence-Based Risk Aggregation & Uncertainty Handling:** Integrate URL ML, threat DB hits, UPI QR parameters, and cross-modal mismatch indicators into `engine.py` without breaking existing multilingual, offline, or cloud-hybrid behavior.

## 3. Genuine Dataset Audit (Milestone 1)

| Dataset | Source & Licence | Rows / Unique | Label Semantics | Usage & Limitations |
|---|---|---|---|---|
| **UCI PhiUSIIL Phishing URL** | `archive.ics.uci.edu/dataset/967` (CC BY 4.0) | 235,795 rows / 235,370 unique URLs | `0` = Phishing (100,945), `1` = Legitimate (134,850) | Genuine collected URLs. Only URL-surface lexical features used; HTML/DOM columns excluded for offline safety. |
| **UCI SMS Spam Collection** | `archive.ics.uci.edu/dataset/228` (CC BY 4.0) | 5,574 rows (`ham`: 4,827, `spam`: 747) | `ham` vs `spam` | Genuine SMS. `spam` includes marketing/promos, not exclusively financial fraud; used for false-positive/generalization audit, not 1:1 fraud labels. |
| **PhishTank Verified Online** | `data.phishtank.com` (Non-commercial/research feed) | 42,467 rows / 42,465 unique URLs | All `verified=yes`, `online=yes` | Positive-only verified phishing feed. Absence never implies safety. |

## 4. Technical Decisions & Milestones
- **Milestone 1 (Baseline & Dataset Audit):** Verified `v2.1.1` test suite (`626 passed, 1 skipped` — Tesseract unavailable), installed `opencv-python-headless==5.1.0.95`, downloaded and audited official UCI & PhishTank datasets into gitignored `data/external/`.
- **Milestone 2 (Offline QR Decoder & UPI Parser):** Implemented `scamshield/qr_decoder.py` using `cv2.QRCodeDetector` with Pillow/NumPy grayscale, upscale, Otsu, and inverted-threshold fallbacks, `upi://pay` URI parsing, payload classification, and cross-modal intent verification (`tests/test_qr_decoder.py`: `6 passed in 0.31s`).
- **Milestone 3 (Offline URL Classifier & Threat DB):** Implemented `scamshield/url_classifier.py` and `tools/train_url_model.py`:
  - Built `scamshield/data/verified_threats.db` (6.4 MB, `42,314` unique SHA-256 hashes from PhishTank `online-valid.csv.gz`).
  - Trained `TfidfVectorizer(char_wb, 3-5)` + 25 URL-only lexical features + `LogisticRegression` (`scamshield/data/url_model.joblib`, `148.5 KB`) on `234,687` deduplicated UCI PhiUSIIL URLs with strict registered-domain-grouped 80/20 split (`172,953` domain groups; `53,019` held-out test URLs).
  - Held-out unseen-domain evaluation (`scamshield/data/url_eval_report.json`): **ROC-AUC 0.9584**; at `p >= 0.50`: Accuracy **0.9134**, Precision **0.9498**, Recall **0.8705**, F1 **0.9085**; at `p >= 0.85`: Precision **0.9967**, Recall **0.7973**.
