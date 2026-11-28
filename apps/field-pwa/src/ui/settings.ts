import { uuid } from "../core/uuid";
/** Persisted UI settings. localStorage may be unavailable: every access is guarded. */
export const DEFAULT_HUB_URL = "http://127.0.0.1:8000";

export function lsGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
export function lsSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}

function lsRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

/** The parts of `location` the hub-origin rule needs (injected so the rule stays pure). */
export type LocLike = { protocol: string; host: string; hostname: string; pathname: string };
export const HUB_MOUNT = "/phone";

/** Origin of the hub when this page is served from its /phone/ mount, else null. */
export function hubOriginFrom(loc: LocLike | null | undefined): string | null {
  if (typeof globalThis !== "undefined" && "AarogyaNativeBridge" in globalThis) return null;
  if (!loc || (loc.protocol !== "http:" && loc.protocol !== "https:")) return null;
  const p = loc.pathname;
  if (p !== HUB_MOUNT && !p.startsWith(`${HUB_MOUNT}/`)) return null;
  return `${loc.protocol}//${loc.host}`;
}

export function isLoopbackHost(hostname: string): boolean {
  const h = hostname.replace(/^\[|\]$/g, "").toLowerCase();
  return h === "localhost" || h === "::1" || /^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(h);
}

function hostnameOf(url: string): string | null {
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

/** Normalize a user-entered Hub URL: trim spaces, strip trailing slashes, default missing scheme to http://. */
export function normalizeHubUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (/^[a-zA-Z][a-zA-Z\d+\-.]*:\/\/$/i.test(trimmed)) return trimmed;
  const s = trimmed.replace(/\/+$/, "");
  if (/^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//i.test(s) || /^(javascript|data|vbscript|file):/i.test(s)) {
    return s;
  }
  return `http://${s}`;
}

/** Saved override wins, except a loopback value saved while served from a non-loopback hub origin (stale). */
export function resolveHubUrl(saved: string | null, loc: LocLike | null | undefined): string {
  const auto = hubOriginFrom(loc);
  const s = normalizeHubUrl(saved ?? "");
  if (s && isValidHubUrl(s)) {
    const sh = hostnameOf(s);
    const stale = auto !== null && loc != null && !isLoopbackHost(loc.hostname) && sh !== null && isLoopbackHost(sh);
    if (!stale) return s;
  }
  return auto ?? DEFAULT_HUB_URL;
}

const curLoc = (): LocLike | null => (typeof location === "undefined" ? null : location);
/** Page-origin hub URL when served from the hub, else null. */
export const getAutoHubOrigin = (): string | null => hubOriginFrom(curLoc());
export const getHubUrl = (): string => resolveHubUrl(lsGet("aarogya.hubUrl"), curLoc());
export const clearHubUrl = (): void => lsRemove("aarogya.hubUrl");
export const setHubUrl = (url: string): void => {
  const norm = normalizeHubUrl(url);
  if (norm) lsSet("aarogya.hubUrl", norm);
  else lsRemove("aarogya.hubUrl");
};

/** Stable per-device node id. */
export function getNodeId(): string {
  let id = lsGet("aarogya.nodeId");
  if (!id) {
    id = `phone-${uuid().slice(0, 8)}`;
    lsSet("aarogya.nodeId", id);
  }
  return id;
}

export function getLastSync(): { at: number; ok: boolean; detail: string } | null {
  try {
    return JSON.parse(lsGet("aarogya.lastSync") ?? "null");
  } catch {
    return null;
  }
}
export const setLastSync = (v: { at: number; ok: boolean; detail: string }): void =>
  lsSet("aarogya.lastSync", JSON.stringify(v));

/** Valid http(s) URL check for the hub setting (accepts bare host:port by normalizing to http://). */
export function isValidHubUrl(s: string): boolean {
  const norm = normalizeHubUrl(s);
  if (!norm || /\s/.test(norm)) return false;
  try {
    const u = new URL(norm);
    if (u.protocol !== "http:" && u.protocol !== "https:") return false;
    const h = u.hostname.toLowerCase();
    return h === "localhost" || h.includes(".") || h.includes(":");
  } catch {
    return false;
  }
}
