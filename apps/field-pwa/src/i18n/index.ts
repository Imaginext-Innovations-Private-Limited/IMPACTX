import { lsGet, lsSet } from "../ui/settings";
import { en, type Key } from "./en";
import { hi } from "./hi";
import { kn } from "./kn";
import { ta } from "./ta";

export type Lang = "en" | "hi" | "kn" | "ta";
export type { Key };
export const SUPPORTED_LANGS: readonly Lang[] = ["en", "hi", "kn", "ta"] as const;
export const LANG_STORAGE_KEY = "aarogya.lang";
export const TABLES: Record<Lang, Record<Key, string>> = { en, hi, kn, ta };

/** Parse an untrusted value into a supported Lang, or null if invalid. */
export function parseLang(raw: unknown): Lang | null {
  if (typeof raw !== "string") return null;
  const v = raw.trim().toLowerCase();
  if (v === "en" || v === "hi" || v === "kn" || v === "ta") return v;
  return null;
}

/** Read `?lang=` from a query string (defaults to current `location.search`). */
export function queryLang(search?: string): Lang | null {
  const s = search ?? (typeof location !== "undefined" ? location.search : "");
  if (!s) return null;
  try {
    return parseLang(new URLSearchParams(s).get("lang"));
  } catch {
    return null;
  }
}

/** Resolve initial language: `?lang=` > `localStorage` > `"en"`. */
export function resolveInitialLang(search?: string): Lang {
  return queryLang(search) ?? parseLang(lsGet(LANG_STORAGE_KEY)) ?? "en";
}

let lang: Lang = resolveInitialLang();
if (typeof document !== "undefined") document.documentElement.lang = lang;

export const getLang = (): Lang => lang;

/** Notify the Android native shell if present; never throws. */
export function notifyNativeLang(l: Lang, g: unknown = globalThis): void {
  try {
    (g as { AarogyaNativeBridge?: { setLanguage?: (lang: string) => void } }).AarogyaNativeBridge?.setLanguage?.(l);
  } catch {
    /* ignore */
  }
}

export function setLang(l: Lang, opts: { persist?: boolean; notifyNative?: boolean } = {}): void {
  lang = l;
  if (opts.persist !== false) lsSet(LANG_STORAGE_KEY, l);
  if (typeof document !== "undefined") document.documentElement.lang = l;
  if (opts.notifyNative !== false) notifyNativeLang(l);
}

const fill = (s: string, vars?: Record<string, string | number>) =>
  vars ? s.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`)) : s;

/** Translate a known key (compile-time checked). */
export function t(key: Key, vars?: Record<string, string | number>): string {
  return fill(TABLES[lang][key] ?? en[key], vars);
}

/** Translate a data-driven key (e.g. from rule-table flags); falls back to `fallback`. */
export function tx(key: string, fallback: string): string {
  const tbl = TABLES[lang] as Record<string, string>;
  return tbl[key] ?? (en as Record<string, string>)[key] ?? fallback;
}
