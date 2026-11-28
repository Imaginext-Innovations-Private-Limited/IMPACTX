import { evaluateTriage, evaluateWatchRapidTriage } from "../../clinical";
import type { PatientCategory } from "../../clinical";
import type { PatientRecord } from "../../core";
import { t, tx } from "../../i18n";
import { checkbox, clear, field, h } from "../dom";
import type { Ctx } from "../ctx";
import {
  TEMP_F_BOUNDS,
  VITAL_SPECS,
  applyCategory,
  convertTempDisplay,
  dangerOptionsForCategory,
  fastEmergencyOptions,
  flagLabel,
  buildTriageInput,
  dehydrationFlags,
  maternalRedOptions,
  maternalYellowOptions,
  patientAgeMonths,
  suggestCategory,
  type FlagOption,
  type NumField,
  type NumError,
  type TempUnit,
  type TriageFormState,
} from "../triage_map";
import { renderTriageResult } from "./triage_result";
import { extractClinicInsights, localizeRiskBand, renderStageTracker, type ClinicInsight } from "../stage_tracker";
import { runSync } from "../app_state";
import type { CrdtEvent, TriageAssessment } from "../../../../../packages/contracts/ts/index";

const NUM_LABEL: Record<NumField, Parameters<typeof t>[0]> = {
  temperature_c: "v.temp",
  spo2_pct: "v.spo2",
  respiratory_rate_bpm: "v.rr",
  systolic_bp: "v.sys",
  diastolic_bp: "v.dia",
  hemoglobin_g_dl: "v.hb",
  muac_cm: "v.muac",
  age_months: "v.ageMonths",
  gestational_weeks: "v.weeks",
  fever_days: "v.feverDays",
  diarrhea_days: "v.diarrheaDays",
};

export async function triage(ctx: Ctx, params: string[]): Promise<HTMLElement> {
  const patients = await ctx.store.listPatients();
  const preset = params[0] ? patients.find((p) => p.patient_id === params[0]) : undefined;
  const st: TriageFormState = {
    category: preset ? suggestCategory(preset) : null,
    patientId: preset?.patient_id ?? null,
    nums: {},
    tempUnit: "F",
    isPregnant: preset?.is_pregnant ?? false,
    isPostpartum: false,
    dangerFlags: [],
    symptomFlags: [],
    dehydrationFlags: [],
    cough: false,
    chestIndrawing: false,
    diarrhea: false,
    bloodInStool: false,
    edema: false,
    pallor: false,
    malariaRdt: false,
  };
  if (preset) {
    const m = patientAgeMonths(preset);
    if (m !== null) st.nums.age_months = String(m);
    if (preset.gestational_weeks !== null) st.nums.gestational_weeks = String(preset.gestational_weeks);
  }

  const resultBox = h("div", { "aria-live": "assertive" });
  const errBox = h("div", { class: "error", role: "alert" });
  const formBox = h("div");

  const patientSel = h(
    "select",
    { name: "patient" },
    h("option", { value: "" }, t("triage.anon")),
    patients.map((p) => h("option", { value: p.patient_id, selected: p.patient_id === st.patientId }, p.full_name)),
  );
  const catSel = h(
    "select",
    { name: "category" },
    (["PEDIATRIC", "MATERNAL", "GENERAL"] as PatientCategory[]).map((c) =>
      h("option", { value: c, selected: c === st.category }, t(`cat.${c}` as const)),
    ),
  );
  catSel.prepend(h("option", { value: "", selected: st.category === null }, t("triage.chooseCat")));
  const noteBox = h("div", { class: "error", role: "alert" });
  const setCategory = (c: PatientCategory | null) => {
    const { cleared } = applyCategory(st, c);
    clear(noteBox);
    if (cleared.length) noteBox.append(h("p", {}, t("triage.cleared", { list: cleared.map(flagLabel).join("; ") })));
    catSel.value = c ?? "";
    drawForm();
  };
  patientSel.addEventListener("change", () => {
    st.patientId = patientSel.value || null;
    drawFastOptions();
    const p: PatientRecord | undefined = patients.find((x) => x.patient_id === st.patientId);
    if (p) {
      st.isPregnant = p.is_pregnant;
      const m = patientAgeMonths(p);
      if (m !== null) st.nums.age_months = String(m);
      if (p.gestational_weeks !== null) st.nums.gestational_weeks = String(p.gestational_weeks);
      setCategory(suggestCategory(p));
    }
  });
  catSel.addEventListener("change", () => {
    setCategory((catSel.value || null) as PatientCategory | null);
  });

  const tempField = () => {
    const unit = (): TempUnit => st.tempUnit ?? "F";
    const bounds = () => (unit() === "F" ? TEMP_F_BOUNDS : VITAL_SPECS.temperature_c);
    const b0 = bounds();
    const i = h("input", {
      type: "number",
      name: "temperature_c",
      min: b0.min,
      max: b0.max,
      step: b0.step,
      inputmode: "decimal",
      value: st.nums.temperature_c ?? "",
    });
    i.addEventListener("input", () => (st.nums.temperature_c = i.value));
    const unitSel = h(
      "select",
      { name: "temp_unit", "aria-label": t("v.tempF") },
      h("option", { value: "F", selected: unit() === "F" }, "°F"),
      h("option", { value: "C", selected: unit() === "C" }, "°C"),
    );
    const wrap = field(t(unit() === "F" ? "v.tempF" : "v.temp"), h("div", { class: "agerow" }, i, unitSel), `${b0.min}–${b0.max} °${unit()}`);
    unitSel.addEventListener("change", () => {
      const nextUnit = unitSel.value as TempUnit;
      st.tempUnit = nextUnit;
      const converted = convertTempDisplay(i.value, nextUnit);
      i.value = converted;
      st.nums.temperature_c = converted;
      const b = bounds();
      i.min = String(b.min);
      i.max = String(b.max);
      wrap.querySelector("label")!.textContent = t(nextUnit === "F" ? "v.tempF" : "v.temp");
      wrap.querySelector("small")!.textContent = `${b.min}–${b.max} °${nextUnit}`;
    });
    return wrap;
  };

  const numField = (f: NumField) => {
    if (f === "temperature_c") return tempField();
    const spec = VITAL_SPECS[f];
    const i = h("input", {
      type: "number",
      name: f,
      min: spec.min,
      max: spec.max,
      step: spec.step,
      inputmode: spec.integer ? "numeric" : "decimal",
      value: st.nums[f] ?? "",
    });
    i.addEventListener("input", () => (st.nums[f] = i.value));
    return field(t(NUM_LABEL[f]), i, `${spec.min}–${spec.max}`);
  };

  const flagGroup = (title: string, opts: FlagOption[], into: string[]) =>
    h(
      "fieldset",
      {},
      h("legend", {}, title),
      opts.map((o) =>
        checkbox(tx(`flag.${o.flag}`, o.label), o.flag, into.includes(o.flag), (c) => {
          const i = into.indexOf(o.flag);
          if (c && i < 0) into.push(o.flag);
          if (!c && i >= 0) into.splice(i, 1);
        }),
      ),
    );
  const bool = (label: string, key: keyof TriageFormState) =>
    checkbox(label, String(key), st[key] as boolean, (c) => ((st[key] as boolean) = c));

  function drawForm() {
    clear(formBox);
    const rb = document.getElementById("run-triage") as HTMLButtonElement | null;
    if (rb) rb.disabled = st.category === null;
    if (st.category === null) {
      formBox.append(h("p", { class: "error", role: "alert" }, t("triage.pickCategory")));
      return;
    }

    const otherSymInput = h("input", {
      type: "text",
      name: "additional_symptoms",
      maxlength: 500,
      value: st.additionalSymptoms ?? "",
    });
    otherSymInput.addEventListener("input", () => (st.additionalSymptoms = otherSymInput.value));

    const optionalVitals = h("div", { class: "grid2" }, numField("spo2_pct"), numField("respiratory_rate_bpm"));
    const moreContent: HTMLElement[] = [field(t("triage.otherSymptoms"), otherSymInput, t("triage.otherSymptomsHint"))];

    if (st.category === "PEDIATRIC") {
      formBox.append(
        flagGroup(t("triage.dangerSigns"), dangerOptionsForCategory(st.category), st.dangerFlags),
        numField("temperature_c"),
      );
      optionalVitals.append(numField("age_months"), numField("fever_days"), numField("diarrhea_days"), numField("muac_cm"));
      moreContent.unshift(
        h("fieldset", {}, h("legend", {}, t("triage.symptoms")), bool(t("s.cough"), "cough"), bool(t("s.indrawing"), "chestIndrawing"), bool(t("s.diarrhea"), "diarrhea"), bool(t("s.blood"), "bloodInStool"), bool(t("s.edema"), "edema"), bool(t("s.pallor"), "pallor"), bool(t("s.rdt"), "malariaRdt")),
        flagGroup(
          t("triage.dehydration"),
          dehydrationFlags().map((f) => ({ flag: f, label: tx(`dehy.${f}`, f) })),
          st.dehydrationFlags,
        ),
      );
    } else if (st.category === "MATERNAL") {
      formBox.append(
        h("fieldset", {}, h("legend", {}, t("triage.maternalStatus")), bool(t("reg.pregnant"), "isPregnant"), bool(t("triage.postpartum"), "isPostpartum")),
        flagGroup(t("triage.dangerSigns"), dangerOptionsForCategory(st.category), st.dangerFlags),
        flagGroup(t("triage.maternalDanger"), maternalRedOptions(), st.dangerFlags),
        numField("temperature_c"),
      );
      optionalVitals.append(numField("systolic_bp"), numField("diastolic_bp"), numField("gestational_weeks"), numField("hemoglobin_g_dl"));
      moreContent.unshift(flagGroup(t("triage.watchSigns"), maternalYellowOptions(), st.symptomFlags));
    } else {
      formBox.append(
        flagGroup(t("triage.dangerSigns"), dangerOptionsForCategory(st.category), st.dangerFlags),
        numField("temperature_c"),
      );
      optionalVitals.append(numField("systolic_bp"), numField("diastolic_bp"), numField("age_months"), numField("fever_days"));
    }

    formBox.append(
      h("details", { class: "optional-group" }, h("summary", {}, t("triage.optionalVitals")), optionalVitals),
      h("details", { class: "optional-group" }, h("summary", {}, t("triage.moreSymptoms")), moreContent),
    );
  }
  drawForm();

  const errText = (e: NumError) => {
    if (e.field === "temperature_c" && (st.tempUnit ?? "F") === "F") {
      return t(e.reason === "NaN" ? "err.nan" : e.reason === "integer" ? "err.int" : "err.range", {
        f: t("v.tempF"),
        min: TEMP_F_BOUNDS.min,
        max: TEMP_F_BOUNDS.max,
      });
    }
    const s = VITAL_SPECS[e.field];
    return t(e.reason === "NaN" ? "err.nan" : e.reason === "integer" ? "err.int" : "err.range", { f: t(NUM_LABEL[e.field]), min: s.min, max: s.max });
  };

  let liveUnsubs: Array<() => void> = [];
  const clearLiveUnsubs = () => {
    while (liveUnsubs.length) liveUnsubs.pop()?.();
  };

  const renderMlInsightBox = (ins: ClinicInsight): HTMLElement => {
    const riskCls = ins.riskPct >= 65 ? "risk-high" : ins.riskPct >= 35 ? "risk-mod" : "risk-low";
    return h(
      "div",
      { class: `card insight-card ${riskCls}`, "data-provenance": "laptop-ml" },
      h(
        "div",
        { class: "insight-head" },
        h("span", { class: "stage-pill stage-ai" }, t("prov.stage3Badge")),
        h("span", { class: `risk-pill ${riskCls}` }, `${t("insights.riskScore", { pct: ins.riskPct })}${ins.riskBand ? ` · ${localizeRiskBand(ins.riskBand)}` : ""}`),
      ),
      h(
        "div",
        { class: "provenance-box provenance-ml" },
        h("p", { class: "prov-line" }, h("strong", {}, `${t("prov.mlSourceTitle")}: `), h("span", { lang: "en" }, ins.mlEngine)),
        ins.mlSummary ? h("p", { class: "prov-line" }, ins.mlSummary) : null,
      ),
      ins.topFeatures.length
        ? h(
            "ul",
            { class: "shap-list" },
            ins.topFeatures.map((f) =>
              h(
                "li",
                { class: f.isRisk ? "shap-item shap-pos" : "shap-item shap-neg" },
                h("span", { class: "shap-tag" }, t(f.isRisk ? "insights.riskDriver" : "insights.protectiveDriver")),
                " ",
                h("span", {}, f.feature),
                " ",
                h("code", { lang: "en" }, `(${f.contribution >= 0 ? "+" : ""}${f.contribution.toFixed(2)})`),
              ),
            ),
          )
        : null,
    );
  };

  /** Show the engine's result immediately, then persist locally and live-sync for Laptop ML Risk Score. */
  function show(a: TriageAssessment) {
    clearLiveUnsubs();
    clear(errBox);
    clear(resultBox);
    const stageSlot = h("div", { class: "triage-live-stage", "aria-live": "polite" });
    resultBox.append(renderTriageResult(a, { stageSlot }));
    const saved = h("p", { class: "muted", role: "status" }, t("triage.saving"));
    resultBox.append(saved);
    const resEl = document.getElementById("triage-result") as HTMLElement | null;
    resEl?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    resEl?.focus();
    runBtn.disabled = true;
    ctx.engine
      .enqueue({ event_type: "TRIAGE_COMPLETED", patient_id: a.patient_id, enrichment_state: "PENDING", payload: { ...a } })
      .then((triageEvent) => {
        saved.textContent = t("triage.saved");
        let syncInFlight = false;
        let syncedOnce = false;
        let lastOfflineHint: string | null = null;

        const findMatchingInsight = async (): Promise<{ insight: ClinicInsight | null; stillOutbox: boolean }> => {
          const [allEvents, pendingEvents] = await Promise.all([ctx.store.getAllEvents(), ctx.store.getPendingEvents()]);
          const outboxIds = new Set(pendingEvents.map((e) => e.event_id));
          const stillOutbox = outboxIds.has(triageEvent.event_id);
          const matching: CrdtEvent[] = allEvents.filter(
            (e) =>
              e.event_type === "ENRICHMENT_COMPLETED" &&
              (e.ref_event_id === triageEvent.event_id ||
                (a.patient_id !== null && e.patient_id === a.patient_id && e.hlc.wall_ms >= triageEvent.hlc.wall_ms)),
          );
          const insights = extractClinicInsights(matching, patients);
          return { insight: insights[0] ?? null, stillOutbox };
        };

        const syncBtn = h(
          "button",
          {
            type: "button",
            class: "primary",
            onclick: () => void triggerSync(),
          },
          t("triage.syncAndAi"),
        );

        const refreshStage = async () => {
          if (!stageSlot.isConnected) {
            clearLiveUnsubs();
            return;
          }
          const { insight, stillOutbox } = await findMatchingInsight();
          if (insight) {
            clearLiveUnsubs();
            stageSlot.replaceChildren(
              renderStageTracker({
                completedSteps: 3,
                activeStep: 3,
                headline: t("triage.aiReadyHeadline"),
                nextCue: insight.recommendedFollowUp ?? t("prov.nextLaptopMl"),
                reasoningNode: renderMlInsightBox(insight),
              }),
            );
            return;
          }
          if (syncInFlight) {
            syncBtn.disabled = true;
            syncBtn.textContent = t("sync.running");
            stageSlot.replaceChildren(
              renderStageTracker({
                completedSteps: stillOutbox ? 1 : 2,
                activeStep: stillOutbox ? 2 : 3,
                headline: t("triage.syncingAi"),
                nextCue: t("triage.stageNext"),
                actions: [syncBtn],
              }),
            );
            return;
          }
          syncBtn.disabled = false;
          syncBtn.textContent = t("triage.syncAndAi");
          if (!stillOutbox || (syncedOnce && ctx.engine.status === "idle" && !lastOfflineHint)) {
            stageSlot.replaceChildren(
              renderStageTracker({
                completedSteps: 2,
                activeStep: 3,
                headline: t("triage.syncedWaitingAi"),
                nextCue: t("triage.stageNext"),
                actions: [syncBtn],
              }),
            );
            return;
          }
          stageSlot.replaceChildren(
            renderStageTracker({
              completedSteps: 1,
              activeStep: 2,
              headline: t("triage.stageHeadline"),
              nextCue: lastOfflineHint ?? t("triage.stageNext"),
              actions: [syncBtn],
            }),
          );
        };

        const triggerSync = async () => {
          if (syncInFlight) return;
          const online = typeof navigator === "undefined" ? true : navigator.onLine;
          if (!online) {
            lastOfflineHint = t("triage.offlineAiHint");
            await refreshStage();
            return;
          }
          syncInFlight = true;
          lastOfflineHint = null;
          await refreshStage();
          try {
            await runSync(ctx.engine);
            syncedOnce = true;
            if (ctx.engine.status !== "idle") {
              lastOfflineHint = t("triage.offlineAiHint");
            } else {
              const { insight } = await findMatchingInsight();
              if (!insight) {
                await new Promise((r) => setTimeout(r, 700));
                if (stageSlot.isConnected) await runSync(ctx.engine);
              }
            }
          } finally {
            syncInFlight = false;
            await refreshStage();
          }
        };

        liveUnsubs = [
          ctx.engine.events.on("enrichment", () => void refreshStage()),
          ctx.engine.events.on("status", () => void refreshStage()),
        ];

        void refreshStage().then(() => {
          const online = typeof navigator === "undefined" ? true : navigator.onLine;
          if (online) void triggerSync();
          else {
            lastOfflineHint = t("triage.offlineAiHint");
            void refreshStage();
          }
        });
      })
      .catch((e) => {
        saved.className = "error";
        saved.textContent = `${t("triage.saveFail")} ${String(e)}`;
      })
      .finally(() => {
        runBtn.disabled = st.category === null;
      });
  }

  const runBtn = h("button", { type: "button", class: "primary", id: "run-triage", disabled: st.category === null, onclick: () => {
    clear(errBox);
    clear(resultBox);
    const r = buildTriageInput(st);
    if (!r.ok) {
      if (r.needsCategory) errBox.append(h("p", {}, t("triage.pickCategory")));
      if (r.hiddenFlags) errBox.append(h("p", {}, t("triage.hiddenFlags")));
      errBox.append(h("ul", {}, [...r.errors.map((e) => h("li", {}, errText(e))), r.message ? h("li", {}, r.message) : null]));
      return;
    }
    try {
      show(evaluateTriage(r.input));
    } catch (e) {
      errBox.append(h("p", {}, e instanceof Error ? e.message : String(e)));
    }
  } }, t("triage.run"));

  // Fast path: worker confirms which danger sign; the engine classifies (RED via the canonical danger-sign floor).
  let radios: HTMLInputElement[] = [];
  const radioBox = h("div");
  const confirmBtn = h("button", { type: "button", class: "confirm", disabled: true }, t("triage.fastConfirm"));
  const cancelBtn = h("button", { type: "button" }, t("triage.fastCancel"));
  function drawFastOptions() {
    clear(radioBox);
    const flags = fastEmergencyOptions(patients.find((p) => p.patient_id === st.patientId)?.sex);
    radios = flags.map((f) => h("input", { type: "radio", name: "fastflag", value: f }));
    radios.forEach((r) => r.addEventListener("change", () => (confirmBtn.disabled = false)));
    radioBox.append(...radios.map((r, i) => h("label", { class: "check" }, r, h("span", {}, flagLabel(flags[i]!)))));
    confirmBtn.disabled = true;
  }
  drawFastOptions();
  const fastPanel = h("div", { class: "fastpanel", role: "group", "aria-label": t("triage.fastAsk"), hidden: true },
    h("p", {}, h("strong", {}, t("triage.fastAsk"))),
    radioBox,
    h("div", { class: "row" }, confirmBtn, cancelBtn),
  );
  const fastBtn = h("button", { type: "button", class: "bigbtn danger fast", "aria-expanded": "false" }, h("span", { "aria-hidden": "true", class: "ico" }, "⛔"), h("span", {}, t("triage.fast")));
  const closeFast = () => {
    fastPanel.hidden = true;
    fastBtn.setAttribute("aria-expanded", "false");
    radios.forEach((r) => (r.checked = false));
    confirmBtn.disabled = true;
  };
  fastBtn.addEventListener("click", () => {
    if (!fastPanel.hidden) return closeFast();
    fastPanel.hidden = false;
    fastBtn.setAttribute("aria-expanded", "true");
    radios[0]!.focus();
  });
  cancelBtn.addEventListener("click", () => {
    closeFast();
    fastBtn.focus();
  });
  confirmBtn.addEventListener("click", () => {
    const chosen = radios.find((r) => r.checked)?.value;
    if (!chosen) return;
    try {
      show(evaluateWatchRapidTriage([chosen], { patient_id: st.patientId, assessed_at_ms: Date.now() }));
      closeFast();
    } catch (e) {
      errBox.append(h("p", {}, e instanceof Error ? e.message : String(e)));
    }
  });

  return h("section", {}, h("h1", {}, t("triage.title")), fastBtn, fastPanel, field(t("triage.patient"), patientSel), field(t("triage.category"), catSel), noteBox, formBox, errBox, runBtn, resultBox);
}
