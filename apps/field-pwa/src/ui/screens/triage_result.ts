import type { TriageAssessment, TriageSeverity } from "../../../../../packages/contracts/ts/index";
import { getLang, t, type Lang } from "../../i18n";
import { HI_TRIAGE_ACTIONS, HI_TRIAGE_RATIONALE } from "../../i18n/hi";
import { KN_TRIAGE_ACTIONS, KN_TRIAGE_RATIONALE } from "../../i18n/kn";
import { TA_TRIAGE_ACTIONS, TA_TRIAGE_RATIONALE } from "../../i18n/ta";
import { h } from "../dom";
import { deriveTriageProtocol } from "../stage_tracker";

const SEV = {
  RED_EMERGENCY: { cls: "sev-red", icon: "⛔", title: "sev.red", sub: "sev.redSub" },
  YELLOW_PHC: { cls: "sev-yellow", icon: "▲", title: "sev.yellow", sub: "sev.yellowSub" },
  GREEN_HOME: { cls: "sev-green", icon: "✔", title: "sev.green", sub: "sev.greenSub" },
} as const satisfies Record<TriageSeverity, { cls: string; icon: string; title: string; sub: string }>;

const ACTION_TABLES: Partial<Record<Lang, Readonly<Record<string, string>>>> = {
  hi: HI_TRIAGE_ACTIONS,
  kn: KN_TRIAGE_ACTIONS,
  ta: TA_TRIAGE_ACTIONS,
};

const RATIONALE_TABLES: Partial<Record<Lang, Readonly<Record<string, string>>>> = {
  hi: HI_TRIAGE_RATIONALE,
  kn: KN_TRIAGE_RATIONALE,
  ta: TA_TRIAGE_RATIONALE,
};

/** Display-only localized action string for hi/kn; the stored English is never changed. */
export function localizeTriageAction(text: string, lang: Lang = getLang()): string {
  const tbl = ACTION_TABLES[lang];
  return tbl ? (tbl[text] ?? text) : text;
}

/** Display-only localized rationale built from matched rule ids; any unknown id keeps the English. */
export function localizeTriageRationale(text: string, matchedRules: readonly string[], lang: Lang = getLang()): string {
  const tbl = RATIONALE_TABLES[lang];
  if (!tbl || matchedRules.length === 0) return text;
  const out: string[] = [];
  for (const id of matchedRules) {
    const locText = tbl[id];
    if (locText === undefined) return text;
    if (!out.includes(locText)) out.push(locText);
  }
  return out.join(" ");
}

/** Haptic alert via the Android shell, if present. Never throws. */
export function vibrateIfEmergency(severity: TriageSeverity, g: unknown = globalThis): void {
  if (severity !== "RED_EMERGENCY") return;
  try {
    (g as { AarogyaNativeBridge?: { vibrateEmergency?: () => void } }).AarogyaNativeBridge?.vibrateEmergency?.();
  } catch {
    /* ignore */
  }
}

export interface SafetyFloorProof {
  executionTarget: string;
  confidence: string;
  matchedRules: readonly string[];
}

/** Pure proof metadata surfaced on every triage result card (0 network calls). */
export function buildSafetyFloorProof(a: TriageAssessment): SafetyFloorProof {
  return {
    executionTarget: a.execution_target,
    confidence: a.confidence.toFixed(2),
    matchedRules: a.matched_rules,
  };
}

export interface TriageResultOptions {
  /** Optional live-updating slot for the 3-step stage tracker and Laptop ML insight card. */
  stageSlot?: HTMLElement;
}

/**
 * Huge text + icon + colour banner. Never colour alone. Actions/rationale are shown localized
 * (display only); the stored TriageAssessment keeps the engine's English strings.
 */
export function renderTriageResult(a: TriageAssessment, options?: TriageResultOptions): HTMLElement {
  const s = SEV[a.severity];
  vibrateIfEmergency(a.severity);
  const why = localizeTriageRationale(a.rationale, a.matched_rules);
  const proof = buildSafetyFloorProof(a);
  const proto = deriveTriageProtocol(a);
  return h(
    "section",
    { class: `result ${s.cls}`, role: "alert", "aria-live": "assertive", tabindex: "-1", id: "triage-result" },
    h("div", { class: "banner" }, h("span", { class: "bigicon", "aria-hidden": "true" }, s.icon), h("div", {}, h("h2", {}, t(s.title)), h("p", {}, t(s.sub)))),
    a.severity === "RED_EMERGENCY"
      ? h("a", { class: "call108", href: "tel:108" }, "☎ ", t("sev.call108"))
      : null,
    a.referral_required ? h("p", { class: "referral" }, t(a.severity === "RED_EMERGENCY" ? "ref.red" : "ref.yellow")) : null,
    h(
      "div",
      { class: "proof-strip", "data-proof": "safety-floor", "data-provenance": "on-phone" },
      h(
        "div",
        { class: "proof-pills" },
        h("span", { class: "proof-pill" }, t("proof.localDeterministic")),
        h("span", { class: "proof-pill" }, t("proof.confidence", { val: proof.confidence })),
        h("span", { class: "proof-pill" }, t("proof.zeroNetwork")),
      ),
      h(
        "div",
        { class: "prov-details" },
        h("p", { class: "prov-line" }, h("strong", {}, `${t("prov.stageLabel")}: `), t("prov.phoneStage")),
        h("p", { class: "prov-line" }, h("strong", {}, `${t("prov.sourceLabel")}: `), t(proto.isMaternal ? "prov.protocolMaternal" : "prov.protocolImnci")),
        h("p", { class: "prov-line" }, h("strong", {}, `${t("prov.paramsLabel")}: `), why),
        h("p", { class: "prov-line" }, h("strong", {}, `${t("stage.whatsNext")}: `), t("prov.nextLaptopMl")),
      ),
      proof.matchedRules.length > 0
        ? h(
            "div",
            { class: "proof-rules" },
            h("span", { class: "proof-label" }, `${t("proof.matchedRules")}:`),
            ...proof.matchedRules.map((id) => h("code", { class: "rule-badge", lang: "en" }, id)),
          )
        : null,
    ),
    h("h3", {}, t("result.actions")),
    h("ul", {}, a.immediate_actions.map((x) => h("li", {}, localizeTriageAction(x)))),
    h(
      "details",
      {},
      h("summary", {}, t("result.why")),
      h("p", {}, why),
      why !== a.rationale ? h("p", { class: "orig-en", lang: "en" }, h("small", {}, `${t("result.originalEn")}: ${a.rationale}`)) : null,
    ),
    options?.stageSlot ?? null,
    h(
      "div",
      { class: "next-actions" },
      h("a", { class: "bigbtn", href: a.patient_id ? `#/voice/${encodeURIComponent(a.patient_id)}` : "#/voice" }, t("reg.nextVoice")),
      h("a", { class: "bigbtn", href: "#/sync" }, t("nav.sync")),
      h("a", { class: "bigbtn", href: "#/" }, t("nav.home")),
    ),
  );
}
