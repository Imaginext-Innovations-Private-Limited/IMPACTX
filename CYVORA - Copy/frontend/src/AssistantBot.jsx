import { useEffect, useRef, useState } from "react";
import { Bot, Send, X } from "lucide-react";

// ---------------------------------------------------------------------------
// CYVORA Assistant — a help bot for new users. Speaks English, Hindi,
// Kannada and Tamil. It knows every box on the site (pages, panels, cards,
// scores, header, footer) and can take you to the exact spot: tap a button
// and it navigates there, scrolls to the box, and highlights it.
// ---------------------------------------------------------------------------

const LANGUAGES = [
  { id: "en", label: "EN", name: "English" },
  { id: "hi", label: "हिं", name: "हिन्दी" },
  { id: "kn", label: "ಕನ್ನಡ", name: "ಕನ್ನಡ" },
  { id: "ta", label: "தமிழ்", name: "தமிழ்" },
];

const PAGE_NAMES = {
  home: { en: "Home", hi: "होम", kn: "ಹೋಂ", ta: "முகப்பு" },
  soc: {
    en: "Security Operations Center",
    hi: "सुरक्षा संचालन केंद्र",
    kn: "ಭದ್ರತಾ ಕಾರ್ಯಾಚರಣೆ ಕೇಂದ್ರ",
    ta: "பாதுகாப்பு செயல்பாட்டு மையம்",
  },
  network: { en: "Network", hi: "नेटवर्क", kn: "ನೆಟ್‌ವರ್ಕ್", ta: "நெட்வொர்க்" },
  reports: { en: "Reports", hi: "रिपोर्ट", kn: "ವರದಿಗಳು", ta: "அறிக்கைகள்" },
};

const UI_TEXT = {
  en: {
    subtitle: "Here to help you explore",
    placeholder: "Ask about CYVORA…",
    greeting:
      "Hi, I'm the CYVORA assistant.\n\nI know every box on the site — ask about anything, and I'll answer with a button that takes you straight to that exact box.",
    fallback:
      "I don't know that yet, but I'm good at the tour. Try “Show me live stats”, “Where are the threat records?”, or “Why is the backend offline?”",
    takingYou: (page) => `Taking you to ${page} — watch for the glowing box…`,
    liveNumbers: (lines) => `Live numbers on that box right now:\n${lines}`,
    chips: [
      "What is CYVORA?",
      "Show me the Earth map",
      "Show me live stats",
      "Show me detection modules",
      "Where are the threat records?",
      "Why is the backend offline?",
      "Show me the tabs",
    ],
    langChanged: "You got it — I'll speak English from now on.",
  },
  hi: {
    subtitle: "आपकी मदद के लिए यहाँ हूँ",
    placeholder: "CYVORA के बारे में पूछें…",
    greeting:
      "नमस्ते, मैं CYVORA असिस्टेंट हूँ।\n\nमैं इस साइट का हर बॉक्स जानता हूँ — आप मुझसे कुछ भी पूछिए, मैं उस बॉक्स तक ले जाने का बटन दूँगा।",
    fallback:
      "ये मैं अभी नहीं जानता, लेकिन मैं इस साइट की जानकारी के लिए बहुत अच्छा हूँ। “मुझे लाइव स्टैट्स दिखाओ”, “थ्रेट रिकॉर्ड्स कहाँ हैं?” या “बैकएंड क्यों ऑफ़लाइन है?” पूछकर देखें।",
    takingYou: (page) => `आपको ${page} ले जा रहा हूँ — चमकता बॉक्स देखें…`,
    liveNumbers: (lines) => `उस बॉक्स पर अभी के लाइव नंबर:\n${lines}`,
    chips: [
      "CYVORA क्या है?",
      "मुझे पृथ्वी का नक्शा दिखाओ",
      "मुझे लाइव स्टैट्स दिखाओ",
      "मुझे डिटेक्शन मॉड्यूल दिखाओ",
      "थ्रेट रिकॉर्ड्स कहाँ हैं?",
      "बैकएंड क्यों ऑफ़लाइन है?",
      "मुझे टैब दिखाओ",
    ],
    langChanged: "ठीक है — अब मैं हिंदी में बात करूँगा।",
  },
  kn: {
    subtitle: "ನಿಮ್ಮ ಸಹಾಯಕ್ಕೆ ಇಲ್ಲಿದ್ದೇನೆ",
    placeholder: "CYVORA ಬಗ್ಗೆ ಕೇಳಿ…",
    greeting:
      "ನಮಸ್ತೆ, ನಾನು CYVORA ಅಸಿಸ್ಟೆಂಟ್.\n\nಈ ಸೈಟ್‌ನ ಪ್ರತಿಯೊಂದು ಬಾಕ್ಸ್ ನನಗೆ ಗೊತ್ತಿದೆ — ಏನೇ ಕೇಳಿ, ಆ ಬಾಕ್ಸ್‌ಗೆ ನಿಮ್ಮನ್ನು ಕರೆದೊಯ್ಯುವ ಬಟನ್ ನೀಡುತ್ತೇನೆ.",
    fallback:
      "ಇದು ನನಗೆ ಇನ್ನೂ ಗೊತ್ತಿಲ್ಲ, ಆದರೆ ಸೈಟ್ ಟೂರ್‌ನಲ್ಲಿ ನಾನು ಚೆನ್ನಾಗಿದ್ದೇನೆ. “ಲೈವ್ ಸ್ಟ್ಯಾಟ್ಸ್ ತೋರಿಸು”, “ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್ಸ್ ಎಲ್ಲಿ?” ಅಥವಾ “ಬ್ಯಾಕೆಂಡ್ ಏಕೆ ಆಫ್‌ಲೈನ್?” ಎಂದು ಕೇಳಿ ನೋಡಿ.",
    takingYou: (page) => `ನಿಮ್ಮನ್ನು ${page} ಗೆ ಕರೆದೊಯ್ಯುತ್ತಿದ್ದೇನೆ — ಹೊಳೆಯುವ ಬಾಕ್ಸ್ ನೋಡಿ…`,
    liveNumbers: (lines) => `ಆ ಬಾಕ್ಸ್‌ನಲ್ಲಿ ಈಗಿನ ಲೈವ್ ಸಂಖ್ಯೆಗಳು:\n${lines}`,
    chips: [
      "CYVORA ಎಂದರೇನು?",
      "ಭೂಮಿಯ ನಕ್ಷೆ ತೋರಿಸು",
      "ಲೈವ್ ಸ್ಟ್ಯಾಟ್ಸ್ ತೋರಿಸು",
      "ಪತ್ತೆ ಮಾಡ್ಯೂಲ್‌ಗಳನ್ನು ತೋರಿಸು",
      "ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್ಸ್ ಎಲ್ಲಿ?",
      "ಬ್ಯಾಕೆಂಡ್ ಏಕೆ ಆಫ್‌ಲೈನ್?",
      "ಟ್ಯಾಬ್‌ಗಳನ್ನು ತೋರಿಸು",
    ],
    langChanged: "ಸರಿ — ಈಗಿನಿಂದ ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡುತ್ತೇನೆ.",
  },
  ta: {
    subtitle: "உங்களுக்கு உதவ இங்கே இருக்கிறேன்",
    placeholder: "CYVORA பற்றி கேளுங்கள்…",
    greeting:
      "வணக்கம், நான் CYVORA உதவியாளர்.\n\nஇந்த இணையதளத்தின் ஒவ்வொரு பெட்டியும் எனக்குத் தெரியும் — ஏதேனும் கேளுங்கள், அந்த பெட்டிக்கு உங்களை கொண்டு செல்லும் பட்டனை தருகிறேன்.",
    fallback:
      "இது எனக்கு இன்னும் தெரியாது, ஆனால் சுற்றுப்பயணத்தில் நான் நல்லவன். “நேரடி புள்ளிவிவரங்களை காட்டு”, “அச்சுறுத்தல் பதிவுகள் எங்கே?” அல்லது “பேக்எண்ட் ஏன் ஆஃப்லைன்?” என்று கேளுங்கள்.",
    takingYou: (page) => `உங்களை ${page} க்கு கொண்டு செல்கிறேன் — ஒளிரும் பெட்டியை கவனியுங்கள்…`,
    liveNumbers: (lines) => `அந்த பெட்டியில் இப்போதைய நேரடி எண்கள்:\n${lines}`,
    chips: [
      "CYVORA என்றால் என்ன?",
      "பூமி வரைபடத்தை காட்டு",
      "நேரடி புள்ளிவிவரங்களை காட்டு",
      "கண்டறிதல் தொகுதிகளை காட்டு",
      "அச்சுறுத்தல் பதிவுகள் எங்கே?",
      "பேக்எண்ட் ஏன் ஆஃப்லைன்?",
      "அட்டவணைகளை காட்டு",
    ],
    langChanged: "சரி — இனி தமிழில் பேசுகிறேன்.",
  },
};

const LANG_FALLBACK = (local) => local || UI_TEXT.en;

// Each target: { label: {en,hi,kn,ta}, action?, selector?, panel? }
//   action  — page to open ("home" | "soc" | "network" | "reports")
//   selector— CSS selector of the box to scroll to and light up
//   panel   — SOC strip tab label; the bot opens that panel first
const KNOWLEDGE = [
  {
    id: "greeting",
    words: ["hello", "hi", "hey", "help", "guide", "नमस्ते", "सलाम", "हेलो", "मदद", "सहायता", "शुरू", "नया", "ನಮಸ್ತೆ", "ಹಾಯ್", "ಸಹಾಯ", "ಹೊಸ", "ಪ್ರಾರಂಭ", "வணக்கம்", "உதவி", "புதிய", "தொடங்கு"],
    answers: {
      en: UI_TEXT.en.greeting,
      hi: "नमस्ते! मैं आपसे कुछ भी पूछा जा सकता हूँ — बताइए, आप क्या जानना चाहते हैं?\n\nउदाहरण: “पृथ्वी का नक्शा दिखाओ”, “थ्रेट रिकॉर्ड्स कहाँ हैं?” या “बैकएंड क्यों ऑफ़लाइन है?”",
      kn: "ನಮಸ್ತೆ! ನೀವು ನನ್ನನ್ನು ಏನೇ ಕೇಳಬಹುದು — ಹೇಳಿ, ನಿಮಗೆ ಏನು ತಿಳಿಯಬೇಕು?\n\nಉದಾಹರಣೆ: “ಭೂಮಿಯ ನಕ್ಷೆ ತೋರಿಸು”, “ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್ಸ್ ಎಲ್ಲಿ?” ಅಥವಾ “ಬ್ಯಾಕೆಂಡ್ ಏಕೆ ಆಫ್‌ಲೈನ್?”",
      ta: "வணக்கம்! என்னிடம் எதுவும் கேள்வி கேட்கலாம் — சொல்லுங்கள், என்ன தெரிந்து கொள்ள வேண்டும்?\n\nஎடுத்துக்காட்டு: “பூமி வரைபடத்தை காட்டு”, “அச்சுறுத்தல் பதிவுகள் எங்கே?” அல்லது “பேக்எண்ட் ஏன் ஆஃப்லைன்?”",
    },
  },
  {
    id: "about",
    words: ["what is cyvora", "about", "what does this", "what is this", "cyvora", "साइबरा क्या है", "साइबरा", "क्या है", "वेबसाइट", "CYVORA ಎಂದರೇನು", "ಸೈಬರಾ", "ಸೈಟ್", "CYVORA ಎಂದು", "CYVORA ಎಂದರೇನು", "CYVORA என்றால்", "சைபோரா", "இணையதளம்"],
    answers: {
      en: "CYVORA is a network security monitoring dashboard.\n\nIt shows a 3D rotating Earth with live network arcs, satellites and the Moon, and lets you watch security detection in action: packets captured, flows extracted, and threats flagged by four detector modules.",
      hi: "CYVORA एक नेटवर्क सुरक्षा निगरानी डैशबोर्ड है।\n\nइसमें रोटेट करती 3D पृथ्वी, लाइव नेटवर्क आर्क, सैटेलाइट और चंद्रमा दिखते हैं, और आप देख सकते हैं कि सुरक्षा पत्ता कैसे काम करता है — पैकेट, फ्लो, और चार डिटेक्टर मॉड्यूल से पकड़े गए खतरे।",
      kn: "CYVORA ಒಂದು ನೆಟ್‌ವರ್ಕ್ ಭದ್ರತಾ ಮೇಲ್ವಿಚಾರಣಾ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್.\n\nಇದು ಸುತ್ತುತ್ತಿರುವ 3D ಭೂಮಿ, ಲೈವ್ ನೆಟ್‌ವರ್ಕ್ ಆರ್ಕ್‌ಗಳು, ಉಪಗ್ರಹಗಳು ಮತ್ತು ಚಂದ್ರನನ್ನು ತೋರಿಸುತ್ತದೆ. ಪ್ಯಾಕೆಟ್‌ಗಳು, ಫ್ಲೋಗಳು ಮತ್ತು ನಾಲ್ಕು ಡಿಟೆಕ್ಟರ್ ಮಾಡ್ಯೂಲ್‌ಗಳು ಹಿಡಿದ ಬೆದರಿಕೆಗಳನ್ನು ನೀವು ನೇರವಾಗಿ ನೋಡಬಹುದು.",
      ta: "CYVORA ஒரு நெட்வொர்க் பாதுகாப்பு கண்காணிப்பு டாஷ்போர்டு.\n\nஇது சுழலும் 3D பூமி, நேரடி நெட்வொர்க் வளைவுகள், செயற்கைக்கோள்கள் மற்றும் நிலவை காட்டுகிறது. பாக்கெட்டுகள், ஃபுளோக்கள் மற்றும் நான்கு கண்டறிதல் தொகுதிகள் பிடித்த அச்சுறுத்தல்களை நீங்கள் நேரடியாக பார்க்கலாம்.",
    },
    targets: [{ label: { en: "Show me the Earth map", hi: "मुझे पृथ्वी का नक्शा दिखाओ", kn: "ಭೂಮಿಯ ನಕ್ಷೆ ತೋರಿಸು", ta: "பூமி வரைபடத்தை காட்டு" }, action: "home", selector: ".dashboard-map .globe-map" }],
  },
  {
    id: "pages",
    words: ["tabs", "pages", "navigate", "navigation", "menus", "show me the tabs", "टैब", "पेज", "नेविगेशन", "मेनू", "ಟ್ಯಾಬ್", "ಪುಟಗಳು", "ಟ್ಯಾಬ್‌ಗಳನ್ನು ತೋರಿಸು", "அட்டவணைகள்", "பக்கங்கள்", "வழிசெலுத்தல்"],
    answers: {
      en: "The top bar has three tabs:\n\n• Home — the rotating Earth globe, the Security Operations Center button, and the detection strip.\n• Network — interface capture controls, packet and flow stats, and the second globe view.\n• Reports — the capture session report with the latest session's interface and outcome.",
      hi: "ऊपर की बार में तीन टैब हैं:\n\n• होम — घूमती पृथ्वी, सुरक्षा संचालन केंद्र का बटन, और डिटेक्शन स्ट्रिप।\n• नेटवर्क — इंटरफ़ेस कैप्चर कंट्रोल, पैकेट व फ्लो स्टैट्स, और दूसरा ग्लोब व्यू।\n• रिपोर्ट — कैप्चर सेशन रिपोर्ट।",
      kn: "ಮೇಲಿನ ಬಾರ್‌ನಲ್ಲಿ ಮೂರು ಟ್ಯಾಬ್‌ಗಳಿವೆ:\n\n• ಹೋಂ — ಸುತ್ತುತ್ತಿರುವ ಭೂಮಿ, ಭದ್ರತಾ ಕಾರ್ಯಾಚರಣೆ ಕೇಂದ್ರ ಬಟನ್ ಮತ್ತು ಪತ್ತೆ ಸ್ಟ್ರಿಪ್.\n• ನೆಟ್‌ವರ್ಕ್ — ಇಂಟರ್‌ಫೇಸ್ ಕ್ಯಾಪ್ಚರ್ ಕಂಟ್ರೋಲ್‌ಗಳು, ಪ್ಯಾಕೆಟ್/ಫ್ಲೋ ಸ್ಟ್ಯಾಟ್ಸ್ ಮತ್ತು ಎರಡನೇ ಗ್ಲೋಬ್ ವ್ಯೂ.\n• ವರದಿಗಳು — ಕ್ಯಾಪ್ಚರ್ ಸೆಷನ್ ವರದಿ.",
      ta: "மேல் பட்டியில் மூன்று அட்டவணைகள் உள்ளன:\n\n• முகப்பு — சுழலும் பூமி, பாதுகாப்பு செயல்பாட்டு மைய பட்டன் மற்றும் கண்டறிதல் பட்டை.\n• நெட்வொர்க் — இடைமுக கேப்ஷர் கட்டுப்பாடுகள், பாக்கெட்/ஃபுளோ புள்ளிவிவரங்கள் மற்றும் இரண்டாவது குளோப்.\n• அறிக்கைகள் — கேப்ஷர் அமர்வு அறிக்கை.",
    },
    targets: [
      { label: { en: "Show the top tabs", hi: "ऊपर के टैब दिखाओ", kn: "ಮೇಲಿನ ಟ್ಯಾಬ್‌ಗಳನ್ನು ತೋರಿಸು", ta: "மேல் அட்டவணைகளை காட்டு" }, selector: ".top-nav" },
      { label: { en: "Go to Home", hi: "होम पर जाओ", kn: "ಹೋಂ ಗೆ ಹೋಗಿ", ta: "முகப்புக்கு செல்" }, action: "home" },
      { label: { en: "Go to Network", hi: "नेटवर्क पर जाओ", kn: "ನೆಟ್‌ವರ್ಕ್ ಗೆ ಹೋಗಿ", ta: "நெட்வொர்க்குக்கு செல்" }, action: "network" },
      { label: { en: "Go to Reports", hi: "रिपोर्ट पर जाओ", kn: "ವರದಿಗಳಿಗೆ ಹೋಗಿ", ta: "அறிக்கைகளுக்கு செல்" }, action: "reports" },
    ],
  },
  {
    id: "home",
    words: ["home page", "dashboard page", "globe", "earth", "earth map", "spin", "rotate", "drag", "fullscreen", "expand", "hover", "cursor", "पृथ्वी", "नक्शा", "ग्लोब", "घुमाना", "भूमि", "ಭೂಮಿ", "ನಕ್ಷೆ", "ಗ್ಲೋಬ್", "ಸುತ್ತು", "பூமி", "வரைபடம்", "குளோப்", "சுழற்று"],
    answers: {
      en: "Home is the front page:\n\n• The Earth map: drag to spin it (it auto-rotates too), click it to go full-screen, and hover — the globe gently swells and leans toward your cursor.\n• Location arcs appear only after a capture: each line runs from this machine's resolved location to a city that was actually seen in the captured traffic. Before any capture, the globe draws no routes at all. Satellites circle the Earth; the Moon follows its own wide orbit.\n• Under the globe sits the Security Operations Center button.",
      hi: "होम मुख्य पेज है:\n\n• पृथ्वी का नक्शा: घुमाने के लिए ड्रैग करें (यह खुद भी घूमता रहता है), फुल-स्क्रीन के लिए क्लिक करें, और होवर करें — ग्लोब आपके कर्सर की ओर हल्का झुकता है।\n• लोकेशन आर्क केवल कैप्चर के बाद दिखते हैं: हर रेखा इस मशीन की पहचानी गई लोकेशन से उस शहर तक जाती है जो कैप्चर किए गए ट्रैफ़िक में वास्तव में दिखा था। कैप्चर से पहले मैप कोई रूट नहीं दिखाता। सैटेलाइट पृथ्वी के चारों ओर घूमते हैं; चंद्रमा अपनी कक्षा में चलता है।\n• ग्लोब के नीचे सुरक्षा संचालन केंद्र का बटन है।",
      kn: "ಹೋಂ ಮುಖ್ಯ ಪುಟ:\n\n• ಭೂಮಿಯ ನಕ್ಷೆ: ಸುತ್ತಿಸಲು ಎಳೆಯಿರಿ (ತಾನಾಗಿಯೂ ಸುತ್ತುತ್ತದೆ), ಫುಲ್-ಸ್ಕ್ರೀನ್‌ಗೆ ಕ್ಲಿಕ್ ಮಾಡಿ, ಹೊವರ್ ಮಾಡಿದರೆ ಗ್ಲೋಬ್ ನಿಮ್ಮ ಕರ್ಸರ್ ಕಡೆ ಸ್ವಲ್ಪ ಒಲವುತ್ತದೆ.\n• ಸ್ಥಳ ಆರ್ಕ್‌ಗಳು ಕ್ಯಾಪ್ಚರ್ ನಂತರವೇ ಕಾಣುತ್ತವೆ: ಪ್ರತಿ ರೇಖೆ ಈ ಯಂತ್ರದ ಗುರುತಿಸಿದ ಸ್ಥಳದಿಂದ ಕ್ಯಾಪ್ಚರ್ ಮಾಡಿದ ಟ್ರಾಫಿಕ್‌ನಲ್ಲಿ ನಿಜವಾಗಿ ಕಂಡ ನಗರಕ್ಕೆ ಹೋಗುತ್ತದೆ. ಕ್ಯಾಪ್ಚರ್ ಮೊದಲು ನಕ್ಷೆ ಯಾವುದೇ ಮಾರ್ಗ ತೋರಿಸುವುದಿಲ್ಲ. ಉಪಗ್ರಹಗಳು ಭೂಮಿಯ ಸುತ್ತ ಸುತ್ತುತ್ತವೆ; ಚಂದ್ರ ತನ್ನ ಕಕ್ಷೆಯಲ್ಲಿ ಚಲಿಸುತ್ತದೆ.\n• ಗ್ಲೋಬ್ ಕೆಳಗೆ ಭದ್ರತಾ ಕಾರ್ಯಾಚರಣೆ ಕೇಂದ್ರ ಬಟನ್ ಇದೆ.",
      ta: "முகப்பு முக்கிய பக்கம்:\n\n• பூமி வரைபடம்: சுழற்ற இழுக்கவும் (தானாகவும் சுழலும்), முழுத் திரைக்கு கிளிக் செய்யவும், ஹோவர் செய்யும் போது குளோப் உங்கள் கர்சரை நோக்கி சற்று சாயும்.\n• இருப்பிட வளைவுகள் கேப்ஷருக்குப் பிறகே தோன்றும்: ஒவ்வொரு கோடும் இந்த இயந்திரத்தின் கண்டறியப்பட்ட இருப்பிடத்திலிருந்து கேப்ஷர் செய்யப்பட்ட டிராஃபிக்கில் உண்மையில் கண்ட நகரத்திற்குச் செல்லும். கேப்ஷருக்கு முன் வரைபடம் எந்தப் பாதையையும் காட்டாது. செயற்கைக்கோள்கள் பூமியைச் சுற்றும்; நிலவு தன் பாதையில் செல்கிறது.\n• குளோப்பின் கீழ் பாதுகாப்பு செயல்பாட்டு மைய பட்டன் உள்ளது.",
    },
    targets: [
      { label: { en: "Show the Earth map", hi: "पृथ्वी का नक्शा दिखाओ", kn: "ಭೂಮಿಯ ನಕ್ಷೆ ತೋರಿಸು", ta: "பூமி வரைபடத்தை காட்டு" }, action: "home", selector: ".dashboard-map .globe-map" },
      { label: { en: "Show the SOC button", hi: "SOC बटन दिखाओ", kn: "SOC ಬಟನ್ ತೋರಿಸು", ta: "SOC பட்டனை காட்டு" }, action: "home", selector: ".soc-cta" },
      { label: { en: "Open Security Operations Center", hi: "सुरक्षा संचालन केंद्र खोलो", kn: "ಭದ್ರತಾ ಕಾರ್ಯಾಚರಣೆ ಕೇಂದ್ರ ತೆರೆಯಿರಿ", ta: "பாதுகாப்பு செயல்பாட்டு மையத்தை திற" }, action: "soc" },
    ],
  },
  {
    id: "soc",
    words: ["security operations center", "security operations", "operations center", "soc", "open soc", "strip", "panels", "सुरक्षा संचालन", "केंद्र", "ऑपरेशन", "ಭದ್ರತಾ ಕಾರ್ಯಾಚರಣೆ", "ಕೇಂದ್ರ", "ಪ್ಯಾನಲ್‌ಗಳು", "பாதுகாப்பு செயல்பாடு", "மையம்", "பேனல்கள்"],
    answers: {
      en: "The Security Operations Center (SOC) is the heart of CYVORA.\n\nIt opens as a vertical strip of panels — Live capture, Live stats, Detector modules, Threat alerts, Capture overview, Recent detections, and Session summary.\n\nOne panel is open at a time: hover or tap a panel to widen it. Under the strip sits the big Threat Intelligence section.",
      hi: "सुरक्षा संचालन केंद्र (SOC) CYVORA का दिल है।\n\nयह पैनलों की एक वर्टिकल स्ट्रिप के रूप में खुलता है — लाइव कैप्चर, लाइव स्टैट्स, डिटेक्टर मॉड्यूल, थ्रेट अलर्ट्स, कैप्चर ओवरव्यू, रिसेंट डिटेक्शंस, और सेशन समरी।\n\nएक समय पर एक पैनल खुला रहता है: खोलने के लिए किसी पैनल पर होवर या टैप करें। स्ट्रिप के नीचे बड़ा थ्रेट इंटेलिजेंस सेक्शन है।",
      kn: "ಭದ್ರತಾ ಕಾರ್ಯಾಚರಣೆ ಕೇಂದ್ರ (SOC) CYVORA ದ ಹೃದಯ.\n\nಇದು ಲಂಬ ಪ್ಯಾನೆಲ್‌ಗಳ ಸ್ಟ್ರಿಪ್ ಆಗಿ ತೆರೆಯುತ್ತದೆ — ಲೈವ್ ಕ್ಯಾಪ್ಚರ್, ಲೈವ್ ಸ್ಟ್ಯಾಟ್ಸ್, ಡಿಟೆಕ್ಟರ್ ಮಾಡ್ಯೂಲ್‌ಗಳು, ಥ್ರೆಟ್ ಅಲರ್ಟ್‌ಗಳು, ಕ್ಯಾಪ್ಚರ್ ಅವಲೋಕನ, ಇತ್ತೀಚಿನ ಪತ್ತೆಗಳು ಮತ್ತು ಸೆಷನ್ ಸಾರಾಂಶ.\n\nಒಂದೇ ಸಮಯದಲ್ಲಿ ಒಂದು ಪ್ಯಾನೆಲ್ ತೆರೆದಿರುತ್ತದೆ: ಪ್ಯಾನೆಲ್ ಅನ್ನು ಹೊವರ್ ಅಥವಾ ಟ್ಯಾಪ್ ಮಾಡಿ ವಿಸ್ತರಿಸಿ. ಸ್ಟ್ರಿಪ್ ಕೆಳಗೆ ದೊಡ್ಡ ಥ್ರೆಟ್ ಇಂಟೆಲಿಜೆನ್ಸ್ ವಿಭಾಗ ಇದೆ.",
      ta: "பாதுகாப்பு செயல்பாட்டு மையம் (SOC) CYVORA-வின் இதயம்.\n\nஇது செங்குத்து பேனல்களின் பட்டையாக திறக்கும் — நேரடி கேப்ஷர், நேரடி புள்ளிவிவரங்கள், கண்டறிதல் தொகுதிகள், அச்சுறுத்தல் எச்சரிக்கைகள், கேப்ஷர் கண்ணோட்டம், சமீபத்திய கண்டறிதல்கள் மற்றும் அமர்வு சுருக்கம்.\n\nஒரு நேரத்தில் ஒரு பேனல் மட்டும் திறந்திருக்கும்: பேனலின் மீது ஹோவர் அல்லது டேப் செய்து விரிவுபடுத்தவும். பட்டையின் கீழ் பெரிய அச்சுறுத்தல் உளவுத் தகவல் பகுதி உள்ளது.",
    },
    targets: [
      { label: { en: "Open Security Operations Center", hi: "सुरक्षा संचालन केंद्र खोलो", kn: "ಭದ್ರತಾ ಕಾರ್ಯಾಚರಣೆ ಕೇಂದ್ರ ತೆರೆಯಿರಿ", ta: "பாதுகாப்பு செயல்பாட்டு மையத்தை திற" }, action: "soc" },
      { label: { en: "Show the panel strip", hi: "पैनल स्ट्रिप दिखाओ", kn: "ಪ್ಯಾನೆಲ್ ಸ್ಟ್ರಿಪ್ ತೋರಿಸು", ta: "பேனல் பட்டையை காட்டு" }, action: "soc", selector: ".soc-strip" },
    ],
  },
  {
    id: "live-capture",
    words: ["live capture", "live network capture", "लाइव कैप्चर", "लाइव नेटवर्क कैप्चर", "ಲೈವ್ ಕ್ಯಾಪ್ಚರ್", "ನೇರடி கேப்ஷர்", "நேரடி நெட்வொர்க் கேப்ஷர்"],
    answers: {
      en: "Live capture is the first panel in the SOC strip — it's open by default.\n\nPick an interface and a duration, then start the capture. It drives the packet count, flow stats, and every detector verdict.",
      hi: "लाइव कैप्चर SOC स्ट्रिप का पहला पैनल है — यह डिफ़ॉल्ट रूप से खुला है।\n\nइंटरफ़ेस और अवधि चुनें, फिर कैप्चर शुरू करें। यही पैकेट संख्या, फ्लो स्टैट्स और हर डिटेक्टर नतीजे चलाता है।",
      kn: "ಲೈವ್ ಕ್ಯಾಪ್ಚರ್ SOC ಸ್ಟ್ರಿಪ್‌ನ ಮೊದಲ ಪ್ಯಾನೆಲ್ — ಡೀಫಾಲ್ಟ್ ಆಗಿ ತೆರೆದಿದೆ.\n\nಇಂಟರ್‌ಫೇಸ್ ಮತ್ತು ಅವಧಿಯನ್ನು ಆಯ್ಕೆಮಾಡಿ, ನಂತರ ಕ್ಯಾಪ್ಚರ್ ಪ್ರಾರಂಭಿಸಿ. ಇದೇ ಪ್ಯಾಕೆಟ್ ಸಂಖ್ಯೆ, ಫ್ಲೋ ಸ್ಟ್ಯಾಟ್ಸ್ ಮತ್ತು ಪ್ರತಿ ಡಿಟೆಕ್ಟರ್ ಫಲಿತಾಂಶವನ್ನು ನಡೆಸುತ್ತದೆ.",
      ta: "நேரடி கேப்ஷர் SOC பட்டையின் முதல் பேனல் — இயல்பாக திறந்துள்ளது.\n\nஇடைமுகம் மற்றும் காலத்தை தேர்வுசெய்து, கேப்ஷரை தொடங்கவும். இது பாக்கெட் எண், ஃபுளோ புள்ளிவிவரங்கள் மற்றும் ஒவ்வொரு கண்டறிதல் முடிவையும் இயக்குகிறது.",
    },
    targets: [
      { label: { en: "Show Live capture", hi: "लाइव कैप्चर दिखाओ", kn: "ಲೈವ್ ಕ್ಯಾಪ್ಚರ್ ತೋರಿಸು", ta: "நேரடி கேப்ஷரை காட்டு" }, action: "soc", panel: "Live capture" },
      { label: { en: "Go to Network capture controls", hi: "नेटवर्क कैप्चर कंट्रोल पर जाओ", kn: "ನೆಟ್‌ವರ್ಕ್ ಕ್ಯಾಪ್ಚರ್ ಕಂಟ್ರೋಲ್‌ಗಳಿಗೆ ಹೋಗಿ", ta: "நெட்வொர்க் கேப்ஷர் கட்டுப்பாடுகளுக்கு செல்" }, action: "network", selector: ".capture-controls" },
    ],
  },
  {
    id: "live-stats",
    words: ["live stats", "packets captured", "network flows", "live numbers", "scores", "packet count", "flow count", "लाइव स्टैट्स", "पैकेट", "फ्लो", "स्कोर", "ಲೈವ್ ಸ್ಟ್ಯಾಟ್ಸ್", "ಪ್ಯಾಕೆಟ್", "ಫ್ಲೋ", "ஸ்கೋರ್‌ಗಳು", "நேரடி புள்ளிவிவரங்கள்", "பாக்கெட்", "ஃபுளோ", "ஸ்கோர்கள்"],
    answers: {
      en: "The Live stats panel shows four score cards: Packets captured, Network flows, Threat records, and Benign records.",
      hi: "लाइव स्टैट्स पैनल चार स्कोर कार्ड दिखाता है: कैप्चर किए गए पैकेट, नेटवर्क फ्लो, थ्रेट रिकॉर्ड्स, और बेनाइन रिकॉर्ड्स।",
      kn: "ಲೈವ್ ಸ್ಟ್ಯಾಟ್ಸ್ ಪ್ಯಾನೆಲ್ ನಾಲ್ಕು ಸ್ಕೋರ್ ಕಾರ್ಡ್‌ಗಳನ್ನು ತೋರಿಸುತ್ತದೆ: ಸೆರೆಹಿಡಿದ ಪ್ಯಾಕೆಟ್‌ಗಳು, ನೆಟ್‌ವರ್ಕ್ ಫ್ಲೋಗಳು, ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್‌ಗಳು ಮತ್ತು ಬೆನೈನ್ ರೆಕಾರ್ಡ್‌ಗಳು.",
      ta: "நேரடி புள்ளிவிவர பேனல் நான்கு ஸ்கோர் கார்டுகளை காட்டுகிறது: கைப்பற்றப்பட்ட பாக்கெட்டுகள், நெட்வொர்க் ஃபுளோக்கள், அச்சுறுத்தல் பதிவுகள் மற்றும் நல்ல பதிவுகள்.",
    },
    targets: [
      { label: { en: "Show Live stats", hi: "लाइव स्टैट्स दिखाओ", kn: "ಲೈವ್ ಸ್ಟ್ಯಾಟ್ಸ್ ತೋರಿಸು", ta: "நேரடி புள்ளிவிவரங்களை காட்டு" }, action: "soc", panel: "Live stats" },
      { label: { en: "Go to Network stats", hi: "नेटवर्क स्टैट्स पर जाओ", kn: "ನೆಟ್‌ವರ್ಕ್ ಸ್ಟ್ಯಾಟ್ಸ್ ಗೆ ಹೋಗಿ", ta: "நெட்வொர்க் புள்ளிவிவரங்களுக்கு செல்" }, action: "network", selector: ".tab-view > .stats" },
    ],
    live: "stats",
  },
  {
    id: "detectors",
    words: ["detector", "detectors", "modules", "ddos", "c2", "exfiltration", "dns", "tunnelling", "tunneling", "confidence", "how does detection work", "model", "डिटेक्टर", "मॉड्यूल", "आत्मविश्वास", "डिटेक्टर मॉड्यूल", "ಡಿಟೆಕ್ಟರ್", "ಮಾಡ್ಯೂಲ್", "ಆತ್ಮವಿಶ್ವಾಸ", "கண்டறிதல்", "தொகுதிகள்", "நம்பிக்கை", "கண்டறிதல் தொகுதிகள்"],
    answers: {
      en: "CYVORA runs four detector modules:\n\n• DDoS Detection — spots flood-style traffic patterns.\n• C2 Beaconing — flags suspicious command-and-control beacons.\n• Data Exfiltration — watches outgoing data leaving the network.\n• DNS Tunnelling — catches data hidden inside DNS queries.\n\nEach shows a confidence score, and anything abnormal lands in Threat alerts and the threat records table.",
      hi: "CYVORA चार डिटेक्टर मॉड्यूल चलाता है:\n\n• DDoS डिटेक्शन — फ्लड जैसा ट्रैफ़िक पैटर्न पकड़ता है।\n• C2 बीकनिंग — संदिग्ध कमांड-एंड-कंट्रोल बीकन चिह्नित करता है।\n• डेटा एक्सफ़िल्ट्रेशन — नेटवर्क से बाहर जाता डेटा देखता है।\n• DNS टनेलिंग — DNS क्वेरी में छिपा डेटा पकड़ता है।\n\nहर मॉड्यूल आत्मविश्वास स्कोर दिखाता है, और असामान्य चीज़ थ्रेट अलर्ट्स व थ्रेट रिकॉर्ड्स टेबल में जाती है।",
      kn: "CYVORA ನಾಲ್ಕು ಡಿಟೆಕ್ಟರ್ ಮಾಡ್ಯೂಲ್‌ಗಳನ್ನು ಚಲಾಯಿಸುತ್ತದೆ:\n\n• DDoS ಪತ್ತೆ — ಫ್ಲಡ್ ಶೈಲಿಯ ಟ್ರಾಫಿಕ್ ಮಾದರಿಗಳನ್ನು ಗುರುತಿಸುತ್ತದೆ.\n• C2 ಬೀಕನಿಂಗ್ — ಅನುಮಾನಾಸ್ಪದ ಕಮಾಂಡ್-ಅಂಡ್-ಕಂಟ್ರೋಲ್ ಬೀಕನ್‌ಗಳನ್ನು ಸೂಚಿಸುತ್ತದೆ.\n• ಡೇಟಾ ಎಕ್ಸ್‌ಫಿಲ್ಟ್ರೇಷನ್ — ನೆಟ್‌ವರ್ಕ್ ಹೊರಗೆ ಹೋಗುವ ಡೇಟಾವನ್ನು ಗಮನಿಸುತ್ತದೆ.\n• DNS ಟನ್ನೆಲಿಂಗ್ — DNS ಪ್ರಶ್ನೆಗಳಲ್ಲಿ ಅಡಗಿರುವ ಡೇಟಾವನ್ನು ಹಿಡಿಯುತ್ತದೆ.\n\nಪ್ರತಿ ಮಾಡ್ಯೂಲ್ ಆತ್ಮವಿಶ್ವಾಸ ಸ್ಕೋರ್ ತೋರಿಸುತ್ತದೆ, ಮತ್ತು ಅಸಹಜವಾದದ್ದು ಥ್ರೆಟ್ ಅಲರ್ಟ್‌ಗಳು ಮತ್ತು ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್‌ಗಳ ಕೋಷ್ಟಕದಲ್ಲಿ ಕಾಣುತ್ತದೆ.",
      ta: "CYVORA நான்கு கண்டறிதல் தொகுதிகளை இயக்குகிறது:\n\n• DDoS கண்டறிதல் — வெள்ளம் போன்ற டிராஃபிக் வடிவங்களை கண்டறியும்.\n• C2 பீக்கனிங் — சந்தேகமான கட்டளை-மற்றும்-கட்டுப்பாட்டு பீக்கன்களை குறிக்கும்.\n• தரவு கசிவு — நெட்வொர்க்கை விட்டு வெளியேறும் தரவை கவனிக்கும்.\n• DNS சுரங்கம் — DNS வினவல்களில் மறைந்த தரவை பிடிக்கும்.\n\nஒவ்வொரு தொகுதியும் நம்பிக்கை மதிப்பெண்ணை காட்டும், அசாதாரணமானது அச்சுறுத்தல் எச்சரிக்கைகள் மற்றும் அச்சுறுத்தல் பதிவுகள் அட்டவணையில் செல்லும்.",
    },
    targets: [
      { label: { en: "Show Detector modules", hi: "डिटेक्टर मॉड्यूल दिखाओ", kn: "ಡಿಟೆಕ್ಟರ್ ಮಾಡ್ಯೂಲ್‌ಗಳನ್ನು ತೋರಿಸು", ta: "கண்டறிதல் தொகுதிகளை காட்டு" }, action: "soc", panel: "Detector modules" },
      { label: { en: "Show the Threat Intelligence detectors", hi: "थ्रेट इंटेलिजेंस डिटेक्टर दिखाओ", kn: "ಥ್ರೆಟ್ ಇಂಟೆಲಿಜೆನ್ಸ್ ಡಿಟೆಕ್ಟರ್‌ಗಳನ್ನು ತೋರಿಸು", ta: "அச்சுறுத்தல் உளவுத் தகவல் கண்டறிதல்களை காட்டு" }, action: "soc", selector: ".ti-section .ti-detectors" },
    ],
  },
  {
    id: "threat-alerts",
    words: ["threat alerts", "alerts", "थ्रेट अलर्ट्स", "अलर्ट", "ಥ್ರೆಟ್ ಅಲರ್ಟ್‌ಗಳು", "ಎಚ್ಚರಿಕೆಗಳು", "அச்சுறுத்தல் எச்சரிக்கைகள்", "எச்சரிக்கைகள்"],
    answers: {
      en: "Threat alerts is a SOC strip panel listing the most recent threats caught by the detectors. The same threats feed the Threat records card and the records table below.",
      hi: "थ्रेट अलर्ट्स एक SOC स्ट्रिप पैनल है जिसमें डिटेक्टरों द्वारा पकड़े गए हाल के खतरे दिखते हैं। वही खतरे थ्रेट रिकॉर्ड्स कार्ड और नीचे की तालिका में भी आते हैं।",
      kn: "ಥ್ರೆಟ್ ಅಲರ್ಟ್‌ಗಳು SOC ಸ್ಟ್ರಿಪ್ ಪ್ಯಾನೆಲ್, ಡಿಟೆಕ್ಟರ್‌ಗಳು ಹಿಡಿದ ಇತ್ತೀಚಿನ ಬೆದರಿಕೆಗಳನ್ನು ಪಟ್ಟಿ ಮಾಡುತ್ತದೆ. ಅದೇ ಬೆದರಿಕೆಗಳು ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್‌ಗಳ ಕಾರ್ಡ್ ಮತ್ತು ಕೆಳಗಿನ ಕೋಷ್ಟಕದಲ್ಲೂ ಕಾಣುತ್ತವೆ.",
      ta: "அச்சுறுத்தல் எச்சரிக்கைகள் என்பது SOC பட்டை பேனல், கண்டறிதல்கள் பிடித்த சமீபத்திய அச்சுறுத்தல்களை பட்டியலிடும். அதே அச்சுறுத்தல்கள் அச்சுறுத்தல் பதிவுகள் கார்டு மற்றும் கீழே உள்ள அட்டவணையிலும் வரும்.",
    },
    targets: [{ label: { en: "Show Threat alerts", hi: "थ्रेट अलर्ट्स दिखाओ", kn: "ಥ್ರೆಟ್ ಅಲರ್ಟ್‌ಗಳನ್ನು ತೋರಿಸು", ta: "அச்சுறுத்தல் எச்சரிக்கைகளை காட்டு" }, action: "soc", panel: "Threat alerts" }],
  },
  {
    id: "capture-overview",
    words: ["capture overview", "overview chart", "traffic chart", "chart", "कैप्चर ओवरव्यू", "चार्ट", "ಟ್ರಾಫಿಕ್ ಚಾರ್ಟ್", "ಚಾರ್ಟ್", "கேப்ஷர் கண்ணோட்டம்", "சார்ட்"],
    answers: {
      en: "Capture overview plots this session's traffic over time — how packets and flows built up during the capture.",
      hi: "कैप्चर ओवरव्यू इस सेशन का ट्रैफ़िक समय के साथ दिखाता है — कैप्चर के दौरान पैकेट और फ्लो कैसे बढ़े।",
      kn: "ಕ್ಯಾಪ್ಚರ್ ಅವಲೋಕನ ಈ ಸೆಷನ್‌ನ ಟ್ರಾಫಿಕ್ ಅನ್ನು ಕಾಲಾನಂತರದಲ್ಲಿ ಪ್ಲಾಟ್ ಮಾಡುತ್ತದೆ — ಕ್ಯಾಪ್ಚರ್ ಸಮಯದಲ್ಲಿ ಪ್ಯಾಕೆಟ್‌ಗಳು ಮತ್ತು ಫ್ಲೋಗಳು ಹೇಗೆ ಬೆಳೆದವು.",
      ta: "கேப்ஷர் கண்ணோட்டம் இந்த அமர்வின் டிராஃபிக்கை காலப்போக்கில் வரைகிறது — கேப்ஷரின் போது பாக்கெட்டுகள் மற்றும் ஃபுளோக்கள் எப்படி வளர்ந்தன.",
    },
    targets: [{ label: { en: "Show Capture overview", hi: "कैप्चर ओवरव्यू दिखाओ", kn: "ಕ್ಯಾಪ್ಚರ್ ಅವಲೋಕನ ತೋರಿಸು", ta: "கேப்ஷர் கண்ணோட்டத்தை காட்டு" }, action: "soc", panel: "Capture overview" }],
  },
  {
    id: "recent-detections",
    words: ["recent detections", "detection history", "past detections", "रिसेंट डिटेक्शंस", "इतिहास", "ಇತ್ತೀಚಿನ ಪತ್ತೆಗಳು", "ಇತಿಹಾಸ", "சமீபத்திய கண்டறிதல்கள்", "வரலாறு"],
    answers: {
      en: "Recent detections lists the latest detection records — what was flagged, which detector caught it, and the confidence.",
      hi: "रिसेंट डिटेक्शंस में हाल के डिटेक्शन रिकॉर्ड्स हैं — क्या चिह्नित हुआ, किस डिटेक्टर ने पकड़ा, और आत्मविश्वास।",
      kn: "ಇತ್ತೀಚಿನ ಪತ್ತೆಗಳು ಇತ್ತೀಚಿನ ಪತ್ತೆ ದಾಖಲೆಗಳನ್ನು ಪಟ್ಟಿ ಮಾಡುತ್ತವೆ — ಏನು ಸೂಚಿಸಲ್ಪಟ್ಟಿತು, ಯಾವ ಡಿಟೆಕ್ಟರ್ ಹಿಡಿಯಿತು, ಮತ್ತು ಆತ್ಮವಿಶ್ವಾಸ.",
      ta: "சமீபத்திய கண்டறிதல்கள் சமீபத்திய கண்டறிதல் பதிவுகளை பட்டியலிடும் — எது குறிக்கப்பட்டது, எந்த கண்டறிதல் பிடித்தது, மற்றும் நம்பிக்கை.",
    },
    targets: [{ label: { en: "Show Recent detections", hi: "रिसेंट डिटेक्शंस दिखाओ", kn: "ಇತ್ತೀಚಿನ ಪತ್ತೆಗಳನ್ನು ತೋರಿಸು", ta: "சமீபத்திய கண்டறிதல்களை காட்டு" }, action: "soc", panel: "Recent detections" }],
  },
  {
    id: "session-summary",
    words: ["session summary", "summary", "latest session", "session report", "सेशन समरी", "सारांश", "ಸೆಷನ್ ಸಾರಾಂಶ", "ಸಾರಾಂಶ", "அமர்வு சுருக்கம்", "சுருக்கம்"],
    answers: {
      en: "Session summary appears once a capture finishes: the interface, duration, packet and flow totals, and the detection breakdown for that session.",
      hi: "कैप्चर खत्म होने पर सेशन समरी दिखाई देती है: इंटरफ़ेस, अवधि, पैकेट व फ्लो कुल, और उस सेशन का डिटेक्शन विवरण।",
      kn: "ಕ್ಯಾಪ್ಚರ್ ಮುಗಿದ ನಂತರ ಸೆಷನ್ ಸಾರಾಂಶ ಕಾಣುತ್ತದೆ: ಇಂಟರ್‌ಫೇಸ್, ಅವಧಿ, ಪ್ಯಾಕೆಟ್ ಮತ್ತು ಫ್ಲೋ ಒಟ್ಟುಗಳು, ಮತ್ತು ಆ ಸೆಷನ್‌ನ ಪತ್ತೆ ವಿವರ.",
      ta: "கேப்ஷர் முடிந்ததும் அமர்வு சுருக்கம் தோன்றும்: இடைமுகம், காலம், பாக்கெட் மற்றும் ஃபுளோ மொத்தங்கள், மற்றும் அந்த அமர்வின் கண்டறிதல் விவரம்.",
    },
    targets: [
      { label: { en: "Show Session summary", hi: "सेशन समरी दिखाओ", kn: "ಸೆಷನ್ ಸಾರಾಂಶ ತೋರಿಸು", ta: "அமர்வு சுருக்கத்தை காட்டு" }, action: "soc", panel: "Session summary" },
      { label: { en: "Go to the Reports page", hi: "रिपोर्ट पेज पर जाओ", kn: "ವರದಿ ಪುಟಕ್ಕೆ ಹೋಗಿ", ta: "அறிக்கை பக்கத்திற்கு செல்" }, action: "reports", selector: ".report-panel" },
    ],
  },
  {
    id: "threat-intelligence",
    words: ["threat intelligence", "threat records", "benign records", "benign", "records table", "avg confidence", "detectors loaded", "थ्रेट इंटेलिजेंस", "थ्रेट रिकॉर्ड्स", "बेनाइन", "थ्रेट रिकॉर्ड्स टेबल", "औसत आत्मविश्वास", "ಥ್ರೆಟ್ ಇಂಟೆಲಿಜೆನ್ಸ್", "ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್ಸ್", "ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್", "ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್‌ಗಳು", "ಬೆನೈನ್", "ಕೋಷ್ಟಕ", "ಸರಾಸರಿ ಆತ್ಮವಿಶ್ವಾಸ", "அச்சுறுத்தல் உளவுத் தகவல்", "அச்சுறுத்தல் பதிவுகள்", "நல்ல பதிவுகள்", "அட்டவணை", "சராசரி நம்பிக்கை"],
    answers: {
      en: "Threat Intelligence sits right under the SOC panel strip as one big section.\n\n• Top: the giant THREAT INTELLIGENCE title with Threats and Detectors-loaded counters on the side.\n• Cards row: Threat records, Benign records, Average confidence, Active detectors.\n• Then the detection modules and the threat records table with the latest verdicts.",
      hi: "थ्रेट इंटेलिजेंस SOC पैनल स्ट्रिप के ठीक नीचे एक बड़े सेक्शन के रूप में है।\n\n• ऊपर: बड़ा THREAT INTELLIGENCE शीर्षक, साथ में खतरे व लोडेड डिटेक्टर काउंटर।\n• कार्ड पंक्ति: थ्रेट रिकॉर्ड्स, बेनाइन रिकॉर्ड्स, औसत आत्मविश्वास, सक्रिय डिटेक्टर।\n• फिर डिटेक्शन मॉड्यूल और ताज़ा नतीजों वाली थ्रेट रिकॉर्ड्स टेबल।",
      kn: "ಥ್ರೆಟ್ ಇಂಟೆಲಿಜೆನ್ಸ್ SOC ಪ್ಯಾನೆಲ್ ಸ್ಟ್ರಿಪ್ ಕೆಳಗೆ ಒಂದು ದೊಡ್ಡ ವಿಭಾಗವಾಗಿ ಇದೆ.\n\n• ಮೇಲಿನ: ದೊಡ್ಡ THREAT INTELLIGENCE ಶೀರ್ಷಿಕೆ, ಪಕ್ಕದಲ್ಲಿ ಬೆದರಿಕೆಗಳು ಮತ್ತು ಲೋಡ್ ಆದ ಡಿಟೆಕ್ಟರ್ ಕೌಂಟರ್‌ಗಳು.\n• ಕಾರ್ಡ್ ಸಾಲು: ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್‌ಗಳು, ಬೆನೈನ್ ರೆಕಾರ್ಡ್‌ಗಳು, ಸರಾಸರಿ ಆತ್ಮವಿಶ್ವಾಸ, ಸಕ್ರಿಯ ಡಿಟೆಕ್ಟರ್‌ಗಳು.\n• ನಂತರ ಪತ್ತೆ ಮಾಡ್ಯೂಲ್‌ಗಳು ಮತ್ತು ಇತ್ತೀಚಿನ ಫಲಿತಾಂಶಗಳ ಥ್ರೆಟ್ ರೆಕಾರ್ಡ್‌ಗಳ ಕೋಷ್ಟಕ.",
      ta: "அச்சுறுத்தல் உளவுத் தகவல் SOC பேனல் பட்டையின் கீழ் ஒரு பெரிய பகுதியாக உள்ளது.\n\n• மேலே: பெரிய THREAT INTELLIGENCE தலைப்பு, பக்கத்தில் அச்சுறுத்தல்கள் மற்றும் ஏற்றப்பட்ட கண்டறிதல்கள் எண்ணிக்கைகள்.\n• கார்டு வரிசை: அச்சுறுத்தல் பதிவுகள், நல்ல பதிவுகள், சராசரி நம்பிக்கை, செயலில் உள்ள கண்டறிதல்கள்.\n• பின்னர் கண்டறிதல் தொகுதிகள் மற்றும் சமீபத்திய முடிவுகளுடன் கூடிய அச்சுறுத்தல் பதிவுகள் அட்டவணை.",
    },
    targets: [
      { label: { en: "Show Threat Intelligence section", hi: "थ्रेट इंटेलिजेंस सेक्शन दिखाओ", kn: "ಥ್ರೆಟ್ ಇಂಟೆಲಿಜೆನ್ಸ್ ವಿಭಾಗ ತೋರಿಸು", ta: "அச்சுறுத்தல் உளவுத் தகவல் பகுதியை காட்டு" }, action: "soc", selector: ".ti-section" },
      { label: { en: "Show the TI stat cards", hi: "TI स्टैट कार्ड दिखाओ", kn: "TI ಸ್ಟ್ಯಾಟ್ ಕಾರ್ಡ್‌ಗಳನ್ನು ತೋರಿಸು", ta: "TI புள்ளிவிவர கார்டுகளை காட்டு" }, action: "soc", selector: ".ti-section .stats" },
      { label: { en: "Show the TI records table", hi: "TI रिकॉर्ड्स टेबल दिखाओ", kn: "TI ರೆಕಾರ್ಡ್‌ಗಳ ಕೋಷ್ಟಕ ತೋರಿಸು", ta: "TI பதிவுகள் அட்டவணையை காட்டு" }, action: "soc", selector: ".ti-section .records-panel" },
    ],
    live: "ti",
  },
  {
    id: "capture",
    words: ["capture", "start capture", "stop capture", "interface", "duration", "record traffic", "capture button", "कैप्चर", "इंटरफ़ेस", "अवधि", "कैप्चर बटन", "ಕ್ಯಾಪ್ಚರ್", "ಇಂಟರ್‌ಫೇಸ್", "ಅವಧಿ", "ಕ್ಯಾಪ್ಚರ್ ಬಟನ್", "கேப்ஷர்", "இடைமுகம்", "காலம்", "கேப்ஷர் பட்டன்"],
    answers: {
      en: "To capture traffic:\n\n• Pick an interface and a duration — on the Network tab or in the SOC's Live capture panel.\n• Press Start capture and watch the packet count and flows rise.\n• When it finishes, the session appears in Recent detections, gets a Session summary, and lands in Reports.",
      hi: "ट्रैफ़िक कैप्चर करने के लिए:\n\n• इंटरफ़ेस और अवधि चुनें — नेटवर्क टैब पर या SOC के लाइव कैप्चर पैनल में।\n• स्टार्ट कैप्चर दबाएँ और पैकेट संख्या व फ्लो बढ़ते देखें।\n• खत्म होने पर सेशन रिसेंट डिटेक्शंस में आता है, सेशन समरी मिलती है, और रिपोर्ट में जाता है।",
      kn: "ಟ್ರಾಫಿಕ್ ಕ್ಯಾಪ್ಚರ್ ಮಾಡಲು:\n\n• ಇಂಟರ್‌ಫೇಸ್ ಮತ್ತು ಅವಧಿಯನ್ನು ಆಯ್ಕೆಮಾಡಿ — ನೆಟ್‌ವರ್ಕ್ ಟ್ಯಾಬ್‌ನಲ್ಲಿ ಅಥವಾ SOC ನ ಲೈವ್ ಕ್ಯಾಪ್ಚರ್ ಪ್ಯಾನೆಲ್‌ನಲ್ಲಿ.\n• ಸ್ಟಾರ್ಟ್ ಕ್ಯಾಪ್ಚರ್ ಒತ್ತಿ ಪ್ಯಾಕೆಟ್ ಸಂಖ್ಯೆ ಮತ್ತು ಫ್ಲೋಗಳು ಏರುವುದನ್ನು ನೋಡಿ.\n• ಮುಗಿದ ನಂತರ ಸೆಷನ್ ಇತ್ತೀಚಿನ ಪತ್ತೆಗಳಲ್ಲಿ ಕಾಣುತ್ತದೆ, ಸೆಷನ್ ಸಾರಾಂಶ ಸಿಗುತ್ತದೆ ಮತ್ತು ವರದಿಗಳಲ್ಲಿ ಹೋಗುತ್ತದೆ.",
      ta: "டிராஃபிக்கை கைப்பற்ற:\n\n• இடைமுகம் மற்றும் காலத்தை தேர்வுசெய்யவும் — நெட்வொர்க் அட்டவணையில் அல்லது SOC-வின் நேரடி கேப்ஷர் பேனலில்.\n• ஸ்டார்ட் கேப்ஷரை அழுத்தி பாக்கெட் எண் மற்றும் ஃபுளோக்கள் அதிகரிப்பதை கவனியுங்கள்.\n• முடிந்ததும் அமர்வு சமீபத்திய கண்டறிதல்களில் தோன்றும், அமர்வு சுருக்கம் கிடைக்கும், அறிக்கைகளில் செல்லும்.",
    },
    targets: [
      { label: { en: "Show the capture controls", hi: "कैप्चर कंट्रोल दिखाओ", kn: "ಕ್ಯಾಪ್ಚರ್ ಕಂಟ್ರೋಲ್‌ಗಳನ್ನು ತೋರಿಸು", ta: "கேப்ஷர் கட்டுப்பாடுகளை காட்டு" }, action: "network", selector: ".capture-controls" },
      { label: { en: "Show the capture button", hi: "कैप्चर बटन दिखाओ", kn: "ಕ್ಯಾಪ್ಚರ್ ಬಟನ್ ತೋರಿಸು", ta: "கேப்ஷர் பட்டனை காட்டு" }, action: "network", selector: ".capture-button" },
      { label: { en: "Show Live capture in the SOC", hi: "SOC में लाइव कैप्चर दिखाओ", kn: "SOC ನಲ್ಲಿ ಲೈವ್ ಕ್ಯಾಪ್ಚರ್ ತೋರಿಸು", ta: "SOC-இல் நேரடி கேப்ஷரை காட்டு" }, action: "soc", panel: "Live capture" },
    ],
  },
  {
    id: "network",
    words: ["network page", "network tab", "selected interface", "नेटवर्क पेज", "नेटवर्क टैब", "ನೆಟ್‌ವರ್ಕ್ ಪುಟ", "ನೆಟ್‌ವರ್ಕ್ ಟ್ಯಾಬ್", "நெட்வொர்க் பக்கம்", "நெட்வொர்க் அட்டவணை"],
    answers: {
      en: "The Network tab is the workbench:\n\n• Capture controls up top (interface picker + duration + start button).\n• Live score cards: packets captured, network flows, detectors loaded, database status.\n• The second globe view at the bottom — same Earth, same drag, click, and hover behavior as on Home.",
      hi: "नेटवर्क टैब वर्कबेंच है:\n\n• ऊपर कैप्चर कंट्रोल (इंटरफ़ेस चुनने का खाना + अवधि + स्टार्ट बटन)।\n• लाइव स्कोर कार्ड: कैप्चर पैकेट, नेटवर्क फ्लो, लोडेड डिटेक्टर, डेटाबेस स्थिति।\n• नीचे दूसरा ग्लोब व्यू — वही पृथ्वी, वही ड्रैग, क्लिक और होवर व्यवहार जैसे होम पर।",
      kn: "ನೆಟ್‌ವರ್ಕ್ ಟ್ಯಾಬ್ ವರ್ಕ್‌ಬೆಂಚ್:\n\n• ಮೇಲಿನ ಕ್ಯಾಪ್ಚರ್ ಕಂಟ್ರೋಲ್‌ಗಳು (ಇಂಟರ್‌ಫೇಸ್ ಪಿಕರ್ + ಅವಧಿ + ಸ್ಟಾರ್ಟ್ ಬಟನ್).\n• ಲೈವ್ ಸ್ಕೋರ್ ಕಾರ್ಡ್‌ಗಳು: ಪ್ಯಾಕೆಟ್‌ಗಳು, ನೆಟ್‌ವರ್ಕ್ ಫ್ಲೋಗಳು, ಲೋಡ್ ಆದ ಡಿಟೆಕ್ಟರ್‌ಗಳು, ಡೇಟಾಬೇಸ್ ಸ್ಥಿತಿ.\n• ಕೆಳಗೆ ಎರಡನೇ ಗ್ಲೋಬ್ ವ್ಯೂ — ಹೋಂ ನಲ್ಲಿರುವಂತೆ ಅದೇ ಭೂಮಿ, ಅದೇ ಎಳೆಯುವಿಕೆ, ಕ್ಲಿಕ್ ಮತ್ತು ಹೊವರ್ ನಡವಳಿಕೆ.",
      ta: "நெட்வொர்க் அட்டவணை பணியிடம்:\n\n• மேலே கேப்ஷர் கட்டுப்பாடுகள் (இடைமுக தேர்வி + காலம் + ஸ்டார்ட் பட்டன்).\n• நேரடி ஸ்கோர் கார்டுகள்: பாக்கெட்டுகள், நெட்வொர்க் ஃபுளோக்கள், ஏற்றப்பட்ட கண்டறிதல்கள், தரவுத்தள நிலை.\n• கீழே இரண்டாவது குளோப் — முகப்பில் உள்ள அதே பூமி, அதே இழுப்பு, கிளிக் மற்றும் ஹோவர் நடத்தை.",
    },
    targets: [
      { label: { en: "Show Network stats cards", hi: "नेटवर्क स्टैट्स कार्ड दिखाओ", kn: "ನೆಟ್‌ವರ್ಕ್ ಸ್ಟ್ಯಾಟ್ಸ್ ಕಾರ್ಡ್‌ಗಳನ್ನು ತೋರಿಸು", ta: "நெட்வொர்க் புள்ளிவிவர கார்டுகளை காட்டு" }, action: "network", selector: ".tab-view > .stats" },
      { label: { en: "Show the Network globe", hi: "नेटवर्क ग्लोब दिखाओ", kn: "ನೆಟ್‌ವರ್ಕ್ ಗ್ಲೋಬ್ ತೋರಿಸು", ta: "நெட்வொர்க் குளோப்பை காட்டு" }, action: "network", selector: ".network-map-wrap .globe-map" },
    ],
  },
  {
    id: "reports",
    words: ["reports", "report", "capture session report", "report ready", "export", "रिपोर्ट", "रिपोर्ट पेज", "ವರದಿಗಳು", "ವರದಿ", "அறிக்கைகள்", "அறிக்கை"],
    answers: {
      en: "Reports shows the capture session report — interface, duration, packet and flow counts, and the detection outcome.\n\nIt reads “Report ready” once a capture has completed, otherwise “No capture yet” until you run your first capture.",
      hi: "रिपोर्ट कैप्चर सेशन रिपोर्ट दिखाता है — इंटरफ़ेस, अवधि, पैकेट व फ्लो संख्या, और डिटेक्शन नतीजा।\n\nकैप्चर पूरा होने पर “रिपोर्ट तैयार” दिखता है, वरना पहला कैप्चर चलाने तक “अभी कोई कैप्चर नहीं”।",
      kn: "ವರದಿಗಳು ಕ್ಯಾಪ್ಚರ್ ಸೆಷನ್ ವರದಿಯನ್ನು ತೋರಿಸುತ್ತವೆ — ಇಂಟರ್‌ಫೇಸ್, ಅವಧಿ, ಪ್ಯಾಕೆಟ್ ಮತ್ತು ಫ್ಲೋ ಸಂಖ್ಯೆಗಳು, ಮತ್ತು ಪತ್ತೆ ಫಲಿತಾಂಶ.\n\nಕ್ಯಾಪ್ಚರ್ ಪೂರ್ಣಗೊಂಡರೆ “ವರದಿ ಸಿದ್ಧ” ಎಂದು ತೋರಿಸುತ್ತದೆ, ಇಲ್ಲದಿದ್ದರೆ ಮೊದಲ ಕ್ಯಾಪ್ಚರ್ ನಡೆಸುವವರೆಗೆ “ಇನ್ನೂ ಕ್ಯಾಪ್ಚರ್ ಇಲ್ಲ”.",
      ta: "அறிக்கைகள் கேப்ஷர் அமர்வு அறிக்கையை காட்டும் — இடைமுகம், காலம், பாக்கெட் மற்றும் ஃபுளோ எண்ணிக்கைகள், மற்றும் கண்டறிதல் முடிவு.\n\nகேப்ஷர் முடிந்தால் “அறிக்கை தயார்” என்று காட்டும், இல்லையேல் முதல் கேப்ஷர் இயக்கும் வரை “இன்னும் கேப்ஷர் இல்லை”.",
    },
    targets: [
      { label: { en: "Go to Reports", hi: "रिपोर्ट पर जाओ", kn: "ವರದಿಗಳಿಗೆ ಹೋಗಿ", ta: "அறிக்கைகளுக்கு செல்" }, action: "reports" },
      { label: { en: "Show the report panel", hi: "रिपोर्ट पैनल दिखाओ", kn: "ವರದಿ ಪ್ಯಾನೆಲ್ ತೋರಿಸು", ta: "அறிக்கை பேனலை காட்டு" }, action: "reports", selector: ".report-panel" },
      { label: { en: "Show the report cells", hi: "रिपोर्ट सेल दिखाओ", kn: "ವರದಿ ಸೆಲ್‌ಗಳನ್ನು ತೋರಿಸು", ta: "அறிக்கை செல்களை காட்டு" }, action: "reports", selector: ".report-grid" },
    ],
  },
  {
    id: "backend",
    words: ["backend offline", "offline", "database", "unknown", "not running", "cannot connect", "connection", "status", "connected", "online", "बैकएंड ऑफ़लाइन", "ऑफ़लाइन", "डेटाबेस", "अज्ञात", "नहीं चल रहा", "स्थिति", "जुड़ा", "ऑनलाइन", "ಬ್ಯಾಕೆಂಡ್ ಆಫ್‌ಲೈನ್", "ಆಫ್‌ಲೈನ್", "ಡೇಟಾಬೇಸ್", "ಅಜ್ಞಾತ", "ಸ್ಥಿತಿ", "ಸಂಪರ್ಕ", "ಪೇಗೆಂಡ್ ಆஃப்லைன்", "ஆஃப்லைன்", "தரவுத்தளம்", "தெரியவில்லை", "நிலை", "இணைப்பு", "ஆன்லைன்"],
    answers: {
      en: "Two live status lights tell you the health of the system:\n\n• Top-right: the backend status dot — green “SYSTEM ONLINE”, or red “BACKEND OFFLINE” when the local service isn't running.\n• Footer right: the database status — “CONNECTED” or “UNKNOWN”.\n\nWhile offline, the dashboard still works for exploring; you'll just see empty stats and dashes until the service is started.",
      hi: "दो लाइव स्थिति लाइट सिस्टम की सेहत बताती हैं:\n\n• ऊपर दाईं ओर: बैकएंड स्थिति डॉट — हरा “SYSTEM ONLINE”, या लाल “BACKEND OFFLINE” जब लोकल सेवा चालू नहीं है।\n• फुटर दाईं ओर: डेटाबेस स्थिति — “CONNECTED” या “UNKNOWN”।\n\nऑफ़लाइन रहते भी डैशबोर्ड घुमाने के लिए चलता है; सेवा चालू होने तक खाली स्टैट्स व डैश दिखेंगे।",
      kn: "ಎರಡು ಲೈವ್ ಸ್ಥಿತಿ ದೀಪಗಳು ವ್ಯವಸ್ಥೆಯ ಆರೋಗ್ಯವನ್ನು ತೋರಿಸುತ್ತವೆ:\n\n• ಮೇಲು ಬಲಭಾಗ: ಬ್ಯಾಕೆಂಡ್ ಸ್ಥಿತಿ ಚುಕ್ಕೆ — ಹಸಿರು “SYSTEM ONLINE”, ಅಥವಾ ಸ್ಥಳೀಯ ಸೇವೆ ಚಾಲನೆಯಲ್ಲಿಲ್ಲದಿದ್ದರೆ ಕೆಂಪು “BACKEND OFFLINE”.\n• ಫೂಟರ್ ಬಲಭಾಗ: ಡೇಟಾಬೇಸ್ ಸ್ಥಿತಿ — “CONNECTED” ಅಥವಾ “UNKNOWN”.\n\nಆಫ್‌ಲೈನ್‌ನಲ್ಲಿದ್ದರೂ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ ಅನ್ವೇಷಣೆಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ; ಸೇವೆ ಪ್ರಾರಂಭವಾಗುವವರೆಗೆ ಖಾಲಿ ಸ್ಟ್ಯಾಟ್ಸ್ ಮತ್ತು ಡ್ಯಾಶ್‌ಗಳು ಕಾಣುತ್ತವೆ.",
      ta: "இரண்டு நேரடி நிலை விளக்குகள் கணினியின் ஆரோக்கியத்தை காட்டும்:\n\n• மேல் வலது: பேக்எண்ட் நிலை புள்ளி — பச்சை “SYSTEM ONLINE”, அல்லது உள்ளூர் சேவை இயங்கவில்லை எனில் சிவப்பு “BACKEND OFFLINE”.\n• அடிக்குறிப்பு வலது: தரவுத்தள நிலை — “CONNECTED” அல்லது “UNKNOWN”.\n\nஆஃப்லைனில் இருந்தாலும் டாஷ்போர்டு ஆராய பயன்படும்; சேவை தொடங்கும் வரை காலி புள்ளிவிவரங்கள் மற்றும் கோடுகள் தோன்றும்.",
    },
    targets: [
      { label: { en: "Show the backend status", hi: "बैकएंड स्थिति दिखाओ", kn: "ಬ್ಯಾಕೆಂಡ್ ಸ್ಥಿತಿ ತೋರಿಸು", ta: "பேக்எண்ட் நிலையை காட்டு" }, selector: ".online" },
      { label: { en: "Show the database status", hi: "डेटाबेस स्थिति दिखाओ", kn: "ಡೇಟಾಬೇಸ್ ಸ್ಥಿತಿ ತೋರಿಸು", ta: "தரவுத்தள நிலையை காட்டு" }, selector: ".footer" },
    ],
    live: "status",
  },
  {
    id: "footer",
    words: ["footer", "bottom bar", "status bar", "pinned bar", "credit", "sachin", "फ़ुटर", "नीचे की बार", "स्थिति बार", "क्रेडिट", "फ़ೂಟರ್", "ಕೆಳಗಿನ ಬಾರ್", "ಸ್ಥಿತಿ ಬಾರ್", "ಕ್ರೆಡಿಟ್", "அடிக்குறிப்பு", "கீழ் பட்டை", "நிலை பட்டை", "கிரெடிட்"],
    answers: {
      en: "The pinned bar at the very bottom is the status bar — it never scrolls away and looks the same on every page.\n\nLeft: the CYVORA network monitoring label. Right: the live database status. The glowing badge in the middle is the credit line.",
      hi: "सबसे नीचे पिन की गई बार स्टेटस बार है — यह कभी नहीं हटती और हर पेज पर एक जैसी दिखती है।\n\nबाईं ओर: CYVORA नेटवर्क निगरानी लेबल। दाईं ओर: लाइव डेटाबेस स्थिति। बीच में चमकता बैज क्रेडिट लाइन है।",
      kn: "ಅತ್ಯಂತ ಕೆಳಗಿರವ ಪಿನ್ ಮಾಡಿದ ಬಾರ್ ಸ್ಥಿತಿ ಬಾರ್ — ಇದು ಎಂದಿಗೂ ಸ್ಕ್ರಾಲ್ ಆಗುವುದಿಲ್ಲ ಮತ್ತು ಪ್ರತಿ ಪುಟದಲ್ಲಿ ಒಂದೇ ರೀತಿ ಕಾಣುತ್ತದೆ.\n\nಎಡಭಾಗ: CYVORA ನೆಟ್‌ವರ್ಕ್ ಮೇಲ್ವಿಚಾರಣಾ ಲೇಬಲ್. ಬಲಭಾಗ: ಲೈವ್ ಡೇಟಾಬೇಸ್ ಸ್ಥಿತಿ. ಮಧ್ಯದ ಹೊಳೆಯುವ ಬ್ಯಾಡ್ಜ್ ಕ್ರೆಡಿಟ್ ಲೈನ್.",
      ta: "மிக கீழே உள்ள பின் செய்யப்பட்ட பட்டை நிலை பட்டை — இது ஒருபோதும் ஸ்க்ரோல் ஆகாது, ஒவ்வொரு பக்கத்திலும் ஒரே மாதிரி தோன்றும்.\n\nஇடது: CYVORA நெட்வொர்க் கண்காணிப்பு லேபிள். வலது: நேரடி தரவுத்தள நிலை. நடுவில் உள்ள ஒளிரும் பேட்ஜ் கிரெடிட் வரி.",
    },
    targets: [
      { label: { en: "Show the footer bar", hi: "फ़ुटर बार दिखाओ", kn: "ಫೂಟರ್ ಬಾರ್ ತೋರಿಸು", ta: "அடிக்குறிப்பு பட்டையை காட்டு" }, selector: ".footer" },
      { label: { en: "Show the credit badge", hi: "क्रेडिट बैज दिखाओ", kn: "ಕ್ರೆಡಿಟ್ ಬ್ಯಾಡ್ಜ್ ತೋರಿಸು", ta: "கிரெடிட் பேட்ஜை காட்டு" }, selector: ".footer-credit" },
    ],
  },
];

// Read the live box values currently on screen, so answers can quote them.
function readScores() {
  const stats = [...document.querySelectorAll(".stats .stat")].map((card) => ({
    label: card.querySelector(".stat-top span")?.textContent?.trim(),
    value: card.querySelector("strong")?.textContent?.trim(),
  }));
  const tiMeta = [...document.querySelectorAll(".ti-meta-item")].map((item) => ({
    label: item.querySelector("span")?.textContent?.trim(),
    value: item.querySelector("strong")?.textContent?.trim(),
  }));
  const backend = document.querySelector(".online")?.textContent?.replace(/\s+/g, " ").trim();
  const database = document.querySelector(".footer-row span:last-child")?.textContent?.trim();
  return { stats, tiMeta, backend, database };
}

function scoreText(stats) {
  // The same card can appear in two places (SOC strip + TI section): one line per label.
  const byLabel = new Map();
  stats.forEach((stat) => {
    if (stat.label && stat.value && !byLabel.has(stat.label)) byLabel.set(stat.label, stat.value);
  });
  return [...byLabel.entries()].map(([label, value]) => `${label}: ${value}`).join("\n");
}

function findAnswer(text) {
  // Keep Hindi, Kannada and Tamil words intact while matching: letters,
  // combining marks (vowel signs) and numbers all survive the cleanup.
  const normalized = ` ${text.toLowerCase().replace(/[^\p{L}\p{M}\p{N}\s]/gu, " ")} `;
  let best = null;
  let bestScore = 0;

  KNOWLEDGE.forEach((entry) => {
    // Longer phrases weigh more, so "capture overview" beats plain "capture".
    const score = entry.words.reduce((total, word) => {
      return total + (normalized.includes(` ${word} `) || normalized.includes(word) ? word.length : 0);
    }, 0);
    if (score > bestScore) {
      best = entry;
      bestScore = score;
    }
  });

  return best;
}

// Scroll the page to a box and pulse a glow around it so the user sees it.
function highlight(element) {
  if (!element) return;
  document.querySelectorAll(".bot-locate").forEach((node) => node.classList.remove("bot-locate"));
  element.classList.add("bot-locate");
  element.scrollIntoView({ behavior: "smooth", block: "center" });
  window.setTimeout(() => element.classList.remove("bot-locate"), 3000);
}

function locateTarget(target) {
  if (target.panel) {
    const label = [...document.querySelectorAll(".soc-panel-label")].find(
      (node) => node.textContent.trim() === target.panel
    );
    const panel = label?.closest(".soc-panel");
    if (panel) {
      // Focusing the tab widens the strip panel so its contents are visible.
      panel.focus({ preventScroll: true });
      highlight(panel);
      return;
    }
  }
  if (target.selector) {
    highlight(document.querySelector(target.selector));
  }
}

let messageId = 0;
const nextId = () => {
  messageId += 1;
  return messageId;
};

export default function AssistantBot({ onAction }) {
  const [open, setOpen] = useState(false);
  const [lang, setLang] = useState(() => {
    try {
      const saved = window.localStorage?.getItem("cyvora-assistant-lang");
      return saved && LANGUAGES.some((item) => item.id === saved) ? saved : "en";
    } catch {
      return "en";
    }
  });
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [messages, setMessages] = useState([
    { id: nextId(), from: "bot", text: UI_TEXT[lang]?.greeting || UI_TEXT.en.greeting },
  ]);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const langRef = useRef(lang);

  useEffect(() => {
    langRef.current = lang;
  }, [lang]);

  const text = LANG_FALLBACK(UI_TEXT[lang]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, typing, open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const reply = (inputText) => {
    setTyping(true);
    window.setTimeout(() => {
      const entry = findAnswer(inputText);
      const ui = LANG_FALLBACK(UI_TEXT[langRef.current]) || UI_TEXT.en;
      setTyping(false);
      let answer = entry?.answers?.[langRef.current] || entry?.answers?.en;
      if (entry?.live === "stats") {
        const stats = scoreText(readScores().stats);
        if (stats) answer += `\n\n${ui.liveNumbers(stats)}`;
      } else if (entry?.live === "ti") {
        const { tiMeta } = readScores();
        const meta = scoreText(tiMeta);
        if (meta) answer += `\n\n${ui.liveNumbers(meta)}`;
      } else if (entry?.live === "status") {
        const { backend, database } = readScores();
        const status = [backend && `Backend: ${backend}`, database && `Database: ${database}`].filter(Boolean).join("\n");
        if (status) answer += `\n\n${status}`;
      }
      setMessages((value) => [
        ...value,
        {
          id: nextId(),
          from: "bot",
          text: answer || ui.fallback,
          targets: entry?.targets,
        },
      ]);
    }, 650);
  };

  const send = (inputText) => {
    const trimmed = inputText.trim();
    if (!trimmed || typing) return;
    setMessages((value) => [...value, { id: nextId(), from: "user", text: trimmed }]);
    setInput("");
    reply(trimmed);
  };

  const setLanguage = (next) => {
    setLang(next);
    try {
      window.localStorage?.setItem("cyvora-assistant-lang", next);
    } catch {
      /* storage unavailable; language still applies for this session */
    }
    setMessages((value) => [
      ...value,
      { id: nextId(), from: "bot", text: LANG_FALLBACK(UI_TEXT[next])?.langChanged || UI_TEXT.en.langChanged },
    ]);
    if (open) inputRef.current?.focus();
  };

  const goTo = (target) => {
    if (target.action) onAction?.(target.action);
    const page = target.action ? PAGE_NAMES[target.action]?.[lang] || PAGE_NAMES[target.action]?.en : null;
    const ui = LANG_FALLBACK(UI_TEXT[lang]) || UI_TEXT.en;
    if (page) {
      setMessages((value) => [
        ...value,
        { id: nextId(), from: "bot", text: ui.takingYou(page) },
      ]);
    }
    // Let the page mount (and the SOC strip animate) before locating the box.
    window.setTimeout(() => {
      locateTarget(target);
      // Once there, read the real numbers off the box we landed on.
      const { stats, tiMeta } = readScores();

      const lines = scoreText([...stats, ...tiMeta]);
      if (lines) {
        setMessages((value) => [
          ...value,
          { id: nextId(), from: "bot", text: ui.liveNumbers(lines) },
        ]);
      }
    }, target.action ? 950 : 450);
  };

  return (
    <>
      <div className={`assistant-panel ${open ? "" : "assistant-panel--closed"}`} role="dialog" aria-label="CYVORA assistant">
        <div className="assistant-header">
          <span className="assistant-avatar">
            <Bot size={17} />
          </span>
          <span className="assistant-title">
            <strong>CYVORA Assistant</strong>
            <small>{text?.subtitle}</small>
          </span>
          <span className="assistant-languages" role="group" aria-label="Assistant language">
            {LANGUAGES.map((item) => (
              <button
                key={item.id}
                type="button"
                title={item.name}
                aria-label={`Switch assistant to ${item.name}`}
                aria-pressed={lang === item.id}
                className={lang === item.id ? "active" : ""}
                onClick={() => setLanguage(item.id)}
              >
                {item.label}
              </button>
            ))}
          </span>
          <button type="button" className="assistant-close" aria-label="Close assistant" onClick={() => setOpen(false)}>
            <X size={14} />
          </button>
        </div>

        <div className="assistant-messages" ref={scrollRef}>
          {messages.map((message) => (
            <div key={message.id} className={`assistant-message assistant-message--${message.from}`}>
              <p>{message.text}</p>
              {message.targets?.length > 0 && (
                <span className="assistant-actions">
                  {message.targets.map((target) => (
                    <button key={target.label.en} type="button" className="assistant-action" onClick={() => goTo(target)}>
                      {target.label[lang] || target.label.en}
                    </button>
                  ))}
                </span>
              )}
            </div>
          ))}
          {typing && (
            <div className="assistant-message assistant-message--bot">
              <span className="assistant-typing" aria-label="Assistant is typing">
                <i />
                <i />
                <i />
              </span>
            </div>
          )}
        </div>

        <div className="assistant-chips">
          {(text?.chips || UI_TEXT.en.chips).map((question) => (
            <button key={question} type="button" onClick={() => send(question)}>
              {question}
            </button>
          ))}
        </div>

        <form
          className="assistant-input-row"
          onSubmit={(event) => {
            event.preventDefault();
            send(input);
          }}
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={text?.placeholder}
            aria-label="Ask the assistant"
          />
          <button type="submit" aria-label="Send message">
            <Send size={14} />
          </button>
        </form>
      </div>

      <button
        type="button"
        className={`assistant-toggle ${open ? "assistant-toggle--open" : ""}`}
        aria-label={open ? "Close assistant" : "Open assistant"}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? <X size={20} /> : <Bot size={22} />}
      </button>
    </>
  );
}
