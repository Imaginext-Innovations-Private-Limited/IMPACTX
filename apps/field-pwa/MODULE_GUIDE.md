# `apps/field-pwa` — Module Guide (Teammate A)

**Track**: Tier-1 CHW Offline Phone PWA  
**Owned Path**: `apps/field-pwa/` (do NOT edit `packages/` or `services/`)


---

## 1. Contract Lock & Core Invariants

1. **TypeScript Contracts**: Import all shared types from `../../packages/contracts/ts/index.ts` (`CrdtEvent`, `SyncEnvelope`, `PatientRecord`, `TriageAssessment`, `ActionCard`, `HardwareCapabilityManifest`).
2. **Zero RPC Coupling**: Every patient registration, WHO IMNCI danger-sign triage, UIP vaccination checklist, and voice-note recording MUST succeed in **Airplane Mode** with local persistence (IndexedDB) before any Hub sync occurs.
3. **Pure Indigenous Indic Vocabulary**: Any Hindi/regional UI strings MUST use *Shuddh Tatsama* / classical Dravidian clinical vocabulary (zero Perso-Arabic loanwords or Hinglish).

---

## 2. Quickstart

```bash
cd apps/field-pwa
npm install
npm run build      # esbuild bundle -> dist/, then stamps the service-worker cache version
npm run dev        # build + serve on http://127.0.0.1:5173
npm run typecheck  # tsc --noEmit (src + tests, contracts imported from packages/contracts/ts)
npm test           # vitest: core, sync, clinical parity, ui
```

Run against a hub: `make run-hub` from the repo root. Set `AAROGYA_HUB_DB=<path>` so
events survive a hub restart (the default is in-memory). Hub URL is set in the app's Sync screen.
The hub serves the **built** `dist/` at `/phone/` (run `npm run build` first). When opened from
`http://<hub>:8000/phone/` the hub URL defaults to the page origin; otherwise `127.0.0.1:8000`.
Clear the field to return to automatic. A saved loopback address is ignored on a non-loopback
hub origin. An `http://` override is blocked on an `https://` page.

---

## 3. Layout

| Path | Responsibility |
|---|---|
| `src/core/` | IndexedDB event log, outbox, cursor, patients, cards; persisted HLC |
| `src/sync/` | Hub delta sync (`POST /api/v1/sync`, `WS /ws/mesh`), apply/projection, emitter |
| `src/clinical/` | TypeScript port of IMNCI / maternal triage, UIP schedule, ANC/PNC checklists; rule tables copied from `packages/clinical-engine/rules/` |
| `src/ui/`, `src/i18n/` | Offline screens, Hindi/English strings, voice notes |
| `sw.js`, `scripts/stamp-sw.mjs` | App-shell service worker (never caches `/api/` or `/ws/`) |
| `tests/` | Unit tests plus parity fixtures generated from the Python engine |

Dependencies: no runtime dependencies; dev only (typescript, vitest, fake-indexeddb, esbuild).

---

## 4. Status and Known Gaps

Done: patient registration, triage (RED on any single danger sign), UIP vaccination log,
ANC/PNC checklists, offline voice notes, hub delta sync, action cards and enrichment count.

- **Hindi strings** have had only an AI review; a native-speaker pass is needed.
- **Rule tables** are generated copies; `tests/clinical/rules_parity.test.ts` fails if they drift from `packages/clinical-engine/rules/`. Regenerate them when the engine rules change.
- **Python engine aliases:** some natural phrasings (e.g. `not_able_to_drink`) have no alias in the Python engine; the UI offers canonical flags only.
- **Multi-tab:** two tabs on one database could mint duplicate HLCs (HLC read-compute-write is not one transaction).

**Plain-http LAN access:** over `http://<lan-ip>/phone/` (a non-secure context) the app loads and works; ids use a `getRandomValues` fallback for `crypto.randomUUID` (`src/core/uuid.ts`).
The service worker (offline shell) and microphone recording need https or localhost (secure context); everything else works.
