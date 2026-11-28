import { t } from "../../i18n";
import { h } from "../dom";
import type { Ctx } from "../ctx";
import { patientAgeMonths } from "../triage_map";
import { derivePatientStage } from "../stage_tracker";
import { compareHlc } from "../../core/hlc";
import type { CrdtEvent, PatientRecord, TriageSeverity } from "../../../../../packages/contracts/ts/index";

export interface RosterRow {
  patient: PatientRecord;
  severity: TriageSeverity | null;
  touched: number;
}

const SEVERITIES: ReadonlySet<string> = new Set(["RED_EMERGENCY", "YELLOW_PHC", "GREEN_HOME"]);

/** One row per patient (never date-filtered): latest-touch time and latest triage severity, newest first. */
export function buildRoster(patients: readonly PatientRecord[], events: readonly CrdtEvent[]): RosterRow[] {
  const touched = new Map<string, number>();
  const triage = new Map<string, CrdtEvent>();
  for (const e of events) {
    if (!e.patient_id) continue;
    touched.set(e.patient_id, Math.max(touched.get(e.patient_id) ?? 0, e.hlc.wall_ms));
    if (e.event_type === "TRIAGE_COMPLETED") {
      const prev = triage.get(e.patient_id);
      if (!prev || compareHlc(e.hlc, prev.hlc) > 0) triage.set(e.patient_id, e);
    }
  }
  const rows: RosterRow[] = patients.map((patient) => {
    const sev = triage.get(patient.patient_id)?.payload.severity;
    return {
      patient,
      severity: typeof sev === "string" && SEVERITIES.has(sev) ? (sev as TriageSeverity) : null,
      touched: touched.get(patient.patient_id) ?? 0,
    };
  });
  return rows.sort(
    (a, b) =>
      b.touched - a.touched ||
      a.patient.full_name.localeCompare(b.patient.full_name) ||
      (a.patient.patient_id < b.patient.patient_id ? -1 : a.patient.patient_id > b.patient.patient_id ? 1 : 0),
  );
}

/** Case-insensitive match on name, village or household; blank query keeps every row. */
export function filterRoster(rows: readonly RosterRow[], query: string): RosterRow[] {
  const q = query.trim().toLowerCase();
  if (!q) return [...rows];
  return rows.filter(({ patient: p }) =>
    [p.full_name, p.village_id, p.household_id].some((v) => v != null && v.toLowerCase().includes(q)),
  );
}

export async function home(ctx: Ctx): Promise<HTMLElement> {
  const [pending, enrich, patients, events, pendingEvents] = await Promise.all([
    ctx.engine.pendingCount(),
    ctx.engine.pendingEnrichmentCount(),
    ctx.store.listPatients(),
    ctx.store.getAllEvents(),
    ctx.store.getPendingEvents(),
  ]);
  const outboxIds = new Set(pendingEvents.map((e) => e.event_id));
  const rows = buildRoster(patients, events);
  const SEV_KEY = { RED_EMERGENCY: "sev.red", YELLOW_PHC: "sev.yellow", GREEN_HOME: "sev.green" } as const;
  const item = ({ patient: p, severity }: RosterRow) => {
    const m = patientAgeMonths(p);
    const age = m === null ? null : m >= 24 ? t("roster.ageYm", { y: Math.floor(m / 12), m: m % 12 }) : t("age.months", { n: m });
    const stage = derivePatientStage(p.patient_id, events, outboxIds);
    const stagePill =
      stage.kind === "ai_ready"
        ? h("span", { class: "stage-pill stage-ai" }, t("stage.pillAi", { pct: stage.riskPct }))
        : stage.kind === "offline"
          ? h("span", { class: "stage-pill stage-offline" }, t("stage.pillOffline"))
          : h("span", { class: "stage-pill stage-synced" }, t("stage.pillSynced"));
    return h(
      "li",
      {},
      h("a", { href: `#/triage/${encodeURIComponent(p.patient_id)}` }, h("strong", {}, p.full_name), h("span", { class: "muted" }, t("roster.village", { v: p.village_id })), age ? h("span", { class: "muted" }, age) : null, stagePill, severity ? h("span", { class: `sevbadge sev-${severity}` }, t(SEV_KEY[severity])) : null),
    );
  };
  const list = h("ul", { class: "list roster" });
  const draw = (q: string) => {
    const shown = filterRoster(rows, q);
    list.replaceChildren(...(shown.length ? shown.map(item) : [h("li", {}, h("p", { class: "muted" }, t("roster.noMatch")))]));
  };
  const search = h("input", { type: "search", class: "rostersearch", "aria-label": t("roster.search"), placeholder: t("roster.search") });
  search.addEventListener("input", () => draw(search.value));
  draw("");

  const nav = (href: string, icon: string, key: Parameters<typeof t>[0], cls = "") =>
    h("a", { class: `bigbtn ${cls}`, href }, h("span", { "aria-hidden": "true", class: "ico" }, icon), h("span", {}, t(key)));

  return h(
    "section",
    {},
    h("h1", {}, t("home.title")),
    h(
      "div",
      { class: "stats", role: "group", "aria-label": t("home.status") },
      h("div", { class: "stat" }, h("strong", {}, String(pending)), h("span", {}, t("home.pendingSync"))),
      h("div", { class: "stat" }, h("strong", {}, String(enrich)), h("span", {}, t("home.pendingEnrich"))),
      h("div", { class: "stat" }, h("strong", {}, String(patients.length)), h("span", {}, t("home.patients"))),
    ),
    h(
      "div",
      { class: "navgrid" },
      nav("#/triage", "⚠", "nav.triage", "danger"),
      nav("#/register", "＋", "nav.register"),
      nav("#/vaccines", "💉", "nav.vaccines"),
      nav("#/checklist", "☑", "nav.checklist"),
      nav("#/voice", "🎤", "nav.voice"),
      nav("#/sync", "⇅", "nav.sync"),
    ),
    h("h2", {}, t("roster.title")),
    rows.length === 0 ? h("p", { class: "muted" }, t("roster.empty")) : [search, list],
  );
}
