import "./app.css";
import { SyncEngine } from "../sync";
import { openStore } from "../core";
import { getHubUrl, getNodeId } from "./settings";
import { startRouter } from "./router";
import { buildShell } from "./shell";
import { runSync, startSyncLoop } from "./app_state";
import type { Ctx, Screen } from "./ctx";
import { home } from "./screens/home";
import { register } from "./screens/register";
import { triage } from "./screens/triage";
import { vaccines } from "./screens/vaccines";
import { checklist } from "./screens/checklist";
import { voice } from "./screens/voice";
import { syncPanel } from "./screens/sync";

async function boot() {
  const app = document.getElementById("app")!;
  const nodeId = getNodeId();
  const store = await openStore(nodeId);
  const engine = new SyncEngine(store, { hubUrl: getHubUrl() });

  let current = "home";
  let render: (scroll?: boolean) => Promise<void> = async () => {};
  let timer: ReturnType<typeof setTimeout> | undefined;
  const debounced = (fn: () => void, ms: number) => {
    clearTimeout(timer);
    timer = setTimeout(fn, ms);
  };
  const shell = buildShell(app, () => void render());

  const ctx: Ctx = {
    store,
    engine,
    nodeId,
    nav: (hash) => (location.hash = hash),
    rerender: () => void render(),
    // Best effort, fire and forget; local save has already completed.
    syncSoon: () => {
      if (navigator.onLine) debounced(() => void runSync(engine), 1500);
    },
  };

  const routes: Record<string, Screen> = {
    home,
    register,
    triage,
    vaccines,
    checklist,
    voice,
    sync: syncPanel,
  };
  const go = startRouter(shell.view, routes, ctx, (n) => {
    current = n;
    shell.setRoute(n);
  });
  render = go;

  // Live refresh of read-only dashboards only (never wipe a form the CHW is filling in).
  // Own timer, so a refresh never cancels a pending syncSoon.
  let liveTimer: ReturnType<typeof setTimeout> | undefined;
  const typing = () => document.activeElement instanceof HTMLInputElement || document.activeElement instanceof HTMLTextAreaElement;
  const refresh = () => {
    clearTimeout(liveTimer);
    liveTimer = setTimeout(() => void go(), 250);
  };
  const liveHome = () => {
    if (current === "home" && !typing()) refresh();
  };
  // Sync panel: only on card changes, never mid-sync (avoids flicker on every status tick).
  const liveSync = () => {
    if (current === "sync" && !typing() && engine.status !== "syncing") refresh();
  };
  engine.events.on("status", liveHome);
  engine.events.on("cards", liveHome);
  engine.events.on("cards", liveSync);
  engine.events.on("enrichment", liveHome);

  await go(true);
  startSyncLoop(engine);
  registerServiceWorker(shell);

  window.addEventListener("aarogya:hub-url-changed", () => {
    engine.hubUrl = getHubUrl();
    if (navigator.onLine) void runSync(engine);
  });
}

function registerServiceWorker(shell: ReturnType<typeof buildShell>) {
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker
    .register("./sw.js")
    .then((reg) => {
      const watch = (w: ServiceWorker | null) =>
        w?.addEventListener("statechange", () => {
          if (w.state === "installed" && navigator.serviceWorker.controller) {
            shell.showUpdate(() => w.postMessage({ type: "SKIP_WAITING" }));
          }
        });
      if (reg.waiting && navigator.serviceWorker.controller) {
        shell.showUpdate(() => reg.waiting?.postMessage({ type: "SKIP_WAITING" }));
      }
      reg.addEventListener("updatefound", () => watch(reg.installing));
    })
    .catch(() => undefined);
  let reloaded = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (reloaded) return;
    reloaded = true;
    location.reload();
  });
}

boot().catch((e) => {
  const el = document.getElementById("app");
  if (el) el.textContent = `Startup error: ${e instanceof Error ? e.message : String(e)}`;
});
