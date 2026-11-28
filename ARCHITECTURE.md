# Aarogya Mesh — System Architecture Specification

> **Mission**: An autonomous, offline-first, capability-proportional edge health mesh for Community Health Workers (ASHA/ANM) with a dual-mode Tier-0 Watch companion (`CHW_COMPANION` and `PATIENT_FAMILY`).

---

## 1. Core Invariant: The Autonomous Node Kernel

Every device tier in **Aarogya Mesh** runs an identical conceptual **Autonomous Node Kernel**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AUTONOMOUS NODE KERNEL                          │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐  │
│  │ Deterministic Rules │  │ Local Append-Only   │  │ Capability      │  │
│  │ (WHO IMNCI / ASHA / │  │ Event Store + HLC   │  │ Router          │  │
│  │  UIP Schedules)     │  │ + CRDT Projector    │  │ (Manifest)      │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ Opportunistic Local Sync
                                   │ (Hotspot / LAN / BLE / mDNS — Zero Internet)
                                   ▼
                 Immutable CrdtEvent Delta Exchange (SyncEnvelope)
```

### Architectural Guarantees
1. **Zero RPC Coupling**: No node ever blocks on a synchronous network call to another node or cloud server to complete patient registration, danger-sign triage, checklist capture, or vaccination tracking.
2. **Indefinite Standalone Operation**:
   - **Tier 0 (`TIER_0_WATCH`)**: Smart/wearable companion running deterministic 1-tap danger-sign screening, offline action cards, and dual-mode UX:
     - `CHW_COMPANION`: Hands-free ASHA quick-triage, red-flag alarm, next household action card.
     - `PATIENT_FAMILY`: Patient/family medication & vaccination reminders, red-flag self-check, emergency escalation prompt.
   - **Tier 1 (`TIER_1_PHONE`)**: CHW offline-first PWA (`apps/field-pwa`) running full WHO IMNCI pediatric triage, NHM ASHA maternal ANC/PNC checklists, UIP immunization schedules, local IndexedDB/SQLite event log, and offline voice-note capture.
   - **Tier 2 (`TIER_2_HUB`)**: Primary Health Centre (PHC) laptop hub (`services/phc-hub` + `services/ml-pipeline`) running FastAPI delta-sync, aggregated village caseload projection, and local CPU/NPU-optimized ML enrichment (`whisper.cpp`/`faster-whisper` INT8, quantized `Qwen2.5-3B` GBNF structurer, `LightGBM+SHAP` risk scoring, `EWMA` outbreak detection).
3. **Opportunistic Peer Upgrade via HLC/CRDT Delta Sync**:
   - Nodes append immutable `CrdtEvent` records ordered by **Hybrid Logical Clock (`HlcTimestamp`: `(wall_ms, logical, node_id)`)**.
   - Whenever two peers meet on local Wi-Fi Hotspot / LAN / mDNS, they exchange `SyncEnvelope` deltas using cursor-based idempotent deduplication (`event_id`).
   - Materialized state (`patients`, `triage_history`, `vaccinations`, `action_cards`) converges deterministically via LWW-Element-Map (by HLC) and add-wins sets — guaranteeing **strong eventual consistency** regardless of sync order or offline duration.
   - **Deferred Enrichment (Non-Blocking Offload)**: A Tier-0 Watch or Tier-1 Phone records a `VOICE_NOTE_RECORDED` event with `enrichment_state = PENDING`. When synced to a Tier-2 Hub, the Hub executes local transcription/structuring and appends `ENRICHMENT_COMPLETED` (referencing `ref_event_id`) plus optional `ACTION_CARD_ISSUED`. On the next peer sync, the enriched action card flows back to Phone and Watch, and `pending_enrichments` drops to zero.

---

## 2. Capability-Proportional Execution Matrix

Every node advertises a live `HardwareCapabilityManifest`:
- `node_id`, `tier` (`TIER_0_WATCH` | `TIER_1_PHONE` | `TIER_2_HUB`)
- `ram_mb`, `cpu_cores`, `battery_pct`, `has_npu`, `installed_models`, `watch_mode`

The **Capability Router** (`ExecutionTarget`) maps each workload strictly from the local manifest without remote discovery:

| Workload | `TIER_0_WATCH` (<512 MiB) | `TIER_1_PHONE` (2–6 GiB) | `TIER_2_HUB` (≥16 GiB / Intel Core Ultra) |
| :--- | :--- | :--- | :--- |
| Danger-sign triage (IMNCI / ANC) | `LOCAL_DETERMINISTIC` | `LOCAL_DETERMINISTIC` | `LOCAL_DETERMINISTIC` |
| UIP Vaccine schedule & checklists | `LOCAL_DETERMINISTIC` | `LOCAL_DETERMINISTIC` | `LOCAL_DETERMINISTIC` |
| Keyword spotting / tiny risk check | `DEFER_TO_HUB` (or `LOCAL_TINY_ML` if battery ≥ 20% & model present) | `LOCAL_TINY_ML` (if battery ≥ 20% & model installed) | `LOCAL_TINY_ML` |
| Indic ASR (`whisper.cpp` INT8) | `DEFER_TO_HUB` (`PENDING`) | `DEFER_TO_HUB` (`PENDING`) | `LOCAL_TINY_ML` (Hub enrichment worker) |
| Clinical note structuring (GBNF SLM) | `DEFER_TO_HUB` (`PENDING`) | `DEFER_TO_HUB` (`PENDING`) | `LOCAL_TINY_ML` (Hub enrichment worker) |
| Village EWMA outbreak detection | `DEFER_TO_HUB` | `DEFER_TO_HUB` | `LOCAL_DETERMINISTIC` / `LOCAL_TINY_ML` |

### Hardware & Dependency Discipline
- **Reference Target**: Fedora Linux, Python 3.12 (`uv`), 32 GiB RAM, Intel Core Ultra 9 185H (x86_64 CPU + iGPU/NPU).
- **Zero Bloat Policy**: No `torch`, `cuda`, `nvidia-*`, or multi-gigabyte cloud SDKs in workspace dependencies. Edge inference uses lightweight native/ONNX/GGUF CPU+NPU runtimes (`whisper.cpp`, `llama.cpp`, `lightgbm`).

---

## 3. Clinical Safety Invariant

1. **Deterministic Hard Floor**: WHO IMNCI pediatric danger signs, NHM ASHA maternal pre-eclampsia/hemorrhage red flags, and India UIP vaccine schedules are encoded as inspectable JSON rule tables executed deterministically (`confidence = 1.0`, `execution_target = LOCAL_DETERMINISTIC`).
2. **Red-Flag Monotonicity**: Any single general danger sign or maternal emergency criterion **immediately forces `TriageSeverity.RED_EMERGENCY` and `referral_required = True`** — enforced both in `packages/clinical-engine` and as a Pydantic contract validator in `packages/contracts`.
3. **SLM Containment Boundary**: Local SLMs (`services/ml-pipeline`) **never** own raw triage severity classification or override deterministic danger signs. SLMs are strictly constrained via GBNF grammar to:
   - Structured symptom extraction from CHW voice notes (fed *into* the deterministic engine),
   - Patient/CHW-friendly localized `ActionCard` summaries grounded in deterministic outputs.

---

## 4. Pure Indigenous Indic Vocabulary Rule

All Indic-language UI labels, voice prompts, and `ActionCard` templates across `packages/`, `services/`, and `apps/` MUST adhere to **pure indigenous vocabulary**:
- **Indo-Aryan languages (Hindi, Marathi, Gujarati, Bengali, etc.)**: Use *Shuddh Tatsama* / *Tadbhava* Sanskrit-derived clinical and everyday terms (e.g., *ज्वर* instead of *बुख़ार*, *श्वास कष्ट* instead of *साँस की तकलीफ़*, *चिकित्सालय* / *प्राथमिक स्वास्थ्य केन्द्र* instead of *अस्पताल*/*दवाख़ाना*, *टीकाकरण*, *गर्भवती माता*, *आपातकाल*).
- **Dravidian languages (Tamil, Telugu, Kannada, Malayalam)**: Use classical Dravidian / standard indigenous clinical registers (e.g., Tamil *காய்ச்சல்*, *மூச்சுத்திணறல்*, *தடுப்பூசி*, *அவசர நிலை*).
- **Zero Perso-Arabic loanwords and zero Hinglish transliterations** in canonical Indic strings.

---

## 5. Contract-First Monorepo Layout

```text
aarogya-mesh/
├── packages/
│   ├── contracts/        # Single source of truth: Pydantic v2 models, JSON Schema 2020-12, TypeScript types
│   ├── clinical-engine/  # Deterministic WHO IMNCI, NHM ASHA ANC/PNC, India UIP vaccine engine
│   └── crdt-sync/        # Hybrid Logical Clock, SQLite event store, CRDT state projector, sync protocol
├── services/
│   ├── phc-hub/          # Tier-2 PHC FastAPI hub, capability router, delta-sync & WebSocket endpoints
│   └── ml-pipeline/      # Tier-2 local edge ML protocols & deterministic stubs (ASR, GBNF SLM, Risk, EWMA)
└── apps/
    ├── field-pwa/        # Tier-1 CHW offline-first PWA (typed against packages/contracts/ts/index.ts)
    └── watch-companion/  # Tier-0 dual-mode Watch companion (CHW_COMPANION / PATIENT_FAMILY)
```

All cross-module data structures MUST be imported from `aarogya_contracts` (Python) or `packages/contracts/ts/index.ts` (TypeScript) and validated against `packages/contracts/schemas/*.schema.json` via `make verify`.
