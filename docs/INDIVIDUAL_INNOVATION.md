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
- **Milestone 4 (Engine & API Integration):** Integrated `url_classifier` + `verified_threats.db` + `qr_decoder` into `scamshield/engine.py` and `scamshield/main.py` (`/api/ocr` decodes QR codes locally even when Tesseract OCR is unavailable; `/api/analyze` accepts `qr_payloads`). Full suite verified: `639 passed, 1 skipped in 5.10s`.
- **Milestone 5 (Frontend Quishing UI & Real-World SMS Audit):**
  - Updated `static/index.html` and `static/app.js` to display decoded QR payloads (`#qr-preview`) and forward `qr_payloads` to `/api/analyze` without automatically opening URLs or initiating payments.
  - Evaluated on genuine **UCI SMS Spam Collection** (`5,574` messages): on `4,827` `ham` messages, `0` were flagged `high` and only `2` (`0.04%`) were `caution` (`4,189` `no_clear_signal`, `507` `review`, `129` `unknown`). On `747` general `spam` messages, `26` were `caution` and `114` `review` (confirming generic promotional spam is not conflated with high-risk financial fraud).
- **Milestone 6 (Evaluator Feedback — Polished Phishing, Identity Verification & Zero-Key Auto Protect):**
  - **Evaluator Requirement:** Detect professionally written, legitimate-looking phishing emails/URLs even without obvious scam keywords, and run automatically without requiring end-user API keys.
  - **Offline Email & Identity Verification (`scamshield/identity_verifier.py` + `publicsuffix2` PSL):**
    - Extracts `From`, `Reply-To`, claimed organisations (against curated `ORG_DOMAIN_REGISTRY`), safe HTML `<a href>` & Markdown hyperlinks (without rendering scripts or loading remote resources), requested actions, and unverified `SPF`/`DKIM`/`DMARC` header claims.
    - Detects sender-domain mismatches, `Reply-To` mismatches, Punycode/Unicode homographs, misleading brand subdomains (via Mozilla PSL), and deceptive hyperlink labels.
    - Never treats an official-domain match or uploaded header as independent authentication; unknown organisations/missing senders remain neutral.
  - **Strengthened Offline Engine & Zero-Key Auto Protect (`scamshield/engine.py`, `scamshield/main.py`, `static/app.js`):**
    - Standalone URLs, short phishing links, and QR-only payloads are evaluated before minimum-text-length gating.
    - Added `/api/parse-email` for `.eml` files and **Auto Protect** mode (ON by default) with 550ms debouncing, `AbortController` stale-request cancellation, duplicate-submission prevention, and local-only default execution (Groq/Sarvam require explicit user consent and server-side keys).
  - **Leakage & Challenge Evaluation (`tests/test_challenge_suite.py`):**
    - Verified `0` domain overlap (`155,227` train domains vs `38,807` test domains) and `0` URL overlap in PhiUSIIL, with `TfidfVectorizer` and `StandardScaler` fitted strictly on training data.
    - Authored challenge suite (`7` polished phishing/quishing/identity attacks, `3` benign controls, plus missing-key, cloud-timeout, and stale-request tests): **7/7 attacks detected** (Precision `1.00`, Recall `1.00`, F1 `1.00`, `0` false positives, `0` missed attacks).
  - **PhishTank Redistribution Note:** `scamshield/data/verified_threats.db` contains SHA-256 hashes derived from PhishTank's non-commercial/research feed (`phishtank.org`); verify redistribution/licensing terms before publishing the derived DB to a public repository or regenerate locally with `tools/train_url_model.py`.
- **Milestone 7 (Online/Offline Intelligence, Threat DB Refresh, OCR+QR & Comparative Benchmark):**
  - **Live Online Intelligence (`scamshield/live_reputation.py`, `scamshield/cloud.py`, `scamshield/main.py`):**
    - Added Google Safe Browsing v4 lookup (`check_urls_live`) with bounded 4s timeout, HTTP 429 rate-limit handling, and explicit distinction between `threat_match`, `no_match`, `provider_error`, and `unavailable`.
    - Updated `cloud.py` to pass redacted structured `offline_evidence` (URLs, QR types, identity claims) to Groq while never allowing cloud AI to suppress confirmed offline threat findings.
    - Added `engine_contributions` and `threat_db` age/count metadata to `/api/health` and `/api/analyze`, surfaced clearly in the Offline Protection / Online Protection UI.
    - **Live Provider Status:** `GROQ_API_KEY` and `GOOGLE_SAFE_BROWSING_API_KEY` are not configured in this environment; live API calls were not fabricated (`10/10` `offline_fallback` verified in `5.72 ms` avg). Mocked online provider tests (`tests/test_online_intelligence.py`) verify `threat_match`, `no_match`, `429`/timeout fallback, and non-suppression of local evidence.
  - **Atomic Threat DB Refresh (`tools/refresh_threat_db.py`):** Validates gzip/CSV schema and minimum record count before atomic `os.replace`, writing `verified_threats.meta.json` (`42,314` unique hashes).
  - **OCR + QR Verification (`tests/test_ocr_and_qr.py`):** Verified Tesseract OCR (`C:\Program Files\Tesseract-OCR\tesseract.exe`, `eng`) + OpenCV `QRCodeDetector` together on a combined screenshot.
  - **Genuine Dataset & Comparative Evaluation (`benchmark/genuine_eval_report.json`, `benchmark/comparative_benchmark.json`):**
    - **UCI SMS Spam Collection (5,574 msgs, 0.98 ms/msg):** `ham` (`4,827`): `no_clear_signal=4189`, `review=507`, `unknown=129`, `caution=2`, `high=0` (`0.04%` caution+high FP). `spam` (`747`): `no_clear_signal=601`, `review=115`, `caution=29`, `unknown=2`, `high=0`.
    - **PhiUSIIL Held-out (2,000 unseen-domain URLs, 0 overlap, 2.79 ms/URL):** `25` exact PhishTank DB matches; full engine Precision **0.9762**, Recall **0.7840**, F1 **0.8696** (excluding DB hits: Precision **0.9753**, Recall **0.7774**, F1 **0.8652**, 16 FP, 181 FN).
    - **Comparative 500-URL Held-out Benchmark (`v2.1.1` vs `v2.2` offline):** `v2.1.1` Accuracy **0.5700**, Recall **0.0000**, F1 **0.0000** (`215` FN) → `v2.2` Offline Accuracy **0.8920**, Precision **0.9763**, Recall **0.7674**, F1 **0.8594** (`4` FP, `50` FN, `1.60 ms`/URL).
  - **Remaining Limitations:** Lexical URL ML misses ~22–23% of unseen phishing URLs that mimic clean short domains; live Groq/Safe Browsing accuracy could not be measured live without configured API keys; PhishTank redistribution terms must be verified before publishing `verified_threats.db` publicly.

- **Milestone 8 (Final Reliability, OCR Repair & Release Readiness):**
  - **Launcher & API Key Forwarding (`run.bat`, `tools/start_hybrid.py`):** Updated `run.bat` to check `cv2` and `publicsuffix2`, clear `GOOGLE_SAFE_BROWSING_API_KEY` in `offline` mode, and forward `GOOGLE_SAFE_BROWSING_API_KEY` alongside `GROQ_API_KEY` and `SARVAM_API_KEY` in `tools/start_hybrid.py`.
  - **Consistent OCR Resolution (`scamshield/main.py`, `tests/test_api.py`):** Extracted `_resolve_tesseract_cmd()` so both `/api/ocr` and tests locate `C:\Program Files\Tesseract-OCR\tesseract.exe` consistently.
  - **Live vs Offline Verification (`tools/verify_live_and_offline.py`, `benchmark/live_offline_verification.json`):** Ran 9 privacy-safe scenarios across both modes (`7/7` attacks detected, `0/2` false positives; `100%` graceful `offline_fallback` in `3.7–9.8 ms` when `GROQ_API_KEY` / `GOOGLE_SAFE_BROWSING_API_KEY` are absent).
  - **Dev-Split Missed-URL Investigation:** On `202` dev phishing misses, bare root domains with no path/brand/TLD cues (e.g., `http://www.hesselawchambers.com/`) cannot be separated lexically without live reputation or page/identity context; `46` had `p` in `[0.50, 0.65)`. Kept `0.65` review threshold to preserve `97.6%` precision.
  - **Secret & Redistribution Audit:** Verified `0` credential or restricted-dataset (`bsis`) hits in `git diff v2.1.1..HEAD`. Note: `scamshield/data/verified_threats.db` contains SHA-256 hashes from PhishTank's non-commercial/research feed; confirm redistribution terms before pushing `verified_threats.db` to a public repo.

- **Milestone 10 (Genuine-Data Offline Intelligence Upgrade — Zenodo MeAJOR):**
  - **Dataset Audit (`tools/audit_meajor.py`, `benchmark/meajor_audit.json`):** Downloaded `meajor_cleaned_preprocessed.csv` (191.1 MB, MD5 `aa8f59e96787cbd696c0b650e5400dc9`, CC BY 4.0, Zenodo `18471483`): `108,685` rows (`0.0`: `60,650`, `1.0`: `48,034`, `1` malformed) across `trec5` (`49,583`), `trec6` (`15,005`), and `trec7` (`44,096`), with `3,752` exact duplicates and `5,112` near-template duplicates. Because TREC labels `spam` (`1.0`) rather than phishing vs promotional spam, we stripped anonymization tokens (`<|...|>` / `[ORGANIZATION]`), deduplicated templates, and filtered `1.0` to phishing/financial/account/advance-fee topics.
  - **Cross-Source Model Comparison (`tools/meajor_experiments.py`, `benchmark/meajor_model_comparison.json` — train `trec5+trec6` `8,000` rows, unseen test `trec7` `3,000` rows, plus `4,827` UCI SMS `ham`):**
    - `1_baseline_char_svm_394`: Acc `0.5323`, Prec `0.8012`, Rec `0.0860`, F1 `0.1553` (`1,371` FN), UCI SMS `ham` FP `9.90%`.
    - `2_word_char_linear_svm`: Acc `0.8663`, Prec `0.8829`, Rec `0.8447`, F1 `0.8634` (`233` FN), UCI SMS `ham` FP `4.62%`, `1,413.9 KB` (uncompressed).
    - `3_word_char_logreg` *(selected)*: Acc `0.8743`, Prec `0.8968`, Rec `0.8460`, F1 `0.8707` (`146` FP, `231` FN), UCI SMS `ham` FP `2.92%`, `0.002 ms/doc`, **`470.0 KB`** compressed (`scamshield/data/email_phish_model.joblib`).
    - `4_word_char_complement_nb`: Acc `0.8550`, Prec `0.8429`, Rec `0.8727`, F1 `0.8575`, UCI SMS `ham` FP `22.77%` (too noisy).
    - `5_ensemble_logreg_cnb`: Acc `0.8670`, Prec `0.8722`, Rec `0.8600`, F1 `0.8661`, UCI SMS `ham` FP `7.06%`.
  - **Validated Production Integration (`scamshield/email_classifier.py`, `scamshield/engine.py`):** Integrated `email_phish_model.joblib` as a specialized email classifier alongside the existing multilingual engine (activated for `email` channel, `.eml` uploads, or messages with email headers; never double-counts with the 394-row SVM; respects `safety_education_hint` guards). Full 10-category contextual suite: **10/10** correct (`polished_phishing_email` improved from `no_clear_signal` to `caution`, `legit_similar_wording` stays `no_clear_signal`).
  - **Final Verification:** `.\.venv\Scripts\python.exe -m pytest -v -s` → **668 passed, 0 failed, 0 skipped in 6.92s**.
