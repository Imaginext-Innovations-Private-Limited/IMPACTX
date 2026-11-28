import { t, getLang } from "../../i18n";
import { checkbox, field, h, numberInput } from "../dom";
import type { Ctx } from "../ctx";
import { BASELINE_SYMPTOM_TAGS, ageFromDob, buildPatient, type RegErr, type RegisterForm } from "../register_logic";
import { formatIntakeReasoning, renderStageTracker } from "../stage_tracker";
import type { PatientSex } from "../../../../../packages/contracts/ts/index";

const ERR_KEY: Record<RegErr, Parameters<typeof t>[0]> = {
  name: "reg.err.name",
  village: "reg.err.village",
  age_or_dob: "reg.err.ageOrDob",
  dob: "reg.err.dob",
  age: "reg.err.age",
  preg_sex: "reg.err.pregSex",
  weeks: "reg.err.weeks",
};

export function register(ctx: Ctx): HTMLElement {
  const name = h("input", { type: "text", name: "full_name", autocomplete: "off", required: true, maxlength: 200 });
  const sex = h(
    "select",
    { name: "sex" },
    (["F", "M", "O", "U"] as PatientSex[]).map((s) => h("option", { value: s }, t(`sex.${s}` as const))),
  );
  const dob = h("input", { type: "date", name: "dob", max: new Date().toISOString().slice(0, 10) });
  const age = numberInput("age_months", 0, 1500);
  const village = h("input", { type: "text", name: "village_id", required: true, maxlength: 128 });
  const hh = h("input", { type: "text", name: "household_id", maxlength: 128 });
  const weeks = numberInput("gestational_weeks", 0, 45);
  const weeksField = field(t("reg.weeks"), weeks);
  weeksField.hidden = true;
  const preg = checkbox(t("reg.pregnant"), "is_pregnant", false, (c) => (weeksField.hidden = !c));
  const pregInput = preg.querySelector("input") as HTMLInputElement;
  const syncSex = () => {
    preg.hidden = sex.value !== "F";
    if (preg.hidden) pregInput.checked = false;
    if (!pregInput.checked) {
      weeksField.hidden = true;
      weeks.value = "";
    }
  };
  sex.addEventListener("change", syncSex);
  const unitSel = h("select", { name: "age_unit" }, h("option", { value: "months" }, t("reg.unitMonths")), h("option", { value: "years" }, t("reg.unitYears")));
  const ageField = field(t("reg.age"), age, t("reg.ageHint"));
  const syncUnit = () => {
    const years = unitSel.value === "years";
    age.max = years ? "125" : "1500";
    ageField.querySelector("small")!.textContent = t(years ? "reg.ageHintYears" : "reg.ageHint");
  };
  unitSel.addEventListener("change", syncUnit);
  const syncAgeFromDob = () => {
    const derived = ageFromDob(dob.value);
    if (!derived) return;
    unitSel.value = derived.unit;
    syncUnit();
    age.value = String(derived.value);
  };
  dob.addEventListener("input", syncAgeFromDob);
  dob.addEventListener("change", syncAgeFromDob);
  const selectedSymptoms = new Set<string>();
  const otherSymptoms = h("input", { type: "text", name: "other_symptoms", maxlength: 500 });
  const clinicalNotes = h("textarea", { name: "clinical_notes", rows: 2, maxlength: 1000 });
  const notesSection = h(
    "fieldset",
    {},
    h("legend", {}, t("reg.notesSection")),
    BASELINE_SYMPTOM_TAGS.map((tag) =>
      checkbox(t(`reg.sym.${tag}` as const), `init_${tag}`, false, (c) => {
        if (c) selectedSymptoms.add(tag);
        else selectedSymptoms.delete(tag);
      }),
    ),
    field(t("reg.otherSymptoms"), otherSymptoms),
    field(t("reg.clinicalNotes"), clinicalNotes),
  );
  const errors = h("div", { class: "error", role: "alert", "aria-live": "assertive" });
  const ok = h("div", { class: "ok", role: "status" });

  const submitBtn = h("button", { type: "submit", class: "primary" }, t("reg.save"));
  const form = h(
    "form",
    { novalidate: true },
    field(t("reg.name"), name),
    field(t("reg.sex"), sex),
    field(t("reg.dob"), dob),
    h("div", { class: "agerow" }, ageField, field(t("reg.ageUnit"), unitSel)),
    field(t("reg.village"), village),
    preg,
    weeksField,
    h("details", { class: "optional-group" }, h("summary", {}, t("reg.optionalDetails")), field(t("reg.household"), hh), notesSection),
    errors,
    submitBtn,
    ok,
  );
  syncSex();
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (submitBtn.disabled) return;
    const f: RegisterForm = {
      full_name: name.value,
      sex: sex.value as PatientSex,
      dob: dob.value,
      age_months: age.value,
      age_unit: unitSel.value as "months" | "years",
      village_id: village.value,
      household_id: hh.value,
      is_pregnant: pregInput.checked,
      gestational_weeks: weeks.value,
      preferred_language: getLang(),
      initial_symptoms: [...selectedSymptoms],
      other_symptoms: otherSymptoms.value,
      clinical_notes: clinicalNotes.value,
    };
    const r = buildPatient(f, ctx.nodeId);
    errors.replaceChildren();
    ok.replaceChildren();
    if (!r.ok) {
      errors.append(h("ul", {}, r.errors.map((e) => h("li", {}, t(e === "age" && unitSel.value === "years" ? "reg.err.ageYears" : ERR_KEY[e])))));
      return;
    }
    const p = r.patient;
    submitBtn.disabled = true;
    // Persist locally first; UI never awaits the network.
    void ctx.engine
      .enqueue({ event_type: "PATIENT_REGISTERED", patient_id: p.patient_id, payload: { ...p } })
      .then(() => {
        ctx.syncSoon();
        ok.append(
          h("p", {}, t("reg.saved", { name: p.full_name })),
          renderStageTracker({
            completedSteps: 1,
            activeStep: 2,
            headline: t("reg.stageHeadline"),
            reasoningNode: h(
              "div",
              { class: "provenance-box", "data-provenance": "intake" },
              h("p", { class: "prov-line" }, h("strong", {}, `${t("prov.intakeTitle")}: `), formatIntakeReasoning(p)),
            ),
            nextCue: t("reg.stageNext"),
            actions: [
              h("a", { class: "bigbtn danger", href: `#/triage/${encodeURIComponent(p.patient_id)}` }, t("reg.nextCheck")),
              h("a", { class: "bigbtn", href: `#/voice/${encodeURIComponent(p.patient_id)}` }, t("reg.nextVoice")),
              h("a", { class: "bigbtn", href: `#/vaccines/${encodeURIComponent(p.patient_id)}` }, t("nav.vaccines")),
            ],
          }),
          h("a", { class: "bigbtn", href: "#/register", onclick: () => ctx.rerender() }, t("reg.another")),
        );
        form.reset();
        selectedSymptoms.clear();
        syncSex();
        syncUnit();
      })
      .catch((e) => errors.append(h("p", {}, String(e))))
      .finally(() => {
        submitBtn.disabled = false;
      });
  });
  return h("section", {}, h("h1", {}, t("reg.title")), form);
}
