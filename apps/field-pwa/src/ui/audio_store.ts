/** Separate small IndexedDB owned by the UI for voice-note blobs (core store has no blob API). */
const DB = "aarogya-field-audio";
const STORE = "blobs";

const open = (factory: IDBFactory): Promise<IDBDatabase> =>
  new Promise((res, rej) => {
    const r = factory.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(STORE);
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });

export async function putAudio(key: string, blob: Blob, factory: IDBFactory = indexedDB): Promise<void> {
  const db = await open(factory);
  try {
    await new Promise<void>((res, rej) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(blob, key);
      tx.oncomplete = () => res();
      tx.onerror = tx.onabort = () => rej(tx.error);
    });
  } finally {
    db.close();
  }
}

export async function getAudio(key: string, factory: IDBFactory = indexedDB): Promise<Blob | undefined> {
  const db = await open(factory);
  try {
    return await new Promise<Blob | undefined>((res, rej) => {
      const r = db.transaction(STORE).objectStore(STORE).get(key);
      r.onsuccess = () => res(r.result as Blob | undefined);
      r.onerror = () => rej(r.error);
    });
  } finally {
    db.close();
  }
}
