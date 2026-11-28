import { t } from "../../i18n";
import { clear, field, h } from "../dom";
import type { Ctx } from "../ctx";
import { STATUS_ORDER, buildVaccinationPayload, groupByStatus, scheduleFor } from "../vacc_logic";

const todayIso = () => {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};

export async function vaccines(ctx: Ctx, params: string[]): Promise<HTMLElement> {
  const kids = (await ctx.store.listPatients()).filter((p) => p.date_of_birth);
  const sel = h(
    "select",
    { name: "child" },
    h("option", { value: "" }, t("vac.pick")),
    kids.map((p) => h("option", { value: p.patient_id, selected: p.patient_id === params[0] }, `${p.full_name} (${p.date_of_birth})`)),
  );
  const out = h("div");
  const msg = h("div", { role: "status", "aria-live": "polite" });

  async function draw() {
    clear(out);
    const p = kids.find((k) => k.patient_id === sel.value);
    if (!p || !p.date_of_birth) return;
    const dob = p.date_of_birth;
    const asOf = todayIso();
    let items;
    try {
      items = scheduleFor(dob, await ctx.store.getAllEvents(), p.patient_id, asOf);
    } catch (e) {
      out.append(h("p", { class: "error", role: "alert" }, e instanceof Error ? e.message : String(e)));
      return;
    }
    const g = groupByStatus(items);
    for (const s of STATUS_ORDER) {
      if (!g[s].length) continue;
      out.append(
        h(
          "section",
          { class: `vgroup v-${s}` },
          h("h2", {}, `${t(`vst.${s}` as const)} (${g[s].length})`),
          h(
            "ul",
            { class: "list" },
            g[s].map((i) => {
              const date = h("input", { type: "date", value: asOf, min: dob, max: asOf, "aria-label": t("vac.date") });
              return h(
                "li",
                {},
                h("strong", {}, `${i.vaccine_name} — ${i.dose_label}`),
                h("div", { class: "muted" }, i.status === "COMPLETED" ? `${t("vac.given")}: ${i.administered_date}` : `${t("vac.due")}: ${i.due_date}`),
                i.status === "COMPLETED"
                  ? null
                  : (() => {
                      const logBtn = h("button", { type: "button", onclick: () => log(i.vaccine_code, date.value, logBtn) }, t("vac.log"));
                      return h("div", { class: "row" }, date, logBtn);
                    })(),
              );
            }),
          ),
        ),
      );
    }
    function log(code: string, date: string, logBtn: HTMLButtonElement) {
      if (logBtn.disabled) return;
      clear(msg);
      const payload = buildVaccinationPayload(dob, code, date, todayIso());
      if (!payload) {
        msg.append(h("p", { class: "error", role: "alert" }, t("vac.badDate")));
        return;
      }
      logBtn.disabled = true;
      ctx.engine
        .enqueue({ event_type: "VACCINATION_LOGGED", patient_id: p!.patient_id, payload: { ...payload } })
        .then(() => {
          ctx.syncSoon();
          msg.append(h("p", { class: "ok" }, t("vac.saved")));
          return draw(); // recompute from the event log
        })
        .catch((e) => msg.append(h("p", { class: "error" }, String(e))))
        .finally(() => {
          logBtn.disabled = false;
        });
    }
  }
  sel.addEventListener("change", () => {
    clear(msg);
    void draw();
  });
  void draw();
  return h("section", {}, h("h1", {}, t("vac.title")), kids.length ? field(t("vac.child"), sel) : h("p", { class: "muted" }, t("vac.none")), msg, out);
}
