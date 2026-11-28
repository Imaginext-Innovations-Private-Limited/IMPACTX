# `services/ml-pipeline` — Module Guide (Teammate C)

**Track**: Tier-2 Local Edge ML & Outbreak Pipeline  
**Package**: `aarogya-ml-pipeline` (importable as `aarogya_ml_pipeline`)  
**Target Hardware**: Fedora Linux, Python 3.12 (`uv`), 32 GiB RAM, Intel Core Ultra 9 185H (x86_64 CPU + iGPU/NPU)


---

## 1. Zero-Bloat Hardware & Safety Rules

1. **NO PyTorch / CUDA Bloat**: Never add `torch`, `torchvision`, `torchaudio`, `tensorflow`, or `nvidia-*` to `pyproject.toml`. CI fails automatically if any of those packages appear in `uv pip list`.
2. **Clinical Safety Invariant**: Local ML models **never** own raw triage severity or override deterministic WHO IMNCI / ASHA rules in `packages/clinical-engine`. SLMs only extract structured symptom flags (which feed *into* deterministic rules) and format grounded `ActionCard` summaries.
3. **Graceful Offline Fallback**: Keep `Stub*` classes intact or ensure your adapters fall back cleanly when local GGUF/Whisper weights are absent so `make verify` passes on fresh clones.
4. **Pure Indigenous Indic Vocabulary**: Any generated Indic `ActionCard` templates or voice prompts must use *Shuddh Tatsama* (Indo-Aryan) or classical Dravidian clinical terms — zero Perso-Arabic loanwords or Hinglish.

---

## 2. Protocol Interfaces to Implement (`src/aarogya_ml_pipeline/interfaces.py`)

Implement concrete adapters for the 4 `@runtime_checkable` protocols:

1. **`VoiceTranscriber` -> `faster-whisper` or `whisper.cpp` INT8**
   - Recommended: `faster-whisper` (CTranslate2 CPU `int8`) or `pywhispercpp` with `whisper-small` / Indic Whisper quantized INT8 GGUF.
   - Input: `audio_bytes: bytes, language_hint: str = "hi"`.
   - Output: `TranscriptionResult`.

2. **`ClinicalSlmStructurer` -> `llama.cpp` (`Qwen2.5-3B-Instruct` Q4_K_M + GBNF)**
   - Recommended: `llama-cpp-python` (CPU / OpenVINO / Vulkan, no CUDA) with a strict **GBNF grammar** enforcing JSON matching `StructuredClinicalNote`.
   - Input: `transcript: str, language: str = "hi"`.
   - Output: `StructuredClinicalNote` (`extracted_symptoms`, `candidate_danger_flags`, `recommended_follow_up`).

3. **`RiskScorer` -> `LightGBM` + `SHAP`**
   - Recommended: `lightgbm` + `shap` (`TreeExplainer`) on tabular patient features (`age_months`, `fever_days`, `respiratory_rate`, `gestational_weeks`, etc.).
   - Output: `RiskScoreResult` with calibrated `risk_score`, `risk_band`, and `shap_attributions`.

4. **`OutbreakDetector` -> `EWMA` Spatiotemporal Spike Detector**
   - Pure NumPy/Python Exponentially Weighted Moving Average over rolling village syndrome counts.
   - Output: `OutbreakSignal` mapped to `EventType.OUTBREAK_ALERT_RAISED` when `alert_triggered=True`.

---

## 3. Optional Local Weights, Synthetic Model Training & Offline Fallback

Base workspace installation (`uv sync --all-packages`) intentionally excludes heavy native wheels and model weights so CI and fresh clones stay fast and free of PyTorch/CUDA bloat. Each concrete backend degrades cleanly to a deterministic stub when optional dependencies or local weight files are absent:

| Backend | Protocol | Optional Extra / Runtime | Environment Variable(s) | Offline Fallback |
| --- | --- | --- | --- | --- |
| `WhisperVoiceTranscriber` | `VoiceTranscriber` | `asr` (`faster-whisper` / `pywhispercpp` CPU INT8) | `AAROGYA_WHISPER_MODEL_PATH`, `AAROGYA_WHISPER_MODEL_SIZE` | `StubVoiceTranscriber` (`stub-asr-fallback`) |
| `LlamaCppSlmStructurer` | `ClinicalSlmStructurer` | `slm` (`llama-cpp-python` + `clinical_note.gbnf`) | `AAROGYA_SLM_GGUF_PATH` | `StubClinicalSlmStructurer` (`stub-slm-fallback`) |
| `LightGbmRiskScorer` | `RiskScorer` | `risk` (`lightgbm` + TreeSHAP `pred_contrib=True`) | `AAROGYA_RISK_MODEL_PATH` | `StubRiskScorer` (`stub-lightgbm-fallback`) |
| `EwmaOutbreakDetector` | `OutbreakDetector` | Pure Python stdlib (`math`, `statistics`) | — | Always active natively |

### Training the Local LightGBM Risk Model

`services/ml-pipeline/models/` is gitignored (`models/risk_lgbm.txt` is generated locally, not checked into git). To generate a deterministic (`seed=42`) CPU LightGBM model locally after installing optional `risk` dependencies:

```bash
uv run python services/ml-pipeline/scripts/train_synthetic_risk_model.py \
  --output services/ml-pipeline/models/risk_lgbm.txt \
  --samples 3000 \
  --seed 42
```

---

## 4. Running Tests Locally

From the repo root (`aarogya-mesh/`):

```bash
uv sync
uv run pytest -v services/ml-pipeline/tests/
uv run ruff check services/ml-pipeline/
```

---

## 5. Wiring into Tier-2 Hub

`services/phc-hub` fetches pending `VOICE_NOTE_RECORDED` (`ENRICHMENT_PENDING`) events via `GET /api/v1/enrichment/pending` and processes them with `EnrichmentPipeline` / `enrich_voice_note_event(...)`, appending `ENRICHMENT_COMPLETED`, `ACTION_CARD_ISSUED`, and conditional `OUTBREAK_ALERT_RAISED` events to the CRDT store so they sync back to Tier-1 Phone and Tier-0 Watch.
