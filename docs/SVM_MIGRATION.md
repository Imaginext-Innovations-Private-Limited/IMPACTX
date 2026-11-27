# ScamShield AI — experimental Linear SVM migration

> Historical notes. For current v2.1 behavior and setup, see [final release guide](FINAL_RELEASE.md) and [README](../README.md).

## Decision and safeguards

The candidate was integrated into the v2.1 development branch after Windows regression and live offline/hybrid checks. The stable v2.0.1 release remains unchanged. The bundled 64 synthetic training messages and character-level TF-IDF (3–5 grams) are unchanged. LinearSVC replaces LogisticRegression. The model is fitted locally on first use and cached. The former threshold (LR score >= 0.85) is replaced with a signed SVM decision margin >= 0.30, NOT a probability. The five-word minimum and Review-only cap are preserved. No safety rules, score scale, cloud integration, language handling, OCR, frontend, or voice files changed. These statements describe the migration experiment itself, not subsequent UI updates.

The margin was chosen using a conservative training-only rule: five-fold stratified out-of-fold predictions (shuffle, seed 42), then round the maximum benign score (0.284739 in this environment) up to the next 0.05 step (0.30). This does not guarantee zero false alerts on unseen data. The older challenge had already been seen during project development; the additional challenge is separately authored synthetic data, not blinded external validation. No tuning is performed on the second challenge.

## Results

| Dataset | Metric | Former LR | SVM candidate |
|---|---|---:|---:|
| Previous 40 | Review or higher: suspicious flagged / 20 | 7 | 11 |
| Previous 40 | Review or higher: benign flagged / 20 | 4 | 5 |
| Previous 40 | Review or higher: F1 | 45.2% | 61.1% |
| Previous 40 | Caution or higher: suspicious flagged / 20 | 6 | 6 |
| Previous 40 | Caution or higher: benign flagged / 20 | 3 | 3 |
| Second 40 | Review or higher: suspicious flagged / 20 | 10 | 13 |
| Second 40 | Review or higher: benign flagged / 20 | 0 | 1 |
| Second 40 | Review or higher: F1 | 66.7% | 76.5% |
| Second 40 | Caution or higher: suspicious flagged / 20 | 9 | 9 |
| Second 40 | Caution or higher: benign flagged / 20 | 0 | 0 |

In total, Review-or-higher flagged 17/40 suspicious cases before and 24/40 after; benign warnings rose from 4/40 to 6/40. Seven additional suspicious cases and two additional benign cases moved to Review. All Caution and High classifications and their indicators remained identical in the two challenges. Fifteen of 40 suspicious cases still received Caution or High Risk; SVM does not solve the underlying offline rules' coverage limitation. Review is an independent verification recommendation, not proof of fraud.

Test run: baseline 442 passed; candidate 453 passed (442 original + 11 new). English Tesseract OCR test ran successfully in this Linux environment. Python 3.13 / scikit-learn 1.8.0; the user's Windows installation may still skip the OCR test. Cloud tests use mocked providers. Live Groq/Sarvam credentials were not used. Chromium local navigation was blocked by the environment (ERR_BLOCKED_BY_ADMINISTRATOR); actual browser and hardware playback checks remain pending. JavaScript source was not modified during the migration experiment. Later Windows checks: 452 passed, 1 skipped; live offline and primary Groq hybrid checks passed. Full release verification remains pending.

## Reproduce from the project root

Windows CMD:

```cmd
.venv\Scripts\python.exe -m pytest -v -s
.venv\Scripts\python.exe benchmark\model_comparison.py
```

The command above runs the simplified three-classifier experiment (64 synthetic training samples and 40 synthetic challenge samples) and regenerates `benchmark/model_comparison.csv`. It does not reproduce the full-engine results in the table. For that separate historical experiment, use the `benchmark_svm_migration.py` and supporting `benchmark_offline_models.py` files from the archived evaluation/testing copy, in that project root. The migration experiment swapped the old LR model and threshold only inside the isolated benchmark process and restored SVM automatically. Its outputs were `svm_migration_results/metrics.json` and `predictions.csv`. Keep the archived evidence separate from the live demo.

Do not claim real-world accuracy, full multilingual model validation or better high-risk detection. Retain the stable LR branch until Windows regression and live demo tests pass. Adoption is a trade-off: more useful Review warnings at the cost of some additional benign Review warnings, with no demonstrated improvement to Caution/High detection. Larger, independent multilingual datasets are needed before production selection.
