import type { CrdtEvent, PatientRecord, TriageAssessment } from "../../../../packages/contracts/ts/index";
import { t } from "../i18n";
import { h } from "./dom";
import { patientAgeMonths } from "./triage_map";

export type StageStep = 1 | 2 | 3;

export interface StageTrackerOptions {
  /** Number of steps completed (1, 2, or 3). */
  completedSteps: 1 | 2 | 3;
  /** Currently highlighted step (1, 2, or 3). */
  activeStep: StageStep;
  /** Short plain-language status headline. */
  headline: string;
  /** 1-line "What's Next" guidance cue for the ASHA worker. */
  nextCue: string;
  /** Optional reasoning / provenance detail block rendered inside the tracker. */
  reasoningNode?: HTMLElement | null;
  /** Optional 1-tap next-step buttons or links. */
  actions?: HTMLElement[];
}

const STEP_KEYS = ["stage.step1", "stage.step2", "stage.step3"] as const;

/**
 * Reusable 3-step visual progress tracker + "What's Next" cue (pure DOM).
 * 1. Saved Offline -> 2. Synced to Clinic Hub -> 3. Clinic AI Insight Ready.
 */
export function renderStageTracker(opts: StageTrackerOptions): HTMLElement {
  const pct = Math.round((opts.completedSteps / 3) * 100);
  const stepsEl = h(
    "ol",
    { class: "stage-steps" },
    STEP_KEYS.map((key, idx) => {
      const n = (idx + 1) as StageStep;
      const done = n <= opts.completedSteps;
      const active = n === opts.activeStep && !done;
      const cls = done ? "stage-step done" : active ? "stage-step active" : "stage-step";
      const mark = done ? "✔ " : active ? "● " : "○ ";
      return h("li", { class: cls }, h("span", { "aria-hidden": "true" }, mark), t(key));
    }),
  );

  const track = h(
    "div",
    {
      class: "voice-progress-track",
      role: "progressbar",
      "aria-valuenow": String(opts.completedSteps),
      "aria-valuemin": "1",
      "aria-valuemax": "3",
      "aria-label": opts.headline,
    },
    h("div", {
      class: `voice-progress-fill stage-${opts.completedSteps === 3 ? "completed" : opts.completedSteps === 2 ? "hub_processing" : "waiting_connection"}`,
      style: `width: ${pct}%`,
    }),
  );

  return h(
    "div",
    { class: "stage-tracker", "data-stage-tracker": String(opts.completedSteps) },
    h("p", { class: "stage-headline" }, opts.headline),
    stepsEl,
    track,
    opts.reasoningNode ?? null,
    h("p", { class: "stage-next" }, h("strong", {}, `${t("stage.whatsNext")}: `), opts.nextCue),
    opts.actions && opts.actions.length ? h("div", { class: "stage-actions" }, opts.actions) : null,
  );
}

export interface IntakePathway {
  pathway: "MATERNAL_ANC" | "PEDIATRIC_IMNCI" | "GENERAL_IMNCI";
  protocolCode: "NHM_ASHA_MATERNAL_ANC_PNC_2024" | "WHO_IMNCI_INDIA_2024";
  weeks: number | null;
  trimester: 1 | 2 | 3 | null;
  hasDob: boolean;
}

/** Determine the offline clinical pathway activated at patient registration. */
export function deriveIntakePathway(
  p: Pick<PatientRecord, "is_pregnant" | "gestational_weeks" | "age_months" | "date_of_birth">,
  asOf: Date = new Date(),
): IntakePathway {
  if (p.is_pregnant) {
    const w = p.gestational_weeks;
    const tri: 1 | 2 | 3 | null = w === null ? null : w <= 12 ? 1 : w <= 27 ? 2 : 3;
    return {
      pathway: "MATERNAL_ANC",
      protocolCode: "NHM_ASHA_MATERNAL_ANC_PNC_2024",
      weeks: w,
      trimester: tri,
      hasDob: Boolean(p.date_of_birth),
    };
  }
  const ageM = patientAgeMonths(p, asOf);
  if (ageM !== null && ageM < 60) {
    return {
      pathway: "PEDIATRIC_IMNCI",
      protocolCode: "WHO_IMNCI_INDIA_2024",
      weeks: null,
      trimester: null,
      hasDob: Boolean(p.date_of_birth),
    };
  }
  return {
    pathway: "GENERAL_IMNCI",
    protocolCode: "WHO_IMNCI_INDIA_2024",
    weeks: null,
    trimester: null,
    hasDob: Boolean(p.date_of_birth),
  };
}

/** Format localized Offline Intake Reasoning text for a newly registered patient. */
export function formatIntakeReasoning(p: Pick<PatientRecord, "is_pregnant" | "gestational_weeks" | "age_months" | "date_of_birth">): string {
  const info = deriveIntakePathway(p);
  if (info.pathway === "MATERNAL_ANC") {
    return info.weeks !== null && info.trimester !== null
      ? t("prov.intakeMaternal", { w: info.weeks, tri: info.trimester })
      : t("prov.intakeMaternalNoWeeks");
  }
  if (info.pathway === "PEDIATRIC_IMNCI") {
    return info.hasDob ? t("prov.intakePediatricDob") : t("prov.intakePediatric");
  }
  return t("prov.intakeGeneral");
}

/** Determine whether a triage assessment matched Maternal NHM vs WHO IMNCI rules. */
export function deriveTriageProtocol(a: Pick<TriageAssessment, "matched_rules">): {
  isMaternal: boolean;
  protocolCode: "NHM_ASHA_MATERNAL_ANC_PNC_2024" | "WHO_IMNCI_INDIA_2024";
} {
  const isMaternal = a.matched_rules.some((r) => r.startsWith("MAT_"));
  return {
    isMaternal,
    protocolCode: isMaternal ? "NHM_ASHA_MATERNAL_ANC_PNC_2024" : "WHO_IMNCI_INDIA_2024",
  };
}

export interface ShapDriver {
  feature: string;
  contribution: number;
  isRisk: boolean;
}

export interface ClinicInsight {
  eventId: string;
  refEventId: string | null;
  patientId: string | null;
  patientName: string | null;
  recordedAtMs: number;
  riskScore: number;
  riskPct: number;
  riskBand: string | null;
  topFeatures: ShapDriver[];
  recommendedFollowUp: string | null;
  /** Reasoning provenance: WHO/NHM clinical floor + Laptop ML model metadata. */
  clinicalProtocol: string;
  matchedRuleIds: string[];
  clinicalParameters: string | null;
  mlEngine: string;
  mlSummary: string | null;
}

const DEFAULT_ML_ENGINE = "28-Tree Monotone GBDT + Exact TreeSHAP (clinical_gbdt_v1.json, AUROC 0.8318)";

function parseTopFeatures(raw: unknown): ShapDriver[] {
  if (!Array.isArray(raw)) return [];
  const out: ShapDriver[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const o = item as Record<string, unknown>;
    const feat = typeof o.feature === "string" ? o.feature : typeof o.name === "string" ? o.name : null;
    const contrib =
      typeof o.contribution === "number"
        ? o.contribution
        : typeof o.shap_value === "number"
          ? o.shap_value
          : typeof o.value === "number"
            ? o.value
            : 0;
    if (!feat) continue;
    const dir = typeof o.direction === "string" ? o.direction.toLowerCase() : "";
    const isRisk = dir === "protective" || dir === "negative" ? false : dir === "risk" || dir === "positive" ? true : contrib >= 0;
    out.push({
      feature: feat.replaceAll("_", " "),
      contribution: contrib,
      isRisk,
    });
  }
  return out.slice(0, 5);
}

function extractRiskFromEnrichmentPayload(payload: Record<string, unknown>): {
  riskScore: number | null;
  riskBand: string | null;
  topFeatures: ShapDriver[];
  followUp: string | null;
  clinicalProtocol: string;
  matchedRuleIds: string[];
  clinicalParameters: string | null;
  mlEngine: string;
  mlSummary: string | null;
} {
  const rsObj = payload.risk_score && typeof payload.risk_score === "object" ? (payload.risk_score as Record<string, unknown>) : null;
  const riskScore =
    typeof payload.risk_score === "number"
      ? payload.risk_score
      : rsObj && typeof rsObj.risk_score === "number"
        ? rsObj.risk_score
        : rsObj && typeof rsObj.score === "number"
          ? rsObj.score
          : null;
  const riskBand =
    typeof payload.risk_band === "string"
      ? payload.risk_band
      : rsObj && typeof rsObj.risk_band === "string"
        ? rsObj.risk_band
        : null;
  const topFeatures = parseTopFeatures(payload.top_features ?? rsObj?.top_features ?? rsObj?.shap_drivers);
  const noteObj = payload.structured_note && typeof payload.structured_note === "object" ? (payload.structured_note as Record<string, unknown>) : null;
  const triageObj =
    payload.triage_assessment && typeof payload.triage_assessment === "object" ? (payload.triage_assessment as Record<string, unknown>) : null;
  const firstAction =
    triageObj && Array.isArray(triageObj.immediate_actions) && typeof triageObj.immediate_actions[0] === "string"
      ? triageObj.immediate_actions[0]
      : null;
  const followUp =
    typeof payload.recommended_follow_up === "string"
      ? payload.recommended_follow_up
      : noteObj && typeof noteObj.recommended_follow_up === "string"
        ? noteObj.recommended_follow_up
        : firstAction;

  const prov =
    payload.reasoning_provenance && typeof payload.reasoning_provenance === "object"
      ? (payload.reasoning_provenance as Record<string, unknown>)
      : null;
  const rawRules = prov?.matched_rule_ids ?? triageObj?.matched_rules;
  const matchedRuleIds = Array.isArray(rawRules) ? rawRules.filter((x): x is string => typeof x === "string") : [];
  const isMaternal = matchedRuleIds.some((r) => r.startsWith("MAT_"));
  const clinicalProtocol =
    typeof prov?.clinical_protocol === "string" && prov.clinical_protocol.length > 0
      ? prov.clinical_protocol
      : isMaternal
        ? "NHM ASHA Maternal (NHM_ASHA_MATERNAL_ANC_PNC_2024)"
        : "WHO IMNCI (WHO_IMNCI_INDIA_2024)";
  const clinicalParameters =
    typeof prov?.clinical_parameters === "string" && prov.clinical_parameters.length > 0
      ? prov.clinical_parameters
      : typeof triageObj?.rationale === "string" && triageObj.rationale.length > 0
        ? triageObj.rationale
        : null;
  const mlEngine =
    typeof prov?.ml_engine === "string" && prov.ml_engine.length > 0 ? prov.ml_engine : DEFAULT_ML_ENGINE;
  const mlSummary = typeof prov?.ml_summary === "string" && prov.ml_summary.length > 0 ? prov.ml_summary : null;

  return {
    riskScore,
    riskBand,
    topFeatures,
    followUp,
    clinicalProtocol,
    matchedRuleIds,
    clinicalParameters,
    mlEngine,
    mlSummary,
  };
}

/** Extract synced ENRICHMENT_COMPLETED ML insights, newest first. */
export function extractClinicInsights(
  events: readonly CrdtEvent[],
  patients: readonly Pick<PatientRecord, "patient_id" | "full_name">[],
): ClinicInsight[] {
  const byPatient = new Map(patients.map((p) => [p.patient_id, p.full_name]));
  const items: ClinicInsight[] = [];
  for (const e of events) {
    if (e.event_type !== "ENRICHMENT_COMPLETED") continue;
    const payload = (e.payload ?? {}) as Record<string, unknown>;
    const parsed = extractRiskFromEnrichmentPayload(payload);
    if (parsed.riskScore === null) continue;
    const clamped = Math.max(0, Math.min(1, parsed.riskScore));
    items.push({
      eventId: e.event_id,
      refEventId: e.ref_event_id,
      patientId: e.patient_id,
      patientName: e.patient_id ? (byPatient.get(e.patient_id) ?? e.patient_id) : null,
      recordedAtMs: e.hlc.wall_ms,
      riskScore: clamped,
      riskPct: Math.round(clamped * 100),
      riskBand: parsed.riskBand,
      topFeatures: parsed.topFeatures,
      recommendedFollowUp: parsed.followUp,
      clinicalProtocol: parsed.clinicalProtocol,
      matchedRuleIds: parsed.matchedRuleIds,
      clinicalParameters: parsed.clinicalParameters,
      mlEngine: parsed.mlEngine,
      mlSummary: parsed.mlSummary,
    });
  }
  return items.sort((a, b) => b.recordedAtMs - a.recordedAtMs);
}

export type PatientStageBadge =
  | { kind: "ai_ready"; riskPct: number; riskBand: string | null }
  | { kind: "synced" }
  | { kind: "offline" };

/** Derive a compact status badge for a patient row on Home. */
export function derivePatientStage(
  patientId: string,
  events: readonly CrdtEvent[],
  outboxIds: ReadonlySet<string>,
): PatientStageBadge {
  let latestAi: { wallMs: number; riskPct: number; riskBand: string | null } | null = null;
  let hasOffline = false;
  for (const e of events) {
    if (e.patient_id !== patientId) continue;
    if (outboxIds.has(e.event_id)) hasOffline = true;
    if (e.event_type === "ENRICHMENT_COMPLETED") {
      const { riskScore, riskBand } = extractRiskFromEnrichmentPayload((e.payload ?? {}) as Record<string, unknown>);
      if (riskScore !== null && (!latestAi || e.hlc.wall_ms >= latestAi.wallMs)) {
        latestAi = {
          wallMs: e.hlc.wall_ms,
          riskPct: Math.round(Math.max(0, Math.min(1, riskScore)) * 100),
          riskBand,
        };
      }
    }
  }
  if (latestAi) return { kind: "ai_ready", riskPct: latestAi.riskPct, riskBand: latestAi.riskBand };
  if (hasOffline) return { kind: "offline" };
  return { kind: "synced" };
}

/** Map a raw ML risk band enum (LOW/MODERATE/HIGH/CRITICAL) to a localized label. */
export function localizeRiskBand(band: string): string {
  switch (band.toUpperCase()) {
    case "LOW":
      return t("riskBand.LOW");
    case "MODERATE":
    case "MEDIUM":
      return t("riskBand.MODERATE");
    case "HIGH":
      return t("riskBand.HIGH");
    case "CRITICAL":
      return t("riskBand.CRITICAL");
    default:
      return band;
  }
}
