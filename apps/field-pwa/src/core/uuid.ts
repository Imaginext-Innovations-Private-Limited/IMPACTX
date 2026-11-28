/**
 * RFC 4122 v4 UUID that also works in non-secure contexts (plain http on a LAN
 * address), where `crypto.randomUUID` is undefined but `getRandomValues` exists.
 * Ids are CRDT event ids, so there is deliberately no Math.random fallback.
 */
export function uuid(): string {
  const c = (globalThis as { crypto?: Partial<Crypto> }).crypto;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  if (!c || typeof c.getRandomValues !== "function") {
    throw new Error("uuid: no Web Crypto (crypto.getRandomValues) available; cannot generate a collision-safe id");
  }
  const b = c.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const hex = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
