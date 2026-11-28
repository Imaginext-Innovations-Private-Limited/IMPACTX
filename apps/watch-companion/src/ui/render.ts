/**
 * Circular 360x360 Watch DOM Renderer.
 * Renders pure state from `WatchUiController` and dispatches user actions.
 */

import { t } from "../i18n/index";
import { isVoiceRecordingSupported, WatchVoiceRecorder } from "./recorder";
import type { WatchTab, WatchUiController } from "./state";

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function mountWatchUi(root: HTMLElement, controller: WatchUiController): () => void {
  const recorder = new WatchVoiceRecorder();
  let recordingSeconds = 0;
  let recordingTimer: ReturnType<typeof setInterval> | null = null;
  let activeRecBtn: HTMLButtonElement | null = null;
  let micError = false;
  let recBusy = false;
  let hubDetailsOpen = false;

  const renderSyncFeedback = (): HTMLElement | null => {
    const lastSync = controller.getLastSyncResult();
    if (!lastSync) {
      return null;
    }
    if (lastSync.ok) {
      return el(
        "div",
        "status-ok",
        t("sync.success", {
          sent: lastSync.ackedCount,
          received: lastSync.appliedCount,
        }),
      );
    }
    const detail = lastSync.reason.trim();
    const message =
      detail.length > 0 && !detail.includes(t("sync.offlineFail"))
        ? `${t("sync.offlineFail")} — ${detail}`
        : t("sync.offlineFail");
    return el("div", "status-warn", message);
  };

  const formatRecLabel = (recording: boolean): string =>
    recording
      ? `${t("sos.recordStop")} · ${t("sos.recording", { sec: recordingSeconds })}`
      : t("sos.recordStart");

  const clearRecordingTimer = () => {
    if (recordingTimer !== null) {
      clearInterval(recordingTimer);
      recordingTimer = null;
    }
    recordingSeconds = 0;
  };

  const renderHeader = (): HTMLElement => {
    const header = el("div", "watch-top-bar");
    const mode = controller.getMode();

    const modeBtn = el(
      "button",
      `pill mode-pill ${mode === "CHW_COMPANION" ? "mode-chw" : "mode-family"}`,
      t(mode === "CHW_COMPANION" ? "mode.CHW_COMPANION" : "mode.PATIENT_FAMILY"),
    );
    modeBtn.type = "button";
    modeBtn.id = "mode-toggle";
    modeBtn.setAttribute("data-mode", mode);
    modeBtn.setAttribute("aria-label", t("mode.switchAria"));
    modeBtn.addEventListener("click", () => controller.toggleMode());

    const langBtn = el("button", "pill lang-pill", t("lang.toggle"));
    langBtn.type = "button";
    langBtn.id = "lang-toggle";
    langBtn.setAttribute("data-lang", controller.getLanguage());
    langBtn.setAttribute("aria-label", t("lang.switchAria"));
    langBtn.addEventListener("click", () => controller.toggleLanguage());

    header.append(modeBtn, langBtn);
    return header;
  };

  const renderTabs = (): HTMLElement => {
    const bar = el("nav", "watch-tabs");
    bar.setAttribute("aria-label", t("nav.aria"));
    const mode = controller.getMode();
    const activeTab = controller.getTab();
    const outboxCount = controller.getOutboxCount();

    const tabs: Array<{ id: WatchTab; label: string; badge?: number }> =
      mode === "CHW_COMPANION"
        ? [
            { id: "danger", label: t("tab.danger") },
            { id: "cards", label: t("tab.cards"), badge: controller.getOpenActionCardCount() },
            { id: "sync", label: t("tab.sync"), badge: outboxCount },
          ]
        : [
            { id: "reminders", label: t("tab.reminders"), badge: controller.getReminders().length },
            { id: "sos", label: t("tab.sos") },
            { id: "sync", label: t("tab.sync"), badge: outboxCount },
          ];

    for (const item of tabs) {
      const btn = el("button", `tab-btn${activeTab === item.id ? " active" : ""}`);
      btn.type = "button";
      btn.setAttribute("data-tab", item.id);
      btn.textContent =
        item.badge && item.badge > 0 ? `${item.label} (${item.badge})` : item.label;
      btn.addEventListener("click", () => controller.setTab(item.id));
      bar.append(btn);
    }

    return bar;
  };

  const renderDangerView = (): HTMLElement => {
    const wrap = el("section", "watch-pane");
    const lastTriage = controller.getLastTriage();
    const lang = controller.getLanguage();

    if (lastTriage) {
      const isRed = lastTriage.severity === "RED_EMERGENCY";
      const banner = el("div", `triage-banner ${isRed ? "banner-red" : "banner-green"}`);
      banner.append(
        el("div", "banner-title", t(isRed ? "danger.redTitle" : "danger.greenTitle")),
        el("div", "banner-sub", t(isRed ? "danger.redBanner" : "danger.greenBanner")),
      );

      if (isRed) {
        const call108 = el("a", "action-btn btn-108", t("danger.call108"));
        call108.href = "tel:108";
        banner.append(call108);
      }

      const syncBannerBtn = el(
        "button",
        "action-btn btn-teal",
        controller.getIsSyncing() ? t("sync.syncing") : t("sync.now"),
      );
      syncBannerBtn.type = "button";
      syncBannerBtn.disabled = controller.getIsSyncing();
      syncBannerBtn.addEventListener("click", () => {
        void controller.syncNow();
      });
      banner.append(syncBannerBtn);

      const bannerSyncFeedback = renderSyncFeedback();
      if (bannerSyncFeedback) {
        banner.append(bannerSyncFeedback);
      }

      const resetBtn = el("button", "action-btn btn-secondary", t("danger.reset"));
      resetBtn.type = "button";
      resetBtn.addEventListener("click", () => controller.resetTriage());
      banner.append(resetBtn);
      wrap.append(banner);
      return wrap;
    }

    const catRow = el("div", "cat-row");
    for (const cat of ["PEDIATRIC", "MATERNAL"] as const) {
      const btn = el(
        "button",
        `cat-pill${controller.getDangerCategory() === cat ? " active" : ""}`,
        t(cat === "PEDIATRIC" ? "danger.cat.PEDIATRIC" : "danger.cat.MATERNAL"),
      );
      btn.type = "button";
      btn.addEventListener("click", () => controller.setDangerCategory(cat));
      catRow.append(btn);
    }

    const pidInput = el("input", "watch-input");
    pidInput.type = "text";
    pidInput.placeholder = t("danger.patientId");
    pidInput.value = controller.getPatientIdInput();
    pidInput.addEventListener("input", () => controller.setPatientIdInput(pidInput.value));

    const signs = controller.getDangerSignsForCategory();
    const armedFlag = controller.getPendingConfirmFlag();

    if (armedFlag) {
      const armedSign = signs.find((s) => s.flag === armedFlag);
      const confirmBar = el("div", "confirm-bar");
      const labelText = armedSign
        ? lang === "hi"
          ? armedSign.labelHi
          : lang === "kn"
            ? armedSign.labelKn
            : lang === "ta"
              ? armedSign.labelTa
              : armedSign.labelEn
        : armedFlag;
      confirmBar.append(
        el("div", "confirm-title", t("danger.confirmPrompt")),
        el("div", "confirm-sub", labelText),
      );
      const actions = el("div", "confirm-actions");
      const confirmBtn = el("button", "action-btn btn-red", t("danger.confirmBtn"));
      confirmBtn.type = "button";
      confirmBtn.setAttribute("data-role", "danger-confirm-btn");
      confirmBtn.addEventListener("click", () => controller.confirmArmedDangerSign());

      const cancelBtn = el("button", "action-btn btn-secondary", t("danger.cancelBtn"));
      cancelBtn.type = "button";
      cancelBtn.setAttribute("data-role", "danger-cancel-btn");
      cancelBtn.addEventListener("click", () => controller.cancelArmedDangerSign());

      actions.append(confirmBtn, cancelBtn);
      confirmBar.append(actions);
      wrap.append(confirmBar);
    }

    const list = el("div", "sign-list");
    for (const sign of signs) {
      const btn = el(
        "button",
        `sign-btn${armedFlag === sign.flag ? " armed" : ""}`,
        lang === "hi"
          ? sign.labelHi
          : lang === "kn"
            ? sign.labelKn
            : lang === "ta"
              ? sign.labelTa
              : sign.labelEn,
      );
      btn.type = "button";
      btn.setAttribute("data-flag", sign.flag);
      btn.addEventListener("click", () => controller.armDangerSign(sign.flag));
      list.append(btn);
    }

    const customWrap = el("div", "custom-danger-box");
    const customInput = el("input", "watch-input");
    customInput.type = "text";
    customInput.setAttribute("data-role", "custom-danger-input");
    customInput.placeholder = t("danger.otherPlaceholder");
    customInput.value = controller.getCustomDangerDraft();

    const customWarn = el("div", "status-warn", t("danger.otherRequired"));
    customWarn.hidden = !controller.getCustomDangerError();

    customInput.addEventListener("input", () => {
      controller.setCustomDangerDraft(customInput.value);
      if (customInput.value.trim().length > 0) {
        customWarn.hidden = true;
      }
    });

    const customBtn = el("button", "action-btn btn-amber", t("danger.otherSubmit"));
    customBtn.type = "button";
    customBtn.setAttribute("data-role", "custom-danger-btn");
    customBtn.addEventListener("click", () => controller.submitCustomDangerSign(customInput.value));

    customWrap.append(customInput, customWarn, customBtn);

    const greenBtn = el("button", "action-btn btn-green", t("danger.noneBtn"));
    greenBtn.type = "button";
    greenBtn.addEventListener("click", () => controller.triggerDangerScreen([]));

    const optionalDetails = el("details", "watch-optional");
    if (
      controller.getCustomDangerError() ||
      controller.getCustomDangerDraft().trim().length > 0 ||
      controller.getPatientIdInput().trim().length > 0
    ) {
      optionalDetails.open = true;
    }
    optionalDetails.append(el("summary", undefined, t("danger.optionalSummary")));
    const optionalBody = el("div", "watch-optional-body");
    optionalBody.append(pidInput, customWrap);
    optionalDetails.append(optionalBody);

    wrap.append(catRow, list, greenBtn, optionalDetails);
    return wrap;
  };

  const renderCardsView = (): HTMLElement => {
    const wrap = el("section", "watch-pane");
    const cards = controller.getVisibleActionCards();

    if (cards.length === 0) {
      wrap.append(el("p", "empty-msg", t("cards.empty")));
      return wrap;
    }

    for (const card of cards) {
      const item = el("article", `watch-card prio-${card.priority.toLowerCase()}`);
      const top = el("div", "card-head");
      top.append(
        el("span", `badge badge-${card.priority.toLowerCase()}`, t(`priority.${card.priority}`)),
      );
      if (card.due_by) {
        top.append(el("span", "card-due", t("cards.due", { date: card.due_by })));
      }
      item.append(
        top,
        el("div", "card-title", card.title),
        el("div", "card-summary", card.summary),
      );

      if (card.status === "OPEN") {
        const ackBtn = el("button", "action-btn btn-teal", t("cards.ack"));
        ackBtn.type = "button";
        ackBtn.addEventListener("click", () => controller.acknowledgeCard(card.card_id));
        item.append(ackBtn);
      } else {
        item.append(el("div", "acked-tag", t("cards.acked")));
      }
      wrap.append(item);
    }

    return wrap;
  };

  const renderRemindersView = (): HTMLElement => {
    const wrap = el("section", "watch-pane");
    const reminders = controller.getReminders();

    if (reminders.length === 0) {
      wrap.append(el("p", "empty-msg", t("rem.empty")));
    } else {
      for (const rem of reminders) {
        const item = el("article", `watch-card prio-${rem.priority.toLowerCase()}`);
        const head = el("div", "card-head");
        head.append(
          el("span", `badge badge-${rem.priority.toLowerCase()}`, t(`rem.cat.${rem.category}`)),
        );
        if (rem.dueBy) {
          head.append(el("span", "card-due", t("cards.due", { date: rem.dueBy })));
        }
        item.append(
          head,
          el("div", "card-title", rem.title),
          el("div", "card-summary", rem.message),
        );
        if (rem.sourceCardId && rem.status === "OPEN") {
          const ackBtn = el("button", "action-btn btn-teal", t("cards.ack"));
          ackBtn.type = "button";
          ackBtn.addEventListener("click", () => controller.acknowledgeCard(rem.sourceCardId!));
          item.append(ackBtn);
        } else if (rem.sourceCardId) {
          item.append(el("div", "acked-tag", t("cards.acked")));
        }
        wrap.append(item);
      }
    }

    const sosHint = el("a", "action-btn btn-108 compact-108", t("danger.call108"));
    sosHint.href = "tel:108";
    wrap.append(sosHint);
    return wrap;
  };

  const renderSosView = (): HTMLElement => {
    const wrap = el("section", "watch-pane");
    wrap.append(el("div", "sos-guidance", t("sos.guidance108")));

    const call108 = el("a", "action-btn btn-108", t("danger.call108"));
    call108.href = "tel:108";
    wrap.append(call108);

    const canRecord = isVoiceRecordingSupported();
    if (canRecord && !micError) {
      const recording = recorder.isRecording();
      const recBtn = el(
        "button",
        `action-btn ${recording ? "btn-red" : "btn-amber"}`,
        formatRecLabel(recording),
      );
      recBtn.type = "button";
      recBtn.disabled = recBusy || controller.getIsSubmittingSos();
      recBtn.setAttribute("data-role", "sos-rec-btn");
      activeRecBtn = recBtn;
      recBtn.addEventListener("click", async () => {
        if (recBusy || controller.getIsSubmittingSos()) {
          return;
        }
        recBusy = true;
        recBtn.disabled = true;
        try {
          if (recorder.isRecording()) {
            clearRecordingTimer();
            const result = await recorder.stop();
            await controller.submitSos({
              audioBlob: result?.blob ?? null,
              mimeType: result?.mimeType ?? null,
              durationMs: result?.durationMs ?? 0,
            });
            render();
          } else {
            try {
              await recorder.start();
              recordingSeconds = 0;
              recordingTimer = setInterval(() => {
                recordingSeconds += 1;
                if (activeRecBtn) {
                  activeRecBtn.textContent = formatRecLabel(true);
                }
              }, 1000);
              render();
            } catch {
              clearRecordingTimer();
              micError = true;
              render();
            }
          }
        } finally {
          recBusy = false;
        }
      });
      wrap.append(recBtn);
    } else {
      wrap.append(el("div", "muted-note", t("sos.micUnavailable")));
    }

    const textInput = el("input", "watch-input");
    textInput.type = "text";
    textInput.placeholder = t("sos.textPlaceholder");
    textInput.value = controller.getSosTextDraft();

    const textWarn = el("div", "status-warn", t("sos.textRequired"));
    textWarn.hidden = !controller.getSosTextError();

    textInput.addEventListener("input", () => {
      controller.setSosTextDraft(textInput.value);
      if (textInput.value.trim().length > 0) {
        textWarn.hidden = true;
      }
    });

    const sendTextBtn = el("button", "action-btn btn-amber", t("sos.sendText"));
    sendTextBtn.type = "button";
    sendTextBtn.disabled = controller.getIsSubmittingSos();
    sendTextBtn.addEventListener("click", async () => {
      if (controller.getIsSubmittingSos()) {
        return;
      }
      sendTextBtn.disabled = true;
      await controller.submitTextSos(textInput.value);
    });

    wrap.append(textInput, textWarn, sendTextBtn);

    if (controller.getLastSosEvent()) {
      wrap.append(el("div", "status-ok", t("sos.queued")));
      const syncSosBtn = el(
        "button",
        "action-btn btn-teal",
        controller.getIsSyncing() ? t("sync.syncing") : t("sync.now"),
      );
      syncSosBtn.type = "button";
      syncSosBtn.disabled = controller.getIsSyncing();
      syncSosBtn.addEventListener("click", () => {
        void controller.syncNow();
      });
      wrap.append(syncSosBtn);
      const sosSyncFeedback = renderSyncFeedback();
      if (sosSyncFeedback) {
        wrap.append(sosSyncFeedback);
      }
    }
    return wrap;
  };

  const renderSyncView = (): HTMLElement => {
    const wrap = el("section", "watch-pane");
    const online = typeof navigator === "undefined" ? true : navigator.onLine;
    wrap.append(
      el(
        "div",
        `net-pill ${online ? "net-online" : "net-offline"}`,
        t(online ? "net.online" : "net.offline"),
      ),
    );

    const urlLabel = el("label", "field-label", t("sync.hubLabel"));
    const urlInput = el("input", "watch-input");
    urlInput.type = "text";
    urlInput.inputMode = "url";
    urlInput.setAttribute("data-hub-url", "1");
    urlInput.placeholder = t("sync.hubHint");
    urlInput.value = controller.getHubUrlDraft();
    urlInput.addEventListener("input", () => controller.setHubUrlDraft(urlInput.value));
    urlInput.addEventListener("change", () => controller.setHubUrl(urlInput.value));

    const syncBtn = el(
      "button",
      "action-btn btn-teal",
      controller.getIsSyncing() ? t("sync.syncing") : t("sync.now"),
    );
    syncBtn.type = "button";
    syncBtn.disabled = controller.getIsSyncing();
    syncBtn.addEventListener("click", async () => {
      controller.setHubUrl(urlInput.value);
      await controller.syncNow();
    });

    wrap.append(syncBtn);

    const syncFeedback = renderSyncFeedback();
    if (syncFeedback) {
      wrap.append(syncFeedback);
    }

    const hubUrlError = controller.getHubUrlError();
    const hubDetails = el("details", "watch-optional");
    hubDetails.open = hubDetailsOpen || hubUrlError !== null;
    hubDetails.addEventListener("toggle", () => {
      hubDetailsOpen = hubDetails.open;
    });
    hubDetails.append(el("summary", undefined, t("sync.hubSummary")));
    const hubBody = el("div", "watch-optional-body");
    hubBody.append(urlLabel, urlInput);
    if (hubUrlError) {
      hubBody.append(el("div", "status-warn", hubUrlError));
    }
    hubDetails.append(hubBody);
    wrap.append(hubDetails);

    return wrap;
  };

  const renderFooter = (): HTMLElement =>
    el("div", "watch-footer", t("sync.footer", { count: controller.getOutboxCount() }));

  const render = () => {
    activeRecBtn = null;
    const tab = controller.getTab();
    if (tab !== "sos" && !recorder.isRecording()) {
      clearRecordingTimer();
    }
    root.replaceChildren();
    if (typeof document !== "undefined") {
      document.title = t("app.title");
      document.documentElement.lang = controller.getLanguage();
    }
    const bezel = el("div", "watch-bezel");
    bezel.setAttribute("role", "application");
    bezel.setAttribute("aria-label", t("app.aria"));

    let content: HTMLElement;
    switch (tab) {
      case "danger":
        content = renderDangerView();
        break;
      case "cards":
        content = renderCardsView();
        break;
      case "reminders":
        content = renderRemindersView();
        break;
      case "sos":
        content = renderSosView();
        break;
      case "sync":
      default:
        content = renderSyncView();
        break;
    }

    bezel.append(renderHeader(), renderTabs(), content, renderFooter());
    root.append(bezel);
  };

  const unsubscribe = controller.subscribe(render);
  const handleOnlineChange = () => render();
  if (typeof window !== "undefined") {
    window.addEventListener("online", handleOnlineChange);
    window.addEventListener("offline", handleOnlineChange);
  }

  render();

  return () => {
    clearRecordingTimer();
    unsubscribe();
    if (typeof window !== "undefined") {
      window.removeEventListener("online", handleOnlineChange);
      window.removeEventListener("offline", handleOnlineChange);
    }
  };
}
