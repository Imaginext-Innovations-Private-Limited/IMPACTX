"""Welfare Scheme Navigator - single-file Streamlit app.

Run:  streamlit run app.py
Files needed in the same folder: scheme_data.json
API key: put GROQ_API_KEY in .streamlit/secrets.toml (or set it as an environment
variable). NEVER write the key in this file.
"""
import json
import os
import re
from pathlib import Path

import streamlit as st
from fpdf import FPDF
from groq import Groq
from streamlit_float import float_init

# ----------------------------------------------------------------- constants
DATA_FILE = Path(__file__).parent / "scheme_data.json"
MODEL = "openai/gpt-oss-20b"
SENIOR_AGE = 60
NATIONAL = {"All India", "Other state"}      # schemes available in every state
ALL_GENDERS = ["Male", "Female", "Other"]
ALL_CASTES = ["General", "OBC", "SC", "ST"]
OCCUPATIONS = ["Student", "Farmer", "Business", "Other"]
NEED_OPTIONS = [
    "Education / Scholarship",
    "Employment / Internship",
    "Healthcare",
    "Housing",
    "Women & Girl Child",
    "Senior Citizen",
    "Agriculture",
    "Business / Self-Employment",
    "Financial Assistance",
    "Food / Basic Needs",
]

NEED_KEYWORDS = {
    "Education / Scholarship": {"education", "scholarship", "student", "students", "school", "college", "university", "study", "academic", "tuition", "fee", "fees", "fellowship", "pragati"},
    "Employment / Internship": {"employment", "internship", "intern", "job", "jobs", "skill", "skills", "training", "placement", "career", "apprentice", "apprenticeship", "work", "worker", "unemployed"},
    "Healthcare": {"health", "healthcare", "medical", "medicine", "hospital", "treatment", "insurance", "disease", "surgery", "maternal", "maternity", "pregnancy", "disability", "ayushman"},
    "Housing": {"housing", "house", "home", "construction", "shelter", "roof", "awas", "pmay"},
    "Women & Girl Child": {"women", "woman", "girl", "girls", "female", "widow", "maternity", "mother", "child", "girl child", "sukanya", "mahila", "pragati"},
    "Senior Citizen": {"senior", "elderly", "old age", "pension", "retirement", "aged", "elder", "senior citizen"},
    "Agriculture": {"agriculture", "farmer", "farmers", "farming", "crop", "crops", "kisan", "irrigation", "fertilizer", "seed", "seeds", "livestock", "dairy", "agri"},
    "Business / Self-Employment": {"business", "enterprise", "entrepreneur", "entrepreneurship", "startup", "self employment", "self-employment", "loan", "msme", "micro", "small business", "vendor", "mudra"},
    "Financial Assistance": {"financial", "assistance", "benefit", "cash", "grant", "subsidy", "support", "savings", "income support", "stipend", "pension", "loan", "credit"},
    "Food / Basic Needs": {"food", "ration", "nutrition", "basic needs", "cooking", "gas", "lpg", "pds", "ration card", "meal", "essential"},
}
STATES = [
    "Other state",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry"
]

STOPWORDS = {
    "the", "a", "an", "is", "are", "for", "to", "of", "in", "and", "or", "i", "me", "my",
    "can", "how", "what", "do", "does", "get", "scheme", "schemes", "apply", "tell",
    "about", "which", "who", "it", "this", "that",
}

# ---------------------------------------------------------------- page setup
st.set_page_config(
    page_title="Welfare Scheme Navigator",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)
float_init()

# Dark glassmorphism theme. We only hide the footer: hiding the whole header would
# also hide the button that re-opens the sidebar (where the language selector is).
st.markdown("""
<style>
    h1 {
        background: -webkit-linear-gradient(45deg, #FF9933, #FFFFFF, #138808);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900 !important;
        text-align: center;
        padding-bottom: 20px;
    }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #FF7E5F, #FEB47B) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
        font-weight: bold !important;
        box-shadow: 0 4px 15px rgba(255, 126, 95, 0.4) !important;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(255, 126, 95, 0.6) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px) !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(255, 126, 95, 0.5) !important;
    }
    div[data-testid="stPopover"] > button {
        background: #FF7E5F !important;
        border-radius: 50px !important;
        height: 65px !important;
        width: 65px !important;
        font-size: 24px !important;
        padding: 0 !important;
        box-shadow: 0 10px 25px rgba(255, 126, 95, 0.5) !important;
        border: 2px solid rgba(255,255,255,0.2) !important;
    }
    div[data-testid="stPopoverBody"] {
        width: 400px !important;
        max-width: 90vw !important;
        height: 550px !important;
        max-height: 80vh !important;
    }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ UI text
LANG_TEXT = {
    "English": {
        "title": "Welfare Scheme Navigator 🤝",
        "subtitle": "Your AI-powered guide to discovering, understanding, and applying for government welfare schemes.",
        "personal": "👤 Personal Details",
        "financial": "💼 Financial & Social Details",
        "location": "📍 Location",
        "name_label": "Full Name",
        "age": "Select Your Age",
        "gender_label": "Gender",
        "income": "Annual Income (₹)",
        "occupation": "Occupation / Status",
        "caste_label": "Social Category",
        "state": "Select State",
        "check_btn": "Check Eligibility",
        "found_msg": "Found {n} scheme(s) matching your profile!",
        "no_match": "No schemes found for your specific details. Try adjusting your filters.",
        "report_header": "📥 Download Eligibility Report (PDF)",
        "benefit": "💰 Financial Benefit:",
        "overview": "🎯 Overview:",
        "checklist_header": "📋 Document Checklist:",
        "apply": "🔗 Apply on Official Website",
        "verified": "Last verified: {d}",
        "compare_header": "⚖️ Scheme Comparison Tool",
        "compare_sub": "Select schemes below to compare their benefits and eligibility side-by-side.",
        "compare_select": "Select schemes to compare:",
        "col_name": "Scheme Name",
        "col_category": "Category",
        "col_benefit": "Financial Benefit",
        "col_income": "Max Income Limit",
        "no_limit": "No limit",
        "chat_header": "🤖 AI Scheme Assistant",
        "chat_sub": "Ask any questions regarding scheme documents, eligibility, benefits, or application procedures!",
        "chat_placeholder": "Ask about any scheme...",
        "thinking": "Searching database & thinking...",
        "no_key": "The AI assistant isn't set up yet: add GROQ_API_KEY to the Streamlit secrets.",
        "ai_error": "Could not reach the AI assistant. Please try again.",
        "data_error": "Could not load scheme_data.json. Check that the file exists and is valid JSON. Details:",
        "pdf_error": "The PDF report could not be created.",
        "disclaimer": "This information is a guide only. Always confirm eligibility and documents on the official scheme website before applying.",
    },
    "हिंदी": {
        "title": "सरकारी योजना फाइंडर 📜",
        "subtitle": "अपनी प्रोफ़ाइल के अनुसार सरकारी योजनाएं खोजें, दस्तावेज़ ट्रैक करें और AI सहायक से बात करें।",
        "personal": "👤 व्यक्तिगत जानकारी",
        "financial": "💼 आर्थिक और सामाजिक जानकारी",
        "location": "📍 स्थान",
        "name_label": "पूरा नाम",
        "age": "अपनी आयु चुनें",
        "gender_label": "लिंग",
        "income": "वार्षिक आय (₹)",
        "occupation": "व्यवसाय / स्थिति",
        "caste_label": "सामाजिक श्रेणी",
        "state": "राज्य चुनें",
        "check_btn": "पात्रता जांचें",
        "found_msg": "आपकी प्रोफ़ाइल के अनुसार {n} योजना(एं) मिलीं!",
        "no_match": "आपकी विशिष्ट जानकारी के अनुसार कोई योजना नहीं मिली। कृपया अपने फ़िल्टर बदलकर प्रयास करें।",
        "report_header": "📥 पात्रता रिपोर्ट डाउनलोड करें (PDF)",
        "benefit": "💰 आर्थिक लाभ:",
        "overview": "🎯 विवरण:",
        "checklist_header": "📋 दस्तावेज़ चेकलिस्ट:",
        "apply": "🔗 आधिकारिक वेबसाइट पर आवेदन करें",
        "verified": "अंतिम सत्यापन: {d}",
        "compare_header": "⚖️ योजना तुलना टूल",
        "compare_sub": "उनके लाभों और पात्रता की तुलना करने के लिए नीचे योजनाएं चुनें。",
        "compare_select": "तुलना के लिए योजनाएं चुनें:",
        "col_name": "योजना का नाम",
        "col_category": "श्रेणी",
        "col_benefit": "आर्थिक लाभ",
        "col_income": "अधिकतम आय सीमा",
        "no_limit": "कोई सीमा नहीं",
        "chat_header": "🤖 एआई योजना सहायक",
        "chat_sub": "योजना दस्तावेजों, पात्रता, लाभ या आवेदन प्रक्रियाओं से जुड़े कोई भी सवाल पूछें!",
        "chat_placeholder": "किसी भी योजना के बारे में पूछें...",
        "thinking": "योजनाएं खोजी जा रही हैं...",
        "no_key": "AI सहायक अभी सेट नहीं है: Streamlit secrets में GROQ_API_KEY जोड़ें।",
        "ai_error": "AI सहायक से संपर्क नहीं हो सका। कृपया दोबारा कोशिश करें।",
        "data_error": "scheme_data.json लोड नहीं हो सकी। जांचें कि फ़ाइल मौजूद है और सही JSON है। विवरण:",
        "pdf_error": "PDF रिपोर्ट नहीं बन सकी।",
        "disclaimer": "यह जानकारी केवल मार्गदर्शन के लिए है। आवेदन से पहले आधिकारिक वेबसाइट पर पात्रता और दस्तावेज़ ज़रूर जांचें。",
    },
    "ಕನ್ನಡ": {
        "title": "ಸರ್ಕಾರಿ ಯೋಜನೆ ನ್ಯಾವಿಗೇಟರ್ 🤝", "subtitle": "ಸರ್ಕಾರಿ ಕಲ್ಯಾಣ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಲು, ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ಮತ್ತು ಅರ್ಜಿ ಸಲ್ಲಿಸಲು AI ಸಹಾಯಕ.",
        "personal": "👤 ವೈಯಕ್ತಿಕ ವಿವರಗಳು", "financial": "💼 ಆರ್ಥಿಕ ಮತ್ತು ಸಾಮಾಜಿಕ ವಿವರಗಳು", "location": "📍 ಸ್ಥಳ",
        "name_label": "ಪೂರ್ಣ ಹೆಸರು", "age": "ನಿಮ್ಮ ವಯಸ್ಸನ್ನು ಆಯ್ಕೆಮಾಡಿ", "gender_label": "ಲಿಂಗ", "income": "ವಾರ್ಷಿಕ ಆದಾಯ (₹)",
        "occupation": "ಉದ್ಯೋಗ / ಸ್ಥಿತಿ", "caste_label": "ಸಾಮಾಜಿಕ ವರ್ಗ", "state": "ರಾಜ್ಯ ಆಯ್ಕೆಮಾಡಿ", "check_btn": "ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ",
        "found_msg": "ನಿಮ್ಮ ಪ್ರೊಫೈಲ್‌ಗೆ ಹೊಂದುವ {n} ಯೋಜನೆ(ಗಳು) ಕಂಡುಬಂದಿವೆ!", "no_match": "ನಿಮ್ಮ ವಿವರಗಳಿಗೆ ಯಾವುದೇ ಯೋಜನೆ ಕಂಡುಬಂದಿಲ್ಲ. ಫಿಲ್ಟರ್‌ಗಳನ್ನು ಬದಲಿಸಿ ಪ್ರಯತ್ನಿಸಿ.",
        "report_header": "📥 ಅರ್ಹತಾ ವರದಿ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ (PDF)", "benefit": "💰 ಆರ್ಥಿಕ ಪ್ರಯೋಜನ:", "overview": "🎯 ಅವಲೋಕನ:",
        "checklist_header": "📋 ದಾಖಲೆಗಳ ಪಟ್ಟಿ:", "apply": "🔗 ಅಧಿಕೃತ ವೆಬ್‌ಸೈಟ್‌ನಲ್ಲಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ", "verified": "ಕೊನೆಯ ಪರಿಶೀಲನೆ: {d}",
        "compare_header": "⚖️ ಯೋಜನೆ ಹೋಲಿಕೆ ಸಾಧನ", "compare_sub": "ಪ್ರಯೋಜನ ಮತ್ತು ಅರ್ಹತೆಯನ್ನು ಹೋಲಿಸಲು ಕೆಳಗಿನ ಯೋಜನೆಗಳನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
        "compare_select": "ಹೋಲಿಸಲು ಯೋಜನೆಗಳನ್ನು ಆಯ್ಕೆಮಾಡಿ:", "col_name": "ಯೋಜನೆಯ ಹೆಸರು", "col_category": "ವರ್ಗ", "col_benefit": "ಆರ್ಥಿಕ ಪ್ರಯೋಜನ", "col_income": "ಗರಿಷ್ಠ ಆದಾಯ ಮಿತಿ", "no_limit": "ಮಿತಿ ಇಲ್ಲ",
        "chat_header": "🤖 AI ಯೋಜನೆ ಸಹಾಯಕ", "chat_sub": "ಯೋಜನೆಗಳ ದಾಖಲೆಗಳು, ಅರ್ಹತೆ, ಪ್ರಯೋಜನಗಳು ಅಥವಾ ಅರ್ಜಿ ಪ್ರಕ್ರಿಯೆಯ ಬಗ್ಗೆ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ!", "chat_placeholder": "ಯಾವುದೇ ಯೋಜನೆಯ ಬಗ್ಗೆ ಕೇಳಿ...", "thinking": "ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಲಾಗುತ್ತಿದೆ...",
        "no_key": "AI ಸಹಾಯಕವನ್ನು ಇನ್ನೂ ಹೊಂದಿಸಲಾಗಿಲ್ಲ: Streamlit secrets ನಲ್ಲಿ GROQ_API_KEY ಸೇರಿಸಿ.", "ai_error": "AI ಸಹಾಯಕವನ್ನು ಸಂಪರ್ಕಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
        "data_error": "scheme_data.json ಲೋಡ್ ಆಗಲಿಲ್ಲ. ಫೈಲ್ ಸರಿಯಿದೆಯೇ ಎಂದು ಪರಿಶೀಲಿಸಿ. ವಿವರ:", "pdf_error": "PDF ವರದಿಯನ್ನು ರಚಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.", "disclaimer": "ಈ ಮಾಹಿತಿ ಮಾರ್ಗದರ್ಶನಕ್ಕಾಗಿ ಮಾತ್ರ. ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ಮೊದಲು ಅಧಿಕೃತ ವೆಬ್‌ಸೈಟ್‌ನಲ್ಲಿ ಅರ್ಹತೆ ಮತ್ತು ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."
    },
    "தமிழ்": {
        "title": "அரசு நலத்திட்ட வழிகாட்டி 🤝", "subtitle": "அரசு நலத்திட்டங்களை கண்டறிந்து, புரிந்துகொண்டு, விண்ணப்பிக்க AI வழிகாட்டி.",
        "personal": "👤 தனிப்பட்ட விவரங்கள்", "financial": "💼 பொருளாதார மற்றும் சமூக விவரங்கள்", "location": "📍 இருப்பிடம்",
        "name_label": "முழுப் பெயர்", "age": "உங்கள் வயதைத் தேர்ந்தெடுக்கவும்", "gender_label": "பாலினம்", "income": "ஆண்டு வருமானம் (₹)",
        "occupation": "தொழில் / நிலை", "caste_label": "சமூகப் பிரிவு", "state": "மாநிலத்தைத் தேர்ந்தெடுக்கவும்", "check_btn": "தகுதியைச் சரிபார்க்கவும்",
        "found_msg": "உங்கள் சுயவிவரத்துடன் பொருந்தும் {n} திட்டங்கள் கிடைத்தன!", "no_match": "உங்கள் விவரங்களுக்கு திட்டங்கள் எதுவும் கிடைக்கவில்லை. வடிகட்டிகளை மாற்றி முயற்சிக்கவும்.",
        "report_header": "📥 தகுதி அறிக்கையைப் பதிவிறக்கவும் (PDF)", "benefit": "💰 நிதிப் பயன்:", "overview": "🎯 மேலோட்டம்:", "checklist_header": "📋 ஆவணப் பட்டியல்:",
        "apply": "🔗 அதிகாரப்பூர்வ இணையதளத்தில் விண்ணப்பிக்கவும்", "verified": "கடைசியாக சரிபார்த்தது: {d}", "compare_header": "⚖️ திட்ட ஒப்பீட்டு கருவி", "compare_sub": "பயன்கள் மற்றும் தகுதியை ஒப்பிட கீழே திட்டங்களைத் தேர்ந்தெடுக்கவும்.", "compare_select": "ஒப்பிட திட்டங்களைத் தேர்ந்தெடுக்கவும்:",
        "col_name": "திட்டத்தின் பெயர்", "col_category": "வகை", "col_benefit": "நிதிப் பயன்", "col_income": "அதிகபட்ச வருமான வரம்பு", "no_limit": "வரம்பு இல்லை",
        "chat_header": "🤖 AI திட்ட உதவியாளர்", "chat_sub": "ஆவணங்கள், தகுதி, பயன்கள் அல்லது விண்ணப்ப நடைமுறை பற்றி கேளுங்கள்!", "chat_placeholder": "எந்த திட்டத்தைப் பற்றியும் கேளுங்கள்...", "thinking": "திட்டங்கள் தேடப்படுகின்றன...", "no_key": "AI உதவியாளர் அமைக்கப்படவில்லை: Streamlit secrets-ல் GROQ_API_KEY சேர்க்கவும்.", "ai_error": "AI உதவியாளரை அணுக முடியவில்லை. மீண்டும் முயற்சிக்கவும்.", "data_error": "scheme_data.json ஏற்ற முடியவில்லை. விவரங்கள்:", "pdf_error": "PDF அறிக்கையை உருவாக்க முடியவில்லை.", "disclaimer": "இந்த தகவல் வழிகாட்டுதலுக்காக மட்டுமே. விண்ணப்பிக்கும் முன் அதிகாரப்பூர்வ இணையதளத்தில் தகுதி மற்றும் ஆவணங்களைச் சரிபார்க்கவும்."
    },
    "తెలుగు": {
        "title": "ప్రభుత్వ సంక్షేమ పథకాల నావిగేటర్ 🤝", "subtitle": "ప్రభుత్వ సంక్షేమ పథకాలను కనుగొని, అర్థం చేసుకుని, దరఖాస్తు చేసుకోవడానికి AI మార్గదర్శి.",
        "personal": "👤 వ్యక్తిగత వివరాలు", "financial": "💼 ఆర్థిక మరియు సామాజిక వివరాలు", "location": "📍 స్థానం", "name_label": "పూర్తి పేరు", "age": "మీ వయస్సును ఎంచుకోండి", "gender_label": "లింగం", "income": "వార్షిక ఆదాయం (₹)", "occupation": "వృత్తి / స్థితి", "caste_label": "సామాజిక వర్గం", "state": "రాష్ట్రాన్ని ఎంచుకోండి", "check_btn": "అర్హతను తనిఖీ చేయండి",
        "found_msg": "మీ ప్రొఫైల్‌కు సరిపడే {n} పథకాలు కనుగొనబడ్డాయి!", "no_match": "మీ వివరాలకు పథకాలు కనుగొనబడలేదు. ఫిల్టర్లను మార్చి ప్రయత్నించండి.", "report_header": "📥 అర్హత నివేదికను డౌన్‌లోడ్ చేయండి (PDF)", "benefit": "💰 ఆర్థిక ప్రయోజనం:", "overview": "🎯 అవలోకనం:", "checklist_header": "📋 పత్రాల జాబితా:", "apply": "🔗 అధికారిక వెబ్‌సైట్‌లో దరఖాస్తు చేయండి", "verified": "చివరిగా ధృవీకరించినది: {d}", "compare_header": "⚖️ పథకాల పోలిక సాధనం", "compare_sub": "ప్రయోజనాలు మరియు అర్హతలను పోల్చడానికి పథకాలను ఎంచుకోండి.", "compare_select": "పోల్చడానికి పథకాలను ఎంచుకోండి:", "col_name": "పథకం పేరు", "col_category": "వర్గం", "col_benefit": "ఆర్థిక ప్రయోజనం", "col_income": "గరిష్ఠ ఆదాయ పరిమితి", "no_limit": "పరిమితి లేదు", "chat_header": "🤖 AI పథక సహాయకుడు", "chat_sub": "పథకాల పత్రాలు, అర్హత, ప్రయోజనాలు లేదా దరఖాస్తు విధానం గురించి అడగండి!", "chat_placeholder": "ఏ పథకం గురించి అయినా అడగండి...", "thinking": "పథకాలు వెతుకుతున్నాము...", "no_key": "AI సహాయకుడు సెటప్ కాలేదు: Streamlit secrets లో GROQ_API_KEY జోడించండి.", "ai_error": "AI సహాయకుడిని చేరుకోలేకపోయాము. మళ్లీ ప్రయత్నించండి.", "data_error": "scheme_data.json లోడ్ కాలేదు. వివరాలు:", "pdf_error": "PDF నివేదికను సృష్టించలేకపోయాము.", "disclaimer": "ఈ సమాచారం మార్గదర్శకం మాత్రమే. దరఖాస్తు ముందు అధికారిక వెబ్‌సైట్‌లో అర్హత మరియు పత్రాలను నిర్ధారించుకోండి."
    },
    "मराठी": {
        "title": "सरकारी योजना मार्गदर्शक 🤝", "subtitle": "सरकारी कल्याणकारी योजना शोधण्यासाठी, समजून घेण्यासाठी आणि अर्ज करण्यासाठी AI मार्गदर्शक.", "personal": "👤 वैयक्तिक माहिती", "financial": "💼 आर्थिक आणि सामाजिक माहिती", "location": "📍 स्थान", "name_label": "पूर्ण नाव", "age": "आपले वय निवडा", "gender_label": "लिंग", "income": "वार्षिक उत्पन्न (₹)", "occupation": "व्यवसाय / स्थिती", "caste_label": "सामाजिक प्रवर्ग", "state": "राज्य निवडा", "check_btn": "पात्रता तपासा", "found_msg": "आपल्या प्रोफाइलशी जुळणाऱ्या {n} योजना सापडल्या!", "no_match": "आपल्या माहितीनुसार योजना सापडल्या नाहीत. फिल्टर बदलून पुन्हा प्रयत्न करा.", "report_header": "📥 पात्रता अहवाल डाउनलोड करा (PDF)", "benefit": "💰 आर्थिक लाभ:", "overview": "🎯 आढावा:", "checklist_header": "📋 कागदपत्रांची यादी:", "apply": "🔗 अधिकृत वेबसाइटवर अर्ज करा", "verified": "शेवटचे सत्यापन: {d}", "compare_header": "⚖️ योजना तुलना साधन", "compare_sub": "लाभ आणि पात्रता तुलना करण्यासाठी योजना निवडा.", "compare_select": "तुलना करण्यासाठी योजना निवडा:", "col_name": "योजनेचे नाव", "col_category": "वर्ग", "col_benefit": "आर्थिक लाभ", "col_income": "कमाल उत्पन्न मर्यादा", "no_limit": "मर्यादा नाही", "chat_header": "🤖 AI योजना सहाय्यक", "chat_sub": "योजना कागदपत्रे, पात्रता, लाभ किंवा अर्ज प्रक्रियेबद्दल प्रश्न विचारा!", "chat_placeholder": "कोणत्याही योजनेबद्दल विचारा...", "thinking": "योजना शोधत आहे...", "no_key": "AI सहाय्यक सेट केलेले नाही: Streamlit secrets मध्ये GROQ_API_KEY जोडा.", "ai_error": "AI सहाय्यकाशी संपर्क होऊ शकला नाही. पुन्हा प्रयत्न करा.", "data_error": "scheme_data.json लोड करता आले नाही. तपशील:", "pdf_error": "PDF अहवाल तयार करता आला नाही.", "disclaimer": "ही माहिती फक्त मार्गदर्शनासाठी आहे. अर्ज करण्यापूर्वी अधिकृत वेबसाइटवर पात्रता आणि कागदपत्रे तपासा."
    }
}

selected_lang = st.sidebar.selectbox("🌐 Choose Language / भाषा चुनें", ["English", "हिंदी", "ಕನ್ನಡ", "தமிழ்", "తెలుగు", "मराठी"])
t = LANG_TEXT[selected_lang]


# ------------------------------------------------------------ core functions
def rule(rules, key, default):
    """Read a rule from the JSON; a missing OR null value means 'no restriction'."""
    value = rules.get(key)
    return default if value is None else value


def is_eligible(profile, scheme):
    """True if the user's profile satisfies every rule of the scheme."""
    rules = scheme.get("eligibility", {})
    age, income = profile["age"], profile["income"]

    if not (rule(rules, "min_age", 0) <= age <= rule(rules, "max_age", 120)):
        return False
    if income > rule(rules, "max_income", float("inf")):
        return False

    # "Women" and "Senior Citizen" schemes depend on gender / age, not occupation.
    category = scheme.get("category", "General")
    category_ok = (
        category == "General"
        or category == profile["occupation"]
        or (category == "Women" and profile["gender"] == "Female")
        or (category == "Senior Citizen" and age >= SENIOR_AGE)
    )
    if not category_ok:
        return False

    state = scheme.get("state", "All India")
    if state not in NATIONAL and state != profile["state"]:
        return False

    if profile["gender"] not in scheme.get("target_gender", ALL_GENDERS):
        return False
    if profile["caste"] not in scheme.get("target_caste", ALL_CASTES):
        return False
    return True


def scheme_need_match(need, scheme):
    """Score how strongly a scheme's text matches the user's selected need."""
    if not need:
        return 0
    text = " ".join([
        str(scheme.get("scheme_name", "")),
        str(scheme.get("category", "")),
        str(scheme.get("benefits", "")),
        str(scheme.get("financial_benefit", "")),
        " ".join(map(str, scheme.get("required_documents", []))),
    ]).lower()
    matched = sum(1 for keyword in NEED_KEYWORDS.get(need, set()) if keyword in text)
    if matched >= 4:
        return 15
    if matched >= 2:
        return 11
    if matched == 1:
        return 6
    return 0


def calculate_match_score(profile, scheme):
    """Calculate a 0-100 personalized fit score including the user's primary need."""
    score = 0
    rules = scheme.get("eligibility", {})
    age = profile["age"]
    income = profile["income"]

    # Age: 15 points
    if rule(rules, "min_age", 0) <= age <= rule(rules, "max_age", 120):
        score += 15

    # Income: 20 points
    max_income = rules.get("max_income")
    if max_income is None:
        score += 15
    elif income <= max_income * 0.50:
        score += 20
    elif income <= max_income * 0.80:
        score += 17
    else:
        score += 14

    # Target group / occupation: 20 points
    category = scheme.get("category", "General")
    if category == profile["occupation"]:
        score += 20
    elif category == "Women" and profile["gender"] == "Female":
        score += 20
    elif category == "Senior Citizen" and age >= SENIOR_AGE:
        score += 20
    elif category == "General":
        score += 10

    # State: 10 points
    state = scheme.get("state", "All India")
    if state == profile["state"]:
        score += 10
    elif state in NATIONAL:
        score += 7

    # Gender: 10 points
    target_gender = scheme.get("target_gender", ALL_GENDERS)
    if profile["gender"] in target_gender:
        score += 10 if set(target_gender) != set(ALL_GENDERS) else 6

    # Social category: 10 points
    target_caste = scheme.get("target_caste", ALL_CASTES)
    if profile["caste"] in target_caste:
        score += 10 if set(target_caste) != set(ALL_CASTES) else 6

    # Primary welfare need: up to 15 points
    score += scheme_need_match(profile.get("need", ""), scheme)
    return min(score, 100)


def recommendation_reasons(profile, scheme):
    """Return concise, evidence-based reasons for a scheme recommendation."""
    reasons = []
    rules = scheme.get("eligibility", {})
    age = profile["age"]
    income = profile["income"]

    min_age = rule(rules, "min_age", 0)
    max_age = rule(rules, "max_age", 120)
    if min_age <= age <= max_age:
        reasons.append(f"Your age ({age}) fits the scheme age range of {min_age}–{max_age} years.")

    max_income = rules.get("max_income")
    if max_income is not None:
        reasons.append(
            f"Your annual income (Rs. {income:,}) is within the Rs. {max_income:,} limit."
        )
    else:
        reasons.append("No income limit is specified in the scheme data.")

    category = scheme.get("category", "General")
    if category == profile["occupation"]:
        reasons.append(f"This scheme specifically targets {profile['occupation'].lower()}s.")
    elif category == "Women" and profile["gender"] == "Female":
        reasons.append("This scheme specifically targets women, matching your profile.")
    elif category == "Senior Citizen" and age >= SENIOR_AGE:
        reasons.append("This scheme specifically targets senior citizens, matching your age.")
    elif category == "General":
        reasons.append("The scheme is broadly available to the general category.")

    state = scheme.get("state", "All India")
    if state == profile["state"]:
        reasons.append(f"It is specifically available in {profile['state']}.")
    elif state in NATIONAL:
        reasons.append("It is listed as an All India scheme.")

    target_gender = scheme.get("target_gender", ALL_GENDERS)
    if set(target_gender) != set(ALL_GENDERS):
        reasons.append(f"Your gender ({profile['gender']}) matches the scheme's target group.")

    target_caste = scheme.get("target_caste", ALL_CASTES)
    if set(target_caste) != set(ALL_CASTES):
        reasons.append(f"Your social category ({profile['caste']}) is included in the target group.")

    need = profile.get("need", "")
    if need:
        need_points = scheme_need_match(need, scheme)
        if need_points >= 11:
            reasons.append(f"This scheme strongly matches your selected need: {need}.")
        elif need_points >= 6:
            reasons.append(f"This scheme has some relevance to your selected need: {need}.")
        else:
            reasons.append(f"Your selected need is {need}; this scheme is mainly matched through your eligibility profile.")

    # Keep the explanation short enough to scan during a demo.
    return reasons[:5]


def match_strength(score):
    """Convert a score into a simple explanation label."""
    if score >= 90:
        return "Excellent match", "🟢"
    if score >= 75:
        return "Strong match", "🟡"
    if score >= 60:
        return "Good match", "🟠"
    return "Basic match", "🔵"


def near_miss_analysis(profile, schemes, eligible_schemes):
    """Find schemes that are close to eligibility and explain the blocking detail.

    This is deterministic and uses the same eligibility rules as the main engine.
    It never invents a requirement that is not present in scheme_data.json.
    """
    eligible_names = {s.get("scheme_name") for s in eligible_schemes}
    candidates = []

    for scheme in schemes:
        if scheme.get("scheme_name") in eligible_names:
            continue

        rules = scheme.get("eligibility", {})
        failures = []
        age = profile["age"]
        income = profile["income"]
        category = scheme.get("category", "General")

        min_age = rule(rules, "min_age", 0)
        max_age = rule(rules, "max_age", 120)
        if not (min_age <= age <= max_age):
            failures.append({
                "field": "age",
                "label": "Age",
                "message": f"Age {age} is outside this scheme's range ({min_age}-{max_age}).",
                "value": age,
            })

        max_income = rules.get("max_income")
        if max_income is not None and income > max_income:
            failures.append({
                "field": "income",
                "label": "Annual income",
                "message": f"Your income (Rs. {income:,}) is above the scheme limit of Rs. {max_income:,}.",
                "value": income,
                "limit": max_income,
            })

        category_ok = (
            category == "General"
            or category == profile["occupation"]
            or (category == "Women" and profile["gender"] == "Female")
            or (category == "Senior Citizen" and age >= SENIOR_AGE)
        )
        if not category_ok:
            failures.append({
                "field": "occupation",
                "label": "Occupation / status",
                "message": f"This scheme targets {category}, while your current profile is {profile['occupation']}.",
                "value": profile["occupation"],
                "target": category,
            })

        state = scheme.get("state", "All India")
        if state not in NATIONAL and state != profile["state"]:
            failures.append({
                "field": "state",
                "label": "State",
                "message": f"This scheme is listed for {state}, while your current state is {profile['state']}.",
                "value": profile["state"],
                "target": state,
            })

        target_gender = scheme.get("target_gender", ALL_GENDERS)
        if profile["gender"] not in target_gender:
            failures.append({
                "field": "gender",
                "label": "Gender",
                "message": f"Your gender ({profile['gender']}) is not in this scheme's target group.",
                "value": profile["gender"],
                "target": ", ".join(target_gender),
            })

        target_caste = scheme.get("target_caste", ALL_CASTES)
        if profile["caste"] not in target_caste:
            failures.append({
                "field": "caste",
                "label": "Social category",
                "message": f"Your category ({profile['caste']}) is not in this scheme's target group.",
                "value": profile["caste"],
                "target": ", ".join(target_caste),
            })

        # A one-rule near miss is the best candidate for an interactive question.
        if len(failures) == 1:
            candidates.append((scheme, failures[0]))

    # Prefer candidates with the strongest personalized score after the one blocker.
    candidates.sort(
        key=lambda item: calculate_match_score(profile, item[0]),
        reverse=True,
    )
    return candidates[:5]


def apply_agent_update(profile, field, value):
    """Return a copied profile with one user-confirmed field changed."""
    updated = dict(profile)
    updated[field] = value
    return updated


def words(text):
    return set(re.findall(r"[a-z0-9]+", str(text).lower()))


def retrieve_relevant_schemes(query, data, eligible, top_k=3):
    """Keyword retrieval: score schemes by words shared with the question."""
    query_words = words(query) - STOPWORDS
    scored = []
    for scheme in data:
        name_words = words(scheme.get("scheme_name", ""))
        body = (
            f"{scheme.get('category', '')} {scheme.get('benefits', '')} "
            f"{scheme.get('financial_benefit', '')} {scheme.get('state', '')} "
            f"{scheme.get('required_documents', '')}"
        )
        score = 3 * len(query_words & name_words) + len(query_words & words(body))
        if score > 0 and scheme in eligible:   # small boost, only if already relevant
            score += 1
        scored.append((score, scheme))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    best = [s for score, s in scored[:top_k] if score > 0]
    # Nothing matched (e.g. a Hindi question): fall back to eligible schemes, then any.
    return best or eligible[:top_k] or data[:top_k]


def pdf_safe(text):
    """Built-in PDF fonts only support Latin-1, so swap other characters for '?'."""
    return str(text).replace("₹", "Rs.").encode("latin-1", "replace").decode("latin-1")


def pdf_line(pdf, text, height=6, align="L"):
    pdf.multi_cell(0, height, pdf_safe(text), align=align, new_x="LMARGIN", new_y="NEXT")


def create_pdf_report(profile, schemes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf_line(pdf, "Government Scheme Eligibility Report", height=10, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf_line(pdf, f"Prepared For: {profile.get('name', '').strip() or 'Applicant'}", align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf_line(pdf, f"Age: {profile['age']} | Gender: {profile['gender']} | State: {profile['state']}", align="C")
    pdf_line(pdf, f"Income: Rs.{profile['income']} | Occupation: {profile['occupation']} | Category: {profile['caste']}", align="C")
    if profile.get("need"):
        pdf_line(pdf, f"Primary Welfare Need: {profile['need']}", align="C")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 12)
    pdf_line(pdf, f"Matched Schemes ({len(schemes)} Found):")
    pdf.set_font("Helvetica", "", 10)
    for number, s in enumerate(schemes, 1):
        pdf_line(pdf, f"{number}. {s.get('scheme_name', 'Unnamed scheme')}")
        pdf_line(pdf, f"   - Benefit: {s.get('financial_benefit', 'N/A')}")
        pdf_line(pdf, f"   - Official Link: {s.get('application_link', 'N/A')}")
        if s.get("last_verified"):
            pdf_line(pdf, f"   - Last verified: {s['last_verified']}")
        pdf.ln(4)

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf_line(pdf, LANG_TEXT["English"]["disclaimer"], height=5)
    return bytes(pdf.output())


def get_api_key():
    """Streamlit secrets first, then the environment. Returns None if not set."""
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.environ.get("GROQ_API_KEY")


# ----------------------------------------------------------------- page body
# Safe title rendering with emoji gradient clipping fix
title_parts = t["title"].rsplit(" ", 1)
main_title = title_parts[0]
emoji = title_parts[1] if len(title_parts) > 1 else ""

st.markdown(
    f"<h1 style='text-align: center;'>{main_title} <span style='-webkit-text-fill-color: initial; background: none; display: inline-block;'>{emoji}</span></h1>",
    unsafe_allow_html=True
)
st.write(t["subtitle"])

# Load data (errors are shown, never hidden)
try:
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        scheme_data = json.load(file)
    if not isinstance(scheme_data, list):
        raise ValueError("the file must contain a list of schemes")
except Exception as error:
    scheme_data = []
    st.error(f"{t['data_error']} {error}")

# Session state (survives reruns)
defaults = {
    "eligible_schemes": [],
    "searched": False,
    "search_profile": {},
    "pdf_bytes": None,
    "messages": [],
    "agent_question": None,
    "agent_candidates": [],
    "agent_before_count": 0,
    "agent_updated": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Input form
with st.container(border=True):
    st.markdown(f"#### {t['personal']}")
    col1, col2, col3 = st.columns(3)
    with col1:
        user_name = st.text_input(t["name_label"], placeholder="John Doe")
    with col2:
        user_age = st.number_input(t["age"], min_value=0, max_value=120, value=18, step=1)
    with col3:
        user_gender = st.selectbox(t["gender_label"], ALL_GENDERS)

    st.markdown(f"#### {t['financial']}")
    col4, col5, col6 = st.columns(3)
    with col4:
        user_income = st.number_input(t["income"], min_value=0, max_value=10000000, value=300000, step=50000)
    with col5:
        user_occupation = st.selectbox(t["occupation"], OCCUPATIONS)
    with col6:
        user_caste = st.selectbox(t["caste_label"], ALL_CASTES)

    st.markdown("#### 🎯 What kind of support do you need?")
    user_need = st.selectbox(
        "Select your primary welfare need",
        NEED_OPTIONS,
        help="This helps rank eligible schemes according to the type of support you need. It does not override eligibility rules."
    )

    st.markdown(f"#### {t['location']}")
    user_state = st.selectbox(t["state"], STATES)

    st.markdown("<br>", unsafe_allow_html=True)
    check_button = st.button(t["check_btn"])

# On click: freeze the profile, filter, build the PDF once
if check_button:
    profile = {
        "name": user_name,
        "age": user_age,
        "gender": user_gender,
        "income": user_income,
        "occupation": user_occupation,
        "caste": user_caste,
        "need": user_need,
        "state": user_state,
    }
    matched = [s for s in scheme_data if is_eligible(profile, s)]

    # Rank eligible schemes by personalized match score
    matched.sort(
        key=lambda s: calculate_match_score(profile, s),
        reverse=True
    )

    st.session_state.searched = True
    st.session_state.search_profile = profile
    st.session_state.eligible_schemes = matched
    st.session_state.pdf_bytes = None
    if matched:
        try:
            st.session_state.pdf_bytes = create_pdf_report(profile, matched)
        except Exception as error:
            st.error(f"{t['pdf_error']} ({error})")

# ------------------------------------------------------- What Am I Missing? Agent
# The agent is a rule-based layer over the existing eligibility engine. It looks for
# schemes that are one profile detail away from eligibility and asks the user to
# review that specific detail instead of requesting sensitive documents.
if st.session_state.get("agent_question"):
    aq = st.session_state.agent_question
    st.session_state.agent_question = None
    profile = st.session_state.search_profile

    field = aq["field"]
    st.session_state.agent_before_count = len(st.session_state.eligible_schemes)

    st.markdown("### 🔍 What Am I Missing? Agent")
    st.info(
        f"The agent found a scheme you are close to: **{aq['scheme'].get('scheme_name', 'Scheme')}**.\n\n"
        f"**Why it is not currently matched:** {aq['failure']['message']}"
    )

    st.markdown("**The agent wants to verify one profile detail:**")

    with st.container(border=True):
        if field == "income":
            new_value = st.number_input(
                "What is your current annual income?",
                min_value=0,
                max_value=10000000,
                value=int(profile["income"]),
                step=50000,
                key="agent_income",
            )
        elif field == "age":
            new_value = st.number_input(
                "What is your current age?",
                min_value=0,
                max_value=120,
                value=int(profile["age"]),
                step=1,
                key="agent_age",
            )
        elif field == "gender":
            new_value = st.selectbox(
                "Please confirm your gender:",
                ALL_GENDERS,
                index=ALL_GENDERS.index(profile["gender"]),
                key="agent_gender",
            )
        elif field == "caste":
            new_value = st.selectbox(
                "Please confirm your social category:",
                ALL_CASTES,
                index=ALL_CASTES.index(profile["caste"]),
                key="agent_caste",
            )
        elif field == "occupation":
            new_value = st.selectbox(
                "Please confirm your occupation / status:",
                OCCUPATIONS,
                index=OCCUPATIONS.index(profile["occupation"]),
                key="agent_occupation",
            )
        else:
            new_value = st.selectbox(
                "Please confirm your state:",
                STATES,
                index=STATES.index(profile["state"]),
                key="agent_state",
            )

        if st.button("🤖 Update Profile & Re-analyze", key="agent_update"):
            updated_profile = apply_agent_update(profile, field, new_value)
            matched_after = [s for s in scheme_data if is_eligible(updated_profile, s)]
            matched_after.sort(
                key=lambda s: calculate_match_score(updated_profile, s),
                reverse=True,
            )

            before_names = {
                s.get("scheme_name") for s in st.session_state.eligible_schemes
            }
            new_names = [
                s.get("scheme_name") for s in matched_after
                if s.get("scheme_name") not in before_names
            ]

            st.session_state.search_profile = updated_profile
            st.session_state.eligible_schemes = matched_after
            st.session_state.agent_updated = True
            st.session_state.agent_new_names = new_names
            try:
                st.session_state.pdf_bytes = create_pdf_report(updated_profile, matched_after) if matched_after else None
            except Exception:
                st.session_state.pdf_bytes = None
            st.rerun()

# Results
if st.session_state.searched:
    st.divider()
    eligible_schemes = st.session_state.eligible_schemes

    if eligible_schemes:
        st.success(t["found_msg"].format(n=len(eligible_schemes)))

        # Agentic improvement loop: analyze near misses and ask only when a
        # single existing profile field can change the outcome.
        agent_candidates = near_miss_analysis(
            st.session_state.search_profile,
            scheme_data,
            eligible_schemes,
        )
        st.session_state.agent_candidates = agent_candidates

        if agent_candidates:
            best_candidate, best_failure = agent_candidates[0]
            st.markdown("### 🤖 Improve My Recommendations")
            st.write(
                "I found a scheme that is very close to matching your profile. "
                "I can ask one targeted question and re-check your eligibility."
            )
            with st.container(border=True):
                st.markdown(
                    f"**Potential additional match:** {best_candidate.get('scheme_name', 'Scheme')}"
                )
                st.caption(f"🔎 Agent found one possible blocker: {best_failure['message']}")
                if st.button("✨ Ask the Agent to Check", key="start_missing_agent"):
                    st.session_state.agent_question = {
                        "scheme": best_candidate,
                        "failure": best_failure,
                        "field": best_failure["field"],
                    }
                    st.rerun()

        if st.session_state.get("agent_updated"):
            new_names = st.session_state.get("agent_new_names", [])
            before_count = st.session_state.get("agent_before_count", 0)
            after_count = len(eligible_schemes)
            st.success(
                f"🔄 Profile re-analyzed: {before_count} → {after_count} eligible schemes. "
                f"New schemes discovered: {len(new_names)}"
            )
            if new_names:
                st.markdown("**🆕 Newly discovered schemes:**")
                for name in new_names[:5]:
                    st.markdown(f"- {name}")
            st.session_state.agent_updated = False

        selected_need = st.session_state.search_profile.get("need", "")
        if selected_need:
            st.info(f"🎯 **Your priority need:** {selected_need} — recommendations are ranked using this need plus your eligibility profile.")

        # Personalized recommendation dashboard
        st.markdown("### 🎯 Your Welfare Scheme Dashboard")

        top_scheme = eligible_schemes[0]
        top_score = calculate_match_score(
            st.session_state.search_profile,
            top_scheme
        )

        category_count = len(set(
            s.get("category", "General")
            for s in eligible_schemes
        ))

        document_count = len(set(
            doc
            for s in eligible_schemes
            for doc in s.get("required_documents", [])
        ))

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Eligible Schemes", len(eligible_schemes))

        with col2:
            st.metric("Best Match", f"{top_score}%")

        with col3:
            st.metric("Documents Needed", document_count)

        st.info(
            f"🏆 **Top Recommendation:** "
            f"{top_scheme.get('scheme_name', 'Scheme')} "
            f"— {top_score}% personalized match"
        )

        top_reasons = recommendation_reasons(
            st.session_state.search_profile,
            top_scheme
        )
        if top_reasons:
            with st.expander("🧠 Why is this your top recommendation?", expanded=True):
                for reason in top_reasons:
                    st.markdown(f"- {reason}")

        if st.session_state.pdf_bytes:
            st.download_button(
                label=t["report_header"],
                data=st.session_state.pdf_bytes,
                file_name="scheme_eligibility_report.pdf",
                mime="application/pdf",
            )

        cols = st.columns(3)
        for index, scheme in enumerate(eligible_schemes):
            with cols[index % 3]:
                with st.container(border=True):
                    st.subheader(scheme.get("scheme_name", "Unnamed scheme"))

                    score = calculate_match_score(
                        st.session_state.search_profile,
                        scheme
                    )

                    st.progress(
                        score / 100,
                        text=f"🎯 Personalized Match: {score}%"
                    )

                    strength_label, strength_icon = match_strength(score)
                    st.caption(f"{strength_icon} **{strength_label}**")

                    with st.expander("🧠 Why is this recommended?"):
                        reasons = recommendation_reasons(
                            st.session_state.search_profile,
                            scheme
                        )

                        if reasons:
                            st.markdown("**Recommendation reasoning:**")
                            for reason in reasons:
                                st.markdown(f"- {reason}")
                        else:
                            st.write("This scheme passed the eligibility rules in our database.")

                        st.caption(
                            "The recommendation is based only on the profile and scheme "
                            "rules stored in this application. Always verify current "
                            "requirements on the official scheme website."
                        )

                    st.markdown(f"**{t['benefit']}** {scheme.get('financial_benefit', '-')}")
                    st.markdown(f"**{t['overview']}** {scheme.get('benefits', '-')}")

                    docs = scheme.get("required_documents", [])
                    if docs:
                        st.markdown(f"**{t['checklist_header']}**")
                        for doc_idx, doc in enumerate(docs):
                            st.checkbox(doc, key=f"{scheme.get('scheme_name')}_{doc}_{doc_idx}")

                    if scheme.get("last_verified"):
                        st.caption(t["verified"].format(d=scheme["last_verified"]))

                    link = scheme.get("application_link")
                    if link:
                        st.markdown("---")
                        st.markdown(f"[{t['apply']}]({link})")

        # Comparison tool
        st.divider()
        st.subheader(t["compare_header"])
        st.write(t["compare_sub"])

        by_name = {s.get("scheme_name", "Unnamed scheme"): s for s in eligible_schemes}
        picked = st.multiselect(t["compare_select"], list(by_name))
        if picked:
            rows = []
            for name in picked:
                s = by_name[name]
                limit = s.get("eligibility", {}).get("max_income")
                rows.append({
                    t["col_name"]: name,
                    t["col_category"]: s.get("category", "-"),
                    t["col_benefit"]: s.get("financial_benefit", "-"),
                    t["col_income"]: f"₹{limit:,}" if isinstance(limit, (int, float)) else t["no_limit"],
                })
            st.table(rows)
    else:
        st.warning(t["no_match"])


# ------------------------------------------------------ Advanced agent features
# 1) Natural-language profile assistant (local extraction; no document upload)
st.divider()
st.subheader("💬 Tell Me Your Situation")
st.caption("Describe your situation in your own words. The assistant will extract profile details and help you search the scheme database.")
free_text = st.text_area(
    "Example: I am a 22 year old student from Karnataka. My family income is 150000 and I need education support.",
    key="natural_profile_text",
    height=100,
)
if st.button("✨ Understand My Situation", key="natural_profile_btn"):
    txt = free_text.lower().strip()
    extracted = {}
    age_match = re.search(r"\b(\d{1,3})\s*(?:years?|yrs?)\b", txt)
    income_match = re.search(r"(?:income|earn|earning|family income)[^\d]{0,20}(?:₹|rs\.?|inr)?\s*([\d,]+)", txt)
    if age_match:
        extracted["age"] = max(0, min(120, int(age_match.group(1))))
    if income_match:
        extracted["income"] = int(income_match.group(1).replace(",", ""))
    gender_map = {"female":"Female", "woman":"Female", "women":"Female", "male":"Male", "man":"Male"}
    for k, v in gender_map.items():
        if re.search(r"\b" + re.escape(k) + r"\b", txt):
            extracted["gender"] = v; break
    for occ in OCCUPATIONS:
        if occ.lower() in txt:
            extracted["occupation"] = occ; break
    for state in STATES:
        if state.lower() in txt:
            extracted["state"] = state; break
    need_map = {
        "education": "Education / Scholarship", "scholarship": "Education / Scholarship",
        "job": "Employment / Internship", "employment": "Employment / Internship", "internship": "Employment / Internship",
        "health": "Healthcare", "medical": "Healthcare", "hospital": "Healthcare",
        "housing": "Housing", "house": "Housing", "rent": "Housing",
        "farmer": "Agriculture", "farming": "Agriculture", "agriculture": "Agriculture",
        "business": "Business / Self-Employment", "loan": "Business / Self-Employment",
        "food": "Food / Basic Needs", "ration": "Food / Basic Needs",
    }
    for k, v in need_map.items():
        if k in txt:
            extracted["need"] = v; break
    if extracted:
        st.success("Extracted profile information:")
        st.json(extracted)
        st.session_state["natural_extracted"] = extracted
    else:
        st.info("I could not confidently extract profile details. Try mentioning age, income, occupation, state, and your main need.")

# 2) Scheme stacking: complementary recommendations from the existing database
if st.session_state.searched and st.session_state.eligible_schemes:
    st.subheader("🔗 Scheme Stacking Engine")
    st.caption("Find potentially complementary benefits from different welfare categories. Always verify whether benefits can legally be combined.")
    eligible = st.session_state.eligible_schemes
    stack = []
    seen_categories = set()
    for base in eligible[:10]:
        base_cat = base.get("category", "General")
        for candidate in eligible:
            if candidate.get("scheme_name") == base.get("scheme_name"):
                continue
            cat = candidate.get("category", "General")
            if cat != base_cat and cat not in seen_categories:
                stack.append((base, candidate))
                seen_categories.add(cat)
                break
        if len(stack) >= 4:
            break
    if stack:
        for base, candidate in stack:
            st.markdown(
                f"**{base.get('scheme_name','Scheme')}** ➜ **{candidate.get('scheme_name','Scheme')}**  "
                f"\n{base.get('category','General')} + {candidate.get('category','General')} — potentially complementary."
            )
    else:
        st.info("No clearly different-category combinations were found in the current eligible results.")

# 3) Privacy-first document readiness: only Yes/No, never upload sensitive documents
if st.session_state.searched and st.session_state.eligible_schemes:
    st.subheader("🔐 Privacy-First Application Readiness")
    st.caption("No Aadhaar, bank statement, certificate, or other document is uploaded. You only indicate whether you have each required document.")
    top_for_docs = st.session_state.eligible_schemes[:3]
    for scheme in top_for_docs:
        docs = scheme.get("required_documents", [])
        if not docs:
            continue
        with st.expander(f"📋 {scheme.get('scheme_name','Scheme')} — readiness check"):
            ready = 0
            for i, doc in enumerate(docs):
                if st.checkbox(f"I have: {doc}", key=f"ready_{scheme.get('scheme_name')}_{i}"):
                    ready += 1
            pct = round(ready / len(docs) * 100) if docs else 100
            st.progress(pct / 100, text=f"Application readiness: {pct}%")
            if pct == 100:
                st.success("You have indicated that all listed documents are ready.")
            else:
                st.warning(f"{len(docs)-ready} listed document(s) still need to be arranged.")

# 4) Simple application action plan
if st.session_state.searched and st.session_state.eligible_schemes:
    st.subheader("🧭 Your Application Action Plan")
    steps = [
        "1️⃣ Review the eligibility explanation and selected scheme.",
        "2️⃣ Check the required-document checklist.",
        "3️⃣ Verify the latest eligibility rules on the official scheme website.",
        "4️⃣ Open the official application link and submit the application.",
        "5️⃣ Save the acknowledgement/reference number and track the application.",
    ]
    for step in steps:
        st.markdown(step)

st.caption(t["disclaimer"])

# ------------------------------------------------------------ AI assistant
chat_container = st.container()
with chat_container:
    with st.popover("💬"):
        st.subheader(t["chat_header"])
        st.caption(t["chat_sub"])

        msg_container = st.container(height=350)
        for message in st.session_state.messages:
            with msg_container.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input(t["chat_placeholder"]):
            with msg_container.chat_message("user"):
                st.markdown(prompt)

            with msg_container.chat_message("assistant"):
                api_key = get_api_key()
                if not api_key:
                    st.warning(t["no_key"])
                else:
                    with st.spinner(t["thinking"]):
                        try:
                            eligible = st.session_state.eligible_schemes
                            retrieved = retrieve_relevant_schemes(prompt, scheme_data, eligible)

                            profile_context = ""
                            if st.session_state.searched and st.session_state.search_profile:
                                p = st.session_state.search_profile
                                ranked_lines = []
                                for item in eligible[:5]:
                                    item_score = calculate_match_score(p, item)
                                    ranked_lines.append(
                                        f"{item.get('scheme_name', '?')} — {item_score}% match; "
                                        f"reasons: {' '.join(recommendation_reasons(p, item))}"
                                    )
                                profile_context = (
                                    f"User Profile: Age: {p['age']}, Gender: {p['gender']}, "
                                    f"Income: {p['income']}, Occupation: {p['occupation']}, "
                                    f"Category: {p['caste']}, State: {p['state']}, "
                                    f"Primary welfare need: {p.get('need', 'not specified')}.\n"
                                    f"Top ranked eligible schemes:\n{'\n'.join(ranked_lines) or 'none'}"
                                )

                            system_content = (
                                "You are an expert Indian government schemes consultant.\n"
                                "CRITICAL RULE: Answer strictly and only from the retrieved scheme context "
                                "below. Do not assume or make up facts. If the information is not in the "
                                "context, say you don't have the details and suggest visiting the official "
                                "website.\n"
                                "Reply in the same language the user writes in.\n\n"
                                f"{profile_context}\n\n"
                                f"Retrieved Schemes Context:\n{json.dumps(retrieved, ensure_ascii=False)}"
                            )

                            history = st.session_state.messages[-6:]
                            messages = (
                                [{"role": "system", "content": system_content}]
                                + history
                                + [{"role": "user", "content": prompt}]
                            )

                            completion = Groq(api_key=api_key).chat.completions.create(
                                model=MODEL, messages=messages, temperature=0.2
                            )
                            reply = completion.choices[0].message.content
                            st.markdown(reply)

                            # Save the exchange only if it succeeded, so history never has gaps
                            st.session_state.messages.append({"role": "user", "content": prompt})
                            st.session_state.messages.append({"role": "assistant", "content": reply})
                        except Exception as error:
                            print(f"AI error: {error!r}")   # full details in the server log
                            st.error(f"{t['ai_error']} ({type(error).__name__})")

# Float the chat button at the bottom-right
chat_container.float("bottom: 30px; right: 30px; width: max-content; z-index: 999999;")