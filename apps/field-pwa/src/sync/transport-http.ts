/** POST /api/v1/sync transport. Never caches; classifies failures for the engine. */
import type { SyncEnvelope } from "../../../../packages/contracts/ts/index";
import { isSyncEnvelope } from "./apply";

export class SyncTransportError extends Error {
  constructor(message: string, readonly kind: "offline" | "error") {
    super(message);
  }
}

export async function postSync(
  hubUrl: string,
  envelope: SyncEnvelope,
  fetchImpl: typeof fetch = globalThis.fetch,
  timeoutMs = 15000,
): Promise<SyncEnvelope> {
  const ctrl = typeof AbortController === "function" ? new AbortController() : undefined;
  const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : undefined;
  let res: Response;
  try {
    res = await fetchImpl(`${hubUrl.replace(/\/+$/, "")}/api/v1/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(envelope),
      cache: "no-store",
      signal: ctrl?.signal,
    });
  } catch (err) {
    if (timer) clearTimeout(timer);
    throw new SyncTransportError(`hub unreachable: ${String(err)}`, "offline");
  }
  let body: unknown;
  try {
    // Timeout stays armed until the body is fully read (a stalled body aborts too).
    if (!res.ok) throw new SyncTransportError(`hub sync failed: HTTP ${res.status}`, "error");
    body = await res.json();
  } catch (err) {
    if (err instanceof SyncTransportError) throw err;
    throw new SyncTransportError(`hub reply unreadable: ${String(err)}`, "error");
  } finally {
    if (timer) clearTimeout(timer);
  }
  if (!isSyncEnvelope(body)) throw new SyncTransportError("hub reply is not a SyncEnvelope", "error");
  return body;
}
