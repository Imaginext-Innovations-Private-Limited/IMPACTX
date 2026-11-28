import { describe, expect, it } from "vitest";
import type { CrdtEvent } from "../../../../packages/contracts/ts/index";
import { deriveIntakePathway, derivePatientStage, deriveTriageProtocol, extractClinicInsights, localizeRiskBand } from "../../src/ui/stage_tracker";

function makeEvent(partial: Partial<CrdtEvent> & Pick<CrdtEvent, "event_id" | "event_type">): CrdtEvent {
  return {
    origin_node_id: "phone-1",
    hlc: { wall_ms: 1_700_000_000_000, logical: 0, node_id: "phone-1" },
    patient_id: "p1",
    ref_event_id: null,
    enrichment_state: "NOT_NEEDED",
    payload: {},
    ...partial,
  };
}

describe("stage_tracker pure helpers", () => {
  it("extracts Clinic AI insights from ENRICHMENT_COMPLETED events with SHAP drivers", () => {
    const events: CrdtEvent[] = [
      makeEvent({
        event_id: "e-enr-1",
        event_type: "ENRICHMENT_COMPLETED",
        origin_node_id: "phc-hub",
        patient_id: "p1",
        ref_event_id: "e-triage-1",
        hlc: { wall_ms: 1_700_000_005_000, logical: 0, node_id: "phc-hub" },
        payload: {
          risk_score: {
            risk_score: 0.84,
            risk_band: "HIGH",
            top_features: [
              { feature: "systolic_bp", contribution: 0.32, direction: "positive" },
              { feature: "hemoglobin_g_dl", contribution: -0.09, direction: "negative" },
            ],
          },
          recommended_follow_up: "Immediate obstetric referral to FRU",
          reasoning_provenance: {
            stage: "HOST_LAPTOP_ML_ANALYTICS",
            clinical_protocol: "NHM ASHA Maternal (NHM_ASHA_MATERNAL_ANC_PNC_2024)",
            matched_rule_ids: ["MAT_RED_01", "MAT_PREECLAMPSIA_SYMPTOMATIC_RED"],
            clinical_parameters: "Severe headache + BP 156/102",
            ml_engine: "28-Tree Monotone GBDT + Exact TreeSHAP (clinical_gbdt_v1.json, AUROC 0.8318)",
            ml_summary: "Laptop GBDT combined 13 vitals & flags -> Risk 84% (WHO safety floor enforced)",
          },
        },
      }),
    ];
    const insights = extractClinicInsights(events, [{ patient_id: "p1", full_name: "Lakshmi Devi" }]);
    expect(insights).toHaveLength(1);
    expect(insights[0]!.patientName).toBe("Lakshmi Devi");
    expect(insights[0]!.riskPct).toBe(84);
    expect(insights[0]!.riskBand).toBe("HIGH");
    expect(insights[0]!.clinicalProtocol).toContain("NHM_ASHA_MATERNAL_ANC_PNC_2024");
    expect(insights[0]!.matchedRuleIds).toEqual(["MAT_RED_01", "MAT_PREECLAMPSIA_SYMPTOMATIC_RED"]);
    expect(insights[0]!.clinicalParameters).toBe("Severe headache + BP 156/102");
    expect(insights[0]!.mlEngine).toContain("28-Tree Monotone GBDT");
    expect(insights[0]!.mlSummary).toContain("Risk 84%");
    expect(insights[0]!.topFeatures).toEqual([
      { feature: "systolic bp", contribution: 0.32, isRisk: true },
      { feature: "hemoglobin g dl", contribution: -0.09, isRisk: false },
    ]);
    expect(insights[0]!.recommendedFollowUp).toBe("Immediate obstetric referral to FRU");
  });

  it("derives offline intake pathway and triage protocol accurately", () => {
    expect(deriveIntakePathway({ is_pregnant: true, gestational_weeks: 28, age_months: 300, date_of_birth: null })).toEqual({
      pathway: "MATERNAL_ANC",
      protocolCode: "NHM_ASHA_MATERNAL_ANC_PNC_2024",
      weeks: 28,
      trimester: 3,
      hasDob: false,
    });
    expect(deriveIntakePathway({ is_pregnant: false, gestational_weeks: null, age_months: 18, date_of_birth: "2025-05-01" }, new Date("2026-11-28"))).toEqual({
      pathway: "PEDIATRIC_IMNCI",
      protocolCode: "WHO_IMNCI_INDIA_2024",
      weeks: null,
      trimester: null,
      hasDob: true,
    });
    expect(deriveTriageProtocol({ matched_rules: ["MAT_RED_01"] })).toEqual({
      isMaternal: true,
      protocolCode: "NHM_ASHA_MATERNAL_ANC_PNC_2024",
    });
    expect(deriveTriageProtocol({ matched_rules: ["IMNCI_FEVER_MODERATE_YELLOW"] })).toEqual({
      isMaternal: false,
      protocolCode: "WHO_IMNCI_INDIA_2024",
    });
  });

  it("derives patient stage badges: offline -> synced -> ai_ready", () => {
    const reg = makeEvent({ event_id: "e-reg", event_type: "PATIENT_REGISTERED", patient_id: "p1" });
    const enr = makeEvent({
      event_id: "e-enr",
      event_type: "ENRICHMENT_COMPLETED",
      patient_id: "p1",
      payload: { risk_score: 0.72, risk_band: "HIGH" },
    });

    expect(derivePatientStage("p1", [reg], new Set(["e-reg"]))).toEqual({ kind: "offline" });
    expect(derivePatientStage("p1", [reg], new Set())).toEqual({ kind: "synced" });
    expect(derivePatientStage("p1", [reg, enr], new Set())).toEqual({ kind: "ai_ready", riskPct: 72, riskBand: "HIGH" });
  });

  it("localizes raw ML risk bands into plain-language labels", () => {
    expect(localizeRiskBand("LOW")).toBe("Low");
    expect(localizeRiskBand("MODERATE")).toBe("Moderate");
    expect(localizeRiskBand("HIGH")).toBe("High");
    expect(localizeRiskBand("CRITICAL")).toBe("Critical");
  });
});
