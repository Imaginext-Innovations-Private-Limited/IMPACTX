# ScamShield AI v2.1.1 — Digital Arrest and UPI Fraud Detector

Track B · Problem Statement 5 · Wisework × Imagenext internship hackathon

ScamShield is a local-first safety assessment prototype for suspicious messages, UPI requests, screenshots and user-supplied call transcripts. It shows warning signs and practical next steps. It does not prove fraud or intercept calls, read private chats or verify senders.

## Run on Windows

Use Python 3.11 or newer with compatible dependencies (tested on Python 3.14.6 / scikit-learn 1.9.1). Install Tesseract separately for OCR. Add traineddata for desired languages: eng, hin, ben, kan, tel, ori, mar, tam, mal, guj, pan.

```cmd
run.bat setup
run.bat offline
```

First setup needs internet to install missing Python packages from `requirements.txt`; no transformer model download is needed. Normal `run.bat` also installs missing dependencies and privately prompts for optional Groq and Sarvam keys. Press Enter to skip either. Open http://127.0.0.1:8000 after startup. Stop the server with Ctrl+C before restarting; the launcher checks that port 8000 is available. Use `run.bat setup` to explicitly refresh the dependency installation (no automatic upgrade on every launch).

`run.bat offline` disables the Groq/Sarvam cloud keys, not the entire computer network. After setup, text analysis and bundled audio work without internet; OCR needs the local executable and language files. Browser dictation may still use its provider. Uploaded recording transcription needs configured Sarvam and consent. Keys are not saved by the launcher. Never commit keys, private messages or personal recordings.

## Use the app

1. Paste text or a UPI request, upload a screenshot and review OCR, or review a dictated/transcribed recording.
2. Analyze locally; optionally opt in to online AI when configured. Consent is off on page load. Analysis never starts automatically.
3. Read the evidence and safety actions. **No Clear Signal** means no known scam signals were found, not that the message is legitimate. Review is a recommendation to verify, not confirmed fraud.
4. Choose English, Hindi, Bengali, Kannada, Telugu, Odia, Marathi, Tamil, Malayalam, Gujarati or Punjabi for written/spoken guidance. Press Hear warning. Saved clips and bundled basic voices are fixed safety scripts, not arbitrary user text. Detailed evidence and Rescue Assistant may remain English. Native-speaker review is incomplete.
5. If affected, use Rescue Assistant and contact your bank promptly if money or credentials were exposed. For Indian financial cybercrime, guidance includes 1930 and https://cybercrime.gov.in/. The app does not submit reports itself.

## Architecture

- FastAPI, HTML/CSS/JS, Pillow and Tesseract OCR.
- Offline: contextual rules plus character TF-IDF + Linear SVM (394 balanced synthetic training messages; decision margin 0.20). SVM-only alerts are limited to Review; the margin is not a probability. Native-script contextual rules combine arrest, recruitment, prize and UPI-PIN action concepts in ten Indian-language lexicons; the existing English rules remain in place.
- Optional online AI: Groq GPT-OSS 120B with bounded GPT-OSS 20B backup on eligible failures, structured evidence, best-effort masking and local fallback. The higher warning level is retained on disagreement.
- Sarvam optional transcription and fixed warning synthesis, local cached audio, browser and bundled basic fallback. No user message is sent for fixed-script synthesis.
- The IndicSBERT and combined-feature candidates were evaluated but excluded from this release; no PyTorch or sentence-transformers dependency is required.

## Tests and evidence

```cmd
.venv\Scripts\python.exe -m pytest -v -s
.venv\Scripts\python.exe benchmark\final_comparison.py
```

Previous v2.1.0 package verified on Windows: 615 passed, 1 skipped; offline release smoke passed. v2.1.1 verified in Linux (Python 3.13.5, scikit-learn 1.8.0): 627 passed, zero failed/skipped, including 11 research-tool tests. Actual English OCR, 121 cached warning endpoints and 242 MP3 streams checked. Seven Chromium DOM smoke groups passed using an in-process API bridge and simulated provider/microphone events. This is not a live browser/provider test. Run Windows acceptance for this revision before distribution.

Run the final full-engine comparison: `.venv\Scripts\python.exe benchmark\final_comparison.py`. Against the uploaded 350-example engine in the same Linux environment, the 394-example candidate flags 34/55 suspicious and 5/55 benign messages on the earlier selection set (previously 34/55 and 11/55). On the prior small holdout it flags 22/22 suspicious and 2/22 benign (previously 22/22 and 6/22). On a regional development audit it flags 44/44 suspicious and 13/44 benign (previously 35/44 and 13/44). These are synthetic, scenario-related development cases, not independent real-world accuracy. All four previously missed regional messages now have rule evidence and receive Caution. See [benchmark guide](benchmark/README.md) and [release verification](docs/RELEASE_VERIFICATION.md).

## Research and known limitations

The 10,164-message external-data research did not justify a production replacement. The new ensemble evaluator is fixture-tested but real external files were absent from the submitted archive, so its performance is pending. Run `run_research.bat` only if you retain the original cached datasets and research environment. No model export or runtime integration occurs. See [research guide](benchmark/research/external/README.md). The new 44-message synthetic audit flagged 16/22 suspicious messages and 5/22 benign messages. Actual OCR returned text for all 11 synthetic language examples, but Odia and Malayalam lost the warning after recognition errors. Review all extracted text. No claim of real-world reliability or equal per-language detection.

## Project layout

- `scamshield/` — detection and backend
- `static/` — interface, fonts and bundled basic audio
- `tools/` — launch and optional voice generation
- `tests/` — regression and integration tests (cloud responses mocked)
- `benchmark/` — standalone classifier and full-engine comparisons
- `docs/` — engineering and demonstration notes; older version-labelled documents describe historical behavior, not the current release
- `voice_cache/` — locally generated audio excluded from Git; distribute only with appropriate provider rights

See [final release guide](docs/FINAL_RELEASE.md), [demo script](docs/DEMO_SCRIPT.md) and [historical SVM migration](docs/SVM_MIGRATION.md). The prototype has not received independent financial, security or production validation; do not treat any warning as proof of fraud or safety. License: MIT.
