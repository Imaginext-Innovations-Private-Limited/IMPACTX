/**
 * Voice-clip blob transport: HEAD-then-PUT /api/v1/blobs/{key} (idempotent dedup).
 * Transient failures throw SyncTransportError ("offline" | "error"); permanent
 * ones (bad key, hub 4xx) resolve as "rejected" so callers stop retrying.
 */
import { SyncTransportError } from "./transport-http";

/** Mirrors the hub's blob_store key rule. */
const BLOB_KEY_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;

export const isValidBlobKey = (key: unknown): key is string =>
  typeof key === "string" && BLOB_KEY_RE.test(key) && !key.includes("..");

/** "missing": hub lacks it and so does this device. "rejected": permanent (bad key / hub 4xx). */
export type BlobUploadOutcome = "present" | "uploaded" | "missing" | "rejected";

/** 4xx other than timeout / rate-limit will never succeed on retry. */
const permanent = (status: number) => status >= 400 && status < 500 && status !== 408 && status !== 429;

const blobUrl = (hubUrl: string, key: string) =>
  `${hubUrl.replace(/\/+$/, "")}/api/v1/blobs/${encodeURIComponent(key)}`;

/**
 * One deadline covers HEAD, local blob load, PUT and draining the PUT reply.
 * `loadBlob` runs only when the hub lacks the key; a locally absent clip
 * resolves "missing" (the caller decides what that means).
 */
export async function uploadBlobIfMissing(
  hubUrl: string,
  blobKey: string,
  loadBlob: () => Promise<Blob | undefined>,
  fetchImpl: typeof fetch = globalThis.fetch,
  timeoutMs = 30000,
): Promise<BlobUploadOutcome> {
  if (!isValidBlobKey(blobKey)) return "rejected";
  const ctrl = typeof AbortController === "function" ? new AbortController() : undefined;
  const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : undefined;
  const url = blobUrl(hubUrl, blobKey);
  const send = async (init: RequestInit): Promise<Response> => {
    try {
      return await fetchImpl(url, { ...init, cache: "no-store", signal: ctrl?.signal });
    } catch (err) {
      throw new SyncTransportError(`blob ${init.method} failed: ${String(err)}`, "offline");
    }
  };
  try {
    const head = await send({ method: "HEAD" });
    if (head.ok) return "present";
    if (head.status !== 404) {
      if (permanent(head.status)) return "rejected";
      throw new SyncTransportError(`blob HEAD failed: HTTP ${head.status}`, "error");
    }
    let blob: Blob | undefined;
    try {
      blob = await loadBlob();
    } catch (err) {
      throw new SyncTransportError(`local audio unreadable: ${String(err)}`, "error");
    }
    if (!blob) return "missing";
    const put = await send({
      method: "PUT",
      headers: { "Content-Type": blob.type || "application/octet-stream" },
      body: blob,
    });
    try {
      await put.text(); // drain under the same deadline
    } catch (err) {
      throw new SyncTransportError(`blob PUT reply unreadable: ${String(err)}`, "error");
    }
    if (put.ok) return "uploaded";
    if (permanent(put.status)) return "rejected";
    throw new SyncTransportError(`blob PUT failed: HTTP ${put.status}`, "error");
  } finally {
    if (timer) clearTimeout(timer);
  }
}
