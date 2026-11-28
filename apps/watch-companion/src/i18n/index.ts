import { en, type Key } from "./en";
import { hi } from "./hi";
import { kn } from "./kn";
import { ta } from "./ta";

export type Lang = "en" | "hi" | "kn" | "ta";
export type { Key };

export const SUPPORTED_LANGS: readonly Lang[] = ["en", "hi", "kn", "ta"] as const;
export const TABLES: Record<Lang, Record<Key, string>> = { en, hi, kn, ta };

export const LANG_STORAGE_KEY = "aarogya.lang";
const LEGACY_LANG_STORAGE_KEY = "aarogya.watch.lang";

interface AarogyaNativeBridgeLike {
  setLanguage?: (lang: string) => void;
}

export function isValidLang(value: unknown): value is Lang {
  return value === "en" || value === "hi" || value === "kn" || value === "ta";
}

function readQueryLang(): Lang | null {
  try {
    if (typeof window !== "undefined" && typeof window.location?.search === "string") {
      const param = new URLSearchParams(window.location.search).get("lang");
      if (isValidLang(param)) {
        return param;
      }
    }
  } catch {
    // Ignore URL parsing errors in non-browser environments.
  }
  return null;
}

function readStoredLang(): Lang {
  const fromQuery = readQueryLang();
  if (fromQuery) {
    return fromQuery;
  }
  try {
    if (typeof localStorage !== "undefined") {
      const primary = localStorage.getItem(LANG_STORAGE_KEY);
      if (isValidLang(primary)) {
        return primary;
      }
      const legacy = localStorage.getItem(LEGACY_LANG_STORAGE_KEY);
      if (isValidLang(legacy)) {
        return legacy;
      }
    }
  } catch {
    // Ignore storage access errors in restricted contexts.
  }
  return "en";
}

let currentLang: Lang = readStoredLang();

if (typeof document !== "undefined") {
  document.documentElement.lang = currentLang;
}

export function getLang(): Lang {
  return currentLang;
}

export interface SetLangOptions {
  notifyBridge?: boolean;
}

export function setLang(lang: Lang, options: SetLangOptions = {}): Lang {
  const safeLang: Lang = isValidLang(lang) ? lang : "en";
  currentLang = safeLang;
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(LANG_STORAGE_KEY, safeLang);
    }
  } catch {
    // Ignore storage access errors in restricted contexts.
  }
  if (typeof document !== "undefined") {
    document.documentElement.lang = safeLang;
  }
  if (options.notifyBridge !== false && typeof window !== "undefined") {
    const bridge = (window as unknown as { AarogyaNativeBridge?: AarogyaNativeBridgeLike })
      .AarogyaNativeBridge;
    try {
      bridge?.setLanguage?.(safeLang);
    } catch {
      // Fail-soft if native bridge throws.
    }
  }
  return currentLang;
}

export function nextLang(lang: Lang): Lang {
  if (lang === "en") return "hi";
  if (lang === "hi") return "kn";
  if (lang === "kn") return "ta";
  return "en";
}

export function toggleLang(): Lang {
  return setLang(nextLang(currentLang));
}

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));
}

export function t(key: Key, vars?: Record<string, string | number>, langOverride?: Lang): string {
  const active = langOverride ?? currentLang;
  const raw = TABLES[active][key] ?? en[key];
  return interpolate(raw, vars);
}

export function tx(key: string, fallback: string, vars?: Record<string, string | number>): string {
  const table = TABLES[currentLang] as Record<string, string>;
  const enTable = en as Record<string, string>;
  return interpolate(table[key] ?? enTable[key] ?? fallback, vars);
}
