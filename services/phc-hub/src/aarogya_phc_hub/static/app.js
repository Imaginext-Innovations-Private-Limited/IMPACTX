(() => {
  "use strict";

  const STORAGE_LANG_KEY = "aarogya.lang";
  const STORAGE_THEME_KEY = "aarogya.theme";
  const SUPPORTED_LANGS = ["en", "hi", "kn", "ta"];

  const I18N = {
    en: {
      appTitle: "Aarogya Mesh — Tier-2 PHC Command Center",
      appSubtitle: "Autonomous Offline-First Clinical Mesh Operations",
      badgeTier: "TIER-2 HUB",
      badgeOffline: "AIRPLANE-MODE SAFE",
      langToggle: "हिन्दी",
      themeLight: "Light",
      themeDark: "Dark",
      autoOn: "Auto-Refresh: ON",
      autoOff: "Auto-Refresh: OFF",
      refresh: "Refresh",
      refreshing: "Refreshing...",
      reconnecting: "Reconnecting...",
      demoBarLabel: "Live Scenarios",
      scenarioMaternal: "Maternal Watch SOS",
      scenarioVoice: "Offline Voice → AI",
      scenarioOutbreak: "Village Outbreak",
      scenarioCrdt: "CRDT Merge Proof",
      scMaternalTitle: "Maternal Watch SOS → ASHA Phone",
      scVoiceTitle: "Offline Voice Note → Hub AI Enrichment",
      scOutbreakTitle: "Multi-Worker EWMA Village Outbreak",
      scCrdtTitle: "Offline Conflict-Free CRDT Merge",
      demoReset: "Reset",
      openShowcase: "Open 3-Tier Live Stage →",
      demoLoading: "Running live clinical scenario...",
      demoLoaded: "Scenario executed through live CRDT sync:",
      demoResetting: "Resetting Hub state...",
      demoResetDone: "Hub SQLite event store and peer registry cleared.",
      demoUnavailable: "Demo scenario endpoint unavailable.",
      scenarioStepsLabel: "Clinical Flow",
      dismiss: "Dismiss",
      archTitle: "Compute-Proportional 3-Tier Autonomous Mesh",
      tier0Label: "Watch (Tier 0)",
      tier0Desc: "Standalone SOS & Reminders for Normal Public & CHW",
      tier0CapTag: "1-Tap SOS · BLE/LAN",
      tier1Label: "ASHA Phone (Tier 1)",
      tier1Desc: "WHO IMNCI Deterministic Triage + Offline IndexedDB",
      tier1CapTag: "Voice Queue · Delta Sync",
      tier2Label: "PHC Hub (Tier 2)",
      tier2Desc: "Whisper + SLM + LightGBM SHAP + EWMA Outbreak",
      activePeersShort: "active",
      hubOnlineShort: "online",
      nodeId: "Node ID",
      ram: "RAM",
      cpu: "CPU Cores",
      npu: "NPU",
      npuAvailable: "Available",
      npuAbsent: "None",
      connectUrl: "LAN Connect URL",
      wsUrl: "Mesh WebSocket",
      lastUpdated: "Last Updated",
      patients: "Registered Patients",
      triageRed: "RED Emergency",
      triageYellow: "YELLOW PHC",
      triageGreen: "GREEN Home",
      pendingEnrichments: "Pending Enrichments",
      completedEnrichments: "Completed Enrichments",
      totalEvents: "CRDT Events",
      clinicalPanel: "Clinical Triage, Action Cards & SHAP Risk",
      triageFeedTitle: "Active Triage Decisions",
      patientsRosterTitle: "Synced Patient Registry & Peers",
      peerTopology: "Live Mesh Peers",
      hubTelemetryTitle: "Hub Hardware & LAN Discovery",
      runEnrichment: "Run Hub Enrichment",
      runningEnrichment: "Running Enrichment...",
      enrichmentDone: "Enrichment cycle completed.",
      enrichmentUnavailable: "Enrichment endpoint unavailable.",
      outbreakAlerts: "EWMA Outbreak Alerts",
      shapTitle: "SHAP Risk Attributions",
      actionCards: "Action Cards",
      eventLog: "HLC CRDT Event Log Inspector",
      showEventLog: "Show Log",
      hideEventLog: "Hide Log",
      filterEvents: "Filter by event type",
      allEvents: "All Events",
      evPatientRegistered: "Patient Registered",
      evTriageCompleted: "Triage Completed",
      evChecklistRecorded: "Checklist Recorded",
      evVaccinationLogged: "Vaccination Logged",
      evVoiceNoteRecorded: "Voice Note Recorded",
      evEnrichmentCompleted: "Enrichment Completed",
      evActionCardIssued: "Action Card Issued",
      evOutbreakAlertRaised: "Outbreak Alert Raised",
      synFebrile: "Febrile Illness",
      synDiarrheal: "Acute Diarrheal Disease",
      synRespiratory: "Acute Respiratory Illness",
      synMaternal: "Maternal Danger Sign",
      synMalaria: "Suspected Malaria Cluster",
      synDengue: "Suspected Dengue Cluster",
      colHlc: "HLC Timestamp",
      colOrigin: "Origin Node",
      colType: "Event Type",
      colPatient: "Patient",
      colEnrichment: "Enrichment",
      colSummary: "Payload",
      noPatients: "No patients synced yet. Launch a scenario above or sync a peer.",
      noTriage: "No triage assessments recorded yet.",
      noPeers: "No mesh peers connected yet.",
      noOutbreaks: "No active outbreak alerts.",
      noShap: "No completed SHAP risk enrichments yet.",
      noActionCards: "No active action cards.",
      noEvents: "No CRDT events recorded yet.",
      battery: "Battery",
      riskScore: "Risk Score",
      outbreakBannerPrefix: "ACTIVE EWMA OUTBREAK ALERT",
      pregnantWeeks: "Pregnant",
      weeksShort: "w",
      referralYes: "PHC Referral",
      eventsUnit: "events",
      peersUnit: "peers",
      moreCount: "+{n} more",
      villagePrefix: "Village:",
      sevRed: "RED Emergency",
      sevYellow: "YELLOW PHC",
      sevGreen: "GREEN Home",
      prioCritical: "Critical",
      prioHigh: "High",
      prioMedium: "Medium",
      prioLow: "Low",
      statusOpen: "Open",
      statusAcknowledged: "Acknowledged",
      statusCompleted: "Completed",
      statusDismissed: "Dismissed",
      riskHigh: "High Risk",
      riskModerate: "Moderate Risk",
      riskLow: "Low Risk",
      riskEnriched: "Enriched",
      enrPending: "Pending",
      enrCompleted: "Completed",
      enrNotNeeded: "Not Needed",
      enrFailed: "Failed",
      watchModeChw: "ASHA Companion",
      watchModeFamily: "Patient / Family",
      expandPayload: "Click to expand JSON payload",
      collapsePayload: "Click to collapse JSON payload",
      proofCloudRpcs: "0 Cloud RPCs",
      proofSafetyFloor: "WHO Safety Floor · conf=1.00",
      proofZeroBloat: "0 PyTorch · 0 CUDA",
      convergedPatientsUnit: "converged patients",
      crdtMergeTitle: "CRDT LWW Conflict-Free Merge Proof",
      zeroDataLoss: "0 data loss",
      simultaneousTieBreak: "Same wall_ms HLC tie-break",
      convergedRecord: "Converged LWW PatientRecord",
      stageAudio: "Audio Blob",
      stageAsr: "ASR",
      stageSlm: "GBNF SLM",
      stageTriage: "WHO Rule (1.00)",
      stageShap: "TreeSHAP",
      symptomsLabel: "Symptoms",
      dangerFlagsLabel: "Danger Flags",
      shapPosLegend: "+ Risk-driving",
      shapNegLegend: "- Protective",
      connectCardTitle: "Connect Mobile / Watch to This Hub",
      connectCardDesc: "Make sure your phone or watch is on the same Wi-Fi/hotspot, then enter this address or scan the QR code.",
      copyAddress: "Copy Address",
      copiedAddress: "Copied!",
      copyFailed: "Copy failed",
      showQrCode: "Show QR Code",
      hideQrCode: "Hide QR Code",
      qrScanTitle: "Scan from Field PWA or Android App",
      qrScanHint: "Open Sync → Set Hub Address → Scan QR to fill this address automatically.",
      clinicalPanelDesc: "Urgent cases, ASHA follow-up cards, AI voice-note risk scores, and village outbreak alerts.",
      patientsRosterDesc: "Patients synced from field phones, connected mesh devices, and Hub hardware status.",
      kpiMlAnalytics: "ML Analytics & Sync",
      pendingShort: "pending:",
      syncedFeedTitle: "Immediately Synced Feed",
      syncedFeedDesc: "Newest registrations, triage checks, voice notes, checklists & vaccines from field devices.",
      justSynced: "Just Synced",
      noSyncedEvents: "No clinical events synced yet. Launch a scenario or sync a field device.",
      originPhone: "Phone",
      originWatch: "Watch",
      originHub: "Hub",
      mlAnalyticsTitle: "Recent ML Analytics (GBDT + TreeSHAP)",
      mlAnalyticsDesc: "WHO Clinical Safety Floor + 28-Tree GBDT risk scoring & SHAP feature attributions.",
      aboutSourcesTitle: "What do these medical sources mean?",
      aboutWho: "WHO IMNCI: World Health Organization's official handbook used across India to spot urgent danger signs in babies and children (0–5 years).",
      aboutNhm: "NHM ASHA & UIP: Government of India's pregnancy/newborn safety rules and child vaccination calendar.",
      aboutMl: "Laptop ML Risk Score: Trained 28-tree GBDT + TreeSHAP model combining 13 vitals to rank priority — it never overrides WHO/NHM emergency rules.",
      clinicalOpsTitle: "Clinical Triage, Action Cards & Outbreaks",
      sysDetailsTitle: "System Architecture & Hardware Details",
      showDetails: "Show Details",
      hideDetails: "Hide Details",
      whoFloorLabel: "WHO Clinical Floor",
      laptopMlLabel: "Laptop ML",
      laptopMlModel: "28-Tree GBDT + TreeSHAP",
      recommendedFollowUpLabel: "Recommended Follow-up",
      matchedRulesLabel: "Rules",
    },
    hi: {
      appTitle: "आरोग्य संजाल — प्राथमिक स्वास्थ्य केन्द्र नियन्त्रण कक्ष",
      appSubtitle: "स्वावलम्बी अन्तर्जाल-रहित चिकित्सकीय समन्वय प्रणाली",
      badgeTier: "स्तर-२ मुख्य केन्द्र",
      badgeOffline: "अन्तर्जाल-रहित सुरक्षित",
      langToggle: "English",
      themeLight: "प्रकाश रूप",
      themeDark: "रात्रि रूप",
      autoOn: "स्वतः अद्यतन: सक्रिय",
      autoOff: "स्वतः अद्यतन: निष्क्रिय",
      refresh: "अद्यतन करें",
      refreshing: "अद्यतन हो रहा है...",
      reconnecting: "पुनः संयोजन हो रहा है...",
      demoBarLabel: "प्रदर्शन परिदृश्य",
      scenarioMaternal: "मातृ घटिका आपात संकेत",
      scenarioVoice: "अन्तर्जाल-रहित स्वर → प्रज्ञा",
      scenarioOutbreak: "ग्राम संक्रमण प्रकोप",
      scenarioCrdt: "द्वन्द्व-रहित विलय प्रमाण",
      scMaternalTitle: "मातृ घटिका आपात संकेत → आशा दूरभाष",
      scVoiceTitle: "अन्तर्जाल-रहित स्वर → मुख्य केन्द्र प्रज्ञा संवर्धन",
      scOutbreakTitle: "ग्राम संक्रमण प्रकोप संसूचन",
      scCrdtTitle: "अन्तर्जाल-रहित द्वन्द्व-रहित विलय प्रमाण",
      demoReset: "पुनःस्थापन",
      openShowcase: "त्रि-स्तरीय जीवन्त मंच →",
      demoLoading: "जीवन्त चिकित्सकीय परिदृश्य प्रारम्भ हो रहा है...",
      demoLoaded: "परिदृश्य वास्तविक समन्वय द्वारा पूर्ण हुआ:",
      demoResetting: "मुख्य केन्द्र पुनःस्थापित हो रहा है...",
      demoResetDone: "घटना अभिलेख एवं सहकर्मी सूची स्वच्छ हुई।",
      demoUnavailable: "परिदृश्य सेवा अभी संयोजित नहीं है।",
      scenarioStepsLabel: "चिकित्सकीय क्रम",
      dismiss: "बन्द करें",
      archTitle: "क्षमता-आधारित त्रि-स्तरीय स्वावलम्बी संजाल संरचना",
      tier0Label: "स्तर-० घटिका",
      tier0Desc: "सामान्य जन एवं स्वास्थ्य कार्यकर्ता हेतु स्वावलम्बी आपात संकेत एवं स्मरण",
      tier0CapTag: "एक-स्पर्श आपात · स्थानीय संजाल",
      tier1Label: "स्तर-१ दूरभाष",
      tier1Desc: "विश्व स्वास्थ्य संगठन नियम वर्गीकरण एवं स्थानीय संग्रहण",
      tier1CapTag: "स्वर पंक्ति · अंश समन्वय",
      tier2Label: "स्तर-२ मुख्य केन्द्र",
      tier2Desc: "ध्वनि अनुलेखन · संकट कारक विश्लेषण · प्रकोप संसूचन",
      activePeersShort: "सक्रिय",
      hubOnlineShort: "सक्रिय",
      nodeId: "केन्द्र पहचान",
      ram: "मुख्य स्मृति",
      cpu: "प्रक्रमक क्रोड",
      npu: "तन्त्रिका प्रक्रमक",
      npuAvailable: "उपलब्ध",
      npuAbsent: "अनुपलब्ध",
      connectUrl: "स्थानीय सम्पर्क सूत्र",
      wsUrl: "तत्काल संजाल सूत्र",
      lastUpdated: "अन्तिम अद्यतन",
      patients: "पंजीकृत रोगी",
      triageRed: "रक्त — आपातकाल",
      triageYellow: "पीत — स्वास्थ्य केन्द्र",
      triageGreen: "हरित — गृह देखभाल",
      pendingEnrichments: "प्रतीक्षारत संवर्धन",
      completedEnrichments: "पूर्ण संवर्धन",
      totalEvents: "कुल घटनाएँ",
      clinicalPanel: "चिकित्सकीय वर्गीकरण, कार्य पत्रक एवं संकट विश्लेषण",
      triageFeedTitle: "सक्रिय चिकित्सकीय वर्गीकरण",
      patientsRosterTitle: "समन्वित रोगी पंजिका एवं सहकर्मी",
      peerTopology: "जीवन्त संजाल सहकर्मी",
      hubTelemetryTitle: "मुख्य केन्द्र उपकरण एवं स्थानीय सम्पर्क",
      runEnrichment: "तत्काल संवर्धन चलाएँ",
      runningEnrichment: "संवर्धन प्रगति पर...",
      enrichmentDone: "संवर्धन चक्र पूर्ण हुआ।",
      enrichmentUnavailable: "संवर्धन सेवा अभी संयोजित नहीं है।",
      outbreakAlerts: "संक्रमण प्रकोप चेतावनी",
      shapTitle: "संकट कारक विश्लेषण (SHAP)",
      actionCards: "तत्काल कार्य पत्रक",
      eventLog: "जीवन्त कालक्रम घटना अभिलेख निरीक्षक",
      showEventLog: "अभिलेख दिखाएँ",
      hideEventLog: "अभिलेख छिपाएँ",
      filterEvents: "घटना प्रकार चयन",
      allEvents: "समस्त घटनाएँ",
      evPatientRegistered: "रोगी पंजीकरण",
      evTriageCompleted: "वर्गीकरण पूर्ण",
      evChecklistRecorded: "परीक्षण सूची अभिलेख",
      evVaccinationLogged: "टीकाकरण अभिलेख",
      evVoiceNoteRecorded: "स्वर टिप्पणी अभिलेख",
      evEnrichmentCompleted: "संवर्धन पूर्ण",
      evActionCardIssued: "कार्य पत्रक जारी",
      evOutbreakAlertRaised: "प्रकोप चेतावनी जारी",
      synFebrile: "ज्वर संक्रमण",
      synDiarrheal: "तीव्र अतिसार रोग",
      synRespiratory: "तीव्र श्वसन संक्रमण",
      synMaternal: "मातृ संकट लक्षण",
      synMalaria: "सन्दिग्ध मलेरिया समूह",
      synDengue: "सन्दिग्ध डेंगू समूह",
      colHlc: "कालक्रम मुहर",
      colOrigin: "उद्गम केन्द्र",
      colType: "घटना प्रकार",
      colPatient: "रोगी",
      colEnrichment: "संवर्धन स्थिति",
      colSummary: "विवरण",
      noPatients: "अभी कोई रोगी पंजीकृत नहीं है। ऊपर से परिदृश्य चुनें।",
      noTriage: "अभी कोई चिकित्सकीय वर्गीकरण अभिलेखित नहीं है।",
      noPeers: "कोई संजाल सहकर्मी अभी संयोजित नहीं है।",
      noOutbreaks: "कोई सक्रिय संक्रमण प्रकोप चेतावनी नहीं है।",
      noShap: "अभी कोई संकट कारक संवर्धन उपलब्ध नहीं है।",
      noActionCards: "कोई सक्रिय कार्य पत्रक नहीं है।",
      noEvents: "अभिलेख में अभी कोई घटना नहीं है।",
      battery: "विद्युत स्तर",
      riskScore: "संकट सूचकांक",
      outbreakBannerPrefix: "सक्रिय संक्रमण प्रकोप चेतावनी",
      pregnantWeeks: "गर्भावस्था",
      weeksShort: "सप्ताह",
      referralYes: "शीघ्र स्वास्थ्य केन्द्र प्रेषण",
      eventsUnit: "घटनाएँ",
      peersUnit: "सहकर्मी",
      moreCount: "+{n} अतिरिक्त",
      villagePrefix: "ग्राम:",
      sevRed: "रक्त · आपातकाल",
      sevYellow: "पीत · स्वास्थ्य केन्द्र",
      sevGreen: "हरित · गृह देखभाल",
      prioCritical: "अति गम्भीर",
      prioHigh: "उच्च",
      prioMedium: "मध्यम",
      prioLow: "सामान्य",
      statusOpen: "सक्रिय",
      statusAcknowledged: "स्वीकृत",
      statusCompleted: "पूर्ण",
      statusDismissed: "निरस्त",
      riskHigh: "उच्च संकट",
      riskModerate: "मध्यम संकट",
      riskLow: "न्यून संकट",
      riskEnriched: "संवर्धित",
      enrPending: "प्रतीक्षारत",
      enrCompleted: "पूर्ण",
      enrNotNeeded: "अनावश्यक",
      enrFailed: "विफल",
      watchModeChw: "स्वास्थ्य कर्मी सहायक",
      watchModeFamily: "रोगी परिवार",
      expandPayload: "पूर्ण विवरण देखने हेतु स्पर्श करें",
      collapsePayload: "विवरण संक्षिप्त करने हेतु स्पर्श करें",
      proofCloudRpcs: "० मेघ-सेवा अनुरोध",
      proofSafetyFloor: "विश्व स्वास्थ्य सुरक्षा स्तर · १.००",
      proofZeroBloat: "० भारी तन्त्र भार",
      convergedPatientsUnit: "अभिसरित रोगी",
      crdtMergeTitle: "द्वन्द्व-रहित विलय प्रमाण (LWW)",
      zeroDataLoss: "शून्य तथ्यांश हानि",
      simultaneousTieBreak: "समान कालक्रम संयोग",
      convergedRecord: "एकीकृत रोगी अभिलेख",
      stageAudio: "श्रव्य संचिका",
      stageAsr: "ध्वनि अनुलेखन",
      stageSlm: "संरचना प्रज्ञा",
      stageTriage: "निश्चित वर्गीकरण (१.००)",
      stageShap: "संकट कारक विश्लेषण",
      symptomsLabel: "चिह्नित लक्षण",
      dangerFlagsLabel: "संकट संकेत",
      shapPosLegend: "+ संकट वर्धक",
      shapNegLegend: "- संरक्षक कारक",
      connectCardTitle: "दूरभाष एवं घटिका को मुख्य केन्द्र से संयोजित करें",
      connectCardDesc: "सुनिश्चित करें कि आपका दूरभाष इसी स्थानीय संजाल पर है, फिर यह पता भरें अथवा द्वि-आयामी कूट (QR) क्रमवीक्षण करें।",
      copyAddress: "पता प्रतिलिपि करें",
      copiedAddress: "प्रतिलिपि पूर्ण!",
      copyFailed: "प्रतिलिपि विफल",
      showQrCode: "QR कूट दिखाएँ",
      hideQrCode: "QR कूट छिपाएँ",
      qrScanTitle: "क्षेत्रीय दूरभाष अनुप्रयोग से क्रमवीक्षण करें",
      qrScanHint: "समन्वय पृष्ठ पर जाकर मुख्य केन्द्र पता में QR क्रमवीक्षण चुनें; यह पता स्वतः भर जाएगा।",
      clinicalPanelDesc: "आपातकालीन प्रकरण, आशा कार्यकर्ता कार्य पत्रक, स्वर टिप्पणी संकट मूल्यांकन एवं ग्राम प्रकोप चेतावनी।",
      patientsRosterDesc: "क्षेत्रीय दूरभाष से समन्वित रोगी, सक्रिय संजाल उपकरण एवं मुख्य केन्द्र स्थिति।",
      kpiMlAnalytics: "प्रज्ञा विश्लेषण एवं समन्वय",
      pendingShort: "प्रतीक्षारत:",
      syncedFeedTitle: "तत्काल समन्वित घटनाएँ",
      syncedFeedDesc: "क्षेत्रीय उपकरणों से नवीनतम पंजीकरण, वर्गीकरण, स्वर टिप्पणी, परीक्षण सूची एवं टीकाकरण।",
      justSynced: "अभी समन्वित",
      noSyncedEvents: "अभी तक कोई चिकित्सकीय घटना समन्वित नहीं हुई है।",
      originPhone: "दूरभाष",
      originWatch: "घटिका",
      originHub: "मुख्य केन्द्र",
      mlAnalyticsTitle: "नवीनतम प्रज्ञा विश्लेषण (GBDT + TreeSHAP)",
      mlAnalyticsDesc: "विश्व स्वास्थ्य सुरक्षा स्तर + २८-वृक्ष GBDT संकट मूल्यांकन एवं SHAP कारण विश्लेषण।",
      aboutSourcesTitle: "इन चिकित्सा स्रोतों का क्या अर्थ है?",
      aboutWho: "विश्व स्वास्थ्य संगठन बाल एवं नवजात नियमावली (WHO IMNCI): 0 से 5 वर्ष के शिशुओं में गम्भीर संकट लक्षण पहचानने की आधिकारिक वैश्विक पुस्तिका।",
      aboutNhm: "राष्ट्रीय स्वास्थ्य मिशन एवं टीकाकरण (NHM ASHA एवं UIP): भारत सरकार की मातृ, नवजात सुरक्षा तथा टीकाकरण नियमावली।",
      aboutMl: "केन्द्र यन्त्र-अधिगम संकट अंक (GBDT एवं TreeSHAP): 13 स्वास्थ्य मानदण्डों से प्राथमिकता दर्शाता है — यह सुनिश्चित आपात नियमों को कभी नहीं बदलता।",
      clinicalOpsTitle: "चिकित्सकीय वर्गीकरण, कार्य पत्रक एवं प्रकोप",
      sysDetailsTitle: "तन्त्र संरचना एवं उपकरण विवरण",
      showDetails: "विवरण दिखाएँ",
      hideDetails: "विवरण छिपाएँ",
      whoFloorLabel: "WHO सुरक्षा स्तर",
      laptopMlLabel: "मुख्य केन्द्र प्रज्ञा",
      laptopMlModel: "२८-वृक्ष GBDT + TreeSHAP",
      recommendedFollowUpLabel: "अनुशंसित अनुवर्ती क्रिया",
      matchedRulesLabel: "नियम",
    },
    kn: {
      appTitle: "ಆರೋಗ್ಯ ಮೆಶ್ — ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರ (PHC) ನಿಯಂತ್ರಣ ಕೇಂದ್ರ",
      appSubtitle: "ಇಂಟರ್ನೆಟ್ ರಹಿತ ಸ್ವಾಯತ್ತ ವೈದ್ಯಕೀಯ ಜಾಲ ಕಾರ್ಯಾಚರಣೆ",
      badgeTier: "ಹಂತ-೨ ಮುಖ್ಯ ಕೇಂದ್ರ",
      badgeOffline: "ಆಫ್‌ಲೈನ್ ಸುರಕ್ಷಿತ",
      langToggle: "ಕನ್ನಡ",
      themeLight: "ಬೆಳಕು",
      themeDark: "ಕತ್ತಲೆ",
      autoOn: "ಸ್ವಯಂ ನವೀಕರಣ: ಚಾಲೂ",
      autoOff: "ಸ್ವಯಂ ನವೀಕರಣ: ಬಂದ್",
      refresh: "ನವೀಕರಿಸಿ",
      refreshing: "ನವೀಕರಿಸಲಾಗುತ್ತಿದೆ...",
      reconnecting: "ಮರುಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ...",
      demoBarLabel: "ನೇರ ಪ್ರದರ್ಶನ ಸನ್ನಿವೇಶಗಳು",
      scenarioMaternal: "ಗರ್ಭಿಣಿ ವಾಚ್ ತುರ್ತು ಕರೆ",
      scenarioVoice: "ಆಫ್‌ಲೈನ್ ಧ್ವನಿ → AI",
      scenarioOutbreak: "ಗ್ರಾಮ ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ",
      scenarioCrdt: "CRDT ವಿಲೀನ ಪುರಾವೆ",
      scMaternalTitle: "ಗರ್ಭಿಣಿ ವಾಚ್ ತುರ್ತು ಕರೆ → ಆಶಾ ಫೋನ್",
      scVoiceTitle: "ಆಫ್‌ಲೈನ್ ಧ್ವನಿ ಟಿಪ್ಪಣಿ → ಕೇಂದ್ರದ AI ವಿಶ್ಲೇಷಣೆ",
      scOutbreakTitle: "ಗ್ರಾಮ ಮಟ್ಟದ EWMA ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ ಪತ್ತೆ",
      scCrdtTitle: "ಆಫ್‌ಲೈನ್ ದ್ವಂದ್ವ-ರಹಿತ CRDT ವಿಲೀನ ಪುರಾವೆ",
      demoReset: "ಮರುಹೊಂದಿಸಿ",
      openShowcase: "೩-ಹಂತದ ನೇರ ವೇದಿಕೆ ತೆರೆಯಿರಿ →",
      demoLoading: "ನೇರ ವೈದ್ಯಕೀಯ ಸನ್ನಿವೇಶ ಚಾಲನೆಯಲ್ಲಿದೆ...",
      demoLoaded: "ನೇರ CRDT ಸಿಂಕ್ ಮೂಲಕ ಸನ್ನಿವೇಶ ಪೂರ್ಣಗೊಂಡಿದೆ:",
      demoResetting: "ಮುಖ್ಯ ಕೇಂದ್ರವನ್ನು ಮರುಹೊಂದಿಸಲಾಗುತ್ತಿದೆ...",
      demoResetDone: "ಕೇಂದ್ರದ ಘಟನೆಗಳ ದಾಖಲೆ ಮತ್ತು ಸಾಧನ ಪಟ್ಟಿ ತೆರವುಗೊಳಿಸಲಾಗಿದೆ.",
      demoUnavailable: "ಪ್ರದರ್ಶನ ಸೇವೆ ಸದ್ಯ ಲಭ್ಯವಿಲ್ಲ.",
      scenarioStepsLabel: "ವೈದ್ಯಕೀಯ ಪ್ರಕ್ರಿಯೆ",
      dismiss: "ಮುಚ್ಚಿ",
      archTitle: "ಸಾಮರ್ಥ್ಯ-ಆಧಾರಿತ ೩-ಹಂತದ ಸ್ವಾಯತ್ತ ಆರೋಗ್ಯ ಜಾಲ",
      tier0Label: "ಹಂತ-೦ ವಾಚ್",
      tier0Desc: "ಸಾರ್ವಜನಿಕರು ಮತ್ತು ಆರೋಗ್ಯ ಕಾರ್ಯಕರ್ತರಿಗೆ ಸ್ವತಂತ್ರ ತುರ್ತು ಕರೆ ಹಾಗೂ ಜ್ಞಾಪನೆ",
      tier0CapTag: "೧-ಸ್ಪರ್ಶ ತುರ್ತು · BLE/LAN",
      tier1Label: "ಹಂತ-೧ ಫೋನ್",
      tier1Desc: "WHO IMNCI ಖಚಿತ ವರ್ಗೀಕರಣ ಮತ್ತು ಆಫ್‌ಲೈನ್ ಸಂಗ್ರಹಣೆ",
      tier1CapTag: "ಧ್ವನಿ ಸಾಲು · ಡೆಲ್ಟಾ ಸಿಂಕ್",
      tier2Label: "ಹಂತ-೨ ಮುಖ್ಯ ಕೇಂದ್ರ",
      tier2Desc: "ಧ್ವನಿ ಲಿಪ್ಯಂತರ · SLM · LightGBM SHAP · EWMA ಪ್ರಕೋಪ ಪತ್ತೆ",
      activePeersShort: "ಸಕ್ರಿಯ",
      hubOnlineShort: "ಆನ್‌ಲೈನ್",
      nodeId: "ಕೇಂದ್ರದ ಗುರುತು",
      ram: "RAM ಮೆಮೊರಿ",
      cpu: "CPU ಕೋರ್‌ಗಳು",
      npu: "NPU ಘಟಕ",
      npuAvailable: "ಲಭ್ಯವಿದೆ",
      npuAbsent: "ಲಭ್ಯವಿಲ್ಲ",
      connectUrl: "ಸ್ಥಳೀಯ LAN ಸಂಪರ್ಕ",
      wsUrl: "ಮೆಶ್ ವೆಬ್‌ಸಾಕೆಟ್",
      lastUpdated: "ಕೊನೆಯ ನವೀಕರಣ",
      patients: "ನೋಂದಾಯಿತ ರೋಗಿಗಳು",
      triageRed: "ಕೆಂಪು — ತುರ್ತು ಚಿಕಿತ್ಸೆ",
      triageYellow: "ಹಳದಿ — PHC ತಪಾಸಣೆ",
      triageGreen: "ಹಸಿರು — ಮನೆ ಆರೈಕೆ",
      pendingEnrichments: "ಬಾಕಿ AI ವಿಶ್ಲೇಷಣೆ",
      completedEnrichments: "ಪೂರ್ಣಗೊಂಡ ವಿಶ್ಲೇಷಣೆ",
      totalEvents: "CRDT ಘಟನೆಗಳು",
      clinicalPanel: "ವೈದ್ಯಕೀಯ ವರ್ಗೀಕರಣ, ಕ್ರಿಯಾ ಕಾರ್ಡ್‌ಗಳು ಮತ್ತು SHAP ಅಪಾಯ ವಿಶ್ಲೇಷಣೆ",
      triageFeedTitle: "ಸಕ್ರಿಯ ವೈದ್ಯಕೀಯ ವರ್ಗೀಕರಣಗಳು",
      patientsRosterTitle: "ಸಿಂಕ್ ಆದ ರೋಗಿಗಳ ಪಟ್ಟಿ ಮತ್ತು ಸಾಧನಗಳು",
      peerTopology: "ಸಕ್ರಿಯ ಜಾಲ ಸಾಧನಗಳು",
      hubTelemetryTitle: "ಕೇಂದ್ರದ ಹಾರ್ಡ್‌ವೇರ್ ಮತ್ತು LAN ಸಂಪರ್ಕ",
      runEnrichment: "AI ವಿಶ್ಲೇಷಣೆ ಪ್ರಾರಂಭಿಸಿ",
      runningEnrichment: "ವಿಶ್ಲೇಷಣೆ ನಡೆಯುತ್ತಿದೆ...",
      enrichmentDone: "AI ವಿಶ್ಲೇಷಣೆ ಪೂರ್ಣಗೊಂಡಿದೆ.",
      enrichmentUnavailable: "ವಿಶ್ಲೇಷಣೆ ಸೇವೆ ಸದ್ಯ ಲಭ್ಯವಿಲ್ಲ.",
      outbreakAlerts: "EWMA ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ ಎಚ್ಚರಿಕೆಗಳು",
      shapTitle: "SHAP ಅಪಾಯ ಕಾರಣಗಳ ವಿಶ್ಲೇಷಣೆ",
      actionCards: "ತುರ್ತು ಕ್ರಿಯಾ ಕಾರ್ಡ್‌ಗಳು",
      eventLog: "HLC CRDT ಘಟನೆಗಳ ದಾಖಲೆ ಪರಿಶೀಲಕ",
      showEventLog: "ದಾಖಲೆ ತೋರಿಸಿ",
      hideEventLog: "ದಾಖಲೆ ಮರೆಮಾಡಿ",
      filterEvents: "ಘಟನೆ ಪ್ರಕಾರ ಆಯ್ಕೆ",
      allEvents: "ಎಲ್ಲಾ ಘಟನೆಗಳು",
      evPatientRegistered: "ರೋಗಿ ನೋಂದಣಿ",
      evTriageCompleted: "ವರ್ಗೀಕರಣ ಪೂರ್ಣ",
      evChecklistRecorded: "ತಪಾಸಣಾ ಪಟ್ಟಿ ದಾಖಲೆ",
      evVaccinationLogged: "ಲಸಿಕೆ ದಾಖಲೆ",
      evVoiceNoteRecorded: "ಧ್ವನಿ ಟಿಪ್ಪಣಿ ದಾಖಲೆ",
      evEnrichmentCompleted: "AI ವಿಶ್ಲೇಷಣೆ ಪೂರ್ಣ",
      evActionCardIssued: "ಕ್ರಿಯಾ ಕಾರ್ಡ್ ಜಾರಿ",
      evOutbreakAlertRaised: "ಪ್ರಕೋಪ ಎಚ್ಚರಿಕೆ ಜಾರಿ",
      synFebrile: "ಜ್ವರ ಸಂಬಂಧಿತ ಕಾಯಿಲೆ",
      synDiarrheal: "ತೀವ್ರ ಅತಿಸಾರ ರೋಗ",
      synRespiratory: "ತೀವ್ರ ಶ್ವಾಸಕೋಶ ಸೋಂಕು",
      synMaternal: "ಗರ್ಭಿಣಿ ಅಪಾಯದ ಲಕ್ಷಣ",
      synMalaria: "ಶಂಕಿತ ಮಲೇರಿಯಾ ಪ್ರಕರಣಗಳು",
      synDengue: "ಶಂಕಿತ ಡೆಂಗ್ಯೂ ಪ್ರಕರಣಗಳು",
      colHlc: "HLC ಸಮಯಮುದ್ರೆ",
      colOrigin: "ಮೂಲ ಸಾಧನ",
      colType: "ಘಟನೆ ಪ್ರಕಾರ",
      colPatient: "ರೋಗಿ",
      colEnrichment: "ವಿಶ್ಲೇಷಣೆ ಸ್ಥಿತಿ",
      colSummary: "ದತ್ತಾಂಶ ವಿವರ",
      noPatients: "ಇನ್ನೂ ಯಾವುದೇ ರೋಗಿಗಳು ಸಿಂಕ್ ಆಗಿಲ್ಲ. ಮೇಲಿನ ಸನ್ನಿವೇಶ ಆಯ್ಕೆಮಾಡಿ.",
      noTriage: "ಇನ್ನೂ ಯಾವುದೇ ವೈದ್ಯಕೀಯ ವರ್ಗೀಕರಣ ದಾಖಲಾಗಿಲ್ಲ.",
      noPeers: "ಯಾವುದೇ ಜಾಲ ಸಾಧನಗಳು ಇನ್ನೂ ಸಂಪರ್ಕಗೊಂಡಿಲ್ಲ.",
      noOutbreaks: "ಯಾವುದೇ ಸಕ್ರಿಯ ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ.",
      noShap: "ಇನ್ನೂ ಯಾವುದೇ SHAP ಅಪಾಯ ವಿಶ್ಲೇಷಣೆ ಲಭ್ಯವಿಲ್ಲ.",
      noActionCards: "ಯಾವುದೇ ಸಕ್ರಿಯ ಕ್ರಿಯಾ ಕಾರ್ಡ್‌ಗಳಿಲ್ಲ.",
      noEvents: "ಇನ್ನೂ ಯಾವುದೇ CRDT ಘಟನೆಗಳು ದಾಖಲಾಗಿಲ್ಲ.",
      battery: "ಬ್ಯಾಟರಿ",
      riskScore: "ಅಪಾಯದ ಮಟ್ಟ",
      outbreakBannerPrefix: "ಸಕ್ರಿಯ EWMA ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ ಎಚ್ಚರಿಕೆ",
      pregnantWeeks: "ಗರ್ಭಿಣಿ",
      weeksShort: "ವಾರ",
      referralYes: "ತಕ್ಷಣ PHC ಗೆ ಕಳುಹಿಸಿ",
      eventsUnit: "ಘಟನೆಗಳು",
      peersUnit: "ಸಾಧನಗಳು",
      moreCount: "+{n} ಇನ್ನಷ್ಟು",
      villagePrefix: "ಗ್ರಾಮ:",
      sevRed: "ಕೆಂಪು · ತುರ್ತು ಚಿಕಿತ್ಸೆ",
      sevYellow: "ಹಳದಿ · PHC ತಪಾಸಣೆ",
      sevGreen: "ಹಸಿರು · ಮನೆ ಆರೈಕೆ",
      prioCritical: "ಅತಿ ಗಂಭೀರ",
      prioHigh: "ಹೆಚ್ಚು",
      prioMedium: "ಮಧ್ಯಮ",
      prioLow: "ಸಾಮಾನ್ಯ",
      statusOpen: "ಸಕ್ರಿಯ",
      statusAcknowledged: "ಸ್ವೀಕರಿಸಲಾಗಿದೆ",
      statusCompleted: "ಪೂರ್ಣಗೊಂಡಿದೆ",
      statusDismissed: "ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ",
      riskHigh: "ಹೆಚ್ಚಿನ ಅಪಾಯ",
      riskModerate: "ಮಧ್ಯಮ ಅಪಾಯ",
      riskLow: "ಕಡಿಮೆ ಅಪಾಯ",
      riskEnriched: "ವಿಶ್ಲೇಷಿತ",
      enrPending: "ಬಾಕಿ ಇದೆ",
      enrCompleted: "ಪೂರ್ಣಗೊಂಡಿದೆ",
      enrNotNeeded: "ಅಗತ್ಯವಿಲ್ಲ",
      enrFailed: "ವಿಫಲವಾಗಿದೆ",
      watchModeChw: "ಆರೋಗ್ಯ ಕಾರ್ಯಕರ್ತೆ ಸಹಾಯಕ",
      watchModeFamily: "ರೋಗಿ ಕುಟುಂಬ",
      expandPayload: "ಪೂರ್ಣ JSON ವಿವರ ನೋಡಲು ಕ್ಲಿಕ್ ಮಾಡಿ",
      collapsePayload: "ವಿವರ ಕುಗ್ಗಿಸಲು ಕ್ಲಿಕ್ ಮಾಡಿ",
      proofCloudRpcs: "೦ ಕ್ಲೌಡ್ ಕರೆಗಳು",
      proofSafetyFloor: "WHO ಸುರಕ್ಷತಾ ಮಾನದಂಡ · ೧.೦೦",
      proofZeroBloat: "೦ PyTorch · ೦ CUDA",
      convergedPatientsUnit: "ಸಂಯೋಜಿತ ರೋಗಿಗಳು",
      crdtMergeTitle: "CRDT ದ್ವಂದ್ವ-ರಹಿತ ವಿಲೀನ ಪುರಾವೆ (LWW)",
      zeroDataLoss: "ಶೂನ್ಯ ದತ್ತಾಂಶ ನಷ್ಟ",
      simultaneousTieBreak: "ಏಕಕಾಲದ HLC ಸಂಘರ್ಷ ಪರಿಹಾರ",
      convergedRecord: "ಸಂಯೋಜಿತ ರೋಗಿ ದಾಖಲೆ",
      stageAudio: "ಧ್ವನಿ ಕಡತ",
      stageAsr: "ಧ್ವನಿ ಲಿಪ್ಯಂತರ",
      stageSlm: "ರಚನಾತ್ಮಕ SLM",
      stageTriage: "WHO ನಿಯಮ (೧.೦೦)",
      stageShap: "TreeSHAP",
      symptomsLabel: "ಲಕ್ಷಣಗಳು",
      dangerFlagsLabel: "ಅಪಾಯದ ಸೂಚನೆಗಳು",
      shapPosLegend: "+ ಅಪಾಯ ಹೆಚ್ಚಿಸುವ",
      shapNegLegend: "- ರಕ್ಷಣಾತ್ಮಕ",
      connectCardTitle: "ಮೊಬೈಲ್ / ವಾಚ್ ಅನ್ನು ಈ ಕೇಂದ್ರಕ್ಕೆ ಸಂಪರ್ಕಿಸಿ",
      connectCardDesc: "ನಿಮ್ಮ ಫೋನ್ ಅಥವಾ ವಾಚ್ ಒಂದೇ Wi-Fi/ಹಾಟ್‌ಸ್ಪಾಟ್‌ನಲ್ಲಿರುವುದನ್ನು ಖಚಿತಪಡಿಸಿ, ನಂತರ ಈ ವಿಳಾಸವನ್ನು ನಮೂದಿಸಿ ಅಥವಾ QR ಸ್ಕ್ಯಾನ್ ಮಾಡಿ.",
      copyAddress: "ವಿಳಾಸ ನಕಲಿಸಿ",
      copiedAddress: "ನಕಲಿಸಲಾಗಿದೆ!",
      copyFailed: "ನಕಲು ವಿಫಲವಾಗಿದೆ",
      showQrCode: "QR ಕೋಡ್ ತೋರಿಸಿ",
      hideQrCode: "QR ಕೋಡ್ ಮರೆಮಾಡಿ",
      qrScanTitle: "ಫೀಲ್ಡ್ PWA ಅಥವಾ Android ಆ್ಯಪ್‌ನಿಂದ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ",
      qrScanHint: "Sync → Hub ವಿಳಾಸ ಹೊಂದಿಸಿ → QR ಸ್ಕ್ಯಾನ್ ತೆರೆಯಿರಿ; ವಿಳಾಸ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಭರ್ತಿಯಾಗುತ್ತದೆ.",
      clinicalPanelDesc: "ತುರ್ತು ಪ್ರಕರಣಗಳು, ಆಶಾ ಕಾರ್ಯ ಕಾರ್ಡ್‌ಗಳು, ಧ್ವನಿ ಟಿಪ್ಪಣಿ ಅಪಾಯ ಅಂಕಗಳು ಮತ್ತು ಗ್ರಾಮ ಪ್ರಕೋಪ ಎಚ್ಚರಿಕೆಗಳು.",
      patientsRosterDesc: "ಫೀಲ್ಡ್ ಫೋನ್‌ಗಳಿಂದ ಸಿಂಕ್ ಆದ ರೋಗಿಗಳು, ಸಂಪರ್ಕಿತ ಸಾಧನಗಳು ಮತ್ತು ಕೇಂದ್ರದ ಯಂತ್ರಾಂಶ ಸ್ಥಿತಿ.",
      kpiMlAnalytics: "ML ವಿಶ್ಲೇಷಣೆ ಮತ್ತು ಸಿಂಕ್",
      pendingShort: "ಬಾಕಿ:",
      syncedFeedTitle: "ತಕ್ಷಣ ಸಿಂಕ್ ಆದ ದಾಖಲೆಗಳು",
      syncedFeedDesc: "ಫೀಲ್ಡ್ ಸಾಧನಗಳಿಂದ ಇತ್ತೀಚಿನ ನೋಂದಣಿ, ವರ್ಗೀಕರಣ, ಧ್ವನಿ ಟಿಪ್ಪಣಿ, ತಪಾಸಣೆ ಮತ್ತು ಲಸಿಕೆಗಳು.",
      justSynced: "ಇದೀಗ ಸಿಂಕ್ ಆಗಿದೆ",
      noSyncedEvents: "ಇನ್ನೂ ಯಾವುದೇ ವೈದ್ಯಕೀಯ ಘಟನೆಗಳು ಸಿಂಕ್ ಆಗಿಲ್ಲ.",
      originPhone: "ಫೋನ್",
      originWatch: "ವಾಚ್",
      originHub: "ಮುಖ್ಯ ಕೇಂದ್ರ",
      mlAnalyticsTitle: "ಇತ್ತೀಚಿನ ML ವಿಶ್ಲೇಷಣೆ (GBDT + TreeSHAP)",
      mlAnalyticsDesc: "WHO ಸುರಕ್ಷತಾ ಮಾನದಂಡ + 28-Tree GBDT ಅಪಾಯ ಅಂಕ ಮತ್ತು SHAP ಕಾರಣಗಳು.",
      aboutSourcesTitle: "ಈ ವೈದ್ಯಕೀಯ ಮೂಲಗಳ ಅರ್ಥವೇನು?",
      aboutWho: "WHO IMNCI: ವಿಶ್ವ ಆರೋಗ್ಯ ಸಂಸ್ಥೆಯ (WHO) 0–5 ವರ್ಷದ ಮಕ್ಕಳ ತುರ್ತು ಅಪಾಯದ ಲಕ್ಷಣಗಳನ್ನು ಗುರುತಿಸುವ ಅಧಿಕೃತ ಮಾರ್ಗದರ್ಶಿ.",
      aboutNhm: "NHM ಆಶಾ ಮತ್ತು UIP: ಭಾರತ ಸರ್ಕಾರದ ಗರ್ಭಿಣಿ/ನವಜಾತ ಶಿಶು ಸುರಕ್ಷತಾ ನಿಯಮಗಳು ಹಾಗೂ ರಾಷ್ಟ್ರೀಯ ಲಸಿಕೆ ವೇಳಾಪಟ್ಟಿ.",
      aboutMl: "ಲ್ಯಾಪ್‌ಟಾಪ್ ML ಅಪಾಯ ಅಂಕ (GBDT + TreeSHAP): 13 ಆರೋಗ್ಯ ಅಂಶಗಳಿಂದ ಆದ್ಯತೆಯನ್ನು ತೋರಿಸುತ್ತದೆ — ಇದು WHO/NHM ತುರ್ತು ನಿಯಮಗಳನ್ನು ಎಂದಿಗೂ ಬದಲಾಯಿಸುವುದಿಲ್ಲ.",
      clinicalOpsTitle: "ವೈದ್ಯಕೀಯ ವರ್ಗೀಕರಣ, ಕ್ರಿಯಾ ಕಾರ್ಡ್‌ಗಳು ಮತ್ತು ಪ್ರಕೋಪ",
      sysDetailsTitle: "ವ್ಯವಸ್ಥೆಯ ವಿನ್ಯಾಸ ಮತ್ತು ಹಾರ್ಡ್‌ವೇರ್ ವಿವರಗಳು",
      showDetails: "ವಿವರ ತೋರಿಸಿ",
      hideDetails: "ವಿವರ ಮರೆಮಾಡಿ",
      whoFloorLabel: "WHO ಸುರಕ್ಷತಾ ಮಾನದಂಡ",
      laptopMlLabel: "ಲ್ಯಾಪ್‌ಟಾಪ್ ML",
      laptopMlModel: "28-Tree GBDT + TreeSHAP",
      recommendedFollowUpLabel: "ಶಿಫಾರಸು ಮಾಡಿದ ಮುಂದಿನ ಕ್ರಮ",
      matchedRulesLabel: "ನಿಯಮಗಳು",
    },
    ta: {
      appTitle: "ஆரோக்கிய வலையமைப்பு — ஆரம்ப சுகாதார நிலைய (PHC) கட்டுப்பாட்டு மையம்",
      appSubtitle: "இணையமில்லா தன்னாட்சி மருத்துவ வலையமைப்பு செயல்பாடுகள்",
      badgeTier: "நிலை-2 தலைமை மையம்",
      badgeOffline: "இணையமில்லா பாதுகாப்பு",
      langToggle: "தமிழ்",
      themeLight: "வெளிச்சம்",
      themeDark: "இருள்",
      autoOn: "தானியங்கி புதுப்பிப்பு: இயக்கம்",
      autoOff: "தானியங்கி புதுப்பிப்பு: நிறுத்தம்",
      refresh: "புதுப்பி",
      refreshing: "புதுப்பிக்கப்படுகிறது...",
      reconnecting: "மீண்டும் இணைக்கப்படுகிறது...",
      demoBarLabel: "நேரடி செயல்முறை காட்சிகள்",
      scenarioMaternal: "கர்ப்பிணி கடிகார அவசர அழைப்பு",
      scenarioVoice: "இணையமில்லா குரல் → AI",
      scenarioOutbreak: "கிராமத் தொற்று பரவல்",
      scenarioCrdt: "CRDT இணைப்பு சான்று",
      scMaternalTitle: "கர்ப்பிணி கடிகார அவசர அழைப்பு → ஆஷா தொலைபேசி",
      scVoiceTitle: "இணையமில்லா குரல் குறிப்பு → மைய AI பகுப்பாய்வு",
      scOutbreakTitle: "கிராம அளவிலான EWMA தொற்று பரவல் கண்டறிதல்",
      scCrdtTitle: "இணையமில்லா முரணற்ற CRDT தரவு இணைப்பு",
      demoReset: "மீட்டமை",
      openShowcase: "3-நிலை நேரடி மேடை திற →",
      demoLoading: "நேரடி மருத்துவ செயல்முறை இயங்குகிறது...",
      demoLoaded: "நேரடி CRDT ஒத்திசைவு மூலம் செயல்முறை நிறைவடைந்தது:",
      demoResetting: "தலைமை மையம் மீட்டமைக்கப்படுகிறது...",
      demoResetDone: "மைய நிகழ்வு பதிவேடு மற்றும் சாதனப் பட்டியல் சுத்தம் செய்யப்பட்டது.",
      demoUnavailable: "செயல்முறை சேவை தற்போது கிடைக்கவில்லை.",
      scenarioStepsLabel: "மருத்துவ செயல்முறை வரிசை",
      dismiss: "மூடு",
      archTitle: "திறன்-அடிப்படையிலான 3-நிலை தன்னாட்சி மருத்துவ வலையமைப்பு",
      tier0Label: "நிலை-0 கடிகாரம்",
      tier0Desc: "பொதுமக்கள் மற்றும் சுகாதாரப் பணியாளர்களுக்கான தனிப்பட்ட அவசர அழைப்பு & நினைவூட்டல்",
      tier0CapTag: "1-தொடு அவசரம் · BLE/LAN",
      tier1Label: "நிலை-1 தொலைபேசி",
      tier1Desc: "WHO IMNCI உறுதியான பரிசோதனை வகைப்பாடு + இணையமில்லா சேமிப்பு",
      tier1CapTag: "குரல் வரிசை · டெல்டா ஒத்திசைவு",
      tier2Label: "நிலை-2 தலைமை மையம்",
      tier2Desc: "குரல் எழுத்துமாற்றம் · SLM · LightGBM SHAP · EWMA தொற்று கண்டறிதல்",
      activePeersShort: "செயலில்",
      hubOnlineShort: "இணைப்பில்",
      nodeId: "மைய அடையாளம்",
      ram: "RAM நினைவகம்",
      cpu: "CPU கோர்கள்",
      npu: "NPU செயலி",
      npuAvailable: "உள்ளது",
      npuAbsent: "இல்லை",
      connectUrl: "உள்ளூர் LAN இணைப்பு",
      wsUrl: "வலையமைப்பு WebSocket",
      lastUpdated: "கடைசி புதுப்பிப்பு",
      patients: "பதிவான நோயாளிகள்",
      triageRed: "சிவப்பு — அவசர சிகிச்சை",
      triageYellow: "மஞ்சள் — PHC பரிசோதனை",
      triageGreen: "பச்சை — வீட்டுப் பராமரிப்பு",
      pendingEnrichments: "நிலுவை AI பகுப்பாய்வு",
      completedEnrichments: "முடிந்த பகுப்பாய்வு",
      totalEvents: "CRDT நிகழ்வுகள்",
      clinicalPanel: "மருத்துவ வகைப்பாடு, நடவடிக்கை அட்டைகள் & SHAP அபாய பகுப்பாய்வு",
      triageFeedTitle: "செயலில் உள்ள மருத்துவ வகைப்பாடுகள்",
      patientsRosterTitle: "ஒத்திசைக்கப்பட்ட நோயாளிகள் & சாதனங்கள்",
      peerTopology: "நேரடி வலையமைப்பு சாதனங்கள்",
      hubTelemetryTitle: "மைய வன்பொருள் & LAN இணைப்பு",
      runEnrichment: "AI பகுப்பாய்வு இயக்கு",
      runningEnrichment: "பகுப்பாய்வு நடைபெறுகிறது...",
      enrichmentDone: "AI பகுப்பாய்வு சுழற்சி நிறைவடைந்தது.",
      enrichmentUnavailable: "பகுப்பாய்வு சேவை தற்போது கிடைக்கவில்லை.",
      outbreakAlerts: "EWMA தொற்று பரவல் எச்சரிக்கைகள்",
      shapTitle: "SHAP அபாய காரணிகள் பகுப்பாய்வு",
      actionCards: "உடனடி நடவடிக்கை அட்டைகள்",
      eventLog: "HLC CRDT நிகழ்வுப் பதிவேடு ஆய்வாளர்",
      showEventLog: "பதிவேட்டைக் காட்டு",
      hideEventLog: "பதிவேட்டை மறை",
      filterEvents: "நிகழ்வு வகையைத் தேர்ந்தெடு",
      allEvents: "அனைத்து நிகழ்வுகள்",
      evPatientRegistered: "நோயாளி பதிவு",
      evTriageCompleted: "பரிசோதனை வகைப்பாடு முடிவு",
      evChecklistRecorded: "சரிபார்ப்புப் பட்டியல் பதிவு",
      evVaccinationLogged: "தடுப்பூசி பதிவு",
      evVoiceNoteRecorded: "குரல் குறிப்பு பதிவு",
      evEnrichmentCompleted: "AI பகுப்பாய்வு முடிவு",
      evActionCardIssued: "நடவடிக்கை அட்டை வெளியீடு",
      evOutbreakAlertRaised: "தொற்று எச்சரிக்கை வெளியீடு",
      synFebrile: "காய்ச்சல் சார்ந்த நோய்",
      synDiarrheal: "கடுமையான வயிற்றுப்போக்கு",
      synRespiratory: "கடுமையான சுவாசத் தொற்று",
      synMaternal: "கர்ப்பிணி அபாய அறிகுறி",
      synMalaria: "சந்தேகிக்கப்படும் மலேரியா பரவல்",
      synDengue: "சந்தேகிக்கப்படும் டெங்கு பரவல்",
      colHlc: "HLC நேரமுத்திரை",
      colOrigin: "மூல சாதனம்",
      colType: "நிகழ்வு வகை",
      colPatient: "நோயாளி",
      colEnrichment: "பகுப்பாய்வு நிலை",
      colSummary: "தரவு விவரம்",
      noPatients: "இன்னும் நோயாளிகள் ஒத்திசைக்கப்படவில்லை. மேலே உள்ள காட்சியை இயக்குங்கள்.",
      noTriage: "இன்னும் மருத்துவ வகைப்பாடுகள் பதிவாகவில்லை.",
      noPeers: "இன்னும் வலையமைப்பு சாதனங்கள் இணையவில்லை.",
      noOutbreaks: "செயலில் உள்ள தொற்று பரவல் எச்சரிக்கைகள் இல்லை.",
      noShap: "இன்னும் SHAP அபாய பகுப்பாய்வு கிடைக்கவில்லை.",
      noActionCards: "செயலில் உள்ள நடவடிக்கை அட்டைகள் இல்லை.",
      noEvents: "இன்னும் CRDT நிகழ்வுகள் பதிவாகவில்லை.",
      battery: "மின்கலம்",
      riskScore: "அபாய மதிப்பீடு",
      outbreakBannerPrefix: "செயலில் உள்ள EWMA தொற்று பரவல் எச்சரிக்கை",
      pregnantWeeks: "கர்ப்ப காலம்",
      weeksShort: "வாரம்",
      referralYes: "உடனடி PHC பரிந்துரை",
      eventsUnit: "நிகழ்வுகள்",
      peersUnit: "சாதனங்கள்",
      moreCount: "+{n} மேலும்",
      villagePrefix: "கிராமம்:",
      sevRed: "சிவப்பு · அவசர சிகிச்சை",
      sevYellow: "மஞ்சள் · PHC பரிசோதனை",
      sevGreen: "பச்சை · வீட்டுப் பராமரிப்பு",
      prioCritical: "மிக தீவிரம்",
      prioHigh: "அதிகம்",
      prioMedium: "நடுத்தரம்",
      prioLow: "குறைவு",
      statusOpen: "செயலில்",
      statusAcknowledged: "ஏற்றுக்கொள்ளப்பட்டது",
      statusCompleted: "நிறைவடைந்தது",
      statusDismissed: "நீக்கப்பட்டது",
      riskHigh: "அதிக அபாயம்",
      riskModerate: "நடுத்தர அபாயம்",
      riskLow: "குறைந்த அபாயம்",
      riskEnriched: "பகுப்பாய்வு செய்யப்பட்டது",
      enrPending: "நிலுவையில்",
      enrCompleted: "நிறைவடைந்தது",
      enrNotNeeded: "தேவையில்லை",
      enrFailed: "தோல்வியடைந்தது",
      watchModeChw: "சுகாதாரப் பணியாளர் துணை",
      watchModeFamily: "நோயாளி குடும்பம்",
      expandPayload: "முழு JSON விவரத்தைப் பார்க்க கிளிக் செய்க",
      collapsePayload: "விவரத்தைச் சுருக்க கிளிக் செய்க",
      proofCloudRpcs: "0 மேகக்கணி அழைப்புகள்",
      proofSafetyFloor: "WHO பாதுகாப்புத் தளம் · 1.00",
      proofZeroBloat: "0 PyTorch · 0 CUDA",
      convergedPatientsUnit: "ஒருங்கிணைந்த நோயாளிகள்",
      crdtMergeTitle: "CRDT முரணற்ற தரவு இணைப்பு சான்று (LWW)",
      zeroDataLoss: "பூஜ்ஜிய தரவு இழப்பு",
      simultaneousTieBreak: "ஒரே நேர HLC முரண் தீர்வு",
      convergedRecord: "ஒருங்கிணைந்த நோயாளி ஆவணம்",
      stageAudio: "ஒலி கோப்பு",
      stageAsr: "குரல் எழுத்துமாற்றம்",
      stageSlm: "கட்டமைப்பு SLM",
      stageTriage: "WHO விதி (1.00)",
      stageShap: "TreeSHAP",
      symptomsLabel: "அறிகுறிகள்",
      dangerFlagsLabel: "அபாயக் குறிகள்",
      shapPosLegend: "+ அபாயத்தை உயர்த்தும்",
      shapNegLegend: "- பாதுகாக்கும்",
      connectCardTitle: "மொபைல் / கடிகாரத்தை இந்த மையத்துடன் இணைக்கவும்",
      connectCardDesc: "உங்கள் தொலைபேசி ஒரே Wi-Fi/ஹாட்ஸ்பாட்டில் உள்ளதா என்பதை உறுதிசெய்து, இந்த முகவரியை உள்ளிடவும் அல்லது QR குறியீட்டை ஸ்கேன் செய்யவும்.",
      copyAddress: "முகவரியை நகலெடு",
      copiedAddress: "நகலெடுக்கப்பட்டது!",
      copyFailed: "நகலெடுப்பு தோல்வி",
      showQrCode: "QR குறியீட்டைக் காட்டு",
      hideQrCode: "QR குறியீட்டை மறை",
      qrScanTitle: "Field PWA அல்லது Android செயலியில் ஸ்கேன் செய்யவும்",
      qrScanHint: "Sync → Hub முகவரி → QR ஸ்கேன் என்பதைத் திறக்கவும்; முகவரி தானாக நிரப்பப்படும்.",
      clinicalPanelDesc: "அவசர நோயாளிகள், ஆஷா செயல் அட்டைகள், குரல் குறிப்பு அபாய மதிப்பெண் மற்றும் கிராம நோய் எச்சரிக்கைகள்.",
      patientsRosterDesc: "தொலைபேசிகளில் இருந்து ஒத்திசைக்கப்பட்ட நோயாளிகள், இணைந்த சாதனங்கள் மற்றும் மைய நிலை.",
      kpiMlAnalytics: "ML பகுப்பாய்வு & ஒத்திசைவு",
      pendingShort: "நிலுவை:",
      syncedFeedTitle: "உடனடியாக ஒத்திசைக்கப்பட்டவை",
      syncedFeedDesc: "களச் சாதனங்களிலிருந்து புதிய பதிவுகள், வகைப்பாடு, குரல் குறிப்பு, சரிபார்ப்பு & தடுப்பூசிகள்.",
      justSynced: "இப்போது ஒத்திசைக்கப்பட்டது",
      noSyncedEvents: "இன்னும் மருத்துவ நிகழ்வுகள் எதுவும் ஒத்திசைக்கப்படவில்லை.",
      originPhone: "தொலைபேசி",
      originWatch: "கடிகாரம்",
      originHub: "தலைமை மையம்",
      mlAnalyticsTitle: "சமீபத்திய ML பகுப்பாய்வு (GBDT + TreeSHAP)",
      mlAnalyticsDesc: "WHO பாதுகாப்புத் தளம் + 28-Tree GBDT அபாய மதிப்பீடு & SHAP காரணிகள்.",
      aboutSourcesTitle: "இந்த மருத்துவ ஆதாரங்களின் பொருள் என்ன?",
      aboutWho: "WHO IMNCI: உலக சுகாதார அமைப்பின் (WHO) 0–5 வயது குழந்தைகளின் அவசர அபாய அறிகுறிகளைக் கண்டறியும் அதிகாரப்பூர்வ கையேடு.",
      aboutNhm: "NHM ஆஷா & UIP: இந்திய அரசின் கர்ப்பிணி/பச்சிளம் குழந்தை பாதுகாப்பு விதிகள் மற்றும் தேசிய தடுப்பூசி அட்டவணை.",
      aboutMl: "மடிக்கணினி ML அபாய மதிப்பெண் (GBDT + TreeSHAP): 13 அளவீடுகளைக் கொண்டு முன்னுரிமையைக் காட்டுகிறது — இது WHO/NHM அவசர விதிகளை ஒருபோதும் மாற்றாது.",
      clinicalOpsTitle: "மருத்துவ வகைப்பாடு, நடவடிக்கை அட்டைகள் & பரவல்",
      sysDetailsTitle: "அமைப்பு வடிவமைப்பு & வன்பொருள் விவரங்கள்",
      showDetails: "விவரங்களைக் காட்டு",
      hideDetails: "விவரங்களை மறை",
      whoFloorLabel: "WHO பாதுகாப்புத் தளம்",
      laptopMlLabel: "மைய ML",
      laptopMlModel: "28-Tree GBDT + TreeSHAP",
      recommendedFollowUpLabel: "பரிந்துரைக்கப்பட்ட தொடர் நடவடிக்கை",
      matchedRulesLabel: "விதிகள்",
    },
  };

  const SCENARIO_TITLE_KEYS = {
    maternal_sos: "scMaternalTitle",
    pediatric_voice_offload: "scVoiceTitle",
    village_outbreak: "scOutbreakTitle",
    crdt_conflict_merge: "scCrdtTitle",
  };

  const LOCALIZED_SCENARIOS = {
    hi: {
      maternal_sos: {
        title: "मातृ घटिका आपात संकेत → आशा दूरभाष",
        persona: "गर्भवती परिवार घटिका → आशा दीदी",
        subtitle: "गम्भीर मातृ संकट लक्षण एक-स्पर्श में घटिका से मुख्य केन्द्र एवं आशा दूरभाष तक पहुँचते हैं।",
        steps: [
          "परिवार घटिका पर गर्भावस्था संकट संकेत अंकित हुआ।",
          "निश्चित विश्व स्वास्थ्य नियम द्वारा रक्त-आपात वर्गीकरण पूर्ण।",
          "मुख्य केन्द्र ने तत्काल स्वास्थ्य केन्द्र प्रेषण कार्य पत्रक जारी किया।",
        ],
      },
      pediatric_voice_offload: {
        title: "अन्तर्जाल-रहित स्वर → मुख्य केन्द्र प्रज्ञा संवर्धन",
        persona: "आशा दूरभाष → मुख्य केन्द्र प्रज्ञा",
        subtitle: "क्षेत्रीय स्वर टिप्पणी स्थानीय संजाल द्वारा मुख्य केन्द्र पर आकर ध्वनि अनुलेखन एवं संकट कारक विश्लेषण करती है।",
        steps: [
          "आशा दूरभाष ने अन्तर्जाल-रहित अवस्था में स्वर टिप्पणी सहेजी।",
          "मुख्य केन्द्र ने ध्वनि अनुलेखन, लक्षण निष्कर्षण एवं निश्चित वर्गीकरण किया।",
          "संकट कारक विश्लेषण एवं कार्य पत्रक सभी सहकर्मियों पर समन्वित।",
        ],
      },
      village_outbreak: {
        title: "ग्राम संक्रमण प्रकोप संसूचन",
        persona: "बहु-कर्मी संजाल → मुख्य केन्द्र निगरानी",
        subtitle: "विभिन्न स्वास्थ्य कर्मियों के अभिलेखों से ग्राम में ज्वर अथवा अतिसार वृद्धि का स्वतः संसूचन।",
        steps: [
          "एकाधिक आशा दूरभाषों से ग्राम रोगी घटनाएँ समन्वित हुईं।",
          "मुख्य केन्द्र की सांख्यिकीय निगरानी ने असामान्य वृद्धि पहचानी।",
          "संक्रमण प्रकोप चेतावनी एवं ग्राम कार्य निर्देश जारी हुए।",
        ],
      },
      crdt_conflict_merge: {
        title: "अन्तर्जाल-रहित द्वन्द्व-रहित विलय प्रमाण",
        persona: "दूरभाष एवं घटिका समकालीन अद्यतन",
        subtitle: "समान क्षण पर दो उपकरणों के अद्यतन बिना किसी तथ्यांश हानि के एकीकृत रोगी अभिलेख में विलीन होते हैं।",
        steps: [
          "आशा दूरभाष एवं परिवार घटिका ने पृथक-पृथक अद्यतन अंकित किए।",
          "कालक्रम मुहर द्वारा प्रत्येक क्षेत्र का द्वन्द्व-रहित विलय सम्पन्न।",
          "दोनों अद्यतन सुरक्षित रहकर एकीकृत रोगी पंजिका निर्मित हुई।",
        ],
      },
    },
    kn: {
      maternal_sos: {
        title: "ಗರ್ಭಿಣಿ ವಾಚ್ ತುರ್ತು ಕರೆ → ಆಶಾ ಫೋನ್",
        persona: "ಕುಟುಂಬ ವಾಚ್ → ಆಶಾ ಕಾರ್ಯಕರ್ತೆ",
        subtitle: "ಗರ್ಭಿಣಿಯ ಅಪಾಯದ ಲಕ್ಷಣವು ಒಂದೇ ಸ್ಪರ್ಶದಲ್ಲಿ ವಾಚ್‌ನಿಂದ ಮುಖ್ಯ ಕೇಂದ್ರ ಮತ್ತು ಆಶಾ ಫೋನ್‌ಗೆ ತಲುಪುತ್ತದೆ.",
        steps: [
          "ಕುಟುಂಬದ ವಾಚ್‌ನಲ್ಲಿ ಗರ್ಭಿಣಿ ಅಪಾಯದ ತುರ್ತು ಕರೆ ದಾಖಲಾಗಿದೆ.",
          "WHO ಖಚಿತ ನಿಯಮದಂತೆ ಕೆಂಪು ತುರ್ತು ವರ್ಗೀಕರಣ ಪೂರ್ಣಗೊಂಡಿದೆ.",
          "ತಕ್ಷಣ PHC ಗೆ ಕರೆದೊಯ್ಯಲು ತುರ್ತು ಕ್ರಿಯಾ ಕಾರ್ಡ್ ಜಾರಿಯಾಗಿದೆ.",
        ],
      },
      pediatric_voice_offload: {
        title: "ಆಫ್‌ಲೈನ್ ಧ್ವನಿ ಟಿಪ್ಪಣಿ → ಕೇಂದ್ರದ AI ವಿಶ್ಲೇಷಣೆ",
        persona: "ಆಶಾ ಫೋನ್ → PHC ಕೇಂದ್ರ AI",
        subtitle: "ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿ ದಾಖಲಿಸಿದ ಧ್ವನಿ ಟಿಪ್ಪಣಿಯು ಮುಖ್ಯ ಕೇಂದ್ರದಲ್ಲಿ ಲಿಪ್ಯಂತರ ಹಾಗೂ SHAP ಅಪಾಯ ವಿಶ್ಲೇಷಣೆಗೆ ಒಳಪಡುತ್ತದೆ.",
        steps: [
          "ಆಶಾ ಕಾರ್ಯಕರ್ತೆ ಇಂಟರ್ನೆಟ್ ಇಲ್ಲದೆ ಧ್ವನಿ ಟಿಪ್ಪಣಿ ದಾಖಲಿಸಿದ್ದಾರೆ.",
          "ಮುಖ್ಯ ಕೇಂದ್ರವು ಧ್ವನಿ ಲಿಪ್ಯಂತರ, ಲಕ್ಷಣ ಗುರುತಿಸುವಿಕೆ ಮತ್ತು WHO ವರ್ಗೀಕರಣ ನಡೆಸಿದೆ.",
          "SHAP ಅಪಾಯ ಕಾರಣಗಳು ಮತ್ತು ಕ್ರಿಯಾ ಕಾರ್ಡ್ ಎಲ್ಲಾ ಸಾಧನಗಳಿಗೆ ಸಿಂಕ್ ಆಗಿವೆ.",
        ],
      },
      village_outbreak: {
        title: "ಗ್ರಾಮ ಮಟ್ಟದ EWMA ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ ಪತ್ತೆ",
        persona: "ಬಹು-ಕಾರ್ಯಕರ್ತ ಜಾಲ → PHC ಕಣ್ಗಾವಲು",
        subtitle: "ವಿವಿಧ ಆರೋಗ್ಯ ಕಾರ್ಯಕರ್ತೆಯರ ದಾಖಲೆಗಳಿಂದ ಗ್ರಾಮದಲ್ಲಿ ಜ್ವರ ಅಥವಾ ಅತಿಸಾರ ಹೆಚ್ಚಳವನ್ನು ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಪತ್ತೆಹಚ್ಚುತ್ತದೆ.",
        steps: [
          "ಹಲವು ಆಶಾ ಫೋನ್‌ಗಳಿಂದ ಗ್ರಾಮದ ರೋಗಿಗಳ ವಿವರಗಳು ಸಿಂಕ್ ಆಗಿವೆ.",
          "ಮುಖ್ಯ ಕೇಂದ್ರದ EWMA ವಿಶ್ಲೇಷಣೆ ಅಸಹಜ ಪ್ರಕರಣಗಳ ಏರಿಕೆಯನ್ನು ಗುರುತಿಸಿದೆ.",
          "ಗ್ರಾಮ ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ ಎಚ್ಚರಿಕೆ ಮತ್ತು ಕ್ರಮ ಸೂಚನೆ ಜಾರಿಯಾಗಿದೆ.",
        ],
      },
      crdt_conflict_merge: {
        title: "ಆಫ್‌ಲೈನ್ ದ್ವಂದ್ವ-ರಹಿತ CRDT ವಿಲೀನ ಪುರಾವೆ",
        persona: "ಫೋನ್ ಮತ್ತು ವಾಚ್ ಏಕಕಾಲದ ನವೀಕರಣ",
        subtitle: "ಒಂದೇ ಸಮಯದಲ್ಲಿ ಎರಡು ಸಾಧನಗಳಲ್ಲಿ ಮಾಡಿದ ಬದಲಾವಣೆಗಳು ಯಾವುದೇ ದತ್ತಾಂಶ ನಷ್ಟವಿಲ್ಲದೆ ಒಂದೇ ದಾಖಲೆಯಾಗಿ ವಿಲೀನಗೊಳ್ಳುತ್ತವೆ.",
        steps: [
          "ಆಶಾ ಫೋನ್ ಮತ್ತು ಕುಟುಂಬದ ವಾಚ್ ಪ್ರತ್ಯೇಕವಾಗಿ ರೋಗಿ ವಿವರ ನವೀಕರಿಸಿವೆ.",
          "HLC ಸಮಯಮುದ್ರೆ ಮೂಲಕ ಪ್ರತಿ ಕ್ಷೇತ್ರದ ದ್ವಂದ್ವ-ರಹಿತ ವಿಲೀನ ಪೂರ್ಣಗೊಂಡಿದೆ.",
          "ಎರಡೂ ಮಾಹಿತಿಗಳು ಸುರಕ್ಷಿತವಾಗಿ ಉಳಿದು ಸಂಯೋಜಿತ ರೋಗಿ ದಾಖಲೆ ಸಿದ್ಧವಾಗಿದೆ.",
        ],
      },
    },
    ta: {
      maternal_sos: {
        title: "கர்ப்பிணி கடிகார அவசர அழைப்பு → ஆஷா தொலைபேசி",
        persona: "குடும்பக் கடிகாரம் → ஆஷா பணியாளர்",
        subtitle: "கர்ப்பிணியின் அபாய அறிகுறி ஒரே தொடுதலில் கடிகாரத்திலிருந்து தலைமை மையம் மற்றும் ஆஷா தொலைபேசிக்குச் சென்றடைகிறது.",
        steps: [
          "குடும்பக் கடிகாரத்தில் கர்ப்பிணி அபாய அவசர அழைப்பு பதிவானது.",
          "WHO உறுதியான விதியின்படி சிவப்பு அவசர வகைப்பாடு நிறைவடைந்தது.",
          "உடனடியாக ஆரம்ப சுகாதார நிலையத்திற்கு அழைத்துச் செல்ல நடவடிக்கை அட்டை வெளியிடப்பட்டது.",
        ],
      },
      pediatric_voice_offload: {
        title: "இணையமில்லா குரல் குறிப்பு → மைய AI பகுப்பாய்வு",
        persona: "ஆஷா தொலைபேசி → PHC மைய AI",
        subtitle: "இணையமின்றி பதிவு செய்யப்பட்ட குரல் குறிப்பு தலைமை மையத்தில் எழுத்துமாற்றம் மற்றும் SHAP அபாய பகுப்பாய்விற்கு உட்படுகிறது.",
        steps: [
          "ஆஷா பணியாளர் இணையமின்றி குரல் குறிப்பைப் பதிவு செய்தார்.",
          "தலைமை மையம் குரல் எழுத்துமாற்றம், அறிகுறி அடையாளம் மற்றும் WHO வகைப்பாட்டை மேற்கொண்டது.",
          "SHAP அபாய காரணிகள் மற்றும் நடவடிக்கை அட்டை அனைத்து சாதனங்களுக்கும் ஒத்திசைக்கப்பட்டன.",
        ],
      },
      village_outbreak: {
        title: "கிராம அளவிலான EWMA தொற்று பரவல் கண்டறிதல்",
        persona: "பல-பணியாளர் வலையமைப்பு → PHC கண்காணிப்பு",
        subtitle: "பல்வேறு சுகாதாரப் பணியாளர்களின் பதிவுகளிலிருந்து கிராமத்தில் காய்ச்சல் அல்லது வயிற்றுப்போக்கு உயர்வைத் தானாகக் கண்டறிகிறது.",
        steps: [
          "பல ஆஷா தொலைபேசிகளிலிருந்து கிராம நோயாளி விவரங்கள் ஒத்திசைக்கப்பட்டன.",
          "தலைமை மையத்தின் EWMA பகுப்பாய்வு வழக்கத்திற்கு மாறான பரவலைக் கண்டறிந்தது.",
          "கிராமத் தொற்று பரவல் எச்சரிக்கையும் செயல்பாட்டு அறிவுறுத்தலும் வெளியிடப்பட்டன.",
        ],
      },
      crdt_conflict_merge: {
        title: "இணையமில்லா முரணற்ற CRDT தரவு இணைப்பு",
        persona: "தொலைபேசி மற்றும் கடிகாரம் ஒரே நேர புதுப்பிப்பு",
        subtitle: "ஒரே நேரத்தில் இரு சாதனங்களில் செய்யப்பட்ட மாற்றங்கள் எந்தத் தரவு இழப்புமின்றி ஒரே நோயாளி ஆவணமாக இணைகின்றன.",
        steps: [
          "ஆஷா தொலைபேசியும் குடும்பக் கடிகாரமும் தனித்தனியாக நோயாளி விவரத்தைப் புதுப்பித்தன.",
          "HLC நேரமுத்திரை மூலம் ஒவ்வொரு புலமும் முரணின்றி இணைக்கப்பட்டது.",
          "இரு தகவல்களும் பாதுகாப்பாக இணைந்து ஒருங்கிணைந்த நோயாளி ஆவணம் உருவானது.",
        ],
      },
    },
  };

  const state = {
    lang: "en",
    theme: "dark",
    autoRefresh: true,
    timerId: null,
    refreshing: false,
    reconnecting: false,
    enriching: false,
    demoBusy: false,
    copyFeedbackKey: null,
    copyTimerId: null,
    selectedEventType: "",
    eventsExpanded: false,
    sysDetailsExpanded: false,
    crdtExpanded: false,
    qrExpanded: false,
    hubLanUrl: "",
    activeScenario: null,
    scenarioCatalog: {},
    narrativeDismissed: false,
    demoStatus: null,
    enrichmentStatusKey: null,
    expandedEventIds: new Set(),
    lastSummary: null,
    lastPeers: [],
    lastConnectInfo: null,
    lastEvents: [],
  };

  function readStoredPref(key, allowed, fallback) {
    try {
      const value = window.localStorage.getItem(key);
      if (value && allowed.includes(value)) return value;
    } catch (_err) {
      // Ignore storage access errors in restricted contexts
    }
    return fallback;
  }

  function writeStoredPref(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (_err) {
      // Ignore storage access errors in restricted contexts
    }
  }

  function t(key) {
    return (I18N[state.lang] && I18N[state.lang][key]) || I18N.en[key] || key;
  }

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (k === "className") {
          node.className = v;
        } else if (v !== null && v !== undefined) {
          node.setAttribute(k, String(v));
        }
      }
    }
    for (const child of children) {
      if (child === null || child === undefined) continue;
      if (typeof child === "string" || typeof child === "number") {
        node.appendChild(document.createTextNode(String(child)));
      } else {
        node.appendChild(child);
      }
    }
    return node;
  }

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = String(value);
  }

  function severityStyle(severity) {
    if (severity === "RED_EMERGENCY") {
      return { badge: "badge badge-red", card: "item-card item-card-red" };
    }
    if (severity === "YELLOW_PHC") {
      return { badge: "badge badge-yellow", card: "item-card item-card-yellow" };
    }
    return { badge: "badge badge-green", card: "item-card item-card-green" };
  }

  function formatHlc(hlc) {
    if (!hlc) return "--";
    return `${hlc.wall_ms}:${hlc.logical}:${hlc.node_id}`;
  }

  function buildPatientNameMap(patients) {
    const map = new Map();
    if (!Array.isArray(patients)) return map;
    for (const pat of patients) {
      if (pat && pat.patient_id && pat.full_name) {
        map.set(String(pat.patient_id), String(pat.full_name));
      }
    }
    return map;
  }

  function formatPatientLabel(patientId, nameMap) {
    if (!patientId) return "--";
    const idStr = String(patientId);
    const fullName = nameMap && nameMap.get(idStr);
    return fullName ? `${fullName} (${idStr})` : idStr;
  }

  function buildPatientHeadingNode(patientId, nameMap, fallbackId) {
    const idStr = patientId ? String(patientId) : "";
    const fullName = idStr && nameMap ? nameMap.get(idStr) : null;
    if (fullName) {
      return el(
        "span",
        { className: "item-card-title", title: formatPatientLabel(idStr, nameMap) },
        fullName,
        el("span", { className: "patient-id-sub mono" }, idStr)
      );
    }
    return el("span", { className: "item-card-title mono" }, idStr || fallbackId || "--");
  }

  function humanizeToken(raw) {
    return String(raw || "")
      .replace(/[_-]+/g, " ")
      .replace(/\b\w/g, (ch) => ch.toUpperCase())
      .replace(/\bBp\b/g, "BP")
      .replace(/\bSpo2\b/g, "SpO2")
      .replace(/\bPhc\b/g, "PHC")
      .replace(/\bWho\b/g, "WHO")
      .trim();
  }

  function formatMoreCounter(remaining) {
    return t("moreCount").replace("{n}", String(remaining));
  }

  function translateSeverity(severity) {
    if (severity === "RED_EMERGENCY") return t("sevRed");
    if (severity === "YELLOW_PHC") return t("sevYellow");
    if (severity === "GREEN_HOME") return t("sevGreen");
    return severity || "--";
  }

  function translatePriority(priority) {
    if (priority === "CRITICAL") return t("prioCritical");
    if (priority === "HIGH") return t("prioHigh");
    if (priority === "MEDIUM") return t("prioMedium");
    if (priority === "LOW") return t("prioLow");
    return priority || t("prioMedium");
  }

  function translateActionStatus(status) {
    if (status === "OPEN") return t("statusOpen");
    if (status === "ACKNOWLEDGED") return t("statusAcknowledged");
    if (status === "COMPLETED") return t("statusCompleted");
    if (status === "DISMISSED") return t("statusDismissed");
    return status || t("statusOpen");
  }

  function translateRiskBand(band) {
    if (band === "RED_EMERGENCY") return t("sevRed");
    if (band === "YELLOW_PHC") return t("sevYellow");
    if (band === "GREEN_HOME") return t("sevGreen");
    if (band === "HIGH") return t("riskHigh");
    if (band === "MODERATE" || band === "MEDIUM") return t("riskModerate");
    if (band === "LOW") return t("riskLow");
    return band || t("riskEnriched");
  }

  function translateEnrichmentState(enrState) {
    if (enrState === "PENDING") return t("enrPending");
    if (enrState === "COMPLETED") return t("enrCompleted");
    if (enrState === "FAILED") return t("enrFailed");
    if (enrState === "NOT_NEEDED" || !enrState) return t("enrNotNeeded");
    return enrState;
  }

  function translateTier(tier) {
    if (tier === "TIER_0_WATCH") return t("tier0Label");
    if (tier === "TIER_1_PHONE") return t("tier1Label");
    if (tier === "TIER_2_HUB") return t("tier2Label");
    return tier || "";
  }

  function translateWatchMode(mode) {
    if (mode === "CHW_COMPANION") return t("watchModeChw");
    if (mode === "PATIENT_FAMILY") return t("watchModeFamily");
    return mode || "";
  }

  function readInitialLang() {
    try {
      const params = new URLSearchParams(window.location.search);
      const qLang = params.get("lang");
      if (qLang && SUPPORTED_LANGS.includes(qLang)) {
        writeStoredPref(STORAGE_LANG_KEY, qLang);
        return qLang;
      }
    } catch (_err) {
      // Ignore URL parsing errors
    }
    return readStoredPref(STORAGE_LANG_KEY, SUPPORTED_LANGS, "en");
  }

  function translateEventType(eventType) {
    const map = {
      PATIENT_REGISTERED: "evPatientRegistered",
      TRIAGE_COMPLETED: "evTriageCompleted",
      CHECKLIST_RECORDED: "evChecklistRecorded",
      VACCINATION_LOGGED: "evVaccinationLogged",
      VOICE_NOTE_RECORDED: "evVoiceNoteRecorded",
      ENRICHMENT_COMPLETED: "evEnrichmentCompleted",
      ACTION_CARD_ISSUED: "evActionCardIssued",
      OUTBREAK_ALERT_RAISED: "evOutbreakAlertRaised",
    };
    const key = map[eventType];
    return key ? t(key) : eventType || "--";
  }

  function translateSyndrome(syndrome) {
    const raw = String(syndrome || "").toLowerCase();
    if (raw === "febrile_illness" || raw === "fever") return t("synFebrile");
    if (raw === "acute_diarrheal_disease" || raw === "diarrhea" || raw === "diarrheal_illness") {
      return t("synDiarrheal");
    }
    if (raw === "acute_respiratory_illness" || raw === "respiratory_illness") {
      return t("synRespiratory");
    }
    if (raw === "maternal_danger" || raw === "maternal_emergency") return t("synMaternal");
    if (raw === "malaria") return t("synMalaria");
    if (raw === "dengue") return t("synDengue");
    return syndrome || "";
  }

  function syncLangSwitcher() {
    const btns = document.querySelectorAll("#lang-switcher [data-lang]");
    for (const btn of btns) {
      const isSelected = btn.getAttribute("data-lang") === state.lang;
      btn.classList.toggle("active", isSelected);
      btn.setAttribute("aria-pressed", String(isSelected));
    }
  }

  function applyTranslations() {
    document.documentElement.lang = state.lang;
    document.title = t("appTitle");
    setText("app-title", t("appTitle"));
    setText("app-subtitle", t("appSubtitle"));
    setText("badge-tier", t("badgeTier"));
    setText("badge-offline-text", state.reconnecting ? t("reconnecting") : t("badgeOffline"));
    syncLangSwitcher();
    setText("btn-theme", state.theme === "dark" ? t("themeLight") : t("themeDark"));
    setText("btn-autorefresh", state.autoRefresh ? t("autoOn") : t("autoOff"));
    setText("btn-refresh", state.refreshing ? t("refreshing") : t("refresh"));
    setText("btn-toggle-events", state.eventsExpanded ? t("hideEventLog") : t("showEventLog"));
    setText("btn-toggle-sys-details", state.sysDetailsExpanded ? t("hideDetails") : t("showDetails"));
    setText("btn-toggle-crdt", state.crdtExpanded ? t("hideDetails") : t("showDetails"));
    setText("btn-toggle-qr", state.qrExpanded ? t("hideQrCode") : t("showQrCode"));

    const nodes = document.querySelectorAll("[data-i18n]");
    for (const node of nodes) {
      const key = node.getAttribute("data-i18n");
      if (key) node.textContent = t(key);
    }
    if (state.enriching) {
      setText("btn-run-enrichment", t("runningEnrichment"));
    }
    if (state.copyFeedbackKey) {
      setText("btn-copy-hub-url", t(state.copyFeedbackKey));
    }
    setText("btn-toggle-events", state.eventsExpanded ? t("hideEventLog") : t("showEventLog"));
    setText("btn-toggle-sys-details", state.sysDetailsExpanded ? t("hideDetails") : t("showDetails"));
    setText("btn-toggle-crdt", state.crdtExpanded ? t("hideDetails") : t("showDetails"));
    setText("btn-toggle-qr", state.qrExpanded ? t("hideQrCode") : t("showQrCode"));

    if (state.enrichmentStatusKey) {
      const status = document.getElementById("enrichment-status");
      if (status) {
        status.classList.remove("hidden");
        status.textContent = t(state.enrichmentStatusKey);
      }
    }
    renderDemoStatus();
  }

  function renderManifest(summary, connectInfo) {
    const manifest = summary && summary.manifest ? summary.manifest : null;
    if (manifest) {
      setText("manifest-node-id", manifest.node_id || "--");
      setText("arch-hub-node", manifest.node_id || "phc-hub-local");
      const ramGb = manifest.ram_mb ? `${Math.max(1, Math.round(manifest.ram_mb / 1024))} GB` : "32 GB";
      setText("arch-hub-ram", ramGb);
      setText("manifest-ram", manifest.ram_mb ? `${manifest.ram_mb} MB` : "--");
      setText("manifest-cpu", manifest.cpu_cores || "--");
      setText("manifest-npu", manifest.has_npu ? t("npuAvailable") : t("npuAbsent"));
    }

    if (summary && summary.latest_hlc) {
      setText("arch-hlc-badge", `HLC: ${formatHlc(summary.latest_hlc)}`);
    } else {
      setText("arch-hlc-badge", "HLC: --");
    }

    const httpUrl =
      (connectInfo &&
        (connectInfo.preferred_url ||
          connectInfo.http_url ||
          connectInfo.base_url ||
          connectInfo.lan_url)) ||
      (summary && summary.hub_lan_url) ||
      window.location.origin;
    const wsUrl =
      (connectInfo && (connectInfo.ws_url || connectInfo.websocket_url)) ||
      `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/mesh`;
    state.hubLanUrl = httpUrl;
    setText("connect-url", httpUrl);
    setText("connect-ws", wsUrl);
    setText("hub-lan-url", httpUrl);
    setText("hub-qr-url-caption", httpUrl);
    const qrImg = document.getElementById("hub-qr-img");
    if (qrImg) {
      const nextSrc = `/api/v1/hub-qr.svg?text=${encodeURIComponent(httpUrl)}`;
      if (qrImg.getAttribute("data-qr-url") !== httpUrl) {
        qrImg.setAttribute("data-qr-url", httpUrl);
        qrImg.src = nextSrc;
      }
    }
  }

  function renderKpis(summary) {
    if (!summary) return;
    const tc = summary.triage_counts || {};
    setText("kpi-patients", summary.patient_count ?? 0);
    setText("kpi-red", tc.RED_EMERGENCY ?? 0);
    setText("kpi-yellow", tc.YELLOW_PHC ?? 0);
    setText("kpi-green", tc.GREEN_HOME ?? 0);
    setText("kpi-pending", summary.pending_enrichments ?? 0);
    setText("kpi-completed", summary.completed_enrichments ?? 0);
    setText("kpi-events", summary.event_count ?? 0);
    setText("event-log-count", summary.event_count ?? 0);
  }

  function renderPatients(patients) {
    const container = document.getElementById("patients-list");
    if (!container) return;

    const list = Array.isArray(patients) ? patients : [];
    if (list.length === 0) {
      container.replaceChildren(el("p", { className: "empty-state" }, t("noPatients")));
      return;
    }

    const limit = 8;
    const cards = list.slice(0, limit).map((pat) => {
      const chips = [];
      if (pat.village_id) chips.push(el("span", { className: "meta-chip mono" }, pat.village_id));
      if (pat.is_pregnant) {
        const wk = pat.gestational_weeks ? ` · ${pat.gestational_weeks} ${t("weeksShort")}` : "";
        chips.push(el("span", { className: "meta-chip" }, `${t("pregnantWeeks")}${wk}`));
      }
      if (pat.metadata && typeof pat.metadata === "object") {
        for (const [k, v] of Object.entries(pat.metadata).slice(0, 3)) {
          chips.push(el("span", { className: "meta-chip mono" }, `${k}: ${String(v)}`));
        }
      }

      return el(
        "div",
        { className: "item-card" },
        el(
          "div",
          { className: "item-card-head" },
          el("span", { className: "item-card-title" }, pat.full_name || pat.patient_id),
          el("span", { className: "badge badge-brand mono" }, pat.patient_id)
        ),
        chips.length > 0 ? el("div", { className: "meta-chips" }, ...chips) : null
      );
    });
    if (list.length > limit) {
      cards.push(el("span", { className: "more-counter" }, formatMoreCounter(list.length - limit)));
    }
    container.replaceChildren(...cards);
  }

  function renderTriageHistory(summary, nameMap) {
    const container = document.getElementById("triage-list");
    if (!container) return;

    const history = summary && Array.isArray(summary.triage_history) ? summary.triage_history : [];
    const enrichmentTriages = [];
    if (summary && Array.isArray(summary.enrichments)) {
      for (const enr of summary.enrichments) {
        const ta = enr && enr.payload && enr.payload.triage_assessment;
        if (ta && typeof ta === "object" && ta.severity) {
          enrichmentTriages.push(ta);
        }
      }
    }
    const combined = [...history, ...enrichmentTriages].reverse();
    setText("triage-count-badge", combined.length);

    if (combined.length === 0) {
      container.replaceChildren(el("p", { className: "empty-state" }, t("noTriage")));
      return;
    }

    const limit = 6;
    const cards = combined.slice(0, limit).map((item) => {
      const style = severityStyle(item.severity);
      const rules = Array.isArray(item.matched_rules) ? item.matched_rules.map(humanizeToken).join(", ") : "";
      return el(
        "div",
        { className: style.card },
        el(
          "div",
          { className: "item-card-head" },
          buildPatientHeadingNode(item.patient_id, nameMap, item.assessment_id),
          el("span", { className: style.badge }, translateSeverity(item.severity))
        ),
        item.rationale ? el("div", { className: "item-card-meta" }, item.rationale) : null,
        rules
          ? el("div", { className: "item-card-meta mono" }, rules)
          : null,
        item.referral_required
          ? el("div", { className: "meta-chips" }, el("span", { className: "badge badge-red" }, t("referralYes")))
          : null
      );
    });
    if (combined.length > limit) {
      cards.push(
        el("span", { className: "more-counter" }, formatMoreCounter(combined.length - limit))
      );
    }
    container.replaceChildren(...cards);
  }

  function renderPeers(peers) {
    const container = document.getElementById("peers-list");
    if (!container) return;

    const list = Array.isArray(peers) ? peers : [];
    setText("peer-count-badge", list.length);

    let tier0 = 0;
    let tier1 = 0;
    for (const p of list) {
      const tier = (p.manifest && p.manifest.tier) || p.tier || "";
      if (tier === "TIER_0_WATCH") tier0 += 1;
      if (tier === "TIER_1_PHONE") tier1 += 1;
    }
    setText("tier0-count", tier0);
    setText("tier1-count", tier1);

    const card0 = document.getElementById("arch-tier-0");
    const card1 = document.getElementById("arch-tier-1");
    if (card0) card0.classList.toggle("arch-tier-active", tier0 > 0);
    if (card1) card1.classList.toggle("arch-tier-active", tier1 > 0);

    if (list.length === 0) {
      container.replaceChildren(el("p", { className: "empty-state" }, t("noPeers")));
      return;
    }

    const cards = list.map((peer) => {
      const m = peer.manifest || peer;
      const nodeId = m.node_id || peer.node_id || "unknown-peer";
      const tier = m.tier || peer.tier || "PEER";
      const battery = m.battery_pct !== undefined ? `${t("battery")}: ${m.battery_pct}%` : "";
      const mode = m.watch_mode ? ` · ${translateWatchMode(m.watch_mode)}` : "";
      const source = peer.source ? ` · ${peer.source}` : "";
      const metaParts = [battery, mode, source].filter(Boolean).join(" ");

      return el(
        "div",
        { className: "item-card" },
        el(
          "div",
          { className: "item-card-head" },
          el("span", { className: "item-card-title mono" }, nodeId),
          el("span", { className: "badge badge-accent" }, translateTier(tier))
        ),
        metaParts ? el("div", { className: "item-card-meta" }, metaParts) : null
      );
    });
    container.replaceChildren(...cards);
  }

  function renderOutbreaks(alerts) {
    const banner = document.getElementById("outbreak-banner");
    const container = document.getElementById("outbreak-list");
    const list = Array.isArray(alerts) ? alerts : [];
    setText("outbreak-count-badge", list.length);

    if (banner) {
      if (list.length > 0) {
        const latest = list[list.length - 1];
        const p = latest.payload || {};
        const detail =
          p.message ||
          (p.syndrome ? translateSyndrome(p.syndrome) : null) ||
          (p.village_id ? `${t("villagePrefix")} ${p.village_id}` : null) ||
          latest.event_id;
        banner.classList.remove("hidden");
        banner.replaceChildren(
          el("strong", null, `${t("outbreakBannerPrefix")}: ${detail}`),
          el("span", { className: "badge badge-red" }, String(list.length))
        );
      } else {
        banner.classList.add("hidden");
        banner.replaceChildren();
      }
    }

    if (!container) return;
    if (list.length === 0) {
      container.replaceChildren(el("p", { className: "empty-state" }, t("noOutbreaks")));
      return;
    }

    const cards = list.map((alert) => {
      const p = alert.payload || {};
      const title = p.syndrome
        ? translateSyndrome(p.syndrome)
        : p.disease || p.title || translateEventType(alert.event_type);
      const village = p.village_id ? `${t("villagePrefix")} ${p.village_id}` : "EWMA";
      const detail = p.message || p.rationale || JSON.stringify(p);
      return el(
        "div",
        { className: "item-card item-card-red" },
        el(
          "div",
          { className: "item-card-head" },
          el("span", { className: "item-card-title" }, title),
          el("span", { className: "badge badge-red" }, village)
        ),
        el("div", { className: "item-card-meta" }, detail)
      );
    });
    container.replaceChildren(...cards);
  }

  function normalizeShapEntries(raw) {
    if (Array.isArray(raw)) {
      return raw
        .map((item) => {
          if (item && typeof item === "object") {
            const name = item.feature || item.name || "feature";
            const value = Number(item.contribution ?? item.value ?? item.shap ?? 0);
            return { name: String(name), value: Number.isFinite(value) ? value : 0 };
          }
          return null;
        })
        .filter(Boolean);
    }
    if (raw && typeof raw === "object") {
      return Object.entries(raw).map(([name, val]) => ({
        name,
        value: Number.isFinite(Number(val)) ? Number(val) : 0,
      }));
    }
    return [];
  }

  function formatCompactFieldValue(val) {
    if (Array.isArray(val)) return val.join(", ");
    if (typeof val === "boolean") return val ? "true" : "false";
    return String(val);
  }

  function renderEngineeringProofStrip(summary) {
    const ep = (summary && summary.engineering_proof) || {};
    const eventsCount = summary ? summary.event_count ?? 0 : 0;
    const patientCount = summary ? summary.patient_count ?? 0 : 0;
    const hlcText =
      summary && summary.latest_hlc ? `HLC ${formatHlc(summary.latest_hlc)}` : "HLC --";

    setText("dash-proof-cloud", t("proofCloudRpcs"));
    setText("dash-proof-safety", t("proofSafetyFloor"));
    setText("dash-proof-hlc", hlcText);
    setText(
      "dash-proof-crdt",
      `${ep.crdt_event_count ?? eventsCount} ${t("eventsUnit")} → ${ep.converged_patient_count ?? patientCount} ${t("convergedPatientsUnit")}`
    );
    setText("dash-proof-bloat", t("proofZeroBloat"));
  }

  function classifyOriginTier(originNodeId) {
    const id = String(originNodeId || "").toLowerCase();
    if (id.includes("watch")) return t("originWatch");
    if (id.includes("phone") || id.includes("asha") || id.includes("mobile")) return t("originPhone");
    return t("originHub");
  }

  function formatEventTimestamp(hlc) {
    if (!hlc || !hlc.wall_ms) return "--";
    try {
      return new Date(Number(hlc.wall_ms)).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch (_err) {
      return String(hlc.wall_ms);
    }
  }

  function summarizeSyncedEvent(evt) {
    const p = evt.payload || {};
    if (evt.event_type === "PATIENT_REGISTERED") {
      const parts = [];
      if (p.village_id) parts.push(`${t("villagePrefix")} ${p.village_id}`);
      if (p.is_pregnant) {
        parts.push(
          p.gestational_weeks
            ? `${t("pregnantWeeks")} · ${p.gestational_weeks} ${t("weeksShort")}`
            : t("pregnantWeeks")
        );
      }
      return parts.join(" · ");
    }
    if (evt.event_type === "TRIAGE_COMPLETED") {
      const sev = p.severity ? translateSeverity(p.severity) : "";
      const rat = p.rationale ? String(p.rationale) : "";
      return [sev, rat].filter(Boolean).join(" — ");
    }
    if (evt.event_type === "VOICE_NOTE_RECORDED") {
      const lang = p.language ? `lang=${p.language}` : "";
      const enr = evt.enrichment_state ? translateEnrichmentState(evt.enrichment_state) : "";
      return [lang, enr].filter(Boolean).join(" · ");
    }
    if (evt.event_type === "CHECKLIST_RECORDED") {
      return p.checklist_type || p.summary || p.notes || "";
    }
    if (evt.event_type === "VACCINATION_LOGGED") {
      return p.vaccine_name || p.vaccine || p.dose || "";
    }
    return "";
  }

  function renderSyncedFeed(events, nameMap) {
    const container = document.getElementById("synced-feed-list");
    if (!container) return;

    const clinicalTypes = new Set([
      "PATIENT_REGISTERED",
      "TRIAGE_COMPLETED",
      "VOICE_NOTE_RECORDED",
      "CHECKLIST_RECORDED",
      "VACCINATION_LOGGED",
    ]);
    const list = (Array.isArray(events) ? events : []).filter((evt) =>
      clinicalTypes.has(evt.event_type)
    );
    setText("synced-feed-count", list.length);

    if (list.length === 0) {
      container.replaceChildren(el("p", { className: "empty-state" }, t("noSyncedEvents")));
      return;
    }

    const limit = 7;
    const cards = list.slice(0, limit).map((evt, idx) => {
      const summaryLine = summarizeSyncedEvent(evt);
      const originTier = classifyOriginTier(evt.origin_node_id);
      const tsText = formatEventTimestamp(evt.hlc);

      return el(
        "div",
        { className: "item-card synced-card" },
        el(
          "div",
          { className: "item-card-head" },
          buildPatientHeadingNode(evt.patient_id, nameMap, evt.event_id),
          el(
            "div",
            { className: "synced-badges" },
            idx < 3 ? el("span", { className: "badge just-synced-badge" }, t("justSynced")) : null,
            el("span", { className: "badge badge-accent" }, translateEventType(evt.event_type))
          )
        ),
        summaryLine ? el("div", { className: "item-card-meta" }, summaryLine) : null,
        el(
          "div",
          { className: "synced-foot" },
          el(
            "span",
            { className: "badge origin-pill mono" },
            `${originTier} · ${evt.origin_node_id || "--"}`
          ),
          el("span", { className: "synced-time mono" }, tsText)
        )
      );
    });
    if (list.length > limit) {
      cards.push(el("span", { className: "more-counter" }, formatMoreCounter(list.length - limit)));
    }
    container.replaceChildren(...cards);
  }

  function renderCrdtMergeProofs(proofs) {
    const section = document.getElementById("crdt-merge-proof-section");
    const container = document.getElementById("crdt-merge-proof-list");
    const collapsible = document.getElementById("crdt-collapsible");
    if (!section || !container) return;

    const list = Array.isArray(proofs) ? proofs : [];
    setText("crdt-proof-count-badge", list.length);
    if (list.length === 0) {
      section.classList.add("hidden");
      container.replaceChildren();
      return;
    }

    section.classList.remove("hidden");
    if (collapsible) {
      collapsible.classList.toggle("hidden", !state.crdtExpanded);
    }
    const cards = list.slice(0, 3).map((proof) => {
      const latestByOrigin = new Map();
      for (const c of proof.contributions || []) {
        if (c && c.origin_node_id) latestByOrigin.set(c.origin_node_id, c);
      }
      const peerEdits = Array.from(latestByOrigin.values());
      const boxes = [];

      peerEdits.forEach((edit, idx) => {
        if (idx > 0) boxes.push(el("span", { className: "crdt-op-sep mono" }, "⊕"));
        const chips = Object.entries(edit.fields || {})
          .slice(0, 5)
          .map(([k, v]) =>
            el("span", { className: "meta-chip mono" }, `${k.replace(/^metadata\./, "")}=${formatCompactFieldValue(v)}`)
          );
        const shortHlc = edit.hlc ? `${edit.hlc.wall_ms}:${edit.hlc.logical}` : edit.hlc_str || "--";
        boxes.push(
          el(
            "div",
            { className: "crdt-contrib-box" },
            el(
              "div",
              { className: "crdt-contrib-head" },
              el("span", { className: "mono" }, edit.origin_node_id),
              el("span", { className: "badge badge-accent mono" }, `HLC ${shortHlc}`)
            ),
            chips.length > 0 ? el("div", { className: "meta-chips" }, ...chips) : null
          )
        );
      });

      boxes.push(el("span", { className: "crdt-op-sep mono" }, "⇒"));

      const convergedChips = Object.entries(proof.converged_fields || {})
        .slice(0, 7)
        .map(([k, v]) =>
          el("span", { className: "meta-chip mono" }, `${k.replace(/^metadata\./, "")}=${formatCompactFieldValue(v)}`)
        );
      boxes.push(
        el(
          "div",
          { className: "crdt-contrib-box crdt-contrib-converged" },
          el(
            "div",
            { className: "crdt-contrib-head" },
            el("span", null, `${t("convergedRecord")}: ${proof.full_name || proof.patient_id}`),
            el("span", { className: "badge badge-green" }, t("zeroDataLoss"))
          ),
          convergedChips.length > 0 ? el("div", { className: "meta-chips" }, ...convergedChips) : null
        )
      );

      return el(
        "div",
        { className: "crdt-merge-card" },
        el(
          "div",
          { className: "item-card-head" },
          el("span", { className: "item-card-title" }, proof.full_name || proof.patient_id),
          proof.simultaneous_wall_ms
            ? el("span", { className: "badge badge-accent" }, t("simultaneousTieBreak"))
            : el("span", { className: "badge badge-green" }, t("zeroDataLoss"))
        ),
        el("div", { className: "crdt-contrib-grid" }, ...boxes)
      );
    });
    container.replaceChildren(...cards);
  }

  function renderShap(enrichments, nameMap, pendingCount) {
    const container = document.getElementById("shap-list");
    const enrichBtn = document.getElementById("btn-run-enrichment");
    if (enrichBtn && !enrichBtn.disabled) {
      const pending = Number(pendingCount || 0);
      enrichBtn.classList.toggle("btn-highlight", pending > 0);
      enrichBtn.textContent =
        pending > 0 ? `${t("runEnrichment")} (${pending})` : t("runEnrichment");
    }
    if (!container) return;

    const rawList = Array.isArray(enrichments) ? enrichments : [];
    const list = [...rawList].sort((a, b) => {
      const aw = a && a.hlc ? Number(a.hlc.wall_ms || 0) : 0;
      const bw = b && b.hlc ? Number(b.hlc.wall_ms || 0) : 0;
      if (bw !== aw) return bw - aw;
      const al = a && a.hlc ? Number(a.hlc.logical || 0) : 0;
      const bl = b && b.hlc ? Number(b.hlc.logical || 0) : 0;
      return bl - al;
    });
    setText("shap-count-badge", list.length);
    if (list.length === 0) {
      container.replaceChildren(el("p", { className: "empty-state" }, t("noShap")));
      return;
    }

    const limit = 6;
    const cards = list.slice(0, limit).map((item) => {
      const entries = normalizeShapEntries(item.shap_attributions).sort(
        (a, b) => Math.abs(b.value) - Math.abs(a.value)
      );
      const maxAbs = Math.max(0.01, ...entries.map((entry) => Math.abs(entry.value)));
      const hasScore = item.risk_score !== null && item.risk_score !== undefined;
      const pctScore = hasScore ? `${Math.round(Number(item.risk_score) * 100)}%` : "--";
      const bandText = translateRiskBand(item.risk_band);

      const payload = (item && item.payload) || {};
      const provenance =
        payload.reasoning_provenance && typeof payload.reasoning_provenance === "object"
          ? payload.reasoning_provenance
          : {};
      const triageObj =
        payload.triage_assessment && typeof payload.triage_assessment === "object"
          ? payload.triage_assessment
          : {};
      const structuredObj =
        payload.structured_note && typeof payload.structured_note === "object"
          ? payload.structured_note
          : {};
      const matchedRules = Array.isArray(triageObj.matched_rules)
        ? triageObj.matched_rules.map(humanizeToken).join(", ")
        : "";
      const whoProtocol = provenance.clinical_protocol || matchedRules || "WHO IMNCI";
      const whoChipText = matchedRules && provenance.clinical_protocol
        ? `${t("whoFloorLabel")}: ${provenance.clinical_protocol} (${matchedRules})`
        : `${t("whoFloorLabel")}: ${whoProtocol}`;
      const mlModelText = `${t("laptopMlLabel")}: ${item.risk_backend || t("laptopMlModel")}`;

      const symptoms = Array.isArray(item.extracted_symptoms) ? item.extracted_symptoms : [];
      const dangerFlags = Array.isArray(item.candidate_danger_flags) ? item.candidate_danger_flags : [];
      const tagChips = [
        ...dangerFlags.slice(0, 4).map((flag) =>
          el("span", { className: "badge badge-red" }, `${t("dangerFlagsLabel")}: ${humanizeToken(flag)}`)
        ),
        ...symptoms.slice(0, 4).map((sym) =>
          el("span", { className: "meta-chip" }, `${t("symptomsLabel")}: ${humanizeToken(sym)}`)
        ),
      ];

      const barNodes = entries.slice(0, 5).map((entry) => {
        const pct = Math.min(100, Math.round((Math.abs(entry.value) / maxAbs) * 100));
        const isPos = entry.value >= 0;
        const fillClass = isPos ? "shap-fill-pos" : "shap-fill-neg";
        const fill = el("div", { className: fillClass });
        fill.style.width = `${pct}%`;
        const label = humanizeToken(entry.name);
        return el(
          "div",
          { className: "shap-bar-row" },
          el("span", { className: "shap-feature", title: entry.name }, label),
          el("div", { className: "shap-track" }, fill),
          el(
            "span",
            { className: `mono shap-val ${isPos ? "shap-val-pos" : "shap-val-neg"}` },
            (isPos ? "+" : "") + entry.value.toFixed(2)
          )
        );
      });

      const isHighRisk =
        item.risk_band === "RED_EMERGENCY" ||
        item.risk_band === "HIGH" ||
        (hasScore && Number(item.risk_score) >= 0.7);
      const badgeClass = isHighRisk
        ? "badge badge-red"
        : item.risk_band === "LOW" || item.risk_band === "GREEN_HOME"
          ? "badge badge-green"
          : "badge badge-yellow";
      const followUp = structuredObj.recommended_follow_up || item.summary || "";

      return el(
        "div",
        { className: isHighRisk ? "item-card ml-card ml-card-high" : "item-card ml-card" },
        el(
          "div",
          { className: "item-card-head" },
          buildPatientHeadingNode(item.patient_id, nameMap, item.ref_event_id || item.event_id),
          el(
            "div",
            { className: "ml-score-hero" },
            hasScore ? el("span", { className: "ml-score-pct mono" }, pctScore) : null,
            el("span", { className: badgeClass }, bandText)
          )
        ),
        el(
          "div",
          { className: "ml-provenance-row" },
          el("span", { className: "ml-source-chip ml-source-who" }, whoChipText),
          el("span", { className: "ml-source-chip ml-source-gbdt" }, mlModelText)
        ),
        item.transcript
          ? el("div", { className: "transcript-snippet" }, `"${String(item.transcript).slice(0, 140)}"`)
          : null,
        tagChips.length > 0 ? el("div", { className: "meta-chips" }, ...tagChips) : null,
        barNodes.length > 0
          ? el(
              "div",
              { className: "shap-legend" },
              el("span", { className: "shap-legend-pos" }, t("shapPosLegend")),
              el("span", { className: "shap-legend-neg" }, t("shapNegLegend"))
            )
          : null,
        ...barNodes,
        followUp
          ? el(
              "div",
              { className: "ml-followup-box" },
              el("strong", null, `${t("recommendedFollowUpLabel")}: `),
              followUp
            )
          : null
      );
    });
    if (list.length > limit) {
      cards.push(el("span", { className: "more-counter" }, formatMoreCounter(list.length - limit)));
    }
    container.replaceChildren(...cards);
  }

  function renderActionCards(cardsData, nameMap) {
    const container = document.getElementById("action-cards-list");
    if (!container) return;

    const list = Array.isArray(cardsData) ? cardsData : [];
    setText("action-count-badge", list.length);
    if (list.length === 0) {
      container.replaceChildren(el("p", { className: "empty-state" }, t("noActionCards")));
      return;
    }

    const cards = list.map((card) => {
      const priority = card.priority || "MEDIUM";
      const badgeClass =
        priority === "CRITICAL"
          ? "badge badge-red"
          : priority === "HIGH"
            ? "badge badge-yellow"
            : "badge badge-green";
      const cardClass =
        priority === "CRITICAL"
          ? "item-card item-card-red"
          : priority === "HIGH"
            ? "item-card item-card-yellow"
            : "item-card item-card-green";
      const targetLabel = card.target_tier ? ` → ${translateTier(card.target_tier)}` : "";

      return el(
        "div",
        { className: cardClass },
        el(
          "div",
          { className: "item-card-head" },
          el("span", { className: "item-card-title" }, card.title || card.card_id),
          el(
            "span",
            { className: badgeClass },
            `${translatePriority(priority)} · ${translateActionStatus(card.status || "OPEN")}`
          )
        ),
        el("div", { className: "item-card-meta" }, card.summary || ""),
        card.patient_id
          ? el(
              "div",
              { className: "item-card-meta", title: formatPatientLabel(card.patient_id, nameMap) },
              `${formatPatientLabel(card.patient_id, nameMap)}${targetLabel}`
            )
          : null
      );
    });
    container.replaceChildren(...cards);
  }

  function renderEvents(events, nameMap) {
    const tbody = document.getElementById("events-tbody");
    if (!tbody) return;

    const list = Array.isArray(events) ? events : [];
    if (list.length === 0) {
      const emptyRow = el(
        "tr",
        null,
        el("td", { colspan: "6", className: "empty-state" }, t("noEvents"))
      );
      tbody.replaceChildren(emptyRow);
      return;
    }

    const rows = list.map((evt) => {
      const eventKey = evt.event_id || formatHlc(evt.hlc);
      const isExpanded = state.expandedEventIds.has(eventKey);
      const compactPayload = JSON.stringify(evt.payload || {});
      const prettyPayload = JSON.stringify(evt.payload || {}, null, 2);

      let patientCell;
      if (evt.patient_id) {
        const pid = String(evt.patient_id);
        const fullName = nameMap && nameMap.get(pid);
        if (fullName) {
          patientCell = el(
            "td",
            { title: formatPatientLabel(pid, nameMap) },
            el("span", { className: "patient-cell-name" }, fullName),
            el("span", { className: "patient-cell-id mono" }, pid)
          );
        } else {
          patientCell = el("td", { className: "mono" }, pid);
        }
      } else {
        patientCell = el("td", { className: "mono" }, "--");
      }

      const payloadBtn = el(
        "button",
        {
          type: "button",
          className: isExpanded ? "payload-toggle mono expanded" : "payload-toggle mono",
          "aria-expanded": String(isExpanded),
          title: isExpanded ? t("collapsePayload") : t("expandPayload"),
        },
        isExpanded ? prettyPayload : compactPayload
      );
      payloadBtn.addEventListener("click", () => {
        if (state.expandedEventIds.has(eventKey)) {
          state.expandedEventIds.delete(eventKey);
        } else {
          state.expandedEventIds.add(eventKey);
        }
        renderEvents(state.lastEvents, buildPatientNameMap(state.lastSummary && state.lastSummary.patients));
      });

      return el(
        "tr",
        null,
        el("td", { className: "mono" }, formatHlc(evt.hlc)),
        el("td", { className: "mono" }, evt.origin_node_id || "--"),
        el("td", null, el("span", { className: "badge badge-accent", title: evt.event_type || "" }, translateEventType(evt.event_type))),
        patientCell,
        el("td", null, el("span", { className: "badge" }, translateEnrichmentState(evt.enrichment_state))),
        el("td", { className: "payload-cell" }, payloadBtn)
      );
    });
    tbody.replaceChildren(...rows);
  }

  function renderScenarioNarrative() {
    const card = document.getElementById("scenario-narrative-card");
    if (!card) return;

    const rawInfo =
      state.activeScenario && !state.narrativeDismissed
        ? state.scenarioCatalog[state.activeScenario]
        : null;
    const locMap = LOCALIZED_SCENARIOS[state.lang] || {};
    const locInfo = state.activeScenario ? locMap[state.activeScenario] : null;
    const info =
      state.activeScenario && !state.narrativeDismissed
        ? locInfo || rawInfo
        : null;
    if (!info) {
      card.classList.add("hidden");
      card.replaceChildren();
      return;
    }

    const closeBtn = el(
      "button",
      { type: "button", className: "btn btn-secondary btn-dismiss", "aria-label": t("dismiss") },
      t("dismiss")
    );
    closeBtn.addEventListener("click", () => {
      state.narrativeDismissed = true;
      renderScenarioNarrative();
    });

    const stepNodes = Array.isArray(info.steps)
      ? info.steps.map((step) => el("li", null, String(step)))
      : [];

    card.classList.remove("hidden");
    card.replaceChildren(
      el(
        "div",
        { className: "scenario-narrative-head" },
        el(
          "div",
          { className: "scenario-narrative-title-group" },
          el("h3", { className: "scenario-narrative-title" }, info.title || state.activeScenario),
          info.persona ? el("span", { className: "badge badge-accent" }, info.persona) : null
        ),
        closeBtn
      ),
      info.subtitle ? el("p", { className: "scenario-narrative-sub" }, info.subtitle) : null,
      stepNodes.length > 0 ? el("span", { className: "scenario-steps-label" }, t("scenarioStepsLabel")) : null,
      stepNodes.length > 0 ? el("ol", { className: "scenario-steps" }, ...stepNodes) : null
    );
  }

  async function loadScenarioCatalog() {
    const catalog = await fetchJsonSafe("/api/v1/demo/scenarios");
    if (!Array.isArray(catalog)) return;
    const byId = {};
    for (const item of catalog) {
      if (item && item.id) {
        byId[String(item.id)] = item;
      }
    }
    state.scenarioCatalog = byId;
    renderScenarioNarrative();
  }

  function localizeScenarioTitle(scenarioId) {
    const key = SCENARIO_TITLE_KEYS[scenarioId];
    return key ? t(key) : scenarioId;
  }

  function renderDemoStatus() {
    const banner = document.getElementById("demo-status-banner");
    if (!banner) return;
    const ds = state.demoStatus;
    if (!ds) {
      if (state.reconnecting) {
        banner.classList.remove("hidden");
        banner.replaceChildren(el("span", null, t("reconnecting")));
      } else {
        banner.classList.add("hidden");
        banner.replaceChildren();
      }
      return;
    }
    let message = "";
    let meta = null;
    if (ds.kind === "loading") {
      message = t("demoLoading");
      meta = localizeScenarioTitle(ds.scenarioId);
    } else if (ds.kind === "loaded") {
      message = `${t("demoLoaded")} ${localizeScenarioTitle(ds.scenarioId)}`;
      meta = `${ds.eventsAdded} ${t("eventsUnit")} · ${ds.peersRegistered} ${t("peersUnit")}`;
    } else if (ds.kind === "resetting") {
      message = t("demoResetting");
    } else if (ds.kind === "reset") {
      message = t("demoResetDone");
      meta = `0 ${t("eventsUnit")}`;
    } else if (ds.kind === "unavailable") {
      message = t("demoUnavailable");
      meta = ds.code || null;
    }
    banner.classList.remove("hidden");
    banner.replaceChildren(
      el("span", null, message),
      meta ? el("span", { className: "badge badge-brand mono" }, meta) : null
    );
  }

  function updateScenarioButtons() {
    const buttons = document.querySelectorAll("[data-scenario]");
    for (const btn of buttons) {
      const sid = btn.getAttribute("data-scenario");
      btn.classList.toggle("active", sid === state.activeScenario);
    }
  }

  async function runScenario(scenarioId) {
    if (state.demoBusy) return;
    state.demoBusy = true;
    const buttons = document.querySelectorAll("[data-scenario], #btn-demo-reset");
    for (const b of buttons) b.disabled = true;
    state.demoStatus = { kind: "loading", scenarioId };
    renderDemoStatus();
    try {
      const res = await fetch(`/api/v1/demo/load/${encodeURIComponent(scenarioId)}`, {
        method: "POST",
      });
      if (!res.ok) {
        state.demoStatus = { kind: "unavailable", code: String(res.status) };
        renderDemoStatus();
        return;
      }
      const data = await res.json();
      state.activeScenario = scenarioId;
      state.narrativeDismissed = false;
      updateScenarioButtons();
      renderScenarioNarrative();
      state.demoStatus = {
        kind: "loaded",
        scenarioId,
        eventsAdded: data.events_added ?? 0,
        peersRegistered: data.peers_registered ?? 0,
      };
      renderDemoStatus();
      await refreshAll();
    } catch (_err) {
      state.demoStatus = { kind: "unavailable", code: null };
      renderDemoStatus();
    } finally {
      state.demoBusy = false;
      for (const b of buttons) b.disabled = false;
    }
  }

  async function resetDemo() {
    if (state.demoBusy) return;
    state.demoBusy = true;
    const buttons = document.querySelectorAll("[data-scenario], #btn-demo-reset");
    for (const b of buttons) b.disabled = true;
    state.demoStatus = { kind: "resetting" };
    renderDemoStatus();
    try {
      const res = await fetch("/api/v1/demo/reset", { method: "POST" });
      if (!res.ok) {
        state.demoStatus = { kind: "unavailable", code: String(res.status) };
        renderDemoStatus();
        return;
      }
      state.activeScenario = null;
      state.narrativeDismissed = false;
      state.expandedEventIds.clear();
      updateScenarioButtons();
      renderScenarioNarrative();
      state.demoStatus = { kind: "reset" };
      renderDemoStatus();
      await refreshAll();
    } catch (_err) {
      state.demoStatus = { kind: "unavailable", code: null };
      renderDemoStatus();
    } finally {
      state.demoBusy = false;
      for (const b of buttons) b.disabled = false;
    }
  }

  async function fetchJsonSafe(url) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) return null;
      return await res.json();
    } catch (_err) {
      return null;
    }
  }

  async function refreshAll(opts) {
    if (state.refreshing) return;
    const manual = Boolean(opts && opts.manual);
    state.refreshing = true;
    const refreshBtn = document.getElementById("btn-refresh");
    if (manual && refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.textContent = t("refreshing");
    }

    try {
      const eventsQuery = state.selectedEventType
        ? `/api/v1/events?limit=50&event_type=${encodeURIComponent(state.selectedEventType)}`
        : "/api/v1/events?limit=50";

      const [summary, peersResp, connectInfo, events] = await Promise.all([
        fetchJsonSafe("/api/v1/dashboard/summary"),
        fetchJsonSafe("/api/v1/peers"),
        fetchJsonSafe("/api/v1/discovery/connect-info"),
        fetchJsonSafe(eventsQuery),
      ]);

      if (summary) {
        state.reconnecting = false;
        state.lastSummary = summary;
        if (state.demoStatus && state.demoStatus.kind === "unavailable") {
          state.demoStatus = null;
        }
      } else {
        state.reconnecting = true;
      }

      if (peersResp !== null) {
        state.lastPeers = Array.isArray(peersResp) ? peersResp : peersResp.peers || [];
      } else if (summary && Array.isArray(summary.peers)) {
        state.lastPeers = summary.peers;
      }
      if (connectInfo) state.lastConnectInfo = connectInfo;
      if (Array.isArray(events)) state.lastEvents = events;

      renderAll();
      setText("last-updated", state.reconnecting ? t("reconnecting") : new Date().toLocaleTimeString());
    } finally {
      state.refreshing = false;
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.textContent = t("refresh");
      }
    }
  }

  function renderAll() {
    const patients = state.lastSummary ? state.lastSummary.patients : [];
    const nameMap = buildPatientNameMap(patients);
    applyTranslations();
    renderEngineeringProofStrip(state.lastSummary);
    renderScenarioNarrative();
    renderManifest(state.lastSummary, state.lastConnectInfo);
    renderKpis(state.lastSummary);
    renderSyncedFeed(state.lastEvents, nameMap);
    renderPatients(patients);
    renderCrdtMergeProofs(state.lastSummary ? state.lastSummary.crdt_merge_proofs : []);
    renderTriageHistory(state.lastSummary, nameMap);
    renderPeers(state.lastPeers);
    renderOutbreaks(state.lastSummary ? state.lastSummary.outbreak_alerts : []);
    renderShap(
      state.lastSummary ? state.lastSummary.enrichments : [],
      nameMap,
      state.lastSummary ? state.lastSummary.pending_enrichments : 0
    );
    renderActionCards(state.lastSummary ? state.lastSummary.action_cards : [], nameMap);
    renderEvents(state.lastEvents, nameMap);
  }

  async function triggerEnrichment() {
    if (state.enriching) return;
    state.enriching = true;
    const btn = document.getElementById("btn-run-enrichment");
    const status = document.getElementById("enrichment-status");
    if (btn) {
      btn.disabled = true;
      btn.textContent = t("runningEnrichment");
    }
    try {
      let res = await fetch("/api/v1/enrichment/run", { method: "POST" });
      if (res.status === 404) {
        res = await fetch("/api/v1/enrichment/run-once", { method: "POST" });
      }
      state.enrichmentStatusKey = res.ok ? "enrichmentDone" : "enrichmentUnavailable";
      if (status) {
        status.classList.remove("hidden");
        status.textContent = t(state.enrichmentStatusKey);
      }
      await refreshAll();
    } catch (_err) {
      state.enrichmentStatusKey = "enrichmentUnavailable";
      if (status) {
        status.classList.remove("hidden");
        status.textContent = t(state.enrichmentStatusKey);
      }
    } finally {
      state.enriching = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = t("runEnrichment");
      }
    }
  }

  function syncAutoRefreshTimer() {
    if (state.timerId !== null) {
      clearInterval(state.timerId);
      state.timerId = null;
    }
    if (state.autoRefresh) {
      state.timerId = setInterval(refreshAll, 5000);
    }
  }

  function setLanguage(lang) {
    if (!SUPPORTED_LANGS.includes(lang) || state.lang === lang) return;
    state.lang = lang;
    writeStoredPref(STORAGE_LANG_KEY, state.lang);
    renderAll();
  }

  function bindEvents() {
    const langBtns = document.querySelectorAll("#lang-switcher [data-lang]");
    for (const btn of langBtns) {
      btn.addEventListener("click", () => {
        const nextLang = btn.getAttribute("data-lang");
        if (nextLang) setLanguage(nextLang);
      });
    }

    window.addEventListener("message", (ev) => {
      if (ev && ev.data && ev.data.type === "aarogya:setLang") {
        setLanguage(ev.data.lang);
      }
    });

    window.addEventListener("storage", (ev) => {
      if (ev && ev.key === STORAGE_LANG_KEY && ev.newValue) {
        setLanguage(ev.newValue);
      }
    });

    const themeBtn = document.getElementById("btn-theme");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => {
        state.theme = state.theme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", state.theme);
        writeStoredPref(STORAGE_THEME_KEY, state.theme);
        applyTranslations();
      });
    }

    const autoBtn = document.getElementById("btn-autorefresh");
    if (autoBtn) {
      autoBtn.addEventListener("click", () => {
        state.autoRefresh = !state.autoRefresh;
        autoBtn.classList.toggle("active", state.autoRefresh);
        autoBtn.setAttribute("aria-pressed", String(state.autoRefresh));
        applyTranslations();
        syncAutoRefreshTimer();
      });
    }

    const refreshBtn = document.getElementById("btn-refresh");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => {
        refreshAll({ manual: true });
      });
    }

    const enrichBtn = document.getElementById("btn-run-enrichment");
    if (enrichBtn) {
      enrichBtn.addEventListener("click", () => {
        triggerEnrichment();
      });
    }

    const toggleEventsBtn = document.getElementById("btn-toggle-events");
    const eventsCollapsible = document.getElementById("events-collapsible");

    const filterSelect = document.getElementById("event-type-filter");
    if (filterSelect) {
      filterSelect.addEventListener("change", (ev) => {
        state.selectedEventType = ev.target.value || "";
        if (!state.eventsExpanded) {
          state.eventsExpanded = true;
          if (eventsCollapsible) eventsCollapsible.classList.remove("hidden");
          if (toggleEventsBtn) {
            toggleEventsBtn.setAttribute("aria-expanded", "true");
            toggleEventsBtn.textContent = t("hideEventLog");
          }
        }
        refreshAll();
      });
    }

    if (toggleEventsBtn && eventsCollapsible) {
      toggleEventsBtn.addEventListener("click", () => {
        state.eventsExpanded = !state.eventsExpanded;
        eventsCollapsible.classList.toggle("hidden", !state.eventsExpanded);
        toggleEventsBtn.setAttribute("aria-expanded", String(state.eventsExpanded));
        toggleEventsBtn.textContent = state.eventsExpanded ? t("hideEventLog") : t("showEventLog");
      });
    }

    const toggleSysBtn = document.getElementById("btn-toggle-sys-details");
    const sysCollapsible = document.getElementById("sys-details-collapsible");
    if (toggleSysBtn && sysCollapsible) {
      toggleSysBtn.addEventListener("click", () => {
        state.sysDetailsExpanded = !state.sysDetailsExpanded;
        sysCollapsible.classList.toggle("hidden", !state.sysDetailsExpanded);
        toggleSysBtn.setAttribute("aria-expanded", String(state.sysDetailsExpanded));
        toggleSysBtn.textContent = state.sysDetailsExpanded ? t("hideDetails") : t("showDetails");
      });
    }

    const toggleCrdtBtn = document.getElementById("btn-toggle-crdt");
    const crdtCollapsible = document.getElementById("crdt-collapsible");
    if (toggleCrdtBtn && crdtCollapsible) {
      toggleCrdtBtn.addEventListener("click", () => {
        state.crdtExpanded = !state.crdtExpanded;
        crdtCollapsible.classList.toggle("hidden", !state.crdtExpanded);
        toggleCrdtBtn.setAttribute("aria-expanded", String(state.crdtExpanded));
        toggleCrdtBtn.textContent = state.crdtExpanded ? t("hideDetails") : t("showDetails");
      });
    }

    const scenarioBtns = document.querySelectorAll("[data-scenario]");
    for (const btn of scenarioBtns) {
      btn.addEventListener("click", () => {
        const sid = btn.getAttribute("data-scenario");
        if (sid) runScenario(sid);
      });
    }

    const resetBtn = document.getElementById("btn-demo-reset");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        resetDemo();
      });
    }

    const copyUrlBtn = document.getElementById("btn-copy-hub-url");
    if (copyUrlBtn) {
      copyUrlBtn.addEventListener("click", async () => {
        const urlText = state.hubLanUrl || (document.getElementById("hub-lan-url")?.textContent || "");
        if (!urlText || urlText === "--") return;
        let copied = false;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          try {
            await navigator.clipboard.writeText(urlText);
            copied = true;
          } catch (_err) {
            copied = false;
          }
        }
        if (!copied) {
          const ta = document.createElement("textarea");
          ta.value = urlText;
          ta.setAttribute("readonly", "readonly");
          ta.style.position = "fixed";
          ta.style.left = "-9999px";
          ta.style.top = "0";
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          ta.setSelectionRange(0, urlText.length);
          try {
            copied = document.execCommand("copy");
          } catch (_err) {
            copied = false;
          }
          document.body.removeChild(ta);
        }
        const feedbackKey = copied ? "copiedAddress" : "copyFailed";
        state.copyFeedbackKey = feedbackKey;
        copyUrlBtn.textContent = t(feedbackKey);
        if (state.copyTimerId !== null) {
          window.clearTimeout(state.copyTimerId);
        }
        state.copyTimerId = window.setTimeout(() => {
          state.copyFeedbackKey = null;
          state.copyTimerId = null;
          copyUrlBtn.textContent = t("copyAddress");
        }, 1800);
      });
    }

    const toggleQrBtn = document.getElementById("btn-toggle-qr");
    const qrPanel = document.getElementById("hub-qr-panel");
    const qrImg = document.getElementById("hub-qr-img");
    if (toggleQrBtn && qrPanel) {
      toggleQrBtn.addEventListener("click", () => {
        state.qrExpanded = !state.qrExpanded;
        qrPanel.classList.toggle("hidden", !state.qrExpanded);
        qrPanel.style.display = state.qrExpanded ? "flex" : "none";
        toggleQrBtn.setAttribute("aria-expanded", String(state.qrExpanded));
        toggleQrBtn.textContent = state.qrExpanded ? t("hideQrCode") : t("showQrCode");
        if (state.qrExpanded && qrImg) {
          const urlText = state.hubLanUrl || window.location.origin;
          qrImg.src = `/api/v1/hub-qr.svg?text=${encodeURIComponent(urlText)}`;
        }
      });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    state.lang = readInitialLang();
    state.theme = readStoredPref(STORAGE_THEME_KEY, ["dark", "light"], "dark");
    document.documentElement.setAttribute("data-theme", state.theme);
    bindEvents();
    applyTranslations();
    loadScenarioCatalog();
    refreshAll();
    syncAutoRefreshTimer();
  });
})();
