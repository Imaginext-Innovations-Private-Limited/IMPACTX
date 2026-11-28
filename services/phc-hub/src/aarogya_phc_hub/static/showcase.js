(() => {
  "use strict";

  const STORAGE_THEME_KEY = "aarogya.theme";
  const STORAGE_LANG_KEY = "aarogya.lang";
  const SUPPORTED_LANGS = ["en", "hi", "kn", "ta"];

  const I18N = {
    en: {
      stageTitle: "Aarogya Mesh — 3-Tier Stage",
      stageSubtitle: "Watch ↔ Phone ↔ Hub · Live 2s Sync",
      scMaternal: "1. Watch SOS",
      scVoice: "2. Voice → AI",
      scOutbreak: "3. Outbreak",
      scCrdt: "4. CRDT Merge",
      scMaternalTitle: "Maternal Watch SOS → ASHA Phone",
      scVoiceTitle: "Offline Voice Note → Hub AI Enrichment",
      scOutbreakTitle: "Multi-Worker EWMA Village Outbreak",
      scCrdtTitle: "Offline Conflict-Free CRDT Merge",
      scReset: "Reset",
      runEnrichment: "Run AI",
      runningEnrichment: "Running...",
      badgeOffline: "Offline Safe",
      themeLight: "Light",
      themeDark: "Dark",
      langToggle: "हिन्दी",
      backToHub: "← Hub",
      syncIdle: "Live Sync Ready",
      syncPulse: "CRDT Sync Pulse",
      reconnecting: "Reconnecting...",
      defaultNarrative:
        "Tap a danger sign on Watch, register a patient on Phone, or run a 1-click clinical scenario above.",
      scenarioRunning: "Executing live clinical scenario through Hub CRDT engine...",
      scenarioDonePrefix: "Active:",
      resetting: "Resetting Hub state...",
      resetDone: "Hub state cleared. Ready for live Watch/Phone interaction or scenario playback.",
      enrichmentDone: "Hub AI enrichment completed — SHAP scores & Action Cards updated.",
      endpointUnavailable: "Endpoint unavailable.",
      tier0Eyebrow: "Tier 0 · Watch (256 MB)",
      tier1Eyebrow: "Tier 1 · ASHA Phone (4 GB)",
      tier2Eyebrow: "Tier 2 · PHC Hub Brain",
      tier2EyebrowRam: "Tier 2 · {ram} GB PHC Hub Brain",
      reloadWatchTitle: "Reload Watch",
      reloadPhoneTitle: "Reload Phone",
      colWatchTitle: "Watch Companion",
      colWatchSub: "Patient / Family & ASHA Companion",
      colPhoneTitle: "ASHA Field Phone",
      colPhoneSub: "WHO IMNCI + Offline IndexedDB",
      colHubTitle: "PHC Clinical Intelligence",
      colHubSub: "Whisper + SLM + LightGBM SHAP + EWMA",
      watchCap1: "Standalone SOS",
      watchCap2: "1-Tap Danger Signs",
      watchCap3: "Action Alerts",
      phoneCap1: "WHO IMNCI",
      phoneCap2: "Voice Queue",
      phoneCap3: "HLC Sync",
      kpiPatients: "Patients",
      kpiRed: "Red",
      kpiYellow: "Yellow",
      kpiGreen: "Green",
      kpiPending: "Pending AI",
      hubPeersTitle: "Peers",
      tabAlerts: "Alerts & Cards",
      tabShap: "SHAP & Triage",
      tabStream: "CRDT Stream",
      hubActionsTitle: "Action Cards → Watch & Phone",
      hubOutbreaksTitle: "EWMA Outbreak Alerts",
      hubShapTitle: "SHAP Risk Attributions",
      hubTriageTitle: "Real-Time Triage Decisions",
      hubEventsTitle: "Latest CRDT Sync Stream",
      noPeers: "No peers synced yet.",
      noTriage: "No triage decisions yet.",
      noShap: "No SHAP risk attributions yet.",
      noActions: "No Action Cards issued yet.",
      noOutbreaks: "No active EWMA outbreak alerts.",
      noEvents: "Waiting for CRDT events...",
      outbreakPrefix: "EWMA OUTBREAK",
      villagePrefix: "Village:",
      riskLabel: "Risk",
      riskHigh: "High Risk",
      riskModerate: "Moderate Risk",
      riskLow: "Low Risk",
      riskEnriched: "AI Enriched",
      eventsUnit: "events",
      moreItems: "+{n} more",
      peerWatchFamily: "Watch · Patient / Family",
      peerWatchChw: "Watch · ASHA Companion",
      peerPhoneAsha: "ASHA Phone (Tier 1)",
      peerHub: "PHC Hub (Tier 2)",
      targetWatch: "Watch (Tier 0)",
      targetPhone: "ASHA Phone (Tier 1)",
      targetHub: "PHC Hub (Tier 2)",
      targetMesh: "All Mesh Devices",
      sevRed: "Red · Emergency",
      sevYellow: "Yellow · PHC Review",
      sevGreen: "Green · Home Care",
      prioCritical: "Critical",
      prioHigh: "High",
      prioMedium: "Medium",
      prioLow: "Low",
      statusOpen: "Open",
      statusAcked: "Acknowledged",
      statusResolved: "Resolved",
      statusPending: "Pending",
      watchModeFamily: "Patient / Family",
      watchModeChw: "ASHA Companion",
      evVoiceNote: "Voice Note",
      evPatientRegistered: "Patient Registered",
      evTriageCompleted: "Triage Completed",
      evChecklistRecorded: "Checklist Recorded",
      evVaccinationLogged: "Vaccination Logged",
      evVoiceNoteRecorded: "Voice Note",
      evEnrichmentCompleted: "AI Enrichment Completed",
      evActionCardIssued: "Action Card Issued",
      evOutbreakAlertRaised: "Outbreak Alert Raised",
      synFebrile: "Febrile Illness",
      synDiarrheal: "Acute Diarrheal Disease",
      synRespiratory: "Acute Respiratory Illness",
      synMaternal: "Maternal Danger Sign",
      synMalaria: "Suspected Malaria Cluster",
      synDengue: "Suspected Dengue Cluster",
      proofCloudRpcs: "0 Cloud RPCs",
      proofSafetyFloor: "WHO Safety Floor · conf=1.00",
      proofZeroBloat: "0 PyTorch · 0 CUDA",
      convergedPatientsUnit: "converged patients",
      hubCrdtMergeTitle: "CRDT LWW Conflict-Free Merge Proof",
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
    },
    hi: {
      stageTitle: "आरोग्य संजाल — त्रि-स्तरीय मंच",
      stageSubtitle: "घटिका ↔ दूरभाष ↔ मुख्य केन्द्र · २ क्षण समन्वय",
      scMaternal: "१. घटिका आपात",
      scVoice: "२. स्वर → प्रज्ञा",
      scOutbreak: "३. ग्राम प्रकोप",
      scCrdt: "४. द्वन्द्व-रहित विलय",
      scMaternalTitle: "मातृ घटिका आपात संकेत → आशा दूरभाष",
      scVoiceTitle: "अन्तर्जाल-रहित स्वर → मुख्य केन्द्र प्रज्ञा संवर्धन",
      scOutbreakTitle: "ग्राम संक्रमण प्रकोप संसूचन",
      scCrdtTitle: "अन्तर्जाल-रहित द्वन्द्व-रहित विलय प्रमाण",
      scReset: "पुनःस्थापन",
      runEnrichment: "संवर्धन",
      runningEnrichment: "प्रगति पर...",
      badgeOffline: "अन्तर्जाल-रहित",
      themeLight: "प्रकाश रूप",
      themeDark: "रात्रि रूप",
      langToggle: "English",
      backToHub: "← केन्द्र",
      syncIdle: "जीवन्त समन्वय तत्पर",
      syncPulse: "नवीन समन्वय स्पन्दन",
      reconnecting: "पुनः संयोजन हो रहा है...",
      defaultNarrative:
        "घटिका पर आपात लक्षण चुनें, दूरभाष में रोगी पंजीकृत करें अथवा ऊपर से परिदृश्य प्रारम्भ करें।",
      scenarioRunning: "वास्तविक चिकित्सकीय परिदृश्य प्रारम्भ हो रहा है...",
      scenarioDonePrefix: "सक्रिय परिदृश्य:",
      resetting: "मुख्य केन्द्र पुनःस्थापित हो रहा है...",
      resetDone: "मुख्य केन्द्र स्वच्छ हुआ। जीवन्त प्रदर्शन हेतु तत्पर।",
      enrichmentDone: "मुख्य केन्द्र संवर्धन पूर्ण — संकट सूचकांक एवं कार्य पत्रक अद्यतन।",
      endpointUnavailable: "सेवा अभी संयोजित नहीं है।",
      tier0Eyebrow: "स्तर ० · २५६ MB",
      tier1Eyebrow: "स्तर १ · ४ GB",
      tier2Eyebrow: "स्तर २ · मुख्य केन्द्र प्रज्ञा",
      tier2EyebrowRam: "स्तर २ · {ram} GB मुख्य केन्द्र प्रज्ञा",
      reloadWatchTitle: "घटिका पुनःभारित करें",
      reloadPhoneTitle: "दूरभाष पुनःभारित करें",
      colWatchTitle: "घटिका सहचर",
      colWatchSub: "रोगी एवं परिवार · आशा सहचर",
      colPhoneTitle: "आशा क्षेत्र दूरभाष",
      colPhoneSub: "निश्चित वर्गीकरण एवं स्थानीय संग्रहण",
      colHubTitle: "प्राथमिक स्वास्थ्य केन्द्र प्रज्ञा",
      colHubSub: "ध्वनि अनुलेखन · संकट कारक विश्लेषण · प्रकोप संसूचन",
      watchCap1: "स्वावलम्बी आपात",
      watchCap2: "एक-स्पर्श लक्षण",
      watchCap3: "कार्य सूचना",
      phoneCap1: "नियम वर्गीकरण",
      phoneCap2: "स्वर पंक्ति",
      phoneCap3: "कालक्रम समन्वय",
      kpiPatients: "रोगी",
      kpiRed: "रक्त",
      kpiYellow: "पीत",
      kpiGreen: "हरित",
      kpiPending: "प्रतीक्षारत",
      hubPeersTitle: "सहकर्मी",
      tabAlerts: "चेतावनी एवं पत्रक",
      tabShap: "संकट एवं वर्गीकरण",
      tabStream: "घटना प्रवाह",
      hubActionsTitle: "कार्य पत्रक → घटिका एवं दूरभाष",
      hubOutbreaksTitle: "संक्रमण प्रकोप चेतावनी",
      hubShapTitle: "संकट कारक विश्लेषण (SHAP)",
      hubTriageTitle: "तत्काल चिकित्सकीय वर्गीकरण",
      hubEventsTitle: "नवीनतम घटना प्रवाह",
      noPeers: "अभी कोई सहकर्मी संयोजित नहीं है।",
      noTriage: "अभी कोई चिकित्सकीय वर्गीकरण नहीं है।",
      noShap: "अभी कोई संकट कारक विश्लेषण उपलब्ध नहीं है।",
      noActions: "अभी कोई कार्य पत्रक जारी नहीं हुआ है।",
      noOutbreaks: "कोई सक्रिय संक्रमण प्रकोप चेतावनी नहीं है।",
      noEvents: "घटनाओं की प्रतीक्षा...",
      outbreakPrefix: "संक्रमण प्रकोप चेतावनी",
      villagePrefix: "ग्राम:",
      riskLabel: "संकट",
      riskHigh: "उच्च संकट",
      riskModerate: "मध्यम संकट",
      riskLow: "न्यून संकट",
      riskEnriched: "संवर्धित",
      eventsUnit: "घटनाएँ",
      moreItems: "+{n} अतिरिक्त",
      peerWatchFamily: "घटिका · रोगी एवं परिवार",
      peerWatchChw: "घटिका · आशा सहचर",
      peerPhoneAsha: "आशा दूरभाष (स्तर १)",
      peerHub: "मुख्य केन्द्र (स्तर २)",
      targetWatch: "घटिका (स्तर ०)",
      targetPhone: "आशा दूरभाष (स्तर १)",
      targetHub: "मुख्य केन्द्र (स्तर २)",
      targetMesh: "समस्त संजाल उपकरण",
      sevRed: "रक्त · आपातकाल",
      sevYellow: "पीत · स्वास्थ्य केन्द्र",
      sevGreen: "हरित · गृह देखभाल",
      prioCritical: "अत्यन्त गम्भीर",
      prioHigh: "उच्च",
      prioMedium: "मध्यम",
      prioLow: "न्यून",
      statusOpen: "सक्रिय",
      statusAcked: "स्वीकृत",
      statusResolved: "समाधानित",
      statusPending: "प्रतीक्षारत",
      watchModeFamily: "रोगी एवं परिवार",
      watchModeChw: "आशा सहचर",
      evVoiceNote: "स्वर टिप्पणी",
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
      proofCloudRpcs: "० मेघ-सेवा अनुरोध",
      proofSafetyFloor: "विश्व स्वास्थ्य सुरक्षा स्तर · १.००",
      proofZeroBloat: "० भारी तन्त्र भार",
      convergedPatientsUnit: "अभिसरित रोगी",
      hubCrdtMergeTitle: "द्वन्द्व-रहित विलय प्रमाण (LWW)",
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
    },
    kn: {
      stageTitle: "ಆರೋಗ್ಯ ಮೆಶ್ — ೩-ಹಂತದ ನೇರ ವೇದಿಕೆ",
      stageSubtitle: "ವಾಚ್ ↔ ಫೋನ್ ↔ ಕೇಂದ್ರ · ೨ ಸೆ. ನೇರ ಸಿಂಕ್",
      scMaternal: "೧. ವಾಚ್ ತುರ್ತು",
      scVoice: "೨. ಧ್ವನಿ → AI",
      scOutbreak: "೩. ಗ್ರಾಮ ಪ್ರಕೋಪ",
      scCrdt: "೪. CRDT ವಿಲೀನ",
      scMaternalTitle: "ಗರ್ಭಿಣಿ ವಾಚ್ ತುರ್ತು ಕರೆ → ಆಶಾ ಫೋನ್",
      scVoiceTitle: "ಆಫ್‌ಲೈನ್ ಧ್ವನಿ ಟಿಪ್ಪಣಿ → ಕೇಂದ್ರದ AI ವಿಶ್ಲೇಷಣೆ",
      scOutbreakTitle: "ಗ್ರಾಮ ಮಟ್ಟದ EWMA ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ ಪತ್ತೆ",
      scCrdtTitle: "ಆಫ್‌ಲೈನ್ ದ್ವಂದ್ವ-ರಹಿತ CRDT ವಿಲೀನ ಪುರಾವೆ",
      scReset: "ಮರುಹೊಂದಿಸಿ",
      runEnrichment: "AI ನಡೆಸಿ",
      runningEnrichment: "ನಡೆಯುತ್ತಿದೆ...",
      badgeOffline: "ಆಫ್‌ಲೈನ್ ಸುರಕ್ಷಿತ",
      themeLight: "ಬೆಳಕು",
      themeDark: "ಕತ್ತಲೆ",
      langToggle: "ಕನ್ನಡ",
      backToHub: "← ಕೇಂದ್ರ",
      syncIdle: "ನೇರ ಸಿಂಕ್ ಸಿದ್ಧ",
      syncPulse: "CRDT ಸಿಂಕ್ ಸ್ಪಂದನ",
      reconnecting: "ಮರುಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ...",
      defaultNarrative:
        "ವಾಚ್‌ನಲ್ಲಿ ಅಪಾಯದ ಲಕ್ಷಣ ಒತ್ತಿ, ಫೋನ್‌ನಲ್ಲಿ ರೋಗಿ ನೋಂದಾಯಿಸಿ ಅಥವಾ ಮೇಲಿನ ಸನ್ನಿವೇಶ ಆಯ್ಕೆಮಾಡಿ.",
      scenarioRunning: "ಕೇಂದ್ರದ CRDT ಎಂಜಿನ್ ಮೂಲಕ ನೇರ ವೈದ್ಯಕೀಯ ಸನ್ನಿವೇಶ ಚಾಲನೆಯಲ್ಲಿದೆ...",
      scenarioDonePrefix: "ಸಕ್ರಿಯ ಸನ್ನಿವೇಶ:",
      resetting: "ಮುಖ್ಯ ಕೇಂದ್ರವನ್ನು ಮರುಹೊಂದಿಸಲಾಗುತ್ತಿದೆ...",
      resetDone: "ಕೇಂದ್ರದ ದಾಖಲೆ ತೆರವುಗೊಳಿಸಲಾಗಿದೆ. ವಾಚ್/ಫೋನ್ ನೇರ ಪ್ರದರ್ಶನಕ್ಕೆ ಸಿದ್ಧ.",
      enrichmentDone: "ಕೇಂದ್ರದ AI ವಿಶ್ಲೇಷಣೆ ಪೂರ್ಣ — SHAP ಅಂಕಗಳು ಮತ್ತು ಕ್ರಿಯಾ ಕಾರ್ಡ್‌ಗಳು ನವೀಕರಣಗೊಂಡಿವೆ.",
      endpointUnavailable: "ಸೇವೆ ಸದ್ಯ ಲಭ್ಯವಿಲ್ಲ.",
      tier0Eyebrow: "ಹಂತ ೦ · ೨೫೬ MB",
      tier1Eyebrow: "ಹಂತ ೧ · ೪ GB",
      tier2Eyebrow: "ಹಂತ ೨ · PHC ಕೇಂದ್ರ ಬುದ್ಧಿಮತ್ತೆ",
      tier2EyebrowRam: "ಹಂತ ೨ · {ram} GB PHC ಕೇಂದ್ರ ಬುದ್ಧಿಮತ್ತೆ",
      reloadWatchTitle: "ವಾಚ್ ಮರುಲೋಡ್ ಮಾಡಿ",
      reloadPhoneTitle: "ಫೋನ್ ಮರುಲೋಡ್ ಮಾಡಿ",
      colWatchTitle: "ವಾಚ್ ಸಹಾಯಕ",
      colWatchSub: "ರೋಗಿ / ಕುಟುಂಬ ಮತ್ತು ಆಶಾ ಸಹಾಯಕ",
      colPhoneTitle: "ಆಶಾ ಕ್ಷೇತ್ರ ಫೋನ್",
      colPhoneSub: "WHO IMNCI + ಆಫ್‌ಲೈನ್ ಸಂಗ್ರಹಣೆ",
      colHubTitle: "PHC ವೈದ್ಯಕೀಯ ಬುದ್ಧಿಮತ್ತೆ",
      colHubSub: "ಧ್ವನಿ ಲಿಪ್ಯಂತರ · SLM · LightGBM SHAP · EWMA",
      watchCap1: "ಸ್ವತಂತ್ರ ತುರ್ತು ಕರೆ",
      watchCap2: "೧-ಸ್ಪರ್ಶ ಅಪಾಯ ಲಕ್ಷಣ",
      watchCap3: "ಕ್ರಿಯಾ ಎಚ್ಚರಿಕೆ",
      phoneCap1: "WHO IMNCI",
      phoneCap2: "ಧ್ವನಿ ಸಾಲು",
      phoneCap3: "HLC ಸಿಂಕ್",
      kpiPatients: "ರೋಗಿಗಳು",
      kpiRed: "ಕೆಂಪು",
      kpiYellow: "ಹಳದಿ",
      kpiGreen: "ಹಸಿರು",
      kpiPending: "ಬಾಕಿ AI",
      hubPeersTitle: "ಸಾಧನಗಳು",
      tabAlerts: "ಎಚ್ಚರಿಕೆ ಮತ್ತು ಕಾರ್ಡ್",
      tabShap: "SHAP ಮತ್ತು ವರ್ಗೀಕರಣ",
      tabStream: "CRDT ಹರಿವು",
      hubActionsTitle: "ಕ್ರಿಯಾ ಕಾರ್ಡ್‌ಗಳು → ವಾಚ್ ಮತ್ತು ಫೋನ್",
      hubOutbreaksTitle: "EWMA ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ ಎಚ್ಚರಿಕೆಗಳು",
      hubShapTitle: "SHAP ಅಪಾಯ ಕಾರಣಗಳ ವಿಶ್ಲೇಷಣೆ",
      hubTriageTitle: "ತಕ್ಷಣದ ವೈದ್ಯಕೀಯ ವರ್ಗೀಕರಣಗಳು",
      hubEventsTitle: "ಇತ್ತೀಚಿನ CRDT ಸಿಂಕ್ ಹರಿವು",
      noPeers: "ಇನ್ನೂ ಯಾವುದೇ ಸಾಧನ ಸಿಂಕ್ ಆಗಿಲ್ಲ.",
      noTriage: "ಇನ್ನೂ ಯಾವುದೇ ವೈದ್ಯಕೀಯ ವರ್ಗೀಕರಣಗಳಿಲ್ಲ.",
      noShap: "ಇನ್ನೂ ಯಾವುದೇ SHAP ಅಪಾಯ ವಿಶ್ಲೇಷಣೆ ಇಲ್ಲ.",
      noActions: "ಇನ್ನೂ ಯಾವುದೇ ಕ್ರಿಯಾ ಕಾರ್ಡ್‌ಗಳು ಜಾರಿಯಾಗಿಲ್ಲ.",
      noOutbreaks: "ಯಾವುದೇ ಸಕ್ರಿಯ EWMA ಪ್ರಕೋಪ ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ.",
      noEvents: "CRDT ಘಟನೆಗಳಿಗಾಗಿ ಕಾಯಲಾಗುತ್ತಿದೆ...",
      outbreakPrefix: "EWMA ಸಾಂಕ್ರಾಮಿಕ ಪ್ರಕೋಪ",
      villagePrefix: "ಗ್ರಾಮ:",
      riskLabel: "ಅಪಾಯ",
      riskHigh: "ಹೆಚ್ಚಿನ ಅಪಾಯ",
      riskModerate: "ಮಧ್ಯಮ ಅಪಾಯ",
      riskLow: "ಕಡಿಮೆ ಅಪಾಯ",
      riskEnriched: "ವಿಶ್ಲೇಷಿತ",
      eventsUnit: "ಘಟನೆಗಳು",
      moreItems: "+{n} ಇನ್ನಷ್ಟು",
      peerWatchFamily: "ವಾಚ್ · ರೋಗಿ / ಕುಟುಂಬ",
      peerWatchChw: "ವಾಚ್ · ಆಶಾ ಸಹಾಯಕ",
      peerPhoneAsha: "ಆಶಾ ಫೋನ್ (ಹಂತ ೧)",
      peerHub: "PHC ಕೇಂದ್ರ (ಹಂತ ೨)",
      targetWatch: "ವಾಚ್ (ಹಂತ ೦)",
      targetPhone: "ಆಶಾ ಫೋನ್ (ಹಂತ ೧)",
      targetHub: "PHC ಕೇಂದ್ರ (ಹಂತ ೨)",
      targetMesh: "ಎಲ್ಲಾ ಮೆಶ್ ಸಾಧನಗಳು",
      sevRed: "ಕೆಂಪು · ತುರ್ತು ಚಿಕಿತ್ಸೆ",
      sevYellow: "ಹಳದಿ · PHC ತಪಾಸಣೆ",
      sevGreen: "ಹಸಿರು · ಮನೆ ಆರೈಕೆ",
      prioCritical: "ಅತಿ ಗಂಭೀರ",
      prioHigh: "ಹೆಚ್ಚು",
      prioMedium: "ಮಧ್ಯಮ",
      prioLow: "ಕಡಿಮೆ",
      statusOpen: "ತೆರೆದಿದೆ",
      statusAcked: "ದೃಢೀಕರಿಸಲಾಗಿದೆ",
      statusResolved: "ಪರಿಹರಿಸಲಾಗಿದೆ",
      statusPending: "ಬಾಕಿ ಇದೆ",
      watchModeFamily: "ರೋಗಿ / ಕುಟುಂಬ",
      watchModeChw: "ಆಶಾ ಸಹಾಯಕ",
      evVoiceNote: "ಧ್ವನಿ ಟಿಪ್ಪಣಿ",
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
      proofCloudRpcs: "೦ ಕ್ಲೌಡ್ ಕರೆಗಳು",
      proofSafetyFloor: "WHO ಸುರಕ್ಷತಾ ಮಾನದಂಡ · ೧.೦೦",
      proofZeroBloat: "೦ PyTorch · ೦ CUDA",
      convergedPatientsUnit: "ಸಂಯೋಜಿತ ರೋಗಿಗಳು",
      hubCrdtMergeTitle: "CRDT ದ್ವಂದ್ವ-ರಹಿತ ವಿಲೀನ ಪುರಾವೆ (LWW)",
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
    },
    ta: {
      stageTitle: "ஆரோக்கிய வலையமைப்பு — 3-நிலை நேரடி மேடை",
      stageSubtitle: "கடிகாரம் ↔ தொலைபேசி ↔ மையம் · 2 வி. நேரடி ஒத்திசைவு",
      scMaternal: "1. கடிகார அவசரம்",
      scVoice: "2. குரல் → AI",
      scOutbreak: "3. கிராமப் பரவல்",
      scCrdt: "4. CRDT இணைப்பு",
      scMaternalTitle: "கர்ப்பிணி கடிகார அவசர அழைப்பு → ஆஷா தொலைபேசி",
      scVoiceTitle: "இணையமில்லா குரல் குறிப்பு → மைய AI பகுப்பாய்வு",
      scOutbreakTitle: "கிராம அளவிலான EWMA தொற்று பரவல் கண்டறிதல்",
      scCrdtTitle: "இணையமில்லா முரணற்ற CRDT தரவு இணைப்பு",
      scReset: "மீட்டமை",
      runEnrichment: "AI இயக்கு",
      runningEnrichment: "இயங்குகிறது...",
      badgeOffline: "இணையமில்லா பாதுகாப்பு",
      themeLight: "வெளிச்சம்",
      themeDark: "இருள்",
      langToggle: "தமிழ்",
      backToHub: "← மையம்",
      syncIdle: "நேரடி ஒத்திசைவு தயார்",
      syncPulse: "CRDT ஒத்திசைவு துடிப்பு",
      reconnecting: "மீண்டும் இணைக்கப்படுகிறது...",
      defaultNarrative:
        "கடிகாரத்தில் அபாய அறிகுறியைத் தொடவும், தொலைபேசியில் நோயாளியைப் பதிவு செய்யவும் அல்லது மேலே உள்ள காட்சியைத் தேர்ந்தெடுக்கவும்.",
      scenarioRunning: "மைய CRDT இயந்திரம் மூலம் நேரடி மருத்துவ செயல்முறை இயங்குகிறது...",
      scenarioDonePrefix: "செயலில் உள்ள காட்சி:",
      resetting: "தலைமை மையம் மீட்டமைக்கப்படுகிறது...",
      resetDone: "மைய நிலை சுத்தம் செய்யப்பட்டது. நேரடி கடிகாரம்/தொலைபேசி செயல்முறைக்குத் தயார்.",
      enrichmentDone: "மைய AI பகுப்பாய்வு முடிந்தது — SHAP மதிப்பீடுகள் & நடவடிக்கை அட்டைகள் புதுப்பிக்கப்பட்டன.",
      endpointUnavailable: "சேவை தற்போது கிடைக்கவில்லை.",
      tier0Eyebrow: "நிலை 0 · 256 MB",
      tier1Eyebrow: "நிலை 1 · 4 GB",
      tier2Eyebrow: "நிலை 2 · PHC மைய நுண்ணறிவு",
      tier2EyebrowRam: "நிலை 2 · {ram} GB PHC மைய நுண்ணறிவு",
      reloadWatchTitle: "கடிகாரத்தை மீள ஏற்று",
      reloadPhoneTitle: "தொலைபேசியை மீள ஏற்று",
      colWatchTitle: "கடிகாரத் துணை",
      colWatchSub: "நோயாளி / குடும்பம் & ஆஷா துணை",
      colPhoneTitle: "ஆஷா களத் தொலைபேசி",
      colPhoneSub: "WHO IMNCI + இணையமில்லா சேமிப்பு",
      colHubTitle: "PHC மருத்துவ நுண்ணறிவு",
      colHubSub: "குரல் எழுத்துமாற்றம் · SLM · LightGBM SHAP · EWMA",
      watchCap1: "தனிப்பட்ட அவசர அழைப்பு",
      watchCap2: "1-தொடு அபாய அறிகுறி",
      watchCap3: "நடவடிக்கை எச்சரிக்கை",
      phoneCap1: "WHO IMNCI",
      phoneCap2: "குரல் வரிசை",
      phoneCap3: "HLC ஒத்திசைவு",
      kpiPatients: "நோயாளிகள்",
      kpiRed: "சிவப்பு",
      kpiYellow: "மஞ்சள்",
      kpiGreen: "பச்சை",
      kpiPending: "நிலுவை AI",
      hubPeersTitle: "சாதனங்கள்",
      tabAlerts: "எச்சரிக்கை & அட்டை",
      tabShap: "SHAP & வகைப்பாடு",
      tabStream: "CRDT ஓட்டம்",
      hubActionsTitle: "நடவடிக்கை அட்டைகள் → கடிகாரம் & தொலைபேசி",
      hubOutbreaksTitle: "EWMA தொற்று பரவல் எச்சரிக்கைகள்",
      hubShapTitle: "SHAP அபாய காரணிகள் பகுப்பாய்வு",
      hubTriageTitle: "நேரடி மருத்துவ வகைப்பாடுகள்",
      hubEventsTitle: "சமீபத்திய CRDT ஒத்திசைவு ஓட்டம்",
      noPeers: "இன்னும் சாதனங்கள் ஒத்திசைக்கப்படவில்லை.",
      noTriage: "இன்னும் மருத்துவ வகைப்பாடுகள் இல்லை.",
      noShap: "இன்னும் SHAP அபாய பகுப்பாய்வு இல்லை.",
      noActions: "இன்னும் நடவடிக்கை அட்டைகள் வெளியிடப்படவில்லை.",
      noOutbreaks: "செயலில் உள்ள EWMA தொற்று எச்சரிக்கைகள் இல்லை.",
      noEvents: "CRDT நிகழ்வுகளுக்காகக் காத்திருக்கிறது...",
      outbreakPrefix: "EWMA தொற்று பரவல்",
      villagePrefix: "கிராமம்:",
      riskLabel: "அபாயம்",
      riskHigh: "அதிக அபாயம்",
      riskModerate: "நடுத்தர அபாயம்",
      riskLow: "குறைந்த அபாயம்",
      riskEnriched: "பகுப்பாய்வு செய்யப்பட்டது",
      eventsUnit: "நிகழ்வுகள்",
      moreItems: "+{n} மேலும்",
      peerWatchFamily: "கடிகாரம் · நோயாளி / குடும்பம்",
      peerWatchChw: "கடிகாரம் · ஆஷா துணை",
      peerPhoneAsha: "ஆஷா தொலைபேசி (நிலை 1)",
      peerHub: "PHC மையம் (நிலை 2)",
      targetWatch: "கடிகாரம் (நிலை 0)",
      targetPhone: "ஆஷா தொலைபேசி (நிலை 1)",
      targetHub: "PHC மையம் (நிலை 2)",
      targetMesh: "அனைத்து வலையமைப்பு சாதனங்கள்",
      sevRed: "சிவப்பு · அவசர சிகிச்சை",
      sevYellow: "மஞ்சள் · PHC பரிசோதனை",
      sevGreen: "பச்சை · வீட்டுப் பராமரிப்பு",
      prioCritical: "மிக தீவிரம்",
      prioHigh: "அதிகம்",
      prioMedium: "நடுத்தரம்",
      prioLow: "குறைவு",
      statusOpen: "திறந்த நிலை",
      statusAcked: "ஏற்கப்பட்டது",
      statusResolved: "தீர்க்கப்பட்டது",
      statusPending: "நிலுவையில்",
      watchModeFamily: "நோயாளி / குடும்பம்",
      watchModeChw: "ஆஷா துணை",
      evVoiceNote: "குரல் குறிப்பு",
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
      proofCloudRpcs: "0 மேகக்கணி அழைப்புகள்",
      proofSafetyFloor: "WHO பாதுகாப்புத் தளம் · 1.00",
      proofZeroBloat: "0 PyTorch · 0 CUDA",
      convergedPatientsUnit: "ஒருங்கிணைந்த நோயாளிகள்",
      hubCrdtMergeTitle: "CRDT முரணற்ற தரவு இணைப்பு சான்று (LWW)",
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
    },
  };

  const SCENARIO_TITLE_KEYS = {
    maternal_sos: "scMaternalTitle",
    pediatric_voice_offload: "scVoiceTitle",
    village_outbreak: "scOutbreakTitle",
    crdt_conflict_merge: "scCrdtTitle",
  };

  function readPref(key, allowed, fallback) {
    try {
      const val = window.localStorage.getItem(key);
      if (val && allowed.includes(val)) return val;
    } catch (_err) {
      // Fail-soft when storage is unavailable
    }
    return fallback;
  }

  function writePref(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (_err) {
      // Fail-soft when storage is unavailable
    }
  }

  function readInitialLang() {
    try {
      const params = new URLSearchParams(window.location.search);
      const qLang = params.get("lang");
      if (qLang && SUPPORTED_LANGS.includes(qLang)) {
        writePref(STORAGE_LANG_KEY, qLang);
        return qLang;
      }
    } catch (_err) {
      // Fail-soft when URLSearchParams is unavailable
    }
    return readPref(STORAGE_LANG_KEY, SUPPORTED_LANGS, "en");
  }

  const state = {
    lang: readInitialLang(),
    theme: readPref(STORAGE_THEME_KEY, ["dark", "light"], "dark"),
    activeTab: "alerts",
    activeScenario: null,
    scenarioCatalog: {},
    narrativeState: { kind: "default" },
    lastEventCount: -1,
    lastHlcKey: "",
    pulseTimer: null,
    polling: false,
    reconnecting: false,
    enriching: false,
    demoBusy: false,
    lastSummary: null,
    lastPeers: [],
    lastEvents: [],
  };

  function t(key) {
    return (I18N[state.lang] && I18N[state.lang][key]) || I18N.en[key] || key;
  }

  function formatMore(extraCount) {
    return t("moreItems").replace("{n}", String(extraCount));
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

  function formatHlc(hlc) {
    if (!hlc) return "--";
    return `${hlc.wall_ms}:${hlc.logical}:${hlc.node_id}`;
  }

  function severityLabel(sev) {
    if (sev === "RED_EMERGENCY") return t("sevRed");
    if (sev === "YELLOW_PHC") return t("sevYellow");
    return t("sevGreen");
  }

  function priorityLabel(prio) {
    if (prio === "CRITICAL") return t("prioCritical");
    if (prio === "HIGH") return t("prioHigh");
    if (prio === "LOW") return t("prioLow");
    return t("prioMedium");
  }

  function targetTierLabel(tier) {
    if (tier === "TIER_0_WATCH") return t("targetWatch");
    if (tier === "TIER_1_PHONE") return t("targetPhone");
    if (tier === "TIER_2_HUB") return t("targetHub");
    return t("targetMesh");
  }

  function humanizeCode(raw) {
    const str = String(raw || "").trim();
    if (!str) return "--";
    return str
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .replace(/\b\w/g, (ch) => ch.toUpperCase());
  }

  function humanizeEnumToken(token) {
    const keyMap = {
      TIER_0_WATCH: "targetWatch",
      TIER_1_PHONE: "targetPhone",
      TIER_2_HUB: "targetHub",
      PATIENT_FAMILY: "watchModeFamily",
      CHW_COMPANION: "watchModeChw",
      VOICE_NOTE: "evVoiceNote",
      VOICE_NOTE_RECORDED: "evVoiceNoteRecorded",
      TRIAGE_COMPLETED: "evTriageCompleted",
      PATIENT_REGISTERED: "evPatientRegistered",
      CHECKLIST_RECORDED: "evChecklistRecorded",
      VACCINATION_LOGGED: "evVaccinationLogged",
      ENRICHMENT_COMPLETED: "evEnrichmentCompleted",
      ACTION_CARD_ISSUED: "evActionCardIssued",
      OUTBREAK_ALERT_RAISED: "evOutbreakAlertRaised",
      RED_EMERGENCY: "sevRed",
      YELLOW_PHC: "sevYellow",
      GREEN_HOME: "sevGreen",
      CRITICAL: "prioCritical",
      HIGH: "prioHigh",
      MEDIUM: "prioMedium",
      LOW: "prioLow",
      OPEN: "statusOpen",
      ACKNOWLEDGED: "statusAcked",
      ACKED: "statusAcked",
      RESOLVED: "statusResolved",
      PENDING: "statusPending",
    };
    const key = keyMap[token];
    return key ? t(key) : null;
  }

  const INLINE_ENUM_RE =
    /\b(TIER_0_WATCH|TIER_1_PHONE|TIER_2_HUB|PATIENT_FAMILY|CHW_COMPANION|VOICE_NOTE_RECORDED|VOICE_NOTE|TRIAGE_COMPLETED|PATIENT_REGISTERED|CHECKLIST_RECORDED|VACCINATION_LOGGED|ENRICHMENT_COMPLETED|ACTION_CARD_ISSUED|OUTBREAK_ALERT_RAISED|RED_EMERGENCY|YELLOW_PHC|GREEN_HOME)\b/g;

  function humanizeInlineText(text) {
    if (text === null || text === undefined) return "";
    return String(text).replace(INLINE_ENUM_RE, (match) => humanizeEnumToken(match) || match);
  }

  function humanizeOriginNode(nodeId) {
    const id = String(nodeId || "").trim();
    if (!id) return "--";
    const peers = Array.isArray(state.lastPeers) ? state.lastPeers : [];
    for (const p of peers) {
      const m = p.manifest || p;
      const pid = m.node_id || p.node_id;
      if (pid === id) return humanizePeer(p);
    }
    const lower = id.toLowerCase();
    if (lower.includes("watch")) {
      return lower.includes("family") ? t("peerWatchFamily") : t("peerWatchChw");
    }
    if (lower.includes("phone") || lower.includes("asha")) return t("peerPhoneAsha");
    if (lower.includes("hub") || lower.includes("phc")) return t("peerHub");
    return id;
  }

  function humanizePeer(peer) {
    const m = peer.manifest || peer;
    const tier = m.tier || peer.tier || "";
    const mode = m.watch_mode || peer.watch_mode || "";
    if (tier === "TIER_0_WATCH") {
      return mode === "PATIENT_FAMILY" ? t("peerWatchFamily") : t("peerWatchChw");
    }
    if (tier === "TIER_1_PHONE") {
      return t("peerPhoneAsha");
    }
    if (tier === "TIER_2_HUB") {
      return t("peerHub");
    }
    return m.node_id || peer.node_id || "Peer";
  }

  function buildPatientMap(summary) {
    const map = new Map();
    const list = summary && Array.isArray(summary.patients) ? summary.patients : [];
    for (const pat of list) {
      if (pat && pat.patient_id) {
        map.set(pat.patient_id, pat.full_name || pat.patient_id);
      }
    }
    return map;
  }

  function formatPatientName(patientId, patientMap, fallback) {
    if (patientId && patientMap.has(patientId)) {
      return patientMap.get(patientId);
    }
    return patientId || fallback || "--";
  }

  function renderNarrative() {
    const ns = state.narrativeState;
    if (ns.kind === "scenario_loading") {
      setText("narrative-text", t("scenarioRunning"));
      return;
    }
    if (ns.kind === "scenario_loaded") {
      const titleKey = SCENARIO_TITLE_KEYS[ns.scenarioId];
      const localizedTitle = titleKey ? t(titleKey) : ns.scenarioId;
      const catItem = state.scenarioCatalog[ns.scenarioId];
      const suffix =
        state.lang === "en" && catItem && catItem.subtitle
          ? ` — ${catItem.subtitle}`
          : ` (${ns.eventsAdded} ${t("eventsUnit")}, ${ns.patientCount} ${t("kpiPatients")})`;
      setText("narrative-text", `${t("scenarioDonePrefix")} ${localizedTitle}${suffix}`);
      return;
    }
    if (ns.kind === "resetting") {
      setText("narrative-text", t("resetting"));
      return;
    }
    if (ns.kind === "reset") {
      setText("narrative-text", t("resetDone"));
      return;
    }
    if (ns.kind === "enrichment_ok") {
      setText("narrative-text", t("enrichmentDone"));
      return;
    }
    if (ns.kind === "error") {
      setText("narrative-text", t("endpointUnavailable"));
      return;
    }
    setText("narrative-text", t("defaultNarrative"));
  }

  function applyTheme() {
    document.documentElement.setAttribute("data-theme", state.theme);
    setText("btn-stage-theme", state.theme === "dark" ? t("themeLight") : t("themeDark"));
  }

  function translateRiskBand(band) {
    if (band === "RED_EMERGENCY") return t("sevRed");
    if (band === "YELLOW_PHC") return t("sevYellow");
    if (band === "GREEN_HOME") return t("sevGreen");
    if (band === "HIGH") return t("riskHigh");
    if (band === "MODERATE" || band === "MEDIUM") return t("riskModerate");
    if (band === "LOW") return t("riskLow");
    return band ? humanizeCode(band) : t("riskEnriched");
  }

  function translateEventType(eventType) {
    const map = {
      PATIENT_REGISTERED: "evPatientRegistered",
      TRIAGE_COMPLETED: "evTriageCompleted",
      CHECKLIST_RECORDED: "evChecklistRecorded",
      VACCINATION_LOGGED: "evVaccinationLogged",
      VOICE_NOTE: "evVoiceNote",
      VOICE_NOTE_RECORDED: "evVoiceNoteRecorded",
      ENRICHMENT_COMPLETED: "evEnrichmentCompleted",
      ACTION_CARD_ISSUED: "evActionCardIssued",
      OUTBREAK_ALERT_RAISED: "evOutbreakAlertRaised",
    };
    const key = map[eventType];
    return key ? t(key) : eventType ? humanizeCode(eventType) : "--";
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
    const btns = document.querySelectorAll("#stage-lang-switcher [data-lang]");
    for (const btn of btns) {
      const isSelected = btn.getAttribute("data-lang") === state.lang;
      btn.classList.toggle("active", isSelected);
      btn.setAttribute("aria-pressed", String(isSelected));
    }
  }

  function buildFrameUrl(baseSrc, lang) {
    const sep = baseSrc.includes("?") ? "&" : "?";
    return `${baseSrc}${sep}lang=${encodeURIComponent(lang)}`;
  }

  function postLangToFrame(frameId, lang) {
    const frame = document.getElementById(frameId);
    if (!frame || !frame.contentWindow) return;
    try {
      frame.contentWindow.postMessage({ type: "aarogya:setLang", lang }, "*");
    } catch (_err) {
      // Ignore cross-origin postMessage errors
    }
  }

  function broadcastLangToFrames(lang) {
    postLangToFrame("iframe-watch", lang);
    postLangToFrame("iframe-phone", lang);
  }

  function initFrameUrlsWithLang(lang) {
    const pairs = [
      ["iframe-watch", "/watch/?embed=1"],
      ["iframe-phone", "/phone/"],
    ];
    for (const [frameId, baseSrc] of pairs) {
      const frame = document.getElementById(frameId);
      if (!frame) continue;
      frame.addEventListener("load", () => {
        postLangToFrame(frameId, state.lang);
      });
      const nextSrc = buildFrameUrl(baseSrc, lang);
      if (frame.getAttribute("src") !== nextSrc) {
        frame.setAttribute("src", nextSrc);
      } else {
        postLangToFrame(frameId, lang);
      }
    }
  }

  function applyTranslations() {
    document.documentElement.lang = state.lang;
    document.title = t("stageTitle");
    setText("stage-title", t("stageTitle"));
    setText("stage-subtitle", t("stageSubtitle"));
    syncLangSwitcher();
    applyTheme();

    const reloadWatch = document.getElementById("btn-reload-watch");
    if (reloadWatch) {
      reloadWatch.setAttribute("title", t("reloadWatchTitle"));
      reloadWatch.setAttribute("aria-label", t("reloadWatchTitle"));
    }
    const reloadPhone = document.getElementById("btn-reload-phone");
    if (reloadPhone) {
      reloadPhone.setAttribute("title", t("reloadPhoneTitle"));
      reloadPhone.setAttribute("aria-label", t("reloadPhoneTitle"));
    }

    const nodes = document.querySelectorAll("[data-i18n]");
    for (const node of nodes) {
      const key = node.getAttribute("data-i18n");
      if (key) node.textContent = t(key);
    }
    if (state.enriching) {
      setText("btn-stage-enrich", t("runningEnrichment"));
    }
    if (state.reconnecting) {
      setText("sync-pulse-label", t("reconnecting"));
    }

    const evCount = state.lastSummary ? state.lastSummary.event_count ?? 0 : 0;
    setText("stage-metric-events", `${evCount} ${t("eventsUnit")}`);
    renderEngineeringProofStrip(state.lastSummary);
    renderNarrative();
  }

  function setActiveHubTab(tabId) {
    state.activeTab = tabId;
    const buttons = document.querySelectorAll("[data-hub-tab]");
    for (const btn of buttons) {
      const isSelected = btn.getAttribute("data-hub-tab") === tabId;
      btn.classList.toggle("active", isSelected);
      btn.setAttribute("aria-selected", String(isSelected));
    }

    const panelIds = {
      alerts: "hub-panel-alerts",
      shap: "hub-panel-shap",
      stream: "hub-panel-stream",
    };
    for (const [key, panelId] of Object.entries(panelIds)) {
      const panel = document.getElementById(panelId);
      if (panel) panel.classList.toggle("hidden", key !== tabId);
    }
  }

  function triggerSyncPulse() {
    const pill = document.getElementById("sync-pulse-pill");
    const hub = document.getElementById("hub-brain-panel");
    setText("sync-pulse-label", t("syncPulse"));
    if (pill) pill.classList.add("sync-pulsing");
    if (hub) hub.classList.add("hub-synced");

    if (state.pulseTimer !== null) clearTimeout(state.pulseTimer);
    state.pulseTimer = setTimeout(() => {
      if (pill) pill.classList.remove("sync-pulsing");
      if (hub) hub.classList.remove("hub-synced");
      setText("sync-pulse-label", t("syncIdle"));
    }, 1600);
  }

  function normalizeShap(raw) {
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
    if (Array.isArray(val)) return val.map((v) => formatCompactFieldValue(v)).join(", ");
    if (typeof val === "boolean") return val ? "true" : "false";
    const str = String(val);
    return humanizeEnumToken(str) || str;
  }

  function buildCrdtMergeProofCard(proof) {
    const contribs = Array.isArray(proof.contributions) ? proof.contributions : [];
    const flowNodes = [];

    // Show the latest contribution per distinct origin node for crisp diff clarity
    const latestByOrigin = new Map();
    for (const c of contribs) {
      if (c && c.origin_node_id) {
        latestByOrigin.set(c.origin_node_id, c);
      }
    }
    const peerEdits = Array.from(latestByOrigin.values());

    peerEdits.forEach((edit, idx) => {
      if (idx > 0) {
        flowNodes.push(el("div", { className: "crdt-op-sep mono" }, "⊕"));
      }
      const fieldChips = Object.entries(edit.fields || {})
        .slice(0, 5)
        .map(([k, v]) =>
          el("span", { className: "crdt-kv-chip mono" }, `${k.replace(/^metadata\./, "")}=${formatCompactFieldValue(v)}`)
        );
      const shortHlc = edit.hlc ? `${edit.hlc.wall_ms}:${edit.hlc.logical}` : edit.hlc_str || "--";
      flowNodes.push(
        el(
          "div",
          { className: "crdt-contrib-box" },
          el(
            "div",
            { className: "crdt-contrib-head" },
            el("span", { className: "mono", title: edit.origin_node_id || "" }, humanizeOriginNode(edit.origin_node_id)),
            el("span", { className: "badge badge-accent mono" }, `HLC ${shortHlc}`)
          ),
          fieldChips.length > 0 ? el("div", { className: "crdt-kv-row" }, ...fieldChips) : null
        )
      );
    });

    flowNodes.push(el("div", { className: "crdt-op-sep mono" }, "⇒"));

    const convergedChips = Object.entries(proof.converged_fields || {})
      .slice(0, 7)
      .map(([k, v]) =>
        el("span", { className: "crdt-kv-chip mono" }, `${k.replace(/^metadata\./, "")}=${formatCompactFieldValue(v)}`)
      );
    flowNodes.push(
      el(
        "div",
        { className: "crdt-contrib-box crdt-contrib-converged" },
        el(
          "div",
          { className: "crdt-contrib-head" },
          el("span", null, `${t("convergedRecord")}: ${proof.full_name || proof.patient_id}`),
          el("span", { className: "badge badge-green" }, t("zeroDataLoss"))
        ),
        convergedChips.length > 0 ? el("div", { className: "crdt-kv-row" }, ...convergedChips) : null
      )
    );

    return el(
      "div",
      { className: "crdt-merge-card" },
      el(
        "div",
        { className: "hub-card-head" },
        el("span", { className: "hub-card-title" }, proof.full_name || proof.patient_id),
        proof.simultaneous_wall_ms
          ? el("span", { className: "badge badge-accent" }, t("simultaneousTieBreak"))
          : el("span", { className: "badge badge-green" }, t("zeroDataLoss"))
      ),
      el("div", { className: "crdt-contrib-flow" }, ...flowNodes)
    );
  }

  function renderEngineeringProofStrip(summary) {
    const ep = (summary && summary.engineering_proof) || {};
    const eventsCount = summary ? summary.event_count ?? 0 : 0;
    const patientCount = summary ? summary.patient_count ?? 0 : 0;
    const hlcText =
      summary && summary.latest_hlc ? `HLC ${formatHlc(summary.latest_hlc)}` : "HLC --";

    setText("proof-cloud-rpcs", t("proofCloudRpcs"));
    setText("proof-safety-floor", t("proofSafetyFloor"));
    setText("proof-hlc-vector", hlcText);
    setText(
      "proof-crdt-ratio",
      `${ep.crdt_event_count ?? eventsCount} ${t("eventsUnit")} → ${ep.converged_patient_count ?? patientCount} ${t("convergedPatientsUnit")}`
    );
    setText("proof-zero-bloat", t("proofZeroBloat"));
  }

  function renderHubBrain() {
    const summary = state.lastSummary;
    const peers = state.lastPeers;
    const events = state.lastEvents;
    const patientMap = buildPatientMap(summary);
    renderEngineeringProofStrip(summary);

    if (summary) {
      const manifest = summary.manifest;
      if (manifest && manifest.ram_mb) {
        const ramGb = Math.max(1, Math.round(manifest.ram_mb / 1024));
        setText("hub-tier-eyebrow", t("tier2EyebrowRam").replace("{ram}", String(ramGb)));
      } else {
        setText("hub-tier-eyebrow", t("tier2Eyebrow"));
      }

      const tc = summary.triage_counts || {};
      setText("hub-kpi-patients", summary.patient_count ?? 0);
      setText("hub-kpi-red", tc.RED_EMERGENCY ?? 0);
      setText("hub-kpi-yellow", tc.YELLOW_PHC ?? 0);
      setText("hub-kpi-green", tc.GREEN_HOME ?? 0);
      setText("hub-kpi-pending", summary.pending_enrichments ?? 0);
      setText("stage-metric-events", `${summary.event_count ?? 0} ${t("eventsUnit")}`);
      setText("stage-metric-hlc", summary.latest_hlc ? `HLC ${formatHlc(summary.latest_hlc)}` : "HLC --");

      // Pinned Outbreak Banner (never scrolls out of view)
      const ob = document.getElementById("hub-outbreak-banner");
      const alerts = Array.isArray(summary.outbreak_alerts) ? summary.outbreak_alerts : [];
      setText("hub-outbreaks-count", alerts.length);
      if (ob) {
        if (alerts.length > 0) {
          const latest = alerts[alerts.length - 1];
          const p = latest.payload || {};
          const detail =
            p.message ||
            (p.syndrome ? translateSyndrome(p.syndrome) : null) ||
            (p.village_id ? `${t("villagePrefix")} ${p.village_id}` : null) ||
            latest.event_id;
          ob.classList.remove("hidden");
          ob.replaceChildren(
            el("strong", null, `${t("outbreakPrefix")}: ${detail}`),
            el("span", { className: "badge badge-red" }, String(alerts.length))
          );
        } else {
          ob.classList.add("hidden");
          ob.replaceChildren();
        }
      }

      // Outbreak list inside Alerts & Cards tab
      const obList = document.getElementById("hub-outbreaks-list");
      if (obList) {
        if (alerts.length === 0) {
          obList.replaceChildren(el("p", { className: "empty-state" }, t("noOutbreaks")));
        } else {
          const visibleAlerts = alerts.slice(0, 3).map((alert) => {
            const p = alert.payload || {};
            const title = p.syndrome
              ? translateSyndrome(p.syndrome)
              : p.disease || p.title || translateEventType(alert.event_type);
            const village = p.village_id ? `${t("villagePrefix")} ${p.village_id}` : "EWMA";
            const detail = p.message || p.rationale || "";
            return el(
              "div",
              { className: "hub-card hub-card-red" },
              el(
                "div",
                { className: "hub-card-head" },
                el("span", { className: "hub-card-title" }, title),
                el("span", { className: "badge badge-red mono" }, village)
              ),
              detail ? el("div", { className: "hub-card-meta" }, detail) : null
            );
          });
          if (alerts.length > 3) {
            visibleAlerts.push(el("span", { className: "badge badge-more" }, formatMore(alerts.length - 3)));
          }
          obList.replaceChildren(...visibleAlerts);
        }
      }

      // Action Cards inside Alerts & Cards tab
      const actContainer = document.getElementById("hub-actions-list");
      const actionCards = Array.isArray(summary.action_cards) ? summary.action_cards : [];
      setText("hub-actions-count", actionCards.length);
      setText("tab-count-alerts", actionCards.length + alerts.length);
      if (actContainer) {
        if (actionCards.length === 0) {
          actContainer.replaceChildren(el("p", { className: "empty-state" }, t("noActions")));
        } else {
          const cards = actionCards.slice(0, 4).map((card) => {
            const prio = card.priority || "MEDIUM";
            const badgeCls =
              prio === "CRITICAL"
                ? "badge badge-red"
                : prio === "HIGH"
                  ? "badge badge-yellow"
                  : "badge badge-green";
            const cardCls =
              prio === "CRITICAL"
                ? "hub-card hub-card-red"
                : prio === "HIGH"
                  ? "hub-card hub-card-yellow"
                  : "hub-card hub-card-green";
            const patName = formatPatientName(card.patient_id, patientMap, "");
            const targetText = targetTierLabel(card.target_tier);
            return el(
              "div",
              { className: cardCls },
              el(
                "div",
                { className: "hub-card-head" },
                el("span", { className: "hub-card-title" }, humanizeInlineText(card.title || card.card_id)),
                el("span", { className: badgeCls }, priorityLabel(prio))
              ),
              card.summary ? el("div", { className: "hub-card-meta" }, humanizeInlineText(card.summary)) : null,
              el("div", { className: "hub-card-meta" }, `${patName} → ${targetText}`)
            );
          });
          if (actionCards.length > 4) {
            cards.push(el("span", { className: "badge badge-more" }, formatMore(actionCards.length - 4)));
          }
          actContainer.replaceChildren(...cards);
        }
      }

      // CRDT LWW Conflict-Free Merge Proof Cards (Alerts & Stream tabs)
      const mergeProofs = Array.isArray(summary.crdt_merge_proofs) ? summary.crdt_merge_proofs : [];
      for (const [wrapId, listId] of [
        ["hub-crdt-proof-alerts", "hub-crdt-proof-alerts-list"],
        ["hub-crdt-proof-stream", "hub-crdt-proof-stream-list"],
      ]) {
        const wrap = document.getElementById(wrapId);
        const listEl = document.getElementById(listId);
        if (!wrap || !listEl) continue;
        if (mergeProofs.length > 0) {
          wrap.classList.remove("hidden");
          listEl.replaceChildren(...mergeProofs.slice(0, 2).map((pf) => buildCrdtMergeProofCard(pf)));
        } else {
          wrap.classList.add("hidden");
          listEl.replaceChildren();
        }
      }

      // SHAP Bars + Enrichment Pipeline Provenance inside SHAP & Triage tab
      const shapContainer = document.getElementById("hub-shap-list");
      const enrichments = Array.isArray(summary.enrichments) ? summary.enrichments : [];
      setText("hub-shap-count", enrichments.length);
      if (shapContainer) {
        if (enrichments.length === 0) {
          shapContainer.replaceChildren(el("p", { className: "empty-state" }, t("noShap")));
        } else {
          const cards = enrichments.slice(0, 3).map((item) => {
            const entries = normalizeShap(item.shap_attributions).sort(
              (a, b) => Math.abs(b.value) - Math.abs(a.value)
            );
            const maxAbs = Math.max(0.01, ...entries.map((e) => Math.abs(e.value)));
            const scoreText =
              item.risk_score !== null && item.risk_score !== undefined
                ? `${t("riskLabel")}: ${Number(item.risk_score).toFixed(2)}`
                : translateRiskBand(item.risk_band);
            const patName = formatPatientName(item.patient_id, patientMap, item.event_id);

            const stageLabels = [
              item.audio_source === "blob" ? `${t("stageAudio")}` : t("stageAsr"),
              t("stageSlm"),
              item.triage_severity ? `${t("stageTriage")}` : null,
              t("stageShap"),
            ].filter(Boolean);
            const pipelineNodes = [];
            stageLabels.forEach((lbl, idx) => {
              if (idx > 0) pipelineNodes.push(el("span", { className: "pipeline-arrow" }, "→"));
              pipelineNodes.push(el("span", { className: "pipeline-stage mono" }, lbl));
            });

            const symptoms = Array.isArray(item.extracted_symptoms) ? item.extracted_symptoms : [];
            const dangerFlags = Array.isArray(item.candidate_danger_flags) ? item.candidate_danger_flags : [];
            const tagChips = [
              ...dangerFlags.slice(0, 3).map((flag) =>
                el("span", { className: "badge badge-red mono" }, `${t("dangerFlagsLabel")}: ${humanizeCode(flag)}`)
              ),
              ...symptoms.slice(0, 3).map((sym) =>
                el("span", { className: "crdt-kv-chip mono" }, `${t("symptomsLabel")}: ${humanizeCode(sym)}`)
              ),
            ];

            const rows = entries.slice(0, 6).map((entry) => {
              const pct = Math.min(100, Math.round((Math.abs(entry.value) / maxAbs) * 100));
              const isPos = entry.value >= 0;
              const fill = el("div", { className: isPos ? "shap-fill-pos" : "shap-fill-neg" });
              fill.style.width = `${pct}%`;
              return el(
                "div",
                { className: "shap-row" },
                el("span", { className: "mono shap-name", title: entry.name }, humanizeCode(entry.name)),
                el("div", { className: "shap-track" }, fill),
                el(
                  "span",
                  { className: `mono shap-num ${isPos ? "shap-num-pos" : "shap-num-neg"}` },
                  (isPos ? "+" : "") + entry.value.toFixed(2)
                )
              );
            });

            return el(
              "div",
              { className: "hub-card" },
              el(
                "div",
                { className: "hub-card-head" },
                el("span", { className: "hub-card-title", title: item.patient_id || "" }, patName),
                el("span", { className: "badge badge-yellow" }, scoreText)
              ),
              el("div", { className: "pipeline-trace" }, ...pipelineNodes),
              item.transcript
                ? el("div", { className: "transcript-snippet" }, `"${String(item.transcript).slice(0, 120)}"`)
                : null,
              tagChips.length > 0 ? el("div", { className: "crdt-kv-row" }, ...tagChips) : null,
              item.summary ? el("div", { className: "hub-card-meta" }, humanizeInlineText(item.summary)) : null,
              rows.length > 0
                ? el(
                    "div",
                    { className: "shap-legend" },
                    el("span", { className: "shap-legend-pos" }, t("shapPosLegend")),
                    el("span", { className: "shap-legend-neg" }, t("shapNegLegend"))
                  )
                : null,
              ...rows
            );
          });
          if (enrichments.length > 3) {
            cards.push(el("span", { className: "badge badge-more" }, formatMore(enrichments.length - 3)));
          }
          shapContainer.replaceChildren(...cards);
        }
      }

      // Real-time Triage Decisions inside SHAP & Triage tab
      const triageContainer = document.getElementById("hub-triage-list");
      const history = Array.isArray(summary.triage_history) ? summary.triage_history : [];
      const enrTriages = [];
      for (const enr of enrichments) {
        const ta = enr && enr.payload && enr.payload.triage_assessment;
        if (ta && typeof ta === "object" && ta.severity) enrTriages.push(ta);
      }
      const triages = [...history, ...enrTriages].reverse();
      setText("hub-triage-count", triages.length);
      setText("tab-count-shap", enrichments.length + triages.length);
      if (triageContainer) {
        if (triages.length === 0) {
          triageContainer.replaceChildren(el("p", { className: "empty-state" }, t("noTriage")));
        } else {
          const cards = triages.slice(0, 4).map((item) => {
            const sev = item.severity || "GREEN_HOME";
            const badgeCls =
              sev === "RED_EMERGENCY"
                ? "badge badge-red"
                : sev === "YELLOW_PHC"
                  ? "badge badge-yellow"
                  : "badge badge-green";
            const cardCls =
              sev === "RED_EMERGENCY"
                ? "hub-card hub-card-red"
                : sev === "YELLOW_PHC"
                  ? "hub-card hub-card-yellow"
                  : "hub-card hub-card-green";
            const patName = formatPatientName(item.patient_id, patientMap, item.assessment_id);
            return el(
              "div",
              { className: cardCls },
              el(
                "div",
                { className: "hub-card-head" },
                el("span", { className: "hub-card-title", title: item.patient_id || "" }, patName),
                el("span", { className: badgeCls }, severityLabel(sev))
              ),
              item.rationale ? el("div", { className: "hub-card-meta" }, humanizeInlineText(item.rationale)) : null
            );
          });
          if (triages.length > 4) {
            cards.push(el("span", { className: "badge badge-more" }, formatMore(triages.length - 4)));
          }
          triageContainer.replaceChildren(...cards);
        }
      }
    }

    // Humanized Synced Peers strip
    const peersContainer = document.getElementById("hub-peers-list");
    const peerList = Array.isArray(peers) ? peers : [];
    let watchCount = 0;
    let phoneCount = 0;
    for (const p of peerList) {
      const tier = (p.manifest && p.manifest.tier) || p.tier || "";
      if (tier === "TIER_0_WATCH") watchCount += 1;
      if (tier === "TIER_1_PHONE") phoneCount += 1;
    }
    setText("watch-peer-badge", watchCount);
    setText("phone-peer-badge", phoneCount);

    if (peersContainer) {
      if (peerList.length === 0) {
        peersContainer.replaceChildren(el("span", { className: "peer-empty" }, t("noPeers")));
      } else {
        const chips = peerList.slice(0, 4).map((p) => {
          const m = p.manifest || p;
          const nodeId = m.node_id || p.node_id || "peer";
          return el(
            "span",
            { className: "peer-chip", title: nodeId },
            el("span", { className: "peer-chip-dot", "aria-hidden": "true" }),
            el("span", null, humanizePeer(p))
          );
        });
        if (peerList.length > 4) {
          chips.push(el("span", { className: "badge badge-more" }, formatMore(peerList.length - 4)));
        }
        peersContainer.replaceChildren(...chips);
      }
    }

    // CRDT Sync Stream inside CRDT Stream tab
    const eventsContainer = document.getElementById("hub-events-list");
    const evList = Array.isArray(events) ? events : [];
    const totalEvents = summary ? summary.event_count ?? evList.length : evList.length;
    setText("hub-events-count", totalEvents);
    setText("tab-count-stream", totalEvents);
    if (eventsContainer) {
      if (evList.length === 0) {
        eventsContainer.replaceChildren(el("p", { className: "empty-state" }, t("noEvents")));
      } else {
        const visible = evList.slice(0, 8);
        const rows = visible.map((evt) => {
          const patName = evt.patient_id
            ? formatPatientName(evt.patient_id, patientMap, evt.patient_id)
            : "--";
          return el(
            "div",
            { className: "stream-row" },
            el(
              "div",
              { className: "stream-left" },
              el("span", { className: "stream-origin mono", title: evt.origin_node_id || "" }, humanizeOriginNode(evt.origin_node_id)),
              el("span", { className: "stream-meta" }, `${patName} · ${formatHlc(evt.hlc)}`)
            ),
            el("span", { className: "badge badge-accent", title: evt.event_type || "" }, translateEventType(evt.event_type))
          );
        });
        if (totalEvents > visible.length) {
          rows.push(el("span", { className: "badge badge-more" }, formatMore(totalEvents - visible.length)));
        }
        eventsContainer.replaceChildren(...rows);
      }
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

  async function loadScenarioCatalog() {
    const data = await fetchJsonSafe("/api/v1/demo/scenarios");
    if (Array.isArray(data)) {
      for (const item of data) {
        if (item && item.id) {
          state.scenarioCatalog[item.id] = item;
        }
      }
    }
  }

  async function pollHub() {
    if (state.polling) return;
    state.polling = true;
    try {
      const [summary, peersResp, events] = await Promise.all([
        fetchJsonSafe("/api/v1/dashboard/summary"),
        fetchJsonSafe("/api/v1/peers"),
        fetchJsonSafe("/api/v1/events?limit=8"),
      ]);

      if (summary) {
        const wasReconnecting = state.reconnecting;
        state.reconnecting = false;
        const nextCount = summary.event_count ?? 0;
        const nextHlc = summary.latest_hlc ? formatHlc(summary.latest_hlc) : "";
        if (
          state.lastEventCount !== -1 &&
          (nextCount !== state.lastEventCount || nextHlc !== state.lastHlcKey)
        ) {
          triggerSyncPulse();
        } else if (wasReconnecting && state.pulseTimer === null) {
          setText("sync-pulse-label", t("syncIdle"));
        }
        if (wasReconnecting && state.narrativeState.kind === "error") {
          state.narrativeState = { kind: "default" };
          renderNarrative();
        }
        state.lastEventCount = nextCount;
        state.lastHlcKey = nextHlc;
        state.lastSummary = summary;
      } else {
        state.reconnecting = true;
        setText("sync-pulse-label", t("reconnecting"));
      }

      if (peersResp !== null) {
        state.lastPeers = Array.isArray(peersResp) ? peersResp : peersResp.peers || [];
      } else if (summary && Array.isArray(summary.peers)) {
        state.lastPeers = summary.peers;
      }

      if (Array.isArray(events)) {
        state.lastEvents = events;
      }

      renderHubBrain();
      setText("hub-last-tick", state.reconnecting ? t("reconnecting") : new Date().toLocaleTimeString());
    } finally {
      state.polling = false;
    }
  }

  function updateScenarioPills() {
    const pills = document.querySelectorAll("[data-scenario]");
    for (const pill of pills) {
      pill.classList.toggle("active", pill.getAttribute("data-scenario") === state.activeScenario);
    }
  }

  async function runScenario(scenarioId) {
    if (state.demoBusy) return;
    state.demoBusy = true;
    const controls = document.querySelectorAll("[data-scenario], #btn-stage-reset");
    for (const c of controls) c.disabled = true;
    state.narrativeState = { kind: "scenario_loading", scenarioId };
    renderNarrative();

    try {
      const res = await fetch(`/api/v1/demo/load/${encodeURIComponent(scenarioId)}`, {
        method: "POST",
      });
      if (!res.ok) {
        state.narrativeState = { kind: "error" };
        renderNarrative();
        return;
      }
      const data = await res.json();
      state.activeScenario = scenarioId;
      updateScenarioPills();
      state.narrativeState = {
        kind: "scenario_loaded",
        scenarioId,
        eventsAdded: data.events_added ?? 0,
        patientCount: data.patient_count ?? 0,
      };
      renderNarrative();
      triggerSyncPulse();
      await pollHub();
    } catch (_err) {
      state.narrativeState = { kind: "error" };
      renderNarrative();
    } finally {
      state.demoBusy = false;
      for (const c of controls) c.disabled = false;
    }
  }

  async function resetStage() {
    if (state.demoBusy) return;
    state.demoBusy = true;
    const controls = document.querySelectorAll("[data-scenario], #btn-stage-reset");
    for (const c of controls) c.disabled = true;
    state.narrativeState = { kind: "resetting" };
    renderNarrative();
    try {
      const res = await fetch("/api/v1/demo/reset", { method: "POST" });
      if (!res.ok) {
        state.narrativeState = { kind: "error" };
        renderNarrative();
        return;
      }
      state.activeScenario = null;
      updateScenarioPills();
      state.narrativeState = { kind: "reset" };
      renderNarrative();
      await pollHub();
    } catch (_err) {
      state.narrativeState = { kind: "error" };
      renderNarrative();
    } finally {
      state.demoBusy = false;
      for (const c of controls) c.disabled = false;
    }
  }

  async function runEnrichment() {
    if (state.enriching) return;
    state.enriching = true;
    const btn = document.getElementById("btn-stage-enrich");
    if (btn) {
      btn.disabled = true;
      btn.textContent = t("runningEnrichment");
    }
    try {
      let res = await fetch("/api/v1/enrichment/run", { method: "POST" });
      if (res.status === 404) {
        res = await fetch("/api/v1/enrichment/run-once", { method: "POST" });
      }
      state.narrativeState = res.ok ? { kind: "enrichment_ok" } : { kind: "error" };
      renderNarrative();
      if (res.ok) triggerSyncPulse();
      await pollHub();
    } catch (_err) {
      state.narrativeState = { kind: "error" };
      renderNarrative();
    } finally {
      state.enriching = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = t("runEnrichment");
      }
    }
  }

  function reloadIframe(frameId, fallbackSrc) {
    const frame = document.getElementById(frameId);
    if (!frame) return;
    try {
      if (frame.contentWindow) {
        frame.contentWindow.location.reload();
        return;
      }
    } catch (_err) {
      // Cross-origin fallback
    }
    frame.setAttribute("src", buildFrameUrl(fallbackSrc, state.lang));
  }

  function setLanguage(lang, shouldBroadcast) {
    if (!SUPPORTED_LANGS.includes(lang)) return;
    const changed = state.lang !== lang;
    state.lang = lang;
    writePref(STORAGE_LANG_KEY, state.lang);
    if (changed) {
      applyTranslations();
      renderHubBrain();
    }
    if (shouldBroadcast) {
      broadcastLangToFrames(state.lang);
    }
  }

  function bindEvents() {
    const themeBtn = document.getElementById("btn-stage-theme");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => {
        state.theme = state.theme === "dark" ? "light" : "dark";
        writePref(STORAGE_THEME_KEY, state.theme);
        applyTheme();
      });
    }

    const langBtns = document.querySelectorAll("#stage-lang-switcher [data-lang]");
    for (const btn of langBtns) {
      btn.addEventListener("click", () => {
        const nextLang = btn.getAttribute("data-lang");
        if (nextLang) setLanguage(nextLang, true);
      });
    }

    window.addEventListener("message", (ev) => {
      if (ev && ev.data && ev.data.type === "aarogya:setLang") {
        setLanguage(ev.data.lang, false);
      }
    });

    window.addEventListener("storage", (ev) => {
      if (ev && ev.key === STORAGE_LANG_KEY && ev.newValue) {
        setLanguage(ev.newValue, true);
      }
    });

    const tabBtns = document.querySelectorAll("[data-hub-tab]");
    for (const btn of tabBtns) {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-hub-tab");
        if (tab) setActiveHubTab(tab);
      });
    }

    const scenarioBtns = document.querySelectorAll("[data-scenario]");
    for (const btn of scenarioBtns) {
      btn.addEventListener("click", () => {
        const sid = btn.getAttribute("data-scenario");
        if (sid) runScenario(sid);
      });
    }

    const resetBtn = document.getElementById("btn-stage-reset");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        resetStage();
      });
    }

    const enrichBtn = document.getElementById("btn-stage-enrich");
    if (enrichBtn) {
      enrichBtn.addEventListener("click", () => {
        runEnrichment();
      });
    }

    const reloadWatch = document.getElementById("btn-reload-watch");
    if (reloadWatch) {
      reloadWatch.addEventListener("click", () => {
        reloadIframe("iframe-watch", "/watch/?embed=1");
      });
    }

    const reloadPhone = document.getElementById("btn-reload-phone");
    if (reloadPhone) {
      reloadPhone.addEventListener("click", () => {
        reloadIframe("iframe-phone", "/phone/");
      });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    applyTranslations();
    initFrameUrlsWithLang(state.lang);
    setActiveHubTab(state.activeTab);
    loadScenarioCatalog();
    pollHub();
    setInterval(() => {
      if (!document.hidden) pollHub();
    }, 2000);
  });
})();
