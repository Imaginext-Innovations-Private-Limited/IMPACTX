/**
 * FasalSaarathi Interactive Application Logic
 * Voice-First Multilingual Speech Recognition & Synthesis,
 * Leaf Health Doctor, Live Agro Tools, and Terrace & Beginner Farming Studio.
 */

document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentLang = "kn";
    let isTTSActive = true;
    let recognition = null;
    let isRecording = false;

    // Elements - Main Advisor
    const langSelect = document.getElementById("langSelect");
    const ttsToggleBtn = document.getElementById("ttsToggleBtn");
    const ttsIcon = document.getElementById("ttsIcon");
    const ttsLabel = document.getElementById("ttsLabel");
    const micBtn = document.getElementById("micBtn");
    const micIcon = document.getElementById("micIcon");
    const voiceStatus = document.getElementById("voiceStatus");
    const voiceStatusText = document.getElementById("voiceStatusText");
    const detectedLangTag = document.getElementById("detectedLangTag");
    const queryInput = document.getElementById("queryInput");
    const sendBtn = document.getElementById("sendBtn");
    const chatMessages = document.getElementById("chatMessages");
    const clearChatBtn = document.getElementById("clearChatBtn");

    let currentAudioPlayer = null;

    // Initialize Language Selection
    currentLang = langSelect ? langSelect.value : "en";

    if (langSelect) {
        langSelect.addEventListener("change", (e) => {
            currentLang = e.target.value;
            updateLanguagePlaceholder(currentLang);
        });
    }

    let lastWeatherData = null;
    let lastSoilData = null;
    let lastMandiData = null;
    let lastDiseaseSample = null;
    let lastUploadedLeafFile = null;
    let lastDiseaseData = null;
    let lastTerracePlanParams = null;
    let lastTerracePlanData = null;
    let lastTerraceGuideCrop = null;
    let lastTerraceGuideData = null;

    const TERRACE_I18N = {
        en: {
            navLabel: "Terrace & Learn",
            heroTag: "Urban Rooftop, Balcony & Beginner Farming",
            planTitle: "Smart Terrace & Balcony Setup Planner",
            planSubtitle: "Recommends the best crops, simple 10L bucket soil mix, and today's watering from your space, sunlight & live city weather.",
            presetLabel: "Quick Space Sizes:",
            locLabel: "City, Town, Village or PIN",
            locPh: "Enter city, town or PIN...",
            lenLabel: "Length (ft)",
            widLabel: "Width (ft)",
            sunLabel: "Direct Sun (hrs/day)",
            spaceLabel: "Space Type",
            goalLabel: "What do you want to grow?",
            calcBtn: "Calculate My Terrace Plan",
            planPrompt: "Enter your city/PIN (or tap 📍 GPS) and your balcony/terrace length, width, and sunlight hours (or tap a Quick Space Size above) to compute your exact setup.",
            coachTitle: "🌱 Seed-to-Harvest Beginner Farming Coach",
            coachSubtitle: "Zero farming experience needed! Tap a starter crop or type any plant for simple day-by-day home growing steps with voice audio.",
            customPh: "Or type any plant to learn (e.g. Ginger, Tulsi, Cucumber, Garlic, Microgreens)...",
            learnBtn: "Show Growing Guide",
            coachPrompt: "Tap any starter crop pill above (e.g. Methi, Coriander, Tomato, Mint) or type a plant name to see simple step-by-step growing instructions.",
            bagLayout: "Grow-Bag Layout",
            totalArea: "Total Space",
            growZone: "60% Grow Zone (40% walk path)",
            totalBags: "Total Grow Bags",
            roofSafety: "Roof Slab Weight Safety",
            lightMix: "Lightweight Mix (Wet)",
            plainMud: "Plain Mud Would Weigh",
            savedWt: "Roof Weight Saved",
            slabSafe: "Safe for Roof Slab",
            bucketMix: "DIY Potting Mix (10L Buckets)",
            cocopeat: "Cocopeat",
            compost: "Compost",
            redSoil: "Red Soil",
            neemCake: "Neem Powder",
            bucketsUnit: "buckets",
            blocksUnit: "blocks",
            waterToday: "Today's Watering (12×12 Bag)",
            mugsUnit: "mugs",
            bestCrops: "Best Crops for Your Sunlight & Today's Weather",
            learnHowBtn: "Seed-to-Harvest Guide →",
            potNeeded: "Pot / Grow Bag",
            sunNeeded: "Daily Sunlight",
            firstHarvest: "First Harvest",
            stepsHeading: "Step-by-Step Growing Guide",
            boosterHeading: "Homemade Kitchen Booster",
            mistakesHeading: "Beginner Mistakes to Avoid",
            weatherTipHeading: "Today's Local Weather Tip",
            listenGuide: "Listen to Full Guide",
            aiCoachBadge: "Online AI Coach",
            offlineCoachBadge: "Offline Starter Guide"
        },
        kn: {
            navLabel: "ತಾರಸಿ ಕೃಷಿ & ಕಲಿಕೆ",
            heroTag: "ಮನೆ ತಾರಸಿ (Terrace), ಬಾಲ್ಕನಿ ಮತ್ತು ಹೊಸಬರ ಕೃಷಿ ಮಾರ್ಗದರ್ಶಿ",
            planTitle: "ಸ್ಮಾರ್ಟ್ ತಾರಸಿ ಮತ್ತು ಬಾಲ್ಕನಿ ತೋಟದ ಯೋಜಕ",
            planSubtitle: "ನಿಮ್ಮ ಜಾಗದ ಅಳತೆ, ಬಿಸಿಲು ಮತ್ತು ನೇರ ಹವಾಮಾನದ ಆಧಾರದ ಮೇಲೆ ಸೂಕ್ತ ಬೆಳೆಗಳು, 10L ಬಕೆಟ್ ಮಣ್ಣಿನ ಮಿಶ್ರಣ ಮತ್ತು ಇಂದಿನ ನೀರಿನ ಪ್ರಮಾಣವನ್ನು ತೋರಿಸುತ್ತದೆ.",
            presetLabel: "ತ್ವರಿತ ಜಾಗದ ಅಳತೆಗಳು:",
            locLabel: "ನಗರ, ಪಟ್ಟಣ, ಗ್ರಾಮ ಅಥವಾ PIN",
            locPh: "ನಗರ, ಗ್ರಾಮ ಅಥವಾ PIN ನಮೂದಿಸಿ...",
            lenLabel: "ಉದ್ದ (ಅಡಿ / ft)",
            widLabel: "ಅಗಲ (ಅಡಿ / ft)",
            sunLabel: "ನೇರ ಬಿಸಿಲು (ಗಂಟೆ/ದಿನ)",
            spaceLabel: "ಜಾಗದ ವಿಧ",
            goalLabel: "ನೀವು ಏನು ಬೆಳೆಯಲು ಬಯಸುತ್ತೀರಿ?",
            calcBtn: "ನನ್ನ ತಾರಸಿ ಯೋಜನೆ ಲೆಕ್ಕಹಾಕಿ",
            planPrompt: "ನಿಮ್ಮ ನಗರ/PIN (ಅಥವಾ 📍 GPS) ಹಾಗೂ ತಾರಸಿ/ಬಾಲ್ಕನಿ ಉದ್ದ, ಅಗಲ ಮತ್ತು ಬಿಸಿಲಿನ ಗಂಟೆಗಳನ್ನು ನಮೂದಿಸಿ (ಅಥವಾ ಮೇಲಿನ ಜಾಗದ ಅಳತೆ ಆಯ್ಕೆಮಾಡಿ).",
            coachTitle: "🌱 ಬೀಜದಿಂದ ಕೊಯ್ಲಿನವರೆಗೆ — ಹೊಸಬರ ಕೃಷಿ ಗುರು",
            coachSubtitle: "ಯಾವುದೇ ಕೃಷಿ ಅನುಭವ ಬೇಕಿಲ್ಲ! ಮನೆಯಲ್ಲಿ ಸುಲಭವಾಗಿ ಬೆಳೆಯುವ ಹಂತ-ಹಂತದ ಮಾಹಿತಿ ಮತ್ತು ಧ್ವನಿ ಸಲಹೆಗಾಗಿ ಮೇಲಿನ ಬೆಳೆ ಒತ್ತಿ.",
            customPh: "ಅಥವಾ ಯಾವುದೇ ಗಿಡದ ಹೆಸರು ಬರೆಯಿರಿ (ಉದಾ: ಶುಂಠಿ, ತುಳಸಿ, ಸೌತೆಕಾಯಿ, ಬೆಳ್ಳುಳ್ಳಿ)...",
            learnBtn: "ಬೆಳೆಯುವ ವಿಧಾನ ತೋರಿಸಿ",
            coachPrompt: "ಸರಳ ಹಂತ-ಹಂತದ ಮಾರ್ಗದರ್ಶನಕ್ಕಾಗಿ ಮೇಲಿನ ಯಾವುದೇ ಬೆಳೆಯನ್ನು ಒತ್ತಿ (ಉದಾ: ಮೆಂತ್ಯ, ಕೊತ್ತಂಬರಿ, ಟೊಮೆಟೊ, ಪುದೀನಾ).",
            bagLayout: "ಗ್ರೋ-ಬ್ಯಾಗ್ ವಿನ್ಯಾಸ",
            totalArea: "ಒಟ್ಟು ಜಾಗ",
            growZone: "60% ಗಿಡದ ಜಾಗ (40% ಓಡಾಟಕ್ಕೆ)",
            totalBags: "ಒಟ್ಟು ಗ್ರೋ-ಬ್ಯಾಗ್‌ಗಳು",
            roofSafety: "ತಾರಸಿ ತೂಕ ಸುರಕ್ಷತೆ",
            lightMix: "ಹಗುರ ಮಿಶ್ರಣ ತೂಕ (ಒದ್ದೆ)",
            plainMud: "ಸಾಮಾನ್ಯ ಮಣ್ಣಿನ ತೂಕ",
            savedWt: "ತಾರಸಿ ಮೇಲಿನ ತೂಕ ಉಳಿತಾಯ",
            slabSafe: "ತಾರಸಿಗೆ ಸಂಪೂರ್ಣ ಸುರಕ್ಷಿತ",
            bucketMix: "ಮಣ್ಣಿನ ಮಿಶ್ರಣ (10L ಬಕೆಟ್ ಲೆಕ್ಕದಲ್ಲಿ)",
            cocopeat: "ಕೊಕೊಪೀಟ್",
            compost: "ಗೊಬ್ಬರ",
            redSoil: "ಕೆಂಪು ಮಣ್ಣು",
            neemCake: "ಬೇವಿನ ಹಿಂಡಿ",
            bucketsUnit: "ಬಕೆಟ್",
            blocksUnit: "ಬ್ಲಾಕ್",
            waterToday: "ಇಂದಿನ ನೀರಿನ ಅಳತೆ (12×12 ಬ್ಯಾಗ್)",
            mugsUnit: "ಮಗ್",
            bestCrops: "ನಿಮ್ಮ ಬಿಸಿಲು ಮತ್ತು ಇಂದಿನ ಹವಾಮಾನಕ್ಕೆ ಸೂಕ್ತ ಬೆಳೆಗಳು",
            learnHowBtn: "ಬೆಳೆಯುವ ವಿಧಾನ ನೋಡಿ →",
            potNeeded: "ಗ್ರೋ-ಬ್ಯಾಗ್ ಗಾತ್ರ",
            sunNeeded: "ದಿನದ ಬಿಸಿಲು",
            firstHarvest: "ಮೊದಲ ಕೊಯ್ಲು",
            stepsHeading: "ಬೀಜದಿಂದ ಕೊಯ್ಲಿನವರೆಗೆ ಸರಳ ಹಂತಗಳು",
            boosterHeading: "ಮನೆಯಲ್ಲೇ ಮಾಡಬಹುದಾದ ಪೋಷಕಾಂಶ",
            mistakesHeading: "ಹೊಸಬರು ತಪ್ಪಿಸಬೇಕಾದ ತಪ್ಪುಗಳು",
            weatherTipHeading: "ಇಂದಿನ ಸ್ಥಳೀಯ ಹವಾಮಾನ ಸಲಹೆ",
            listenGuide: "ಪೂರ್ಣ ಮಾಹಿತಿ ಕೇಳಿ",
            aiCoachBadge: "ಆನ್‌ಲೈನ್ AI ಗುರು",
            offlineCoachBadge: "ಆಫ್‌ಲೈನ್ ಮಾರ್ಗದರ್ಶಿ"
        },
        hi: {
            navLabel: "छत खेती व सीखें",
            heroTag: "छत (Terrace), बालकनी और शुरुआती बागवानी गाइड",
            planTitle: "स्मार्ट छत व बालकनी गार्डन प्लानर",
            planSubtitle: "आपकी जगह, धूप और लाइव मौसम के आधार पर सही पौधे, 10L बाल्टी मिट्टी मिश्रण और आज का पानी हिसाब दिखाता है।",
            presetLabel: "त्वरित जगह आकार:",
            locLabel: "शहर, कस्बा, गांव या पिन कोड",
            locPh: "शहर, गांव या पिन लिखें...",
            lenLabel: "लंबाई (फीट)",
            widLabel: "चौड़ाई (फीट)",
            sunLabel: "सीधी धूप (घंटे/दिन)",
            spaceLabel: "जगह का प्रकार",
            goalLabel: "आप क्या उगाना चाहते हैं?",
            calcBtn: "मेरा टेरेस प्लान बनाएं",
            planPrompt: "अपना शहर/पिन (या 📍 GPS) और छत/बालकनी की लंबाई, चौड़ाई व धूप के घंटे दर्ज करें (या ऊपर से आकार चुनें)।",
            coachTitle: "🌱 बीज से कटाई तक — शुरुआती खेती कोच",
            coachSubtitle: "खेती के अनुभव की जरूरत नहीं! आसान कदम-दर-कदम घरेलू बागवानी सीखने और ऑडियो सुनने के लिए कोई पौधा चुनें।",
            customPh: "या कोई भी पौधा लिखें (जैसे: अदरक, तुलसी, खीरा, लहसुन)...",
            learnBtn: "उगाने की विधि देखें",
            coachPrompt: "आसान गाइड देखने के लिए ऊपर किसी भी फसल पर टैप करें (जैसे: मेथी, धनिया, टमाटर, पुदीना)।",
            bagLayout: "ग्रो-बैग लेआउट",
            totalArea: "कुल जगह",
            growZone: "60% पौधा क्षेत्र (40% चलने का रास्ता)",
            totalBags: "कुल ग्रो-बैग",
            roofSafety: "छत वजन सुरक्षा जांच",
            lightMix: "हल्की मिट्टी वजन (गीला)",
            plainMud: "सादी मिट्टी का वजन",
            savedWt: "छत पर बचाया गया वजन",
            slabSafe: "छत के लिए पूरी तरह सुरक्षित",
            bucketMix: "पॉटिंग मिट्टी रेसिपी (10L बाल्टी में)",
            cocopeat: "कोकोपीट",
            compost: "खाद / वर्मीकम्पोस्ट",
            redSoil: "लाल/बगीचा मिट्टी",
            neemCake: "नीम खली",
            bucketsUnit: "बाल्टी",
            blocksUnit: "ब्लॉक",
            waterToday: "आज का पानी (प्रति 12×12 बैग)",
            mugsUnit: "मग",
            bestCrops: "आपकी धूप और आज के मौसम के लिए सर्वोत्तम पौधे",
            learnHowBtn: "उगाना सीखें →",
            potNeeded: "ग्रो-बैग आकार",
            sunNeeded: "रोज़ की धूप",
            firstHarvest: "पहली तुड़ाई",
            stepsHeading: "बीज से कटाई तक आसान कदम",
            boosterHeading: "घरेलू रसोई पोषण (बूस्टर)",
            mistakesHeading: "शुरुआती गलतियां जिनसे बचें",
            weatherTipHeading: "आज के मौसम की सलाह",
            listenGuide: "पूरी गाइड सुनें",
            aiCoachBadge: "ऑनलाइन AI कोच",
            offlineCoachBadge: "ऑफ़लाइन गाइड"
        },
        ta: {
            navLabel: "மாடித் தோட்டம்",
            heroTag: "மாடித் தோட்டம், பால்கனி & புதியவர்கள் வழிகாட்டி",
            planTitle: "ஸ்மார்ட் மாடி & பால்கனி தோட்டத் திட்டமிடல்",
            planSubtitle: "உங்கள் இடம், வெயில் மற்றும் நேரடி வானிலை மூலம் சிறந்த பயிர்கள், 10L வாளி மண் கலவை மற்றும் இன்றைய தண்ணீர் அளவைக் காட்டுகிறது.",
            presetLabel: "விரைவு இட அளவுகள்:",
            locLabel: "நகரம், ஊர் அல்லது PIN",
            locPh: "நகரம் அல்லது PIN உள்ளிடவும்...",
            lenLabel: "நீளம் (அடி)",
            widLabel: "அகலம் (அடி)",
            sunLabel: "நேரடி வெயில் (மணி/நாள்)",
            spaceLabel: "இட வகை",
            goalLabel: "என்ன வளர்க்க விரும்புகிறீர்கள்?",
            calcBtn: "மாடித் திட்டத்தைக் கணக்கிடு",
            planPrompt: "உங்கள் ஊர்/PIN (அல்லது 📍 GPS) மற்றும் நீளம், அகலம், வெயில் மணிநேரத்தை உள்ளிடவும்.",
            coachTitle: "🌱 விதை முதல் அறுவடை வரை — ஆரம்ப வழிகாட்டி",
            coachSubtitle: "முன் அனுபவம் தேவையில்லை! வீட்டிலேயே எளிய முறையில் செடி வளர்க்க மேலே உள்ள பயிரைத் தொடவும்.",
            customPh: "அல்லது செடியின் பெயரை எழுதவும் (எ.கா: இஞ்சி, துளசி, வெள்ளரி)...",
            learnBtn: "வளர்ப்பு முறை பார்",
            coachPrompt: "எளிய படிப்படியான வழிகாட்டிக்கு மேலே உள்ள பயிரைத் தேர்ந்தெடுக்கவும்.",
            bagLayout: "குரோ-பேக் அமைப்பு",
            totalArea: "மொத்த இடம்",
            growZone: "60% செடி இடம் (40% நடைபாதை)",
            totalBags: "மொத்த பைகள்",
            roofSafety: "மாடி எடை பாதுகாப்பு",
            lightMix: "இலகுவான கலவை எடை",
            plainMud: "சாதாரண மண் எடை",
            savedWt: "குறைக்கப்பட்ட எடை",
            slabSafe: "மாடிக்கு முற்றிலும் பாதுகாப்பானது",
            bucketMix: "மண் கலவை (10L வாளி அளவு)",
            cocopeat: "கோகோபீட்",
            compost: "மண்புழு உரம்",
            redSoil: "செம்மண்",
            neemCake: "வேப்பம் புண்ணாக்கு",
            bucketsUnit: "வாளி",
            blocksUnit: "கட்டி",
            waterToday: "இன்றைய தண்ணீர் (12×12 பை)",
            mugsUnit: "மக்",
            bestCrops: "உங்கள் வெயில் & வானிலைக்கு ஏற்ற பயிர்கள்",
            learnHowBtn: "வளர்க்கக் கற்றுக்கொள் →",
            potNeeded: "பை அளவு",
            sunNeeded: "தினசரி வெயில்",
            firstHarvest: "முதல் அறுவடை",
            stepsHeading: "படிப்படியான வளர்ப்பு முறை",
            boosterHeading: "வீட்டு சமையலறை ஊட்டச்சத்து",
            mistakesHeading: "தவிர்க்க வேண்டிய தவறுகள்",
            weatherTipHeading: "இன்றைய வானிலை குறிப்பு",
            listenGuide: "முழு வழிகாட்டியைக் கேள்",
            aiCoachBadge: "ஆன்லைன் AI வழிகாட்டி",
            offlineCoachBadge: "ஆஃப்லைன் வழிகாட்டி"
        },
        te: {
            navLabel: "టెర్రస్ సాగు & నేర్చుకోండి",
            heroTag: "మిద్దె తోట (Terrace), బాల్కనీ & కొత్తవారి సాగు గైడ్",
            planTitle: "స్మార్ట్ మిద్దె తోట & బాల్కనీ ప్లానర్",
            planSubtitle: "మీ స్థలం, ఎండ మరియు లైవ్ వాతావరణం ఆధారంగా సరైన పంటలు, 10L బకెట్ మట్టి మిశ్రమం మరియు ఈరోజు నీటి కొలతను చూపుతుంది.",
            presetLabel: "త్వరిత స్థల పరిమాణాలు:",
            locLabel: "నగరం, పట్టణం, గ్రామం లేదా PIN",
            locPh: "నగరం లేదా PIN నమోదు చేయండి...",
            lenLabel: "పొడవు (అడుగులు)",
            widLabel: "వెడల్పు (అడుగులు)",
            sunLabel: "ఎండ (గంటలు/రోజు)",
            spaceLabel: "స్థలం రకం",
            goalLabel: "మీరు ఏమి పెంచాలనుకుంటున్నారు?",
            calcBtn: "నా మిద్దె తోట ప్లాన్ లెక్కించు",
            planPrompt: "మీ ఊరు/PIN (లేదా 📍 GPS) మరియు పొడవు, వెడల్పు, ఎండ గంటలను నమోదు చేయండి.",
            coachTitle: "🌱 విత్తనం నుండి కోత వరకు — కొత్తవారి సాగు గురువు",
            coachSubtitle: "ఎలాంటి అనుభవం అవసరం లేదు! సులభమైన ఇంటి సాగు పద్ధతులు మరియు వాయిస్ ఆడియో కోసం పంటను ఎంచుకోండి.",
            customPh: "లేదా ఏదైనా మొక్క పేరు రాయండి (ఉదా: అల్లం, తులసి, దోసకాయ)...",
            learnBtn: "పెంచే విధానం చూడు",
            coachPrompt: "సులభమైన గైడ్ కోసం పైన ఉన్న ఏదైనా పంటపై నొక్కండి (ఉదా: మెంతుకూర, కొత్తిమీర, టమాటా).",
            bagLayout: "గ్రో-బ్యాగ్ అమరిక",
            totalArea: "మొత్తం స్థలం",
            growZone: "60% మొక్కల స్థలం (40% నడక దారి)",
            totalBags: "మొత్తం బ్యాగులు",
            roofSafety: "స్లాబ్ బరువు భద్రత",
            lightMix: "తేలికపాటి మట్టి బరువు",
            plainMud: "సాధారణ మట్టి బరువు",
            savedWt: "తగ్గిన బరువు",
            slabSafe: "పైకప్పుకు పూర్తిగా సురక్షితం",
            bucketMix: "మట్టి మిశ్రమం (10L బకెట్లలో)",
            cocopeat: "కోకోపీట్",
            compost: "కంపోస్ట్ ఎరువు",
            redSoil: "ఎర్రమట్టి",
            neemCake: "వేపపిండి",
            bucketsUnit: "బకెట్లు",
            blocksUnit: "దిమ్మెలు",
            waterToday: "ఈరోజు నీరు (12×12 బ్యాగ్)",
            mugsUnit: "మగ్గులు",
            bestCrops: "మీ ఎండ & వాతావరణానికి తగిన పంటలు",
            learnHowBtn: "పెంచడం నేర్చుకోండి →",
            potNeeded: "బ్యాగ్ పరిమాణం",
            sunNeeded: "రోజువారీ ఎండ",
            firstHarvest: "మొదటి కోత",
            stepsHeading: "విత్తనం నుండి కోత వరకు దశలు",
            boosterHeading: "వంటింటి సహజ బూస్టర్",
            mistakesHeading: "నివారించాల్సిన తప్పులు",
            weatherTipHeading: "ఈరోజు వాతావరణ సూచన",
            listenGuide: "పూర్తి గైడ్ వినండి",
            aiCoachBadge: "ఆన్‌లైన్ AI కోచ్",
            offlineCoachBadge: "ఆఫ్‌లైన్ గైడ్"
        },
        mr: {
            navLabel: "गच्चीवरील शेती व शिका",
            heroTag: "गच्चीवरील बाग (Terrace), बाल्कनी व नवशिक्यांसाठी शेती",
            planTitle: "स्मार्ट गच्ची व बाल्कनी बाग नियोजक",
            planSubtitle: "तुमची जागा, ऊन आणि थेट हवामानावरून योग्य पिके, 10L बादली माती मिश्रण आणि आजचे पाणी मोजते.",
            presetLabel: "झटपट जागेचे आकार:",
            locLabel: "शहर, गाव किंवा पिन कोड",
            locPh: "शहर, गाव किंवा पिन टाका...",
            lenLabel: "लांबी (फूट)",
            widLabel: "रुंदी (फूट)",
            sunLabel: "थेट ऊन (तास/दिवस)",
            spaceLabel: "जागेचा प्रकार",
            goalLabel: "तुम्हाला काय पिकवायचे आहे?",
            calcBtn: "माझा टेरेस प्लॅन तयार करा",
            planPrompt: "तुमचे शहर/पिन (किंवा 📍 GPS) आणि लांबी, रुंदी व उन्हाचे तास टाका (किंवा वरील आकार निवडा).",
            coachTitle: "🌱 बियाण्यापासून काढणीपर्यंत — नवशिक्यांचा शेती मार्गदर्शक",
            coachSubtitle: "कोणत्याही अनुभवाची गरज नाही! घरच्या घरी सोप्या पद्धतीने झाडे लावण्यासाठी वरील पीक निवडा.",
            customPh: "किंवा कोणतेही झाड लिहा (उदा: आले, तुळस, काकडी, लसूण)...",
            learnBtn: "लागवड पद्धत पहा",
            coachPrompt: "सोप्या मार्गदर्शनासाठी वरील कोणत्याही पिकावर क्लिक करा (उदा: मेथी, कोथिंबीर, टोमॅटो).",
            bagLayout: "ग्रो-बॅग रचना",
            totalArea: "एकूण जागा",
            growZone: "60% लागवड जागा (40% चालण्यासाठी)",
            totalBags: "एकूण ग्रो-बॅग",
            roofSafety: "गच्ची वजन सुरक्षितता",
            lightMix: "हलक्या मिश्रणाचे वजन",
            plainMud: "साध्या मातीचे वजन",
            savedWt: "गच्चीवरील वाचलेले वजन",
            slabSafe: "स्लॅबसाठी पूर्णपणे सुरक्षित",
            bucketMix: "माती मिश्रण (10L बादली प्रमाण)",
            cocopeat: "कोकोपीट",
            compost: "गांडूळ खत",
            redSoil: "लाल माती",
            neemCake: "निंबोळी पेंड",
            bucketsUnit: "बादल्या",
            blocksUnit: "ठोकळे",
            waterToday: "आजचे पाणी (12×12 बॅग)",
            mugsUnit: "मग",
            bestCrops: "तुमच्या ऊन आणि हवामानासाठी सर्वोत्तम पिके",
            learnHowBtn: "लागवड शिका →",
            potNeeded: "बॅग आकार",
            sunNeeded: "दररोजचे ऊन",
            firstHarvest: "पहिली काढणी",
            stepsHeading: "बियाण्यापासून काढणीपर्यंत सोप्या पायऱ्या",
            boosterHeading: "घरगुती खत / बूस्टर",
            mistakesHeading: "टाळावयाच्या चुका",
            weatherTipHeading: "आजचा हवामान सल्ला",
            listenGuide: "पूर्ण माहिती ऐका",
            aiCoachBadge: "ऑनलाइन AI मार्गदर्शक",
            offlineCoachBadge: "ऑफलाइन मार्गदर्शक"
        }
    };

    const DISEASE_I18N = {
        en: {
            tabTitle: "Leaf Health Doctor", uploadBtn: "Upload Leaf Photo", sampleHeading: "Or Tap a Sample Leaf Photo to Test:",
            conf: "Match Confidence", sev: "Damage Level", cause: "What Caused This", area: "Spotted Leaf Area",
            symp: "What We See on the Leaf", org: "Home / Natural Care",
            chem: "Agri-Shop Medicine", proto: "Simple Care Steps",
            aiBadge: "Online AI Vision", offlineCnnBadge: "Offline Local AI Model", fbBadge: "Offline Leaf Scan",
            scanning: "Checking leaf photo with AI Leaf Doctor..."
        },
        kn: {
            tabTitle: "ಎಲೆ ರೋಗ ತಪಾಸಣೆ (Leaf Health Doctor)", uploadBtn: "ಎಲೆಯ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ", sampleHeading: "ಅಥವಾ ಪರೀಕ್ಷಿಸಲು ಮಾದರಿ ಎಲೆ ಚಿತ್ರವನ್ನು ಒತ್ತಿ:",
            conf: "ಹೊಂದಾಣಿಕೆ ನಿಖರತೆ", sev: "ಹಾನಿಯ ಮಟ್ಟ", cause: "ಇದಕ್ಕೆ ಕಾರಣ", area: "ಚುಕ್ಕೆ ಹರಡಿದ ಭಾಗ",
            symp: "ಎಲೆಯ ಮೇಲೆ ಕಾಣುವ ಲಕ್ಷಣಗಳು", org: "ಮನೆ / ನೈಸರ್ಗಿಕ ಪರಿಹಾರ",
            chem: "ಅಂಗಡಿ ಔಷಧಿ ಸಲಹೆ", proto: "ಮುಂದಿನ ಸರಳ ಕ್ರಮಗಳು",
            aiBadge: "ಆನ್‌ಲೈನ್ AI ದೃಷ್ಟಿ", offlineCnnBadge: "ಆಫ್‌ಲೈನ್ ಸ್ಥಳೀಯ AI ಮಾಡೆಲ್", fbBadge: "ಆಫ್‌ಲೈನ್ ಎಲೆ ತಪಾಸಣೆ",
            scanning: "AI ಎಲೆ ವೈದ್ಯರಿಂದ ಫೋಟೋ ತಪಾಸಣೆ ನಡೆಯುತ್ತಿದೆ..."
        },
        hi: {
            tabTitle: "पत्ती स्वास्थ्य डॉक्टर (Leaf Health Doctor)", uploadBtn: "पत्ती की फोटो अपलोड करें", sampleHeading: "या जांच के लिए नमूना पत्ती चुनें:",
            conf: "पहचान भरोसा", sev: "नुकसान का स्तर", cause: "इसका कारण", area: "धब्बे वाला हिस्सा",
            symp: "पत्ती पर दिखने वाले लक्षण", org: "घरेलू / प्राकृतिक उपाय",
            chem: "दुकान की दवा सलाह", proto: "आसान देखभाल कदम",
            aiBadge: "ऑनलाइन AI विज़न", offlineCnnBadge: "ऑफलाइन लोकल AI मॉडल", fbBadge: "ऑफलाइन पत्ती जांच",
            scanning: "AI पत्ती डॉक्टर से फोटो की जांच हो रही है..."
        },
        ta: {
            tabTitle: "இலை நல மருத்துவர் (Leaf Health Doctor)", uploadBtn: "இலை படத்தை பதிவேற்றவும்", sampleHeading: "அல்லது சோதனைக்கு மாதிரி இலையைத் தொடவும்:",
            conf: "நம்பகத்தன்மை", sev: "சேத அளவு", cause: "இதற்கான காரணம்", area: "புள்ளி பரவிய பகுதி",
            symp: "இலையில் தெரியும் அறிகுறிகள்", org: "வீட்டு / இயற்கை தீர்வு",
            chem: "கடை மருந்து பரிந்துரை", proto: "எளிய பராமரிப்பு படிகள்",
            aiBadge: "ஆன்லைன் AI பார்வை", offlineCnnBadge: "ஆஃப்லைன் உள்ளூர் AI மாடல்", fbBadge: "ஆஃப்லைன் இலை சோதனை",
            scanning: "AI இலை மருத்துவர் படத்தைச் சோதிக்கிறார்..."
        },
        te: {
            tabTitle: "ఆకు ఆరోగ్య వైద్యుడు (Leaf Health Doctor)", uploadBtn: "ఆకు ఫోటో అప్‌లోడ్ చేయండి", sampleHeading: "లేదా పరీక్ష కోసం నమూనా ఆకును ఎంచుకోండి:",
            conf: "నిర్ధారణ నమ్మకం", sev: "నష్టం స్థాయి", cause: "దీనికి కారణం", area: "మచ్చలు ఉన్న భాగం",
            symp: "ఆకుపై కనిపించే లక్షణాలు", org: "ఇంటి / సహజ నివారణ",
            chem: "దుకాణం మందు సూచన", proto: "సులభమైన జాగ్రత్తలు",
            aiBadge: "ఆన్‌లైన్ AI విజన్", offlineCnnBadge: "ఆఫ్‌లైన్ లోకల్ AI మోడల్", fbBadge: "ఆఫ్‌లైన్ ఆకు పరీక్ష",
            scanning: "AI ఆకు వైద్యుడు ఫోటోను పరీక్షిస్తున్నారు..."
        },
        mr: {
            tabTitle: "पान आरोग्य डॉक्टर (Leaf Health Doctor)", uploadBtn: "पानाचा फोटो अपलोड करा", sampleHeading: "किंवा चाचणीसाठी नमुना पान निवडा:",
            conf: "ओळख अचूकता", sev: "नुकसानीची पातळी", cause: "यामागचे कारण", area: "ठिपके असलेला भाग",
            symp: "पानावर दिसणारी लक्षणे", org: "घरगुती / नैसर्गिक उपाय",
            chem: "दुकानातील औषध सल्ला", proto: "सोप्या काळजीच्या पायऱ्या",
            aiBadge: "ऑनलाइन AI व्हिजन", offlineCnnBadge: "ऑफलाइन लोकल AI मॉडेल", fbBadge: "ऑफलाइन पान तपासणी",
            scanning: "AI पान डॉक्टर फोटो तपासत आहेत..."
        }
    };

    const TOOLS_I18N = {
        en: {
            weatherTitle: "Live Weather Tool", soilTitle: "Soil Health Tool", mandiTitle: "APMC Mandi Tool",
            fetch: "Fetch", live: "LIVE", cached: "CACHED", benchmark: "BENCHMARK", ready: "READY", offline: "OFFLINE",
            humidity: "Humidity", wind: "Wind", gusts: "Gusts", feelsLike: "Feels like", et0Label: "Sun Drying",
            rainToday: "Rain Today", rainTom: "Rain Tomorrow",
            irrTitle: "Watering Advice", sprayTitle: "Safe Spraying Check (Next 6 Hrs)", forecast7d: "7-Day Weather Plan",
            locPlaceholder: "Village, Taluk, District or PIN...",
            enterLocPrompt: "Enter your village, taluk, district, or 6-digit PIN — or tap 📍 for live farm GPS data.",
            locNotFound: "Location not found. Please check spelling or include your district name.",
            weatherOffline: "Live weather service is unreachable right now. Please check internet.",
            soilMoist: "Soil Moisture", healthyRange: "Healthy range for this soil",
            nitrogen: "Leaf Growth (N)", phosphorus: "Root & Flower (P)",
            potassium: "Fruit Strength (K)", oc: "Soil Richness (Humus)",
            amendment: "What Your Soil Needs", techDetails: "Technical Sensor Readings",
            mandi: "APMC Market", modal: "Usual Rate", dist: "Distance",
            rangeLabel: "Today's Range", mspLabel: "Govt Support Price (MSP)",
            cropPlaceholder: "Crop (e.g. Tomato, Paddy, Onion, Coffee)...",
            enterMandiPrompt: "Choose a crop and optionally enter your village, district, or PIN (or tap 📍) to check live APMC market rates.",
            strategy: "Selling Tip", qtl: "/ 100 kg", kg: "/kg",
            srcLive: "Live — Open-Meteo", srcSoil: "Live — 250m Satellite Soil + Root Moisture", srcMandi: "Live — Agmarknet APMC Arrivals"
        },
        kn: {
            weatherTitle: "ನೇರ ಹವಾಮಾನ ಉಪಕರಣ", soilTitle: "ಮಣ್ಣಿನ ಆರೋಗ್ಯ ಉಪಕರಣ", mandiTitle: "APMC ಮಂಡಿ ದರ ಉಪಕರಣ",
            fetch: "ಪಡೆಯಿರಿ", live: "ನೇರ", cached: "ಸಂಗ್ರಹ", benchmark: "ಅಂದಾಜು", ready: "ಸಿದ್ಧ", offline: "ಆಫ್‌ಲೈನ್",
            humidity: "ತೇವಾಂಶ (ಗಾಳಿ)", wind: "ಗಾಳಿ", gusts: "ಜೋರು ಗಾಳಿ", feelsLike: "ಅನುಭವ", et0Label: "ಬಿಸಿಲಿನ ಒಣಗುವಿಕೆ",
            rainToday: "ಇಂದಿನ ಮಳೆ", rainTom: "ನಾಳೆಯ ಮಳೆ",
            irrTitle: "ನೀರು ಹಾಯಿಸುವ ಸಲಹೆ", sprayTitle: "ಮುಂದಿನ 6 ಗಂಟೆ ಔಷಧಿ ಸಿಂಪಡಣೆ", forecast7d: "7-ದಿನಗಳ ಹವಾಮಾನ ಮಾಹಿತಿ",
            locPlaceholder: "ಗ್ರಾಮ, ತಾಲೂಕು, ಜಿಲ್ಲೆ ಅಥವಾ PIN...",
            enterLocPrompt: "ನೇರ ಮಾಹಿತಿ ಪಡೆಯಲು ನಿಮ್ಮ ಗ್ರಾಮ, ತಾಲೂಕು, ಜಿಲ್ಲೆ ಅಥವಾ PIN ನಮೂದಿಸಿ (ಅಥವಾ 📍 GPS ಒತ್ತಿ).",
            locNotFound: "ಸ್ಥಳ ಕಂಡುಬಂದಿಲ್ಲ. ಕಾಗುಣಿತ ಪರಿಶೀಲಿಸಿ ಅಥವಾ ಜಿಲ್ಲೆಯ ಹೆಸರನ್ನು ಸೇರಿಸಿ.",
            weatherOffline: "ನೇರ ಸೇವೆ ಸಂಪರ್ಕಕ್ಕೆ ಸಿಗುತ್ತಿಲ್ಲ. ಇಂಟರ್ನೆಟ್ ಪರಿಶೀಲಿಸಿ.",
            soilMoist: "ಮಣ್ಣಿನ ತೇವಾಂಶ", healthyRange: "ಈ ಮಣ್ಣಿಗೆ ಸೂಕ್ತ ತೇವಾಂಶ ಮಿತಿ",
            nitrogen: "ಎಲೆ ಬೆಳವಣಿಗೆ (ಸಾರಜನಕ)", phosphorus: "ಬೇರು & ಹೂವು (ರಂಜಕ)",
            potassium: "ಕಾಯಿ ಬಲ (ಪೊಟ್ಯಾಶ್)", oc: "ಮಣ್ಣಿನ ಫಲವತ್ತತೆ (ಹ್ಯೂಮಸ್)",
            amendment: "ಮಣ್ಣಿಗೆ ಮಾಡಬೇಕಾದ ಆರೈಕೆ", techDetails: "ತಾಂತ್ರಿಕ ಮಾಪನ ವಿವರಗಳು",
            mandi: "ಮಾರುಕಟ್ಟೆ (APMC)", modal: "ಸಾಮಾನ್ಯ ದರ", dist: "ದೂರ",
            rangeLabel: "ಇಂದಿನ ದರ ಮಿತಿ", mspLabel: "ಸರ್ಕಾರಿ ಬೆಂಬಲ ಬೆಲೆ (MSP)",
            cropPlaceholder: "ಬೆಳೆ (ಉದಾ: ಟೊಮೆಟೊ, ಭತ್ತ, ಈರುಳ್ಳಿ, ಕಾಫಿ)...",
            enterMandiPrompt: "ನೇರ APMC ಮಂಡಿ ದರ ತಿಳಿಯಲು ಬೆಳೆ ಮತ್ತು ನಿಮ್ಮ ಗ್ರಾಮ/ಜಿಲ್ಲೆಯನ್ನು ನಮೂದಿಸಿ.",
            strategy: "ಮಾರಾಟ ಸಲಹೆ", qtl: "/ ಕ್ವಿಂಟಾಲ್", kg: "/ಕೆ.ಜಿ",
            srcLive: "ನೇರ ಮಾಹಿತಿ — Open-Meteo", srcSoil: "ನೇರ — ಮಣ್ಣು ಮತ್ತು ಬೇರಿನ ತೇವಾಂಶ", srcMandi: "ನೇರ — APMC ಮಾರುಕಟ್ಟೆ ದರ"
        },
        hi: {
            weatherTitle: "लाइव मौसम टूल", soilTitle: "मिट्टी स्वास्थ्य टूल", mandiTitle: "APMC मंडी टूल",
            fetch: "देखें", live: "लाइव", cached: "कैश्ड", benchmark: "अनुमानित", ready: "तैयार", offline: "ऑफ़लाइन",
            humidity: "हवा में नमी", wind: "हवा", gusts: "तेज़ हवा", feelsLike: "महसूस", et0Label: "धूप से सूखना",
            rainToday: "आज की बारिश", rainTom: "कल की बारिश",
            irrTitle: "पानी देने की सलाह", sprayTitle: "अगले 6 घंटे छिड़काव सलाह", forecast7d: "7-दिन का मौसम",
            locPlaceholder: "गांव, तहसील, जिला या पिन कोड...",
            enterLocPrompt: "लाइव जानकारी के लिए अपना गांव, तहसील, जिला या पिन कोड लिखें (या 📍 GPS दबाएं)।",
            locNotFound: "स्थान नहीं मिला। कृपया वर्तनी जांचें या जिले का नाम जोड़ें।",
            weatherOffline: "लाइव सेवा अभी उपलब्ध नहीं है। इंटरनेट कनेक्शन जांचें।",
            soilMoist: "मिट्टी की नमी", healthyRange: "इस मिट्टी के लिए सही नमी",
            nitrogen: "पत्ती विकास (नाइट्रोजन)", phosphorus: "जड़ व फूल (फॉस्फोरस)",
            potassium: "फल मज़बूती (पोटाश)", oc: "मिट्टी की उपजाऊ शक्ति (खाद)",
            amendment: "मिट्टी के लिए आसान उपाय", techDetails: "तकनीकी सेंसर विवरण",
            mandi: "मंडी (APMC)", modal: "सामान्य भाव", dist: "दूरी",
            rangeLabel: "आज का भाव दायरा", mspLabel: "सरकारी समर्थन मूल्य (MSP)",
            cropPlaceholder: "फसल (जैसे: टमाटर, धान, प्याज, मक्का)...",
            enterMandiPrompt: "लाइव मंडी भाव देखने के लिए फसल और अपना गांव/जिला लिखें।",
            strategy: "बिक्री सलाह", qtl: "/ क्विंटल", kg: "/किलो",
            srcLive: "लाइव — Open-Meteo", srcSoil: "लाइव — उपग्रह मिट्टी एवं नमी", srcMandi: "लाइव — APMC मंडी भाव"
        },
        ta: {
            weatherTitle: "நேரடி வானிலை கருவி", soilTitle: "மண் ஆரோக்கிய கருவி", mandiTitle: "APMC சந்தை கருவி",
            fetch: "பெறு", live: "நேரடி", cached: "சேமிப்பு", benchmark: "மதிப்பீடு", ready: "தயார்", offline: "ஆஃப்லைன்",
            humidity: "காற்றின் ஈரம்", wind: "காற்று", gusts: "பலத்த காற்று", feelsLike: "உணர்வு", et0Label: "வெயில் உலர்வு",
            rainToday: "இன்றைய மழை", rainTom: "நாளைய மழை",
            irrTitle: "தண்ணீர் பாய்ச்சும் ஆலோசனை", sprayTitle: "அடுத்த 6 மணி நேர தெளிப்பு", forecast7d: "7-நாள் வானிலை",
            locPlaceholder: "கிராமம், வட்டம், மாவட்டம் / PIN...",
            enterLocPrompt: "நேரடி தகவலுக்கு உங்கள் கிராமம், மாவட்டம் அல்லது PIN எண்ணை உள்ளிடவும் (அல்லது 📍 GPS அழுத்தவும்).",
            locNotFound: "இடம் கண்டறியப்படவில்லை. எழுத்துப்பிழையைச் சரிபார்க்கவும்.",
            weatherOffline: "நேரடி சேவை தற்போது கிடைக்கவில்லை.",
            soilMoist: "மண் ஈரப்பதம்", healthyRange: "இந்த மண்ணுக்கு ஏற்ற ஈரப்பதம்",
            nitrogen: "இலை வளர்ச்சி (தழைச்சத்து)", phosphorus: "வேர் & பூ (மணிச்சத்து)",
            potassium: "காய் உறுதி (சாம்பல் சத்து)", oc: "மண் வளம் (மட்கிய சத்து)",
            amendment: "மண்ணுக்கு செய்ய வேண்டியவை", techDetails: "தொழில்நுட்ப விவரங்கள்",
            mandi: "சந்தை (APMC)", modal: "வழக்கமான விலை", dist: "தூரம்",
            rangeLabel: "இன்றைய விலை வரம்பு", mspLabel: "அரசு ஆதரவு விலை (MSP)",
            cropPlaceholder: "பயிர் (எ.கா: தக்காளி, நெல், வெங்காயம்)...",
            enterMandiPrompt: "நேரடி சந்தை விலைக்கு பயிர் மற்றும் உங்கள் ஊரை உள்ளிடவும்.",
            strategy: "விற்பனை ஆலோசனை", qtl: "/ குவிண்டால்", kg: "/கிலோ",
            srcLive: "நேரடி — Open-Meteo", srcSoil: "நேரடி — மண் & ஈரப்பதம்", srcMandi: "நேரடி — APMC சந்தை விலை"
        },
        te: {
            weatherTitle: "లైవ్ వాతావరణ టూల్", soilTitle: "మట్టి ఆరోగ్య టూల్", mandiTitle: "APMC మార్కెట్ టూల్",
            fetch: "చూడు", live: "లైవ్", cached: "క్యాష్", benchmark: "అంచనా", ready: "సిద్ధం", offline: "ఆఫ్‌లైన్",
            humidity: "గాలిలో తేమ", wind: "గాలి", gusts: "గాలి వేగం", feelsLike: "అనుభూతి", et0Label: "ఎండ ఆవిరి",
            rainToday: "ఈరోజు వర్షం", rainTom: "రేపటి వర్షం",
            irrTitle: "నీరు పెట్టే సలహా", sprayTitle: "6-గంటల పిచికారీ సలహా", forecast7d: "7-రోజుల వాతావరణం",
            locPlaceholder: "గ్రామం, మండలం, జిల్లా లేదా PIN...",
            enterLocPrompt: "లైవ్ సమాచారం కోసం మీ గ్రామం, జిల్లా లేదా PIN నమోదు చేయండి (లేదా 📍 GPS నొక్కండి).",
            locNotFound: "ప్రాంతం కనుగొనబడలేదు. దయచేసి స్పెల్లింగ్ తనిఖీ చేయండి.",
            weatherOffline: "లైవ్ సేవ ప్రస్తుతం అందుబాటులో లేదు.",
            soilMoist: "మట్టిలో తేమ", healthyRange: "ఈ మట్టికి సరైన తేమ",
            nitrogen: "ఆకు పెరుగుదల (నత్రజని)", phosphorus: "వేరు & పూత (భాస్వరం)",
            potassium: "కాయ బలం (పొటాష్)", oc: "మట్టి బలం (సేంద్రీయ ఎరువు)",
            amendment: "మట్టికి చేయాల్సిన జాగ్రత్తలు", techDetails: "సాంకేతిక వివరాలు",
            mandi: "మార్కెట్ (APMC)", modal: "సాధారణ ధర", dist: "దూరం",
            rangeLabel: "ఈరోజు ధర పరిధి", mspLabel: "ప్రభుత్వ మద్దతు ధర (MSP)",
            cropPlaceholder: "పంట (ఉదా: టమాటా, వరి, ఉల్లి, మిర్చి)...",
            enterMandiPrompt: "లైవ్ మార్కెట్ ధర కోసం పంట మరియు మీ గ్రామం/జిల్లా నమోదు చేయండి.",
            strategy: "విక్రయ సలహా", qtl: "/ క్వింటాల్", kg: "/కిలో",
            srcLive: "లైవ్ — Open-Meteo", srcSoil: "లైవ్ — మట్టి & వేర్ల తేమ", srcMandi: "లైవ్ — APMC మార్కెట్ ధర"
        },
        mr: {
            weatherTitle: "थेट हवामान साधन", soilTitle: "माती आरोग्य साधन", mandiTitle: "APMC बाजारभाव साधन",
            fetch: "पहा", live: "थेट", cached: "संग्रहित", benchmark: "अंदाजित", ready: "तयार", offline: "ऑफलाइन",
            humidity: "हवेतील ओलावा", wind: "वारा", gusts: "जोरदार वारा", feelsLike: "जाणीव", et0Label: "उन्हाने सुकणे",
            rainToday: "आजचा पाऊस", rainTom: "उद्याचा पाऊस",
            irrTitle: "पाणी देण्याचा सल्ला", sprayTitle: "पुढील 6 तास फवारणी सल्ला", forecast7d: "7-दिवसांचा अंदाज",
            locPlaceholder: "गाव, तालुका, जिल्हा किंवा पिन...",
            enterLocPrompt: "थेट माहितीसाठी आपले गाव, तालुका, जिल्हा किंवा पिन कोड टाका (किंवा 📍 GPS दाबा).",
            locNotFound: "ठिकाण सापडले नाही. कृपया स्पेलिंग तपासा किंवा जिल्हा जोडा.",
            weatherOffline: "थेट सेवा सध्या उपलब्ध नाही.",
            soilMoist: "मातीतील ओलावा", healthyRange: "या मातीसाठी योग्य ओलावा",
            nitrogen: "पानांची वाढ (नत्र)", phosphorus: "मुळांची व फुलांची ताकद (स्फुरद)",
            potassium: "फळांची ताकद (पालाश)", oc: "मातीचा कस (सेंद्रिय खत)",
            amendment: "मातीसाठी सोपे उपाय", techDetails: "तांत्रिक तपशील",
            mandi: "बाजार (APMC)", modal: "नेहमीचा भाव", dist: "अंतर",
            rangeLabel: "आजची भाव मर्यादा", mspLabel: "हमीभाव (MSP)",
            cropPlaceholder: "पीक (उदा: टोमॅटो, कांदा, भात, कापूस)...",
            enterMandiPrompt: "थेट बाजारभाव पाहण्यासाठी पीक आणि तुमचे गाव/जिल्हा टाका.",
            strategy: "विक्री सल्ला", qtl: "/ क्विंटल", kg: "/किलो",
            srcLive: "थेट — Open-Meteo", srcSoil: "थेट — माती व मुळांचा ओलावा", srcMandi: "थेट — APMC बाजारभाव"
        }
    };

    function getToolT(lang) {
        return TOOLS_I18N[lang] || TOOLS_I18N.en;
    }

    function translateToolStatus(text, lang) {
        if (!text) return "";
        const enFriendly = {
            "DO_NOT_IRRIGATE": "Do not water today — rain expected",
            "DELAY_IRRIGATION": "Hold off watering — rain expected tomorrow",
            "IRRIGATE_SOON": "Water soon — hot weather is drying the soil",
            "NORMAL_SCHEDULE": "Continue normal watering schedule",
            "AVOID_SPRAYING": "Avoid spraying now — rain risk in next 6 hours",
            "HIGH_WIND_DRIFT": "Too windy to spray right now",
            "SPRAY_EARLY_MORNING": "Too hot — spray before 9 AM or after 4:30 PM",
            "IDEAL_FOR_SPRAYING": "Safe to spray in the next 6 hours",
            "OPTIMAL_MOISTURE": "Good Moisture — No Watering Needed",
            "CRITICAL_DEFICIT": "Too Dry — Water Today",
            "MODERATE_MOISTURE": "Slightly Dry — Water in 1–2 Days",
            "SATURATED_SOIL": "Very Wet — Drain Excess Water",
            "Adequate": "Good", "High": "Good (Rich)", "Medium": "Moderate", "Low-Medium": "Slightly Low", "Low": "Low (Needs Boost)"
        };
        if (lang === "en") {
            if (enFriendly[text]) return enFriendly[text];
            return text.replace(/^[A-Z_]{4,}:\s*/, "");
        }
        const map = {
            "kn": {
                "DO_NOT_IRRIGATE": "ಇಂದು ನೀರು ಹಾಯಿಸಬೇಡಿ — ಮಳೆ ನಿರೀಕ್ಷಿತ",
                "DELAY_IRRIGATION": "ನೀರಾವರಿ ಮುಂದೂಡಿ — 24 ಗಂಟೆಯಲ್ಲಿ ಮಳೆ ಸಂಭವ",
                "IRRIGATE_SOON": "ಶೀಘ್ರ ನೀರಾವರಿ ಮಾಡಿ — ಬಾಷ್ಪೀಕರಣ ಹೆಚ್ಚಾಗಿದೆ",
                "NORMAL_SCHEDULE": "ನಿಯಮಿತ ನೀರಾವರಿ ಮುಂದುವರಿಸಿ — ಹವಾಮಾನ ಸ್ಥಿರವಾಗಿದೆ",
                "AVOID_SPRAYING": "ಈಗ ಸಿಂಪಡಣೆ ಬೇಡ — ಮಳೆಯಿಂದ ಔಷಧಿ ತೊಳೆದುಹೋಗುತ್ತದೆ",
                "HIGH_WIND_DRIFT": "ಈಗ ಸಿಂಪಡಣೆ ಬೇಡ — ಜೋರು ಗಾಳಿಯಿದೆ",
                "SPRAY_EARLY_MORNING": "ಬಿಸಿಲು ಹೆಚ್ಚಿದೆ — ಬೆಳಿಗ್ಗೆ 9 ರ ಮೊದಲು ಸಿಂಪಡಿಸಿ",
                "IDEAL_FOR_SPRAYING": "ಮುಂದಿನ 6 ಗಂಟೆ ಸಿಂಪಡಣೆಗೆ ಅತ್ಯಂತ ಸೂಕ್ತ ಸಮಯ",
                "OPTIMAL_MOISTURE": "ಉತ್ತಮ ತೇವಾಂಶ (ಇಂದು ನೀರು ಬೇಡ)",
                "CRITICAL_DEFICIT": "ತೇವಾಂಶ ಕೊರತೆ (ತಕ್ಷಣ ನೀರು ಹಾಯಿಸಿ)",
                "MODERATE_MOISTURE": "ಮಧ್ಯಮ ತೇವಾಂಶ",
                "SATURATED_SOIL": "ಅತಿಯಾದ ತೇವಾಂಶ (ನೀರು ಬಸಿದುಹೋಗುವಂತೆ ನೋಡಿ)",
                "Adequate": "ಸಮರ್ಪಕ", "Low": "ಕಡಿಮೆ", "Medium": "ಮಧ್ಯಮ", "High": "ಹೆಚ್ಚು", "Low-Medium": "ಕಡಿಮೆ-ಮಧ್ಯಮ",
                "RISING": "ಏರಿಕೆ", "STRONG_BULLISH": "ಭಾರೀ ಏರಿಕೆ", "STABLE": "ಸ್ಥಿರ", "FALLING": "ಇಳಿಕೆ", "STABLE_TO_RISING": "ಸ್ಥಿರದಿಂದ ಏರಿಕೆ"
            },
            "hi": {
                "DO_NOT_IRRIGATE": "आज सिंचाई न करें — बारिश की संभावना",
                "DELAY_IRRIGATION": "सिंचाई टालें — कल बारिश का अनुमान",
                "IRRIGATE_SOON": "जल्द सिंचाई करें — अधिक वाष्पीकरण",
                "NORMAL_SCHEDULE": "सामान्य सिंचाई जारी रखें — मौसम स्थिर है",
                "AVOID_SPRAYING": "अभी छिड़काव न करें — अगले 6 घंटे में बारिश का जोखिम",
                "HIGH_WIND_DRIFT": "अभी छिड़काव न करें — हवा तेज़ है",
                "SPRAY_EARLY_MORNING": "तेज़ धूप — सुबह 9 बजे से पहले छिड़काव करें",
                "IDEAL_FOR_SPRAYING": "अगले 6 घंटे छिड़काव के लिए सुरक्षित हैं",
                "OPTIMAL_MOISTURE": "उत्तम नमी (आज सिंचाई की जरूरत नहीं)",
                "CRITICAL_DEFICIT": "नमी की कमी (तुरंत सिंचाई करें)",
                "MODERATE_MOISTURE": "मध्यम नमी",
                "SATURATED_SOIL": "अधिक नमी (जल निकासी करें)",
                "Adequate": "पर्याप्त", "Low": "कम", "Medium": "मध्यम", "High": "अधिक", "Low-Medium": "कम-मध्यम",
                "RISING": "तेजी में", "STRONG_BULLISH": "मजबूत तेजी", "STABLE": "स्थिर", "FALLING": "गिरावट", "STABLE_TO_RISING": "स्थिर से तेजी"
            },
            "ta": {
                "DO_NOT_IRRIGATE": "இன்று பாசனம் வேண்டாம் — மழை வாய்ப்பு",
                "DELAY_IRRIGATION": "பாசனத்தை ஒத்திவைக்கவும்",
                "IRRIGATE_SOON": "விரைவில் பாசனம் செய்யவும்",
                "NORMAL_SCHEDULE": "வழக்கமான பாசனம் தொடரவும்",
                "AVOID_SPRAYING": "இப்போது மருந்து தெளிக்க வேண்டாம் — மழை வாய்ப்பு",
                "HIGH_WIND_DRIFT": "காற்று அதிகம் — தெளிப்பதை தவிர்க்கவும்",
                "SPRAY_EARLY_MORNING": "காலை 9 மணிக்கு முன் தெளிக்கவும்",
                "IDEAL_FOR_SPRAYING": "அடுத்த 6 மணி நேரம் தெளிக்க உகந்த நேரம்",
                "OPTIMAL_MOISTURE": "சிறந்த ஈரப்பதம்", "CRITICAL_DEFICIT": "ஈரப்பதம் குறைவு",
                "MODERATE_MOISTURE": "மிதமான ஈரப்பதம்", "SATURATED_SOIL": "அதிக ஈரப்பதம்",
                "Adequate": "போதுமானது", "Low": "குறைவு", "Medium": "மிதமானது", "High": "அதிகம்", "Low-Medium": "குறைவு-மிதமானது",
                "RISING": "உயர்வு", "STRONG_BULLISH": "அதிக உயர்வு", "STABLE": "நிலையானது", "FALLING": "சரிவு", "STABLE_TO_RISING": "உயர்வு போக்கு"
            },
            "te": {
                "DO_NOT_IRRIGATE": "ఈరోజు నీరు పెట్టకండి — వర్షం అవకాశం",
                "DELAY_IRRIGATION": "నీటిపారుదల వాయిదా వేయండి",
                "IRRIGATE_SOON": "త్వరగా నీరు పెట్టండి",
                "NORMAL_SCHEDULE": "సాధారణ నీటిపారుదల కొనసాగించండి",
                "AVOID_SPRAYING": "ఇప్పుడు పిచికారీ వద్దు — వర్షం అవకాశం",
                "HIGH_WIND_DRIFT": "గాలి ఎక్కువగా ఉంది — పిచికారీ ఆపండి",
                "SPRAY_EARLY_MORNING": "ఉదయం 9 గంటల లోపు పిచికారీ చేయండి",
                "IDEAL_FOR_SPRAYING": "రాబోయే 6 గంటలు పిచికారీకి అనుకూలం",
                "OPTIMAL_MOISTURE": "ఉత్తమ తేమ", "CRITICAL_DEFICIT": "తేమ లోపం",
                "MODERATE_MOISTURE": "మధ్యస్థ తేమ", "SATURATED_SOIL": "అధిక తేమ",
                "Adequate": "సరిపడా", "Low": "తక్కువ", "Medium": "మధ్యస్థం", "High": "ఎక్కువ", "Low-Medium": "తక్కువ-మధ్యస్థం",
                "RISING": "పెరుగుదల", "STRONG_BULLISH": "భారీ పెరుగుదల", "STABLE": "స్థిరం", "FALLING": "తగ్గుదల", "STABLE_TO_RISING": "పెరుగుదల వైపు"
            },
            "mr": {
                "DO_NOT_IRRIGATE": "आज पाणी देऊ नका — पावसाची शक्यता",
                "DELAY_IRRIGATION": "सिंचन पुढे ढकला",
                "IRRIGATE_SOON": "लवकर पाणी द्या",
                "NORMAL_SCHEDULE": "नियमित सिंचन सुरू ठेवा",
                "AVOID_SPRAYING": "आत्ता फवारणी करू नका — पावसाची शक्यता",
                "HIGH_WIND_DRIFT": "जोरदार वारा — फवारणी टाळा",
                "SPRAY_EARLY_MORNING": "सकाळी 9 पूर्वी फवारणी करा",
                "IDEAL_FOR_SPRAYING": "पुढील 6 तास फवारणीसाठी सुरक्षित वेळ",
                "OPTIMAL_MOISTURE": "उत्तम ओलावा", "CRITICAL_DEFICIT": "ओलावा कमी",
                "MODERATE_MOISTURE": "मध्यम ओलावा", "SATURATED_SOIL": "जास्त ओलावा",
                "Adequate": "पुरेसे", "Low": "कमी", "Medium": "मध्यम", "High": "जास्त", "Low-Medium": "कमी-मध्यम",
                "RISING": "वाढ", "STRONG_BULLISH": "तीव्र वाढ", "STABLE": "स्थिर", "FALLING": "घसरण", "STABLE_TO_RISING": "वाढीकडे"
            }
        };
        const langMap = map[lang] || {};
        for (const [k, v] of Object.entries(langMap)) {
            if (text.includes(k)) return v;
        }
        return text;
    }

    function updateLanguagePlaceholder(lang) {
        const titleTranslations = {
            "en": "Quick Farm Inquiries:",
            "kn": "ತ್ವರಿತ ಕೃಷಿ ಪ್ರಶ್ನೆಗಳು:",
            "hi": "त्वरित कृषि प्रश्न:",
            "ta": "விரைவான விவசாய கேள்விகள்:",
            "te": "త్వరిత వ్యవసాయ ప్రశ్నలు:",
            "mr": "त्वरित कृषी प्रश्न:"
        };
        const quickInquiriesTitle = document.getElementById("quickInquiriesTitle");
        if (quickInquiriesTitle) {
            quickInquiriesTitle.textContent = titleTranslations[lang] || titleTranslations["en"];
        }

        const t = getToolT(lang);
        const wTitle = document.getElementById("toolsWeatherTitle");
        const sTitle = document.getElementById("toolsSoilTitle");
        const mTitle = document.getElementById("toolsMandiTitle");
        if (wTitle) wTitle.textContent = t.weatherTitle;
        if (sTitle) sTitle.textContent = t.soilTitle;
        if (mTitle) mTitle.textContent = t.mandiTitle;
        const wInput = document.getElementById("toolWeatherLoc");
        if (wInput) wInput.placeholder = t.locPlaceholder;
        const sInput = document.getElementById("toolSoilDist");
        if (sInput) sInput.placeholder = t.locPlaceholder;
        const mLocInput = document.getElementById("toolMandiLoc");
        if (mLocInput) mLocInput.placeholder = t.locPlaceholder;
        const mCropInput = document.getElementById("toolMandiCrop");
        if (mCropInput && t.cropPlaceholder) mCropInput.placeholder = t.cropPlaceholder;
        const wBtn = document.getElementById("testWeatherBtn");
        const sBtn = document.getElementById("testSoilBtn");
        const mBtn = document.getElementById("testMandiBtn");
        if (wBtn) wBtn.textContent = t.fetch;
        if (sBtn) sBtn.textContent = t.fetch;
        if (mBtn) mBtn.textContent = t.fetch;

        if (lastWeatherData) renderWeatherCard(lastWeatherData);
        else renderWeatherPrompt();
        if (lastSoilData) renderSoilCard(lastSoilData);
        else renderSoilPrompt();
        if (lastMandiData) fetchMandiTool();
        else renderMandiPrompt();

        const dt = DISEASE_I18N[lang] || DISEASE_I18N.en;
        const dTitle = document.getElementById("diseaseTabTitle");
        const dUpload = document.getElementById("uploadLeafBtnLabel");
        const dSampleH = document.getElementById("sampleLeavesHeading");
        if (dTitle) dTitle.textContent = dt.tabTitle;
        if (dUpload) dUpload.textContent = dt.uploadBtn;
        if (dSampleH) dSampleH.textContent = dt.sampleHeading;
        if (lastDiseaseSample) {
            runSampleLeafDiagnosis(lastDiseaseSample.sampleName, lastDiseaseSample.cropHint);
        } else if (lastUploadedLeafFile) {
            uploadLeafForDiagnosis(lastUploadedLeafFile);
        } else if (lastDiseaseData) {
            renderDiseaseDiagnosisResult(lastDiseaseData);
        }

        const tt = TERRACE_I18N[lang] || TERRACE_I18N.en;
        const setTxt = (id, val) => { const el = document.getElementById(id); if (el && val) el.textContent = val; };
        setTxt("navTerraceLabel", tt.navLabel);
        setTxt("terraceHeroTag", tt.heroTag);
        setTxt("terracePlanTitle", tt.planTitle);
        setTxt("terracePlanSubtitle", tt.planSubtitle);
        setTxt("terracePresetLabel", tt.presetLabel);
        setTxt("lblTerraceLoc", tt.locLabel);
        setTxt("lblTerraceLen", tt.lenLabel);
        setTxt("lblTerraceWid", tt.widLabel);
        setTxt("lblTerraceSun", tt.sunLabel);
        setTxt("lblTerraceSpace", tt.spaceLabel);
        setTxt("lblTerraceGoal", tt.goalLabel);
        setTxt("calcTerraceBtnLabel", tt.calcBtn);
        setTxt("terraceCoachTitle", tt.coachTitle);
        setTxt("terraceCoachSubtitle", tt.coachSubtitle);
        setTxt("learnCropBtnLabel", tt.learnBtn);
        const tLocEl = document.getElementById("terraceLoc");
        if (tLocEl) tLocEl.placeholder = tt.locPh;
        const tCustomEl = document.getElementById("terraceCustomCrop");
        if (tCustomEl) tCustomEl.placeholder = tt.customPh;

        if (lastTerracePlanParams) {
            fetchTerracePlan(lastTerracePlanParams);
        } else {
            renderTerracePlanPrompt();
        }
        if (lastTerraceGuideCrop) {
            fetchTerraceCropGuide(lastTerraceGuideCrop);
        } else {
            renderTerraceGuidePrompt();
        }

        const placeholders = {
            "kn": "ಕೇಳಿ (ಉದಾ: ಕೋಲಾರದಲ್ಲಿ ಟೊಮೆಟೊ ಮಂಡಿ ದರ ಎಷ್ಟಿದೆ?)...",
            "hi": "पूछें (जैसे: क्या आज बारिश होगी? क्या मुझे खेत में सिंचाई करनी चाहिए?)...",
            "en": "Ask (e.g. Check weather, soil moisture & tomato price in Kolar)...",
            "ta": "கேளுங்கள் (எ.கா: இன்றைய தக்காளி சந்தை விலை என்ன?)...",
            "te": "అడగండి (ఉదా: ఈరోజు వర్షం పడుతుందా? సాగునీరు పెట్టవచ్చా?)...",
            "mr": "विचारा (उदा: आज पाऊस पडेल का? टोमॅटोचा बाजारभाव काय आहे?)..."
        };
        if (queryInput) queryInput.placeholder = placeholders[lang] || placeholders["en"];
        if (detectedLangTag) detectedLangTag.textContent = lang + "-IN";
    }

    updateLanguagePlaceholder(currentLang);

    // TTS Toggle Button
    if (ttsToggleBtn) {
        ttsToggleBtn.addEventListener("click", () => {
            isTTSActive = !isTTSActive;
            if (isTTSActive) {
                ttsToggleBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition";
                ttsIcon.className = "fa-solid fa-volume-high";
                ttsLabel.textContent = "Voice Audio: ON";
            } else {
                ttsToggleBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-stone-100 text-stone-500 border border-stone-300 hover:bg-stone-200 transition";
                ttsIcon.className = "fa-solid fa-volume-xmark";
                ttsLabel.textContent = "Voice Audio: OFF";
                stopCurrentAudio();
            }
        });
    }

    let activeSpeakBtn = null;
    let activeAudioUrl = null;

    function resetActiveSpeakBtn() {
        if (activeSpeakBtn) {
            const orig = activeSpeakBtn.getAttribute("data-orig-label");
            if (orig) {
                activeSpeakBtn.innerHTML = `<i class="fa-solid fa-volume-high text-[11px]"></i><span>${escapeHtml(orig)}</span>`;
            }
            activeSpeakBtn = null;
        }
        if (activeAudioUrl) {
            try { URL.revokeObjectURL(activeAudioUrl); } catch (_) {}
            activeAudioUrl = null;
        }
    }

    function stopCurrentAudio() {
        if (currentAudioPlayer) {
            currentAudioPlayer.pause();
            currentAudioPlayer = null;
        }
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        resetActiveSpeakBtn();
    }

    // Connect Initial Welcome Message listen button
    document.querySelectorAll(".speak-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const txt = btn.getAttribute("data-text");
            speakText(txt, currentLang, btn);
        });
    });

    // Native Regional Audio Speech Player - Streams 100% Complete Concatenated MP3
    function speakText(text, lang = "en", triggerBtn = null) {
        if (!text) return;

        // If user clicked the same button while it is currently playing, stop playback
        if (triggerBtn && activeSpeakBtn === triggerBtn && (currentAudioPlayer || (window.speechSynthesis && window.speechSynthesis.speaking))) {
            stopCurrentAudio();
            return;
        }

        if (!isTTSActive && !triggerBtn) return;
        stopCurrentAudio();

        const rangeConnectors = {
            "kn": "$1 ರಿಂದ $2",
            "hi": "$1 से $2",
            "en": "$1 to $2",
            "ta": "$1 முதல் $2",
            "te": "$1 నుండి $2",
            "mr": "$1 ते $2"
        };
        const rangeRepl = rangeConnectors[lang] || "$1 to $2";
        const sanitizedText = text.replace(/(\d+)\s*[-–—]\s*(\d+)/g, rangeRepl);
        const cleanText = sanitizedText.replace(/[*#_`•]/g, " ").replace(/\s+/g, " ").trim();
        if (!cleanText) return;

        if (triggerBtn) {
            if (!triggerBtn.getAttribute("data-orig-label")) {
                triggerBtn.setAttribute("data-orig-label", triggerBtn.textContent.trim());
            }
            activeSpeakBtn = triggerBtn;
            triggerBtn.innerHTML = `<i class="fa-solid fa-stop text-[11px] text-red-600"></i><span>Stop Audio</span>`;
        }

        fetch("/api/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: cleanText, lang: lang })
        })
        .then(res => {
            if (!res.ok) throw new Error("TTS fallback");
            const ct = res.headers.get("content-type") || "";
            if (!ct.includes("audio")) throw new Error("Not audio");
            return res.blob();
        })
        .then(blob => {
            if (!isTTSActive && !triggerBtn) {
                resetActiveSpeakBtn();
                return;
            }
            const objUrl = URL.createObjectURL(blob);
            activeAudioUrl = objUrl;
            const audio = new Audio(objUrl);
            currentAudioPlayer = audio;
            audio.onended = () => {
                currentAudioPlayer = null;
                resetActiveSpeakBtn();
            };
            audio.onerror = () => {
                currentAudioPlayer = null;
                playWebSpeechFallback(cleanText, lang);
            };
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise.catch(() => {
                    currentAudioPlayer = null;
                    playWebSpeechFallback(cleanText, lang);
                });
            }
        })
        .catch(() => {
            playWebSpeechFallback(cleanText, lang);
        });
    }

    function playWebSpeechFallback(text, lang) {
        if (!window.speechSynthesis) {
            resetActiveSpeakBtn();
            return;
        }
        const langMap = {
            "kn": "kn-IN", "hi": "hi-IN", "ta": "ta-IN",
            "te": "te-IN", "mr": "mr-IN", "en": "en-IN"
        };
        const targetLangCode = langMap[lang] || "en-IN";
        const voices = window.speechSynthesis.getVoices() || [];
        const matched = voices.find(v => v.lang.toLowerCase().startsWith(lang) || v.lang.toLowerCase().replace("_", "-").includes(targetLangCode.toLowerCase()));

        // Chunk WebSpeech utterances cleanly by sentence without breaking decimal points
        const sentences = text.split(/(?:(?<!\d)\.(?!\d)|[!?।\n])+/).map(s => s.trim()).filter(Boolean);
        if (!sentences.length) {
            resetActiveSpeakBtn();
            return;
        }
        sentences.forEach((sent, idx) => {
            const u = new SpeechSynthesisUtterance(sent);
            u.lang = targetLangCode;
            u.rate = 0.95;
            if (matched) u.voice = matched;
            if (idx === sentences.length - 1) {
                u.onend = () => resetActiveSpeakBtn();
                u.onerror = () => resetActiveSpeakBtn();
            }
            window.speechSynthesis.speak(u);
        });
    }

    // Pre-cache voices when available
    if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = () => {
            window.speechSynthesis.getVoices();
        };
    }

    // ==========================================
    // MAIN ADVISOR VOICE RECOGNITION
    // ==========================================
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;

        recognition.onstart = () => {
            isRecording = true;
            if (micBtn) micBtn.classList.add("recording-pulse");
            if (voiceStatus) {
                voiceStatus.classList.remove("hidden");
                voiceStatus.classList.add("flex");
            }
            if (voiceStatusText) {
                voiceStatusText.textContent = `Listening in ${currentLang === 'kn' ? 'ಕನ್ನಡ (Kannada)' : (currentLang === 'hi' ? 'हिंदी (Hindi)' : 'English')}... Speak now`;
            }
        };

        recognition.onresult = (event) => {
            let transcript = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            if (queryInput) queryInput.value = transcript;
        };

        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            stopRecording();
            if (voiceStatusText) voiceStatusText.textContent = "Microphone error: " + event.error;
            setTimeout(() => { if (voiceStatus) voiceStatus.classList.add("hidden"); }, 3000);
        };

        recognition.onend = () => {
            stopRecording();
            if (queryInput && queryInput.value.trim().length > 0) {
                submitQuery(queryInput.value.trim());
            }
        };
    }

    function toggleRecording() {
        if (!recognition) {
            alert("Web Speech recognition is not supported in this browser. Please type in the input box.");
            return;
        }
        if (isRecording) {
            recognition.stop();
            stopRecording();
        } else {
            const langCodes = { "kn": "kn-IN", "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN", "mr": "mr-IN", "en": "en-IN" };
            recognition.lang = langCodes[currentLang] || "kn-IN";
            try {
                recognition.start();
            } catch (err) {
                console.error("Recording error:", err);
            }
        }
    }

    function stopRecording() {
        isRecording = false;
        if (micBtn) micBtn.classList.remove("recording-pulse");
        if (voiceStatus) voiceStatus.classList.add("hidden");
    }

    if (micBtn) micBtn.addEventListener("click", toggleRecording);

    // Query Submission
    if (sendBtn) {
        sendBtn.addEventListener("click", () => {
            const text = queryInput.value.trim();
            if (text) submitQuery(text);
        });
    }

    if (queryInput) {
        queryInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                const text = queryInput.value.trim();
                if (text) submitQuery(text);
            }
        });
    }

    // Quick Inquiry Prompt Buttons
    document.querySelectorAll(".sample-prompt-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const q = btn.getAttribute("data-query");
            const l = btn.getAttribute("data-lang");
            if (langSelect) langSelect.value = l;
            currentLang = l;
            updateLanguagePlaceholder(l);
            if (queryInput) queryInput.value = q;
            submitQuery(q);
        });
    });

    function submitQuery(queryText, attachedImage = null) {
        if (queryInput) queryInput.value = "";
        appendUserMessage(queryText);

        const loadingId = appendAgentLoadingMessage();

        fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: queryText,
                language: currentLang,
                image_path: attachedImage
            })
        })
        .then(res => res.json())
        .then(data => {
            removeMessage(loadingId);
            if (data.status === "success") {
                const listenBtn = appendAgentResponse(data);
                if (isTTSActive && (data.speech_text || data.response_text)) {
                    speakText(data.speech_text || data.response_text, currentLang, listenBtn);
                }
            } else {
                appendErrorMessage(data.message || "Failed to process query.");
            }
        })
        .catch(err => {
            removeMessage(loadingId);
            appendErrorMessage("Connection error while communicating with FasalSaarathi.");
            console.error(err);
        });
    }

    function appendUserMessage(text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "flex items-start justify-end space-x-3";
        msgDiv.innerHTML = `
            <div class="bg-emerald-700 rounded-xl rounded-tr-none p-3.5 max-w-[85%] text-white text-sm shadow-sm">
                <p class="leading-relaxed font-medium">${escapeHtml(text)}</p>
                <div class="text-[11px] text-emerald-100/80 text-right pt-1">You</div>
            </div>
            <div class="w-8 h-8 rounded-lg bg-stone-200 text-stone-700 flex items-center justify-center text-sm font-bold shrink-0">
                <i class="fa-solid fa-user"></i>
            </div>
        `;
        if (chatMessages) {
            chatMessages.appendChild(msgDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function appendAgentLoadingMessage() {
        const id = "loading-" + Date.now();
        const msgDiv = document.createElement("div");
        msgDiv.id = id;
        msgDiv.className = "flex items-start space-x-3";
        msgDiv.innerHTML = `
            <div class="w-8 h-8 rounded-lg bg-emerald-700 text-white flex items-center justify-center text-sm font-bold shrink-0">
                <i class="fa-solid fa-seedling"></i>
            </div>
            <div class="bg-white border border-[#d4e6da] rounded-xl rounded-tl-none p-3 max-w-[85%] text-stone-600 text-xs flex items-center space-x-2 shadow-sm">
                <i class="fa-solid fa-spinner fa-spin text-emerald-800"></i>
                <span>Analyzing query &amp; fetching farm data...</span>
            </div>
        `;
        if (chatMessages) {
            chatMessages.appendChild(msgDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        return id;
    }

    function appendAgentResponse(data) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "flex items-start space-x-3";

        let formattedText = data.response_text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/^\*\s+/gm, '• ')
            .replace(/\n/g, '<br>');

        msgDiv.innerHTML = `
            <div class="w-8 h-8 rounded-lg bg-emerald-700 text-white flex items-center justify-center text-sm font-bold shrink-0">
                <i class="fa-solid fa-seedling"></i>
            </div>
            <div class="bg-white border border-[#d4e6da] rounded-xl rounded-tl-none p-4 max-w-[85%] space-y-2.5 shadow-sm">
                <div class="text-sm leading-relaxed text-stone-800">${formattedText}</div>
                <div class="flex flex-wrap items-center justify-start gap-2 pt-2 border-t border-[#e2efe7]">
                    <button class="speak-this-btn text-xs px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200 transition flex items-center space-x-1.5 font-semibold">
                        <i class="fa-solid fa-volume-high text-[11px]"></i>
                        <span>Listen Aloud (${escapeHtml(data.language_name)})</span>
                    </button>
                </div>
            </div>
        `;

        const btn = msgDiv.querySelector(".speak-this-btn");
        btn.addEventListener("click", () => {
            speakText(data.speech_text || data.response_text, data.language || currentLang, btn);
        });

        if (chatMessages) {
            chatMessages.appendChild(msgDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        return btn;
    }

    function appendErrorMessage(errorText) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "flex items-start space-x-3";
        msgDiv.innerHTML = `
            <div class="w-8 h-8 rounded-lg bg-red-600 text-white flex items-center justify-center text-sm font-bold shrink-0">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
            <div class="bg-red-50 border border-red-200 rounded-xl rounded-tl-none p-3 max-w-[85%] text-red-800 text-xs">
                ${escapeHtml(errorText)}
            </div>
        `;
        if (chatMessages) {
            chatMessages.appendChild(msgDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function removeMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    if (clearChatBtn) {
        clearChatBtn.addEventListener("click", () => {
            if (chatMessages) chatMessages.innerHTML = "";
        });
    }

    // Tab Navigation Logic
    const navTabs = document.querySelectorAll(".nav-tab");
    const tabPanes = document.querySelectorAll(".tab-pane");

    navTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            navTabs.forEach(t => {
                t.classList.remove("active");
                t.classList.add("text-slate-400");
            });
            tabPanes.forEach(p => p.classList.add("hidden"));

            tab.classList.add("active");
            tab.classList.remove("text-slate-400");
            const targetId = tab.getAttribute("data-target");
            const targetPane = document.getElementById(targetId);
            if (targetPane) targetPane.classList.remove("hidden");
        });
    });

    // ==========================================
    // LEAF VISION DOCTOR LOGIC
    // ==========================================
    const sampleLeafCards = document.querySelectorAll(".sample-leaf-card");
    const diseaseResultPanel = document.getElementById("diseaseResultPanel");
    const leafFileInput = document.getElementById("leafFileInput");

    sampleLeafCards.forEach(card => {
        card.addEventListener("click", () => {
            const sample = card.getAttribute("data-sample");
            const crop = card.getAttribute("data-crop");
            runSampleLeafDiagnosis(sample, crop);
        });
    });

    function uploadLeafForDiagnosis(file) {
        if (!file) return;
        lastUploadedLeafFile = file;
        lastDiseaseSample = null;
        const selectedCrop = (document.getElementById("leafCropHint")?.value || "").trim();
        const dt = DISEASE_I18N[currentLang] || DISEASE_I18N.en;
        const formData = new FormData();
        formData.append("file", file);
        formData.append("crop_hint", selectedCrop);
        formData.append("language", currentLang);

        if (diseaseResultPanel) {
            diseaseResultPanel.innerHTML = `
                <div class="flex items-center space-x-2 text-xs text-emerald-800 py-3 font-medium">
                    <i class="fa-solid fa-spinner fa-spin"></i>
                    <span>${escapeHtml(dt.scanning)}</span>
                </div>
            `;
        }

        fetch("/api/upload-leaf", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(renderDiseaseDiagnosisResult)
        .catch(err => {
            if (diseaseResultPanel) diseaseResultPanel.innerHTML = `<div class="text-xs text-red-700 font-medium">${escapeHtml(err.message)}</div>`;
        });
    }

    if (leafFileInput) {
        leafFileInput.addEventListener("change", (e) => {
            if (!e.target.files.length) return;
            uploadLeafForDiagnosis(e.target.files[0]);
        });
    }

    function runSampleLeafDiagnosis(sampleName, cropHint) {
        lastDiseaseSample = { sampleName, cropHint };
        lastUploadedLeafFile = null;
        const dt = DISEASE_I18N[currentLang] || DISEASE_I18N.en;
        if (diseaseResultPanel) {
            diseaseResultPanel.innerHTML = `
                <div class="flex items-center space-x-2 text-xs text-emerald-800 py-3 font-medium">
                    <i class="fa-solid fa-spinner fa-spin"></i>
                    <span>${escapeHtml(dt.scanning)}</span>
                </div>
            `;
        }

        fetch("/api/diagnose-sample", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sample_name: sampleName, crop_hint: cropHint, language: currentLang })
        })
        .then(res => res.json())
        .then(renderDiseaseDiagnosisResult)
        .catch(err => {
            if (diseaseResultPanel) diseaseResultPanel.innerHTML = `<div class="text-xs text-red-700">Diagnosis failed: ${escapeHtml(err.message)}</div>`;
        });
    }

    function renderDiseaseDiagnosisResult(data) {
        if (!diseaseResultPanel) return;
        lastDiseaseData = data;
        if (data.status !== "success") {
            diseaseResultPanel.innerHTML = `
                <div class="p-4 rounded-xl bg-amber-50 border border-amber-300 text-xs text-amber-900 flex items-start gap-2.5 leading-relaxed">
                    <i class="fa-solid fa-circle-exclamation text-amber-700 text-base mt-0.5"></i>
                    <div>${escapeHtml(data.message || "Please upload a clear close-up photo of a crop leaf.")}</div>
                </div>
            `;
            return;
        }

        const dt = DISEASE_I18N[currentLang] || DISEASE_I18N.en;
        let modeBadge = "";
        if (data.analysis_mode === "gemini_multimodal_vision") {
            modeBadge = `<span class="text-xs px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold"><i class="fa-solid fa-cloud mr-1"></i>${escapeHtml(dt.aiBadge)}</span>`;
        } else if (data.analysis_mode === "local_pytorch_cnn") {
            modeBadge = `<span class="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200 font-semibold"><i class="fa-solid fa-microchip mr-1"></i>${escapeHtml(dt.offlineCnnBadge)}</span>`;
        } else {
            modeBadge = `<span class="text-xs px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">${escapeHtml(dt.fbBadge)}</span>`;
        }

        const sevCode = data.severity_code || (data.is_healthy ? "none" : "medium");
        const sevClasses = sevCode === "none"
            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
            : (sevCode === "serious" ? "bg-red-50 text-red-800 border-red-200" : "bg-amber-50 text-amber-900 border-amber-200");

        const dName = data.disease_name || "";
        const causeSimple = data.cause_simple || "";
        const symp = data.symptoms_identified || "";
        const org = data.organic_prescription || "";
        const chem = data.chemical_prescription || "";
        const damagedPct = data.visual_metrics && typeof data.visual_metrics.damaged_leaf_area_pct === "number"
            ? data.visual_metrics.damaged_leaf_area_pct
            : null;

        diseaseResultPanel.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-12 gap-5">
                <div class="md:col-span-4 flex flex-col items-center">
                    <img src="${data.image_url}" alt="Leaf Image" class="w-full h-44 object-cover rounded-xl border border-[#d4e6da] shadow-sm">
                    <div class="mt-2.5 text-center w-full space-y-1.5">
                        <span class="text-xs font-bold text-emerald-800">${escapeHtml(dt.conf)}: ${data.confidence_score}%</span>
                        <div class="w-40 bg-stone-200 rounded-full h-2 mx-auto overflow-hidden">
                            <div class="bg-emerald-700 h-2" style="width: ${data.confidence_score}%"></div>
                        </div>
                        ${damagedPct !== null ? `<div class="text-xs font-semibold text-stone-700">${escapeHtml(dt.area)}: <span class="text-amber-900 font-bold">${damagedPct}%</span></div>` : ""}
                    </div>
                </div>
                <div class="md:col-span-8 space-y-3">
                    <div class="flex flex-wrap items-start justify-between gap-2 border-b border-[#d4e6da] pb-2.5">
                        <div class="space-y-0.5">
                            <h3 class="text-base font-bold text-stone-900">${escapeHtml(dName)}</h3>
                            ${causeSimple ? `<div class="text-xs text-stone-600 font-medium"><strong class="text-stone-800">${escapeHtml(dt.cause)}:</strong> ${escapeHtml(causeSimple)}</div>` : ""}
                        </div>
                        <div class="flex flex-wrap items-center gap-2">
                            ${modeBadge}
                            <span class="text-xs px-2.5 py-1 rounded-full font-semibold border ${sevClasses}">
                                ${escapeHtml(dt.sev)}: ${escapeHtml(data.severity_level)}
                            </span>
                        </div>
                    </div>

                    <div class="text-xs text-stone-700 leading-relaxed">
                        <strong class="text-stone-900">${escapeHtml(dt.symp)}:</strong> ${escapeHtml(symp)}
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 space-y-1">
                            <div class="font-bold text-emerald-800 flex items-center space-x-1.5">
                                <i class="fa-solid fa-seedling"></i>
                                <span>${escapeHtml(dt.org)}:</span>
                            </div>
                            <div class="text-stone-700 leading-relaxed">${escapeHtml(org)}</div>
                        </div>
                        <div class="p-3 rounded-xl bg-sky-50 border border-sky-200 space-y-1">
                            <div class="font-bold text-sky-900 flex items-center space-x-1.5">
                                <i class="fa-solid fa-flask"></i>
                                <span>${escapeHtml(dt.chem)}:</span>
                            </div>
                            <div class="text-stone-700 leading-relaxed">${escapeHtml(chem)}</div>
                        </div>
                    </div>

                    <div class="text-xs text-amber-900 bg-amber-50 p-3 rounded-xl border border-amber-200 leading-relaxed">
                        <i class="fa-solid fa-list-check mr-1 text-amber-700"></i>
                        <strong>${escapeHtml(dt.proto)}:</strong> ${escapeHtml(data.application_protocol)}
                        ${data.disclaimer ? `<div class="mt-1 text-stone-600">${escapeHtml(data.disclaimer)}</div>` : ""}
                    </div>
                </div>
            </div>
        `;
    }

    // ==========================================
    // ==========================================
    // LIVE TOOL EXPLORER LOGIC (Visual Cards, Multilingual)
    // ==========================================
    function renderSourceBadge(badgeEl, isLive, fallbackText) {
        if (!badgeEl) return;
        const t = getToolT(currentLang);
        if (isLive) {
            badgeEl.className = "text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 inline-flex items-center gap-1.5 whitespace-nowrap shrink-0";
            badgeEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-600"></span><span>${escapeHtml(t.live)}</span>`;
        } else {
            badgeEl.className = "text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200 whitespace-nowrap shrink-0";
            badgeEl.textContent = fallbackText || t.benchmark;
        }
    }

    function renderCardFooter(sourceLabel, lastUpdated) {
        return `
            <div class="mt-auto pt-3 border-t border-[#d4e6da] flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500">
                <span class="truncate">${escapeHtml(sourceLabel)}</span>
                <span class="whitespace-nowrap">🕒 ${escapeHtml(lastUpdated || "Just now")}</span>
            </div>
        `;
    }

    function renderWeatherPrompt() {
        const t = getToolT(currentLang);
        const box = document.getElementById("toolWeatherOutput");
        const badge = document.getElementById("weatherSourceBadge");
        if (!box) return;
        if (badge) {
            badge.className = "text-xs font-semibold px-2.5 py-1 rounded-full bg-sky-50 text-sky-800 border border-sky-200 whitespace-nowrap shrink-0";
            badge.textContent = t.ready;
        }
        box.innerHTML = `
            <div class="flex-1 flex flex-col items-center justify-center bg-[#f7fbf8] rounded-xl border border-[#d4e6da] p-5 text-center space-y-2.5">
                <div class="w-10 h-10 rounded-full bg-sky-100 text-sky-700 flex items-center justify-center text-base">
                    <i class="fa-solid fa-cloud-sun-rain"></i>
                </div>
                <p class="text-xs text-stone-600 leading-relaxed">${escapeHtml(t.enterLocPrompt)}</p>
            </div>
        `;
    }

    function renderWeatherCard(d) {
        lastWeatherData = d;
        const t = getToolT(currentLang);
        const box = document.getElementById("toolWeatherOutput");
        const badge = document.getElementById("weatherSourceBadge");
        if (!box) return;

        // Handle honest non-telemetry states (zero fabricated numbers)
        if (!d || (d.status !== "success" && d.status !== "cached_real")) {
            const st = d ? d.status : "error";
            if (badge) {
                badge.className = "text-xs font-semibold px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200 whitespace-nowrap shrink-0";
                badge.textContent = st === "service_unavailable" ? t.offline : "ALERT";
            }
            const msg = st === "location_not_found"
                ? t.locNotFound
                : (st === "missing_location" ? t.enterLocPrompt : (d?.message || t.weatherOffline));
            box.innerHTML = `
                <div class="flex-1 flex flex-col justify-center bg-amber-50/70 rounded-xl border border-amber-200 p-4 text-xs text-amber-900 space-y-2">
                    <div class="font-bold flex items-center gap-1.5">
                        <i class="fa-solid fa-triangle-exclamation text-amber-600"></i>
                        <span>${escapeHtml(d?.requested_location || d?.display_location || t.weatherTitle)}</span>
                    </div>
                    <p class="leading-relaxed">${escapeHtml(msg)}</p>
                </div>
            `;
            return;
        }

        const isLive = d.is_live_data === true;
        renderSourceBadge(badge, isLive, t.cached);

        const locLabel = d.display_location || d.location || "";
        const coords = d.coordinates ? `${d.coordinates.latitude}°, ${d.coordinates.longitude}°` : "";
        const rainToday = d.rain_today_probability_pct ?? 0;
        const rainTom = d.rain_tomorrow_probability_pct ?? 0;
        const irrCode = d.irrigation_code || "";
        const irrRaw = d.irrigation_action || "";
        const skipIrr = irrCode === "DO_NOT_IRRIGATE" || irrCode === "DELAY_IRRIGATION" || irrRaw.startsWith("Do not water") || irrRaw.startsWith("Hold off");
        const irrDisplay = currentLang === "en" ? translateToolStatus(irrRaw, "en") : translateToolStatus(irrCode || irrRaw, currentLang);

        const sprayCode = d.spray_code || "";
        const sprayRaw = d.spray_action || "";
        const safeSpray = d.safe_to_spray_now === true;
        const sprayDisplay = currentLang === "en" ? translateToolStatus(sprayRaw, "en") : translateToolStatus(sprayCode || sprayRaw, currentLang);

        const daily7d = Array.isArray(d.daily_forecast) ? d.daily_forecast : [];
        const forecastRows = daily7d.map(day => `
            <tr class="border-t border-[#d4e6da]">
                <td class="py-1.5 pr-2 font-medium text-stone-700 whitespace-nowrap">${escapeHtml(day.day_label || day.date)}</td>
                <td class="py-1.5 px-1 text-stone-800 whitespace-nowrap">${day.temp_min_c ?? "--"}°–<b>${day.temp_max_c ?? "--"}°</b></td>
                <td class="py-1.5 px-1 text-sky-700 font-semibold whitespace-nowrap">${day.rain_prob_pct ?? 0}% (${day.rain_mm ?? 0}mm)</td>
                <td class="py-1.5 pl-1 text-right text-stone-500 whitespace-nowrap">${day.et0_mm != null ? day.et0_mm + "mm" : "--"}</td>
            </tr>
        `).join("");

        box.innerHTML = `
            <div class="flex-1 flex flex-col bg-[#f7fbf8] rounded-xl border border-[#d4e6da] p-4 space-y-3.5">
                <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                        <div class="text-xs font-bold text-sky-900 uppercase tracking-wide truncate" title="${escapeHtml(locLabel)}">${escapeHtml(locLabel)}</div>
                        ${coords ? `<div class="text-[11px] text-stone-400">${escapeHtml(d.weather_condition || "")} • ${escapeHtml(coords)}</div>` : ""}
                        <div class="text-3xl font-extrabold text-stone-900 mt-1">${d.current_temperature_c ?? "--"}°C</div>
                        ${d.feels_like_c != null ? `<div class="text-[11px] text-stone-500">${escapeHtml(t.feelsLike)}: ${d.feels_like_c}°C</div>` : ""}
                    </div>
                    <div class="text-right space-y-1 text-xs text-stone-600 shrink-0">
                        <div>💧 ${escapeHtml(t.humidity)}: <b class="text-stone-900">${d.humidity_pct ?? "--"}%</b></div>
                        <div>💨 ${escapeHtml(t.wind)}: <b class="text-stone-900">${d.wind_speed_kmh ?? "--"} km/h</b></div>
                        ${d.et0_today_mm != null ? `<div>☀️ ${escapeHtml(t.et0Label)}: <b class="text-stone-900">${d.et0_today_mm} mm</b></div>` : ""}
                        ${d.topsoil_moisture_pct != null ? `<div>🌱 ${escapeHtml(t.soilMoist)}: <b class="text-emerald-800">${d.topsoil_moisture_pct}%</b></div>` : ""}
                    </div>
                </div>

                <div class="space-y-2.5 pt-2.5 border-t border-[#d4e6da]">
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-stone-600">${escapeHtml(t.rainToday)} (${d.rain_today_mm ?? 0} mm)</span>
                            <span class="font-bold text-sky-700">${rainToday}%</span>
                        </div>
                        <div class="w-full bg-stone-200 rounded-full h-2">
                            <div class="bg-sky-600 h-2 rounded-full" style="width:${Math.min(100, rainToday)}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-stone-600">${escapeHtml(t.rainTom)} (${d.rain_tomorrow_mm ?? 0} mm)</span>
                            <span class="font-bold text-sky-700">${rainTom}%</span>
                        </div>
                        <div class="w-full bg-stone-200 rounded-full h-2">
                            <div class="bg-sky-500 h-2 rounded-full" style="width:${Math.min(100, rainTom)}%"></div>
                        </div>
                    </div>
                </div>

                <div class="p-2.5 rounded-xl text-xs leading-relaxed ${skipIrr ? "bg-amber-50 border border-amber-200 text-amber-900" : "bg-emerald-50 border border-emerald-200 text-emerald-800"}">
                    <div class="font-bold mb-0.5">💧 ${escapeHtml(t.irrTitle)}</div>
                    <div>${escapeHtml(irrDisplay)}</div>
                </div>

                ${sprayDisplay ? `
                <div class="p-2.5 rounded-xl text-xs leading-relaxed ${safeSpray ? "bg-sky-50 border border-sky-200 text-sky-900" : "bg-rose-50 border border-rose-200 text-rose-900"}">
                    <div class="font-bold mb-0.5">🚿 ${escapeHtml(t.sprayTitle)}</div>
                    <div>${escapeHtml(sprayDisplay)}</div>
                </div>` : ""}

                ${forecastRows ? `
                <details class="bg-white rounded-xl border border-[#d4e6da] px-3 py-2 text-xs">
                    <summary class="cursor-pointer font-bold text-sky-900 select-none flex items-center justify-between">
                        <span>📅 ${escapeHtml(t.forecast7d)}</span>
                        <span class="text-stone-400 text-[11px]">▼</span>
                    </summary>
                    <div class="mt-2 overflow-x-auto">
                        <table class="w-full text-[11px] text-left">
                            <thead class="text-stone-400 uppercase">
                                <tr>
                                    <th class="pb-1">Day</th>
                                    <th class="pb-1">Temp</th>
                                    <th class="pb-1">Rain</th>
                                    <th class="pb-1 text-right">Sun Loss</th>
                                </tr>
                            </thead>
                            <tbody>${forecastRows}</tbody>
                        </table>
                    </div>
                </details>` : ""}

                ${renderCardFooter(isLive ? t.srcLive : (d.data_source_label || t.cached), d.last_updated)}
            </div>
        `;
    }

    function renderSoilPrompt() {
        const t = getToolT(currentLang);
        const box = document.getElementById("toolSoilOutput");
        const badge = document.getElementById("soilSourceBadge");
        if (!box) return;
        if (badge) {
            badge.className = "text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 whitespace-nowrap shrink-0";
            badge.textContent = t.ready;
        }
        box.innerHTML = `
            <div class="flex-1 flex flex-col items-center justify-center bg-[#f7fbf8] rounded-xl border border-[#d4e6da] p-5 text-center space-y-2.5">
                <div class="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-base">
                    <i class="fa-solid fa-seedling"></i>
                </div>
                <p class="text-xs text-stone-600 leading-relaxed">${escapeHtml(t.enterLocPrompt)}</p>
            </div>
        `;
    }

    function renderSoilCard(d) {
        lastSoilData = d;
        const t = getToolT(currentLang);
        const box = document.getElementById("toolSoilOutput");
        const badge = document.getElementById("soilSourceBadge");
        if (!box) return;

        if (!d || (d.status !== "success" && d.status !== "cached_real")) {
            const st = d ? d.status : "error";
            if (badge) {
                badge.className = "text-xs font-semibold px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200 whitespace-nowrap shrink-0";
                badge.textContent = st === "service_unavailable" ? t.offline : "ALERT";
            }
            const msg = st === "location_not_found"
                ? t.locNotFound
                : (st === "missing_location" ? t.enterLocPrompt : (d?.message || t.weatherOffline));
            box.innerHTML = `
                <div class="flex-1 flex flex-col justify-center bg-amber-50/70 rounded-xl border border-amber-200 p-4 text-xs text-amber-900 space-y-2">
                    <div class="font-bold flex items-center gap-1.5">
                        <i class="fa-solid fa-triangle-exclamation text-amber-600"></i>
                        <span>${escapeHtml(d?.requested_location || d?.district || t.soilTitle)}</span>
                    </div>
                    <p class="leading-relaxed">${escapeHtml(msg)}</p>
                </div>
            `;
            return;
        }

        const isLive = d.is_live_data === true;
        renderSourceBadge(badge, isLive, t.cached);

        const moist = d.moisture_percentage ?? 0;
        const nut = d.nutrients || {};
        const tex = d.texture || {};
        const depths = d.root_depths_moisture_pct || {};
        const sTemps = d.soil_temperatures_c || {};
        const amends = Array.isArray(d.soil_amendments) ? d.soil_amendments : [];

        const moistFriendly = currentLang === "en"
            ? (d.moisture_label || translateToolStatus(d.moisture_status || "", "en"))
            : translateToolStatus(d.moisture_status || "", currentLang);

        const phWord = d.ph_simple || (d.ph != null ? (d.ph < 6.0 ? "Acidic" : (d.ph <= 7.5 ? "Balanced" : "Alkaline")) : "");
        const nVal = translateToolStatus(nut.nitrogen_status || "--", currentLang);
        const pRaw = (nut.phosphorus_status || "--").split("(")[0].trim();
        const pVal = translateToolStatus(pRaw, currentLang);
        const kRaw = (nut.potassium_status || "--").split("(")[0].trim();
        const kVal = translateToolStatus(kRaw, currentLang);
        const ocWord = nut.organic_carbon_label || (nut.organic_carbon_pct != null ? (nut.organic_carbon_pct < 0.5 ? "Low" : (nut.organic_carbon_pct <= 0.75 ? "Good" : "Rich")) : "");

        const irrSoilDisplay = currentLang === "en"
            ? translateToolStatus(d.irrigation_guidance || "", "en")
            : translateToolStatus(d.moisture_status || "", currentLang);
        const amendItems = (currentLang === "en" ? amends.slice(0, 2) : []).map(a => translateToolStatus(a, "en")).filter(Boolean);
        const isMoistWarn = d.moisture_status === "CRITICAL_DEFICIT" || d.moisture_status === "SATURATED_SOIL";

        box.innerHTML = `
            <div class="flex-1 flex flex-col bg-[#f7fbf8] rounded-xl border border-[#d4e6da] p-4 space-y-3.5">
                <div class="space-y-1">
                    <div class="flex flex-wrap items-center justify-between gap-1.5">
                        <div class="text-xs font-bold text-emerald-900 uppercase tracking-wide truncate min-w-0" title="${escapeHtml(d.district || "")}">${escapeHtml(d.district || "")}</div>
                        <span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-white text-emerald-800 border border-[#d4e6da] whitespace-nowrap shrink-0">
                            ${phWord ? `${escapeHtml(phWord)} (pH ${d.ph ?? "--"})` : `pH ${d.ph ?? "--"}`}
                        </span>
                    </div>
                    <div class="text-sm font-extrabold text-emerald-800">${escapeHtml(d.soil_type || "")}</div>
                    <div class="text-[11px] text-stone-500 leading-snug">${escapeHtml(d.crop || "")} • ${escapeHtml(d.active_root_depth || "")}</div>
                </div>

                <div>
                    <div class="flex justify-between items-baseline gap-2 text-xs mb-1">
                        <span class="text-stone-700 font-semibold">${escapeHtml(moistFriendly)}</span>
                        <span class="font-extrabold text-emerald-800 whitespace-nowrap">${moist}%</span>
                    </div>
                    <div class="w-full bg-stone-200 rounded-full h-2">
                        <div class="${isMoistWarn ? "bg-amber-600" : "bg-[#2d6a4f]"} h-2 rounded-full" style="width:${Math.min(100, Math.round((moist / 50) * 100))}%"></div>
                    </div>
                    ${tex.field_capacity_pct != null ? `<div class="text-[11px] text-stone-500 mt-1">${escapeHtml(t.healthyRange)}: <b>${tex.wilting_point_pct}% – ${tex.field_capacity_pct}%</b></div>` : ""}
                </div>

                ${irrSoilDisplay ? `
                <div class="p-2.5 rounded-xl text-xs leading-relaxed ${isMoistWarn ? "bg-amber-50 border border-amber-200 text-amber-900" : "bg-sky-50 border border-sky-200 text-sky-900"}">
                    <div class="font-bold mb-0.5">💧 ${escapeHtml(t.irrTitle)}</div>
                    <div>${escapeHtml(irrSoilDisplay)}</div>
                </div>` : ""}

                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div class="bg-white p-2 rounded-xl border border-[#d4e6da]">
                        <div class="text-stone-500 text-[11px]">🌿 ${escapeHtml(t.nitrogen)}</div>
                        <div class="text-sm font-bold text-stone-900 mt-0.5">${escapeHtml(nVal)}</div>
                    </div>
                    <div class="bg-white p-2 rounded-xl border border-[#d4e6da]">
                        <div class="text-stone-500 text-[11px]">🌸 ${escapeHtml(t.phosphorus)}</div>
                        <div class="text-sm font-bold text-stone-900 mt-0.5">${escapeHtml(pVal)}</div>
                    </div>
                    <div class="bg-white p-2 rounded-xl border border-[#d4e6da]">
                        <div class="text-stone-500 text-[11px]">🍅 ${escapeHtml(t.potassium)}</div>
                        <div class="text-sm font-bold text-stone-900 mt-0.5">${escapeHtml(kVal)}</div>
                    </div>
                    <div class="bg-white p-2 rounded-xl border border-[#d4e6da]">
                        <div class="text-stone-500 text-[11px]">🪱 ${escapeHtml(t.oc)}</div>
                        <div class="text-sm font-bold text-stone-900 mt-0.5">${ocWord ? `${escapeHtml(ocWord)} (${nut.organic_carbon_pct ?? "--"}%)` : `${nut.organic_carbon_pct ?? "--"}%`}</div>
                    </div>
                </div>

                ${amendItems.length ? `
                <div class="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs leading-relaxed text-emerald-900 space-y-1.5">
                    <div class="font-bold">🌱 ${escapeHtml(t.amendment)}</div>
                    ${amendItems.map(a => `<div>• ${escapeHtml(a)}</div>`).join("")}
                </div>` : ""}

                <details class="bg-white rounded-xl border border-[#d4e6da] px-3 py-2 text-xs">
                    <summary class="cursor-pointer font-bold text-stone-600 select-none flex items-center justify-between">
                        <span>📊 ${escapeHtml(t.techDetails)}</span>
                        <span class="text-stone-400 text-[11px]">▼</span>
                    </summary>
                    <div class="mt-2 space-y-1 text-[11px] text-stone-600">
                        <div class="flex justify-between"><span>Top Surface (0–1 cm):</span><b>${depths.surface_0_1cm ?? "--"}%</b></div>
                        <div class="flex justify-between"><span>Top 4 Inches (3–9 cm):</span><b>${depths.shallow_3_9cm ?? "--"}%</b></div>
                        <div class="flex justify-between"><span>Top 1 Foot (9–27 cm):</span><b>${depths.active_root_9_27cm ?? "--"}%</b></div>
                        <div class="flex justify-between"><span>Deep 2.5 Feet (27–81 cm):</span><b>${depths.deep_root_27_81cm ?? "--"}%</b></div>
                        ${sTemps.root_6cm != null ? `<div class="flex justify-between"><span>Soil Temperature:</span><b>${sTemps.root_6cm}°C</b></div>` : ""}
                        ${tex.sand_pct != null ? `<div class="pt-1 border-t border-stone-100 flex justify-between"><span>Soil Make-up:</span><b>Sand ${tex.sand_pct}% • Clay ${tex.clay_pct}% • Silt ${tex.silt_pct}%</b></div>` : ""}
                    </div>
                </details>

                ${renderCardFooter(isLive ? t.srcSoil : (d.data_source_label || t.cached), d.last_updated)}
            </div>
        `;
    }

    function renderMandiPrompt() {
        const t = getToolT(currentLang);
        const box = document.getElementById("toolMandiOutput");
        const badge = document.getElementById("mandiSourceBadge");
        if (badge) {
            badge.className = "text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-900 border border-amber-200 whitespace-nowrap shrink-0";
            badge.textContent = t.ready;
        }
        if (!box) return;
        box.innerHTML = `
            <div class="flex-1 flex flex-col items-center justify-center bg-amber-50/50 rounded-xl border border-dashed border-amber-200 p-5 text-center space-y-2">
                <i class="fa-solid fa-scale-balanced text-2xl text-amber-600"></i>
                <p class="text-xs text-stone-600 leading-relaxed">${escapeHtml(t.enterMandiPrompt || t.enterLocPrompt)}</p>
            </div>
        `;
    }

    function renderMandiCard(d) {
        const t = getToolT(currentLang);
        const box = document.getElementById("toolMandiOutput");
        const badge = document.getElementById("mandiSourceBadge");
        if (!box) return;

        if (!d || (d.status !== "success" && d.status !== "cached_real")) {
            lastMandiData = null;
            if (badge) {
                badge.className = "text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200 whitespace-nowrap shrink-0";
                badge.textContent = d && d.status === "service_unavailable" ? t.offline : t.ready;
            }
            const msg = (d && d.message) ? d.message : t.weatherOffline;
            box.innerHTML = `
                <div class="flex-1 flex flex-col items-center justify-center bg-amber-50/70 rounded-xl border border-amber-200 p-5 text-center space-y-2">
                    <i class="fa-solid fa-circle-info text-xl text-amber-700"></i>
                    <p class="text-xs text-amber-950 leading-relaxed font-medium">${escapeHtml(msg)}</p>
                </div>
            `;
            return;
        }

        lastMandiData = d;
        const isLive = d.is_live_data === true;
        renderSourceBadge(badge, isLive, t.cached);
        const mandis = (d.all_mandis_comparison || []).slice(0, 4);
        const tCode = d.trend_code || "STEADY";
        const trendColor = tCode === "UP" ? "text-emerald-800" : (tCode === "DOWN" ? "text-red-700" : "text-stone-700");
        const trendIcon = tCode === "UP" ? "fa-arrow-trend-up" : (tCode === "DOWN" ? "fa-arrow-trend-down" : "fa-arrows-left-right");

        const hasDistances = mandis.some(m => typeof m.distance_km === "number");
        const rows = mandis.map(m => {
            const rightCol = typeof m.distance_km === "number"
                ? `${m.distance_km} km`
                : escapeHtml(m.district || m.state || "");
            return `
            <tr class="border-t border-[#d4e6da]">
                <td class="py-2 pr-2 text-stone-700 font-medium">${escapeHtml((m.mandi || "").split("(")[0].trim())}</td>
                <td class="py-2 pr-2 font-bold text-amber-800 whitespace-nowrap">₹${m.modal_price}</td>
                <td class="py-2 text-stone-500 whitespace-nowrap text-right">${rightCol}</td>
            </tr>`;
        }).join("");

        box.innerHTML = `
            <div class="flex-1 flex flex-col bg-[#f7fbf8] rounded-xl border border-[#d4e6da] p-4 space-y-3.5 min-w-0 overflow-hidden">
                <div class="space-y-1.5 min-w-0">
                    <div class="flex items-center justify-between gap-2 min-w-0">
                        <div class="text-xs font-bold text-stone-600 truncate min-w-0" title="${escapeHtml(d.commodity || "")} • ${escapeHtml((d.primary_mandi || "").split("(")[0].trim())}">${escapeHtml(d.commodity || "")} • ${escapeHtml((d.primary_mandi || "").split("(")[0].trim())}</div>
                        <span class="text-xs font-extrabold text-stone-900 bg-white px-2 py-0.5 rounded-full border border-amber-200 whitespace-nowrap shrink-0">₹${d.price_per_kg ?? "--"}${escapeHtml(t.kg)}</span>
                    </div>
                    <div class="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
                        <div class="text-2xl font-extrabold text-amber-800 whitespace-nowrap">₹${d.modal_price ?? "--"} <span class="text-xs font-semibold text-stone-500">${escapeHtml(t.qtl)}</span></div>
                        <div class="text-[11px] font-bold ${trendColor} inline-flex items-center gap-1 bg-white px-2 py-0.5 rounded-full border border-stone-200 max-w-full">
                            <i class="fa-solid ${trendIcon} shrink-0"></i>
                            <span class="truncate">${escapeHtml(d.trend || "")}</span>
                        </div>
                    </div>
                    <div class="text-xs text-stone-600">${escapeHtml(t.rangeLabel || "Today's Range")}: <strong class="text-stone-800 whitespace-nowrap">₹${d.min_price ?? "--"} – ₹${d.max_price ?? "--"}</strong></div>
                </div>

                ${d.msp_price ? `
                <div class="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-between text-xs">
                    <span class="text-emerald-900 font-semibold">${escapeHtml(t.mspLabel || "Govt Support Price (MSP)")}:</span>
                    <strong class="text-emerald-950">₹${d.msp_price} ${escapeHtml(t.qtl)}</strong>
                </div>` : ""}

                ${rows ? `
                <table class="w-full text-xs text-left border-t border-[#d4e6da]">
                    <thead class="text-stone-500 uppercase">
                        <tr>
                            <th class="py-1.5">${escapeHtml(t.mandi)}</th>
                            <th class="py-1.5">${escapeHtml(t.modal)}</th>
                            <th class="py-1.5 text-right">${escapeHtml(hasDistances ? t.dist : "Area")}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>` : ""}

                <div class="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs leading-relaxed text-amber-950">
                    <div class="font-bold mb-0.5">${escapeHtml(t.strategy)}</div>
                    <div>${escapeHtml(d.selling_advisory || "")}</div>
                </div>

                ${renderCardFooter(isLive ? t.srcMandi : (d.data_source_label || t.cached), d.last_updated)}
            </div>
        `;
    }

    function fetchWeatherTool() {
        const locInput = document.getElementById("toolWeatherLoc");
        const loc = locInput ? locInput.value.trim() : "";
        const box = document.getElementById("toolWeatherOutput");
        if (!box) return;
        if (!loc) {
            lastWeatherData = null;
            renderWeatherPrompt();
            return;
        }
        try { localStorage.setItem("kv_weather_loc", loc); } catch (_) {}
        box.innerHTML = `<div class="bg-sky-50/70 p-5 rounded-xl border border-sky-200 text-sky-800 text-xs text-center animate-pulse">Fetching live Open-Meteo telemetry...</div>`;
        fetch(`/api/tools/weather?location=${encodeURIComponent(loc)}`)
            .then(r => r.json())
            .then(renderWeatherCard)
            .catch(e => { box.innerHTML = `<div class="p-4 text-sm text-red-500">Error: ${escapeHtml(e.message)}</div>`; });
    }

    function fetchWeatherByGPS() {
        const box = document.getElementById("toolWeatherOutput");
        const locInput = document.getElementById("toolWeatherLoc");
        if (!box) return;
        if (!navigator.geolocation) {
            renderWeatherCard({ status: "error", message: "Browser geolocation is not supported on this device." });
            return;
        }
        box.innerHTML = `<div class="bg-sky-50/70 p-5 rounded-xl border border-sky-200 text-sky-800 text-xs text-center animate-pulse">Acquiring farm GPS coordinates...</div>`;
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude.toFixed(4);
                const lon = pos.coords.longitude.toFixed(4);
                if (locInput) locInput.value = `${lat}, ${lon}`;
                try { localStorage.setItem("kv_weather_loc", `${lat}, ${lon}`); } catch (_) {}
                fetch(`/api/tools/weather?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`)
                    .then(r => r.json())
                    .then(d => {
                        if (locInput && d && d.location && !d.location.startsWith("Farm GPS")) {
                            locInput.value = d.location;
                            try { localStorage.setItem("kv_weather_loc", d.location); } catch (_) {}
                        }
                        renderWeatherCard(d);
                    })
                    .catch(e => { box.innerHTML = `<div class="p-4 text-sm text-red-500">Error: ${escapeHtml(e.message)}</div>`; });
            },
            (err) => {
                renderWeatherCard({ status: "error", message: `GPS permission denied or unavailable (${err.message}). Please type your village or district name.` });
            },
            { enableHighAccuracy: true, timeout: 8000 }
        );
    }

    function fetchSoilTool() {
        const distInput = document.getElementById("toolSoilDist");
        const cropSelect = document.getElementById("toolSoilCrop");
        const dist = distInput ? distInput.value.trim() : "";
        const crop = cropSelect ? cropSelect.value : "general";
        const box = document.getElementById("toolSoilOutput");
        if (!box) return;
        if (!dist) {
            lastSoilData = null;
            renderSoilPrompt();
            return;
        }
        try { localStorage.setItem("kv_soil_loc", dist); } catch (_) {}
        box.innerHTML = `<div class="bg-emerald-50/70 p-5 rounded-xl border border-emerald-200 text-emerald-800 text-xs text-center animate-pulse">Querying 250m soil grid &amp; 5-depth root moisture...</div>`;
        fetch(`/api/tools/soil?district=${encodeURIComponent(dist)}&crop=${encodeURIComponent(crop)}`)
            .then(r => r.json())
            .then(renderSoilCard)
            .catch(e => { box.innerHTML = `<div class="p-4 text-sm text-red-500">Error: ${escapeHtml(e.message)}</div>`; });
    }

    function fetchSoilByGPS() {
        const box = document.getElementById("toolSoilOutput");
        const distInput = document.getElementById("toolSoilDist");
        const cropSelect = document.getElementById("toolSoilCrop");
        const crop = cropSelect ? cropSelect.value : "general";
        if (!box) return;
        if (!navigator.geolocation) {
            renderSoilCard({ status: "error", message: "Browser geolocation is not supported on this device." });
            return;
        }
        box.innerHTML = `<div class="bg-emerald-50/70 p-5 rounded-xl border border-emerald-200 text-emerald-800 text-xs text-center animate-pulse">Acquiring farm GPS coordinates...</div>`;
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude.toFixed(4);
                const lon = pos.coords.longitude.toFixed(4);
                if (distInput) distInput.value = `${lat}, ${lon}`;
                try { localStorage.setItem("kv_soil_loc", `${lat}, ${lon}`); } catch (_) {}
                fetch(`/api/tools/soil?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&crop=${encodeURIComponent(crop)}`)
                    .then(r => r.json())
                    .then(d => {
                        if (distInput && d && d.location && !d.location.startsWith("Farm GPS")) {
                            distInput.value = d.location;
                            try { localStorage.setItem("kv_soil_loc", d.location); } catch (_) {}
                        }
                        renderSoilCard(d);
                    })
                    .catch(e => { box.innerHTML = `<div class="p-4 text-sm text-red-500">Error: ${escapeHtml(e.message)}</div>`; });
            },
            (err) => {
                renderSoilCard({ status: "error", message: `GPS permission denied or unavailable (${err.message}). Please type your village or district name.` });
            },
            { enableHighAccuracy: true, timeout: 8000 }
        );
    }

    function fetchMandiTool() {
        const cropEl = document.getElementById("toolMandiCrop");
        const locEl = document.getElementById("toolMandiLoc");
        const crop = cropEl ? cropEl.value.trim() : "";
        const loc = locEl ? locEl.value.trim() : "";
        const box = document.getElementById("toolMandiOutput");
        if (!box) return;
        if (!crop) {
            lastMandiData = null;
            renderMandiPrompt();
            return;
        }
        try {
            localStorage.setItem("kv_mandi_crop", crop);
            if (loc) localStorage.setItem("kv_mandi_loc", loc);
        } catch (_) {}
        box.innerHTML = `<div class="bg-amber-50/70 p-5 rounded-xl border border-amber-200 text-amber-900 text-xs text-center animate-pulse">Checking live APMC market arrivals...</div>`;
        const qs = `commodity=${encodeURIComponent(crop)}&location=${encodeURIComponent(loc)}&language=${encodeURIComponent(currentLang)}`;
        fetch(`/api/tools/mandi?${qs}`)
            .then(r => r.json())
            .then(renderMandiCard)
            .catch(e => { box.innerHTML = `<div class="p-4 text-sm text-red-500">Error: ${escapeHtml(e.message)}</div>`; });
    }

    function fetchMandiByGPS() {
        const box = document.getElementById("toolMandiOutput");
        const locEl = document.getElementById("toolMandiLoc");
        const cropEl = document.getElementById("toolMandiCrop");
        const crop = (cropEl ? cropEl.value.trim() : "") || "Tomato";
        if (!box) return;
        if (!navigator.geolocation) {
            renderMandiCard({ status: "error", message: "Browser geolocation is not supported on this device." });
            return;
        }
        box.innerHTML = `<div class="bg-amber-50/70 p-5 rounded-xl border border-amber-200 text-amber-900 text-xs text-center animate-pulse">Finding nearby APMC markets via GPS...</div>`;
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude.toFixed(4);
                const lon = pos.coords.longitude.toFixed(4);
                if (locEl) locEl.value = `${lat}, ${lon}`;
                fetch(`/api/tools/mandi?commodity=${encodeURIComponent(crop)}&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&language=${encodeURIComponent(currentLang)}`)
                    .then(r => r.json())
                    .then(d => {
                        if (locEl && d && d.requested_location && d.requested_location !== "All India") {
                            locEl.value = d.requested_location;
                            try { localStorage.setItem("kv_mandi_loc", d.requested_location); } catch (_) {}
                        }
                        renderMandiCard(d);
                    })
                    .catch(e => { box.innerHTML = `<div class="p-4 text-sm text-red-500">Error: ${escapeHtml(e.message)}</div>`; });
            },
            (err) => {
                renderMandiCard({ status: "error", message: `GPS permission denied or unavailable (${err.message}). Please type your village or district name.` });
            },
            { enableHighAccuracy: true, timeout: 8000 }
        );
    }

    const testWeatherBtn = document.getElementById("testWeatherBtn");
    if (testWeatherBtn) testWeatherBtn.addEventListener("click", fetchWeatherTool);

    const gpsWeatherBtn = document.getElementById("gpsWeatherBtn");
    if (gpsWeatherBtn) gpsWeatherBtn.addEventListener("click", fetchWeatherByGPS);

    const weatherLocInput = document.getElementById("toolWeatherLoc");
    if (weatherLocInput) {
        weatherLocInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") fetchWeatherTool();
        });
    }

    const testSoilBtn = document.getElementById("testSoilBtn");
    if (testSoilBtn) testSoilBtn.addEventListener("click", fetchSoilTool);

    const gpsSoilBtn = document.getElementById("gpsSoilBtn");
    if (gpsSoilBtn) gpsSoilBtn.addEventListener("click", fetchSoilByGPS);

    const soilDistInput = document.getElementById("toolSoilDist");
    if (soilDistInput) {
        soilDistInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") fetchSoilTool();
        });
    }

    const soilCropSelect = document.getElementById("toolSoilCrop");
    if (soilCropSelect) {
        soilCropSelect.addEventListener("change", () => {
            if (soilDistInput && soilDistInput.value.trim()) fetchSoilTool();
        });
    }

    const testMandiBtn = document.getElementById("testMandiBtn");
    if (testMandiBtn) testMandiBtn.addEventListener("click", fetchMandiTool);

    const gpsMandiBtn = document.getElementById("gpsMandiBtn");
    if (gpsMandiBtn) gpsMandiBtn.addEventListener("click", fetchMandiByGPS);

    const mandiLocInput = document.getElementById("toolMandiLoc");
    if (mandiLocInput) {
        mandiLocInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") fetchMandiTool();
        });
    }

    const mandiCropInput = document.getElementById("toolMandiCrop");
    if (mandiCropInput) {
        mandiCropInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") fetchMandiTool();
        });
        mandiCropInput.addEventListener("change", () => {
            if (mandiCropInput.value.trim()) fetchMandiTool();
        });
    }

    // Initialize Weather, Soil & Mandi Tools without any hardcoded default locations
    (function initToolsOnLoad() {
        let savedWeatherLoc = "";
        let savedSoilLoc = "";
        let savedMandiLoc = "";
        let savedMandiCrop = "";
        try {
            savedWeatherLoc = (localStorage.getItem("kv_weather_loc") || "").trim();
            savedSoilLoc = (localStorage.getItem("kv_soil_loc") || savedWeatherLoc || "").trim();
            savedMandiLoc = (localStorage.getItem("kv_mandi_loc") || savedWeatherLoc || "").trim();
            savedMandiCrop = (localStorage.getItem("kv_mandi_crop") || "").trim();
        } catch (_) {}

        if (savedWeatherLoc && weatherLocInput) {
            weatherLocInput.value = savedWeatherLoc;
            fetchWeatherTool();
        } else if (navigator.permissions && navigator.geolocation) {
            navigator.permissions.query({ name: "geolocation" }).then(res => {
                if (res.state === "granted") fetchWeatherByGPS();
                else renderWeatherPrompt();
            }).catch(() => renderWeatherPrompt());
        } else {
            renderWeatherPrompt();
        }

        if (savedSoilLoc && soilDistInput) {
            soilDistInput.value = savedSoilLoc;
            fetchSoilTool();
        } else if (navigator.permissions && navigator.geolocation) {
            navigator.permissions.query({ name: "geolocation" }).then(res => {
                if (res.state === "granted") fetchSoilByGPS();
                else renderSoilPrompt();
            }).catch(() => renderSoilPrompt());
        } else {
            renderSoilPrompt();
        }

        if (savedMandiLoc && mandiLocInput) mandiLocInput.value = savedMandiLoc;
        if (savedMandiCrop && mandiCropInput) mandiCropInput.value = savedMandiCrop;
        if (savedMandiLoc && mandiCropInput && mandiCropInput.value.trim()) {
            fetchMandiTool();
        } else if (!savedMandiLoc && navigator.permissions && navigator.geolocation) {
            navigator.permissions.query({ name: "geolocation" }).then(res => {
                if (res.state === "granted") fetchMandiByGPS();
                else if (mandiCropInput && mandiCropInput.value.trim()) fetchMandiTool();
                else renderMandiPrompt();
            }).catch(() => {
                if (mandiCropInput && mandiCropInput.value.trim()) fetchMandiTool();
                else renderMandiPrompt();
            });
        } else if (mandiCropInput && mandiCropInput.value.trim()) {
            fetchMandiTool();
        } else {
            renderMandiPrompt();
        }

        const terraceLocInit = document.getElementById("terraceLoc");
        if (savedWeatherLoc && terraceLocInit && !terraceLocInit.value) {
            terraceLocInit.value = savedWeatherLoc;
        }
        renderTerracePlanPrompt();
        renderTerraceGuidePrompt();
    })();

    // ==========================================
    // TERRACE & BEGINNER FARMING STUDIO LOGIC
    // ==========================================
    function renderTerracePlanPrompt() {
        const box = document.getElementById("terracePlanOutput");
        if (!box) return;
        const tt = TERRACE_I18N[currentLang] || TERRACE_I18N.en;
        box.innerHTML = `
            <div class="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200 text-xs text-emerald-950 flex items-center space-x-2.5">
                <i class="fa-solid fa-compass-drafting text-emerald-700 text-base shrink-0"></i>
                <span>${escapeHtml(tt.planPrompt)}</span>
            </div>
        `;
    }

    function renderTerraceGuidePrompt() {
        const box = document.getElementById("terraceGuideOutput");
        if (!box) return;
        const tt = TERRACE_I18N[currentLang] || TERRACE_I18N.en;
        box.innerHTML = `
            <div class="p-4 rounded-xl bg-amber-50/60 border border-amber-200 text-xs text-amber-950 flex items-center space-x-2.5">
                <i class="fa-solid fa-seedling text-amber-700 text-base shrink-0"></i>
                <span>${escapeHtml(tt.coachPrompt)}</span>
            </div>
        `;
    }

    document.querySelectorAll(".terrace-size-preset").forEach(btn => {
        btn.addEventListener("click", () => {
            const l = btn.getAttribute("data-l");
            const w = btn.getAttribute("data-w");
            const sun = btn.getAttribute("data-sun");
            const sp = btn.getAttribute("data-space");
            const lenEl = document.getElementById("terraceLengthFt");
            const widEl = document.getElementById("terraceWidthFt");
            const sunEl = document.getElementById("terraceSunHrs");
            const spEl = document.getElementById("terraceSpaceType");
            if (lenEl) lenEl.value = l;
            if (widEl) widEl.value = w;
            if (sunEl) sunEl.value = sun;
            if (spEl && sp) spEl.value = sp;
            const locEl = document.getElementById("terraceLoc");
            if (locEl && locEl.value.trim()) {
                triggerTerracePlanFromInputs();
            } else if (locEl) {
                locEl.focus();
            }
        });
    });

    function triggerTerracePlanFromInputs(gpsCoords = null) {
        const loc = (document.getElementById("terraceLoc")?.value || "").trim();
        const lengthFt = (document.getElementById("terraceLengthFt")?.value || "").trim();
        const widthFt = (document.getElementById("terraceWidthFt")?.value || "").trim();
        const sunHrs = (document.getElementById("terraceSunHrs")?.value || "").trim();
        const spaceType = document.getElementById("terraceSpaceType")?.value || "open_terrace";
        const goal = document.getElementById("terraceGoal")?.value || "daily_kitchen";

        const params = {
            location: loc,
            lat: gpsCoords ? gpsCoords.lat : "",
            lon: gpsCoords ? gpsCoords.lon : "",
            length_ft: lengthFt,
            width_ft: widthFt,
            sunlight_hours: sunHrs,
            space_type: spaceType,
            goal: goal
        };
        fetchTerracePlan(params);
    }

    function fetchTerracePlan(params) {
        const box = document.getElementById("terracePlanOutput");
        if (!box) return;

        if ((!params.location && !params.lat) || !params.length_ft || !params.width_ft || !params.sunlight_hours) {
            box.innerHTML = `
                <div class="p-3.5 rounded-xl bg-amber-50 border border-amber-300 text-xs text-amber-950 flex items-center space-x-2">
                    <i class="fa-solid fa-circle-info text-amber-700"></i>
                    <span>Please enter your City/PIN (or tap 📍 GPS) along with Length (ft), Width (ft), and Direct Sunlight hours.</span>
                </div>
            `;
            return;
        }

        lastTerracePlanParams = params;
        if (params.location) {
            try { localStorage.setItem("kv_weather_loc", params.location); } catch (_) {}
        }

        box.innerHTML = `
            <div class="p-5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-emerald-900 text-xs text-center animate-pulse font-semibold">
                <i class="fa-solid fa-spinner fa-spin mr-1.5"></i>Fetching live local weather &amp; calculating container weight physics...
            </div>
        `;

        const qs = new URLSearchParams({
            location: params.location || "",
            lat: params.lat || "",
            lon: params.lon || "",
            length_ft: params.length_ft,
            width_ft: params.width_ft,
            sunlight_hours: params.sunlight_hours,
            space_type: params.space_type || "open_terrace",
            goal: params.goal || "daily_kitchen",
            language: currentLang
        });

        fetch(`/api/tools/terrace/plan?${qs.toString()}`)
            .then(r => r.json())
            .then(data => {
                if (data.status !== "success") {
                    box.innerHTML = `
                        <div class="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 font-medium">
                            <i class="fa-solid fa-triangle-exclamation mr-1.5"></i>${escapeHtml(data.message || "Could not compute terrace plan.")}
                        </div>
                    `;
                    return;
                }
                const locEl = document.getElementById("terraceLoc");
                if (locEl && data.location && !data.location.startsWith("Farm GPS")) {
                    locEl.value = data.location;
                }
                lastTerracePlanData = data;
                renderTerracePlanCard(data);
            })
            .catch(err => {
                box.innerHTML = `<div class="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800">${escapeHtml(err.message)}</div>`;
            });
    }

    function renderTerracePlanCard(d) {
        const box = document.getElementById("terracePlanOutput");
        if (!box || !d) return;
        const tt = TERRACE_I18N[currentLang] || TERRACE_I18N.en;
        const pm = d.potting_mix_buckets || {};
        const wt = d.watering_today || {};
        const ws = d.weather_snapshot || {};
        const crops = d.recommended_crops || [];

        const cropsHtml = crops.map(c => `
            <div class="p-3 rounded-xl bg-white border border-emerald-200 hover:border-emerald-500 transition flex flex-col justify-between space-y-2 shadow-2xs">
                <div class="space-y-1">
                    <div class="flex items-start justify-between gap-1.5">
                        <div class="font-extrabold text-green-950 text-xs">${escapeHtml(c.name)}</div>
                        <span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-900 font-extrabold text-[10px] shrink-0">${c.fit_score}% Fit</span>
                    </div>
                    <div class="text-[11px] text-gray-600 flex flex-wrap gap-x-2 gap-y-0.5">
                        <span>🪴 ${escapeHtml(c.bag_size)}</span>
                        <span>⏱️ ${escapeHtml(c.harvest_days)}</span>
                    </div>
                    <div class="text-[11px] font-semibold text-amber-800">
                        ✨ ${escapeHtml(c.difficulty)}
                        ${c.local_market_price_per_kg ? ` • <span class="text-emerald-800">APMC ~₹${c.local_market_price_per_kg}/kg</span>` : ""}
                    </div>
                </div>
                <button type="button" class="open-crop-coach-btn w-full mt-1 px-2.5 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-950 border border-amber-300 text-[11px] font-bold transition text-center"
                        data-crop="${escapeHtml(c.crop_key)}">
                    ${escapeHtml(tt.learnHowBtn)}
                </button>
            </div>
        `).join("");

        const sunNotesHtml = (d.sunlight_notes || []).length
            ? `<div class="text-[11px] text-amber-900 bg-amber-50/80 border border-amber-200 rounded-xl px-3 py-2">
                   <i class="fa-solid fa-sun mr-1 text-amber-600"></i>${(d.sunlight_notes || []).map(escapeHtml).join(" ")}
               </div>`
            : "";

        box.innerHTML = `
            <div class="space-y-4 pt-1">
                <!-- 1. Live Weather + Today's Watering Banner -->
                <div class="p-3.5 rounded-xl bg-gradient-to-r from-sky-50 via-emerald-50 to-amber-50 border border-emerald-200 flex flex-wrap items-center justify-between gap-3">
                    <div class="space-y-1 max-w-2xl">
                        <div class="flex flex-wrap items-center gap-2">
                            <span class="font-extrabold text-green-950 text-xs">📍 ${escapeHtml(d.location)}</span>
                            <span class="px-2 py-0.5 rounded-full bg-white border border-sky-200 text-sky-900 font-bold text-[11px]">
                                🌡️ ${ws.temperature_c}°C • 💧 ${ws.humidity_pct}%
                            </span>
                        </div>
                        <p class="text-xs text-gray-800 leading-relaxed">${escapeHtml(ws.weather_care_tip || "")}</p>
                    </div>
                    <div class="bg-white px-3.5 py-2 rounded-xl border border-sky-200 text-center shrink-0 shadow-2xs">
                        <div class="text-[10px] font-bold text-sky-800 uppercase">${escapeHtml(tt.waterToday)}</div>
                        <div class="text-sm font-extrabold text-sky-950">${wt.ml_per_medium_bag} ml <span class="text-xs text-emerald-700">(~${wt.mugs_per_medium_bag} ${escapeHtml(tt.mugsUnit)})</span></div>
                    </div>
                </div>

                <!-- 2. Clean 10L Household Bucket Potting Mix Strip -->
                <div class="p-3.5 rounded-xl bg-amber-50/60 border border-amber-200 space-y-2.5">
                    <div class="font-extrabold text-amber-950 text-xs flex items-center space-x-1.5">
                        <i class="fa-solid fa-bucket text-amber-700"></i>
                        <span>${escapeHtml(tt.bucketMix)}</span>
                    </div>
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                        <div class="bg-white px-3 py-2 rounded-lg border border-amber-200/80">
                            <div class="text-gray-500">🥥 ${escapeHtml(tt.cocopeat)}</div>
                            <div class="font-extrabold text-amber-950 mt-0.5">${pm.cocopeat_buckets} ${escapeHtml(tt.bucketsUnit)}</div>
                        </div>
                        <div class="bg-white px-3 py-2 rounded-lg border border-amber-200/80">
                            <div class="text-gray-500">🪱 ${escapeHtml(tt.compost)}</div>
                            <div class="font-extrabold text-amber-950 mt-0.5">${pm.compost_buckets} ${escapeHtml(tt.bucketsUnit)}</div>
                        </div>
                        <div class="bg-white px-3 py-2 rounded-lg border border-amber-200/80">
                            <div class="text-gray-500">🪴 ${escapeHtml(tt.redSoil)}</div>
                            <div class="font-extrabold text-amber-950 mt-0.5">${pm.red_soil_buckets} ${escapeHtml(tt.bucketsUnit)}</div>
                        </div>
                        <div class="bg-white px-3 py-2 rounded-lg border border-amber-200/80">
                            <div class="text-gray-500">🌿 ${escapeHtml(tt.neemCake)}</div>
                            <div class="font-extrabold text-amber-950 mt-0.5">${pm.neem_cake_kg} kg</div>
                        </div>
                    </div>
                    <div class="text-[11px] text-amber-950 leading-relaxed">
                        ${escapeHtml(pm.how_to_mix || "")}
                    </div>
                </div>

                <!-- 3. Recommended Crops Grid -->
                <div class="space-y-2">
                    <h4 class="text-xs font-extrabold text-green-950 flex items-center space-x-1.5">
                        <i class="fa-solid fa-award text-amber-600"></i>
                        <span>${escapeHtml(tt.bestCrops)}</span>
                    </h4>
                    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                        ${cropsHtml}
                    </div>
                    ${sunNotesHtml}
                </div>
            </div>
        `;

        box.querySelectorAll(".open-crop-coach-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const cKey = btn.getAttribute("data-crop");
                fetchTerraceCropGuide(cKey);
                const coachEl = document.getElementById("terraceCoachCard");
                if (coachEl) coachEl.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        });
    }

    const calcTerraceBtn = document.getElementById("calcTerraceBtn");
    if (calcTerraceBtn) {
        calcTerraceBtn.addEventListener("click", () => triggerTerracePlanFromInputs());
    }

    const gpsTerraceBtn = document.getElementById("gpsTerraceBtn");
    if (gpsTerraceBtn) {
        gpsTerraceBtn.addEventListener("click", () => {
            const box = document.getElementById("terracePlanOutput");
            const locEl = document.getElementById("terraceLoc");
            if (!navigator.geolocation) {
                if (box) box.innerHTML = `<div class="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700">Geolocation is not supported in this browser.</div>`;
                return;
            }
            if (box) box.innerHTML = `<div class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 animate-pulse">Acquiring live GPS coordinates...</div>`;
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    const lat = pos.coords.latitude.toFixed(4);
                    const lon = pos.coords.longitude.toFixed(4);
                    if (locEl) locEl.value = `${lat}, ${lon}`;
                    const lenVal = (document.getElementById("terraceLengthFt")?.value || "").trim();
                    const widVal = (document.getElementById("terraceWidthFt")?.value || "").trim();
                    const sunVal = (document.getElementById("terraceSunHrs")?.value || "").trim();
                    if (lenVal && widVal && sunVal) {
                        triggerTerracePlanFromInputs({ lat, lon });
                    } else {
                        fetch(`/api/tools/weather?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`)
                            .then(r => r.json())
                            .then(w => {
                                if (locEl && w.location && !w.location.startsWith("Farm GPS")) {
                                    locEl.value = w.location;
                                }
                                renderTerracePlanPrompt();
                            })
                            .catch(() => renderTerracePlanPrompt());
                    }
                },
                (err) => {
                    if (box) box.innerHTML = `<div class="p-3 rounded-xl bg-amber-50 border border-amber-300 text-xs text-amber-900">GPS unavailable (${escapeHtml(err.message)}). Please type your city or PIN code.</div>`;
                },
                { enableHighAccuracy: true, timeout: 8000 }
            );
        });
    }

    // Beginner Seed-to-Harvest Coach Handlers
    function fetchTerraceCropGuide(cropQuery) {
        const cleanCrop = (cropQuery || "").trim();
        const box = document.getElementById("terraceGuideOutput");
        if (!box) return;
        if (!cleanCrop) {
            renderTerraceGuidePrompt();
            return;
        }
        lastTerraceGuideCrop = cleanCrop;
        const loc = (document.getElementById("terraceLoc")?.value || "").trim();

        box.innerHTML = `
            <div class="p-5 rounded-xl bg-amber-50/70 border border-amber-200 text-amber-950 text-xs text-center animate-pulse font-semibold">
                <i class="fa-solid fa-spinner fa-spin mr-1.5"></i>Preparing Seed-to-Harvest beginner guide...
            </div>
        `;

        const qs = new URLSearchParams({
            crop: cleanCrop,
            location: loc,
            language: currentLang
        });

        fetch(`/api/tools/terrace/guide?${qs.toString()}`)
            .then(r => r.json())
            .then(data => {
                if (data.status !== "success") {
                    box.innerHTML = `<div class="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800">${escapeHtml(data.message || "Could not load crop guide.")}</div>`;
                    return;
                }
                lastTerraceGuideData = data;
                renderTerraceGuideCard(data);
            })
            .catch(err => {
                box.innerHTML = `<div class="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800">${escapeHtml(err.message)}</div>`;
            });
    }

    function renderTerraceGuideCard(g) {
        const box = document.getElementById("terraceGuideOutput");
        if (!box || !g) return;
        const tt = TERRACE_I18N[currentLang] || TERRACE_I18N.en;

        const badge = g.guide_mode === "online_ai_coach"
            ? `<span class="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-[11px] font-bold"><i class="fa-solid fa-cloud mr-1"></i>${escapeHtml(tt.aiCoachBadge)}</span>`
            : `<span class="px-2.5 py-1 rounded-full bg-amber-50 text-amber-900 border border-amber-300 text-[11px] font-bold"><i class="fa-solid fa-book mr-1"></i>${escapeHtml(tt.offlineCoachBadge)}</span>`;

        const stepsHtml = (g.steps || []).map((step, i) => `
            <li class="flex items-start space-x-2.5 p-2.5 rounded-xl bg-white border border-green-200/80">
                <span class="w-6 h-6 rounded-full bg-green-600 text-white font-extrabold text-[11px] flex items-center justify-center shrink-0 mt-0.5">${i + 1}</span>
                <span class="text-xs text-gray-800 leading-relaxed">${escapeHtml(step)}</span>
            </li>
        `).join("");

        box.innerHTML = `
            <div class="p-4 rounded-2xl bg-gradient-to-br from-green-50/70 via-white to-amber-50/60 border border-green-200 space-y-4">
                <div class="flex flex-wrap items-center justify-between gap-2 border-b border-green-200/70 pb-3">
                    <div>
                        <h4 class="text-base font-extrabold text-green-950">${escapeHtml(g.crop_title)}</h4>
                        <span class="text-[11px] font-bold text-amber-800">✨ ${escapeHtml(g.difficulty || "")}</span>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                        ${badge}
                        <button type="button" id="listenTerraceGuideBtn"
                                data-orig-label="${escapeHtml(tt.listenGuide)}"
                                class="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center space-x-1.5 shadow-2xs transition">
                            <i class="fa-solid fa-volume-high text-[11px]"></i>
                            <span>${escapeHtml(tt.listenGuide)}</span>
                        </button>
                    </div>
                </div>

                <!-- Key Specs -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    <div class="p-2.5 rounded-xl bg-white border border-green-200">
                        <div class="text-[10px] font-bold text-gray-500 uppercase">🪴 ${escapeHtml(tt.potNeeded)}</div>
                        <div class="text-xs font-bold text-green-950 mt-0.5">${escapeHtml(g.pot_size)}</div>
                    </div>
                    <div class="p-2.5 rounded-xl bg-white border border-amber-200">
                        <div class="text-[10px] font-bold text-gray-500 uppercase">☀️ ${escapeHtml(tt.sunNeeded)}</div>
                        <div class="text-xs font-bold text-amber-950 mt-0.5">${escapeHtml(g.sunlight_needed)}</div>
                    </div>
                    <div class="p-2.5 rounded-xl bg-white border border-emerald-200">
                        <div class="text-[10px] font-bold text-gray-500 uppercase">🗓️ ${escapeHtml(tt.firstHarvest)}</div>
                        <div class="text-xs font-bold text-emerald-950 mt-0.5">${escapeHtml(g.harvest_days)}</div>
                    </div>
                </div>

                <!-- 5-Step Timeline -->
                <div class="space-y-2">
                    <div class="text-xs font-extrabold text-green-950">${escapeHtml(tt.stepsHeading)}:</div>
                    <ol class="space-y-2">${stepsHtml}</ol>
                </div>

                <!-- Booster & Mistakes -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 space-y-1">
                        <div class="text-xs font-extrabold text-emerald-900">🥣 ${escapeHtml(tt.boosterHeading)}</div>
                        <div class="text-xs text-gray-800 leading-relaxed">${escapeHtml(g.natural_booster)}</div>
                    </div>
                    <div class="p-3 rounded-xl bg-red-50/70 border border-red-200 space-y-1">
                        <div class="text-xs font-extrabold text-red-900">⚠️ ${escapeHtml(tt.mistakesHeading)}</div>
                        <div class="text-xs text-gray-800 leading-relaxed">${escapeHtml(g.common_mistakes)}</div>
                    </div>
                </div>

                ${g.local_weather_tip ? `
                <div class="p-3 rounded-xl bg-sky-50 border border-sky-200 text-xs text-sky-950 leading-relaxed">
                    <strong>🌤️ ${escapeHtml(tt.weatherTipHeading)}:</strong> ${escapeHtml(g.local_weather_tip)}
                </div>` : ""}
            </div>
        `;

        const listenBtn = document.getElementById("listenTerraceGuideBtn");
        if (listenBtn && g.speech_text) {
            listenBtn.addEventListener("click", () => {
                speakText(g.speech_text, currentLang, listenBtn);
            });
        }
    }

    document.querySelectorAll(".beginner-crop-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            const c = pill.getAttribute("data-crop");
            const customInput = document.getElementById("terraceCustomCrop");
            if (customInput) customInput.value = "";
            fetchTerraceCropGuide(c);
        });
    });

    const learnCropBtn = document.getElementById("learnCropBtn");
    const terraceCustomCrop = document.getElementById("terraceCustomCrop");
    if (learnCropBtn && terraceCustomCrop) {
        learnCropBtn.addEventListener("click", () => {
            const q = terraceCustomCrop.value.trim();
            if (q) fetchTerraceCropGuide(q);
        });
        terraceCustomCrop.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && terraceCustomCrop.value.trim()) {
                fetchTerraceCropGuide(terraceCustomCrop.value.trim());
            }
        });
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
