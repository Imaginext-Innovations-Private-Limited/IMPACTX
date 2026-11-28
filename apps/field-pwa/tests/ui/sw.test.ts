import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(__dirname, "../..");
const src = readFileSync(resolve(root, "sw.js"), "utf8");

function load(origin = "http://127.0.0.1:5173", scope = "/") {
  const listeners: Record<string, (e: any) => void> = {};
  const self: any = { location: { origin }, registration: { scope: origin + scope }, addEventListener: (t: string, f: (e: any) => void) => (listeners[t] = f), skipWaiting() {}, clients: { claim: async () => {} } };
  const calls: string[] = [];
  const caches = { open: async () => ({ addAll: async () => {}, put: async () => {} }), match: async () => undefined, keys: async () => [], delete: async () => true };
  const fn = new Function("self", "caches", "fetch", "importScripts", `${src}\nreturn { shouldHandle, SHELL_ASSETS, CACHE_NAME };`);
  const api = fn(self, caches, async (r: Request) => { calls.push(r.url); return new Response("x"); }, () => { self.SW_BUILD = "abc123"; });
  return { listeners, api, calls };
}
const req = (url: string, method = "GET", mode = "cors") => ({ url, method, mode }) as unknown as Request;

describe("service worker rules", () => {
  const { api, listeners } = load();
  it("handles same-origin GET shell assets and navigations", () => {
    expect(api.shouldHandle(req("http://127.0.0.1:5173/dist/app.js"), "http://127.0.0.1:5173")).toBe(true);
    expect(api.shouldHandle(req("http://127.0.0.1:5173/"), "http://127.0.0.1:5173")).toBe(true);
  });
  it("skips /api/ and /ws/ paths, cross-origin hub requests and non-GET", () => {
    const o = "http://127.0.0.1:5173";
    expect(api.shouldHandle(req(`${o}/api/v1/sync`), o)).toBe(false);
    expect(api.shouldHandle(req(`${o}/ws/mesh`), o)).toBe(false);
    expect(api.shouldHandle(req("http://127.0.0.1:8000/api/v1/sync"), o)).toBe(false);
    expect(api.shouldHandle(req("http://127.0.0.1:8000/anything"), o)).toBe(false);
    expect(api.shouldHandle(req(`${o}/x`, "POST"), o)).toBe(false);
  });
  it("fetch listener does not respond to skipped requests", () => {
    let responded = false;
    for (const url of ["http://127.0.0.1:5173/api/v1/sync", "http://127.0.0.1:8000/api/v1/sync", "http://127.0.0.1:5173/ws/mesh"]) {
      listeners.fetch({ request: req(url), respondWith: () => (responded = true) });
    }
    expect(responded).toBe(false);
    listeners.fetch({ request: req("http://127.0.0.1:5173/dist/app.js"), respondWith: () => (responded = true) });
    expect(responded).toBe(true);
  });
  it("uses a bumped cache version and precaches the full shell with files that exist after build", () => {
    expect(api.CACHE_NAME).not.toBe("aarogya-field-pwa-v1");
    expect(api.CACHE_NAME).toContain("abc123"); // build hash is part of the cache name
    for (const a of ["./", "./index.html", "./manifest.webmanifest", "./dist/app.js", "./dist/app.css"]) expect(api.SHELL_ASSETS).toContain(a);
    for (const a of api.SHELL_ASSETS as string[]) {
      if (a === "./" || a.startsWith("./dist/")) continue; // dist is produced by `npm run build`
      expect(existsSync(resolve(root, a)), a).toBe(true);
    }
  });
});

describe("service worker scope", () => {
  const o = "http://127.0.0.1:5173";
  const { api } = load();
  const h = (url: string, scope: string, method = "GET") => api.shouldHandle(req(url, method), o, scope);
  it("scope /phone/ handles in-scope assets and navigations only", () => {
    expect(h(`${o}/phone/dist/app.js`, "/phone/")).toBe(true);
    expect(h(`${o}/phone/`, "/phone/")).toBe(true);
    expect(h(`${o}/health`, "/phone/")).toBe(false);
    expect(h(`${o}/showcase`, "/phone/")).toBe(false);
    expect(h(`${o}/phone-other/x`, "/phone/")).toBe(false);
    expect(h(`${o}/phone/api/v1/sync`, "/phone/")).toBe(false);
    expect(h(`${o}/phone/ws/mesh`, "/phone/")).toBe(false);
    expect(h(`${o}/api/v1/sync`, "/phone/")).toBe(false);
    expect(h(`${o}/ws/mesh`, "/phone/")).toBe(false);
    expect(h(`${o}/phone/x`, "/phone/", "POST")).toBe(false);
    expect(api.shouldHandle(req("http://127.0.0.1:8000/phone/x"), o, "/phone/")).toBe(false);
  });
  it("scope / behaves as before except /api and /ws", () => {
    expect(h(`${o}/dist/app.js`, "/")).toBe(true);
    expect(h(`${o}/health`, "/")).toBe(true);
    expect(h(`${o}/api/x`, "/")).toBe(false);
    expect(h(`${o}/ws/x`, "/")).toBe(false);
  });
  it("nested scope /apps/field-pwa/", () => {
    expect(h(`${o}/apps/field-pwa/dist/app.js`, "/apps/field-pwa/")).toBe(true);
    expect(h(`${o}/other.js`, "/apps/field-pwa/")).toBe(false);
  });
  it("fetch listener uses registration scope", () => {
    const { listeners } = load(o, "/phone/");
    let responded = false;
    listeners.fetch({ request: req(`${o}/health`), respondWith: () => (responded = true) });
    expect(responded).toBe(false);
    listeners.fetch({ request: req(`${o}/phone/dist/app.js`), respondWith: () => (responded = true) });
    expect(responded).toBe(true);
  });
});

describe("manifest and html", () => {
  const manifest = JSON.parse(readFileSync(resolve(root, "manifest.webmanifest"), "utf8"));
  it("is standalone with icons that exist", () => {
    expect(manifest.display).toBe("standalone");
    expect(manifest.theme_color).toBe("#0d9488");
    for (const i of manifest.icons) expect(existsSync(resolve(root, i.src)), i.src).toBe(true);
  });
  it("index.html loads the bundle and has a viewport", () => {
    const html = readFileSync(resolve(root, "index.html"), "utf8");
    expect(html).toContain("./dist/app.js");
    expect(html).toContain("width=device-width");
  });
});
