import { compareHlc, receive as hlcReceive, tick as hlcTick } from "./hlc";
import type { ActionCard, CrdtEvent, FieldStore, HlcTimestamp, PatientRecord } from "./types";

const STORES = ["events", "outbox", "meta", "patients", "actionCards"] as const;
type StoreName = (typeof STORES)[number];

const req = <T>(r: IDBRequest<T>): Promise<T> =>
  new Promise((res, rej) => {
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });

const done = (tx: IDBTransaction): Promise<void> =>
  new Promise((res, rej) => {
    tx.oncomplete = () => res();
    tx.onerror = tx.onabort = () => rej(tx.error);
  });

/** Open (or create) the durable store. `dbName` defaults to one DB per node. */
export async function openStore(
  nodeId: string,
  dbName = `aarogya-field-${nodeId}`,
  factory: IDBFactory = indexedDB,
): Promise<FieldStore> {
  const open = factory.open(dbName, 1);
  open.onupgradeneeded = () => {
    const db = open.result;
    db.createObjectStore("events", { keyPath: "event_id" });
    db.createObjectStore("outbox", { keyPath: "event_id" });
    db.createObjectStore("meta"); // keys: "hlc", "cursor"
    db.createObjectStore("patients", { keyPath: "patient_id" });
    db.createObjectStore("actionCards", { keyPath: "card_id" });
  };
  const db = await req(open);

  const all = <T>(s: StoreName) => req(db.transaction(s).objectStore(s).getAll() as IDBRequest<T[]>);
  const put = async (s: StoreName, v: unknown, key?: string) => {
    const tx = db.transaction(s, "readwrite");
    tx.objectStore(s).put(v, key);
    await done(tx);
  };
  const loadHlc = async (): Promise<HlcTimestamp> =>
    (await req(db.transaction("meta").objectStore("meta").get("hlc"))) ?? { wall_ms: 0, logical: 0, node_id: nodeId };
  // Serialize clock updates so concurrent ticks never collide.
  let chain: Promise<unknown> = Promise.resolve();
  const advance = (fn: (h: HlcTimestamp) => HlcTimestamp): Promise<HlcTimestamp> => {
    const p = chain.then(async () => {
      const next = fn(await loadHlc());
      await put("meta", next, "hlc");
      return next;
    });
    chain = p.catch(() => undefined);
    return p;
  };
  const byHlc = (a: CrdtEvent, b: CrdtEvent) => compareHlc(a.hlc, b.hlc);

  return {
    nodeId,
    tick: (nowMs) => advance((h) => hlcTick(h, nowMs)),
    receive: (remote, nowMs) => advance((h) => hlcReceive(h, remote, nowMs)),
    async appendEvent(event, opts) {
      const tx = db.transaction(["events", "outbox"], "readwrite");
      const events = tx.objectStore("events");
      const exists = (await req(events.getKey(event.event_id))) !== undefined;
      if (!exists) {
        events.add(event);
        if (opts?.outbox ?? true) tx.objectStore("outbox").put(event);
      }
      await done(tx);
      return !exists;
    },
    async getAllEvents() {
      return (await all<CrdtEvent>("events")).sort(byHlc);
    },
    getEvent: (id) => req(db.transaction("events").objectStore("events").get(id)),
    async getPendingEvents() {
      return (await all<CrdtEvent>("outbox")).sort(byHlc);
    },
    async markAcked(ids) {
      const tx = db.transaction("outbox", "readwrite");
      ids.forEach((id) => tx.objectStore("outbox").delete(id));
      await done(tx);
    },
    async getCursor() {
      return (await req(db.transaction("meta").objectStore("meta").get("cursor"))) ?? null;
    },
    setCursor: (c) => put("meta", c, "cursor"),
    putPatient: (p: PatientRecord) => put("patients", p),
    getPatient: (id) => req(db.transaction("patients").objectStore("patients").get(id)),
    listPatients: () => all<PatientRecord>("patients"),
    putActionCard: (c: ActionCard) => put("actionCards", c),
    listActionCards: () => all<ActionCard>("actionCards"),
    close: () => db.close(),
  };
}
