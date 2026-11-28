/** Minimal typed event emitter for UI subscriptions. */
import type { ActionCard } from "../../../../packages/contracts/ts/index";

export type SyncState = "idle" | "syncing" | "offline" | "error";

export interface SyncEvents {
  /**
   * `rejected`: malformed events in the last hub reply (cursor held back so they are re-offered).
   * `heldClips`: voice notes kept back from the last push until their clip reaches the hub.
   */
  status: { state: SyncState; pendingCount: number; error?: string; rejected?: number; heldClips?: number };
  cards: { cards: ActionCard[] };
  enrichment: { pending: number };
}

type Listener<T> = (data: T) => void;

export class Emitter<E extends object = SyncEvents> {
  private listeners: { [K in keyof E]?: Set<Listener<E[K]>> } = {};

  /** Subscribe; returns an unsubscribe function. */
  on<K extends keyof E>(type: K, fn: Listener<E[K]>): () => void {
    (this.listeners[type] ??= new Set()).add(fn);
    return () => this.listeners[type]?.delete(fn);
  }

  emit<K extends keyof E>(type: K, data: E[K]): void {
    for (const fn of this.listeners[type] ?? []) {
      try {
        fn(data);
      } catch {
        // A faulty UI listener must never break sync.
      }
    }
  }
}
