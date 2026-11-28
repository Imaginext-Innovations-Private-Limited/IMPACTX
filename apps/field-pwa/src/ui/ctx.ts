import type { FieldStore } from "../core";
import type { SyncEngine } from "../sync";

export interface Ctx {
  store: FieldStore;
  engine: SyncEngine;
  nodeId: string;
  /** Navigate to a hash route, e.g. "#/triage". */
  nav(hash: string): void;
  /** Re-render the current screen. */
  rerender(): void;
  /** Best-effort, fire-and-forget sync after a local save. */
  syncSoon(): void;
}

export type Screen = (ctx: Ctx, params: string[]) => HTMLElement | Promise<HTMLElement>;
