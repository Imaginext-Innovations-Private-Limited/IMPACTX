/**
 * Durable IndexedDB-backed queue for pending SOS voice audio blobs.
 *
 * Raw audio bytes are normalized to `Uint8Array` before starting the IndexedDB
 * transaction so transactions never auto-commit across async `Blob` reads and
 * work consistently across Android WebView and desktop browsers. Falls back
 * fail-soft to an in-memory map if IndexedDB is unavailable or blocked.
 */

export const DEFAULT_BLOB_DB_PREFIX = "aarogya-watch-blobs";
const BLOB_STORE_NAME = "blobs";
const BLOB_DB_VERSION = 1;

export interface QueuedWatchBlob {
  blob: Blob | Uint8Array;
  contentType: string;
}

export interface WatchBlobQueue {
  get(blobKey: string): QueuedWatchBlob | undefined | Promise<QueuedWatchBlob | undefined>;
  set(blobKey: string, entry: QueuedWatchBlob): void | Promise<void>;
  delete(blobKey: string): void | Promise<void>;
}

export class MemoryWatchBlobQueue implements WatchBlobQueue {
  private readonly items = new Map<string, QueuedWatchBlob>();

  public get(blobKey: string): QueuedWatchBlob | undefined {
    return this.items.get(blobKey);
  }

  public set(blobKey: string, entry: QueuedWatchBlob): void {
    this.items.set(blobKey, entry);
  }

  public delete(blobKey: string): void {
    this.items.delete(blobKey);
  }

  public has(blobKey: string): boolean {
    return this.items.has(blobKey);
  }

  public size(): number {
    return this.items.size;
  }
}

interface StoredBlobRecord {
  bytes: Uint8Array;
  contentType: string;
}

export interface IndexedDbBlobQueueOptions {
  dbName?: string;
  factory?: IDBFactory;
}

async function toBytes(blob: Blob | Uint8Array): Promise<Uint8Array> {
  if (blob instanceof Uint8Array) {
    const copy = new Uint8Array(blob.byteLength);
    copy.set(blob);
    return copy;
  }
  const buffer = await blob.arrayBuffer();
  return new Uint8Array(buffer);
}

function hydrateQueuedBlob(raw: unknown): QueuedWatchBlob | undefined {
  if (!raw || typeof raw !== "object") {
    return undefined;
  }
  const record = raw as { bytes?: unknown; contentType?: unknown; blob?: unknown };
  const contentType =
    typeof record.contentType === "string" && record.contentType.length > 0
      ? record.contentType
      : "audio/webm";

  if (record.bytes instanceof Uint8Array) {
    const blob =
      typeof Blob === "function"
        ? new Blob([new Uint8Array(record.bytes)], { type: contentType })
        : record.bytes;
    return { blob, contentType };
  }

  if (record.bytes instanceof ArrayBuffer) {
    const bytes = new Uint8Array(record.bytes);
    const blob =
      typeof Blob === "function"
        ? new Blob([bytes], { type: contentType })
        : bytes;
    return { blob, contentType };
  }

  if (record.blob instanceof Uint8Array || (typeof Blob === "function" && record.blob instanceof Blob)) {
    return { blob: record.blob, contentType };
  }

  return undefined;
}

function openBlobDb(factory: IDBFactory, dbName: string): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = factory.open(dbName, BLOB_DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(BLOB_STORE_NAME)) {
        db.createObjectStore(BLOB_STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Failed to open IndexedDB."));
  });
}

export class IndexedDbWatchBlobQueue implements WatchBlobQueue {
  private readonly dbName: string;
  private readonly factory: IDBFactory | undefined;
  private readonly fallback = new MemoryWatchBlobQueue();

  constructor(options: IndexedDbBlobQueueOptions = {}) {
    this.dbName = options.dbName ?? `${DEFAULT_BLOB_DB_PREFIX}-default`;
    this.factory = options.factory ?? (typeof globalThis.indexedDB !== "undefined" ? globalThis.indexedDB : undefined);
  }

  public async get(blobKey: string): Promise<QueuedWatchBlob | undefined> {
    const memHit = this.fallback.get(blobKey);
    if (memHit) {
      return memHit;
    }
    if (!this.factory) {
      return undefined;
    }

    try {
      const db = await openBlobDb(this.factory, this.dbName);
      try {
        const raw = await new Promise<unknown>((resolve, reject) => {
          const tx = db.transaction(BLOB_STORE_NAME, "readonly");
          const req = tx.objectStore(BLOB_STORE_NAME).get(blobKey);
          req.onsuccess = () => resolve(req.result);
          req.onerror = () => reject(req.error ?? new Error("IndexedDB get failed."));
        });
        return hydrateQueuedBlob(raw);
      } finally {
        db.close();
      }
    } catch {
      return undefined;
    }
  }

  public async set(blobKey: string, entry: QueuedWatchBlob): Promise<void> {
    const bytes = await toBytes(entry.blob);
    const record: StoredBlobRecord = { bytes, contentType: entry.contentType };

    if (!this.factory) {
      this.fallback.set(blobKey, entry);
      return;
    }

    try {
      const db = await openBlobDb(this.factory, this.dbName);
      try {
        await new Promise<void>((resolve, reject) => {
          const tx = db.transaction(BLOB_STORE_NAME, "readwrite");
          tx.objectStore(BLOB_STORE_NAME).put(record, blobKey);
          tx.oncomplete = () => resolve();
          tx.onerror = tx.onabort = () =>
            reject(tx.error ?? new Error("IndexedDB put failed."));
        });
        this.fallback.delete(blobKey);
      } finally {
        db.close();
      }
    } catch {
      this.fallback.set(blobKey, entry);
    }
  }

  public async delete(blobKey: string): Promise<void> {
    this.fallback.delete(blobKey);
    if (!this.factory) {
      return;
    }

    try {
      const db = await openBlobDb(this.factory, this.dbName);
      try {
        await new Promise<void>((resolve, reject) => {
          const tx = db.transaction(BLOB_STORE_NAME, "readwrite");
          tx.objectStore(BLOB_STORE_NAME).delete(blobKey);
          tx.oncomplete = () => resolve();
          tx.onerror = tx.onabort = () =>
            reject(tx.error ?? new Error("IndexedDB delete failed."));
        });
      } finally {
        db.close();
      }
    } catch {
      // Fail-soft: fallback already cleared.
    }
  }
}

export function resolveDefaultBlobQueue(
  nodeId = "default",
  factory: IDBFactory | undefined = typeof globalThis.indexedDB !== "undefined"
    ? globalThis.indexedDB
    : undefined,
): WatchBlobQueue {
  if (factory) {
    return new IndexedDbWatchBlobQueue({
      dbName: `${DEFAULT_BLOB_DB_PREFIX}-${nodeId}`,
      factory,
    });
  }
  return new MemoryWatchBlobQueue();
}
