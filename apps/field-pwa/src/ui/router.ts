import type { Ctx, Screen } from "./ctx";

/** "#/triage/abc" -> { name: "triage", params: ["abc"] }; empty -> home. */
export function parseRoute(hash: string): { name: string; params: string[] } {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  return { name: parts[0] ?? "home", params: parts.slice(1) };
}

export function startRouter(root: HTMLElement, routes: Record<string, Screen>, ctx: Ctx, onRoute: (n: string) => void) {
  let seq = 0;
  const render = async (scroll = false) => {
    const { name, params } = parseRoute(location.hash);
    const screen = routes[name] ?? routes.home;
    onRoute(name in routes ? name : "home");
    const mine = ++seq;
    try {
      const el = await screen(ctx, params);
      if (mine === seq) root.replaceChildren(el);
    } catch (err) {
      if (mine === seq) {
        const p = document.createElement("p");
        p.className = "error";
        p.setAttribute("role", "alert");
        p.textContent = String(err instanceof Error ? err.message : err);
        root.replaceChildren(p);
      }
    }
    if (scroll) window.scrollTo(0, 0);
  };
  window.addEventListener("hashchange", () => void render(true));
  return render;
}
