/**
 * Aarogya Mesh shared TypeScript contracts.
 *
 * Mirrors `packages/contracts/src/aarogya_contracts/models.py` (schema v1.0.0)
 * for `apps/field-pwa` (Tier-1 CHW Phone) and `apps/watch-companion` (Tier-0 Watch).
 */

export const CONTRACT_SCHEMA_VERSION = "1.0.0" as const;

export type NodeTier = "TIER_0_WATCH" | "TIER_1_PHONE" | "TIER_2_HUB";

export type WatchMode = "CHW_COMPANION" | "PATIENT_FAMILY";

export type ExecutionTarget =
  | "LOCAL_DETERMINISTIC"
  | "LOCAL_TINY_ML"
  | "DEFER_TO_HUB";

export interface HardwareCapabilityManifest {
  node_id: string;
  tier: NodeTier;
  ram_mb: number;
  cpu_cores: number;
  battery_pct: number;
  has_npu: boolean;
  installed_models: string[];
  watch_mode: WatchMode | null;
}

export interface HlcTimestamp {
  wall_ms: number;
  logical: number;
  node_id: string;
}

export type EventType =
  | "PATIENT_REGISTERED"
  | "TRIAGE_COMPLETED"
  | "CHECKLIST_RECORDED"
  | "VACCINATION_LOGGED"
  | "VOICE_NOTE_RECORDED"
  | "ENRICHMENT_COMPLETED"
  | "ACTION_CARD_ISSUED"
  | "OUTBREAK_ALERT_RAISED";

export type EnrichmentState = "NOT_NEEDED" | "PENDING" | "COMPLETED" | "FAILED";

export interface CrdtEvent {
  event_id: string;
  hlc: HlcTimestamp;
  origin_node_id: string;
  patient_id: string | null;
  event_type: EventType;
  payload: Record<string, unknown>;
  enrichment_state: EnrichmentState;
  ref_event_id: string | null;
}

export type PatientSex = "F" | "M" | "O" | "U";

export interface PatientRecord {
  patient_id: string;
  full_name: string;
  date_of_birth: string | null; // ISO-8601 YYYY-MM-DD
  age_months: number | null;
  sex: PatientSex;
  village_id: string;
  household_id: string | null;
  is_pregnant: boolean;
  gestational_weeks: number | null;
  preferred_language: string;
  registered_by_node: string | null;
  metadata: Record<string, unknown>;
}

export type TriageSeverity = "GREEN_HOME" | "YELLOW_PHC" | "RED_EMERGENCY";

export interface TriageAssessment {
  assessment_id: string;
  patient_id: string | null;
  severity: TriageSeverity;
  matched_rules: string[];
  immediate_actions: string[];
  referral_required: boolean;
  rationale: string;
  confidence: number;
  protocol_source: string;
  execution_target: ExecutionTarget;
  assessed_at_ms: number | null;
}

export type VaccinationStatus = "OVERDUE" | "DUE_SOON" | "UPCOMING" | "COMPLETED";

export interface VaccinationDueItem {
  vaccine_code: string;
  vaccine_name: string;
  dose_label: string;
  due_date: string; // ISO-8601 YYYY-MM-DD
  status: VaccinationStatus;
  administered_date: string | null; // ISO-8601 YYYY-MM-DD
  days_delta: number;
  reminder_text: string;
  schedule_group: string;
}

export type ActionCardPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ActionCardStatus = "OPEN" | "ACKNOWLEDGED" | "COMPLETED" | "DISMISSED";

export interface ActionCard {
  card_id: string;
  patient_id: string | null;
  title: string;
  summary: string;
  action_steps: string[];
  priority: ActionCardPriority;
  severity: TriageSeverity | null;
  status: ActionCardStatus;
  target_tier: NodeTier;
  watch_mode: WatchMode | null;
  source_event_id: string | null;
  due_by: string | null; // ISO-8601 YYYY-MM-DD
  language: string;
}

export interface SyncEnvelope {
  envelope_id: string;
  sender_manifest: HardwareCapabilityManifest;
  sender_hlc: HlcTimestamp;
  since_cursor: string | null;
  next_cursor: string | null;
  events: CrdtEvent[];
  ack_event_ids: string[];
  schema_version: string;
}
