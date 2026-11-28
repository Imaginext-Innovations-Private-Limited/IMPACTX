/**
 * Pure CRDT fold mirroring packages/crdt-sync projector.py for the views the
 * phone materializes: per-field LWW patients, per-field LWW action cards, and
 * pending enrichments. Malformed field values are skipped (never thrown), so a
 * bad payload can't poison the view or the event log.
 */
import type { ActionCard, CrdtEvent, PatientRecord } from "../../../../packages/contracts/ts/index";

type Key = [number, number, string, string];
type Regs = Map<string, { k: Key; v: unknown }>;

const orderKey = (e: CrdtEvent): Key => [e.hlc.wall_ms, e.hlc.logical, e.hlc.node_id, e.event_id];
const cmpKey = (a: Key, b: Key): number => {
  for (let i = 0; i < 4; i++) if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
  return 0;
};
const lww = (r: Regs, f: string, k: Key, v: unknown) => {
  const cur = r.get(f);
  if (!cur || cmpKey(k, cur.k) >= 0) r.set(f, { k, v });
};

const str = (v: unknown) => typeof v === "string" && v.length > 0;
const strOrNull = (v: unknown) => v === null || str(v);
const intOrNull = (v: unknown) => v === null || Number.isInteger(v);
const oneOf = (...xs: string[]) => (v: unknown) => typeof v === "string" && xs.includes(v);
const strList = (v: unknown) => Array.isArray(v) && v.every((x) => typeof x === "string");

const PATIENT_FIELDS: Record<string, (v: unknown) => boolean> = {
  full_name: str,
  date_of_birth: strOrNull,
  age_months: intOrNull,
  sex: oneOf("F", "M", "O", "U"),
  village_id: str,
  household_id: strOrNull,
  is_pregnant: (v) => typeof v === "boolean",
  gestational_weeks: intOrNull,
  preferred_language: str,
  registered_by_node: strOrNull,
};

const SEVERITY = oneOf("GREEN_HOME", "YELLOW_PHC", "RED_EMERGENCY");
const CARD_FIELDS: Record<string, (v: unknown) => boolean> = {
  patient_id: strOrNull,
  title: str,
  summary: str,
  action_steps: strList,
  priority: oneOf("LOW", "MEDIUM", "HIGH", "CRITICAL"),
  severity: (v) => v === null || SEVERITY(v),
  status: oneOf("OPEN", "ACKNOWLEDGED", "COMPLETED", "DISMISSED"),
  target_tier: oneOf("TIER_0_WATCH", "TIER_1_PHONE", "TIER_2_HUB"),
  watch_mode: (v) => v === null || oneOf("CHW_COMPANION", "PATIENT_FAMILY")(v),
  source_event_id: strOrNull,
  due_by: strOrNull,
  language: str,
};

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

export interface Projection {
  patients: Map<string, PatientRecord>;
  cards: Map<string, ActionCard>;
  pendingEnrichments: CrdtEvent[];
}

export function project(events: CrdtEvent[]): Projection {
  const seen = new Set<string>();
  const ordered = events
    .filter((e) => !seen.has(e.event_id) && seen.add(e.event_id))
    .sort((a, b) => cmpKey(orderKey(a), orderKey(b)));

  const pFields = new Map<string, Regs>();
  const pMeta = new Map<string, Regs>();
  const cFields = new Map<string, Regs>();
  const pending: CrdtEvent[] = [];
  const completedRefs = new Set<string>();
  const get = (m: Map<string, Regs>, id: string) => m.get(id) ?? m.set(id, new Map()).get(id)!;

  for (const e of ordered) {
    const k = orderKey(e);
    const p = isObj(e.payload) ? e.payload : {};
    if (e.enrichment_state === "PENDING") pending.push(e);

    if (e.event_type === "PATIENT_REGISTERED") {
      const pid = e.patient_id ?? p.patient_id;
      if (typeof pid !== "string" || !pid) continue;
      const regs = get(pFields, pid);
      for (const [f, ok] of Object.entries(PATIENT_FIELDS)) if (f in p && ok(p[f])) lww(regs, f, k, p[f]);
      if (!regs.has("registered_by_node")) regs.set("registered_by_node", { k, v: e.origin_node_id });
      const meta = get(pMeta, pid);
      if (isObj(p.metadata)) for (const [mk, mv] of Object.entries(p.metadata)) lww(meta, mk, k, mv);
    } else if (
      e.event_type === "ACTION_CARD_ISSUED" ||
      (e.event_type === "CHECKLIST_RECORDED" && str(p.card_id) && "status" in p)
    ) {
      const cid = str(p.card_id) ? (p.card_id as string) : e.event_id;
      const regs = get(cFields, cid);
      if (e.patient_id !== null && !("patient_id" in p)) lww(regs, "patient_id", k, e.patient_id);
      for (const [f, ok] of Object.entries(CARD_FIELDS)) if (f in p && ok(p[f])) lww(regs, f, k, p[f]);
      if (!regs.has("source_event_id")) regs.set("source_event_id", { k, v: e.ref_event_id ?? e.event_id });
    } else if (e.event_type === "ENRICHMENT_COMPLETED" && e.ref_event_id !== null) {
      completedRefs.add(e.ref_event_id);
    }
  }

  const flat = (r: Regs) => Object.fromEntries([...r].map(([f, { v }]) => [f, v]));
  const patients = new Map<string, PatientRecord>();
  for (const [pid, regs] of pFields) {
    const d = flat(regs);
    const meta = pMeta.get(pid) ?? new Map();
    const rec: PatientRecord = {
      patient_id: pid,
      full_name: (d.full_name as string) || "Unknown",
      date_of_birth: (d.date_of_birth as string | null) ?? null,
      age_months: (d.age_months as number | null) ?? null,
      sex: (d.sex as PatientRecord["sex"]) ?? "U",
      village_id: (d.village_id as string) || "UNKNOWN",
      household_id: (d.household_id as string | null) ?? null,
      is_pregnant: (d.is_pregnant as boolean) ?? false,
      gestational_weeks: (d.gestational_weeks as number | null) ?? null,
      preferred_language: (d.preferred_language as string) ?? "en",
      registered_by_node: (d.registered_by_node as string | null) ?? null,
      metadata: Object.fromEntries([...meta].sort(([a], [b]) => (a < b ? -1 : 1)).map(([mk, { v }]) => [mk, v])),
    };
    if (!rec.is_pregnant) rec.gestational_weeks = null;
    patients.set(pid, rec);
  }

  const cards = new Map<string, ActionCard>();
  for (const [cid, regs] of cFields) {
    const d = flat(regs);
    cards.set(cid, {
      card_id: cid,
      patient_id: (d.patient_id as string | null) ?? null,
      title: (d.title as string) || "Action Card",
      summary: (d.summary as string) || "Pending full card details",
      action_steps: (d.action_steps as string[]) ?? [],
      priority: (d.priority as ActionCard["priority"]) ?? "MEDIUM",
      severity: (d.severity as ActionCard["severity"]) ?? null,
      status: (d.status as ActionCard["status"]) ?? "OPEN",
      target_tier: (d.target_tier as ActionCard["target_tier"]) ?? "TIER_0_WATCH",
      watch_mode: (d.watch_mode as ActionCard["watch_mode"]) ?? null,
      source_event_id: (d.source_event_id as string | null) ?? null,
      due_by: (d.due_by as string | null) ?? null,
      language: (d.language as string) ?? "en",
    });
  }

  return { patients, cards, pendingEnrichments: pending.filter((e) => !completedRefs.has(e.event_id)) };
}
