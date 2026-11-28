/** WS /ws/mesh transport: same SyncEnvelope in/out, auto-reconnect with capped exponential backoff. */
import type { SyncEnvelope } from "../../../../packages/contracts/ts/index";
import { isSyncEnvelope } from "./apply";

/** The subset of the browser WebSocket we rely on (lets tests inject a fake). */
export interface WsLike {
  readyState: number;
  send(data: string): void;
  close(): void;
  onopen: ((ev: unknown) => void) | null;
  onclose: ((ev: unknown) => void) | null;
  onerror: ((ev: unknown) => void) | null;
  onmessage: ((ev: { data: unknown }) => void) | null;
}
export type WsFactory = (url: string) => WsLike;

export interface MeshSocketOptions {
  baseDelayMs?: number;
  maxDelayMs?: number;
  wsFactory?: WsFactory;
  onOpen?: () => void;
  onEnvelope: (env: SyncEnvelope) => void;
  onDisconnect?: () => void;
}

const OPEN = 1;

export function backoffDelay(attempt: number, base = 1000, max = 30000): number {
  return Math.min(max, base * 2 ** attempt);
}

export class MeshSocket {
  private ws: WsLike | null = null;
  private attempt = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private stopped = true;

  constructor(private readonly url: string, private readonly opts: MeshSocketOptions) {}

  static urlFor(hubUrl: string): string {
    return hubUrl.replace(/\/+$/, "").replace(/^http/, "ws") + "/ws/mesh";
  }

  get connected(): boolean {
    return this.ws?.readyState === OPEN;
  }

  start(): void {
    if (!this.stopped) return;
    this.stopped = false;
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    const ws = this.ws;
    this.ws = null;
    ws?.close();
  }

  /** Returns false (caller falls back to HTTP) when the socket is not open. */
  send(env: SyncEnvelope): boolean {
    if (!this.ws || this.ws.readyState !== OPEN) return false;
    try {
      this.ws.send(JSON.stringify(env));
      return true;
    } catch {
      return false;
    }
  }

  private connect(): void {
    let ws: WsLike;
    try {
      ws = (this.opts.wsFactory ?? ((u) => new WebSocket(u) as unknown as WsLike))(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.ws = ws;
    ws.onopen = () => {
      this.attempt = 0;
      this.opts.onOpen?.();
    };
    ws.onmessage = (ev) => {
      let msg: unknown;
      try {
        msg = JSON.parse(String(ev.data));
      } catch {
        return;
      }
      if (isSyncEnvelope(msg)) this.opts.onEnvelope(msg); // {"error": ...} replies are ignored
    };
    ws.onerror = () => ws.close();
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      this.opts.onDisconnect?.();
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    if (this.stopped || this.timer) return;
    const delay = backoffDelay(this.attempt++, this.opts.baseDelayMs, this.opts.maxDelayMs);
    this.timer = setTimeout(() => {
      this.timer = null;
      if (!this.stopped) this.connect();
    }, delay);
  }
}
