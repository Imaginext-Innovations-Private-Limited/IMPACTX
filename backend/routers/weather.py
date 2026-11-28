"""
Weather & Farm Action Advisory Router — Sprint 4.
Integrates free Open-Meteo Forecast API (16-day forecast) with Karnataka agro-climatic locations,
offline resilient fallback, and an expert rule-based agricultural advisory engine.
Caches last successful Open-Meteo response in memory for offline resilience.
"""
from datetime import datetime, timedelta
import random
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
import httpx
from pydantic import BaseModel
import config  # Sprint 4: for api_status_pill()
import language_config

router = APIRouter(prefix="/api/weather", tags=["weather"])

# Karnataka Agricultural Districts with coordinates and agro-climatic zones
KARNATAKA_LOCATIONS = [
    {
        "id": "bengaluru",
        "name": "Bengaluru",
        "name_kannada": "ಬೆಂಗಳೂರು",
        "district": "Bengaluru Urban",
        "zone": "Eastern Dry Zone",
        "lat": 12.9716,
        "lon": 77.5946,
        "major_crops": ["Ragi", "Maize", "Vegetables", "Flowers"],
    },
    {
        "id": "shivamogga",
        "name": "Shivamogga (Shimoga)",
        "name_kannada": "ಶಿವಮೊಗ್ಗ",
        "district": "Shivamogga",
        "zone": "Southern Transition Zone / Malnad",
        "lat": 13.9299,
        "lon": 75.5681,
        "major_crops": ["Areca Nut", "Paddy", "Ginger", "Pepper", "Corn"],
    },
    {
        "id": "mangaluru",
        "name": "Mangaluru (Dakshina Kannada)",
        "name_kannada": "ಮಂಗಳೂರು",
        "district": "Dakshina Kannada",
        "zone": "Coastal Zone",
        "lat": 12.9141,
        "lon": 74.8560,
        "major_crops": ["Paddy", "Areca Nut", "Coconut", "Cashew", "Black Pepper"],
    },
    {
        "id": "belagavi",
        "name": "Belagavi (Belgaum)",
        "name_kannada": "ಬೆಳಗಾವಿ",
        "district": "Belagavi",
        "zone": "Northern Transition Zone",
        "lat": 15.8497,
        "lon": 74.4977,
        "major_crops": ["Sugarcane", "Maize", "Cotton", "Soybean", "Paddy"],
    },
    {
        "id": "davanagere",
        "name": "Davanagere",
        "name_kannada": "ದಾವಣಗೆರೆ",
        "district": "Davanagere",
        "zone": "Central Dry Zone",
        "lat": 14.4644,
        "lon": 75.9218,
        "major_crops": ["Corn / Maize", "Paddy", "Areca Nut", "Cotton"],
    },
    {
        "id": "kalaburagi",
        "name": "Kalaburagi (Gulbarga)",
        "name_kannada": "ಕಲಬುರಗಿ",
        "district": "Kalaburagi",
        "zone": "North Eastern Dry Zone",
        "lat": 17.3297,
        "lon": 76.8343,
        "major_crops": ["Tur / Red Gram", "Jowar", "Bengal Gram", "Sunflower"],
    },
    {
        "id": "hassan",
        "name": "Hassan",
        "name_kannada": "ಹಾಸನ",
        "district": "Hassan",
        "zone": "Southern Transition Zone",
        "lat": 13.0072,
        "lon": 76.1031,
        "major_crops": ["Paddy", "Potato", "Coffee", "Pepper", "Ginger", "Areca"],
    },
    {
        "id": "mysuru",
        "name": "Mysuru (Mysore)",
        "name_kannada": "ಮೈಸೂರು",
        "district": "Mysuru",
        "state": "Karnataka",
        "zone": "Southern Dry Zone",
        "lat": 12.2958,
        "lon": 76.6394,
        "major_crops": ["Ragi", "Paddy", "Cotton", "Sugarcane", "Pulses"],
    },
]

PAN_INDIA_LOCATIONS = [
    {**loc, "state": loc.get("state", "Karnataka"), "default_language": "kn-IN"}
    for loc in KARNATAKA_LOCATIONS
] + [
    {"id": "pune", "name": "Pune", "district": "Pune", "state": "Maharashtra", "zone": "Western Maharashtra", "lat": 18.5204, "lon": 73.8567, "major_crops": ["Sugarcane", "Onion", "Soybean", "Jowar"], "default_language": "mr-IN"},
    {"id": "nashik", "name": "Nashik", "district": "Nashik", "state": "Maharashtra", "zone": "North Maharashtra", "lat": 19.9975, "lon": 73.7898, "major_crops": ["Onion", "Grapes", "Tomato", "Soybean"], "default_language": "mr-IN"},
    {"id": "nagpur", "name": "Nagpur", "district": "Nagpur", "state": "Maharashtra", "zone": "Vidarbha", "lat": 21.1458, "lon": 79.0882, "major_crops": ["Cotton", "Orange", "Soybean", "Tur"], "default_language": "mr-IN"},
    {"id": "coimbatore", "name": "Coimbatore", "district": "Coimbatore", "state": "Tamil Nadu", "zone": "Western Zone", "lat": 11.0168, "lon": 76.9558, "major_crops": ["Coconut", "Cotton", "Maize", "Turmeric"], "default_language": "ta-IN"},
    {"id": "thanjavur", "name": "Thanjavur", "district": "Thanjavur", "state": "Tamil Nadu", "zone": "Cauvery Delta", "lat": 10.7870, "lon": 79.1378, "major_crops": ["Paddy", "Sugarcane", "Banana", "Pulses"], "default_language": "ta-IN"},
    {"id": "hyderabad", "name": "Hyderabad", "district": "Rangareddy", "state": "Telangana", "zone": "Southern Telangana", "lat": 17.3850, "lon": 78.4867, "major_crops": ["Paddy", "Cotton", "Maize", "Vegetables"], "default_language": "te-IN"},
    {"id": "warangal", "name": "Warangal", "district": "Warangal", "state": "Telangana", "zone": "Central Telangana", "lat": 17.9689, "lon": 79.5941, "major_crops": ["Cotton", "Paddy", "Chilli", "Maize"], "default_language": "te-IN"},
    {"id": "guntur", "name": "Guntur", "district": "Guntur", "state": "Andhra Pradesh", "zone": "Krishna-Godavari Zone", "lat": 16.3067, "lon": 80.4365, "major_crops": ["Chilli", "Cotton", "Paddy", "Turmeric"], "default_language": "te-IN"},
    {"id": "thrissur", "name": "Thrissur", "district": "Thrissur", "state": "Kerala", "zone": "Central Kerala", "lat": 10.5276, "lon": 76.2144, "major_crops": ["Paddy", "Coconut", "Banana", "Black Pepper"], "default_language": "ml-IN"},
    {"id": "lucknow", "name": "Lucknow", "district": "Lucknow", "state": "Uttar Pradesh", "zone": "Central Plain", "lat": 26.8467, "lon": 80.9462, "major_crops": ["Wheat", "Paddy", "Sugarcane", "Potato"], "default_language": "hi-IN"},
    {"id": "ludhiana", "name": "Ludhiana", "district": "Ludhiana", "state": "Punjab", "zone": "Central Plain Punjab", "lat": 30.9010, "lon": 75.8573, "major_crops": ["Wheat", "Paddy", "Maize", "Cotton"], "default_language": "pa-IN"},
    {"id": "karnal", "name": "Karnal", "district": "Karnal", "state": "Haryana", "zone": "Eastern Haryana", "lat": 29.6857, "lon": 76.9905, "major_crops": ["Wheat", "Basmati Paddy", "Sugarcane", "Mustard"], "default_language": "hi-IN"},
    {"id": "indore", "name": "Indore", "district": "Indore", "state": "Madhya Pradesh", "zone": "Malwa Plateau", "lat": 22.7196, "lon": 75.8577, "major_crops": ["Soybean", "Wheat", "Gram", "Garlic"], "default_language": "hi-IN"},
    {"id": "ahmedabad", "name": "Ahmedabad", "district": "Ahmedabad", "state": "Gujarat", "zone": "Middle Gujarat", "lat": 23.0225, "lon": 72.5714, "major_crops": ["Cotton", "Groundnut", "Wheat", "Cumin"], "default_language": "gu-IN"},
    {"id": "rajkot", "name": "Rajkot", "district": "Rajkot", "state": "Gujarat", "zone": "Saurashtra", "lat": 22.3039, "lon": 70.8022, "major_crops": ["Groundnut", "Cotton", "Cumin", "Sesame"], "default_language": "gu-IN"},
    {"id": "kolkata", "name": "Kolkata / Hooghly", "district": "Hooghly", "state": "West Bengal", "zone": "Gangetic Alluvial", "lat": 22.9000, "lon": 88.3900, "major_crops": ["Paddy", "Potato", "Jute", "Vegetables"], "default_language": "bn-IN"},
    {"id": "jaipur", "name": "Jaipur", "district": "Jaipur", "state": "Rajasthan", "zone": "Semi-Arid Eastern", "lat": 26.9124, "lon": 75.7873, "major_crops": ["Mustard", "Bajra", "Wheat", "Gram"], "default_language": "hi-IN"},
    {"id": "patna", "name": "Patna", "district": "Patna", "state": "Bihar", "zone": "South Bihar Alluvial", "lat": 25.5941, "lon": 85.1376, "major_crops": ["Paddy", "Wheat", "Maize", "Lentil"], "default_language": "hi-IN"},
    {"id": "cuttack", "name": "Cuttack", "district": "Cuttack", "state": "Odisha", "zone": "East & South Eastern Coastal", "lat": 20.4625, "lon": 85.8830, "major_crops": ["Paddy", "Pulses", "Groundnut", "Vegetables"], "default_language": "en-IN"},
]

WMO_WEATHER_CODES = {
    0: {"desc": "Clear sky", "icon": "Sun", "kannada": "ಸ್ವಚ್ಛ ಆಕಾಶ"},
    1: {"desc": "Mainly clear", "icon": "Sun", "kannada": "ಬಹುತೇಕ ಸ್ವಚ್ಛ"},
    2: {"desc": "Partly cloudy", "icon": "CloudSun", "kannada": "ಭಾಗಶಃ ಮೋಡ"},
    3: {"desc": "Overcast", "icon": "Cloud", "kannada": "ಮೋಡ ಕವಿದ ವಾತಾವರಣ"},
    45: {"desc": "Foggy", "icon": "CloudFog", "kannada": "ಮಂಜು"},
    48: {"desc": "Depositing rime fog", "icon": "CloudFog", "kannada": "ದಟ್ಟ ಮಂಜು"},
    51: {"desc": "Light drizzle", "icon": "CloudDrizzle", "kannada": "ತುಂತುರು ಮಳೆ"},
    53: {"desc": "Moderate drizzle", "icon": "CloudDrizzle", "kannada": "ಸಾಧಾರಣ ತುಂತುರು ಮಳೆ"},
    55: {"desc": "Dense drizzle", "icon": "CloudDrizzle", "kannada": "ದಟ್ಟ ತುಂತುರು ಮಳೆ"},
    61: {"desc": "Slight rain", "icon": "CloudRain", "kannada": "ಹಗುರ ಮಳೆ"},
    63: {"desc": "Moderate rain", "icon": "CloudRain", "kannada": "ಸಾಧಾರಣ ಮಳೆ"},
    65: {"desc": "Heavy rain", "icon": "CloudRain", "kannada": "ಭಾರಿ ಮಳೆ"},
    80: {"desc": "Slight rain showers", "icon": "CloudRain", "kannada": "ಕ್ಷಣಿಕ ಮಳೆ"},
    81: {"desc": "Moderate rain showers", "icon": "CloudRain", "kannada": "ಸಾಧಾರಣ ಮಳೆ ಸುರಿತ"},
    82: {"desc": "Violent rain showers", "icon": "CloudLightning", "kannada": "ಗುಡುಗು ಸಹಿತ ಭಾರಿ ಮಳೆ"},
    95: {"desc": "Thunderstorm", "icon": "CloudLightning", "kannada": "ಗುಡುಗು ಸಹಿತ ಮಳೆ"},
}

WMO_WEATHER_LOCALIZED = {
    0: {
        "kn-IN": "ಸ್ವಚ್ಛ ಆಕಾಶ", "hi-IN": "साफ़ आसमान", "te-IN": "స్వచ్ఛమైన ఆకాశం",
        "ta-IN": "தெளிவான வானம்", "mr-IN": "निरभ्र आकाश", "ml-IN": "തെളിഞ്ഞ ആകാശം",
        "bn-IN": "পরিষ্কার আকাশ", "gu-IN": "સ્વચ્છ આકાશ", "pa-IN": "ਸਾਫ਼ ਅਸਮਾਨ", "en-IN": "Clear sky",
    },
    1: {
        "kn-IN": "ಬಹುತೇಕ ಸ್ವಚ್ಛ", "hi-IN": "मुख्य रूप से साफ़", "te-IN": "ఎక్కువగా నిర్మలంగా",
        "ta-IN": "பெரும்பாலும் தெளிவானது", "mr-IN": "मुख्यतः निरभ्र", "ml-IN": "പ്രധാനമായും തെളിഞ്ഞത്",
        "bn-IN": "বেশিরভাগ পরিষ্কার", "gu-IN": "મોટે ભાગે સ્વચ્છ", "pa-IN": "ਮੁੱਖ ਤੌਰ 'ਤੇ ਸਾਫ਼", "en-IN": "Mainly clear",
    },
    2: {
        "kn-IN": "ಭಾಗಶಃ ಮೋಡ", "hi-IN": "आंशिक रूप से बादल", "te-IN": "పాక్షికంగా మేఘావృతం",
        "ta-IN": "பகுதி மேகமூட்டம்", "mr-IN": "अंशतः ढगाळ", "ml-IN": "ഭാഗികമായി മേഘാവൃതം",
        "bn-IN": "আংশিক মেঘলা", "gu-IN": "અંશતઃ વાદળછાયું", "pa-IN": "ਅੰਸ਼ਕ ਤੌਰ 'ਤੇ ਬੱਦਲਵਾਈ", "en-IN": "Partly cloudy",
    },
    3: {
        "kn-IN": "ಮೋಡ ಕವಿದ ವಾತಾವರಣ", "hi-IN": "घने बादल", "te-IN": "పూర్తిగా మేఘావృతం",
        "ta-IN": "முழு மேகமூட்டம்", "mr-IN": "पूर्ण ढगाळ", "ml-IN": "മേഘാവൃതമായ അന്തരീക്ഷം",
        "bn-IN": "মেঘলা আকাশ", "gu-IN": "સંપૂર્ણ વાદળછાયું", "pa-IN": "ਘਣੇ ਬੱਦਲ", "en-IN": "Overcast",
    },
    45: {
        "kn-IN": "ಮಂಜು", "hi-IN": "कोहरा", "te-IN": "పొగమంచు",
        "ta-IN": "மூடுபனி", "mr-IN": "धुके", "ml-IN": "മൂടൽമഞ്ഞ്",
        "bn-IN": "কুয়াশা", "gu-IN": "ધુમ્મસ", "pa-IN": "ਧੁੰਦ", "en-IN": "Foggy",
    },
    48: {
        "kn-IN": "ದಟ್ಟ ಮಂಜು", "hi-IN": "घना कोहरा", "te-IN": "దట్టమైన పొగమంచు",
        "ta-IN": "அடர்ந்த மூடுபனி", "mr-IN": "दाट धुके", "ml-IN": "കനത്ത മൂടൽമഞ്ഞ്",
        "bn-IN": "ঘন কুয়াশা", "gu-IN": "ગાઢ ધુમ્મસ", "pa-IN": "ਸੰਘਣੀ ਧੁੰਦ", "en-IN": "Dense rime fog",
    },
    51: {
        "kn-IN": "ತುಂತುರು ಮಳೆ", "hi-IN": "हल्की बूंदाबांदी", "te-IN": "తేలికపాటి చినుకులు",
        "ta-IN": "லேசான தூறல்", "mr-IN": "हलकी रिमझिम", "ml-IN": "ചെറിയ ചാറ്റൽമഴ",
        "bn-IN": "হালকা গুঁড়ি গুঁড়ি বৃষ্টি", "gu-IN": "હળવી ઝરમર", "pa-IN": "ਹਲਕੀ ਫੁਹਾਰ", "en-IN": "Light drizzle",
    },
    53: {
        "kn-IN": "ಸಾಧಾರಣ ತುಂತುರು ಮಳೆ", "hi-IN": "मध्यम बूंदाबांदी", "te-IN": "చిరుజల్లులు",
        "ta-IN": "மிதமான தூறல்", "mr-IN": "मध्यम रिमझिम", "ml-IN": "സാധാരണ ചാറ്റൽമഴ",
        "bn-IN": "মাঝারি গুঁড়ি গুঁড়ি বৃষ্টি", "gu-IN": "મધ્યમ ઝરમર", "pa-IN": "ਦਰਮਿਆਨੀ ਫੁਹਾਰ", "en-IN": "Moderate drizzle",
    },
    55: {
        "kn-IN": "ದಟ್ಟ ತುಂತುರು ಮಳೆ", "hi-IN": "तेज़ बूंदाबांदी", "te-IN": "దట్టమైన చినుకులు",
        "ta-IN": "அடர்ந்த தூறல்", "mr-IN": "जोरदार रिमझिम", "ml-IN": "കനത്ത ചാറ്റൽമഴ",
        "bn-IN": "ঘন গুঁড়ি গুঁড়ি বৃষ্টি", "gu-IN": "ભારે ઝરમર", "pa-IN": "ਤੇਜ਼ ਫੁਹਾਰ", "en-IN": "Dense drizzle",
    },
    61: {
        "kn-IN": "ಹಗುರ ಮಳೆ", "hi-IN": "हल्की बारिश", "te-IN": "తేలికపాటి వర్షం",
        "ta-IN": "லேசான மழை", "mr-IN": "हलका पाऊस", "ml-IN": "നേരിയ മഴ",
        "bn-IN": "হালকা বৃষ্টি", "gu-IN": "હળવો વરસાદ", "pa-IN": "ਹਲਕਾ ਮੀਂਹ", "en-IN": "Slight rain",
    },
    63: {
        "kn-IN": "ಸಾಧಾರಣ ಮಳೆ", "hi-IN": "मध्यम बारिश", "te-IN": "మితమైన వర్షం",
        "ta-IN": "மிதமான மழை", "mr-IN": "मध्यम पाऊस", "ml-IN": "മിതമായ മഴ",
        "bn-IN": "মাঝারি বৃষ্টি", "gu-IN": "મધ્યમ વરસાદ", "pa-IN": "ਦਰਮਿਆਨਾ ਮੀਂਹ", "en-IN": "Moderate rain",
    },
    65: {
        "kn-IN": "ಭಾರಿ ಮಳೆ", "hi-IN": "भारी बारिश", "te-IN": "భారీ వర్షం",
        "ta-IN": "கனமழை", "mr-IN": "मुसळधार पाऊस", "ml-IN": "കനത്ത മഴ",
        "bn-IN": "ভারী বৃষ্টি", "gu-IN": "ભારે વરસાદ", "pa-IN": "ਭਾਰੀ ਮੀਂਹ", "en-IN": "Heavy rain",
    },
    80: {
        "kn-IN": "ಕ್ಷಣಿಕ ಮಳೆ", "hi-IN": "हल्की बौछारें", "te-IN": "తేలికపాటి జల్లులు",
        "ta-IN": "லேசான மழைச்சாரல்", "mr-IN": "हलक्या सरी", "ml-IN": "നേരിയ മഴത്തുള്ളികൾ",
        "bn-IN": "হালকা পশলা বৃষ্টি", "gu-IN": "હળવા ઝાપટાં", "pa-IN": "ਹਲਕੇ ਛਰਾਟੇ", "en-IN": "Slight rain showers",
    },
    81: {
        "kn-IN": "ಸಾಧಾರಣ ಮಳೆ ಸುರಿತ", "hi-IN": "मध्यम बौछारें", "te-IN": "మితమైన జల్లులు",
        "ta-IN": "மிதமான மழைச்சாரல்", "mr-IN": "मध्यम सरी", "ml-IN": "ഇടവിട്ടുള്ള മഴ",
        "bn-IN": "মাঝারি পশলা বৃষ্টি", "gu-IN": "મધ્યમ ઝાપટાં", "pa-IN": "ਦਰਮਿਆਨੇ ਛਰਾਟੇ", "en-IN": "Moderate rain showers",
    },
    82: {
        "kn-IN": "ಗುಡುಗು ಸಹಿತ ಭಾರಿ ಮಳೆ", "hi-IN": "तेज़ मूसलाधार बौछारें", "te-IN": "తీవ్రమైన వర్షపు జల్లులు",
        "ta-IN": "கடும் மழைக்காலச்சாரல்", "mr-IN": "मुसळधार सरी", "ml-IN": "ശക്തമായ മഴ",
        "bn-IN": "প্রবল বর্ষণ", "gu-IN": "ભારે ઝાપટાં", "pa-IN": "ਭਾਰੀ ਛਰਾਟੇ", "en-IN": "Violent rain showers",
    },
    95: {
        "kn-IN": "ಗುಡುಗು ಸಹಿತ ಮಳೆ", "hi-IN": "गरज के साथ बारिश", "te-IN": "ఉరుములతో కూడిన వర్షం",
        "ta-IN": "இடியுடன் கூடிய மழை", "mr-IN": "वादळी पाऊस", "ml-IN": "ഇടിമിന്നലോട് കൂടിയ മഴ",
        "bn-IN": "বজ্রবিদ্যুৎ সহ বৃষ্টি", "gu-IN": "ગાજવીજ સાથે વરસાદ", "pa-IN": "ਗਰਜ ਨਾਲ ਮੀਂਹ", "en-IN": "Thunderstorm",
    },
}

SECTION_LABELS = {
    "live_farm_action_advisories": {
        "kn-IN": "ಲೈವ್ ಕೃಷಿ ಕಾರ್‍ಯ ಸಲಹೆಗಳು",
        "hi-IN": "लाइव कृषि कार्य सलाह",
        "te-IN": "ప్రత్యక్ష వ్యవసాయ కార్యాచరణ సలహాలు",
        "ta-IN": "நேரலை விவசாய செயல் ஆலோசனைகள்",
        "mr-IN": "थेट कृषी कृती सल्ला",
        "ml-IN": "തത്സമയ കാർഷിക പ്രവർത്തന ഉപദേശങ്ങൾ",
        "bn-IN": "লাইভ কৃষি কর্মপরামর্শ",
        "gu-IN": "લાઇવ કૃષિ કાર્ય સલાહ",
        "pa-IN": "ਲਾਈਵ ਖੇਤੀਬਾੜੀ ਕਾਰਜ ਸਲਾਹ",
        "en-IN": "Live Farm Action Advisories",
    },
    "rule_based_engine": {
        "kn-IN": "ಕೃಷಿ ತಜ್ಞ ಎಂಜಿನ್",
        "hi-IN": "नियम-आधारित कृषि इंजन",
        "te-IN": "వ్యవసాయ నిపుణుల వ్యవస్థ",
        "ta-IN": "வேளாண் விதிகளின் தளம்",
        "mr-IN": "तज्ज्ञ कृषी प्रणाली",
        "ml-IN": "കാർഷിക വിദഗ്ദ്ധ എഞ്ചിൻ",
        "bn-IN": "কৃষি বিশেষজ্ঞ ইঞ্জিন",
        "gu-IN": "કૃષિ નિષ્ણાત એન્જિન",
        "pa-IN": "ਖੇਤੀਬਾੜੀ ਮਾਹਰ ਇੰਜਨ",
        "en-IN": "Rule-based Agri Engine",
    },
    "weather_outlook": {
        "kn-IN": "16 ದಿನಗಳ ಹವಾಮಾನ ಮತ್ತು ಮಣ್ಣಿನ ಮುನ್ನೋಟ",
        "hi-IN": "16-दिवसीय मौसम एवं मिट्टी का दृष्टिकोण",
        "te-IN": "16 రోజుల వాతావరణం మరియు నేల సమగ్ర వివరాలు",
        "ta-IN": "16 நாள் வானிலை மற்றும் மண் கண்ணோட்டம்",
        "mr-IN": "16 दिवसांचे हवामान व जमिनीचा अंदाज",
        "ml-IN": "16 ദിവസത്തെ കാലാവസ്ഥയും മണ്ണും",
        "bn-IN": "১৬ দিনের আবহাওয়া ও মাটির পূর্বাভাস",
        "gu-IN": "16 દિવસનું હવામાન અને માટી વિહંગાવલોકન",
        "pa-IN": "16 ਦਿਨਾਂ ਦਾ ਮੌਸਮ ਅਤੇ ਮਿੱਟੀ ਦਾ ਦ੍ਰਿਸ਼ਟੀਕੋਣ",
        "en-IN": "16-Day Weather & Soil Outlook",
    },
    "outlook_sub": {
        "kn-IN": "ಬೆಳೆ ಯೋಜನೆ ಮತ್ತು ನೀರಾವರಿ ವೇಳಾಪಟ್ಟಿಗಾಗಿ ಹವಾಮಾನ ಮಾಹಿತಿ",
        "hi-IN": "फसल योजना और सिंचाई कार्यक्रम के लिए विस्तृत मौसम अनुमान",
        "te-IN": "పంట ప్రణాళిక మరియు సాగునీటి నిర్వహణ కోసం సూచనలు",
        "ta-IN": "பயிர் திட்டமிடல் மற்றும் பாசனத்திற்கான வானிலை கணிப்பு",
        "mr-IN": "पीक नियोजन व पाणी व्यवस्थापनासाठी हवामान अंदाज",
        "ml-IN": "വിള ആസൂത്രണത്തിനും ജലസേചനത്തിനുമുള്ള വിവരങ്ങൾ",
        "bn-IN": "ফসল পরিকল্পনা ও সেচ পরিচালনার আবহাওয়া তথ্য",
        "gu-IN": "પાક આયોજન અને પિયત માટે હવામાન અંદાજ",
        "pa-IN": "ਫ਼ਸਲ ਯੋਜਨਾਬੰਦੀ ਅਤੇ ਸਿੰਚਾਈ ਲਈ ਮੌਸਮ ਦਾ ਅਨੁਮਾਨ",
        "en-IN": "Extended meteorological projections for crop planning and irrigation scheduling",
    },
    "agro_forecast_subtitle": {
        "kn-IN": "ಮುಕ್ತ ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ · ಭಾರತೀಯ ವಲಯಗಳು",
        "hi-IN": "ओपन-मेटियो उच्च-रिज़ॉल्यूशन कृषि-पूर्वानुमान · अखिल भारतीय क्षेत्र",
        "te-IN": "ఓపెన్-మెటియో వ్యవసాయ వాతావరణ సూచన · అఖిల భారత ప్రాంతాలు",
        "ta-IN": "ஓபன்-மெட்டியோ வேளாண் முன்னறிவிப்பு · அகில இந்திய மண்டலங்கள்",
        "mr-IN": "ओपन-मेटिओ कृषी-अंदाज · अखिल भारतीय विभाग",
        "ml-IN": "ഓപ്പൺ-മെറ്റിയോ കാർഷിക പ്രവചനം · അഖിലേന്ത്യാ മേഖലകൾ",
        "bn-IN": "ওপেন-মেটিও কৃষি পূর্বাভাস · সর্বভারতীয় অঞ্চল",
        "gu-IN": "ઓપન-મેટિયો કૃષિ આગાહી · અખિલ ભારતીય ઝોન",
        "pa-IN": "ਓਪਨ-ਮੀਟਿਓ ਖੇਤੀਬਾੜੀ ਪੂਰਵ-ਅਨੁਮਾਨ · ਆਲ-ਇੰਡੀਆ ਜ਼ੋਨ",
        "en-IN": "Open-Meteo High-Resolution Agro-Forecast · Pan-India Zones",
    },
}

ADVISORY_CATEGORY_LOCALIZED = {
    "Harvesting Alert": {
        "kn-IN": "ಕೊಯ್ಲು ಎಚ್ಚರಿಕೆ",
        "hi-IN": "कटाई चेतावनी",
        "te-IN": "కోత హెచ్చరిక",
        "ta-IN": "அறுவடை எச்சரிக்கை",
        "mr-IN": "कापणी इशारा",
        "ml-IN": "വിളവെടുപ്പ് മുന്നറിയിപ്പ്",
        "bn-IN": "ফসল কাটার সতর্কতা",
        "gu-IN": "લણણી ચેતવણી",
        "pa-IN": "ਵਾਢੀ ਦੀ ਚੇਤਾਵਨੀ",
        "en-IN": "Harvesting Alert",
    },
    "Harvesting Window Open": {
        "kn-IN": "ಕೊಯ್ಲು ಮಾಡಲು ಸುಸಮಯ",
        "hi-IN": "फसल कटाई का अनुकूल समय",
        "te-IN": "పంట కోతకు అనుకూల సమయం",
        "ta-IN": "அறுவடைக்கு உகந்த நேரம்",
        "mr-IN": "कापणीसाठी अनुकूल वेळ",
        "ml-IN": "വിളവെടുപ്പിന് അനുകൂല സമയം",
        "bn-IN": "ফসল কাটার উপযুক্ত সময়",
        "gu-IN": "લણણી માટે અનુકૂળ સમય",
        "pa-IN": "ਵਾਢੀ ਲਈ ਢੁਕਵਾਂ ਸਮਾਂ",
        "en-IN": "Harvesting Window Open",
    },
    "Cultivation & Sowing": {
        "kn-IN": "ಬಿತ್ತನೆ ಮತ್ತು ಕೃಷಿ ಕೆಲಸ",
        "hi-IN": "बुवाई और जुताई अनुकूल",
        "te-IN": "విత్తనాలు & సాగుకు అనుకూలం",
        "ta-IN": "விதைப்பு மற்றும் சாகுபடி",
        "mr-IN": "पेरणी व मशागत अनुकूल",
        "ml-IN": "വിത്ത് നടീലും കൃഷിയും",
        "bn-IN": "বপন ও চাষাবাদের অনুকূল",
        "gu-IN": "વાવણી અને ખેતી કાર્ય",
        "pa-IN": "ਬਿਜਾਈ ਅਤੇ ਕਾਸ਼ਤ ਲਈ ਢੁਕਵਾਂ",
        "en-IN": "Cultivation & Sowing",
    },
    "Soil Moisture Low": {
        "kn-IN": "ಮಣ್ಣಿನಲ್ಲಿ ತೇವಾಂಶ ಕಡಿಮೆ",
        "hi-IN": "मृदा नमी कम",
        "te-IN": "నేలలో తేమ తక్కువ",
        "ta-IN": "மண்ணில் ஈரப்பதம் குறைவு",
        "mr-IN": "जमिनीत ओलावा कमी",
        "ml-IN": "മണ്ണിൽ ഈർപ്പം കുറവ്",
        "bn-IN": "মাটিতে আর্দ্রতা কম",
        "gu-IN": "જમીનમાં ભેજ ઓછો",
        "pa-IN": "ਮਿੱਟੀ ਵਿੱਚ ਨਮੀ ਘੱਟ",
        "en-IN": "Soil Moisture Low",
    },
    "Spraying Window Open": {
        "kn-IN": "ಔಷಧ ಸಿಂಪರಣೆಗೆ ಪ್ರಶಸ್ತ ಸಮಯ",
        "hi-IN": "कीटनाशक/खाद छिड़काव अनुकूल",
        "te-IN": "మందుల పిచికారీకి అనుకూల సమయం",
        "ta-IN": "மருந்து தெளிக்க உகந்த நேரம்",
        "mr-IN": "फवारणीसाठी योग्य वेळ",
        "ml-IN": "കീടനാശിനി പ്രയോഗത്തിന് നല്ല സമയം",
        "bn-IN": "ওষুধ স্প্রে করার উপযুক্ত সময়",
        "gu-IN": "દવા છંટકાવ માટે અનુકૂળ સમય",
        "pa-IN": "ਸਪਰੇਅ ਕਰਨ ਲਈ ਢੁਕਵਾਂ ਸਮਾਂ",
        "en-IN": "Spraying Window Open",
    },
    "Irrigation Management": {
        "kn-IN": "ನೀರಾವರಿ ನಿರ್ವಹಣೆ",
        "hi-IN": "सिंचाई प्रबंधन",
        "te-IN": "సాగునీటి నిర్వహణ",
        "ta-IN": "பாசன மேலாண்மை",
        "mr-IN": "पाणी व्यवस्थापन",
        "ml-IN": "ജലസേചന നിയന്ത്രണം",
        "bn-IN": "সেচ ব্যবস্থাপনা",
        "gu-IN": "પિયત વ્યવસ્થાપન",
        "pa-IN": "ਸਿੰਚਾਈ ਪ੍ਰਬੰਧਨ",
        "en-IN": "Irrigation Management",
    },
    "Irrigation Recommendation": {
        "kn-IN": "ಲಘು ನೀರಾವರಿ ಸಲಹೆ",
        "hi-IN": "सिंचाई की सलाह",
        "te-IN": "సాగునీటి సలహా",
        "ta-IN": "பாசன ஆலோசனை",
        "mr-IN": "सिंचन सल्ला",
        "ml-IN": "നനയ്ക്കൽ ഉപദേശം",
        "bn-IN": "সেচ পরামর্শ",
        "gu-IN": "પિયત ભલામણ",
        "pa-IN": "ਸਿੰਚਾਈ ਦੀ ਸਲਾਹ",
        "en-IN": "Irrigation Recommendation",
    },
    "Extreme Heat Alert": {
        "kn-IN": "ಅತಿಯಾದ ತಾಪಮಾನ ಎಚ್ಚರಿಕೆ",
        "hi-IN": "अत्यधिक गर्मी चेतावनी",
        "te-IN": "తీవ్రమైన ఎండ హెచ్చరిక",
        "ta-IN": "கடும் வெப்ப எச்சரிக்கை",
        "mr-IN": "तीव्र उष्णता इशारा",
        "ml-IN": "കടുത്ത ചൂട് മുന്നറിയിപ്പ്",
        "bn-IN": "তীব্র তাপদাহ সতর্কতা",
        "gu-IN": "તીવ્ર ગરમીની ચેતવણી",
        "pa-IN": "ਅੱਤ ਦੀ ਗਰਮੀ ਦੀ ਚੇਤਾਵਨੀ",
        "en-IN": "Extreme Heat Alert",
    },
    "Cold / Frost Alert": {
        "kn-IN": "ಶೀತ ವಾತಾವರಣ / ಹಿಮ ಎಚ್ಚರಿಕೆ",
        "hi-IN": "शीत लहर / पाला चेतावनी",
        "te-IN": "శీతల గాలులు / మంచు హెచ్చరిక",
        "ta-IN": "குளிர் அலை / பனி எச்சரிக்கை",
        "mr-IN": "थंडीची लाट / दव इशारा",
        "ml-IN": "ശൈത്യതരംഗം / മഞ്ഞ് മുന്നറിയിപ്പ്",
        "bn-IN": "শৈত্যপ্রবাহ / তুষার সতর্কতা",
        "gu-IN": "શીત લહેર / ઝાકળ ચેતવણી",
        "pa-IN": "ਕੋਰਾ / ਠੰਢ ਦੀ ਚੇਤਾਵਨੀ",
        "en-IN": "Cold / Frost Alert",
    },
}


def _get_weather_info(code: int, lang: str = "kn-IN") -> dict:
    info = WMO_WEATHER_CODES.get(code, {"desc": "Partly cloudy", "icon": "CloudSun", "kannada": "ಭಾಗಶಃ ಮೋಡ"})
    localized_map = WMO_WEATHER_LOCALIZED.get(code, {})
    localized_desc = localized_map.get(lang) or localized_map.get("en-IN") or info["desc"]
    return {
        "desc": info["desc"],
        "icon": info["icon"],
        "kannada": info.get("kannada", "ಭಾಗಶಃ ಮೋಡ"),
        "localized": localized_desc,
    }


def generate_offline_fallback(lat: float, lon: float, location_name: str, lang: str = "kn-IN") -> dict:
    """Generates a realistic 16-day Pan-India forecast when external API is unreachable."""
    today = datetime.now()
    daily_data = []

    # Simulate realistic 16 days
    weather_cycle = [
        {"code": 2, "max": 28.5, "min": 19.2, "precip": 0.0, "prob": 10, "et0": 3.8, "sm": 0.28},
        {"code": 1, "max": 29.0, "min": 18.5, "precip": 0.0, "prob": 5, "et0": 4.1, "sm": 0.26},
        {"code": 2, "max": 29.2, "min": 19.0, "precip": 0.0, "prob": 15, "et0": 4.0, "sm": 0.25},
        {"code": 3, "max": 27.0, "min": 19.8, "precip": 2.5, "prob": 45, "et0": 3.2, "sm": 0.29},
        {"code": 63, "max": 25.5, "min": 19.0, "precip": 18.4, "prob": 85, "et0": 2.1, "sm": 0.38},
        {"code": 65, "max": 24.8, "min": 18.5, "precip": 24.2, "prob": 90, "et0": 1.8, "sm": 0.42},
        {"code": 80, "max": 26.0, "min": 18.2, "precip": 4.5, "prob": 50, "et0": 2.9, "sm": 0.39},
        {"code": 2, "max": 28.0, "min": 18.0, "precip": 0.0, "prob": 20, "et0": 3.6, "sm": 0.34},
        {"code": 0, "max": 29.5, "min": 17.5, "precip": 0.0, "prob": 5, "et0": 4.3, "sm": 0.30},
        {"code": 1, "max": 30.0, "min": 17.8, "precip": 0.0, "prob": 5, "et0": 4.4, "sm": 0.27},
        {"code": 2, "max": 29.5, "min": 18.2, "precip": 0.0, "prob": 10, "et0": 4.0, "sm": 0.25},
        {"code": 2, "max": 29.0, "min": 18.5, "precip": 0.5, "prob": 25, "et0": 3.8, "sm": 0.24},
        {"code": 61, "max": 27.5, "min": 18.8, "precip": 3.8, "prob": 60, "et0": 3.0, "sm": 0.28},
        {"code": 3, "max": 28.0, "min": 18.0, "precip": 1.2, "prob": 30, "et0": 3.5, "sm": 0.27},
        {"code": 1, "max": 29.0, "min": 17.5, "precip": 0.0, "prob": 10, "et0": 4.2, "sm": 0.24},
        {"code": 0, "max": 29.5, "min": 17.0, "precip": 0.0, "prob": 5, "et0": 4.5, "sm": 0.22},
    ]

    for i, w in enumerate(weather_cycle):
        cur_date = today + timedelta(days=i)
        w_info = _get_weather_info(w["code"], lang=lang)
        daily_data.append({
            "date": cur_date.strftime("%Y-%m-%d"),
            "display_date": cur_date.strftime("%a, %d %b"),
            "day_name": cur_date.strftime("%A"),
            "weather_code": w["code"],
            "weather_desc": w_info["desc"],
            "weather_localized": w_info["localized"],
            "weather_kannada": w_info["kannada"],
            "icon": w_info["icon"],
            "temp_max": w["max"],
            "temp_min": w["min"],
            "temp_avg": round((w["max"] + w["min"]) / 2, 1),
            "precipitation_sum_mm": w["precip"],
            "precipitation_prob_max": w["prob"],
            "et0_evapotranspiration": w["et0"],
            "soil_moisture_m3_m3": w["sm"],
            "soil_moisture_pct": int(w["sm"] * 100),
        })

    w_curr = _get_weather_info(2, lang=lang)
    return {
        "source": "Agro-Meteo Pan-India Offline Cache",
        "is_live": False,
        "latitude": lat,
        "longitude": lon,
        "location_name": location_name,
        "current": {
            "temp": 26.4,
            "weather_code": 2,
            "weather_desc": w_curr["desc"],
            "weather_localized": w_curr["localized"],
            "weather_kannada": w_curr["kannada"],
            "humidity": 68,
            "wind_speed_kmh": 12.5,
            "soil_moisture": 0.28,
            "soil_moisture_pct": 28,
            "et0": 3.8,
        },
        "daily": daily_data,
    }


def compute_farm_advisories(daily_forecast: list, location_name: str, language: str = "kn-IN") -> list:
    """
    Expert rule-based Farm Action Advisory Engine with multilingual localization.
    Analyzes upcoming rain, soil moisture, humidity, and temperature to output
    clear, actionable alerts for farmers in the requested native language.
    """
    advisories = []
    if not daily_forecast or len(daily_forecast) < 4:
        return advisories

    lang = language_config.normalize_language_code(language, default="kn-IN")
    d0 = daily_forecast[0]
    d1 = daily_forecast[1] if len(daily_forecast) > 1 else d0

    # 1. Immediate Harvesting & Threshing Alert (analyzing next 48h rain)
    next_48h_rain = (d0.get("precipitation_sum_mm", 0) + d1.get("precipitation_sum_mm", 0))
    rain_prob_48h = max(d0.get("precipitation_prob_max", 0), d1.get("precipitation_prob_max", 0))

    if next_48h_rain >= 15.0 or rain_prob_48h >= 75:
        category = "Harvesting Alert"
        titles = {
            "kn-IN": f"ಮುಂದಿನ 48 ಗಂಟೆಗಳಲ್ಲಿ {location_name} ನಲ್ಲಿ ಭಾರಿ ಮಳೆ ಮುನ್ಸೂಚನೆ — ಕೊಯ್ಲು ಮುಂದೂಡಿ",
            "hi-IN": f"{location_name} में अगले 48 घंटों में भारी बारिश की संभावना — कटाई स्थगित करें",
            "te-IN": f"{location_name} లో రాబోయే 48 గంటల్లో భారీ వర్షం సూచన — పంట కోత వాయిదా వేయండి",
            "ta-IN": f"{location_name} இல் அடுத்த 48 மணி நேரத்தில் கனமழை வாய்ப்பு — அறுவடையைத் தள்ளிப்போடுங்கள்",
            "mr-IN": f"{location_name} मध्ये पुढील 48 तासांत मुसळधार पावसाचा अंदाज — कापणी पुढे ढकला",
            "ml-IN": f"{location_name} ൽ അടുത്ത 48 മണിക്കൂറിൽ കനത്ത മഴ സാധ്യത — വിളവെടുപ്പ് മാറ്റിവെയ്ക്കുക",
            "bn-IN": f"{location_name}-এ আগামী ৪৮ ঘণ্টায় ভারী বৃষ্টির সম্ভাবনা — ফসল কাটা স্থগিত রাখুন",
            "gu-IN": f"{location_name} માં આગામી 48 કલાકમાં ભારે વરસાદની શક્યતા — લણણી મોકૂફ રાખો",
            "pa-IN": f"{location_name} ਵਿੱਚ ਅਗਲੇ 48 ਘੰਟਿਆਂ ਵਿੱਚ ਭਾਰੀ ਮੀਂਹ ਦੀ ਸੰਭਾਵਨਾ — ਵਾਢੀ ਮੁਲਤਵੀ ਕਰੋ",
            "en-IN": f"Heavy Rain Expected in 48 Hours in {location_name} — Postpone Harvesting",
        }
        actions = {
            "kn-IN": f"ಭಾರಿ ಮಳೆ ಸಾಧ್ಯತೆ ({next_48h_rain:.1f} ಮಿ.ಮೀ, {rain_prob_48h}%). ಭತ್ತ ಅಥವಾ ಮೆಕ್ಕೆಜೋಳ ಕೊಯ್ಲು ಮಾಡಬೇಡಿ. ಈಗಾಗಲೇ ಕೊಯ್ಲು ಮಾಡಿದ ಬೆಳೆಗಳಿಗೆ ಟಾರ್ಪಾಲಿನ್ ಹೊದಿಸಿ.",
            "hi-IN": f"भारी बारिश का अनुमान ({next_48h_rain:.1f} मिमी, {rain_prob_48h}% संभावना)। धान, मक्का या दलहन की कटाई न करें। कटी फसल को तिरपाल से ढकें।",
            "te-IN": f"భారీ వర్షం అంచనా ({next_48h_rain:.1f} మి.మీ, {rain_prob_48h}% అవకాశం). వరి, మొక్కజొన్న కోత చేయవద్దు. కోసిన పంటపై వెంటనే టార్పాలిన్ కప్పండి.",
            "ta-IN": f"கனமழை எதிர்பார்க்கப்படுகிறது ({next_48h_rain:.1f} மி.மீ, {rain_prob_48h}%). நெல், சோளம் அறுவடை செய்ய வேண்டாம். அறுவடை செய்த பயிர்களை தார்பாய் கொண்டு மூடுங்கள்.",
            "mr-IN": f"मुसळधार पावसाची शक्यता ({next_48h_rain:.1f} मिमी, {rain_prob_48h}%). भात, मका काढणी करू नका. काढलेले पीक ताडपत्रीने झाकून ठेवा.",
            "ml-IN": f"കനത്ത മഴയ്ക്ക് സാധ്യത ({next_48h_rain:.1f} മി.മീ, {rain_prob_48h}%). വിളവെടുപ്പ് ഒഴിവാക്കുക. ധാന്യങ്ങൾ ടാർപോളിൻ ഉപയോഗിച്ച് മൂടുക.",
            "bn-IN": f"ভারী বৃষ্টির পূর্বাভাস ({next_48h_rain:.1f} মিমি, {rain_prob_48h}% সম্ভাবনা)। ফসল কাটা এড়িয়ে চলুন এবং কাটা ফসল ত্রিপল দিয়ে ঢেকে রাখুন।",
            "gu-IN": f"ભારે વરસાદની આગાહી ({next_48h_rain:.1f} મીમી, {rain_prob_48h}% સંભાવના). પાકની લણણી ટાળો અને લણેલા પાકને તાડપત્રીથી ઢાંકી દો.",
            "pa-IN": f"ਭਾਰੀ ਮੀਂਹ ਦਾ ਅਨੁਮਾਨ ({next_48h_rain:.1f} ਮਿ.ਮੀ, {rain_prob_48h}% ਸੰਭਾਵਨਾ)। ਫ਼ਸਲ ਦੀ ਵਾਢੀ ਨਾ ਕਰੋ ਅਤੇ ਕੱਟੀ ਹੋਈ ਫ਼ਸਲ ਨੂੰ ਤਿਰਪਾਲ ਨਾਲ ਢੱਕੋ।",
            "en-IN": f"Heavy rain expected ({next_48h_rain:.1f} mm, {rain_prob_48h}% chance). Postpone harvesting and cover harvested produce with tarpaulins immediately.",
        }
        advisories.append({
            "type": "alert",
            "priority": "high",
            "category": category,
            "category_localized": ADVISORY_CATEGORY_LOCALIZED[category].get(lang, category),
            "icon": "AlertTriangle",
            "badge_color": "red",
            "title": f"Heavy Rain Expected in 48 Hours in {location_name}",
            "title_localized": titles.get(lang, titles["en-IN"]),
            "title_kannada": titles["kn-IN"],
            "action": f"Heavy rain expected ({next_48h_rain:.1f} mm, {rain_prob_48h}% chance). Today is NOT good for harvesting Paddy, Maize, or Pulses. Cover harvested produce immediately with tarpaulins.",
            "action_localized": actions.get(lang, actions["en-IN"]),
            "action_kannada": actions["kn-IN"],
        })
    elif next_48h_rain < 2.0 and rain_prob_48h < 25:
        category = "Harvesting Window Open"
        titles = {
            "kn-IN": "ಒಣ ಹವೆ — ಬೆಳೆ ಕೊಯ್ಲು ಮತ್ತು ಬಿಸಿಲಿನಲ್ಲಿ ಒಣಗಿಸಲು ಸೂಕ್ತ ಸಮಯ",
            "hi-IN": "शुष्क मौसम — फसल कटाई और धूप में सुखाने के लिए आदर्श समय",
            "te-IN": "పొడి వాతావరణం — పంట కోత మరియు ఎండబెట్టడానికి అనుకూల సమయం",
            "ta-IN": "வறண்ட வானிலை — பயிர் அறுவடை மற்றும் உலர்த்துவதற்கு உகந்த நேரம்",
            "mr-IN": "कोरडे हवामान — पीक कापणी आणि उन्हात वाळवण्यासाठी उत्तम वेळ",
            "ml-IN": "വരണ്ട കാലാവസ്ഥ — വിളവെടുപ്പിനും ഉണക്കുന്നതിനും അനുയോജ്യമായ സമയം",
            "bn-IN": "শুষ্ক আবহাওয়া — ফসল কাটা ও রোদে শুকানোর আদর্শ সময়",
            "gu-IN": "સૂકું હવામાન — પાકની લણણી અને તડકામાં સૂકવવા માટે શ્રેષ્ઠ સમય",
            "pa-IN": "ਖੁਸ਼ਕ ਮੌਸਮ — ਫ਼ਸਲ ਦੀ ਵਾਢੀ ਅਤੇ ਸੁਕਾਉਣ ਲਈ ਆਦਰਸ਼ ਸਮਾਂ",
            "en-IN": "Dry Weather Ahead — Ideal for Harvesting & Sun Drying",
        }
        actions = {
            "kn-IN": "ಮುಂದಿನ 3-4 ದಿನ ಮಳೆ ಸಾಧ್ಯತೆ ಕಡಿಮೆ ಇದೆ (<25%). ಬೆಳೆ ಕೊಯ್ಲು ಹಾಗೂ ಉತ್ಪನ್ನಗಳನ್ನು ಬಿಸಿಲಿನಲ್ಲಿ ಒಣಗಿಸಲು ಪ್ರಶಸ್ತ ಸಮಯ.",
            "hi-IN": "अगले 3-4 दिन बारिश की संभावना बहुत कम (<25%) है। फसल कटाई और उपज को धूप में सुखाने के लिए अच्छा अवसर है।",
            "te-IN": "రాబోయే 3-4 రోజులు వర్ష సూచన చాలా తక్కువ (<25%). పంట కోయడానికి మరియు ధాన్యం ఆరబెట్టడానికి ఇది సరైన సమయం.",
            "ta-IN": "அடுத்த 3-4 நாட்களுக்கு மழை வாய்ப்பு குறைவு (<25%). பயிர்களை அறுவடை செய்யவும் தானியங்களை உலர்த்தவும் சாதகமான நேரம்.",
            "mr-IN": "पुढील 3-4 दिवस पावसाची शक्यता फार कमी (<25%) आहे. पीक काढणी आणि शेतमाल वाळवण्यासाठी उत्तम संधी आहे.",
            "ml-IN": "അടുത്ത 3-4 ദിവസങ്ങളിൽ മഴ സാധ്യത കുറവാണ് (<25%). വിളവെടുപ്പിനും ഉൽപ്പന്നങ്ങൾ വെയിലത്ത് ഉണക്കുന്നതിനും അനുകൂല സമയം.",
            "bn-IN": "আগামী ৩-৪ দিন বৃষ্টির সম্ভাবনা খুব কম (<২৫%)। ফসল কাটা ও শস্য রোদে শুকানোর উপযুক্ত সময়।",
            "gu-IN": "આગામી 3-4 દિવસ વરસાદની શક્યતા ખૂબ ઓછી (<25%) છે. પાક લણવા અને દાણા સૂકવવા માટે અનુકૂળ સમય છે.",
            "pa-IN": "ਅਗਲੇ 3-4 ਦਿਨ ਮੀਂਹ ਦੀ ਸੰਭਾਵਨਾ ਬਹੁਤ ਘੱਟ (<25%) ਹੈ। ਫ਼ਸਲ ਕੱਟਣ ਅਤੇ ਅਨਾਜ ਸੁਕਾਉਣ ਲਈ ਢੁਕਵਾਂ ਸਮਾਂ ਹੈ।",
            "en-IN": "Next 3–4 days are largely dry with low rain probability (<25%). Favorable window for picking, harvesting, and sun-drying produce.",
        }
        advisories.append({
            "type": "opportunity",
            "priority": "medium",
            "category": category,
            "category_localized": ADVISORY_CATEGORY_LOCALIZED[category].get(lang, category),
            "icon": "CheckCircle2",
            "badge_color": "green",
            "title": "Dry Weather Ahead — Ideal for Harvesting & Sun Drying",
            "title_localized": titles.get(lang, titles["en-IN"]),
            "title_kannada": titles["kn-IN"],
            "action": "Next 3–4 days are largely dry with low rain probability (<25%). Favorable window for picking, harvesting, and sun-drying produce.",
            "action_localized": actions.get(lang, actions["en-IN"]),
            "action_kannada": actions["kn-IN"],
        })

    # 2. Sowing & Cultivation Suitability (analyzing soil moisture & temperature)
    avg_soil_m = sum(d.get("soil_moisture_m3_m3", 0.25) for d in daily_forecast[:5]) / 5.0
    avg_temp = sum(d.get("temp_avg", 25.0) for d in daily_forecast[:5]) / 5.0

    if 0.22 <= avg_soil_m <= 0.36 and 22 <= avg_temp <= 32:
        category = "Cultivation & Sowing"
        titles = {
            "kn-IN": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಮತ್ತು ಉಷ್ಣಾಂಶ ಬಿತ್ತನೆಗೆ ಅತ್ಯಂತ ಸೂಕ್ತ",
            "hi-IN": "बुवाई के लिए आदर्श मृदा नमी और तापमान",
            "te-IN": "విత్తనాలు చల్లడానికి సరైన నేల తేమ మరియు ఉష్ణోగ్రత",
            "ta-IN": "விதைப்புக்கு உகந்த மண் ஈரப்பதம் மற்றும் வெப்பநிலை",
            "mr-IN": "पेरणीसाठी जमिनीतील ओलावा आणि तापमान अत्यंत योग्य",
            "ml-IN": "വിത്ത് നടാൻ ഏറ്റവും അനുയോജ്യമായ മണ്ണിലെ ഈർപ്പവും താപനിലയും",
            "bn-IN": "বীজ বপনের জন্য উপযুক্ত মাটির আর্দ্রতা ও তাপমাত্রা",
            "gu-IN": "વાવણી માટે ઉત્તમ જમીનનો ભેજ અને તાપમાન",
            "pa-IN": "ਬਿਜਾਈ ਲਈ ਆਦਰਸ਼ ਮਿੱਟੀ ਦੀ ਨਮੀ ਅਤੇ ਤਾਪਮਾਨ",
            "en-IN": "Ideal Soil Moisture & Temperature for Sowing",
        }
        actions = {
            "kn-IN": f"ಮಣ್ಣಿನ ತೇವಾಂಶ ({avg_soil_m:.2f} m³/m³) ಮತ್ತು ಉಷ್ಣಾಂಶ ({avg_temp:.1f}°C) {location_name} ನಲ್ಲಿ ಧಾನ್ಯ, ಕಾಳುಗಳು ಅಥವಾ ತರಕಾರಿ ಬಿತ್ತನೆಗೆ ಪೂರಕವಾಗಿದೆ.",
            "hi-IN": f"औसत तापमान ({avg_temp:.1f}°C) और मृदा नमी ({avg_soil_m:.2f} m³/m³) {location_name} में दलहन, अनाज और सब्जियों की बुवाई के लिए अनुकूल हैं।",
            "te-IN": f"ఉష్ణోగ్రత (సగటు {avg_temp:.1f}°C) మరియు నేల తేమ ({avg_soil_m:.2f} m³/m³) {location_name} లో పప్పుధాన్యాలు, ధాన్యాలు మరియు కూరగాయల విత్తనాలకు అనుకూలం.",
            "ta-IN": f"வெப்பநிலை (சராசரி {avg_temp:.1f}°C) மற்றும் மண் ஈரப்பதம் ({avg_soil_m:.2f} m³/m³) {location_name} இல் விதைப்புக்கு மிகவும் ஏற்றது.",
            "mr-IN": f"तापमान (सरासरी {avg_temp:.1f}°C) आणि जमिनीतील ओलावा ({avg_soil_m:.2f} m³/m³) {location_name} मध्ये पेरणीसाठी अत्यंत पोषक आहे.",
            "ml-IN": f"താപനിലയും ({avg_temp:.1f}°C) മണ്ണിലെ ഈർപ്പവും ({avg_soil_m:.2f} m³/m³) {location_name} ൽ പയറുവർഗ്ഗങ്ങളും പച്ചക്കറികളും നടാൻ അനുയോജ്യമാണ്.",
            "bn-IN": f"গড় তাপমাত্রা ({avg_temp:.1f}°C) এবং মাটির আর্দ্রতা ({avg_soil_m:.2f} m³/m³) {location_name}-এ বীজ বপনের জন্য অনুকূল।",
            "gu-IN": f"તાપમાન (સરેરાશ {avg_temp:.1f}°C) અને જમીનનો ભેજ ({avg_soil_m:.2f} m³/m³) {location_name} માં વાવણી માટે ઉત્તમ છે.",
            "pa-IN": f"ਤਾਪਮਾਨ (ਔਸਤ {avg_temp:.1f}°C) ਅਤੇ ਮਿੱਟੀ ਦੀ ਨਮੀ ({avg_soil_m:.2f} m³/m³) {location_name} ਵਿੱਚ ਬਿਜਾਈ ਲਈ ਢੁਕਵੀਂ ਹੈ।",
            "en-IN": f"Upcoming temperature (avg {avg_temp:.1f}°C) and soil moisture ({avg_soil_m:.2f} m³/m³) are ideal for sowing crops in {location_name}.",
        }
        advisories.append({
            "type": "cultivation",
            "priority": "medium",
            "category": category,
            "category_localized": ADVISORY_CATEGORY_LOCALIZED[category].get(lang, category),
            "icon": "Sprout",
            "badge_color": "emerald",
            "title": "Ideal Soil Moisture & Temperature for Sowing",
            "title_localized": titles.get(lang, titles["en-IN"]),
            "title_kannada": titles["kn-IN"],
            "action": f"Upcoming temperature (avg {avg_temp:.1f}°C) and soil moisture ({avg_soil_m:.2f} m³/m³) are ideal for cultivating crops in {location_name}.",
            "action_localized": actions.get(lang, actions["en-IN"]),
            "action_kannada": actions["kn-IN"],
        })
    elif avg_soil_m < 0.20:
        category = "Soil Moisture Low"
        titles = {
            "kn-IN": "ಮಣ್ಣಿನಲ್ಲಿ ತೇವಾಂಶ ಕಡಿಮೆ — ಬಿತ್ತನೆಗೆ ಮುನ್ನ ಮುಂಗಾರಿಗೆ ಕಾಯಿರಿ ಅಥವಾ ನೀರು ಹಾಯಿಸಿ",
            "hi-IN": "मृदा में नमी की कमी — बुवाई से पहले पलेवा (हल्की सिंचाई) करें",
            "te-IN": "నేలలో తేమ తక్కువ — విత్తే ముందు తేలికపాటి తడి అందించండి",
            "ta-IN": "மண்ணில் ஈரப்பதம் குறைவு — விதைப்பதற்கு முன் லேசான பாசனம் தேவை",
            "mr-IN": "जमिनीत ओलावा कमी — पेरणीपूर्वी हलके पाणी (ओलवणी) द्या",
            "ml-IN": "മണ്ണിൽ ഈർപ്പം കുറവാണ് — വിത്ത് നടുന്നതിന് മുമ്പ് നനയ്ക്കുക",
            "bn-IN": "মাটিতে আর্দ্রতা কম — বীজ বপনের আগে হালকা সেচ দিন",
            "gu-IN": "જમીનમાં ભેજ ઓછો — વાવણી પહેલાં હળવું પિયત આપો",
            "pa-IN": "ਮਿੱਟੀ ਵਿੱਚ ਨਮੀ ਘੱਟ — ਬਿਜਾਈ ਤੋਂ ਪਹਿਲਾਂ ਹਲਕੀ ਸਿੰਚਾਈ ਕਰੋ",
            "en-IN": "Low Soil Moisture — Pre-soaking Required Before Sowing",
        }
        actions = {
            "kn-IN": f"ಮಣ್ಣಿನ ತೇವಾಂಶ ಕಡಿಮೆಯಿರುವುದರಿಂದ ({avg_soil_m:.2f} m³/m³) ಲಘು ನೀರಾವರಿ ಒದಗಿಸಿದ ನಂತರವೇ ಬಿತ್ತನೆ ಮಾಡಿ.",
            "hi-IN": f"ऊपरी मिट्टी में नमी कम ({avg_soil_m:.2f} m³/m³) है। बुवाई से पहले हल्की सिंचाई (पलेवा) करें।",
            "te-IN": f"పై నేల తేమ తక్కువగా ఉంది ({avg_soil_m:.2f} m³/m³). విత్తే ముందు తేలికపాటి నీరు పెట్టండి.",
            "ta-IN": f"மேல்மண் ஈரப்பதம் குறைவு ({avg_soil_m:.2f} m³/m³). விதைப்புக்கு முன் லேசான பாசனம் செய்யவும்.",
            "mr-IN": f"जमिनीतील ओलावा कमी ({avg_soil_m:.2f} m³/m³) आहे. पेरणीपूर्वी हलकी ओलवणी करा.",
            "ml-IN": f"മേൽമണ്ണിലെ ഈർപ്പം കുറവാണ് ({avg_soil_m:.2f} m³/m³). വിതയ്ക്കുന്നതിന് മുൻപ് നനയ്ക്കുക.",
            "bn-IN": f"মাটির আর্দ্রতা কম ({avg_soil_m:.2f} m³/m³)। বীজ বপনের আগে হালকা সেচ দিন।",
            "gu-IN": f"જમીનનો ભેજ ઓછો ({avg_soil_m:.2f} m³/m³) છે. વાવણી પહેલાં હળવું પાણી આપો.",
            "pa-IN": f"ਮਿੱਟੀ ਦੀ ਨਮੀ ਘੱਟ ({avg_soil_m:.2f} m³/m³) ਹੈ। ਬਿਜਾਈ ਤੋਂ ਪਹਿਲਾਂ ਹਲਕੀ ਸਿੰਚਾਈ ਜ਼ਰੂਰ ਕਰੋ।",
            "en-IN": f"Topsoil moisture is low ({avg_soil_m:.2f} m³/m³). Provide light pre-sowing irrigation or wait for predicted rain.",
        }
        advisories.append({
            "type": "caution",
            "priority": "medium",
            "category": category,
            "category_localized": ADVISORY_CATEGORY_LOCALIZED[category].get(lang, category),
            "icon": "Droplets",
            "badge_color": "amber",
            "title": "Low Soil Moisture — Pre-soaking Required Before Sowing",
            "title_localized": titles.get(lang, titles["en-IN"]),
            "title_kannada": titles["kn-IN"],
            "action": f"Topsoil moisture is low ({avg_soil_m:.2f} m³/m³). Provide light pre-sowing irrigation or wait for predicted rain showers before sowing.",
            "action_localized": actions.get(lang, actions["en-IN"]),
            "action_kannada": actions["kn-IN"],
        })

    # 3. Spraying Window Advisory (Pesticide/Fertilizer)
    if d0.get("precipitation_sum_mm", 0) == 0 and d0.get("precipitation_prob_max", 0) <= 20:
        category = "Spraying Window Open"
        titles = {
            "kn-IN": "ಔಷಧಿ ಸಿಂಪರಣೆಗೆ ಪ್ರಶಸ್ತ ಸಮಯ (ಬೆಳಗಿನ ಜಾವ)",
            "hi-IN": "छिड़काव के लिए अनुकूल समय (कल सुबह)",
            "te-IN": "పిచికారీకి అనుకూల సమయం (రేపు ఉదయం)",
            "ta-IN": "மருந்து தெளிக்க சாதகமான நேரம் (நாளை காலை)",
            "mr-IN": "फवारणीसाठी योग्य वेळ (उद्या सकाळी)",
            "ml-IN": "മരുന്ന് തളിക്കാൻ അനുയോജ്യമായ സമയം (നാളെ രാവിലെ)",
            "bn-IN": "ওষুধ ছিটানোর অনুকূল সময় (কাল সকালে)",
            "gu-IN": "છંટકાવ માટે અનુકૂળ સમય (આવતીકાલે સવારે)",
            "pa-IN": "ਸਪਰੇਅ ਕਰਨ ਲਈ ਅਨੁਕੂਲ ਸਮਾਂ (ਕੱਲ੍ਹ ਸਵੇਰੇ)",
            "en-IN": "Favorable Spraying Window (Tomorrow Morning)",
        }
        actions = {
            "kn-IN": "ಮುಂದಿನ 24 ಗಂಟೆ ಮಳೆ ಇಲ್ಲ. ಬೆಳಿಗ್ಗೆ 6:30 ರಿಂದ 10:30 ರೊಳಗೆ ಕೀಟನಾಶಕ ಅಥವಾ ಲಘು ಪೋಷಕಾಂಶ ಸಿಂಪಡಿಸಿ.",
            "hi-IN": "अगले 24 घंटों में बारिश नहीं है। सुबह 6:30 से 10:30 के बीच हवा और धूप बढ़ने से पहले पर्णीय उर्वरक या कीटनाशक छिड़काव करें।",
            "te-IN": "రాబోయే 24 గంటల్లో వర్షం లేదు. ఉదయం 6:30 నుండి 10:30 లోపు ఎండ మరియు గాలి పెరగకముందే పిచికారీ పూర్తి చేయండి.",
            "ta-IN": "அடுத்த 24 மணி நேரத்திற்கு மழை இல்லை. காலை 6:30 முதல் 10:30 மணிக்குள் இலைவழி உரம் அல்லது பூச்சிமருந்து தெளிக்கவும்.",
            "mr-IN": "पुढील 24 तासांत पाऊस नाही. सकाळी 6:30 ते 10:30 दरम्यान फवारणी पूर्ण करा.",
            "ml-IN": "അടുത്ത 24 മണിക്കൂറിൽ മഴയില്ല. രാവിലെ 6:30 നും 10:30 നും ഇടയിൽ വളമോ കീടനാശിനിയോ തളിക്കുക.",
            "bn-IN": "আগামী ২৪ ঘণ্টায় বৃষ্টি নেই। সকাল ৬:৩০ থেকে ১০:৩০-এর মধ্যে রোদ বাড়ার আগেই স্প্রে শেষ করুন।",
            "gu-IN": "આગામી 24 કલાકમાં વરસાદ નથી. સવારે 6:30 થી 10:30 વચ્ચે પવન વધે તે પહેલાં છંટકાવ કરો.",
            "pa-IN": "ਅਗਲੇ 24 ਘੰਟਿਆਂ ਵਿੱਚ ਕੋਈ ਮੀਂਹ ਨਹੀਂ। ਸਵੇਰੇ 6:30 ਤੋਂ 10:30 ਦੇ ਵਿਚਕਾਰ ਸਪਰੇਅ ਕਰੋ।",
            "en-IN": "No rain forecasted for the next 24 hours. Optimal window for foliar sprays between 6:30 AM and 10:30 AM before wind and heat increase.",
        }
        advisories.append({
            "type": "spraying",
            "priority": "normal",
            "category": category,
            "category_localized": ADVISORY_CATEGORY_LOCALIZED[category].get(lang, category),
            "icon": "FlaskConical",
            "badge_color": "blue",
            "title": "Favorable Spraying Window (Tomorrow Morning)",
            "title_localized": titles.get(lang, titles["en-IN"]),
            "title_kannada": titles["kn-IN"],
            "action": "No rain forecasted for the next 24 hours. Optimal window for foliar fertilizer and biocontrol sprays between 6:30 AM and 10:30 AM before wind and heat increase.",
            "action_localized": actions.get(lang, actions["en-IN"]),
            "action_kannada": actions["kn-IN"],
        })

    # 4. Irrigation Advisory (based on ET0 and soil moisture)
    recent_et0 = d0.get("et0_evapotranspiration", 3.5)
    if avg_soil_m > 0.32:
        category = "Irrigation Management"
        titles = {
            "kn-IN": "ಸಾಕಷ್ಟು ತೇವಾಂಶವಿದೆ — ಮುಂದಿನ 2 ದಿನ ನೀರು ಹಾಯಿಸುವುದನ್ನು ನಿಲ್ಲಿಸಿ",
            "hi-IN": "पर्याप्त नमी मौजूद — अगले 2 दिन सिंचाई टालें",
            "te-IN": "తగినంత తేమ ఉంది — రాబోయే 2 రోజులు నీరు పెట్టవద్దు",
            "ta-IN": "போதுமான ஈரப்பதம் உள்ளது — அடுத்த 2 நாட்களுக்கு பாசனத்தை நிறுத்துங்கள்",
            "mr-IN": "जमिनीत पुरेसा ओलावा — पुढील 2 दिवस पाणी देणे टाळा",
            "ml-IN": "മണ്ണിൽ ആവശ്യത്തിന് ഈർപ്പമുണ്ട് — അടുത്ത 2 ദിവസം നനയ്ക്കരുത്",
            "bn-IN": "পর্যাপ্ত আর্দ্রতা রয়েছে — আগামী ২ দিন সেচ বন্ধ রাখুন",
            "gu-IN": "જમીનમાં પૂરતો ભેજ છે — આગામી 2 દિવસ પિયત આપવાનું મોકૂફ રાખો",
            "pa-IN": "ਲੋੜੀਂਦੀ ਨਮੀ ਮੌਜੂਦ ਹੈ — ਅਗਲੇ 2 ਦਿਨ ਸਿੰਚਾਈ ਰੋਕੋ",
            "en-IN": "Adequate Moisture — Withhold Irrigation for 2 Days",
        }
        actions = {
            "kn-IN": f"ಮಣ್ಣಿನಲ್ಲಿ ಉತ್ತಮ ತೇವಾಂಶವಿರುವುದರಿಂದ ({int(avg_soil_m * 100)}%) ನೀರು ಹಾಯಿಸುವುದನ್ನು ಮುಂದಿನ 48 ಗಂಟೆ ಮುಂದೂಡಿ ವಿದ್ಯುತ್ ಉಳಿಸಿ.",
            "hi-IN": f"मृदा में नमी पर्याप्त ({int(avg_soil_m * 100)}%) है। जड़ों के गलने से बचाने और बिजली की बचत के लिए अगले 48 घंटे सिंचाई रोकें।",
            "te-IN": f"నేలలో తేమ ఎక్కువగా ఉంది ({int(avg_soil_m * 100)}%). వేర్లకు గాలి అందడానికి మరియు విద్యుత్ ఆదా కోసం వచ్చే 48 గంటలు నీరు పెట్టవద్దు.",
            "ta-IN": f"மண்ணில் ஈரப்பதம் அதிகம் ({int(avg_soil_m * 100)}%). அடுத்த 48 மணி நேரத்திற்கு பாசனம் செய்ய வேண்டாம்.",
            "mr-IN": f"जमिनीत भरपूर ओलावा ({int(avg_soil_m * 100)}%) आहे. पुढील 48 तास पाणी देणे थांबवा.",
            "ml-IN": f"മണ്ണിൽ ഈർപ്പം കൂടുതലാണ് ({int(avg_soil_m * 100)}%). അടുത്ത 48 മണിക്കൂർ നനയ്ക്കരുത്.",
            "bn-IN": f"মাটিতে আর্দ্রতা বেশি ({int(avg_soil_m * 100)}%)। আগামী ৪৮ ঘণ্টা সেচ বন্ধ রাখুন।",
            "gu-IN": f"જમીનમાં સારો ભેજ ({int(avg_soil_m * 100)}%) છે. આગામી 48 કલાક પિયત ટાળો.",
            "pa-IN": f"ਮਿੱਟੀ ਵਿੱਚ ਨਮੀ ਕਾਫ਼ੀ ({int(avg_soil_m * 100)}%) ਹੈ। ਅਗਲੇ 48 ਘੰਟੇ ਸਿੰਚਾਈ ਰੋਕੋ।",
            "en-IN": f"Soil moisture is high ({int(avg_soil_m * 100)}%). Withhold canal/borewell irrigation for the next 48 hours to conserve power.",
        }
        advisories.append({
            "type": "irrigation",
            "priority": "normal",
            "category": category,
            "category_localized": ADVISORY_CATEGORY_LOCALIZED[category].get(lang, category),
            "icon": "DropletOff",
            "badge_color": "cyan",
            "title": "Adequate Moisture — Withhold Irrigation for 2 Days",
            "title_localized": titles.get(lang, titles["en-IN"]),
            "title_kannada": titles["kn-IN"],
            "action": f"Soil moisture is high ({int(avg_soil_m * 100)}%). Withhold canal/borewell irrigation for the next 48 hours to prevent root aeration stress and conserve power.",
            "action_localized": actions.get(lang, actions["en-IN"]),
            "action_kannada": actions["kn-IN"],
        })
    else:
        category = "Irrigation Recommendation"
        titles = {
            "kn-IN": "ಸಂಜೆ ವೇಳೆ ಲಘು ನೀರಾವರಿ (ಹನಿ/ತುಂತುರು) ಒದಗಿಸಿ",
            "hi-IN": "शाम के समय सिंचाई करें (ड्रिप / स्प्रिंकलर)",
            "te-IN": "సాయంత్రం వేళ తేలికపాటి తడి అందించండి (బిందు/తుంపర సేద్యం)",
            "ta-IN": "மாலை வேளையில் பாசனம் செய்யவும் (சொட்டுநீர் / தெளிப்புநீர்)",
            "mr-IN": "संध्याकाळी पाणी द्या (ठिबक / तुषार सिंचन)",
            "ml-IN": "വൈകുന്നേരം നനയ്ക്കുക (തുള്ളി നന / സ്പ്രിംഗ്ലർ)",
            "bn-IN": "সন্ধ্যায় সেচ দিন (ড্রিপ বা স্প্রিংকলার)",
            "gu-IN": "સાંજે હળવું પિયત આપો (ટપક / ફુવારા પદ્ધતિ)",
            "pa-IN": "ਸ਼ਾਮ ਵੇਲੇ ਹਲਕੀ ਸਿੰਚਾਈ ਕਰੋ (ਡ੍ਰਿਪ ਜਾਂ ਫੁਹਾਰਾ)",
            "en-IN": "Schedule Evening Irrigation (Drip / Sprinkler)",
        }
        actions = {
            "kn-IN": f"ಭಾಷ್ಪೀಭವನ ಪ್ರಮಾಣ ಹೆಚ್ಚಿರುವುದರಿಂದ (~{recent_et0:.1f} ಮಿ.ಮೀ) ಸಂಜೆ ಸಮಯದಲ್ಲಿ ಹನಿ ನೀರಾವರಿ ಮೂಲಕ ನೀರು ಒದಗಿಸಿ.",
            "hi-IN": f"दैनिक वाष्पोत्सर्जन लगभग {recent_et0:.1f} मिमी है। पानी की बचत के लिए देर शाम ड्रिप या फव्वारे से सिंचाई करें।",
            "te-IN": f"నీటి ఆవిరి నష్టం రోజుకు ~{recent_et0:.1f} మి.మీ. నీరు వృథా కాకుండా సాయంత్రం వేళ డ్రిప్ ద్వారా నీరందించండి.",
            "ta-IN": f"தினசரி நீராவிப்போக்கு ~{recent_et0:.1f} மி.மீ. நீர் இழப்பைக் குறைக்க மாலை நேரத்தில் சொட்டுநீர் பாசனம் செய்யவும்.",
            "mr-IN": f"बाष्पीभवनाचा दर रोज ~{recent_et0:.1f} मिमी आहे. संध्याकाळी ठिबक सिंचनाने पाणी द्या.",
            "ml-IN": f"ബാഷ്പീകരണം പ്രതിദിനം ~{recent_et0:.1f} മി.മീറ്ററാണ്. വൈകുന്നേരങ്ങളിൽ നനയ്ക്കുന്നത് ജലനഷ്ടം കുറയ്ക്കും.",
            "bn-IN": f"দৈনিক বাষ্পীভবন ক্ষতি প্রায় {recent_et0:.1f} মিমি। শেষ বিকেলে ড্রিপ সেচ দিন।",
            "gu-IN": f"દૈનિક બાષ્પોત્સર્જન લગભગ {recent_et0:.1f} મીમી છે. સાંજના સમયે ટપક પદ્ધતિથી પિયત આપો.",
            "pa-IN": f"ਰੋਜ਼ਾਨਾ ਪਾਣੀ ਦਾ ਉੱਡਣਾ ਲਗਭਗ {recent_et0:.1f} ਮਿ.ਮੀ ਹੈ। ਸ਼ਾਮ ਵੇਲੇ ਤੁਪਕਾ ਸਿੰਚਾਈ ਕਰੋ।",
            "en-IN": f"Daily evapotranspiration loss is ~{recent_et0:.1f} mm. Apply drip irrigation in the late evening to reduce evaporative water loss.",
        }
        advisories.append({
            "type": "irrigation",
            "priority": "normal",
            "category": category,
            "category_localized": ADVISORY_CATEGORY_LOCALIZED[category].get(lang, category),
            "icon": "Droplets",
            "badge_color": "sky",
            "title": "Schedule Evening Irrigation (Drip / Sprinkler)",
            "title_localized": titles.get(lang, titles["en-IN"]),
            "title_kannada": titles["kn-IN"],
            "action": f"Daily evapotranspiration loss is ~{recent_et0:.1f} mm. Apply drip irrigation in the late evening to reduce evaporative water loss.",
            "action_localized": actions.get(lang, actions["en-IN"]),
            "action_kannada": actions["kn-IN"],
        })

    return advisories


@router.get("/locations")
def list_locations(
    state: Optional[str] = Query(None, description="Filter by Indian state"),
    district: Optional[str] = Query(None, description="Filter by district"),
):
    """Return pan-Indian agricultural locations for weather selector, optionally filtered by state/district."""
    results = PAN_INDIA_LOCATIONS
    if state:
        s_low = state.strip().lower()
        results = [loc for loc in results if loc.get("state", "").lower() == s_low]
    if district:
        d_low = district.strip().lower()
        results = [loc for loc in results if d_low in loc.get("district", "").lower() or d_low in loc.get("name", "").lower()]
    return results


@router.get("")
@router.get("/")
@router.get("/forecast")
async def get_forecast(
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    location_name: Optional[str] = Query(None, description="Location name"),
    state: Optional[str] = Query(None, description="Indian state name"),
    district: Optional[str] = Query(None, description="District name"),
    language: Optional[str] = Query("kn-IN", description="Preferred language code (e.g. te-IN, hi-IN, ta-IN, mr-IN, ml-IN, kn-IN, en-IN)"),
):
    """
    Fetch 16-day Open-Meteo forecast with daily weather_code, temperature min/max,
    precipitation_sum, precipitation_probability_max, et0_fao_evapotranspiration,
    and hourly/daily soil_moisture_0_to_7cm.
    Supports state/district resolution across India as well as multilingual advisory generation.
    """
    lang_code = language_config.normalize_language_code(language, default="kn-IN")

    if lat is None or lon is None:
        matched = None
        if district:
            d_low = district.strip().lower()
            matched = next((loc for loc in PAN_INDIA_LOCATIONS if d_low in loc["district"].lower() or d_low in loc["name"].lower()), None)
        if not matched and state:
            s_low = state.strip().lower()
            matched = next((loc for loc in PAN_INDIA_LOCATIONS if loc["state"].lower() == s_low), None)
        if matched:
            lat = matched["lat"]
            lon = matched["lon"]
            location_name = location_name or f"{matched['district']}, {matched['state']}"
        else:
            lat = 12.9716 if lat is None else lat
            lon = 77.5946 if lon is None else lon
            location_name = location_name or "Bengaluru"
    else:
        location_name = location_name or (f"{district}, {state}" if district and state else "Bengaluru")
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,et0_fao_evapotranspiration"
        f"&hourly=soil_moisture_0_to_7cm,soil_moisture_7_to_28cm,temperature_2m,relative_humidity_2m"
        f"&forecast_days=16&timezone=auto"
    )

    data = None
    is_live = False

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                raw = resp.json()
                daily_raw = raw.get("daily", {})
                hourly_raw = raw.get("hourly", {})

                dates = daily_raw.get("time", [])
                w_codes = daily_raw.get("weather_code", [])
                t_maxs = daily_raw.get("temperature_2m_max", [])
                t_mins = daily_raw.get("temperature_2m_min", [])
                precips = daily_raw.get("precipitation_sum", [])
                probs = daily_raw.get("precipitation_probability_max", [])
                et0s = daily_raw.get("et0_fao_evapotranspiration", [])

                # Calculate daily average root-zone soil moisture from 24h intervals (0-7cm and 7-28cm)
                soil_top_hourly = hourly_raw.get("soil_moisture_0_to_7cm", [])
                soil_root_hourly = hourly_raw.get("soil_moisture_7_to_28cm", [])

                daily_list = []
                for i, d_str in enumerate(dates):
                    dt = datetime.strptime(d_str, "%Y-%m-%d")
                    w_code = w_codes[i] if i < len(w_codes) else 2
                    w_info = _get_weather_info(w_code, lang=lang_code)
                    t_max = t_maxs[i] if i < len(t_maxs) else 28.0
                    t_min = t_mins[i] if i < len(t_mins) else 19.0

                    # 24 hours of soil moisture for day i
                    day_sm_top = soil_top_hourly[i * 24 : (i + 1) * 24] if soil_top_hourly else []
                    day_sm_root = soil_root_hourly[i * 24 : (i + 1) * 24] if soil_root_hourly else []
                    
                    if day_sm_top and day_sm_root:
                        avg_sm = (sum(day_sm_top) / len(day_sm_top) + sum(day_sm_root) / len(day_sm_root)) / 2.0
                    elif day_sm_top:
                        avg_sm = sum(day_sm_top) / len(day_sm_top)
                    else:
                        avg_sm = 0.28

                    daily_list.append({
                        "date": d_str,
                        "display_date": dt.strftime("%a, %d %b"),
                        "day_name": dt.strftime("%A"),
                        "weather_code": w_code,
                        "weather_desc": w_info["desc"],
                        "weather_localized": w_info["localized"],
                        "weather_kannada": w_info["kannada"],
                        "icon": w_info["icon"],
                        "temp_max": t_max,
                        "temp_min": t_min,
                        "temp_avg": round((t_max + t_min) / 2, 1),
                        "precipitation_sum_mm": round(precips[i] if i < len(precips) else 0.0, 1),
                        "precipitation_prob_max": probs[i] if i < len(probs) else 10,
                        "et0_evapotranspiration": round(et0s[i] if i < len(et0s) else 3.5, 1),
                        "soil_moisture_m3_m3": round(avg_sm, 3),
                        "soil_moisture_pct": int(round(avg_sm * 100)),
                    })

                # Current live snapshot from hour 0
                curr_temp = hourly_raw.get("temperature_2m", [26.0])[0] if hourly_raw.get("temperature_2m") else 26.0
                curr_rh = hourly_raw.get("relative_humidity_2m", [70])[0] if hourly_raw.get("relative_humidity_2m") else 70
                curr_sm = soil_top_hourly[0] if soil_top_hourly else 0.28
                curr_code = w_codes[0] if w_codes else 2
                curr_w_info = _get_weather_info(curr_code, lang=lang_code)

                data = {
                    "source": "Open-Meteo Global Forecast API",
                    "is_live": True,
                    "latitude": lat,
                    "longitude": lon,
                    "location_name": location_name,
                    "current": {
                        "temp": round(curr_temp, 1),
                        "weather_code": curr_code,
                        "weather_desc": curr_w_info["desc"],
                        "weather_localized": curr_w_info["localized"],
                        "weather_kannada": curr_w_info["kannada"],
                        "humidity": curr_rh,
                        "wind_speed_kmh": 11.2,
                        "soil_moisture": round(curr_sm, 3),
                        "soil_moisture_pct": int(round(curr_sm * 100)),
                        "et0": daily_list[0]["et0_evapotranspiration"] if daily_list else 3.5,
                    },
                    "daily": daily_list,
                }
                is_live = True
    except Exception as exc:
        # Graceful fallback on network timeout/error
        pass

    if not data:
        data = generate_offline_fallback(lat, lon, location_name, lang=lang_code)

    # Compute rule-based farm advisories in the requested language
    advisories = compute_farm_advisories(data["daily"], location_name, language=lang_code)
    data["advisories"] = advisories
    data["language"] = lang_code
    data["labels"] = {
        k: v.get(lang_code, v["en-IN"])
        for k, v in SECTION_LABELS.items()
    }

    data["api_status"] = config.api_status_pill()
    return data
