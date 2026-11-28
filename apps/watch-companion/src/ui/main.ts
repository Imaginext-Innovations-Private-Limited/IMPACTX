/**
 * Browser entrypoint for the Tier-0 360x360 Dual-Mode Watch Companion PWA.
 * Bundled via `esbuild` into `dist/watch.js` and loaded by `index.html`.
 */

import { isValidLang, LANG_STORAGE_KEY } from "../i18n/index";
import { resolveDefaultHubUrl, WatchSyncClient } from "../sync/index";
import { WatchKernel } from "../watch_kernel";
import { mountWatchUi } from "./render";
import { WatchUiController } from "./state";

function bootstrap(): void {
  const root = document.getElementById("watch-app");
  if (!root) {
    return;
  }

  if (typeof window !== "undefined" && typeof document !== "undefined") {
    const params = new URLSearchParams(window.location.search);
    if (params.get("embed") === "1") {
      document.body.classList.add("embed-mode");
    }
    const queryLang = params.get("lang");
    if (isValidLang(queryLang)) {
      document.documentElement.lang = queryLang;
    }
  }

  const loc = typeof window !== "undefined" ? window.location : null;
  const kernel = new WatchKernel("watch-node-01", "CHW_COMPANION");
  const syncClient = new WatchSyncClient(
    kernel.getStore(),
    resolveDefaultHubUrl(loc),
  );
  const controller = new WatchUiController({ kernel, syncClient, location: loc });

  mountWatchUi(root, controller);

  if (typeof window !== "undefined") {
    window.addEventListener("aarogya:hub-url-changed", () => {
      controller.refreshHubUrlFromStorage();
      if (controller.getHubUrl().trim().length > 0 && !controller.getIsSyncing()) {
        void controller.syncNow();
      }
    });

    window.addEventListener("message", (event: MessageEvent) => {
      const data = event.data;
      if (
        data &&
        typeof data === "object" &&
        (data as { type?: unknown }).type === "aarogya:setLang" &&
        isValidLang((data as { lang?: unknown }).lang)
      ) {
        const next = (data as { lang: "en" | "hi" | "kn" | "ta" }).lang;
        if (controller.getLanguage() !== next) {
          controller.setLanguage(next, { notifyBridge: false });
        }
      }
    });

    window.addEventListener("storage", (event: StorageEvent) => {
      if (event.key === LANG_STORAGE_KEY && isValidLang(event.newValue)) {
        if (controller.getLanguage() !== event.newValue) {
          controller.setLanguage(event.newValue, { notifyBridge: false });
        }
      }
    });
  }

  if (typeof navigator !== "undefined" && "serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js").catch(() => {
      // Fail-soft if SW registration is blocked (e.g., file:// or private browsing).
    });
  }
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
  } else {
    bootstrap();
  }
}
