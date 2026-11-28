/**
 * Offline India UIP immunization schedule engine.
 *
 * Faithful port of `packages/clinical-engine/src/aarogya_clinical_engine/vaccinations.py`
 * (commit 53c61b2). Dates are ISO-8601 `YYYY-MM-DD` strings (calendar dates, no TZ).
 */

import type {
  ActionCard,
  NodeTier,
  VaccinationDueItem,
  VaccinationStatus,
  WatchMode,
} from "../../../../packages/contracts/ts/index";
import { UIP_VACCINE_RULES } from "./rules/uip_vaccines";
import type { UipVaccineEntry } from "./rules/types";
import { uuid } from "../core/uuid";

const DAY_MS = 86_400_000;
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** Parse a strict ISO calendar date into a UTC day ordinal. Throws on invalid input. */
export function isoToDayNumber(iso: string): number {
  const m = ISO_DATE.exec(iso);
  if (!m) throw new Error(`Invalid ISO date: ${iso}`);
  const ms = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const d = new Date(ms);
  if (d.getUTCFullYear() !== Number(m[1]) || d.getUTCMonth() !== Number(m[2]) - 1 || d.getUTCDate() !== Number(m[3])) {
    throw new Error(`Invalid ISO date: ${iso}`);
  }
  return Math.round(ms / DAY_MS);
}

/** Inverse of `isoToDayNumber`. */
export function dayNumberToIso(day: number): string {
  return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

function todayIso(): string {
  const now = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}

/**
 * Administered vaccines: either a mapping `{code: administeredIsoDate | null}`
 * (object or `Map`) or a list of codes (case/alias insensitive).
 */
export type AdministeredVaccines =
  | Readonly<Record<string, string | null>>
  | ReadonlyMap<string, string | null>
  | readonly string[]
  | null
  | undefined;

function buildAliasIndex(vaccines: readonly UipVaccineEntry[]): Map<string, string> {
  const index = new Map<string, string>();
  for (const entry of vaccines) {
    const canonical = String(entry.code);
    index.set(canonical.toLowerCase(), canonical);
    for (const alias of entry.aliases ?? []) index.set(String(alias).trim().toLowerCase(), canonical);
  }
  return index;
}

function normalizeAdministered(given: AdministeredVaccines, aliasIndex: Map<string, string>): Map<string, number | null> {
  const out = new Map<string, number | null>();
  if (given === null || given === undefined) return out;
  const canon = (raw: string) => aliasIndex.get(String(raw).trim().toLowerCase()) ?? String(raw).trim();
  if (Array.isArray(given)) {
    for (const raw of given as readonly string[]) out.set(canon(raw), null);
  } else {
    const entries = given instanceof Map ? [...given.entries()] : Object.entries(given as Record<string, string | null>);
    for (const [raw, adminDate] of entries) out.set(canon(raw), adminDate === null ? null : isoToDayNumber(adminDate));
  }
  return out;
}

/**
 * Compute the deterministic India UIP schedule. `days_delta` = due_date - as_of_date
 * in days (negative when overdue, 0 when due today or completed).
 */
export function computeVaccinationSchedule(
  dob: string,
  administered?: AdministeredVaccines,
  asOfDate?: string | null,
  opts: { dueSoonWindowDays?: number | null } = {},
): VaccinationDueItem[] {
  const dobDay = isoToDayNumber(dob);
  const refIso = asOfDate ?? todayIso();
  const refDay = isoToDayNumber(refIso);
  if (refDay < dobDay) throw new Error(`as_of_date (${refIso}) cannot precede dob (${dob})`);

  const table = UIP_VACCINE_RULES;
  const defaultWindow = Math.trunc(table.defaults.due_soon_window_days);
  const administeredMap = normalizeAdministered(administered, buildAliasIndex(table.vaccines));
  const ageDays = refDay - dobDay;
  const schedule: VaccinationDueItem[] = [];

  for (const entry of table.vaccines) {
    const code = String(entry.code);
    const name = String(entry.name);
    const milestone = String(entry.milestone);
    const leadDays = opts.dueSoonWindowDays ?? Math.trunc(entry.due_soon_lead_days ?? defaultWindow);
    const maxCatchupDays = Math.trunc(entry.max_catchup_age_days ?? 1825);
    const scheduleGroup = String(entry.schedule_group ?? "UIP_INDIA");
    const dueDay = dobDay + Math.trunc(entry.due_age_days);
    const dueIso = dayNumberToIso(dueDay);

    if (administeredMap.has(code)) {
      const recorded = administeredMap.get(code) ?? null;
      const adminIso = dayNumberToIso(recorded !== null ? recorded : Math.min(dueDay, refDay));
      schedule.push({
        vaccine_code: code,
        vaccine_name: name,
        dose_label: milestone,
        due_date: dueIso,
        status: "COMPLETED",
        administered_date: adminIso,
        days_delta: 0,
        reminder_text: `${name} (${milestone}) completed on ${adminIso}.`,
        schedule_group: scheduleGroup,
      });
      continue;
    }

    const daysDelta = dueDay - refDay;
    let status: VaccinationStatus;
    let reminder: string;
    if (daysDelta < 0) {
      status = "OVERDUE";
      const overdueBy = Math.abs(daysDelta);
      reminder =
        ageDays > maxCatchupDays
          ? `${name} (${milestone}) is overdue by ${overdueBy} day(s) and past standard ` +
            "UIP catch-up window — consult Medical Officer at PHC."
          : `${name} (${milestone}) is overdue by ${overdueBy} day(s) ` +
            `(due ${dueIso}). Schedule catch-up at nearest VHND/PHC.`;
    } else if (daysDelta <= leadDays) {
      status = "DUE_SOON";
      reminder =
        daysDelta === 0
          ? `${name} (${milestone}) is due today (${dueIso}).`
          : `${name} (${milestone}) is due in ${daysDelta} day(s) on ${dueIso}.`;
    } else {
      status = "UPCOMING";
      reminder = `${name} (${milestone}) is upcoming on ${dueIso} (in ${daysDelta} days).`;
    }

    schedule.push({
      vaccine_code: code,
      vaccine_name: name,
      dose_label: milestone,
      due_date: dueIso,
      status,
      administered_date: null,
      days_delta: daysDelta,
      reminder_text: reminder,
      schedule_group: scheduleGroup,
    });
  }
  return schedule;
}

/** Generate glanceable `ActionCard` reminders for OVERDUE and DUE_SOON vaccines. */
export function vaccinationItemsToActionCards(
  items: Iterable<VaccinationDueItem>,
  opts: { patient_id?: string | null; target_tier?: NodeTier; watch_mode?: WatchMode | null } = {},
): ActionCard[] {
  const targetTier = opts.target_tier ?? "TIER_0_WATCH";
  const watchMode = opts.watch_mode === undefined ? "PATIENT_FAMILY" : opts.watch_mode;
  const effectiveWatchMode = targetTier === "TIER_0_WATCH" ? watchMode : null;
  const base = {
    patient_id: opts.patient_id ?? null,
    status: "OPEN" as const,
    target_tier: targetTier,
    watch_mode: effectiveWatchMode,
    source_event_id: null,
    language: "en",
  };
  const cards: ActionCard[] = [];
  for (const item of items) {
    if (item.status === "OVERDUE") {
      cards.push({
        ...base,
        card_id: uuid(),
        title: `Overdue Vaccine: ${item.vaccine_code} (${item.dose_label})`.slice(0, 160),
        summary: item.reminder_text,
        action_steps: [
          `Bring child and MCP Card to nearest VHND/PHC for ${item.vaccine_name}.`,
          "Verify catch-up eligibility with ANM.",
        ],
        priority: "HIGH",
        severity: "YELLOW_PHC",
        due_by: item.due_date,
      });
    } else if (item.status === "DUE_SOON") {
      cards.push({
        ...base,
        card_id: uuid(),
        title: `Vaccine Due Soon: ${item.vaccine_code} (${item.dose_label})`.slice(0, 160),
        summary: item.reminder_text,
        action_steps: [`Plan VHND/Sub-Centre visit on or before ${item.due_date} with MCP Card.`],
        priority: "MEDIUM",
        severity: "GREEN_HOME",
        due_by: item.due_date,
      });
    }
  }
  return cards;
}
