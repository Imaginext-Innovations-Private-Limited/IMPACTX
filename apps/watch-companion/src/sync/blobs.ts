/**
 * Idempotent Watch voice-blob upload over Tier-2 PHC Hub `/api/v1/blobs/{blob_key}`.
 *
 * Performs a `HEAD` existence check before `PUT` to avoid redundant transfers over
 * constrained Watch/BLE/Wi-Fi links, and fails soft when offline or on HTTP errors.
 */

export interface BlobMetadata {
  blob_key: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
}

export type BlobUploadStatus = "uploaded" | "already_exists" | "offline" | "error";

export type BlobUploadResult =
  | {
      ok: true;
      status: "uploaded" | "already_exists";
      blobKey: string;
      metadata?: BlobMetadata;
    }
  | {
      ok: false;
      status: "offline" | "error";
      blobKey: string;
      reason: string;
    };

export interface UploadBlobOptions {
  contentType?: string;
  timeoutMs?: number;
}

const BLOB_KEY_REGEX = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;

/** Mirrors `LocalBlobStore.validate_key` in `services/phc-hub`. */
export function isValidBlobKey(blobKey: string): boolean {
  return BLOB_KEY_REGEX.test(blobKey) && !blobKey.includes("..");
}

function normalizeBaseUrl(hubUrl: string): string {
  return hubUrl.trim().replace(/\/+$/, "");
}

function getBlobSize(blob: Blob | Uint8Array): number {
  return blob instanceof Uint8Array ? blob.byteLength : blob.size;
}

function resolveContentType(blob: Blob | Uint8Array, explicit?: string): string {
  if (explicit && explicit.trim().length > 0) {
    return explicit.split(";")[0].trim();
  }
  if (!(blob instanceof Uint8Array) && blob.type) {
    return blob.type.split(";")[0].trim() || "application/octet-stream";
  }
  return "application/octet-stream";
}

function toFetchBody(blob: Blob | Uint8Array): BodyInit {
  if (blob instanceof Uint8Array) {
    const copy = new Uint8Array(blob.byteLength);
    copy.set(blob);
    return copy;
  }
  return blob;
}

async function fetchWithTimeout(
  fetchImpl: typeof fetch,
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const ctrl = typeof AbortController === "function" ? new AbortController() : undefined;
  const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : undefined;
  try {
    return await fetchImpl(url, {
      ...init,
      cache: "no-store",
      signal: ctrl?.signal,
    });
  } finally {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
  }
}

/**
 * Upload `blob` to `{hubUrl}/api/v1/blobs/{blobKey}` only if `HEAD` reports 404.
 *
 * Strictly fail-soft: never throws on network outage, timeout, or 4xx/5xx responses.
 */
export async function uploadWatchBlobIfMissing(
  hubUrl: string,
  blobKey: string,
  blob: Blob | Uint8Array,
  fetchImpl: typeof fetch = globalThis.fetch,
  options: UploadBlobOptions = {},
): Promise<BlobUploadResult> {
  if (!isValidBlobKey(blobKey)) {
    return {
      ok: false,
      status: "error",
      blobKey,
      reason: "Invalid blob_key: must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ without '..'.",
    };
  }

  if (getBlobSize(blob) === 0) {
    return {
      ok: false,
      status: "error",
      blobKey,
      reason: "Blob payload cannot be empty.",
    };
  }

  if (typeof fetchImpl !== "function") {
    return {
      ok: false,
      status: "offline",
      blobKey,
      reason: "Fetch implementation unavailable.",
    };
  }

  const timeoutMs = options.timeoutMs ?? 15_000;
  const url = `${normalizeBaseUrl(hubUrl)}/api/v1/blobs/${encodeURIComponent(blobKey)}`;

  let headRes: Response;
  try {
    headRes = await fetchWithTimeout(fetchImpl, url, { method: "HEAD" }, timeoutMs);
  } catch (err) {
    return {
      ok: false,
      status: "offline",
      blobKey,
      reason: err instanceof Error ? err.message : String(err),
    };
  }

  if (headRes.status === 200 || headRes.ok) {
    return {
      ok: true,
      status: "already_exists",
      blobKey,
    };
  }

  if (headRes.status !== 404) {
    return {
      ok: false,
      status: "error",
      blobKey,
      reason: `HEAD /api/v1/blobs/${blobKey} failed with HTTP ${headRes.status}.`,
    };
  }

  const contentType = resolveContentType(blob, options.contentType);
  let putRes: Response;
  try {
    putRes = await fetchWithTimeout(
      fetchImpl,
      url,
      {
        method: "PUT",
        headers: { "Content-Type": contentType },
        body: toFetchBody(blob),
      },
      timeoutMs,
    );
  } catch (err) {
    return {
      ok: false,
      status: "offline",
      blobKey,
      reason: err instanceof Error ? err.message : String(err),
    };
  }

  if (!putRes.ok) {
    return {
      ok: false,
      status: "error",
      blobKey,
      reason: `PUT /api/v1/blobs/${blobKey} failed with HTTP ${putRes.status}.`,
    };
  }

  let metadata: BlobMetadata | undefined;
  try {
    if (typeof putRes.json === "function") {
      const parsed = (await putRes.json()) as Partial<BlobMetadata> | null;
      if (
        parsed &&
        typeof parsed === "object" &&
        typeof parsed.blob_key === "string" &&
        typeof parsed.sha256 === "string"
      ) {
        metadata = parsed as BlobMetadata;
      }
    }
  } catch {
    // Metadata body is optional if a mock/proxy returns empty 200/201.
  }

  return {
    ok: true,
    status: "uploaded",
    blobKey,
    ...(metadata ? { metadata } : {}),
  };
}
