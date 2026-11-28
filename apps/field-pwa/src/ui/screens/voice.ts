import { getLang, t } from "../../i18n";
import { field, h } from "../dom";
import type { Ctx } from "../ctx";
import { getAudio, putAudio } from "../audio_store";
import { buildVoiceHistory, buildVoicePayload, deriveVoiceStage, formatDurationMmSs, recordingUnavailableReason, voiceNoteValid, type HubEnrichmentStatus, type VoiceHistoryItem, type VoiceStageInfo } from "../voice_logic";
import { localizeRiskBand } from "../stage_tracker";
import { uuid } from "../../core/uuid";

async function fetchHubEnrichmentStatus(hubUrl: string): Promise<HubEnrichmentStatus | null> {
  try {
    const base = hubUrl.replace(/\/+$/, "");
    const ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timer = ctrl ? setTimeout(() => ctrl.abort(), 3000) : undefined;
    try {
      const res = await fetch(`${base}/api/v1/enrichment/status`, {
        method: "GET",
        headers: { Accept: "application/json" },
        ...(ctrl ? { signal: ctrl.signal } : {}),
      });
      if (!res.ok) return null;
      const data = (await res.json()) as unknown;
      return data && typeof data === "object" ? (data as HubEnrichmentStatus) : null;
    } finally {
      if (timer !== undefined) clearTimeout(timer);
    }
  } catch {
    return null;
  }
}

function stageLabelFor(item: VoiceHistoryItem, info: VoiceStageInfo): string {
  switch (info.stage) {
    case "completed":
      return t("voice.statusCompleted");
    case "hub_processing":
      if (info.hubSubStage === "transcribing_audio") return t("voice.stageTranscribing");
      if (info.hubSubStage === "structuring_note") return t("voice.stageStructuring");
      if (info.hubSubStage === "scoring_risk") return t("voice.stageScoring");
      return t("voice.stageProcessing");
    case "queued_on_hub":
      return t("voice.stageQueued");
    case "uploading_audio":
      return item.blobKey ? t("voice.stageUploadingAudio") : t("voice.stageSyncingNote");
    case "waiting_connection":
      return info.isHeldClip ? t("voice.stageWaitingHeld") : t("voice.stageWaiting");
  }
}

export async function voice(ctx: Ctx, params: string[] = []): Promise<HTMLElement> {
  const [patients, allEvents] = await Promise.all([ctx.store.listPatients(), ctx.store.getAllEvents()]);
  const presetPid = params[0] ?? "";
  const pSel = h(
    "select",
    { name: "patient" },
    h("option", { value: "" }, t("triage.anon")),
    patients.map((p) => h("option", { value: p.patient_id, selected: p.patient_id === presetPid }, p.full_name)),
  );
  const hint = h("textarea", { name: "hint", rows: 4, maxlength: 2000 });
  const status = h("p", { role: "status", "aria-live": "polite" });
  const player = h("audio", { controls: true, hidden: true });
  let blob: Blob | null = null;
  let startedAt = 0;
  let durationMs = 0;
  let rec: MediaRecorder | null = null;
  let stream: MediaStream | null = null;
  let previewUrl: string | null = null;
  let tick: ReturnType<typeof setInterval> | undefined;
  let torn = false;
  const timerEl = h("span", { class: "rec-timer", "aria-label": t("voice.elapsed"), hidden: true }, "00:00");
  const discardBtn = h("button", { type: "button", hidden: true, onclick: () => discard() }, t("voice.discard"));

  const stopTimer = () => {
    clearInterval(tick);
    tick = undefined;
  };
  function revokePreview() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    player.removeAttribute("src");
    player.hidden = true;
    discardBtn.hidden = true;
  }
  function discard() {
    revokePreview();
    blob = null;
    durationMs = 0;
    status.className = "muted";
    status.textContent = t("voice.discarded");
  }

  const recBtn = h("button", { type: "button", class: "bigbtn danger", onclick: () => void toggle() }, t("voice.start"));
  const saveBtn = h("button", { type: "button", class: "primary", onclick: () => void save() }, t("voice.save"));

  async function toggle() {
    if (rec && rec.state === "recording") {
      rec.stop();
      return;
    }
    try {
      revokePreview();
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream = s;
      const chunks: Blob[] = [];
      rec = new MediaRecorder(s);
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = () => {
        s.getTracks().forEach((tr) => tr.stop());
        stopTimer();
        if (torn) return;
        durationMs = Date.now() - startedAt;
        blob = new Blob(chunks, { type: rec?.mimeType || "audio/webm" });
        revokePreview();
        previewUrl = URL.createObjectURL(blob);
        player.src = previewUrl;
        player.hidden = false;
        discardBtn.hidden = false;
        recBtn.textContent = t("voice.start");
        status.textContent = t("voice.recorded");
      };
      startedAt = Date.now();
      rec.start();
      timerEl.textContent = "00:00";
      timerEl.hidden = false;
      tick = setInterval(() => {
        if (!root.isConnected) return teardown(); // same-route rerender (e.g. language toggle) left us detached
        timerEl.textContent = formatDurationMmSs(Date.now() - startedAt);
      }, 500);
      recBtn.textContent = t("voice.stop");
      status.textContent = t("voice.recording");
    } catch {
      stopTimer();
      status.textContent = t("voice.denied");
      status.className = "error";
    }
  }

  async function save() {
    if (saveBtn.disabled) return;
    const key = blob ? `vn-${uuid()}` : null;
    const payload = buildVoicePayload({ hint: hint.value, language: getLang(), blobKey: key, mime: blob?.type ?? null, durationMs });
    if (!voiceNoteValid(payload)) {
      status.className = "error";
      status.textContent = t("voice.empty");
      return;
    }
    saveBtn.disabled = true;
    try {
      if (blob && key) await putAudio(key, blob); // local blob first, then the event
      await ctx.engine.enqueue({
        event_type: "VOICE_NOTE_RECORDED",
        patient_id: pSel.value || null,
        enrichment_state: "PENDING",
        payload: { ...payload },
      });
      if (navigator.onLine) void ctx.engine.syncNow();
      else ctx.syncSoon();
      status.className = "ok";
      status.textContent = t("voice.saved");
      blob = null;
      hint.value = "";
      revokePreview();
      durationMs = 0;
      await scheduleDraw();
      historyBox.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
      const firstCard = historyBox.querySelector("li.card") as HTMLElement | null;
      firstCard?.classList.add("voice-card-new");
    } catch (e) {
      status.className = "error";
      status.textContent = `${t("triage.saveFail")} ${String(e)}`;
    } finally {
      saveBtn.disabled = false;
    }
  }

  const historyBox = h("div", { class: "voice-history" });
  const SEV_KEY = { RED_EMERGENCY: "sev.red", YELLOW_PHC: "sev.yellow", GREEN_HOME: "sev.green" } as const;
  const activeUrls: string[] = [];
  let hubStatus: HubEnrichmentStatus | null = null;
  let hasPendingNotes = false;
  let drawInFlight = false;
  let drawQueued = false;

  async function drawHistory() {
    if (torn) return;
    const [latestPatients, latestEvents, pendingEvents] = await Promise.all([
      ctx.store.listPatients(),
      ctx.store.getAllEvents(),
      ctx.store.getPendingEvents(),
    ]);
    if (torn) return;
    while (activeUrls.length) URL.revokeObjectURL(activeUrls.pop()!);
    const outboxIds = new Set(pendingEvents.map((e) => e.event_id));
    const items = buildVoiceHistory(latestEvents, latestPatients);
    hasPendingNotes = items.some((item) => item.status !== "COMPLETED");
    if (items.length === 0) {
      historyBox.replaceChildren(h("p", { class: "muted" }, t("voice.historyEmpty")));
      return;
    }
    const loc = getLang() === "hi" ? "hi-IN" : getLang() === "kn" ? "kn-IN" : getLang() === "ta" ? "ta-IN" : "en-IN";
    const isOnline = typeof navigator === "undefined" ? true : navigator.onLine;
    const listItems = await Promise.all(
      items.map(async (item) => {
        let localAudioEl: HTMLElement | null = null;
        if (item.blobKey) {
          try {
            const localBlob = await getAudio(item.blobKey);
            if (localBlob && !torn) {
              const u = URL.createObjectURL(localBlob);
              activeUrls.push(u);
              localAudioEl = h("audio", { controls: true, src: u });
            }
          } catch {
            // Local blob may have been cleared or unavailable.
          }
        }
        const stageInfo = deriveVoiceStage(item, {
          outboxIds,
          isOnline,
          syncStatus: ctx.engine.status,
          syncPhase: ctx.engine.syncPhase,
          heldBlobKeys: ctx.engine.heldBlobKeys,
          uploadingBlobKeys: ctx.engine.uploadingBlobKeys,
          hubStatus,
        });
        const stageLabel = stageLabelFor(item, stageInfo);
        const stepPill = h(
          "span",
          { class: `voice-stage-pill stage-${stageInfo.stage}` },
          t("voice.stageStep", { step: String(stageInfo.step), total: String(stageInfo.totalSteps) }),
        );
        const progressTrack = h(
          "div",
          {
            class: "voice-progress-track",
            role: "progressbar",
            "aria-valuenow": String(stageInfo.step),
            "aria-valuemin": "1",
            "aria-valuemax": String(stageInfo.totalSteps),
            "aria-label": stageLabel,
          },
          h("div", {
            class: `voice-progress-fill stage-${stageInfo.stage}`,
            style: `width: ${(stageInfo.step / stageInfo.totalSteps) * 100}%`,
          }),
        );
        const metaLine = `${item.patientName ?? t("triage.anon")} · ${new Date(item.recordedAtMs).toLocaleString(loc)}${item.durationMs > 0 ? ` · ${formatDurationMmSs(item.durationMs)}` : ""}`;
        return h(
          "li",
          { class: `card ${item.severity ? `sev-${item.severity}` : ""}` },
          h(
            "div",
            { class: "voice-card-head" },
            h("strong", {}, stageLabel),
            stepPill,
            item.severity ? h("span", { class: `sevbadge sev-${item.severity}` }, t(SEV_KEY[item.severity])) : null,
          ),
          progressTrack,
          h("p", { class: "muted" }, metaLine),
          item.transcriptHint ? h("p", {}, item.transcriptHint) : null,
          localAudioEl,
          item.transcript ? h("p", {}, h("strong", {}, `${t("voice.transcript")}: `), item.transcript) : null,
          item.symptoms.length ? h("p", {}, h("strong", {}, `${t("voice.symptoms")}: `), item.symptoms.join(", ")) : null,
          item.riskBand !== null && item.riskScore !== null
            ? h("p", { class: "muted" }, t("voice.riskScore", { band: localizeRiskBand(item.riskBand), score: item.riskScore.toFixed(2) }))
            : null,
          item.followUp ? h("p", {}, item.followUp) : null,
        );
      }),
    );
    if (!torn) historyBox.replaceChildren(h("ul", { class: "list" }, listItems));
  }

  async function scheduleDraw() {
    if (torn) return;
    if (drawInFlight) {
      drawQueued = true;
      return;
    }
    drawInFlight = true;
    try {
      do {
        drawQueued = false;
        await drawHistory();
      } while (drawQueued && !torn);
    } finally {
      drawInFlight = false;
    }
  }

  void scheduleDraw().then(async () => {
    if (torn || !hasPendingNotes) return;
    const online = typeof navigator === "undefined" ? true : navigator.onLine;
    if (!online) return;
    hubStatus = await fetchHubEnrichmentStatus(ctx.engine.hubUrl);
    await scheduleDraw();
  });

  const unsubs = [
    ctx.engine.events.on("status", () => void scheduleDraw()),
    ctx.engine.events.on("enrichment", () => void scheduleDraw()),
    ctx.engine.events.on("cards", () => void scheduleDraw()),
  ];
  const onNet = () => void scheduleDraw();
  window.addEventListener("online", onNet);
  window.addEventListener("offline", onNet);

  const pollTimer = setInterval(() => {
    if (torn || !root.isConnected) {
      teardown();
      return;
    }
    const online = typeof navigator === "undefined" ? true : navigator.onLine;
    if (!hasPendingNotes || !online) return;
    void (async () => {
      hubStatus = await fetchHubEnrichmentStatus(ctx.engine.hubUrl);
      await scheduleDraw();
      if (!torn && hasPendingNotes && online) {
        void ctx.engine.syncNow();
      }
    })();
  }, 4000);

  // Leaving the screen or the page: stop the mic, timer, polling, listeners and preview URL.
  const teardown = () => {
    window.removeEventListener("pagehide", teardown);
    window.removeEventListener("hashchange", teardown);
    window.removeEventListener("online", onNet);
    window.removeEventListener("offline", onNet);
    clearInterval(pollTimer);
    for (const u of unsubs) u();
    torn = true;
    stopTimer();
    if (rec?.state === "recording") rec.stop();
    stream?.getTracks().forEach((tr) => tr.stop());
    revokePreview();
    while (activeUrls.length) URL.revokeObjectURL(activeUrls.pop()!);
  };
  window.addEventListener("pagehide", teardown);
  window.addEventListener("hashchange", teardown);

  const reason = recordingUnavailableReason();
  const root = h(
    "section",
    {},
    h("h1", {}, t("voice.title")),
    field(t("triage.patient"), pSel),
    reason === "insecure_context"
      ? h("p", { class: "muted" }, t("voice.insecureContext"))
      : reason === "unsupported"
        ? h("p", { class: "muted" }, t("voice.unsupported"))
        : h("div", {}, recBtn, " ", timerEl),
    h("div", { class: "voice-actions" }, player, discardBtn),
    field(t("voice.hint"), hint, t("voice.hintNote")),
    saveBtn,
    status,
    h("h2", {}, t("voice.historyTitle")),
    historyBox,
  );
  // Suppress unused warning when allEvents was preloaded; drawHistory refreshes live.
  void allEvents;
  return root;
}
