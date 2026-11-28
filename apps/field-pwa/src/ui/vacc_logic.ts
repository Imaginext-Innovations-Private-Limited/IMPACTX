import type { CrdtEvent, VaccinationDueItem } from "../../../../packages/contracts/ts/index";
import { computeVaccinationSchedule } from "../clinical";

/** {vaccine_code: administered_date} for one patient, folded from the event log. */
export function administeredFromEvents(events: CrdtEvent[], patientId: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const e of events) {
    if (e.event_type !== "VACCINATION_LOGGED" || e.patient_id !== patientId) continue;
    const p = e.payload as Partial<VaccinationDueItem>;
    if (typeof p.vaccine_code === "string" && typeof p.administered_date === "string") out[p.vaccine_code] = p.administered_date;
  }
  return out;
}

export function scheduleFor(dob: string, events: CrdtEvent[], patientId: string, asOf: string): VaccinationDueItem[] {
  return computeVaccinationSchedule(dob, administeredFromEvents(events, patientId), asOf);
}

export const STATUS_ORDER = ["OVERDUE", "DUE_SOON", "UPCOMING", "COMPLETED"] as const;

export function groupByStatus(items: VaccinationDueItem[]): Record<(typeof STATUS_ORDER)[number], VaccinationDueItem[]> {
  const g = { OVERDUE: [], DUE_SOON: [], UPCOMING: [], COMPLETED: [] } as Record<(typeof STATUS_ORDER)[number], VaccinationDueItem[]>;
  for (const i of items) g[i.status].push(i);
  return g;
}

/**
 * VACCINATION_LOGGED payload = a COMPLETED VaccinationDueItem (the shape the
 * projector validates). Returns null if the code is not in the schedule or the
 * date is invalid / before birth.
 */
export function buildVaccinationPayload(
  dob: string,
  vaccineCode: string,
  administeredDate: string,
  asOf: string,
): VaccinationDueItem | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(administeredDate) || administeredDate < dob || administeredDate > asOf) return null;
  const base = computeVaccinationSchedule(dob, [], asOf).find((i) => i.vaccine_code === vaccineCode);
  if (!base) return null;
  return {
    ...base,
    status: "COMPLETED",
    administered_date: administeredDate,
    days_delta: 0,
    reminder_text: `${base.vaccine_name} (${base.dose_label}) completed on ${administeredDate}.`,
  };
}
