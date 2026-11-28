/**
 * Offline NHM ASHA maternal ANC & postnatal (HBNC) checklist evaluator.
 *
 * Faithful port of `packages/clinical-engine/src/aarogya_clinical_engine/checklists.py`
 * (commit 53c61b2). `ChecklistEvaluation` is an engine-local result model (not a
 * shared contract); its `action_cards` conform to the `ActionCard` contract.
 */

import type { ActionCard, NodeTier, TriageSeverity, WatchMode } from "../../../../packages/contracts/ts/index";
import { MATERNAL_ANC_RULES } from "./rules/maternal_anc";
import { uuid } from "../core/uuid";
import type { ChecklistDef, ChecklistItemDef } from "./rules/types";

export const CHECKLIST_TYPES = [
  "anc_trimester_1",
  "anc_trimester_2",
  "anc_trimester_3",
  "pnc_mother",
  "pnc_newborn",
] as const;

export type ChecklistType = (typeof CHECKLIST_TYPES)[number];

export interface ChecklistEvaluation {
  checklist_type: ChecklistType;
  title: string;
  protocol: string;
  patient_id: string | null;
  total_items: number;
  completed_items: string[];
  missing_items: string[];
  missing_critical_checks: string[];
  missing_critical_labels: string[];
  completion_score: number;
  is_complete: boolean;
  has_critical_gaps: boolean;
  action_cards: ActionCard[];
}

function resolveType(value: string): ChecklistType {
  if (!(CHECKLIST_TYPES as readonly string[]).includes(value)) {
    throw new Error(`'${value}' is not a valid ChecklistType`);
  }
  return value as ChecklistType;
}

/** Return all supported maternal and postnatal checklist identifiers. */
export function listChecklistTypes(): ChecklistType[] {
  return [...CHECKLIST_TYPES];
}

/** Return the raw rule-table definition for a checklist type. */
export function getChecklistDefinition(checklistType: ChecklistType | string): ChecklistDef {
  const key = resolveType(checklistType);
  const def = MATERNAL_ANC_RULES.checklists[key];
  if (def === undefined) throw new Error(`Unknown checklist type: ${key}`);
  return { ...def };
}

/** Map gestational age in weeks to the NHM ANC trimester checklist. */
export function selectAncChecklistForGestationalWeeks(gestationalWeeks: number): ChecklistType {
  if (gestationalWeeks < 0 || gestationalWeeks > 45) {
    throw new Error(`gestational_weeks must be between 0 and 45, got ${gestationalWeeks}`);
  }
  if (gestationalWeeks <= 12) return "anc_trimester_1";
  if (gestationalWeeks <= 27) return "anc_trimester_2";
  return "anc_trimester_3";
}

function normalizeCompletedIds(completed: readonly string[] | Readonly<Record<string, boolean>>): Set<string> {
  if (Array.isArray(completed)) {
    return new Set((completed as readonly string[]).map((id) => String(id).trim()).filter((id) => id));
  }
  return new Set(
    Object.entries(completed as Record<string, boolean>)
      .filter(([, done]) => Boolean(done))
      .map(([k]) => String(k).trim()),
  );
}

/** Evaluate ANC trimester or HBNC postnatal checklist completion and emit ActionCards. */
export function evaluateChecklist(
  checklistType: ChecklistType | string,
  completedChecks: readonly string[] | Readonly<Record<string, boolean>>,
  opts: { patient_id?: string | null; due_by?: string | null; target_tier?: NodeTier; watch_mode?: WatchMode | null } = {},
): ChecklistEvaluation {
  const resolved = resolveType(checklistType);
  const definition = getChecklistDefinition(resolved);
  const items = definition.items;
  const completedSet = normalizeCompletedIds(completedChecks);
  const targetTier = opts.target_tier ?? "TIER_0_WATCH";
  const watchMode = opts.watch_mode === undefined ? "CHW_COMPANION" : opts.watch_mode;
  const base = {
    patient_id: opts.patient_id ?? null,
    status: "OPEN" as const,
    target_tier: targetTier,
    watch_mode: targetTier === "TIER_0_WATCH" ? watchMode : null,
    source_event_id: null,
    due_by: opts.due_by ?? null,
    language: "en",
  };

  const completedIds: string[] = [];
  const missingIds: string[] = [];
  const missingCriticalIds: string[] = [];
  const missingCriticalLabels: string[] = [];
  const missingRoutine: ChecklistItemDef[] = [];
  const actionCards: ActionCard[] = [];

  for (const item of items) {
    const itemId = String(item.id);
    if (completedSet.has(itemId)) {
      completedIds.push(itemId);
      continue;
    }
    missingIds.push(itemId);
    if (item.critical) {
      missingCriticalIds.push(itemId);
      missingCriticalLabels.push(String(item.label));
      const severity: TriageSeverity = item.escalation_severity ?? "YELLOW_PHC";
      actionCards.push({
        ...base,
        card_id: uuid(),
        title: `Missing Critical Check: ${item.label}`.slice(0, 160),
        summary: `${definition.title} — critical check pending: ${item.label}.`,
        action_steps: [String(item.recommended_action)],
        priority: "HIGH",
        severity,
      });
    } else {
      missingRoutine.push(item);
    }
  }

  if (missingRoutine.length > 0) {
    actionCards.push({
      ...base,
      card_id: uuid(),
      title: `Pending Routine Checks (${missingRoutine.length})`,
      summary: `${definition.title} has ${missingRoutine.length} routine check(s) remaining.`,
      action_steps: missingRoutine.map((i) => String(i.recommended_action)),
      priority: "LOW",
      severity: "GREEN_HOME",
    });
  }

  const total = items.length;
  return {
    checklist_type: resolved,
    title: String(definition.title),
    protocol: String(definition.protocol),
    patient_id: opts.patient_id ?? null,
    total_items: total,
    completed_items: completedIds,
    missing_items: missingIds,
    missing_critical_checks: missingCriticalIds,
    missing_critical_labels: missingCriticalLabels,
    completion_score: Math.round((completedIds.length / total) * 10_000) / 10_000,
    is_complete: missingIds.length === 0,
    has_critical_gaps: missingCriticalIds.length > 0,
    action_cards: actionCards,
  };
}
