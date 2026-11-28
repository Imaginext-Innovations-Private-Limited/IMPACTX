/** Tiny DOM helpers (no framework). */
type Kid = Node | string | number | null | undefined | false;
type Attrs = Record<string, unknown>;

export function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Attrs = {},
  ...kids: (Kid | Kid[])[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v as EventListener);
    else if (k === "class") el.className = String(v);
    else if (k === "value") (el as unknown as HTMLInputElement).value = String(v);
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, String(v));
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(typeof kid === "object" ? kid : String(kid));
  }
  return el;
}

/** Labelled form field; returns [wrapper, control]. Label is bound via for/id. */
let uid = 0;
export function field<C extends HTMLElement>(label: string, control: C, hint?: string): HTMLDivElement {
  const id = control.id || `f${++uid}`;
  control.id = id;
  return h("div", { class: "field" }, h("label", { for: id }, label), control, hint ? h("small", {}, hint) : null);
}

export function checkbox(label: string, name: string, checked = false, onchange?: (c: boolean) => void): HTMLLabelElement {
  const input = h("input", { type: "checkbox", name, checked });
  input.checked = checked;
  input.addEventListener("change", () => onchange?.(input.checked));
  return h("label", { class: "check" }, input, h("span", {}, label));
}

export function numberInput(name: string, min: number, max: number, step: number | "any" = 1): HTMLInputElement {
  return h("input", { type: "number", name, min, max, step, inputmode: step === 1 ? "numeric" : "decimal" });
}

export const clear = (el: Element): void => el.replaceChildren();
