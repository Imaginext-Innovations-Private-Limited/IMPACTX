/**
 * FasalSaarathi — Module 3: PMFBY Crop Insurance Shield & Weather-Loss Dossier UI (6 Languages)
 */
document.addEventListener("DOMContentLoaded", () => {
    const langSelect = document.getElementById("langSelect");
    const locInput = document.getElementById("insWeatherLoc");
    const gpsBtn = document.getElementById("insGpsBtn");
    const checkAlertBtn = document.getElementById("insCheckAlertBtn");
    const alertOutput = document.getElementById("insWeatherAlertOutput");

    const cropSelect = document.getElementById("insCropSelect");
    const seasonSelect = document.getElementById("insSeasonSelect");
    const acresInput = document.getElementById("insAcresInput");
    const calcBtn = document.getElementById("insCalcBtn");
    const savePolicyBtn = document.getElementById("insSavePolicyBtn");
    const quoteOutput = document.getElementById("insQuoteOutput");
    const policiesList = document.getElementById("insPoliciesList");
    const policyCount = document.getElementById("insPolicyCount");

    const claimPolicySelect = document.getElementById("insClaimPolicySelect");
    const claimPhotoInput = document.getElementById("insClaimPhoto");
    const claimNotesInput = document.getElementById("insClaimNotes");
    const createDossierBtn = document.getElementById("insCreateDossierBtn");
    const dossierOutput = document.getElementById("insDossierOutput");

    let gpsLat = null;
    let gpsLon = null;
    let insAudio = null;
    let lastAlertChecked = false;

    const CROP_LABELS = {
        en: { paddy: "🌾 Paddy (Rice)", wheat: "🌾 Wheat", tomato: "🍅 Tomato", onion: "🧅 Onion", chilli: "🌶️ Chilli", maize: "🌽 Maize", ragi: "🌾 Ragi", tur: "🫘 Tur / Red Gram", groundnut: "🥜 Groundnut", cotton: "☁️ Cotton", potato: "🥔 Potato", coffee: "☕ Coffee", arecanut: "🌴 Arecanut", banana: "🍌 Banana", sugarcane: "🎋 Sugarcane" },
        kn: { paddy: "🌾 ಭತ್ತ", wheat: "🌾 ಗೋಧಿ", tomato: "🍅 ಟೊಮೆಟೊ", onion: "🧅 ಈರುಳ್ಳಿ", chilli: "🌶️ ಮೆಣಸಿನಕಾಯಿ", maize: "🌽 ಮೆಕ್ಕೆಜೋಳ", ragi: "🌾 ರಾಗಿ", tur: "🫘 ತೊಗರಿ", groundnut: "🥜 ಶೇಂಗಾ", cotton: "☁️ ಹತ್ತಿ", potato: "🥔 ಆಲೂಗಡ್ಡೆ", coffee: "☕ ಕಾಫಿ", arecanut: "🌴 ಅಡಿಕೆ", banana: "🍌 ಬಾಳೆ", sugarcane: "🎋 ಕಬ್ಬು" },
        hi: { paddy: "🌾 धान", wheat: "🌾 गेहूं", tomato: "🍅 टमाटर", onion: "🧅 प्याज", chilli: "🌶️ मिर्च", maize: "🌽 मक्का", ragi: "🌾 रागी", tur: "🫘 अरहर / तुअर", groundnut: "🥜 मूंगफली", cotton: "☁️ कपास", potato: "🥔 आलू", coffee: "☕ कॉफ़ी", arecanut: "🌴 सुपारी", banana: "🍌 केला", sugarcane: "🎋 गन्ना" },
        ta: { paddy: "🌾 நெல்", wheat: "🌾 கோதுமை", tomato: "🍅 தக்காளி", onion: "🧅 வெங்காயம்", chilli: "🌶️ மிளகாய்", maize: "🌽 மக்காச்சோளம்", ragi: "🌾 கேழ்வரகு", tur: "🫘 துவரை", groundnut: "🥜 நிலக்கடலை", cotton: "☁️ பருத்தி", potato: "🥔 உருளைக்கிழங்கு", coffee: "☕ காபி", arecanut: "🌴 பாக்கு", banana: "🍌 வாழை", sugarcane: "🎋 கரும்பு" },
        te: { paddy: "🌾 వరి", wheat: "🌾 గోధుమ", tomato: "🍅 టమాటా", onion: "🧅 ఉల్లి", chilli: "🌶️ మిర్చి", maize: "🌽 మొక్కజొన్న", ragi: "🌾 రాగులు", tur: "🫘 కందులు", groundnut: "🥜 వేరుశనగ", cotton: "☁️ పత్తి", potato: "🥔 బంగాళాదుంప", coffee: "☕ కాఫీ", arecanut: "🌴 పోక", banana: "🍌 అరటి", sugarcane: "🎋 చెరకు" },
        mr: { paddy: "🌾 भात", wheat: "🌾 गहू", tomato: "🍅 टोमॅटो", onion: "🧅 कांदा", chilli: "🌶️ मिरची", maize: "🌽 मका", ragi: "🌾 नाचणी", tur: "🫘 तूर", groundnut: "🥜 भुईमूग", cotton: "☁️ कापूस", potato: "🥔 बटाटा", coffee: "☕ कॉफी", arecanut: "🌴 सुपारी", banana: "🍌 केळी", sugarcane: "🎋 ऊस" },
    };

    const SEASON_LABELS = {
        en: { kharif: "🌧️ Kharif (2%)", rabi: "❄️ Rabi (1.5%)", horticulture: "🍅 Horticulture (5%)" },
        kn: { kharif: "🌧️ ಮುಂಗಾರು / ಖರೀಫ್ (2%)", rabi: "❄️ ಹಿಂಗಾರು / ರಬಿ (1.5%)", horticulture: "🍅 ತೋಟಗಾರಿಕೆ (5%)" },
        hi: { kharif: "🌧️ खरीफ (2%)", rabi: "❄️ रबी (1.5%)", horticulture: "🍅 बागवानी (5%)" },
        ta: { kharif: "🌧️ காரீப் (2%)", rabi: "❄️ ரபி (1.5%)", horticulture: "🍅 தோட்டக்கலை (5%)" },
        te: { kharif: "🌧️ ఖరీఫ్ (2%)", rabi: "❄️ రబీ (1.5%)", horticulture: "🍅 ఉద్యానవన (5%)" },
        mr: { kharif: "🌧️ खरीप (2%)", rabi: "❄️ रब्बी (1.5%)", horticulture: "🍅 फळबाग (5%)" },
    };

    const INS_I18N = {
        en: {
            nav: "Crop Shield", heroTag: "Fasal Suraksha • PMFBY Crop Insurance Shield", helpline: "Helpline: 14447",
            alertTitle: "Live 72-Hour Weather Loss Alert",
            alertSub: "Checks live Open-Meteo hail, heavy rain, and storm triggers for your village so you never miss the 72-hour PMFBY claim window.",
            locPh: "Village, Taluk, District or PIN...", checkBtn: "Check Weather Shield", checking: "Checking live storm & rain triggers...",
            calcTitle: "🛡️ PMFBY Premium & Coverage Calculator", lblCrop: "Crop", lblSeason: "Season", lblAcres: "Land (Acres)",
            calcBtn: "Calculate Premium", saveBtn: "Save Policy", vaultTitle: "📋 My Insured Crops", activeUnit: "Active",
            noPol: "No saved policies yet. Calculate a quote and tap Save Policy.", remove: "Remove", acresUnit: "acres",
            dossierTitle: "📸 One-Click Claim Evidence Dossier",
            dossierSub: "Bundle your field damage photo, GPS coordinates, timestamp, and live Open-Meteo weather record into a claim-ready sheet.",
            lblPolicy: "Linked Policy (Optional)", generalLoss: "General Crop Loss Report", lblPhoto: "Field Damage Photo",
            lblNotes: "Damage Description", notesPh: "e.g. Waterlogging / hail damage in 2 acres",
            dossierHint: "Uses location from Weather Shield above (or live GPS).", dossierBtn: "Generate Claim Evidence Dossier",
            listen: "Listen", coverLabel: "Estimated Cover", farmerPays: "You Pay (Farmer Share)", govtPays: "Govt Subsidy",
            redBadge: "🚨 72-HOUR CLAIM TRIGGER ACTIVE", amberBadge: "⚠️ WEATHER WATCH", greenBadge: "✅ SAFE CONDITIONS",
            todayRain: "Today", gusts: "Gusts", claimRef: "Claim Ref", locLabel: "Location", loggedAt: "Logged At", weatherLog: "Weather Log", notesLabel: "Notes",
        },
        kn: {
            nav: "ಬೆಳೆ ವಿಮೆ", heroTag: "ಫಸಲ್ ಸುರಕ್ಷಾ • PMFBY ಬೆಳೆ ವಿಮಾ ಕವಚ", helpline: "ಸಹಾಯವಾಣಿ: 14447",
            alertTitle: "72-ಗಂಟೆಗಳ ಹವಾಮಾನ ಹಾನಿ ಎಚ್ಚರಿಕೆ",
            alertSub: "ನಿಮ್ಮ ಗ್ರಾಮದ ಆಲಿಕಲ್ಲು, ಭಾರೀ ಮಳೆ ಮತ್ತು ಬಿರುಗಾಳಿ ಎಚ್ಚರಿಕೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ 72 ಗಂಟೆಯೊಳಗೆ ವಿಮಾ ದೂರು ನೀಡಿ.",
            locPh: "ಗ್ರಾಮ, ತಾಲೂಕು, ಜಿಲ್ಲೆ ಅಥವಾ PIN...", checkBtn: "ಹವಾಮಾನ ಕವಚ ಪರಿಶೀಲಿಸಿ", checking: "ಹವಾಮಾನ ಎಚ್ಚರಿಕೆ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ...",
            calcTitle: "🛡️ PMFBY ವಿಮಾ ಕಂತು ಲೆಕ್ಕಾಚಾರ", lblCrop: "ಬೆಳೆ", lblSeason: "ಹಂಗಾಮು", lblAcres: "ಭೂಮಿ (ಎಕರೆ)",
            calcBtn: "ವಿಮೆ ಲೆಕ್ಕಹಾಕಿ", saveBtn: "ಪಾಲಿಸಿ ಉಳಿಸಿ", vaultTitle: "📋 ನನ್ನ ವಿಮೆ ಮಾಡಿದ ಬೆಳೆಗಳು", activeUnit: "ಸಕ್ರಿಯ",
            noPol: "ಇನ್ನೂ ಯಾವುದೇ ಪಾಲಿಸಿ ಉಳಿಸಿಲ್ಲ. ಲೆಕ್ಕಹಾಕಿ 'ಪಾಲಿಸಿ ಉಳಿಸಿ' ಒತ್ತಿ.", remove: "ತೆಗೆದುಹಾಕಿ", acresUnit: "ಎಕರೆ",
            dossierTitle: "📸 ವಿಮಾ ಸಾಕ್ಷ್ಯ ವರದಿ (Claim Dossier)",
            dossierSub: "ಬೆಳೆ ಹಾನಿ ಫೋಟೋ, GPS ಸ್ಥಳ, ಸಮಯ ಮತ್ತು ಹವಾಮಾನ ದಾಖಲೆಯನ್ನು ಒಂದೇ ವರದಿಯಲ್ಲಿ ಸಿದ್ಧಪಡಿಸಿ.",
            lblPolicy: "ಸಂಬಂಧಿತ ಪಾಲಿಸಿ (ಐಚ್ಛಿಕ)", generalLoss: "ಸಾಮಾನ್ಯ ಬೆಳೆ ಹಾನಿ ವರದಿ", lblPhoto: "ಹೊಲದ ಹಾನಿ ಫೋಟೋ",
            lblNotes: "ಹಾನಿಯ ವಿವರ", notesPh: "ಉದಾ: ಮಳೆಯಿಂದ ಬೆಳೆ ಜಲಾವೃತವಾಗಿದೆ",
            dossierHint: "ಮೇಲಿನ ಸ್ಥಳ ಅಥವಾ GPS ಬಳಸುತ್ತದೆ.", dossierBtn: "ವಿಮಾ ಸಾಕ್ಷ್ಯ ವರದಿ ತಯಾರಿಸಿ",
            listen: "ಕೇಳಿ", coverLabel: "ಅಂದಾಜು ವಿಮಾ ರಕ್ಷಣೆ", farmerPays: "ರೈತರ ಪಾಲು", govtPays: "ಸರ್ಕಾರಿ ಸಬ್ಸಿಡಿ",
            redBadge: "🚨 72-ಗಂಟೆ ವಿಮಾ ದೂರು ಎಚ್ಚರಿಕೆ", amberBadge: "⚠️ ಹವಾಮಾನ ನಿಗಾ", greenBadge: "✅ ಸುರಕ್ಷಿತ ಹವಾಮಾನ",
            todayRain: "ಇಂದು ಮಳೆ", gusts: "ಗಾಳಿ ವೇಗ", claimRef: "ಕ್ಲೈಮ್ ಸಂಖ್ಯೆ", locLabel: "ಸ್ಥಳ", loggedAt: "ಸಮಯ", weatherLog: "ಹವಾಮಾನ ದಾಖಲೆ", notesLabel: "ಟಿಪ್ಪಣಿ",
        },
        hi: {
            nav: "फसल बीमा", heroTag: "फसल सुरक्षा • PMFBY फसल बीमा कवच", helpline: "हेल्पलाइन: 14447",
            alertTitle: "लाइव 72-घंटे मौसम नुकसान अलर्ट",
            alertSub: "ओलावृष्टि, भारी बारिश और आंधी की जांच करें ताकि 72 घंटे के भीतर PMFBY दावा कर सकें।",
            locPh: "गांव, तहसील, जिला या पिन कोड...", checkBtn: "बीमा अलर्ट जांचें", checking: "लाइव मौसम अलर्ट की जांच हो रही है...",
            calcTitle: "🛡️ PMFBY प्रीमियम और कवर कैलकुलेटर", lblCrop: "फसल", lblSeason: "मौसम / सीजन", lblAcres: "ज़मीन (एकड़)",
            calcBtn: "प्रीमियम निकालें", saveBtn: "पॉलिसी सेव करें", vaultTitle: "📋 मेरी बीमित फसलें", activeUnit: "सक्रिय",
            noPol: "अभी कोई पॉलिसी सेव नहीं है। प्रीमियम निकालें और सेव करें।", remove: "हटाएं", acresUnit: "एकड़",
            dossierTitle: "📸 वन-क्लिक क्लेम सबूत रिपोर्ट",
            dossierSub: "खेत के नुकसान की फोटो, GPS, समय और मौसम रिकॉर्ड को एक रिपोर्ट में जोड़ें।",
            lblPolicy: "जुड़ी पॉलिसी (वैकल्पिक)", generalLoss: "सामान्य फसल नुकसान रिपोर्ट", lblPhoto: "खेत नुकसान फोटो",
            lblNotes: "नुकसान का विवरण", notesPh: "जैसे: भारी बारिश से फसल खराब",
            dossierHint: "ऊपर दी गई लोकेशन या GPS का उपयोग करता है।", dossierBtn: "क्लेम सबूत रिपोर्ट बनाएं",
            listen: "सुनें", coverLabel: "अनुमानित बीमा कवर", farmerPays: "किसान का हिस्सा", govtPays: "सरकारी सब्सिडी",
            redBadge: "🚨 72-घंटे क्लेम अलर्ट सक्रिय", amberBadge: "⚠️ मौसम चेतावनी", greenBadge: "✅ सुरक्षित मौसम",
            todayRain: "आज बारिश", gusts: "हवा झोंके", claimRef: "क्लेम नंबर", locLabel: "स्थान", loggedAt: "समय", weatherLog: "मौसम रिकॉर्ड", notesLabel: "विवरण",
        },
        ta: {
            nav: "பயிர் காப்பீடு", heroTag: "பசல் சுரக்ஷா • PMFBY பயிர் காப்பீடு", helpline: "உதவி எண்: 14447",
            alertTitle: "72-மணி நேர வானிலை சேத எச்சரிக்கை",
            alertSub: "ஆலங்கட்டி, கனமழை மற்றும் புயல் எச்சரிக்கைகளை சரிபார்த்து 72 மணி நேரத்தில் புகார் செய்யுங்கள்.",
            locPh: "ஊர், தாலுகா, மாவட்டம் அல்லது PIN...", checkBtn: "வானிலை எச்சரிக்கை பார்", checking: "நேரடி வானிலை சரிபார்க்கப்படுகிறது...",
            calcTitle: "🛡️ PMFBY காப்பீட்டு கட்டண கணிப்பான்", lblCrop: "பயிர்", lblSeason: "பருவம்", lblAcres: "நிலம் (ஏக்கர்)",
            calcBtn: "கட்டணம் கணக்கிடு", saveBtn: "பாலிசி சேமி", vaultTitle: "📋 எனது காப்பீட்டு பயிர்கள்", activeUnit: "செயலில்",
            noPol: "இன்னும் பாலிசி சேமிக்கவில்லை.", remove: "நீக்கு", acresUnit: "ஏக்கர்",
            dossierTitle: "📸 உரிமைகோரல் ஆதார அறிக்கை",
            dossierSub: "பயிர் சேத புகைப்படம், GPS, நேரம் மற்றும் வானிலை பதிவை ஒரே அறிக்கையாக உருவாக்குங்கள்.",
            lblPolicy: "தொடர்புடைய பாலிசி", generalLoss: "பொது பயிர் சேத அறிக்கை", lblPhoto: "சேதப் புகைப்படம்",
            lblNotes: "சேத விவரம்", notesPh: "எ.கா: கனமழையால் பயிர் சேதம்",
            dossierHint: "மேலே உள்ள இடம் அல்லது GPS பயன்படுத்தப்படும்.", dossierBtn: "ஆதார அறிக்கை உருவாக்கு",
            listen: "கேள்", coverLabel: "மதிப்பீட்டு காப்பீடு", farmerPays: "விவசாயி பங்கு", govtPays: "அரசு மானியம்",
            redBadge: "🚨 72-மணி நேர எச்சரிக்கை", amberBadge: "⚠️ வானிலை கண்காணிப்பு", greenBadge: "✅ பாதுகாப்பான வானிலை",
            todayRain: "இன்று மழை", gusts: "காற்று", claimRef: "உரிமை எண்", locLabel: "இடம்", loggedAt: "நேரம்", weatherLog: "வானிலை பதிவு", notesLabel: "குறிப்பு",
        },
        te: {
            nav: "పంట బీమా", heroTag: "ఫసల్ సురక్షా • PMFBY పంట బీమా", helpline: "హెల్ప్‌లైన్: 14447",
            alertTitle: "లైవ్ 72-గంటల వాతావరణ నష్ట హెచ్చరిక",
            alertSub: "వడగళ్ళు, భారీ వర్షం మరియు గాలుల హెచ్చరికలను తనిఖీ చేసి 72 గంటల్లోపు క్లెయిమ్ నమోదు చేయండి.",
            locPh: "గ్రామం, మండలం, జిల్లా లేదా PIN...", checkBtn: "వాతావరణ కవచం తనిఖీ", checking: "వాతావరణ హెచ్చరికలు తనిఖీ చేస్తున్నాము...",
            calcTitle: "🛡️ PMFBY ప్రీమియం & కవర్ కాలిక్యులేటర్", lblCrop: "పంట", lblSeason: "సీజన్", lblAcres: "భూమి (ఎకరాలు)",
            calcBtn: "ప్రీమియం లెక్కించు", saveBtn: "పాలసీ సేవ్ చేయి", vaultTitle: "📋 నా బీమా పంటలు", activeUnit: "యాక్టివ్",
            noPol: "ఇంకా పాలసీలు సేవ్ చేయలేదు.", remove: "తొలగించు", acresUnit: "ఎకరాలు",
            dossierTitle: "📸 క్లెయిమ్ సాక్ష్య నివేదిక",
            dossierSub: "పంట నష్టం ఫోటో, GPS, సమయం మరియు వాతావరణ రికార్డును ఒకే రిపోర్ట్‌గా తయారు చేయండి.",
            lblPolicy: "పాలసీ ఎంచుకోండి", generalLoss: "సాధారణ పంట నష్టం రిపోర్ట్", lblPhoto: "పంట నష్టం ఫోటో",
            lblNotes: "నష్టం వివరాలు", notesPh: "ఉదా: భారీ వర్షం వల్ల పంట నీటమునిగింది",
            dossierHint: "పైనున్న గ్రామం లేదా GPS ఉపయోగిస్తుంది.", dossierBtn: "క్లెయిమ్ రిపోర్ట్ తయారు చేయి",
            listen: "వినండి", coverLabel: "అంచనా బీమా కవర్", farmerPays: "రైతు వాటా", govtPays: "ప్రభుత్వ సబ్సిడీ",
            redBadge: "🚨 72-గంటల క్లెయిమ్ అలర్ట్", amberBadge: "⚠️ వాతావరణ నిఘా", greenBadge: "✅ సురక్షిత వాతావరణం",
            todayRain: "నేటి వర్షం", gusts: "గాలి వేగం", claimRef: "క్లెయిమ్ నంబర్", locLabel: "స్థలం", loggedAt: "సమయం", weatherLog: "వాతావరణ రికార్డు", notesLabel: "వివరణ",
        },
        mr: {
            nav: "पीक विमा", heroTag: "फसल सुरक्षा • PMFBY पीक विमा कवच", helpline: "हेल्पलाइन: 14447",
            alertTitle: "लाईव्ह 72-तास हवामान नुकसान इशारा",
            alertSub: "गारपीट, मुसळधार पाऊस व वादळाची तपासणी करून 72 तासांत विमा तक्रार नोंदवा.",
            locPh: "गाव, तालुका, जिल्हा किंवा पिन कोड...", checkBtn: "हवामान कवच तपासा", checking: "हवामान इशारा तपासत आहे...",
            calcTitle: "🛡️ PMFBY हप्ता आणि विमा संरक्षण कॅल्क्युलेटर", lblCrop: "पीक", lblSeason: "हंगाम", lblAcres: "जमीन (एकर)",
            calcBtn: "हप्ता मोजा", saveBtn: "पॉलिसी सेव्ह करा", vaultTitle: "📋 माझी विमा उतरवलेली पिके", activeUnit: "सक्रिय",
            noPol: "अजून कोणतीही पॉलिसी सेव्ह नाही.", remove: "काढा", acresUnit: "एकर",
            dossierTitle: "📸 वन-क्लिक क्लेम पुरावा अहवाल",
            dossierSub: "शेतातील नुकसानीचा फोटो, GPS, वेळ आणि हवामान नोंद एकत्र करून अहवाल तयार करा.",
            lblPolicy: "संबंधित पॉलिसी (ऐच्छिक)", generalLoss: "सामान्य पीक नुकसान अहवाल", lblPhoto: "नुकसानीचा फोटो",
            lblNotes: "नुकसानीचे वर्णन", notesPh: "उदा: अतिवृष्टीमुळे पिकाचे नुकसान",
            dossierHint: "वरील गाव किंवा GPS वापरते.", dossierBtn: "क्लेम पुरावा अहवाल तयार करा",
            listen: "ऐका", coverLabel: "अंदाजे विमा संरक्षण", farmerPays: "शेतकरी हिस्सा", govtPays: "सरकारी अनुदान",
            redBadge: "🚨 72-तास क्लेम इशारा सक्रिय", amberBadge: "⚠️ हवामान सतर्कता", greenBadge: "✅ सुरक्षित हवामान",
            todayRain: "आजचा पाऊस", gusts: "वारा वेग", claimRef: "क्लेम क्रमांक", locLabel: "ठिकाण", loggedAt: "वेळ", weatherLog: "हवामान नोंद", notesLabel: "टीप",
        },
    };

    function lang() {
        return (langSelect && langSelect.value) || "en";
    }

    function esc(s) {
        return String(s || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function playAudio(text) {
        if (!text) return;
        if (insAudio) {
            insAudio.pause();
            insAudio = null;
        }
        fetch("/api/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, lang: lang() }),
        })
            .then(r => {
                if (!r.ok) throw new Error("tts fallback");
                return r.blob();
            })
            .then(blob => {
                const url = URL.createObjectURL(blob);
                insAudio = new Audio(url);
                insAudio.play().catch(() => {});
            })
            .catch(() => {
                if ("speechSynthesis" in window) {
                    const u = new SpeechSynthesisUtterance(text);
                    window.speechSynthesis.speak(u);
                }
            });
    }

    function applyI18n() {
        const l = lang();
        const t = INS_I18N[l] || INS_I18N.en;
        const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        set("navInsuranceLabel", t.nav);
        set("insHeroTag", t.heroTag);
        set("insHelplineBadge", t.helpline);
        set("insAlertTitle", t.alertTitle);
        set("insAlertSubtitle", t.alertSub);
        set("insCheckAlertBtnLabel", t.checkBtn);
        set("insCalcTitle", t.calcTitle);
        set("lblInsCrop", t.lblCrop);
        set("lblInsSeason", t.lblSeason);
        set("lblInsAcres", t.lblAcres);
        set("insCalcBtnLabel", t.calcBtn);
        set("insSaveBtnLabel", t.saveBtn);
        set("insVaultTitle", t.vaultTitle);
        set("insDossierTitle", t.dossierTitle);
        set("insDossierSubtitle", t.dossierSub);
        set("lblClaimPolicy", t.lblPolicy);
        set("lblClaimPhoto", t.lblPhoto);
        set("lblClaimNotes", t.lblNotes);
        set("insDossierHint", t.dossierHint);
        set("insDossierBtnLabel", t.dossierBtn);

        if (locInput) locInput.placeholder = t.locPh;
        if (claimNotesInput) claimNotesInput.placeholder = t.notesPh;

        const cMap = CROP_LABELS[l] || CROP_LABELS.en;
        if (cropSelect) {
            Array.from(cropSelect.options).forEach(opt => {
                if (cMap[opt.value]) opt.textContent = cMap[opt.value];
            });
        }
        const sMap = SEASON_LABELS[l] || SEASON_LABELS.en;
        if (seasonSelect) {
            Array.from(seasonSelect.options).forEach(opt => {
                if (sMap[opt.value]) opt.textContent = sMap[opt.value];
            });
        }
    }

    async function checkWeatherAlert() {
        if (!alertOutput) return;
        const t = INS_I18N[lang()] || INS_I18N.en;
        const loc = (locInput && locInput.value.trim()) || "";
        alertOutput.innerHTML = `<div class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 animate-pulse">${esc(t.checking)}</div>`;

        const params = new URLSearchParams({ language: lang() });
        if (loc) params.set("location", loc);
        if (gpsLat !== null && gpsLon !== null && !loc) {
            params.set("lat", gpsLat);
            params.set("lon", gpsLon);
        }

        try {
            const resp = await fetch(`/api/insurance/weather-alert?${params.toString()}`);
            const data = await resp.json();
            if (!resp.ok || data.status !== "success") {
                alertOutput.innerHTML = `<div class="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-950 font-semibold">${esc(data.message || t.locPh)}</div>`;
                return;
            }
            lastAlertChecked = true;
            if (locInput && !locInput.value.trim() && data.location) {
                locInput.value = data.location;
            }

            const level = data.alert_level;
            const cardCls = level === "RED_72H_CLAIM"
                ? "bg-red-50 border-red-300 text-red-950"
                : level === "AMBER_WATCH"
                ? "bg-amber-50 border-amber-300 text-amber-950"
                : "bg-emerald-50 border-emerald-200 text-emerald-950";
            const badgeText = level === "RED_72H_CLAIM" ? t.redBadge : (level === "AMBER_WATCH" ? t.amberBadge : t.greenBadge);

            const tel = data.telemetry || {};
            alertOutput.innerHTML = `
                <div class="p-4 rounded-2xl border-2 ${cardCls} space-y-2.5">
                    <div class="flex flex-wrap items-center justify-between gap-2">
                        <span class="font-extrabold text-xs">${badgeText} • ${esc(data.location)}</span>
                        <button type="button" id="insAlertSpeakBtn" class="px-2.5 py-1 rounded-lg bg-white border border-gray-300 text-[11px] font-bold text-gray-800 hover:bg-gray-50">
                            <i class="fa-solid fa-volume-high mr-1"></i>${esc(t.listen)}
                        </button>
                    </div>
                    <p class="text-xs leading-relaxed font-medium">${esc(data.advisory)}</p>
                    <div class="flex flex-wrap gap-2 text-[11px] font-bold">
                        <span class="px-2 py-0.5 rounded-lg bg-white/90 border border-gray-200">🌡️ ${esc(tel.temperature_c)}°C</span>
                        <span class="px-2 py-0.5 rounded-lg bg-white/90 border border-gray-200">🌧️ ${esc(t.todayRain)}: ${esc(tel.rain_today_mm)} mm</span>
                        <span class="px-2 py-0.5 rounded-lg bg-white/90 border border-gray-200">💨 ${esc(t.gusts)}: ${esc(tel.wind_gusts_kmh)} km/h</span>
                    </div>
                </div>
            `;
            const speakBtn = document.getElementById("insAlertSpeakBtn");
            if (speakBtn) speakBtn.addEventListener("click", () => playAudio(data.speech_text));
        } catch (_) {
            alertOutput.innerHTML = `<div class="p-3 rounded-xl bg-red-50 border border-red-200 text-red-800">Network error checking weather trigger.</div>`;
        }
    }

    async function calculateQuote() {
        if (!quoteOutput) return;
        const params = new URLSearchParams({
            crop: cropSelect.value,
            season: seasonSelect.value,
            acres: acresInput.value || "1",
            language: lang(),
        });
        const resp = await fetch(`/api/insurance/quote?${params.toString()}`);
        const d = await resp.json();
        if (!resp.ok || d.status !== "success") {
            quoteOutput.innerHTML = `<div class="p-3 rounded-xl bg-red-50 border border-red-200 text-red-800">${esc(d.message)}</div>`;
            return;
        }
        const t = INS_I18N[lang()] || INS_I18N.en;
        quoteOutput.innerHTML = `
            <div class="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200 space-y-2.5">
                <div class="grid grid-cols-3 gap-2 text-center">
                    <div class="p-2 rounded-xl bg-white border border-amber-200">
                        <div class="text-[10px] text-gray-500 font-bold uppercase">${esc(t.coverLabel)}</div>
                        <div class="text-sm font-extrabold text-green-900">₹${Number(d.sum_insured_inr).toLocaleString("en-IN")}</div>
                    </div>
                    <div class="p-2 rounded-xl bg-white border border-emerald-300">
                        <div class="text-[10px] text-gray-500 font-bold uppercase">${esc(t.farmerPays)}</div>
                        <div class="text-sm font-extrabold text-emerald-700">₹${Number(d.farmer_premium_inr).toLocaleString("en-IN")} (${d.farmer_premium_pct}%)</div>
                    </div>
                    <div class="p-2 rounded-xl bg-white border border-sky-200">
                        <div class="text-[10px] text-gray-500 font-bold uppercase">${esc(t.govtPays)}</div>
                        <div class="text-sm font-extrabold text-sky-800">~₹${Number(d.govt_subsidy_estimate_inr).toLocaleString("en-IN")}</div>
                    </div>
                </div>
                <p class="text-xs text-gray-800 leading-relaxed">${esc(d.summary)}</p>
                <div class="flex items-center justify-between text-[11px] text-amber-900 font-semibold">
                    <span>📅 ${esc(d.season_label || d.cutoff_guidance)}</span>
                    <button type="button" id="insQuoteSpeakBtn" class="px-2 py-0.5 rounded-lg bg-white border border-amber-300 hover:bg-amber-100">
                        <i class="fa-solid fa-volume-high mr-1"></i>${esc(t.listen)}
                    </button>
                </div>
            </div>
        `;
        const qSpeak = document.getElementById("insQuoteSpeakBtn");
        if (qSpeak) qSpeak.addEventListener("click", () => playAudio(d.speech_text));
    }

    async function loadPolicies() {
        if (!policiesList) return;
        const l = lang();
        const t = INS_I18N[l] || INS_I18N.en;
        const cMap = CROP_LABELS[l] || CROP_LABELS.en;
        const sMap = SEASON_LABELS[l] || SEASON_LABELS.en;

        const resp = await fetch("/api/insurance/policies");
        const data = await resp.json();
        const items = (data && data.policies) || [];
        if (policyCount) policyCount.textContent = `${items.length} ${t.activeUnit}`;

        if (claimPolicySelect) {
            const curr = claimPolicySelect.value;
            claimPolicySelect.innerHTML = `<option value="">${esc(t.generalLoss)}</option>` +
                items.map(p => `<option value="${esc(p.id)}">${esc(cMap[p.crop] || p.crop)} • ${p.acres} ${esc(t.acresUnit)}</option>`).join("");
            claimPolicySelect.value = curr;
        }

        if (!items.length) {
            policiesList.innerHTML = `<div class="p-3 rounded-xl bg-green-50/50 border border-dashed border-green-300 text-gray-500">${esc(t.noPol)}</div>`;
            return;
        }

        policiesList.innerHTML = items.map(p => `
            <div class="p-3 rounded-xl bg-green-50/70 border border-green-200 flex items-center justify-between gap-2">
                <div>
                    <div class="font-extrabold text-green-950">${esc(cMap[p.crop] || p.crop)} (${esc(sMap[p.season] || p.season)}) • ${p.acres} ${esc(t.acresUnit)}</div>
                    <div class="text-[11px] text-gray-600">${esc(t.coverLabel)}: ₹${Number(p.sum_insured_inr).toLocaleString("en-IN")} • ${esc(t.farmerPays)}: ₹${Number(p.farmer_premium_inr).toLocaleString("en-IN")}</div>
                </div>
                <button type="button" class="del-policy-btn px-2.5 py-1 rounded-lg bg-white hover:bg-red-50 text-red-600 border border-red-200 text-[11px] font-bold" data-id="${esc(p.id)}">
                    ${esc(t.remove)}
                </button>
            </div>
        `).join("");

        policiesList.querySelectorAll(".del-policy-btn").forEach(btn => {
            btn.addEventListener("click", async () => {
                await fetch(`/api/insurance/policy/${encodeURIComponent(btn.getAttribute("data-id"))}`, { method: "DELETE" });
                loadPolicies();
            });
        });
    }

    async function savePolicy() {
        const resp = await fetch("/api/insurance/policy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                crop: cropSelect.value,
                season: seasonSelect.value,
                acres: parseFloat(acresInput.value || "1"),
                language: lang(),
            }),
        });
        if (resp.ok) {
            await calculateQuote();
            await loadPolicies();
        }
    }

    function renderDossierCard(c) {
        const t = INS_I18N[lang()] || INS_I18N.en;
        const snap = c.weather_snapshot || {};
        const tel = snap.telemetry || {};
        return `
            <div class="p-4 rounded-2xl bg-sky-50/60 border-2 border-sky-300 space-y-2.5">
                <div class="flex flex-wrap items-center justify-between gap-2 border-b border-sky-200 pb-2">
                    <span class="font-extrabold text-sky-950">📄 ${esc(t.claimRef)}: ${esc(c.claim_ref || c.id)}</span>
                    <span class="text-[11px] font-bold px-2 py-0.5 rounded-full bg-white border border-sky-300 text-sky-900">${esc(c.weather_event)}</span>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    <div><strong>📍 ${esc(t.locLabel)}:</strong> ${esc(snap.location || "N/A")} (${c.gps_lat ?? "--"}, ${c.gps_lon ?? "--"})</div>
                    <div><strong>🕒 ${esc(t.loggedAt)}:</strong> ${esc((c.created_at || "").replace("T", " ").slice(0, 19))} UTC</div>
                    <div><strong>🌧️ ${esc(t.weatherLog)}:</strong> ${esc(tel.weather_condition || "--")}, ${esc(t.todayRain)}: ${esc(tel.rain_today_mm ?? "--")} mm, ${esc(t.gusts)}: ${esc(tel.wind_gusts_kmh ?? "--")} km/h</div>
                    <div><strong>📝 ${esc(t.notesLabel)}:</strong> ${esc(c.notes || "--")}</div>
                </div>
                ${c.photo_url ? `<img src="${esc(c.photo_url)}" alt="Field damage evidence" class="w-40 h-28 object-cover rounded-xl border border-sky-300">` : ""}
                ${Array.isArray(c.checklist) ? `<ul class="list-disc pl-5 space-y-0.5 text-[11px] text-sky-950">${c.checklist.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
            </div>
        `;
    }

    async function createDossier() {
        const fd = new FormData();
        fd.append("location", (locInput && locInput.value.trim()) || "");
        if (gpsLat !== null && gpsLon !== null) {
            fd.append("lat", gpsLat);
            fd.append("lon", gpsLon);
        }
        if (claimPolicySelect && claimPolicySelect.value) {
            fd.append("policy_id", claimPolicySelect.value);
        }
        fd.append("notes", (claimNotesInput && claimNotesInput.value.trim()) || "");
        fd.append("language", lang());
        if (claimPhotoInput && claimPhotoInput.files && claimPhotoInput.files[0]) {
            fd.append("photo", claimPhotoInput.files[0]);
        }

        const resp = await fetch("/api/insurance/claim-dossier", { method: "POST", body: fd });
        const data = await resp.json();
        if (!resp.ok || data.status !== "success") {
            dossierOutput.innerHTML = `<div class="p-3 rounded-xl bg-red-50 border border-red-200 text-red-800">${esc(data.message || "Could not create dossier.")}</div>`;
            return;
        }
        dossierOutput.innerHTML = renderDossierCard(data.claim);
    }

    if (gpsBtn) {
        gpsBtn.addEventListener("click", () => {
            if (!navigator.geolocation) return;
            navigator.geolocation.getCurrentPosition(pos => {
                gpsLat = Number(pos.coords.latitude.toFixed(4));
                gpsLon = Number(pos.coords.longitude.toFixed(4));
                if (locInput) locInput.value = "";
                checkWeatherAlert();
            });
        });
    }

    if (checkAlertBtn) checkAlertBtn.addEventListener("click", checkWeatherAlert);
    if (calcBtn) calcBtn.addEventListener("click", calculateQuote);
    if (savePolicyBtn) savePolicyBtn.addEventListener("click", savePolicy);
    if (createDossierBtn) createDossierBtn.addEventListener("click", createDossier);

    if (langSelect) {
        langSelect.addEventListener("change", () => {
            applyI18n();
            calculateQuote();
            loadPolicies();
            if (lastAlertChecked) checkWeatherAlert();
        });
    }

    applyI18n();
    calculateQuote();
    loadPolicies();
});
