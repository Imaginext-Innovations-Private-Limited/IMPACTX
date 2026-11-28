/** Offline deterministic clinical safety floor for the Tier-1 phone (ported from packages/clinical-engine). */

export {
  FLAG_ALIASES,
  evaluateTriage,
  evaluateWatchRapidTriage,
  normalizeFlag,
  triageToActionCard,
  validateTriageInput,
} from "./triage";
export type { PatientCategory, TriageInput, TriageMode } from "./triage";
export {
  computeVaccinationSchedule,
  dayNumberToIso,
  isoToDayNumber,
  vaccinationItemsToActionCards,
} from "./vaccinations";
export type { AdministeredVaccines } from "./vaccinations";
export {
  CHECKLIST_TYPES,
  evaluateChecklist,
  getChecklistDefinition,
  listChecklistTypes,
  selectAncChecklistForGestationalWeeks,
} from "./checklists";
export type { ChecklistEvaluation, ChecklistType } from "./checklists";
export { IMNCI_PEDIATRIC_RULES } from "./rules/imnci_pediatric";
export { MATERNAL_ANC_RULES } from "./rules/maternal_anc";
export { UIP_VACCINE_RULES } from "./rules/uip_vaccines";
