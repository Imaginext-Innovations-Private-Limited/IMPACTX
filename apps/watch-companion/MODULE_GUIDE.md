# `apps/watch-companion` — Module Guide (Teammate B)

**Track**: Tier-0 Dual-Mode Watch Companion (`CHW_COMPANION` / `PATIENT_FAMILY`)  
**Owned Path**: `apps/watch-companion/` (do NOT edit `packages/` or `services/`)


---

## 1. Contract Lock & Dual-Mode Spec

1. **TypeScript Contracts**: Import all types from `../../packages/contracts/ts/index.ts` (`WatchMode`, `NodeTier`, `HardwareCapabilityManifest`, `CrdtEvent`, `ActionCard`, `TriageSeverity`, `SyncEnvelope`).
2. **Circular 360x360 Viewport**: Keep the UI glanceable and thumb-operable inside the `360x360` circular bezel (`index.html`), supporting instant toggle between:
   - `CHW_COMPANION`: 1-tap WHO IMNCI danger-sign screening, urgent `ActionCard` notifications, peer sync trigger.
   - `PATIENT_FAMILY`: Medication & India UIP vaccine reminders, clear danger-sign SOS button, offline event queueing.
3. **Clinical Safety Invariant**: Any single danger sign forces `TriageSeverity.RED_EMERGENCY` locally with zero network dependency.
4. **Pure Indigenous Indic Vocabulary**: Use *Shuddh Tatsama* / classical Dravidian clinical strings for localized watch cards and voice/haptic prompts (zero Perso-Arabic loanwords or Hinglish).

---

## 2. Quickstart

```bash
cd apps/watch-companion
npm run dev       # opens 360x360 circular watch simulator on http://127.0.0.1:5174
```

If you install dev tooling (`npm install` inside `apps/watch-companion`):

```bash
npm run typecheck # runs tsc --noEmit against packages/contracts/ts/index.ts
```

---

## 3. What to Build Next

1. Wire `WatchKernel` (`src/watch_kernel.ts`) into `index.html` (or Vite + Preact/Vanilla TS bundle) with `localStorage` / IndexedDB persistence.
2. Render incoming `ActionCard` items filtered by `watch_mode`, sorted by `ActionCardPriority` (`CRITICAL` -> `LOW`).
3. Add peer sync button posting `WatchKernel.buildSyncEnvelope()` to Tier-2 Hub `POST /api/v1/sync` (or Tier-1 Phone relay).
