import type { ActionCard } from "../../../../../packages/contracts/ts/index";
import { getLang, t } from "../../i18n";
import { field, h } from "../dom";
import type { Ctx } from "../ctx";
import { heldClipsFromDetail, runSync } from "../app_state";
import { clearHubUrl, getAutoHubOrigin, getHubUrl, getLastSync, isValidHubUrl, normalizeHubUrl, setHubUrl } from "../settings";
import { ackPayload, bindLiveCount, buildCrdtNodeProof, cardPatientLabel, parseSyncFailureDetail, sortCards } from "../sync_logic";
import { extractClinicInsights, localizeRiskBand, type ClinicInsight } from "../stage_tracker";

export async function syncPanel(ctx: Ctx): Promise<HTMLElement> {
  const [pending, cards, patients, allEvents] = await Promise.all([
    ctx.engine.pendingCount(),
    ctx.store.listActionCards(),
    ctx.store.listPatients(),
    ctx.store.getAllEvents(),
  ]);
  const byId = new Map(patients.map((p) => [p.patient_id, p]));
  const proof = buildCrdtNodeProof(ctx.nodeId, allEvents, pending, ctx.engine.status);
  const formatSyncFailure = (detail: string): string => {
    const parsed = parseSyncFailureDetail(detail);
    switch (parsed.kind) {
      case "device_offline":
        return t("sync.errOffline");
      case "unreachable":
        return t("sync.errUnreachable");
      case "http":
        return t("sync.errHttp", { code: parsed.code });
      case "other":
        return t("sync.fail", { s: parsed.detail });
    }
  };
  const loc = getLang() === "hi" ? "hi-IN" : getLang() === "kn" ? "kn-IN" : getLang() === "ta" ? "ta-IN" : "en-IN";
  const formatLastLine = (rec: { at: number; ok: boolean; detail: string } | null): string => {
    if (!rec) return t("sync.never");
    const h = heldClipsFromDetail(rec.detail);
    const txt = rec.ok ? t("sync.ok") : h ? t("sync.clipsWaiting", { n: h }) : formatSyncFailure(rec.detail);
    return `${t("sync.last")}: ${new Date(rec.at).toLocaleString(loc)} — ${txt}`;
  };
  const last = getLastSync();
  const held = last ? heldClipsFromDetail(last.detail) : 0;
  const lastText = !last ? "" : last.ok ? t("sync.ok") : held ? t("sync.clipsWaiting", { n: held }) : formatSyncFailure(last.detail);
  const url = h("input", { type: "url", name: "hub", value: getHubUrl(), inputmode: "url", autocapitalize: "off" });
  const auto = getAutoHubOrigin();
  const msg = h("p", { role: "status", "aria-live": "polite" });
  const urlMsg = h("p", { role: "status", "aria-live": "polite" });
  const isOfflineNow = typeof navigator !== "undefined" && !navigator.onLine;
  if (isOfflineNow) {
    msg.className = "error";
    msg.textContent = t("sync.errOffline");
  } else if (last && !last.ok && !held) {
    msg.className = "error";
    msg.textContent = lastText;
  }
  const syncPipeline = h("div", { class: "sync-pipeline", role: "status", "aria-live": "polite", hidden: true });
  const SYNC_STAGES = ["sync.stageCheck", "sync.stageUpload", "sync.stageAnalyze", "sync.stageDone"] as const;
  const setSyncStep = (step: 1 | 2 | 3 | 4) => {
    syncPipeline.hidden = false;
    syncPipeline.replaceChildren(
      h(
        "ol",
        { class: "stage-steps" },
        SYNC_STAGES.map((key, idx) => {
          const n = idx + 1;
          const done = n < step || step === 4;
          const active = n === step && step < 4;
          const cls = done ? "stage-step done" : active ? "stage-step active" : "stage-step";
          return h("li", { class: cls }, h("span", { "aria-hidden": "true" }, done ? "✔ " : active ? "● " : "○ "), t(key));
        }),
      ),
      h(
        "div",
        { class: "voice-progress-track", role: "progressbar", "aria-valuenow": String(step), "aria-valuemin": "1", "aria-valuemax": "4" },
        h("div", { class: `voice-progress-fill stage-${step === 4 ? "completed" : step === 3 ? "hub_processing" : "uploading_audio"}`, style: `width: ${(step / 4) * 100}%` }),
      ),
    );
  };

  let hubDetails: HTMLDetailsElement;
  const saveUrl = (showSaved = false) => {
    urlMsg.className = "";
    urlMsg.textContent = "";
    const norm = normalizeHubUrl(url.value);
    if (norm === "" || norm === auto) {
      // Empty (or the automatic value itself): drop the override so the address keeps tracking the page origin.
      clearHubUrl();
      url.value = getHubUrl();
      ctx.engine.hubUrl = url.value;
      if (showSaved) {
        urlMsg.className = "ok";
        urlMsg.textContent = t("sync.urlSaved", { u: url.value });
      }
      return true;
    }
    if (!isValidHubUrl(norm)) {
      hubDetails.open = true;
      msg.className = "error";
      msg.textContent = t("sync.badUrl");
      urlMsg.className = "error";
      urlMsg.textContent = t("sync.badUrl");
      return false;
    }
    setHubUrl(norm);
    url.value = getHubUrl();
    ctx.engine.hubUrl = url.value;
    if (showSaved) {
      urlMsg.className = "ok";
      urlMsg.textContent = t("sync.urlSaved", { u: url.value });
    }
    return true;
  };
  url.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      saveUrl(true);
    }
  });
  const saveUrlBtn = h("button", { type: "button", onclick: () => saveUrl(true) }, t("sync.saveUrl"));
  const lastEl = h("p", { class: "muted" }, formatLastLine(last));

  const alreadySyncing = ctx.engine.status === "syncing";
  const btn = h(
    "button",
    {
      type: "button",
      class: "primary",
      disabled: alreadySyncing,
      ...(alreadySyncing ? { "aria-busy": "true" } : {}),
      onclick: async () => {
        if (btn.disabled) return;
        if (!saveUrl()) return;
        if (typeof navigator !== "undefined" && !navigator.onLine) {
          msg.className = "error";
          msg.textContent = t("sync.errOffline");
          return;
        }
        btn.disabled = true;
        btn.textContent = t("sync.running");
        btn.setAttribute("aria-busy", "true");
        msg.className = "muted";
        msg.textContent = t("sync.running");
        try {
          setSyncStep(1);
          await Promise.resolve();
          setSyncStep(2);
          await runSync(ctx.engine);
          if (ctx.engine.status === "idle") {
            const stillPending = await ctx.engine.pendingEnrichmentCount();
            if (stillPending > 0) {
              setSyncStep(3);
              await new Promise((r) => setTimeout(r, 700));
              await runSync(ctx.engine);
            }
            setSyncStep(4);
            ctx.rerender();
            return;
          }
          const updatedLast = getLastSync();
          const updatedHeld = updatedLast ? heldClipsFromDetail(updatedLast.detail) : 0;
          syncPipeline.hidden = true;
          msg.className = updatedHeld ? "muted" : "error";
          msg.textContent = updatedLast
            ? updatedHeld
              ? t("sync.clipsWaiting", { n: updatedHeld })
              : formatSyncFailure(updatedLast.detail)
            : t("sync.errUnreachable");
          lastEl.textContent = formatLastLine(updatedLast);
          refreshProof();
        } finally {
          btn.disabled = false;
          btn.textContent = t("sync.now");
          btn.removeAttribute("aria-busy");
        }
      },
    },
    alreadySyncing ? t("sync.running") : t("sync.now"),
  );

  const insights = extractClinicInsights(allEvents, patients);
  const insightCard = (ins: ClinicInsight) => {
    const riskCls = ins.riskPct >= 65 ? "risk-high" : ins.riskPct >= 35 ? "risk-mod" : "risk-low";
    const loc = getLang() === "hi" ? "hi-IN" : getLang() === "kn" ? "kn-IN" : getLang() === "ta" ? "ta-IN" : "en-IN";
    return h(
      "li",
      { class: `card insight-card ${riskCls}`, "data-provenance": "laptop-ml" },
      h(
        "div",
        { class: "insight-head" },
        h("strong", {}, ins.patientName ?? t("triage.anon")),
        h("span", { class: "stage-pill stage-ai" }, t("prov.stage3Badge")),
        h("span", { class: `risk-pill ${riskCls}` }, `${t("insights.riskScore", { pct: ins.riskPct })}${ins.riskBand ? ` · ${localizeRiskBand(ins.riskBand)}` : ""}`),
      ),
      h("p", { class: "muted" }, new Date(ins.recordedAtMs).toLocaleString(loc)),
      h(
        "div",
        { class: "provenance-box" },
        h("p", { class: "prov-line" }, h("strong", {}, `${t("prov.whoFloorTitle")}: `), h("span", { lang: "en" }, ins.clinicalProtocol)),
        ins.matchedRuleIds.length
          ? h(
              "div",
              { class: "proof-rules" },
              h("span", { class: "proof-label" }, `${t("proof.matchedRules")}:`),
              ...ins.matchedRuleIds.map((id) => h("code", { class: "rule-badge", lang: "en" }, id)),
            )
          : null,
        ins.clinicalParameters ? h("p", { class: "prov-line muted" }, h("strong", {}, `${t("prov.paramsLabel")}: `), ins.clinicalParameters) : null,
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
      ins.recommendedFollowUp
        ? h("p", { class: "insight-next" }, h("strong", {}, `${t("insights.nextStep")}: `), ins.recommendedFollowUp)
        : null,
    );
  };

  const card = (c: ActionCard) => {
    const lbl = cardPatientLabel(c.patient_id, byId);
    return h(
      "li",
      { class: `card prio-${c.priority}` },
      h("strong", {}, `${t(`prio.${c.priority}` as const)} · ${c.title}`),
      lbl ? h("p", { class: "patient-chip" }, lbl.village ? t("sync.cardPatient", { name: lbl.name, v: lbl.village }) : t("sync.cardPatientId", { id: lbl.name })) : null,
      h("p", {}, c.summary),
      h("ol", {}, c.action_steps.map((s) => h("li", {}, s))),
      c.status === "OPEN"
        ? (() => {
            const ackBtn = h(
              "button",
              {
                type: "button",
                onclick: () => {
                  if (ackBtn.disabled) return;
                  ackBtn.disabled = true;
                  ackBtn.textContent = t("triage.saving");
                  void ctx.engine
                    .enqueue({ event_type: "ACTION_CARD_ISSUED", patient_id: c.patient_id, payload: ackPayload(c) })
                    .then(() => {
                      ctx.syncSoon();
                      ackBtn.replaceWith(h("span", { class: "ok" }, "✔ ", t("cards.acked")));
                      msg.className = "ok";
                      msg.textContent = t("cards.ackSaved");
                    })
                    .catch((e) => {
                      ackBtn.disabled = false;
                      ackBtn.textContent = t("cards.ack");
                      msg.className = "error";
                      msg.textContent = `${t("triage.saveFail")} ${String(e)}`;
                    });
                },
              },
              t("cards.ack"),
            );
            return ackBtn;
          })()
        : h("span", { class: "muted" }, t("cards.acked")),
    );
  };

  let seen = false;
  const born = Date.now();
  const pendingEl = h("span", { class: "pending-count" }, String(pending));
  const hlcEl = h("code", { class: "hlc-code", lang: "en" }, proof.latestHlc);
  const eventCountEl = h("strong", {}, String(proof.eventCount));
  const syncStateEl = h("strong", {}, t(`proof.state.${proof.status}` as const));
  const proofCard = h(
    "section",
    { class: "proof-card", "data-proof": "crdt-node", "aria-label": t("proof.crdtTitle") },
    h("h2", {}, t("proof.crdtTitle")),
    h(
      "dl",
      { class: "proof-grid" },
      h("dt", {}, t("proof.nodeId")),
      h("dd", {}, h("code", { lang: "en" }, proof.nodeId)),
      h("dt", {}, t("proof.latestHlc")),
      h("dd", {}, hlcEl),
      h("dt", {}, t("proof.eventCount")),
      h("dd", {}, eventCountEl),
      h("dt", {}, t("proof.syncState")),
      h("dd", {}, syncStateEl),
    ),
  );
  hubDetails = h(
    "details",
    { class: "optional-group" },
    h("summary", {}, t("sync.hubSettings")),
    field(t("sync.hubUrl"), h("div", { class: "row" }, url, saveUrlBtn), auto ? t("sync.hubAuto", { u: auto }) : t("sync.hubHint")),
    urlMsg,
    proofCard,
  );
  const root = h(
    "section",
    {},
    h("h1", {}, t("sync.title")),
    btn,
    syncPipeline,
    msg,
    h("p", {}, `${t("home.pendingSync")}: `, pendingEl),
    lastEl,
    h("h2", {}, t("cards.title")),
    cards.length ? h("ul", { class: "list" }, sortCards(cards).map(card)) : h("p", { class: "muted" }, t("cards.none")),
    h("section", { "data-section": "clinic-insights" }, h("h2", {}, t("insights.title")), insights.length ? h("ul", { class: "list" }, insights.map(insightCard)) : h("p", { class: "muted" }, t("insights.none"))),
    hubDetails,
  );
  const refreshProof = () => {
    void ctx.store.getAllEvents().then((evts) => {
      const next = buildCrdtNodeProof(ctx.nodeId, evts, Number(pendingEl.textContent || 0), ctx.engine.status);
      hlcEl.textContent = next.latestHlc;
      eventCountEl.textContent = String(next.eventCount);
      syncStateEl.textContent = t(`proof.state.${next.status}` as const);
    });
  };
  // Live count + HLC proof in place (no remount, so `msg` survives); self-unsubscribes once this screen is gone.
  bindLiveCount(
    [
      (fn) => ctx.engine.events.on("status", (s) => fn(s.pendingCount)),
      (fn) => ctx.engine.events.on("enrichment", () => void ctx.engine.pendingCount().then(fn)),
    ],
    // Not yet mounted: keep listening up to 5s (rerender gap); once mounted then removed, or never mounted, drop.
    () => {
      if (root.isConnected) { seen = true; return true; }
      return !seen && Date.now() - born < 5000;
    },
    (n) => {
      pendingEl.textContent = String(n);
      refreshProof();
    },
  );
  return root;
}
