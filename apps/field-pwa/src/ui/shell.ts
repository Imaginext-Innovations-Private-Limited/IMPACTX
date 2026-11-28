import { getLang, LANG_STORAGE_KEY, parseLang, setLang, t, type Lang } from "../i18n";
import { h } from "./dom";

export interface Shell {
  root: HTMLElement;
  view: HTMLElement;
  setRoute(name: string): void;
  refreshNet(): void;
  showUpdate(onApply: () => void): void;
}

const LANG_OPTIONS: ReadonlyArray<{ code: Lang; label: string }> = [
  { code: "en", label: "EN" },
  { code: "hi", label: "हिन्दी" },
  { code: "kn", label: "ಕನ್ನಡ" },
  { code: "ta", label: "தமிழ்" },
];

/** Build the persistent chrome (header, connectivity badge, 3-language switcher, home link). */
export function buildShell(app: HTMLElement, onLang: () => void): Shell {
  let route = "home";
  let updateApply: (() => void) | null = null;
  const view = h("main", { id: "view", tabindex: "-1" });
  const banner = h("div", { class: "update", role: "status", hidden: true });
  const badge = h("span", { class: "badge", role: "status", "aria-live": "polite" });
  const homeLink = h("a", { class: "homelink", href: "#/" });
  const title = h("strong", { class: "apptitle" });
  const sub = h("small", {});

  const applyLanguage = (next: Lang, opts?: { persist?: boolean; notifyNative?: boolean }) => {
    const changed = next !== getLang();
    setLang(next, opts);
    labels();
    if (changed) onLang();
  };

  const langBtns = LANG_OPTIONS.map(({ code, label }) =>
    h(
      "button",
      {
        type: "button",
        class: "lang-btn",
        lang: code,
        "data-lang": code,
        onclick: () => applyLanguage(code),
      },
      label,
    ),
  );
  const langGroup = h("div", { class: "lang-group", role: "group" }, langBtns);

  const refreshNet = () => {
    const on = navigator.onLine;
    badge.className = `badge ${on ? "on" : "off"}`;
    badge.textContent = `${on ? "● " : "✈ "}${t(on ? "net.online" : "net.offline")}`;
  };

  const renderUpdateBanner = () => {
    if (!updateApply) return;
    banner.hidden = false;
    banner.replaceChildren(
      h("span", {}, t("update.ready")),
      h("button", { type: "button", onclick: updateApply }, t("update.btn")),
    );
  };

  const labels = () => {
    const cur = getLang();
    document.documentElement.lang = cur;
    document.title = t("app.name");
    title.textContent = t("app.name");
    sub.textContent = t("app.subtitle");
    langGroup.setAttribute("aria-label", t("lang.label"));
    for (const btn of langBtns) {
      const active = btn.getAttribute("data-lang") === cur;
      btn.setAttribute("aria-pressed", active ? "true" : "false");
      btn.className = active ? "lang-btn active" : "lang-btn";
    }
    homeLink.textContent = `← ${t("nav.back")}`;
    homeLink.hidden = route === "home";
    refreshNet();
    renderUpdateBanner();
  };

  const header = h("header", {}, h("div", { class: "brand" }, title, sub), h("div", { class: "tools" }, badge, langGroup));
  app.replaceChildren(header, banner, homeLink, view);
  labels();

  window.addEventListener("online", refreshNet);
  window.addEventListener("offline", refreshNet);

  // Live cross-frame sync from /showcase or Android MainActivity without reloading.
  window.addEventListener("message", (ev: MessageEvent) => {
    const data = ev.data as { type?: unknown; lang?: unknown } | null;
    if (!data || typeof data !== "object" || data.type !== "aarogya:setLang") return;
    const next = parseLang(data.lang);
    if (next) applyLanguage(next);
  });

  // Live cross-tab / same-origin sync via localStorage key `aarogya.lang`.
  window.addEventListener("storage", (ev: StorageEvent) => {
    if (ev.key !== LANG_STORAGE_KEY) return;
    const next = parseLang(ev.newValue);
    if (next) applyLanguage(next, { persist: false });
  });

  return {
    root: app,
    view,
    setRoute(n) {
      route = n;
      labels();
    },
    refreshNet: labels,
    showUpdate(onApply) {
      updateApply = onApply;
      renderUpdateBanner();
    },
  };
}
