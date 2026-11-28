# v2.1 finalization guide

## Installation and startup

- Install compatible Python and, for screenshot OCR, Tesseract and desired language packs.
- Run `run.bat setup` with internet once. Verify dependency setup completes. Then disconnect internet and run `run.bat offline` to verify the local path. Stop the previous server before restarting.
- For optional online analysis, use `run.bat` and enter keys privately; do not distribute keys. Consent is required before sending message text or recordings to a provider.
- No IndicSBERT model or experimental research environment is required for the release. Do not bundle `.venv`; Windows virtual environments are not portable. A new computer needs dependency installation unless a compatible offline wheel repository is separately prepared and tested.

## Release smoke checks (on each demo machine)

- Text: genuine-style OTP notice remains No Clear Signal; OTP-for-lottery and digital arrest examples are flagged.
- Native-script input: test Tamil job fee, Malayalam lottery fee, Gujarati arrest threat and Punjabi UPI PIN (Caution or higher expected for the known cases). Disclose remaining misses on the wider benchmark.
- Audio: listen to warning and stop/replay in each claimed language. Basic audio is bundled; natural cached speech requires authorized distribution. Native pronunciation remains unverified where no fluent reviewer has checked it.
- OCR: upload a synthetic screenshot; verify extracted text and error behavior. Check installed language data using `tesseract --list-langs` if available on PATH.
- Cloud: with valid keys, test primary analysis, optional backup/fallback and consent off. Browser dictation and recorded upload are optional and require suitable browser/provider connectivity.
- Rescue Assistant: check all five paths, copy safety summary and complaint draft. Reporting is user initiated.
- Tests: run `.venv\Scripts\python.exe -m pytest -v -s` and record pass/fail/skip counts. Do not claim mocks prove live provider behavior.

## Packaging and Git

Review `git status --short` and the exact branch/commit. Keep the stable v2.0.1 release intact until an intentional release decision. Exclude `.git`, `.venv`, caches, API keys, private messages, recordings and experimental model weights from team ZIP. Include source, requirements, launcher, tests, docs, benchmark, bundled fonts/basic audio and only authorized natural cache files. Extract ZIP into a separate directory and test a fresh installation before distributing. Record the exact release commit and results. No public release is implied by this checklist.

## Judge explanation

ScamShield combines fast local rules and a lightweight ML classifier with optional online AI and multilingual spoken warnings. It provides practical actions even without cloud access. We evaluated several algorithms and chose the smaller SVM because larger semantic features brought only a modest improvement on synthetic tests. We expanded training from 64 to 350 and then 394 examples, increasing Review-or-higher flags but introducing some benign warnings. The app never certifies safety, intercepts calls or automatically reports a crime. The project needs independently labeled multilingual real-world data, native-speaker review and security evaluation before production use.

## Final candidate
Check `/api/health` for version `2.1.1` and `training_samples: 394` to detect stale processes. The supplied ZIP has no Git history. Extract to a NEW folder for testing; after successful tests, copy source changes into the existing `external-final-v2.1` checkout, review `git status`, and commit deliberately. Never copy `.git` or a virtual environment. Keep the old stable release. The desktop ZIP size is not an Android APK size; a future mobile app must meet the separate under-100-MB target.

Quick acceptance command after `run.bat setup`: `.venv\Scripts\python.exe tools\verify_release.py`. It checks offline API results, audio availability and English OCR (if installed) without any provider keys. Then run `.venv\Scripts\python.exe -m pytest -v -s` and complete live browser checks.

## Optional research, not required for demo
Run `run_research.bat` only with the sibling research cache and environment intact. Keep BSIS-derived models and data out of the release. See `benchmark/research/external/README.md`. The release retains the 394-example model; real-data ensemble evaluation is pending.
