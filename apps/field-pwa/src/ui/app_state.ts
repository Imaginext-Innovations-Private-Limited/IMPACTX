/** Glue: periodic / opportunistic sync scheduling (best effort, never awaited by user actions). */
import type { SyncEngine } from "../sync";
import { setLastSync } from "./settings";
import { classifySyncFailure } from "./sync_logic";

export const SYNC_INTERVAL_MS = 30_000;

/** lastSync.detail when the exchange worked but voice notes were withheld for their clips. */
const HELD_PREFIX = "heldClips:";

/** Number of withheld voice clips encoded in a lastSync detail, or 0. */
export const heldClipsFromDetail = (detail: string): number =>
  detail.startsWith(HELD_PREFIX) ? Number(detail.slice(HELD_PREFIX.length)) || 0 : 0;

export function runSync(
  engine: SyncEngine,
  isOnline: () => boolean = () => (typeof navigator === "undefined" ? true : navigator.onLine),
): Promise<void> {
  return engine.syncNow().then((res) => {
    const st = engine.status;
    const held = engine.heldClips;
    setLastSync({
      at: Date.now(),
      ok: res !== null && held === 0, // clips still waiting is not plain success
      detail: res === null ? classifySyncFailure(st, engine.lastError, isOnline()) : held ? `${HELD_PREFIX}${held}` : "ok",
    });
  }, () => undefined);
}

export function startSyncLoop(engine: SyncEngine, isOnline: () => boolean = () => navigator.onLine): () => void {
  const tick = () => {
    if (isOnline()) void runSync(engine);
  };
  const timer = setInterval(tick, SYNC_INTERVAL_MS);
  const onOnline = () => tick();
  window.addEventListener("online", onOnline);
  tick();
  return () => {
    clearInterval(timer);
    window.removeEventListener("online", onOnline);
  };
}
