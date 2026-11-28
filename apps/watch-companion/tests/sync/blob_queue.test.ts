import { IDBFactory } from "fake-indexeddb";
import { describe, expect, it } from "vitest";
import {
  CONTRACT_SCHEMA_VERSION,
  type SyncEnvelope,
} from "../../../../packages/contracts/ts/index";
import { MemoryStorage, WatchStore } from "../../src/core";
import {
  IndexedDbWatchBlobQueue,
  MemoryWatchBlobQueue,
  WatchSyncClient,
  resolveDefaultBlobQueue,
} from "../../src/sync";

async function readAllBytes(blob: Blob | Uint8Array): Promise<Uint8Array> {
  if (blob instanceof Uint8Array) return blob;
  return new Uint8Array(await blob.arrayBuffer());
}

describe("IndexedDbWatchBlobQueue (#24)", () => {
  it("persists queued audio blobs across full instance reloads and deletes after sync", async () => {
    const idb = new IDBFactory();
    const audioBytes = new Uint8Array([0x52, 0x49, 0x46, 0x46, 0x01, 0x02, 0x03]);

    const firstQueue = new IndexedDbWatchBlobQueue({
      dbName: "aarogya-watch-blobs-test",
      factory: idb,
    });
    await firstQueue.set("watch-sos-reload-1", {
      blob: new Blob([audioBytes], { type: "audio/webm" }),
      contentType: "audio/webm",
    });

    // Simulate full browser tab reload with a brand-new queue instance
    const reloadedQueue = new IndexedDbWatchBlobQueue({
      dbName: "aarogya-watch-blobs-test",
      factory: idb,
    });
    const restored = await reloadedQueue.get("watch-sos-reload-1");
    expect(restored).toBeDefined();
    expect(restored?.contentType).toBe("audio/webm");
    expect(await readAllBytes(restored!.blob)).toEqual(audioBytes);

    await reloadedQueue.delete("watch-sos-reload-1");
    expect(await reloadedQueue.get("watch-sos-reload-1")).toBeUndefined();
  });

  it("uploads SOS audio blob persisted before reload when WatchSyncClient syncs after reload", async () => {
    const storage = new MemoryStorage();
    const idb = new IDBFactory();
    const audioBytes = new Uint8Array([10, 20, 30, 40, 50]);

    const storeBeforeReload = new WatchStore({ nodeId: "watch-reload", storage });
    const clientBeforeReload = new WatchSyncClient(storeBeforeReload, {
      hubUrl: "http://127.0.0.1:8000",
      blobQueue: resolveDefaultBlobQueue("watch-reload", idb),
      fetchImpl: async () => {
        throw new Error("offline");
      },
    });

    const sosEvent = await clientBeforeReload.enqueueVoiceSos({
      patientId: "p-sos-reload",
      transcriptHint: "आपातकालीन सहायता",
      language: "hi",
      audioBlob: new Blob([audioBytes], { type: "audio/ogg" }),
      audioBlobKey: "watch-sos-persisted-01",
    });

    const offlineResult = await clientBeforeReload.syncNow();
    expect(offlineResult.ok).toBe(false);

    // Simulate full browser tab reload: fresh WatchStore + fresh WatchSyncClient
    const uploadedPayloads: Array<{ key: string; bytes: Uint8Array; contentType: string | null }> = [];
    const mockFetch: typeof fetch = async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.includes("/api/v1/blobs/")) {
        const key = url.split("/").pop() ?? "";
        if (method === "HEAD") {
          return new Response(null, { status: 404 });
        }
        if (method === "PUT") {
          const headers = new Headers(init?.headers);
          const bodyBytes =
            init?.body instanceof Uint8Array
              ? init.body
              : init?.body instanceof Blob
                ? new Uint8Array(await init.body.arrayBuffer())
                : new Uint8Array();
          uploadedPayloads.push({
            key,
            bytes: bodyBytes,
            contentType: headers.get("content-type"),
          });
          return new Response(
            JSON.stringify({
              blob_key: key,
              content_type: headers.get("content-type") ?? "audio/ogg",
              size_bytes: bodyBytes.byteLength,
              sha256: "b".repeat(64),
            }),
            { status: 200 },
          );
        }
      }

      const reply: SyncEnvelope = {
        envelope_id: "env-hub-reload",
        sender_manifest: {
          node_id: "phc-hub",
          tier: "TIER_2_HUB",
          ram_mb: 8192,
          cpu_cores: 4,
          battery_pct: 100,
          has_npu: false,
          installed_models: [],
          watch_mode: null,
        },
        sender_hlc: { wall_ms: Date.now() + 1000, logical: 0, node_id: "phc-hub" },
        since_cursor: null,
        next_cursor: "cursor-reload-1",
        events: [],
        ack_event_ids: [sosEvent.event_id],
        schema_version: CONTRACT_SCHEMA_VERSION,
      };
      return new Response(JSON.stringify(reply), { status: 200 });
    };

    const storeAfterReload = new WatchStore({ nodeId: "watch-reload", storage });
    const queueAfterReload = resolveDefaultBlobQueue("watch-reload", idb);
    const clientAfterReload = new WatchSyncClient(storeAfterReload, {
      hubUrl: "http://127.0.0.1:8000",
      blobQueue: queueAfterReload,
      fetchImpl: mockFetch,
    });

    const syncResult = await clientAfterReload.syncNow();
    expect(syncResult.ok).toBe(true);
    if (syncResult.ok) {
      expect(syncResult.ackedCount).toBe(1);
      expect(syncResult.uploadedBlobKeys).toEqual(["watch-sos-persisted-01"]);
    }
    expect(uploadedPayloads).toHaveLength(1);
    expect(uploadedPayloads[0]?.bytes).toEqual(audioBytes);
    expect(uploadedPayloads[0]?.contentType).toBe("audio/ogg");
    expect(await queueAfterReload.get("watch-sos-persisted-01")).toBeUndefined();
  });

  it("falls back fail-soft when IndexedDB open fails or is unavailable", async () => {
    expect(resolveDefaultBlobQueue("watch-no-idb", undefined)).toBeInstanceOf(
      MemoryWatchBlobQueue,
    );

    const brokenFactory = {
      open: () => {
        throw new Error("IDB blocked in private mode");
      },
    } as unknown as IDBFactory;

    const queue = new IndexedDbWatchBlobQueue({
      dbName: "broken-db",
      factory: brokenFactory,
    });
    const bytes = new Uint8Array([1, 2, 3]);
    await queue.set("watch-sos-fallback", { blob: bytes, contentType: "audio/webm" });

    const hit = await queue.get("watch-sos-fallback");
    expect(hit).toBeDefined();
    expect(await readAllBytes(hit!.blob)).toEqual(bytes);

    await queue.delete("watch-sos-fallback");
    expect(await queue.get("watch-sos-fallback")).toBeUndefined();
  });
});
