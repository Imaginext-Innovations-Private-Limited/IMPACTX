# External dataset research (not production)

The four original training scripts are retained here. The multi-source script now accepts `--ensemble`, which adds fixed threshold-vote experiments (baseline OR MIT; baseline OR MIT OR BSIS; two of three). It uses the same full offline engine, including contextual rules and the 0.20 margin; a model-only flag stays Review. The fusion output is only a threshold sentinel, not calibrated confidence. No external model, raw dataset, API key or trained artifact is shipped or loaded by the production application.

## Reproduce on the original research computer

Keep `Semantic_Research/large_dataset_experiment/downloads` and its `.venv` beside the project. Those files were absent from the uploaded GPT.zip, so the external comparison could not be executed here. DNS/network access to Hugging Face failed here. The research environment needs pyarrow and the project requirements. Run from the main project root:

```cmd
run_research.bat
```

Equivalent command:

```cmd
..\Semantic_Research\.venv\Scripts\python.exe benchmark\research\external\train_mixed_research.py --ensemble
```

The script uses cached parquet data only, writes results under `../Semantic_Research/large_dataset_experiment/ensemble_research`, and does not modify production. The new 44-case authored synthetic challenge is reserved before fitting; this may change the external counts compared with previous results. All previously examined sets are development evidence. The new challenge is not independent real-world validation and has not been reviewed by native speakers. A small fixture pipeline was executed successfully in Linux, not the real external-data ensemble.

`reported_mixed_comparison.csv` is a transcription of the user's actual Windows terminal output, not a rerun. Other original research scripts can be invoked from the project root with their new paths. The MIT-source dataset is declared MIT by its publisher; verify provenance, rights, source revision and data labels before product use. BSIS is research/educational-use restricted in the prior research review; do not distribute derived models or its data without permission. No BSIS data or weights are included here. Do not assume license compatibility for a trained ensemble just because one component is MIT. Keep all research outputs outside public GitHub until reviewed.

## Selection decision

The 394-message model is retained for the release: the external candidates performed better on their own sources but regressed on earlier evaluation sets. The 10,164-row combined candidate reached F1 98.75% on the filtered MIT test and 66.47% on the previously examined BSIS test, but only 59.34% on prior selection (baseline 72.34%). No claim is made that the 394-row model is globally best or safe for unsupervised use. An eligible replacement needs native-speaker/independent labels, appropriately licensed training data, fresh cross-source per-language evaluation, and measured artifact size. Do not select on the same repeatedly reused tests.
