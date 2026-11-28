import { describe, expect, it, vi } from "vitest";
import type {
  ActionCard,
  VaccinationDueItem,
} from "../../../../packages/contracts/ts/index";
import {
  ALLOWED_TRIAGE_ASSESSMENT_KEYS,
  WATCH_DANGER_SIGNS,
  evaluateWatchDangerScreen,
  projectPatientFamilyReminders,
} from "../../src/clinical/index";
import { MemoryStorage } from "../../src/core/index";
import { WatchKernel } from "../../src/watch_kernel";

const ALLOWED_ACTION_CARD_KEYS = [
  "card_id",
  "patient_id",
  "title",
  "summary",
  "action_steps",
  "priority",
  "severity",
  "status",
  "target_tier",
  "watch_mode",
  "source_event_id",
  "due_by",
  "language",
] as const;

const FORBIDDEN_HINDI_LOANWORDS = [
  "ज़रूर",
  "जरूर",
  "मरीज़",
  "मरीज",
  "दवा",
  "ख़तरा",
  "खतरा",
  "खून",
  "बुखार",
  "डॉक्टर",
  "एम्बुलेंस",
  "अस्पताल",
  "खुराक",
  "चेक",
  "अलर्ट",
  "कार्ड",
  "मोड",
  "सिंक",
  "वक़्त",
  "वक्त",
  "दर्द",
];

function assertPureShuddhHindi(text: string): void {
  const nfd = text.normalize("NFD");
  expect(nfd).not.toMatch(/\u093c/);
  expect(text).not.toMatch(/[\u0958-\u095f]/);
  for (const forbidden of FORBIDDEN_HINDI_LOANWORDS) {
    expect(text).not.toContain(forbidden);
  }
}

describe("evaluateWatchDangerScreen", () => {
  it("returns GREEN_HOME with exact TriageAssessment keys when no danger signs are checked", () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = evaluateWatchDangerScreen({
      patientId: "pat-green-01",
      nodeId: "watch-01",
      hlc: { wall_ms: 1_700_000_000_000, logical: 0, node_id: "watch-01" },
      dangerSigns: [],
    });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.severity).toBe("GREEN_HOME");
    expect(result.assessment.severity).toBe("GREEN_HOME");
    expect(result.assessment.referral_required).toBe(false);
    expect(result.assessment.confidence).toBe(1.0);
    expect(result.assessment.execution_target).toBe("LOCAL_DETERMINISTIC");
    expect(result.assessment.matched_rules).toEqual(["WATCH_RAPID_NO_DANGER_SIGNS"]);
    expect(result.actionCard).toBeNull();
    expect(result.actionCardEvent).toBeNull();
    expect(result.events).toHaveLength(1);

    const payloadKeys = Object.keys(result.triageEvent.payload).sort();
    expect(payloadKeys).toEqual([...ALLOWED_TRIAGE_ASSESSMENT_KEYS].sort());
    expect("watch_mode" in result.triageEvent.payload).toBe(false);

    vi.unstubAllGlobals();
  });

  it("forces RED_EMERGENCY, referral_required=true, and companion CRITICAL ActionCard for every danger sign", () => {
    const requiredCoreFlags = [
      "not_able_to_drink_or_breastfeed",
      "vomits_everything",
      "convulsions",
      "lethargic_or_unconscious",
      "severe_respiratory_distress",
      "vaginal_bleeding",
      "severe_headache_or_blurred_vision",
      "convulsions_or_fits",
    ];
    const catalogFlags = WATCH_DANGER_SIGNS.map((d) => d.flag);
    for (const flag of requiredCoreFlags) {
      expect(catalogFlags).toContain(flag);
    }

    for (const def of WATCH_DANGER_SIGNS) {
      const result = evaluateWatchDangerScreen({
        patientId: "pat-red-01",
        nodeId: "watch-02",
        hlc: { wall_ms: 1_700_000_001_000, logical: 0, node_id: "watch-02" },
        dangerSigns: [def.flag],
        language: "en",
      });

      expect(result.severity).toBe("RED_EMERGENCY");
      expect(result.assessment.severity).toBe("RED_EMERGENCY");
      expect(result.assessment.referral_required).toBe(true);
      expect(result.assessment.confidence).toBe(1.0);
      expect(result.assessment.execution_target).toBe("LOCAL_DETERMINISTIC");
      expect(result.assessment.matched_rules).toContain(def.ruleId);

      // Strict Hub extra="forbid" key check on TRIAGE_COMPLETED payload
      expect(Object.keys(result.triageEvent.payload).sort()).toEqual(
        [...ALLOWED_TRIAGE_ASSESSMENT_KEYS].sort(),
      );
      expect("watch_mode" in result.triageEvent.payload).toBe(false);

      // Companion ACTION_CARD_ISSUED verification
      expect(result.actionCard).not.toBeNull();
      expect(result.actionCardEvent).not.toBeNull();
      expect(result.events).toHaveLength(2);
      expect(result.actionCard?.priority).toBe("CRITICAL");
      expect(result.actionCard?.severity).toBe("RED_EMERGENCY");
      expect(result.actionCard?.target_tier).toBe("TIER_0_WATCH");
      expect(result.actionCard?.source_event_id).toBe(result.triageEvent.event_id);
      expect(result.actionCardEvent?.event_type).toBe("ACTION_CARD_ISSUED");
      expect(result.actionCardEvent?.ref_event_id).toBe(result.triageEvent.event_id);
      expect(
        Object.keys(result.actionCardEvent?.payload ?? {}).sort(),
      ).toEqual([...ALLOWED_ACTION_CARD_KEYS].sort());
    }
  });

  it("supports boolean flags, aliases, empty patientId normalization, and pure Shuddh Tatsama Hindi cards", () => {
    const result = evaluateWatchDangerScreen({
      patientId: "   ",
      nodeId: "watch-hi-01",
      unableToDrinkOrBreastfeed: false,
      vomitsEverything: false,
      convulsions: false,
      lethargicOrUnconscious: false,
      severeRespiratoryDistress: true,
      dangerSigns: ["severe_breathing_difficulty"],
      language: "hi",
    });

    expect(result.severity).toBe("RED_EMERGENCY");
    expect(result.assessment.patient_id).toBeNull();
    expect(result.assessment.matched_rules).toEqual(["IMNCI_GDS_05"]);
    expect(result.actionCard?.language).toBe("hi");
    assertPureShuddhHindi(result.actionCard!.title);
    assertPureShuddhHindi(result.actionCard!.summary);
    for (const step of result.actionCard!.action_steps) {
      assertPureShuddhHindi(step);
    }
  });

  it("contains zero nukta U+093C or Perso-Arabic/Hinglish words in all Hindi danger sign labels", () => {
    for (const def of WATCH_DANGER_SIGNS) {
      assertPureShuddhHindi(def.labelHi);
    }
  });
});

describe("projectPatientFamilyReminders", () => {
  const vaccinations: VaccinationDueItem[] = [
    {
      vaccine_code: "BCG",
      vaccine_name: "BCG",
      dose_label: "Birth",
      due_date: "2026-09-01",
      status: "COMPLETED",
      administered_date: "2026-09-01",
      days_delta: 0,
      reminder_text: "Completed on 2026-09-01.",
      schedule_group: "UIP_INDIA",
    },
    {
      vaccine_code: "PENTA-1",
      vaccine_name: "Pentavalent-1",
      dose_label: "6 Weeks",
      due_date: "2026-11-28",
      status: "DUE_SOON",
      administered_date: null,
      days_delta: 5,
      reminder_text: "",
      schedule_group: "UIP_INDIA",
    },
    {
      vaccine_code: "OPV-1",
      vaccine_name: "OPV-1",
      dose_label: "6 Weeks",
      due_date: "2026-11-10",
      status: "OVERDUE",
      administered_date: null,
      days_delta: -13,
      reminder_text: "",
      schedule_group: "UIP_INDIA",
    },
    {
      vaccine_code: "MR-1",
      vaccine_name: "Measles-Rubella-1",
      dose_label: "9 Months",
      due_date: "2027-06-01",
      status: "UPCOMING",
      administered_date: null,
      days_delta: 190,
      reminder_text: "",
      schedule_group: "UIP_INDIA",
    },
  ];

  const actionCards: ActionCard[] = [
    {
      card_id: "card-med-1",
      patient_id: "pat-1",
      title: "Oral Zinc Tablet (20 mg)",
      summary: "Give 1 zinc tablet daily for 14 days.",
      action_steps: ["Dissolve tablet in clean water or breastmilk"],
      priority: "HIGH",
      severity: "YELLOW_PHC",
      status: "OPEN",
      target_tier: "TIER_0_WATCH",
      watch_mode: "PATIENT_FAMILY",
      source_event_id: "evt-1",
      due_by: "2026-11-24",
      language: "en",
    },
    {
      card_id: "card-chw-only",
      patient_id: "pat-1",
      title: "CHW MUAC Follow-Up",
      summary: "Measure MUAC in 14 days.",
      action_steps: [],
      priority: "CRITICAL",
      severity: "RED_EMERGENCY",
      status: "OPEN",
      target_tier: "TIER_0_WATCH",
      watch_mode: "CHW_COMPANION",
      source_event_id: "evt-2",
      due_by: "2026-11-23",
      language: "en",
    },
    {
      card_id: "card-done",
      patient_id: "pat-1",
      title: "Completed ORS Reminder",
      summary: "Already completed.",
      action_steps: [],
      priority: "HIGH",
      severity: "GREEN_HOME",
      status: "COMPLETED",
      target_tier: "TIER_0_WATCH",
      watch_mode: "PATIENT_FAMILY",
      source_event_id: "evt-3",
      due_by: "2026-11-23",
      language: "en",
    },
  ];

  it("maps OVERDUE->HIGH, DUE_SOON->MEDIUM, hides COMPLETED/CHW cards, and sorts by priority then dueBy", () => {
    const reminders = projectPatientFamilyReminders({
      vaccinations,
      actionCards,
      language: "hi",
    });

    // Should include OPV-1 (OVERDUE -> HIGH, due 2026-11-10), card-med-1 (HIGH, due 2026-11-24), PENTA-1 (DUE_SOON -> MEDIUM)
    expect(reminders.map((r) => r.id)).toEqual([
      "vax:OPV-1:6 Weeks",
      "card:card-med-1",
      "vax:PENTA-1:6 Weeks",
    ]);

    expect(reminders[0].priority).toBe("HIGH");
    expect(reminders[1].priority).toBe("HIGH");
    expect(reminders[1].category).toBe("MEDICATION");
    expect(reminders[2].priority).toBe("MEDIUM");

    for (const item of reminders) {
      assertPureShuddhHindi(item.titleHi);
      assertPureShuddhHindi(item.messageHi);
      expect(item.title).toBe(item.titleHi);
      expect(item.message).toBe(item.messageHi);
    }
  });

  it("includes UPCOMING as LOW priority only when includeUpcoming is true", () => {
    const reminders = projectPatientFamilyReminders({
      vaccinations,
      includeUpcoming: true,
      language: "en",
    });

    expect(reminders.map((r) => r.id)).toEqual([
      "vax:OPV-1:6 Weeks",
      "vax:PENTA-1:6 Weeks",
      "vax:MR-1:9 Months",
    ]);
    expect(reminders[2].priority).toBe("LOW");
  });
});

describe("WatchKernel.screenDangerSigns integration", () => {
  it("delegates to evaluateWatchDangerScreen and persists companion ACTION_CARD_ISSUED when persistActionCard=true", () => {
    const storage = new MemoryStorage();
    const kernel = new WatchKernel("watch-clin-1", "CHW_COMPANION", {
      storage,
      nowMs: () => 1_700_000_050_000,
    });

    const outcome = kernel.screenDangerSigns(
      {
        patientId: "pat-mat-01",
        dangerSigns: ["severe_headache_or_blurred_vision"],
        language: "hi",
      },
      { persistActionCard: true },
    );

    expect(outcome.severity).toBe("RED_EMERGENCY");
    expect(outcome.assessment.matched_rules).toEqual(["MAT_RED_01"]);
    expect(outcome.actionCard?.priority).toBe("CRITICAL");
    expect(outcome.actionCardEvent).not.toBeNull();
    expect(kernel.getStore().getOutboxEvents()).toHaveLength(2);
    expect(kernel.getVisibleActionCards()).toHaveLength(1);
    expect(kernel.getVisibleActionCards()[0].priority).toBe("CRITICAL");
    assertPureShuddhHindi(kernel.getVisibleActionCards()[0].title);
  });
});
