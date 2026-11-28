import { evaluateChecklist, getChecklistDefinition, listChecklistTypes, selectAncChecklistForGestationalWeeks } from "../clinical";
import type { ChecklistEvaluation, ChecklistType } from "../clinical";
import type { CrdtEvent } from "../../../../packages/contracts/ts/index";
import { compareHlc } from "../core/hlc";

export const checklistTypes = (): ChecklistType[] => listChecklistTypes();

/** Auto-select ANC trimester checklist from gestational weeks; null when unknown/invalid. */
export function autoChecklistType(weeks: number | null): ChecklistType | null {
  if (weeks === null) return null;
  try {
    return selectAncChecklistForGestationalWeeks(weeks);
  } catch {
    return null;
  }
}

export const checklistItems = (type: ChecklistType) =>
  getChecklistDefinition(type).items.map((i) => ({ id: i.id, label: i.label, critical: !!i.critical }));

/**
 * CHECKLIST_RECORDED payload: summary only. Deliberately has NO card_id/status,
 * so projectors never mistake it for an ActionCard.
 */
export function buildChecklistPayload(ev: ChecklistEvaluation, additionalNotes?: string): Record<string, unknown> {
  const notes = additionalNotes?.trim();
  return {
    checklist_type: ev.checklist_type,
    protocol: ev.protocol,
    completed_items: ev.completed_items,
    missing_items: ev.missing_items,
    missing_critical_checks: ev.missing_critical_checks,
    completion_score: ev.completion_score,
    is_complete: ev.is_complete,
    has_critical_gaps: ev.has_critical_gaps,
    ...(notes ? { additional_notes: notes } : {}),
  };
}

export const evaluate = (type: ChecklistType, done: string[], patientId: string | null) =>
  evaluateChecklist(type, done, { patient_id: patientId, target_tier: "TIER_1_PHONE", watch_mode: null });

/** Completed item ids from the patient's latest CHECKLIST_RECORDED of `type` (by HLC); empty if none. */
export function latestCompletedChecks(events: readonly CrdtEvent[], patientId: string | null, type: ChecklistType): Set<string> {
  if (patientId === null) return new Set();
  let latest: CrdtEvent | null = null;
  for (const e of events) {
    if (e.event_type !== "CHECKLIST_RECORDED" || e.patient_id !== patientId || e.payload.checklist_type !== type) continue;
    if (latest === null || compareHlc(e.hlc, latest.hlc) > 0) latest = e;
  }
  const items = latest?.payload.completed_items;
  return new Set(Array.isArray(items) ? items.filter((i): i is string => typeof i === "string") : []);
}
