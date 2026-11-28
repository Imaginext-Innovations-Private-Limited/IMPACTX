"""
Meta WhatsApp Cloud API Webhook Connector & Local Simulator.
Handles:
- Webhook Verification (GET /api/whatsapp/webhook)
- Incoming Message Handler (POST /api/whatsapp/webhook)
  * Location messages (type == "location"): saves lat/lon, reverse-geocodes district/taluk via Nominatim, confirms in user's language
  * Text messages: enforces location capture for location-dependent queries, calls live Gemini with weather + APMC context
  * Audio / Voice notes: downloads audio, transcribes via Sarvam saaras:v4 (mode=codemix + agri keyterms), calls live Gemini in detected language, replies with OGG/Opus voice note + localized summary
  * Image attachments: downloads photo, runs live Gemini Vision (prompt before image, auto-classifies leaf/disease vs bottle/label vs blurry), replies in user's language
- Local Simulation (POST /api/whatsapp/simulate)
"""
import asyncio
import base64
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

import config
import language_config
import location_service
from routers import scan, voice

logger = logging.getLogger("whatsapp_bot")
router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

GRAPH_API_VERSION = "v26.0"
WHATSAPP_API_VERSION = GRAPH_API_VERSION

LOCATION_DEPENDENT_KEYWORDS = [
    # English
    "weather", "rain", "forecast", "temperature", "humidity", "wind", "climate",
    "disease", "blight", "pest", "spot", "rot", "wilt", "fungus", "insect", "worm", "borer",
    "leaf", "yellowing", "mandi", "apmc", "price", "rate", "market", "quintal", "sell",
    "soil", "ph", "loam", "clay", "irrigation", "spray", "sow", "harvest",
    # Kannada
    "ಮಳೆ", "ಹವಾಮಾನ", "ತಾಪಮಾನ", "ಬಿಸಿಲು", "ರೋಗ", "ಕೀಟ", "ಚುಕ್ಕೆ", "ಎಲೆ", "ಕೊಳೆ",
    "ದರ", "ಬೆಲೆ", "ಮಂಡಿ", "ಮಾರುಕಟ್ಟೆ", "ಮಣ್ಣು", "ನೀರು", "ಸಿಂಪರಣೆ", "ಕೊಯ್ಲು",
    # Hindi / Marathi
    "मौसम", "बारिश", "तापमान", "रोग", "कीट", "ब्लाइट", "पत्ती", "पत्ते", "फफूंद",
    "भाव", "दाम", "मंडी", "बाजार", "मिट्टी", "सिंचाई", "खाद", "पाऊस", "हवामान",
    "माती", "फवारणी", "कापणी", "पीक",
    # Telugu
    "వర్షం", "వాతావరణం", "ఉష్ణోగ్రత", "తెగులు", "పురుగు", "ఆకు", "ధర", "మార్కెట్",
    "మండి", "నేల", "మట్టి", "నీరు",
    # Tamil
    "மழை", "வானிலை", "நோய்", "பூச்சி", "இலை", "விலை", "சந்தை", "மண்", "நீர்",
]

LOCATION_ASK_MESSAGES = {
    "kn-IN": (
        "📍 ನಿಮ್ಮ ಪ್ರದೇಶದ ನಿಖರವಾದ ಹವಾಮಾನ, ಬೆಳೆ ರೋಗ ಮತ್ತು APMC ಮಂಡಿ ದರಗಳ ಮಾಹಿತಿಗಾಗಿ ದಯವಿಟ್ಟು ಮೊದಲು ನಿಮ್ಮ *ಲೈವ್ WhatsApp ಲೊಕೇಶನ್ ಪಿನ್* (📎 → Location → Send your current location) ಹಂಚಿಕೊಳ್ಳಿ ಅಥವಾ ನಿಮ್ಮ *ಗ್ರಾಮ / ತಾಲ್ಲೂಕು / ಜಿಲ್ಲೆಯ ಹೆಸರನ್ನು* ಟೈಪ್ ಮಾಡಿ ಕಳುಹಿಸಿ."
    ),
    "hi-IN": (
        "📍 आपके क्षेत्र के सटीक मौसम, फसल रोग और APMC मंडी भाव की जानकारी देने के लिए कृपया पहले अपना *लाइव WhatsApp लोकेशन पिन* (📎 → Location → Send your current location) भेजें या अपने *गाँव / तहसील / जिले का नाम* लिखकर भेजें।"
    ),
    "te-IN": (
        "📍 మీ ప్రాంతానికి సంబంధించిన ఖచ్చితమైన వాతావరణం, పంట తెగులు మరియు APMC మండి ధరల కోసం దయచేసి ముందుగా మీ *లైవ్ WhatsApp లొకేషన్ పిన్* (📎 → Location → Send your current location) షేర్ చేయండి లేదా మీ *గ్రామం / మండలం / జిల్లా పేరు* పంపండి."
    ),
    "ta-IN": (
        "📍 உங்கள் பகுதியின் துல்லியமான வானிலை, பயிர் நோய் மற்றும் APMC சந்தை விலை விவரங்களுக்கு தயவுசெய்து முதலில் உங்கள் *நேரலை WhatsApp இருப்பிடத்தை* (📎 → Location → Send your current location) பகிரவும் அல்லது உங்கள் *கிராமம் / தாலுகா / மாவட்டத்தின் பெயரை* அனுப்பவும்."
    ),
    "mr-IN": (
        "📍 तुमच्या भागातील अचूक हवामान, पीक रोग आणि APMC बाजार भावासाठी कृपया आधी तुमचे *लाइव्ह WhatsApp लोकेशन पिन* (📎 → Location → Send your current location) शेअर करा किंवा तुमच्या *गाव / तालुका / जिल्ह्याचे नाव* पाठवा."
    ),
    "ml-IN": (
        "📍 നിങ്ങളുടെ പ്രദേശത്തെ കൃത്യമായ കാലാവസ്ഥ, വിള രോഗങ്ങൾ, APMC മാർക്കറ്റ് വിലകൾ എന്നിവയ്ക്കായി ദയവായി ആദ്യം നിങ്ങളുടെ *ലൈവ് WhatsApp ലൊക്കേഷൻ പിൻ* (📎 → Location → Send your current location) പങ്കിടുക അല്ലെങ്കിൽ *ഗ്രാമം / താലൂക്ക് / ജില്ലയുടെ പേര്* അയയ്ക്കുക."
    ),
    "bn-IN": (
        "📍 আপনার এলাকার সঠিক আবহাওয়া, ফসলের রোগ এবং APMC মান্ডি দর জানতে অনুগ্রহ করে প্রথমে আপনার *লাইভ WhatsApp লোকেশন পিন* (📎 → Location → Send your current location) শেয়ার করুন অথবা আপনার *গ্রাম / ব্লক / জেলার নাম* লিখে পাঠান।"
    ),
    "gu-IN": (
        "📍 તમારા વિસ્તારના સચોટ હવામાન, પાકના રોગો અને APMC મંડીના ભાવ જાણવા માટે કૃપા કરીને પહેલા તમારો *લાઇવ WhatsApp લોકેશન પિન* (📎 → Location → Send your current location) શેર કરો અથવા તમારા *ગામ / તાલુકા / જિલ્લાનું નામ* લખીને મોકલો."
    ),
    "pa-IN": (
        "📍 ਆਪਣੇ ਇਲਾਕੇ ਦੇ ਸਹੀ ਮੌਸਮ, ਫ਼ਸਲਾਂ ਦੀਆਂ ਬਿਮਾਰੀਆਂ ਅਤੇ APMC ਮੰਡੀ ਭਾਅ ਜਾਣਨ ਲਈ ਕਿਰਪਾ ਕਰਕੇ ਪਹਿਲਾਂ ਆਪਣਾ *ਲਾਈਵ WhatsApp ਲੋਕੇਸ਼ਨ ਪਿੰਨ* (📎 → Location → Send your current location) ਸਾਂਝਾ ਕਰੋ ਜਾਂ ਆਪਣੇ *ਪਿੰਡ / ਤਹਿਸੀਲ / ਜ਼ਿਲ੍ਹੇ ਦਾ ਨਾਮ* ਲਿਖ ਕੇ ਭੇਜੋ।"
    ),
    "en-IN": (
        "📍 To give you accurate local weather, crop disease, soil, and nearby APMC mandi advice, please share your *live WhatsApp Location pin* (📎 → Location → Send your current location) or reply with your *village / taluk / district name* first."
    ),
}

LOCATION_SAVED_MESSAGES = {
    "kn-IN": "✅ ನಿಮ್ಮ ಲೊಕೇಶನ್ ಉಳಿಸಲಾಗಿದೆ: *{loc}* ({lat:.4f}, {lon:.4f}). ಇನ್ನು ಮುಂದೆ ನಿಮ್ಮ ಪ್ರದೇಶಕ್ಕೆ ತಕ್ಕಂತೆ ಹವಾಮಾನ, ಬೆಳೆ ರೋಗ ಮತ್ತು ಮಂಡಿ ಸಲಹೆಗಳನ್ನು ನೀಡಲಾಗುವುದು.",
    "hi-IN": "✅ आपकी लोकेशन सेव हो गई है: *{loc}* ({lat:.4f}, {lon:.4f})। अब आपको आपके क्षेत्र के अनुसार मौसम, फसल रोग और मंडी सलाह मिलेगी।",
    "te-IN": "✅ మీ లొకేషన్ సేవ్ చేయబడింది: *{loc}* ({lat:.4f}, {lon:.4f}). ఇకపై మీ ప్రాంతానికి తగిన వాతావరణం, పంట మరియు మండి సలహాలు అందుతాయి.",
    "ta-IN": "✅ உங்கள் இருப்பிடம் சேமிக்கப்பட்டது: *{loc}* ({lat:.4f}, {lon:.4f}). இனி உங்கள் பகுதிக்கேற்ற வானிலை, பயிர் மற்றும் சந்தை ஆலோசனைகள் வழங்கப்படும்.",
    "mr-IN": "✅ तुमचे लोकेशन सेव्ह केले आहे: *{loc}* ({lat:.4f}, {lon:.4f}). आता तुमच्या भागाप्रमाणे हवामान, पीक रोग आणि बाजार सल्ला दिला जाईल.",
    "ml-IN": "✅ നിങ്ങളുടെ ലൊക്കേഷൻ സേവ് ചെയ്തിട്ടുണ്ട്: *{loc}* ({lat:.4f}, {lon:.4f}). ഇനി നിങ്ങളുടെ പ്രദേശത്തിന് അനുയോജ്യമായ കാലാവസ്ഥ, വിള രോഗങ്ങൾ, മാർക്കറ്റ് ഉപദേശങ്ങൾ എന്നിവ ലഭിക്കും.",
    "bn-IN": "✅ আপনার লোকেশন সেভ করা হয়েছে: *{loc}* ({lat:.4f}, {lon:.4f})। এখন থেকে আপনার এলাকার আবহাওয়া, ফসলের রোগ ও মান্ডির পরামর্শ দেওয়া হবে।",
    "gu-IN": "✅ તમારું લોકેશન સેવ થઈ ગયું છે: *{loc}* ({lat:.4f}, {lon:.4f}). હવેથી તમારા વિસ્તાર મુજબ હવામાન, પાક રોગ અને મંડીની સલાહ મળશે.",
    "pa-IN": "✅ ਤੁਹਾਡੀ ਲੋਕੇਸ਼ਨ ਸੇਵ ਹੋ ਗਈ ਹੈ: *{loc}* ({lat:.4f}, {lon:.4f})। ਹੁਣ ਤੁਹਾਨੂੰ ਤੁਹਾਡੇ ਇਲਾਕੇ ਮੁਤਾਬਕ ਮੌਸਮ, ਫ਼ਸਲਾਂ ਅਤੇ ਮੰਡੀ ਦੀ ਸਲਾਹ ਮਿਲੇਗੀ।",
    "en-IN": "✅ Your location has been saved: *{loc}* ({lat:.4f}, {lon:.4f}). All future weather, crop disease, soil, and mandi advisories will be tailored to your area.",
}

VOICE_SUMMARY_HEADERS = {
    "kn-IN": ("🎙️ *ಕೃಷಿ ಮಿತ್ರ ಧ್ವನಿ ಸಲಹೆ*", "ಪ್ರಶ್ನೆ", "ಸಲಹೆ"),
    "hi-IN": ("🎙️ *कृषि मित्र वॉइस सलाह*", "प्रश्न", "सलाह"),
    "te-IN": ("🎙️ *కృషి మిత్ర వాయిస్ సలహా*", "ప్రశ్న", "సలహా"),
    "ta-IN": ("🎙️ *கிருஷி மித்ரா குரல் ஆலோசனை*", "கேள்வி", "ஆலோசனை"),
    "mr-IN": ("🎙️ *कृषी मित्र व्हॉइस सल्ला*", "प्रश्न", "सल्ला"),
    "ml-IN": ("🎙️ *കൃഷി മിത്ര വോയ്‌സ് ഉപദേശം*", "ചോദ്യം", "ഉപദേശം"),
    "bn-IN": ("🎙️ *কৃষি মিত্র ভয়েস পরামর্শ*", "প্রশ্ন", "পরামর্শ"),
    "gu-IN": ("🎙️ *કૃષિ મિત્ર વૉઇસ સલાહ*", "પ્રશ્ન", "સલાહ"),
    "pa-IN": ("🎙️ *ਕ੍ਰਿਸ਼ੀ ਮਿੱਤਰ ਵੌਇਸ ਸਲਾਹ*", "ਸਵਾਲ", "ਸਲਾਹ"),
    "en-IN": ("🎙️ *KrishiMitra Voice Advisory*", "Query", "Advisory"),
}

ERROR_MESSAGES = {
    "kn-IN": "⚠️ ಕ್ಷಮಿಸಿ, ಲೈವ್ AI ಸೇವೆಯಲ್ಲಿ ತಾತ್ಕಾಲಿಕ ದೋಷ ಉಂಟಾಗಿದೆ. ದಯವಿಟ್ಟು ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    "hi-IN": "⚠️ क्षमा करें, लाइव AI सेवा में अस्थायी त्रुटि हुई है। कृपया थोड़ी देर बाद फिर प्रयास करें।",
    "te-IN": "⚠️ క్షమించండి, లైవ్ AI సేవలో తాత్కాలిక లోపం ఏర్పడింది. దయచేసి కాసేపటి తర్వాత మళ్లీ ప్రయత్నించండి.",
    "ta-IN": "⚠️ மன்னிக்கவும், நேரலை AI சேவையில் தற்காலிக பிழை ஏற்பட்டுள்ளது. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.",
    "mr-IN": "⚠️ क्षमस्व, लाइव्ह AI सेवेमध्ये तात्पुरती तांत्रिक अडचण आली आहे. कृपया थोड्या वेळाने पुन्हा प्रयत्न करा.",
    "ml-IN": "⚠️ ക്ഷമിക്കണം, ലൈവ് AI സേവനത്തിൽ താൽക്കാലിക പിശക് ഉണ്ടായി. ദയവായി അല്പസമയത്തിന് ശേഷം വീണ്ടും ശ്രമിക്കുക.",
    "bn-IN": "⚠️ দুঃখিত, লাইভ AI পরিষেবায় সাময়িক ত্রুটি হয়েছে। অনুগ্রহ করে কিছুক্ষণ পরে আবার চেষ্টা করুন।",
    "gu-IN": "⚠️ માફ કરશો, લાઇવ AI સેવામાં અસ્થાયી ખામી આવી છે. કૃપા કરીને થોડી વાર પછી ફરી પ્રયાસ કરો.",
    "pa-IN": "⚠️ ਮਾਫ਼ ਕਰਨਾ, ਲਾਈਵ AI ਸੇਵਾ ਵਿੱਚ ਅਸਥਾਈ ਤਕਨੀਕੀ ਖਰਾਬੀ ਆਈ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਥੋੜ੍ਹੀ ਦੇਰ ਬਾਅਦ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
    "en-IN": "⚠️ Sorry, the live AI advisory service encountered an error. Please try again in a moment.",
}

RESEND_MEDIA_MESSAGES = {
    "kn-IN": "📷/🎤 ಕ್ಷಮಿಸಿ, ನಿಮ್ಮ ಫೋಟೋ ಅಥವಾ ಧ್ವನಿ ಸಂದೇಶವನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಓದಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಸ್ಪಷ್ಟವಾಗಿ ಮತ್ತೆ ಕಳುಹಿಸಿ.",
    "hi-IN": "📷/🎤 क्षमा करें, आपका फोटो या वॉइस संदेश प्राप्त नहीं हो सका। कृपया फिर से स्पष्ट भेजें।",
    "te-IN": "📷/🎤 క్షమించండి, మీ ఫోటో లేదా వాయిస్ సందేశం అందలేదు. దయచేసి మళ్లీ స్పష్టంగా పంపండి.",
    "ta-IN": "📷/🎤 மன்னிக்கவும், உங்கள் புகைப்படம் அல்லது குரல் செய்தியைப் பெற முடியவில்லை. தயவுசெய்து மீண்டும் அனுப்பவும்.",
    "mr-IN": "📷/🎤 क्षमस्व, तुमचा फोटो किंवा व्हॉइस संदेश मिळू शकला नाही. कृपया पुन्हा स्पष्ट पाठवा.",
    "ml-IN": "📷/🎤 ക്ഷമിക്കണം, നിങ്ങളുടെ ഫോട്ടോയോ വോയ്‌സ് സന്ദേശമോ വായിക്കാൻ കഴിഞ്ഞില്ല. ദയവായി വ്യക്തമായി വീണ്ടും അയയ്ക്കുക.",
    "bn-IN": "📷/🎤 দুঃখিত, আপনার ছবি বা ভয়েস মেসেজটি স্পষ্টভাবে পড়া যায়নি। অনুগ্রহ করে আবার স্পষ্টভাবে পাঠান।",
    "gu-IN": "📷/🎤 માફ કરશો, તમારો ફોટો અથવા વૉઇસ મેસેજ સ્પષ્ટ રીતે વાંચી શકાયો નથી. કૃપા કરીને ફરીથી સ્પષ્ટ મોકલો.",
    "pa-IN": "📷/🎤 ਮਾਫ਼ ਕਰਨਾ, ਤੁਹਾਡੀ ਫੋਟੋ ਜਾਂ ਵੌਇਸ ਸੁਨੇਹਾ ਸਪਸ਼ਟ ਨਹੀਂ ਪੜ੍ਹਿਆ ਜਾ ਸਕਿਆ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਸਪਸ਼ਟ ਭੇਜੋ।",
    "en-IN": "📷/🎤 Sorry, we could not download or read your media file. Please resend a clear photo or voice note.",
}


class WhatsAppSimulateRequest(BaseModel):
    type: str = Field(default="text", description="Message type: text, audio, image, or location")
    text: Optional[str] = Field(default=None, description="User query text")
    query: Optional[str] = Field(default=None, description="Alias for text")
    from_number: Optional[str] = Field(default="919876543210", alias="from", description="Sender WhatsApp phone number")
    caption: Optional[str] = Field(default=None, description="Image caption or specific question")
    audio_base64: Optional[str] = Field(default=None, description="Base64 encoded audio bytes")
    image_base64: Optional[str] = Field(default=None, description="Base64 encoded image bytes")
    latitude: Optional[float] = Field(default=None, description="Latitude for simulated location message")
    longitude: Optional[float] = Field(default=None, description="Longitude for simulated location message")
    location_name: Optional[str] = Field(default=None, description="Optional location label")
    entry: Optional[List[Dict[str, Any]]] = Field(default=None, description="Standard Meta Graph API webhook entry payload")

    class Config:
        populate_by_name = True
        extra = "allow"


def is_location_dependent_query(text: str) -> bool:
    """Return True if the query depends on local weather, crop disease, mandi rate, or soil."""
    if not text:
        return False
    low = text.lower()
    return any(kw in low for kw in LOCATION_DEPENDENT_KEYWORDS)


async def _try_resolve_place_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to interpret a user message as a village/taluk/district location reply
    when the user has no saved location yet.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    # Strip common conversational prefixes
    prefixes = [
        r"^(my\s+(village|town|city|taluk|district|location|place)\s*(is|:)?\s*)",
        r"^(i\s+(am\s+from|live\s+in|stay\s+in)\s+)",
        r"^(location\s*:\s*)",
        r"^(from\s+)",
        r"^(ನನ್ನ\s*(ಊರು|ಜಿಲ್ಲೆ|ತಾಲ್ಲೂಕು)\s*)",
        r"^(मेरा\s*(गांव|जिला|शहर)\s*)",
    ]
    candidate = cleaned
    for pat in prefixes:
        candidate = re.sub(pat, "", candidate, flags=re.IGNORECASE).strip()

    # Do not treat multi-word farm questions as place names
    if "?" in candidate or len(candidate.split()) > 5:
        return None
    if any(kw in candidate.lower() for kw in LOCATION_DEPENDENT_KEYWORDS):
        return None

    return await location_service.geocode_place_nominatim(candidate)


def format_scan_result_for_whatsapp(scan_data: Dict[str, Any], language: str = "en-IN") -> str:
    """
    Format live Gemini Vision output into clean WhatsApp text in the farmer's native language.
    Never injects hardcoded/fake dosages.
    """
    result = scan_data.get("result", {})

    # 1. Blurry / unreadable check
    if result.get("is_blurry_or_unreadable") or scan_data.get("mode") == "blurry":
        retake_msg = result.get("retake_photo_message") or result.get("formatted_whatsapp_reply")
        if retake_msg:
            return retake_msg

    # 2. Prefer Gemini's native-language formatted_whatsapp_reply when rich & present
    formatted = (result.get("formatted_whatsapp_reply") or "").strip()
    if formatted:
        return formatted

    # 3. Fallback structural formatting purely from Gemini's JSON output
    mode = scan_data.get("mode", "crop")
    lines = []
    if result.get("direct_answer_to_question"):
        lines.append(f"💬 {result['direct_answer_to_question']}\n")

    if mode == "disease":
        lines.append("🌿 *KrishiMitra Crop Diagnosis*")
        if result.get("detected_crop"):
            lines.append(f"• *Crop:* {result['detected_crop']}")
        if result.get("disease_name"):
            lines.append(f"• *Disease/Pest:* {result['disease_name']}")
        if result.get("severity"):
            lines.append(f"• *Severity:* {result['severity']}")
        if result.get("symptoms"):
            lines.append(f"\n🔍 *Symptoms:* {result['symptoms']}")
        if result.get("cause"):
            lines.append(f"\n🌦️ *Cause (Weather-Linked):* {result['cause']}")
        if result.get("organic_treatments"):
            lines.append("\n🌱 *Organic Treatment:*")
            for o in result["organic_treatments"]:
                lines.append(f"  - {o}")
        if result.get("chemical_treatments"):
            lines.append("\n🧪 *Chemical Treatment & Dosage:*")
            for c in result["chemical_treatments"]:
                lines.append(f"  - {c}")
        if result.get("spray_frequency"):
            lines.append(f"\n⏱️ *Spray Frequency:* {result['spray_frequency']}")

    elif mode == "agrochemical":
        lines.append("🧪 *KrishiMitra Agrochemical Guide*")
        if result.get("product_name"):
            lines.append(f"• *Product:* {result['product_name']}")
        if result.get("active_ingredient"):
            lines.append(f"• *Active Ingredient / NPK:* {result['active_ingredient']}")
        if result.get("purpose"):
            lines.append(f"\n🎯 *Uses:* {result['purpose']}")
        dosage = result.get("dosage")
        if isinstance(dosage, dict) and any(dosage.values()):
            lines.append("\n💧 *Dosage & Using Method:*")
            if dosage.get("per_litre"):
                lines.append(f"  - Per Litre: {dosage['per_litre']}")
            if dosage.get("per_knapsack_15L"):
                lines.append(f"  - Per 15L Knapsack: {dosage['per_knapsack_15L']}")
            if dosage.get("per_barrel_200L"):
                lines.append(f"  - Per 200L Barrel: {dosage['per_barrel_200L']}")
            if dosage.get("per_acre"):
                lines.append(f"  - Per Acre: {dosage['per_acre']}")
        if result.get("using_method") or result.get("application_method"):
            lines.append(f"• *Method:* {result.get('using_method') or result.get('application_method')}")
        if result.get("safety_cautions"):
            lines.append("\n⚠️ *Safety Cautions:*")
            for s in result["safety_cautions"]:
                lines.append(f"  - {s}")

    elif mode == "soil":
        lines.append("⛰️ *KrishiMitra Soil Analysis*")
        if result.get("soil_type"):
            lines.append(f"• *Soil Type:* {result['soil_type']}")
        if result.get("ranked_suitable_crops"):
            lines.append("\n🌾 *Suitable Crops:*")
            for c in result["ranked_suitable_crops"][:5]:
                if isinstance(c, dict):
                    lines.append(f"  - *{c.get('crop', '')}:* {c.get('reason', '')}")
        if result.get("amendments_recommended"):
            lines.append("\n🧪 *Amendments:*")
            for a in result["amendments_recommended"][:4]:
                lines.append(f"  - {a}")

    else:
        lines.append(f"🌱 *KrishiMitra Crop Guide: {result.get('detected_crop', '')}*")
        for step in (result.get("cultivation_steps") or [])[:5]:
            lines.append(f"  - {step}")

    return "\n".join(lines).strip() or ERROR_MESSAGES.get(language, ERROR_MESSAGES["en-IN"])


def convert_audio_to_ogg_opus(input_audio_bytes: bytes) -> bytes:
    """
    Convert audio bytes (WAV/MP3/WebM) to mono audio/ogg (Opus codec, 24k bitrate, <= 512 KB)
    so WhatsApp renders the native inline voice-note player bubble.
    """
    if not input_audio_bytes:
        return b""

    if input_audio_bytes.startswith(b"OggS") and len(input_audio_bytes) <= 512 * 1024:
        return input_audio_bytes

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        logger.warning("[Audio Converter] ffmpeg not found in PATH; falling back to raw audio bytes")
        return input_audio_bytes

    input_file = None
    output_file = None
    t0 = time.perf_counter()
    try:
        suffix = ".wav"
        if input_audio_bytes.startswith(b"\xff\xfb") or input_audio_bytes.startswith(b"ID3"):
            suffix = ".mp3"
        elif input_audio_bytes.startswith(b"\x1aE\xdf\xa3"):
            suffix = ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as in_f:
            in_f.write(input_audio_bytes)
            input_file = in_f.name

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as out_f:
            output_file = out_f.name

        cmd = [
            ffmpeg_path, "-y", "-i", input_file,
            "-c:a", "libopus", "-ac", "1", "-b:a", "24k",
            output_file,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=6)
        elapsed = time.perf_counter() - t0
        if res.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as f:
                converted_bytes = f.read()
            logger.info("[Audio Converter] ffmpeg converted %d -> %d bytes in %.2fs", len(input_audio_bytes), len(converted_bytes), elapsed)
            return converted_bytes
        logger.warning("[Audio Converter] ffmpeg conversion failed (code %s in %.2fs)", res.returncode, elapsed)
    except Exception as e:
        logger.error("[Audio Converter] Exception during ffmpeg conversion: %s", e)
    finally:
        for fpath in [input_file, output_file]:
            if fpath and os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    return input_audio_bytes


async def mark_whatsapp_message_read(message_id: str) -> Optional[Dict[str, Any]]:
    """Send read receipt to Meta WhatsApp Cloud API."""
    if not config.has_whatsapp():
        return {"status": "simulated", "message_id": message_id, "read": True}

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"messaging_product": "whatsapp", "status": "read", "message_id": message_id}
    try:
        timeout = httpx.Timeout(connect=2.5, read=5.0, write=5.0, pool=6.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("[WhatsApp] Failed sending read receipt for %s: %s", message_id, exc)
        return None


async def upload_whatsapp_media(audio_bytes: bytes, mime_type: str = "audio/mpeg") -> Optional[str]:
    """Upload media binary to Meta WhatsApp Cloud API."""
    byte_len = len(audio_bytes) if audio_bytes else 0
    if not config.has_whatsapp() or not audio_bytes:
        logger.warning(
            "[WhatsApp Media Upload] Skipped upload (has_whatsapp=%s, byte_len=%d, mime_type=%s)",
            config.has_whatsapp(), byte_len, mime_type,
        )
        print(
            f"[WhatsApp Media Upload SKIP] has_whatsapp={config.has_whatsapp()} | byte_len={byte_len} | mime_type={mime_type}",
            flush=True,
        )
        return None
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{config.WHATSAPP_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}"}
    filename = "reply.mp3" if mime_type == "audio/mpeg" else "voice_reply.ogg"
    files = {"file": (filename, audio_bytes, mime_type)}
    data = {"messaging_product": "whatsapp", "type": mime_type}
    timeout = httpx.Timeout(connect=3.0, read=12.0, write=12.0, pool=15.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            resp_text = resp.text[:300]
            logger.info("[WhatsApp Media Upload] HTTP %s | byte_len=%d | body=%s", resp.status_code, byte_len, resp_text)
            print(
                f"[WhatsApp Media Upload] HTTP {resp.status_code} | byte_len={byte_len} | mime_type={mime_type} | body={resp_text}",
                flush=True,
            )
            resp.raise_for_status()
            resp_json = resp.json()
            media_id = resp_json.get("id")
            if not media_id:
                logger.warning("[WhatsApp Media Upload] Missing media_id in response (byte_len=%d): %s", byte_len, resp_text)
                print(
                    f"[WhatsApp Media Upload ERROR] Missing media_id | byte_len={byte_len} | status={resp.status_code} | body={resp_text}",
                    flush=True,
                )
            return media_id if media_id else None
    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", "N/A")
        resp_body = getattr(getattr(exc, "response", None), "text", "N/A")
        logger.error(
            "[WhatsApp Media Upload ERROR] byte_len=%d | mime_type=%s | status=%s | body=%s | exc=%s",
            byte_len, mime_type, status_code, resp_body, exc, exc_info=True,
        )
        print(
            f"[WhatsApp Media Upload ERROR] byte_len={byte_len} | mime_type={mime_type} | status={status_code} | body={resp_body} | exc={type(exc).__name__}: {exc}",
            flush=True,
        )
        return None


async def send_whatsapp_audio(recipient_phone: str, media_id: str) -> Dict[str, Any]:
    """Send audio message to recipient via Meta WhatsApp Cloud API."""
    if not config.has_whatsapp():
        return {"status": "simulated", "recipient": recipient_phone, "audio_media_id": media_id}

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone,
        "type": "audio",
        "audio": {"id": media_id},
    }
    try:
        timeout = httpx.Timeout(connect=2.5, read=7.0, write=7.0, pool=8.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp_text = resp.text[:300]
            logger.info("[WhatsApp Audio Send] HTTP %s | media_id=%s | body=%s", resp.status_code, media_id, resp_text)
            print(
                f"[WhatsApp Audio Send] HTTP {resp.status_code} | media_id={media_id} | to={recipient_phone} | body={resp_text}",
                flush=True,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", "N/A")
        resp_body = getattr(getattr(exc, "response", None), "text", "N/A")
        logger.error(
            "[WhatsApp Audio Send ERROR] recipient=%s | media_id=%s | status=%s | body=%s | exc=%s",
            recipient_phone, media_id, status_code, resp_body, exc, exc_info=True,
        )
        print(
            f"[WhatsApp Audio Send ERROR] recipient={recipient_phone} | media_id={media_id} | status={status_code} | body={resp_body} | exc={type(exc).__name__}: {exc}",
            flush=True,
        )
        return {"sent": False, "media_id": media_id, "status": status_code, "error": str(exc)}


async def send_whatsapp_text(recipient_phone: str, text: str) -> Dict[str, Any]:
    """Send text message to recipient via Meta WhatsApp Cloud API."""
    if not config.has_whatsapp():
        return {"status": "simulated", "recipient": recipient_phone, "message": text}

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "text",
        "text": {"body": text},
    }
    try:
        timeout = httpx.Timeout(connect=2.5, read=7.0, write=7.0, pool=8.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("[WhatsApp] Failed sending text message to %s: %s", recipient_phone, exc)
        return {"sent": False, "error": str(exc)}


MIME_TO_EXT = {
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/amr": ".amr",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}

GREETING_TRIGGERS = {"hi", "hello", "namaskara", "namaste", "start", "hey", "ನಮಸ್ಕಾರ", "नमस्ते"}

STATE_TO_LANGUAGE = {
    "karnataka": "kn-IN",
    "maharashtra": "mr-IN",
    "goa": "mr-IN",
    "andhra pradesh": "te-IN",
    "telangana": "te-IN",
    "tamil nadu": "ta-IN",
    "puducherry": "ta-IN",
    "uttar pradesh": "hi-IN",
    "madhya pradesh": "hi-IN",
    "rajasthan": "hi-IN",
    "bihar": "hi-IN",
    "haryana": "hi-IN",
    "chhattisgarh": "hi-IN",
    "jharkhand": "hi-IN",
    "uttarakhand": "hi-IN",
    "himachal pradesh": "hi-IN",
    "delhi": "hi-IN",
    "kerala": "ml-IN",
    "lakshadweep": "ml-IN",
}

NATIVE_ONBOARDING_PROMPTS = {
    "kn-IN": (
        "ನಿಮ್ಮ ಸ್ಥಳ {district}, {state} ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ. "
        "ನಿಮ್ಮ ಭಾಷೆ ಕನ್ನಡವಾಗಿದ್ದರೆ ಕೆಳಗಿನ ಬಟನ್ ಒತ್ತಿ ಮತ್ತು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಕೇಳಿ. "
        "ನಿಮ್ಮ ಭಾಷೆ ಕನ್ನಡವಲ್ಲದಿದ್ದರೆ, ಧ್ವನಿ ಸಂದೇಶದ ಮೂಲಕ ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ತಿಳಿಸಿ."
    ),
    "mr-IN": (
        "तुमचे ठिकाण {district}, {state} म्हणून ओळखले गेले आहे. "
        "तुमची भाषा मराठी असल्यास खालील बटण दाबा आणि तुमचा प्रश्न विचारा. "
        "जर तुमची भाषा मराठी नसेल, तर व्हॉइस मेसेजद्वारे तुमची भाषा सांगा."
    ),
    "te-IN": (
        "మీ స్థానం {district}, {state} గా గుర్తించబడింది. "
        "మీ భాష తెలుగు అయితే కింది బటన్ నొక్కి మీ ప్రశ్న అడగండి. "
        "మీ భాష తెలుగు కాకపోతే, వాయిస్ మెసేజ్ ద్వారా మీ భాషను తెలియజేయండి."
    ),
    "ta-IN": (
        "உங்கள் இடம் {district}, {state} என கண்டறியப்பட்டது. "
        "உங்கள் மொழி தமிழ் என்றால் கீழே உள்ள பொத்தானை அழுத்தி உங்கள் கேள்வியைக் கேளுங்கள். "
        "உங்கள் மொழி தமிழ் இல்லையென்றால், குரல் செய்தி மூலம் உங்கள் மொழியைத் தெரிவிக்கவும்."
    ),
    "hi-IN": (
        "आपका स्थान {district}, {state} के रूप में पहचाना गया है। "
        "यदि आपकी भाषा हिंदी है तो नीचे दिया गया बटन दबाएं और अपना प्रश्न पूछें। "
        "यदि आपकी भाषा हिंदी नहीं है, तो वॉइस मैसेज द्वारा अपनी भाषा बताएं।"
    ),
    "ml-IN": (
        "നിങ്ങളുടെ സ്ഥലം {district}, {state} ആയി കണ്ടെത്തിയിട്ടുണ്ട്. "
        "നിങ്ങളുടെ ഭാഷ മലയാളം ആണെങ്കിൽ താഴെയുള്ള ബട്ടൺ അമർത്തി ചോദ്യം ചോദിക്കുക. "
        "നിങ്ങളുടെ ഭാഷ മലയാളം അല്ലെങ്കിൽ, വോയ്‌സ് മെസ്സേജിലൂടെ നിങ്ങളുടെ ഭാഷ അറിയിക്കുക."
    ),
    "en-IN": (
        "Your location has been detected as {district}, {state}. "
        "If your preferred language is English, tap the button below and ask your question. "
        "Otherwise, tap Other Language and tell me your preferred language."
    ),
}

NATIVE_LANGUAGE_BUTTONS = {
    "kn-IN": ("ಹೌದು, ಕನ್ನಡ", "ಬೇರೆ ಭಾಷೆ"),
    "mr-IN": ("होय, मराठी", "इतर भाषा"),
    "te-IN": ("అవును, తెలుగు", "ఇతర భాష"),
    "ta-IN": ("ஆம், தமிழ்", "வேறு மொழி"),
    "hi-IN": ("हाँ, हिंदी", "अन्य भाषा"),
    "ml-IN": ("അതെ, മലയാളം", "മറ്റൊരു ഭാഷ"),
    "en-IN": ("Yes, English", "Other Language"),
}

LANGUAGE_CONFIRMED_MESSAGES = {
    "kn-IN": "✅ ನಿಮ್ಮ ಭಾಷೆ (ಕನ್ನಡ) ಮತ್ತು ಸ್ಥಳವನ್ನು ಉಳಿಸಲಾಗಿದೆ. ಈಗ ನೀವು ಧ್ವನಿ ಸಂದೇಶ ಅಥವಾ ಬೆಳೆ/ಕೀಟನಾಶಕ ಫೋಟೋ ಕಳುಹಿಸಿ ಪ್ರಶ್ನೆ ಕೇಳಬಹುದು.",
    "mr-IN": "✅ तुमची भाषा (मराठी) आणि ठिकाण सेव्ह केले आहे. आता तुम्ही व्हॉइस मेसेज किंवा पिकाचा/औषधाचा फोटो पाठवून प्रश्न विचारू शकता.",
    "te-IN": "✅ మీ భాష (తెలుగు) మరియు స్థానం సేవ్ చేయబడ్డాయి. ఇప్పుడు మీరు వాయిస్ మెసేజ్ లేదా పంట/పురుగుమందు ఫోటో పంపి ప్రశ్న అడగవచ్చు.",
    "ta-IN": "✅ உங்கள் மொழி (தமிழ்) மற்றும் இடம் சேமிக்கப்பட்டது. இப்போது நீங்கள் குரல் செய்தி அல்லது பயிர்/மருந்து புகைப்படம் அனுப்பி கேள்வி கேட்கலாம்.",
    "hi-IN": "✅ आपकी भाषा (हिंदी) और स्थान सेव हो गया है। अब आप कोई भी वॉइस सवाल या फसल/कीटनाशक की फोटो भेज सकते हैं।",
    "ml-IN": "✅ നിങ്ങളുടെ ഭാഷയും (മലയാളം) സ്ഥലവും സേവ് ചെയ്തിട്ടുണ്ട്. ഇപ്പോൾ നിങ്ങൾക്ക് ശബ്ദ സന്ദേശമോ വിളയുടെ/കീടനാശിനിയുടെ ഫോട്ടോയോ അയച്ച് ചോദ്യങ്ങൾ ചോദിക്കാം.",
    "en-IN": "✅ Your language (English) and location are set! You can now send any voice question or crop/pesticide photo.",
}

ASK_OTHER_LANGUAGE_MESSAGE = (
    "🗣️ Please speak or type your preferred language: Kannada, Hindi, Telugu, Tamil, Marathi, Malayalam, or English."
)


async def download_whatsapp_media(media_id: str) -> Tuple[bytes, str, str]:
    """
    Download media binary using Meta WhatsApp Graph API:
    1. GET https://graph.facebook.com/{WHATSAPP_API_VERSION}/{media_id} with Authorization: Bearer
       to retrieve fresh "url" and "mime_type".
    2. Download from "url" using httpx.AsyncClient(follow_redirects=True) with BOTH
       Authorization: Bearer and User-Agent: Mozilla/5.0 headers.
    3. Normalize mime_type = raw_mime.split(";")[0].strip(). Ensure len(media_bytes) > 100.
    Logs exact failure stage, HTTP status, and response details.
    """
    if not config.WHATSAPP_ACCESS_TOKEN:
        print(f"[WhatsApp Media Download FAIL] No WHATSAPP_ACCESS_TOKEN configured for media_id={media_id}", flush=True)
        return b"", "", ""

    meta_headers = {"Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}"}
    download_headers = {
        "Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    timeout = httpx.Timeout(connect=5.0, read=25.0, write=10.0, pool=15.0)

    # Stage 1: Metadata Lookup
    download_url = None
    raw_mime = "application/octet-stream"
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            meta_url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{media_id}"
            meta_resp = await client.get(meta_url, headers=meta_headers)
            print(
                f"[WhatsApp Media Stage 1: Metadata] media_id={media_id} | HTTP {meta_resp.status_code} | body={meta_resp.text[:300]}",
                flush=True,
            )
            logger.info("[WhatsApp Media] Metadata HTTP %s for %s: %s", meta_resp.status_code, media_id, meta_resp.text[:200])
            meta_resp.raise_for_status()
            meta_json = meta_resp.json()
            download_url = meta_json.get("url")
            raw_mime = meta_json.get("mime_type", "application/octet-stream")
            if not download_url:
                raise ValueError(f"No download URL returned in metadata for media ID {media_id}")
    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", "N/A")
        resp_body = getattr(getattr(exc, "response", None), "text", "N/A")
        logger.error(
            "[WhatsApp Media Download ERROR - Metadata Stage] media_id=%s, status=%s, body=%s, exc=%s",
            media_id, status_code, resp_body, exc, exc_info=True,
        )
        print(
            f"[WhatsApp Media Download ERROR - Metadata Stage] media_id={media_id} | status={status_code} | body={resp_body} | exc={type(exc).__name__}: {exc}",
            flush=True,
        )
        return b"", "", ""

    # Normalize mime_type
    mime_type = raw_mime.split(";")[0].strip().lower()
    ext = MIME_TO_EXT.get(mime_type, "")

    # Stage 2: Binary Media Download
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            media_resp = await client.get(download_url, headers=download_headers)
            byte_len = len(media_resp.content) if media_resp.content else 0
            print(
                f"[WhatsApp Media Stage 2: Binary] media_id={media_id} | HTTP {media_resp.status_code} | mime_type={mime_type} | byte_length={byte_len}",
                flush=True,
            )
            logger.info(
                "[WhatsApp Media] Binary HTTP %s, %d bytes, mime=%s (%s)",
                media_resp.status_code, byte_len, mime_type, ext or "no-ext",
            )
            media_resp.raise_for_status()
            content = media_resp.content

            if len(content) <= 100:
                err_msg = f"Downloaded media bytes too small ({len(content)} bytes <= 100) for media_id={media_id}"
                logger.error("[WhatsApp Media Download ERROR] %s", err_msg)
                print(f"[WhatsApp Media Download ERROR] {err_msg} | content_sample={content[:100]!r}", flush=True)
                return b"", "", ""

            return content, mime_type, ext
    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", "N/A")
        resp_body = getattr(getattr(exc, "response", None), "text", "N/A")
        logger.error(
            "[WhatsApp Media Download ERROR - Binary Stage] media_id=%s, mime_type=%s, status=%s, body=%s, exc=%s",
            media_id, mime_type, status_code, resp_body, exc, exc_info=True,
        )
        print(
            f"[WhatsApp Media Download ERROR - Binary Stage] media_id={media_id} | mime_type={mime_type} | status={status_code} | body={resp_body} | exc={type(exc).__name__}: {exc}",
            flush=True,
        )
        return b"", "", ""


async def _deliver_text(from_number: str, text: str, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"status": "dry_run", "sent": False, "recipient": from_number, "message": text}
    return await send_whatsapp_text(recipient_phone=from_number, text=text)


def _clean_tts_text(text: str) -> str:
    """Strip Markdown symbols (*, #, _, `) and collapse extra whitespace so edge-tts reads cleanly."""
    cleaned = re.sub(r"[*_`#]", "", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


async def send_whatsapp_interactive(recipient_phone: str, interactive_payload: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Send a WhatsApp Interactive message (location_request_message or button)."""
    if dry_run or not config.has_whatsapp():
        return {"status": "simulated", "recipient": recipient_phone, "interactive": interactive_payload}

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone,
        "type": "interactive",
        "interactive": interactive_payload,
    }
    try:
        timeout = httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=12.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("[WhatsApp] Failed sending interactive message to %s: %s", recipient_phone, exc)
        return {"sent": False, "error": str(exc)}


async def send_whatsapp_location_request(recipient_phone: str, dry_run: bool = False) -> Dict[str, Any]:
    """Send Step 1 WhatsApp Interactive Location Request button."""
    interactive = {
        "type": "location_request_message",
        "body": {
            "text": "📍 Tap 'Send Location' below so I can check your local weather, mandi rates, and language."
        },
        "action": {"name": "send_location"},
    }
    return await send_whatsapp_interactive(recipient_phone, interactive, dry_run=dry_run)


async def send_whatsapp_language_buttons(
    recipient_phone: str, language_code: str, district: str, state: str, dry_run: bool = False
) -> Dict[str, Any]:
    """Send Step 2 Interactive Reply Buttons in the state's native language (titles <= 20 chars)."""
    yes_title, other_title = NATIVE_LANGUAGE_BUTTONS.get(language_code, NATIVE_LANGUAGE_BUTTONS["en-IN"])
    body_template = NATIVE_ONBOARDING_PROMPTS.get(language_code, NATIVE_ONBOARDING_PROMPTS["en-IN"])
    body_text = body_template.format(district=district or "your area", state=state or "India")
    interactive = {
        "type": "button",
        "body": {"text": body_text},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": "lang_confirm_native", "title": yes_title[:20]}},
                {"type": "reply", "reply": {"id": "lang_other_voice", "title": other_title[:20]}},
            ]
        },
    }
    return await send_whatsapp_interactive(recipient_phone, interactive, dry_run=dry_run)


def _is_valid_mp3(mp3_bytes: bytes) -> bool:
    """Validate that MP3 bytes are non-empty (>500B) and start with a valid MP3 frame sync or ID3 header."""
    if not mp3_bytes or len(mp3_bytes) <= 500:
        return False
    return mp3_bytes.startswith((b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"ID3"))


async def _send_voice_note_text(
    recipient_phone: str, text: str, language_code: str, dry_run: bool = False
) -> Optional[str]:
    """Synthesize plain text via free edge-tts (MP3) and send as WhatsApp audio message."""
    target_lang = language_code or "kn-IN"
    clean_text = _clean_tts_text(text)
    if len(clean_text) > 450:
        truncated = clean_text[:450]
        clean_text = truncated.rsplit(" ", 1)[0].strip() if " " in truncated else truncated
    if not clean_text:
        print(f"[WhatsApp TTS SKIP] Empty text after stripping markdown (lang={target_lang})", flush=True)
        return None

    mp3_bytes = b""
    audio_b64: Optional[str] = None
    try:
        audio_b64 = await voice.synthesize_speech(clean_text, language_code=target_lang)
        if not audio_b64:
            logger.warning("[WhatsApp TTS] edge-tts returned empty audio (lang=%s, chars=%d)", target_lang, len(clean_text))
            print(f"[WhatsApp TTS ERROR] edge-tts returned empty audio | lang={target_lang} | chars={len(clean_text)}", flush=True)
            return None
        mp3_bytes = base64.b64decode(audio_b64)
        byte_len = len(mp3_bytes)
        if not _is_valid_mp3(mp3_bytes):
            logger.warning("[WhatsApp TTS] Invalid or empty MP3 bytes (byte_len=%d, lang=%s); skipping audio send", byte_len, target_lang)
            print(f"[WhatsApp TTS ERROR] Invalid MP3 bytes | byte_len={byte_len} | lang={target_lang}", flush=True)
            return None
        print(f"[WhatsApp TTS] Synthesized MP3 | lang={target_lang} | chars={len(clean_text)} | byte_len={byte_len}", flush=True)
    except Exception as tts_exc:
        logger.error("[WhatsApp TTS ERROR] edge-tts synthesis failed (lang=%s): %s", target_lang, tts_exc, exc_info=True)
        print(
            f"[WhatsApp TTS ERROR] edge-tts synthesis failed | lang={target_lang} | byte_len={len(mp3_bytes)} | exc={type(tts_exc).__name__}: {tts_exc}",
            flush=True,
        )
        return None

    if not dry_run and config.has_whatsapp():
        byte_len = len(mp3_bytes)
        up_id: Optional[str] = None
        try:
            up_id = await upload_whatsapp_media(mp3_bytes, mime_type="audio/mpeg")
            if not up_id:
                logger.error("[WhatsApp TTS Media Upload ERROR] media_id=None | byte_len=%d | lang=%s", byte_len, target_lang)
                print(f"[WhatsApp TTS Media Upload ERROR] media_id=None | byte_len={byte_len} | lang={target_lang}", flush=True)
                return audio_b64
        except Exception as up_exc:
            status_code = getattr(getattr(up_exc, "response", None), "status_code", "N/A")
            logger.error("[WhatsApp TTS Media Upload ERROR] byte_len=%d | status=%s | exc=%s", byte_len, status_code, up_exc, exc_info=True)
            print(
                f"[WhatsApp TTS Media Upload ERROR] byte_len={byte_len} | media_id={up_id} | status={status_code} | exc={type(up_exc).__name__}: {up_exc}",
                flush=True,
            )
            return audio_b64

        try:
            send_res = await send_whatsapp_audio(recipient_phone, up_id)
            if isinstance(send_res, dict) and send_res.get("sent") is False:
                logger.error("[WhatsApp TTS Audio Send ERROR] media_id=%s | byte_len=%d | res=%s", up_id, byte_len, send_res)
                print(
                    f"[WhatsApp TTS Audio Send ERROR] media_id={up_id} | byte_len={byte_len} | status={send_res.get('status', 'N/A')} | error={send_res.get('error')}",
                    flush=True,
                )
        except Exception as send_exc:
            status_code = getattr(getattr(send_exc, "response", None), "status_code", "N/A")
            logger.error("[WhatsApp TTS Audio Send ERROR] media_id=%s | byte_len=%d | status=%s | exc=%s", up_id, byte_len, status_code, send_exc, exc_info=True)
            print(
                f"[WhatsApp TTS Audio Send ERROR] media_id={up_id} | byte_len={byte_len} | status={status_code} | exc={type(send_exc).__name__}: {send_exc}",
                flush=True,
            )

    return audio_b64


async def _reverse_geocode_nominatim(lat: float, lon: float) -> Tuple[str, str]:
    """Reverse-geocode lat/lon via OpenStreetMap Nominatim to extract (district, state)."""
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10"
    headers = {"User-Agent": "FarmAdvisorBot/1.0"}
    try:
        timeout = httpx.Timeout(connect=3.0, read=8.0, write=5.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            addr = resp.json().get("address", {})
            district = (
                addr.get("state_district")
                or addr.get("county")
                or addr.get("city")
                or addr.get("town")
                or addr.get("village")
                or "Your Area"
            )
            state = addr.get("state") or "India"
            return district, state
    except Exception as exc:
        logger.warning("[Nominatim] Reverse geocode failed: %s", exc)
        return "Your Area", "India"


def _map_state_to_language(state: str) -> str:
    """Map Indian state name to its native Sarvam/WhatsApp language code."""
    if not state:
        return "en-IN"
    return STATE_TO_LANGUAGE.get(state.strip().lower(), "en-IN")


LANGUAGE_MATCH_RULES: List[Tuple[str, Tuple[str, ...], Tuple[str, ...]]] = [
    (
        "hi-IN",
        ("hi", "hi-in"),
        (
            "hindi", "hindhi", "hindustani",
            "हिंदी", "हिन्दी", "हिनदी",
            "ಹಿಂದಿ", "హిందీ", "హింది", "ஹிந்தி", "இந்தி", "ഹിന്ദി",
        ),
    ),
    (
        "te-IN",
        ("te", "te-in"),
        (
            "telugu", "telgu", "thelegu", "telegu", "telagu",
            "తెలుగు", "तेलुगु", "तेलुगू", "ತೆಲುಗು", "தெலுங்கு", "തെലുങ്ക്", "തെലുഗു",
        ),
    ),
    (
        "ta-IN",
        ("ta", "ta-in"),
        (
            "tamil", "tamizh", "thamil", "thamizh",
            "தமிழ்", "तमिल", "तमिळ", "ತಮಿಳು", "తమిళం", "తమిళ్", "തമിഴ്",
        ),
    ),
    (
        "mr-IN",
        ("mr", "mr-in"),
        (
            "marathi", "marati", "maraathi", "marathee",
            "मराठी", "ಮರಾಠಿ", "మరాఠీ", "మరాఠి", "மராத்தி", "മറാത്തി", "മറാഠി",
        ),
    ),
    (
        "ml-IN",
        ("ml", "ml-in"),
        (
            "malayalam", "malyalam", "malayala", "malayaalam", "malayali",
            "മലയാളം", "मलयालम", "मलयाळम", "ಮಲಯಾಳಂ", "ಮಲೆಯಾಳಂ", "మలయాళం", "మళయాళం", "மலையாளம்",
        ),
    ),
    (
        "kn-IN",
        ("kn", "kn-in"),
        (
            "kannada", "kanada", "kannad", "kannda",
            "ಕನ್ನಡ", "कन्नड़", "कन्नड", "కన్నడ", "కన్నడం", "கன்னடம்", "കന്നഡ",
        ),
    ),
    (
        "en-IN",
        ("en", "eng", "en-in"),
        (
            "english", "inglish", "angrezi", "angreji",
            "ಇಂಗ್ಲಿಷ್", "ಇಂಗ್ಲೀಷ್", "अंग्रेजी", "अंग्रेज़ी", "इंग्लिश", "इंग्रजी",
            "ఇంగ్లీష్", "ఇంగ్లిష్", "ஆங்கிலம்", "இங்கிலீஷ்", "ഇംഗ്ലീഷ്",
        ),
    ),
]


def _normalize_language_input(text: str) -> Tuple[str, List[str]]:
    """Lowercase text and strip punctuation/symbols while preserving Indic combining marks."""
    raw = (text or "").strip().lower()
    cleaned_chars = [
        " " if unicodedata.category(ch).startswith(("P", "S")) else ch
        for ch in raw
    ]
    cleaned = " ".join("".join(cleaned_chars).split())
    return cleaned, cleaned.split()


def _parse_requested_language(text: str) -> Optional[str]:
    """Identify a user's requested language from English names, native scripts, or phonetic variants."""
    cleaned, tokens = _normalize_language_input(text)
    if not cleaned:
        return None
    token_set = set(tokens)

    # Match full names, native scripts, and phonetic variants before 2-letter codes
    # so e.g. "marathi" never collides with "hi".
    for lang_code, _, terms in LANGUAGE_MATCH_RULES:
        if any(term in cleaned for term in terms):
            return lang_code

    for lang_code, exact_tokens, _ in LANGUAGE_MATCH_RULES:
        if any(tok in token_set for tok in exact_tokens):
            return lang_code

    return None


async def _sarvam_stt_saarika(audio_bytes: bytes, language_code: str = "unknown", ext: str = ".ogg") -> Tuple[str, str]:
    """Transcribe audio using Sarvam STT (saarika:v2.5) with the user's saved language_code."""
    if not config.has_sarvam():
        raise RuntimeError("SARVAM_API_KEY not configured")
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key": config.SARVAM_API_KEY}
    filename = f"voice{ext or '.ogg'}"
    files = {"file": (filename, audio_bytes, "audio/ogg")}
    data = {
        "model": "saarika:v2.5",
        "language_code": language_code or "unknown",
    }
    timeout = httpx.Timeout(connect=3.0, read=14.0, write=10.0, pool=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, files=files, data=data)
        resp.raise_for_status()
        res = resp.json()
        transcript = (res.get("transcript") or "").strip()
        detected_lang = res.get("language_code") or (language_code if language_code != "unknown" else "kn-IN")
        return transcript, detected_lang


async def _gemini_audio_fallback(
    audio_bytes: bytes,
    mime_type: str,
    language_code: str,
    expected_hint: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Pass audio bytes directly to Gemini via types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    using candidate models ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.6-flash"]
    with thinking_config=types.ThinkingConfig(thinking_level="LOW").
    Falls back cleanly with detailed failure logging.
    """
    if not config.has_gemini():
        err_msg = "GEMINI_API_KEY is missing; cannot analyze audio."
        logger.error("[Gemini Audio] %s", err_msg)
        print(f"[Gemini Audio ERROR] {err_msg}", flush=True)
        raise RuntimeError(err_msg)

    client = genai.Client(
        api_key=config.GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=20000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    clean_mime = (mime_type or "audio/ogg").split(";")[0].strip().lower()
    expected = expected_hint or language_code or "Indian language/Kannada/Hindi/English"
    prompt = (
        f"Listen to this farmer's voice message carefully. "
        f"Transcribe this farmer's voice query accurately in its original language "
        f"(expected language: {expected}). "
        "Return ONLY the transcribed text, nothing else. If unintelligible, return an empty string."
    )

    contents = [
        prompt,
        types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime),
    ]

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.6-flash"]
    last_error: Optional[Exception] = None

    for model_name in candidate_models:
        try:
            t0 = time.perf_counter()
            logger.info(
                "[Gemini Audio] Calling %s (mime=%s, bytes=%d, lang=%s)...",
                model_name, clean_mime, len(audio_bytes), language_code,
            )
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction="You are an expert Indic agricultural speech-to-text transcriber.",
                    thinking_config=types.ThinkingConfig(thinking_level="LOW"),
                ),
            )
            raw_text = response.text or ""
            transcript = raw_text.strip()
            elapsed = time.perf_counter() - t0
            print(
                f"[Gemini Audio] Model {model_name} responded in {elapsed:.2f}s | byte_len={len(audio_bytes)} | transcript_len={len(transcript)}",
                flush=True,
            )
            if transcript:
                return transcript, language_code or "kn-IN"
            logger.warning("[Gemini Audio] Model %s returned empty text, trying next model...", model_name)
        except Exception as exc:
            last_error = exc
            status_code = getattr(getattr(exc, "response", None), "status_code", "N/A")
            resp_body = getattr(getattr(exc, "response", None), "text", "N/A")
            logger.error(
                "[Gemini Audio ERROR] Model %s failed: status=%s, body=%s, exc=%s",
                model_name, status_code, resp_body, exc, exc_info=True,
            )
            print(
                f"[Gemini Audio ERROR] Model {model_name} failed | status={status_code} | body={resp_body} | exc={type(exc).__name__}: {exc}",
                flush=True,
            )
            continue

    raise RuntimeError(f"All Gemini Audio models failed ({candidate_models}): {last_error}")


async def _handle_location_saved_and_pending(
    from_number: str,
    lat: float,
    lon: float,
    district: str,
    state: str,
    location_name: str,
    user_lang: str,
    pending_question: Optional[str],
    dry_run: bool,
) -> Dict[str, Any]:
    saved = location_service.save_user_location(
        user_id=from_number,
        phone_number=from_number,
        latitude=lat,
        longitude=lon,
        district=district,
        state=state,
        location_name=location_name,
    )
    location_service.update_whatsapp_state(
        phone_number=from_number,
        preferred_language=user_lang,
        clear_pending=True,
    )

    template = LOCATION_SAVED_MESSAGES.get(user_lang, LOCATION_SAVED_MESSAGES["en-IN"])
    confirm_text = template.format(loc=saved["location_name"], lat=lat, lon=lon)
    reply_text = confirm_text

    if pending_question:
        try:
            advisor_res = await voice.process_voice_or_text(
                query_text=pending_question,
                audio_bytes=None,
                language=user_lang,
                lat=lat,
                lon=lon,
                location_name=saved["location_name"],
                user_id=from_number,
                skip_tts=True,
            )
            answer = advisor_res.get("response", "").strip()
            if answer:
                reply_text = f"{confirm_text}\n\n{answer}"
        except Exception as exc:
            logger.error("[WhatsApp] Failed answering pending question after location save: %s", exc, exc_info=True)
            print(f"[WhatsApp Pending Query ERROR] {exc}", flush=True)
            err_note = ERROR_MESSAGES.get(user_lang, ERROR_MESSAGES["en-IN"])
            reply_text = f"{confirm_text}\n\n{err_note}"

    send_status = await _deliver_text(from_number, reply_text, dry_run)
    return {
        "location": saved,
        "language": user_lang,
        "reply_text": reply_text,
        "send_status": send_status,
    }


async def _handle_awaiting_language_choice(
    from_number: str,
    saved_loc: Dict[str, Any],
    user_input: str,
    dry_run: bool,
) -> Dict[str, Any]:
    """
    Shared handler for Step 3 (`awaiting_language_choice == True`) across text and voice replies.
    Matches the requested language, saves it to SQLite (`user_locations` and `whatsapp_user_states`),
    clears `awaiting_language_choice`, and sends the confirmation message + edge-tts voice note
    in the newly selected native language.
    """
    chosen_lang = _parse_requested_language(user_input) or voice.detect_language_from_text(
        user_input, default="en-IN"
    )
    location_service.save_user_location(
        user_id=from_number,
        phone_number=from_number,
        latitude=saved_loc["latitude"],
        longitude=saved_loc["longitude"],
        district=saved_loc.get("district"),
        state=saved_loc.get("state"),
        location_name=saved_loc.get("location_name"),
        language_code=chosen_lang,
        awaiting_language_choice=False,
    )
    location_service.update_whatsapp_state(
        phone_number=from_number,
        preferred_language=chosen_lang,
    )
    confirm_msg = LANGUAGE_CONFIRMED_MESSAGES.get(chosen_lang, LANGUAGE_CONFIRMED_MESSAGES["en-IN"])
    audio_b64 = await _send_voice_note_text(from_number, confirm_msg, chosen_lang, dry_run=dry_run)
    send_status = await _deliver_text(from_number, confirm_msg, dry_run)
    result: Dict[str, Any] = {
        "transcript": user_input,
        "language": chosen_lang,
        "awaiting_language_choice": False,
        "reply_text": confirm_msg,
        "send_status": send_status,
    }
    if audio_b64:
        result["reply_audio_base64"] = audio_b64
        result["voice"] = True
    return result


async def process_whatsapp_incoming_message(
    msg: Dict[str, Any],
    from_number: str = "919876543210",
    raw_audio_bytes: Optional[bytes] = None,
    raw_image_bytes: Optional[bytes] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Process an incoming parsed WhatsApp message:
    - Location message (type == "location")
    - Text message
    - Audio message (Sarvam saaras:v4 -> Gemini -> Sarvam TTS + OGG/Opus voice note + localized summary)
    - Image message (Live Gemini Vision prompt-first multimodal analysis)
    """
    msg_type = msg.get("type", "text")
    message_id = msg.get("id")
    metadata: Dict[str, Any] = {"type": msg_type, "from": from_number}
    if message_id:
        metadata["message_id"] = message_id

    if not dry_run and message_id and config.has_whatsapp() and not msg.get("_read_marked"):
        try:
            await mark_whatsapp_message_read(message_id)
            metadata["read_receipt_sent"] = True
        except Exception as e:
            logger.warning("[WhatsApp] Could not send read receipt for %s: %s", message_id, e)
    elif msg.get("_read_marked"):
        metadata["read_receipt_sent"] = True

    user_state = location_service.get_whatsapp_state(from_number)
    saved_loc = location_service.get_saved_user_location(from_number)

    # ── 0. INTERACTIVE BUTTON CLICKS ──────────────────────────────────────────
    if msg_type == "interactive":
        button_reply = msg.get("interactive", {}).get("button_reply", {})
        button_id = button_reply.get("id")
        native_lang = (saved_loc.get("language_code") if saved_loc else None) or user_state.get("preferred_language") or "en-IN"

        if button_id == "lang_confirm_native":
            confirm_msg = LANGUAGE_CONFIRMED_MESSAGES.get(native_lang, LANGUAGE_CONFIRMED_MESSAGES["en-IN"])
            await _send_voice_note_text(from_number, confirm_msg, native_lang, dry_run=dry_run)
            send_status = await _deliver_text(from_number, confirm_msg, dry_run)
            metadata.update({"button_id": button_id, "language": native_lang, "reply_text": confirm_msg, "send_status": send_status})
            return metadata

        if button_id == "lang_other_voice":
            if saved_loc:
                location_service.save_user_location(
                    user_id=from_number,
                    phone_number=from_number,
                    latitude=saved_loc["latitude"],
                    longitude=saved_loc["longitude"],
                    district=saved_loc.get("district"),
                    state=saved_loc.get("state"),
                    location_name=saved_loc.get("location_name"),
                    language_code=saved_loc.get("language_code"),
                    awaiting_language_choice=True,
                )
            send_status = await _deliver_text(from_number, ASK_OTHER_LANGUAGE_MESSAGE, dry_run)
            metadata.update({"button_id": button_id, "awaiting_language_choice": True, "reply_text": ASK_OTHER_LANGUAGE_MESSAGE, "send_status": send_status})
            return metadata

    # ── 1. WHATSAPP LOCATION PIN ──────────────────────────────────────────────
    if msg_type == "location":
        loc_obj = msg.get("location", {})
        lat = loc_obj.get("latitude")
        lon = loc_obj.get("longitude")
        if lat is None or lon is None:
            reply_text = LOCATION_ASK_MESSAGES.get(user_state["preferred_language"], LOCATION_ASK_MESSAGES["en-IN"])
            send_status = await _deliver_text(from_number, reply_text, dry_run)
            metadata["reply_text"] = reply_text
            metadata["send_status"] = send_status
            return metadata

        district, state = await _reverse_geocode_nominatim(float(lat), float(lon))
        native_lang = _map_state_to_language(state)
        display_name = f"{district}, {state}"

        saved = location_service.save_user_location(
            user_id=from_number,
            phone_number=from_number,
            latitude=float(lat),
            longitude=float(lon),
            district=district,
            state=state,
            location_name=display_name,
            language_code=native_lang,
            awaiting_language_choice=False,
        )
        location_service.update_whatsapp_state(
            phone_number=from_number,
            preferred_language=native_lang,
            clear_pending=True,
        )

        voice_prompt = NATIVE_ONBOARDING_PROMPTS.get(native_lang, NATIVE_ONBOARDING_PROMPTS["en-IN"]).format(
            district=district, state=state
        )
        await _send_voice_note_text(from_number, voice_prompt, native_lang, dry_run=dry_run)
        btn_status = await send_whatsapp_language_buttons(
            from_number, native_lang, district, state, dry_run=dry_run
        )
        metadata.update({
            "location": saved,
            "language": native_lang,
            "reply_text": voice_prompt,
            "send_status": btn_status,
        })
        return metadata

    # ── 2. TEXT MESSAGE ───────────────────────────────────────────────────────
    if msg_type == "text":
        user_text = ""
        if isinstance(msg.get("text"), dict):
            user_text = msg["text"].get("body", "")
        elif isinstance(msg.get("text"), str):
            user_text = msg["text"]
        user_text = user_text.strip()

        # Step 3: Handle awaiting_language_choice
        if saved_loc and saved_loc.get("awaiting_language_choice"):
            lang_res = await _handle_awaiting_language_choice(
                from_number=from_number,
                saved_loc=saved_loc,
                user_input=user_text,
                dry_run=dry_run,
            )
            metadata.update(lang_res)
            return metadata

        # Step 1 Onboarding: Greeting or first message without saved location
        if user_text.lower() in GREETING_TRIGGERS or (not saved_loc and not user_state.get("awaiting_location")):
            welcome_voice = (
                "Welcome to Farm Advisor! Please tap the Send Location button below "
                "so I can check your local weather, mandi rates, and language."
            )
            await _send_voice_note_text(from_number, welcome_voice, "en-IN", dry_run=dry_run)
            loc_req_status = await send_whatsapp_location_request(from_number, dry_run=dry_run)
            metadata.update({
                "transcript": user_text,
                "onboarding": "step_1_location_request",
                "reply_text": welcome_voice,
                "send_status": loc_req_status,
            })
            return metadata

        detected_lang = voice.detect_language_from_text(
            user_text, default=user_state["preferred_language"] or "kn-IN"
        )
        location_service.update_whatsapp_state(
            phone_number=from_number, preferred_language=detected_lang
        )

        # If no saved location yet, check if user is replying with their village/district name
        if not saved_loc:
            place_match = await _try_resolve_place_from_text(user_text)
            if place_match and (user_state.get("awaiting_location") or len(user_text.split()) <= 3):
                res = await _handle_location_saved_and_pending(
                    from_number=from_number,
                    lat=place_match["latitude"],
                    lon=place_match["longitude"],
                    district=place_match["district"],
                    state=place_match["state"],
                    location_name=place_match["location_name"],
                    user_lang=detected_lang,
                    pending_question=user_state.get("pending_question"),
                    dry_run=dry_run,
                )
                metadata["transcript"] = user_text
                metadata.update(res)
                return metadata

            if is_location_dependent_query(user_text):
                location_service.update_whatsapp_state(
                    phone_number=from_number,
                    preferred_language=detected_lang,
                    awaiting_location=True,
                    pending_question=user_text,
                )
                reply_text = LOCATION_ASK_MESSAGES.get(detected_lang, LOCATION_ASK_MESSAGES["en-IN"])
                send_status = await _deliver_text(from_number, reply_text, dry_run)
                metadata.update({
                    "transcript": user_text,
                    "language": detected_lang,
                    "awaiting_location": True,
                    "reply_text": reply_text,
                    "send_status": send_status,
                })
                return metadata

        try:
            advisor_res = await voice.process_voice_or_text(
                query_text=user_text,
                audio_bytes=None,
                language=detected_lang,
                lat=saved_loc["latitude"] if saved_loc else None,
                lon=saved_loc["longitude"] if saved_loc else None,
                location_name=saved_loc["location_name"] if saved_loc else None,
                user_id=from_number,
                skip_tts=True,
            )
            reply_text = advisor_res["response"]
            metadata["language"] = advisor_res.get("language", detected_lang)
            metadata["status"] = "live"
        except Exception as exc:
            logger.error("[WhatsApp Text] Live Gemini processing failed: %s", exc, exc_info=True)
            print(f"[WhatsApp Text ERROR] {type(exc).__name__}: {exc}", flush=True)
            reply_text = ERROR_MESSAGES.get(detected_lang, ERROR_MESSAGES["en-IN"])
            metadata["language"] = detected_lang
            metadata["status"] = "error"
            metadata["error"] = str(exc)

        send_status = await _deliver_text(from_number, reply_text, dry_run)
        metadata["transcript"] = user_text
        metadata["reply_text"] = reply_text
        metadata["send_status"] = send_status
        return metadata

    # ── 3. AUDIO / VOICE NOTE ─────────────────────────────────────────────────
    if msg_type == "audio":
        audio_obj = msg.get("audio", {})
        media_id = audio_obj.get("id") if isinstance(audio_obj, dict) else None
        audio_bytes = raw_audio_bytes
        audio_mime = "audio/ogg"
        audio_ext = ".ogg"

        pref_lang = (saved_loc.get("language_code") if saved_loc else None) or user_state["preferred_language"] or "kn-IN"

        # Separate Try/Except Block 1: Media Download
        if not audio_bytes and not dry_run and media_id:
            try:
                audio_bytes, audio_mime, audio_ext = await download_whatsapp_media(media_id)
            except Exception as dl_exc:
                status_code = getattr(getattr(dl_exc, "response", None), "status_code", "N/A")
                resp_body = getattr(getattr(dl_exc, "response", None), "text", "N/A")
                logger.error(
                    "[WhatsApp Audio Download FAILURE] media_id=%s | status=%s | body=%s | exc=%s",
                    media_id, status_code, resp_body, dl_exc, exc_info=True,
                )
                print(
                    f"[WhatsApp Audio Download FAILURE] media_id={media_id} | status={status_code} | body={resp_body} | exc={type(dl_exc).__name__}: {dl_exc}",
                    flush=True,
                )
                audio_bytes = b""

        if not audio_bytes or len(audio_bytes) <= 100:
            print(
                f"[WhatsApp Audio Download INCOMPLETE] media_id={media_id} | byte_len={len(audio_bytes) if audio_bytes else 0} <= 100",
                flush=True,
            )
            reply_text = RESEND_MEDIA_MESSAGES.get(pref_lang, RESEND_MEDIA_MESSAGES["en-IN"])
            send_status = await _deliver_text(from_number, reply_text, dry_run)
            metadata.update({
                "status": "error",
                "error": "Media download failed or byte length <= 100",
                "media_id": media_id,
                "reply_text": reply_text,
                "send_status": send_status,
            })
            return metadata

        # Separate Try/Except Block 2: Gemini Audio Transcription / Analysis
        saved_lang = (saved_loc.get("language_code") if saved_loc else None) or user_state.get("preferred_language") or "kn-IN"
        is_awaiting_lang = bool(saved_loc and saved_loc.get("awaiting_language_choice"))
        transcript = ""
        lang_code = saved_lang if saved_lang != "unknown" else "kn-IN"
        expected_hint = (
            "English or Indian language name (Hindi, Telugu, Tamil, Marathi, Malayalam, Kannada, English)"
            if is_awaiting_lang
            else None
        )
        try:
            transcript, lang_code = await _gemini_audio_fallback(
                audio_bytes,
                audio_mime or "audio/ogg",
                lang_code,
                expected_hint=expected_hint,
            )
            if not transcript:
                raise ValueError("Gemini returned empty transcription text")
        except Exception as gem_exc:
            status_code = getattr(getattr(gem_exc, "response", None), "status_code", "N/A")
            resp_body = getattr(getattr(gem_exc, "response", None), "text", "N/A")
            byte_len = len(audio_bytes) if audio_bytes else 0
            logger.error(
                "[WhatsApp Audio Gemini Analysis FAILURE] media_id=%s | mime_type=%s | byte_len=%d | status=%s | body=%s | exc=%s",
                media_id, audio_mime, byte_len, status_code, resp_body, gem_exc, exc_info=True,
            )
            print(
                f"[WhatsApp Audio Gemini Analysis FAILURE] media_id={media_id} | mime_type={audio_mime} | byte_len={byte_len} | status={status_code} | body={resp_body} | exc={type(gem_exc).__name__}: {gem_exc}",
                flush=True,
            )
            # Clean fallback: instead of generic resend message, provide helpful agricultural fallback
            fallback_msgs = {
                "kn-IN": "ಧ್ವನಿ ಸಂದೇಶ ಸ್ವೀಕರಿಸಲಾಗಿದೆ. ನಿಮ್ಮ ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆಯನ್ನು ಪಠ್ಯ ಸಂದೇಶದ ಮೂಲಕ ಟೈಪ್ ಮಾಡಿ ಕಳುಹಿಸಿ ಅಥವಾ ಸ್ಪಷ್ಟ ಧ್ವನಿಯಲ್ಲಿ ಮತ್ತೆ ಕಳುಹಿಸಿ.",
                "hi-IN": "वॉइस संदेश प्राप्त हुआ। आपकी आवाज स्पष्ट नहीं सुनाई दी। कृपया अपना कृषि सवाल टेक्स्ट में लिखकर भेजें या फिर से स्पष्ट बोलें।",
                "te-IN": "వాయిస్ సందేశం అందింది. మీ ప్రశ్న స్పష్టంగా లేదు. దయచేసి మీ ప్రశ్నను టైప్ చేసి పంపండి లేదా మళ్లీ స్పష్టంగా మాట్లాడండి.",
                "ta-IN": "குரல் செய்தி பெறப்பட்டது. உங்கள் கேள்வி தெளிவாக இல்லை. தயவுசெய்து உங்கள் கேள்வியை தட்டச்சு செய்து அனுப்பவும் அல்லது மீண்டும் தெளிவாக பேசவும்.",
                "mr-IN": "व्हॉइस मेसेज मिळाला. तुमचा आवाज स्पष्ट ऐकू आला नाही. कृपया तुमचा शेतीविषयक प्रश्न मेसेजमध्ये टाईप करून पाठवा किंवा पुन्हा स्पष्ट बोला.",
                "ml-IN": "വോയ്‌സ് സന്ദേശം ലഭിച്ചു, എന്നാൽ വ്യക്തമായി മനസ്സിലായില്ല. ദയവായി നിങ്ങളുടെ ചോദ്യം ടെക്സ്റ്റ് ആയി ടൈപ്പ് ചെയ്ത് അയയ്ക്കുക അല്ലെങ്കിൽ വ്യക്തമായി വീണ്ടും സംസാരിക്കുക.",
                "en-IN": "Voice note received, but could not transcribe clearly. Please type your agricultural query as a text message or resend a clear voice note.",
            }
            reply_text = fallback_msgs.get(lang_code, fallback_msgs["en-IN"])
            send_status = await _deliver_text(from_number, reply_text, dry_run)
            metadata.update({
                "status": "error",
                "error": str(gem_exc),
                "media_id": media_id,
                "mime_type": audio_mime,
                "byte_len": byte_len,
                "reply_text": reply_text,
                "send_status": send_status,
            })
            return metadata

        # Step 3: Handle awaiting_language_choice via the shared text/voice handler
        if is_awaiting_lang:
            lang_res = await _handle_awaiting_language_choice(
                from_number=from_number,
                saved_loc=saved_loc,
                user_input=transcript,
                dry_run=dry_run,
            )
            metadata.update(lang_res)
            return metadata

        location_service.update_whatsapp_state(phone_number=from_number, preferred_language=lang_code)
        metadata["transcript"] = transcript
        metadata["language"] = lang_code

        # Check saved location before answering location-dependent voice queries
        if not saved_loc:
            place_match = await _try_resolve_place_from_text(transcript)
            if place_match and (user_state.get("awaiting_location") or len(transcript.split()) <= 3):
                res = await _handle_location_saved_and_pending(
                    from_number=from_number,
                    lat=place_match["latitude"],
                    lon=place_match["longitude"],
                    district=place_match["district"],
                    state=place_match["state"],
                    location_name=place_match["location_name"],
                    user_lang=lang_code,
                    pending_question=user_state.get("pending_question"),
                    dry_run=dry_run,
                )
                metadata.update(res)
                return metadata

            if is_location_dependent_query(transcript):
                location_service.update_whatsapp_state(
                    phone_number=from_number,
                    preferred_language=lang_code,
                    awaiting_location=True,
                    pending_question=transcript,
                )
                reply_text = LOCATION_ASK_MESSAGES.get(lang_code, LOCATION_ASK_MESSAGES["en-IN"])
                reply_audio_b64 = await voice.synthesize_speech(reply_text, language_code=lang_code)
                if reply_audio_b64:
                    metadata["reply_audio_base64"] = reply_audio_b64
                    metadata["voice"] = True
                    if not dry_run and config.has_whatsapp():
                        ogg = await asyncio.to_thread(convert_audio_to_ogg_opus, base64.b64decode(reply_audio_b64))
                        up_id = await upload_whatsapp_media(ogg, mime_type="audio/ogg")
                        if up_id:
                            metadata["audio_send_status"] = await send_whatsapp_audio(from_number, up_id)
                send_status = await _deliver_text(from_number, reply_text, dry_run)
                metadata.update({
                    "awaiting_location": True,
                    "reply_text": reply_text,
                    "send_status": send_status,
                })
                return metadata

        # Step B: Live Gemini reasoning + Sarvam TTS in exact detected language
        try:
            advisor_res = await voice.process_voice_or_text(
                query_text=transcript,
                audio_bytes=None,
                language=lang_code,
                lat=saved_loc["latitude"] if saved_loc else None,
                lon=saved_loc["longitude"] if saved_loc else None,
                location_name=saved_loc["location_name"] if saved_loc else None,
                user_id=from_number,
                skip_tts=False,
            )
            reply_text = advisor_res["response"]
            lang_code = advisor_res.get("language", lang_code)
            reply_audio_b64 = advisor_res.get("audio_base64")
            metadata["status"] = "live"
        except Exception as exc:
            logger.error("[WhatsApp Audio] Live Gemini failed: %s", exc, exc_info=True)
            print(f"[WhatsApp Audio GEMINI ERROR] {type(exc).__name__}: {exc}", flush=True)
            reply_text = ERROR_MESSAGES.get(lang_code, ERROR_MESSAGES["en-IN"])
            reply_audio_b64 = await voice.synthesize_speech(reply_text, language_code=lang_code)
            metadata["status"] = "error"
            metadata["error"] = str(exc)

        if reply_audio_b64:
            metadata["reply_audio_base64"] = reply_audio_b64
            metadata["voice"] = True
            try:
                mp3_bytes = base64.b64decode(reply_audio_b64)
                if not _is_valid_mp3(mp3_bytes):
                    logger.warning("[WhatsApp Audio] Invalid or empty MP3 bytes (%d bytes); skipping audio send", len(mp3_bytes))
                elif not dry_run and config.has_whatsapp():
                    uploaded_media_id = await upload_whatsapp_media(mp3_bytes, mime_type="audio/mpeg")
                    if uploaded_media_id:
                        metadata["audio_send_status"] = await send_whatsapp_audio(
                            recipient_phone=from_number, media_id=uploaded_media_id
                        )
            except Exception as exc:
                logger.error("[WhatsApp Audio] Failed sending voice reply audio: %s", exc)

        hdr, q_lbl, a_lbl = VOICE_SUMMARY_HEADERS.get(lang_code, VOICE_SUMMARY_HEADERS["en-IN"])
        summary_text = "\n".join([
            hdr,
            f"• *{q_lbl}:* {transcript}",
            f"• *{a_lbl}:* {reply_text}",
        ])
        send_status = await _deliver_text(from_number, summary_text, dry_run)
        metadata["reply_text"] = reply_text
        metadata["summary_text"] = summary_text
        metadata["send_status"] = send_status
        return metadata

    # ── 4. IMAGE ATTACHMENT ───────────────────────────────────────────────────
    if msg_type == "image":
        img_obj = msg.get("image", {})
        caption = img_obj.get("caption", "") if isinstance(img_obj, dict) else msg.get("caption", "")
        media_id = img_obj.get("id") if isinstance(img_obj, dict) else None

        image_bytes = raw_image_bytes
        image_mime = "image/jpeg"
        if not image_bytes and not dry_run and media_id:
            try:
                image_bytes, image_mime, _ = await download_whatsapp_media(media_id)
            except Exception as dl_exc:
                status_code = getattr(getattr(dl_exc, "response", None), "status_code", "N/A")
                resp_body = getattr(getattr(dl_exc, "response", None), "text", "N/A")
                logger.error(
                    "[WhatsApp Image Download FAILURE] media_id=%s | status=%s | body=%s | exc=%s",
                    media_id, status_code, resp_body, dl_exc, exc_info=True,
                )
                print(
                    f"[WhatsApp Image Download FAILURE] media_id={media_id} | status={status_code} | body={resp_body} | exc={type(dl_exc).__name__}: {dl_exc}",
                    flush=True,
                )
                image_bytes = b""

        pref_lang = (saved_loc.get("language_code") if saved_loc else None) or user_state.get("preferred_language") or "kn-IN"
        detected_lang = (
            voice.detect_language_from_text(caption, default=pref_lang)
            if caption and caption.strip()
            else pref_lang
        )
        location_service.update_whatsapp_state(phone_number=from_number, preferred_language=detected_lang)

        if not image_bytes or len(image_bytes) <= 100:
            byte_len = len(image_bytes) if image_bytes else 0
            print(
                f"[WhatsApp Image Download INCOMPLETE] media_id={media_id} | mime_type={image_mime} | byte_len={byte_len} <= 100",
                flush=True,
            )
            reply_text = RESEND_MEDIA_MESSAGES.get(detected_lang, RESEND_MEDIA_MESSAGES["en-IN"])
            send_status = await _deliver_text(from_number, reply_text, dry_run)
            metadata.update({
                "status": "error",
                "error": "Media download failed or byte length <= 100",
                "media_id": media_id,
                "mime_type": image_mime,
                "byte_len": byte_len,
                "reply_text": reply_text,
                "send_status": send_status,
            })
            return metadata

        try:
            scan_data = await asyncio.to_thread(
                scan.process_scan_bytes,
                image_bytes=image_bytes,
                mode="auto",
                filename="whatsapp_photo.jpg",
                question=caption,
                language=detected_lang,
                lat=saved_loc["latitude"] if saved_loc else None,
                lon=saved_loc["longitude"] if saved_loc else None,
                location_name=saved_loc["location_name"] if saved_loc else None,
                user_id=from_number,
            )
            reply_text = format_scan_result_for_whatsapp(scan_data, language=detected_lang)
            metadata["mode"] = scan_data.get("mode")
            metadata["caption"] = caption
            metadata["language"] = detected_lang
            metadata["scan_result"] = scan_data.get("result")
            metadata["status"] = "live"
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", "N/A")
            resp_body = getattr(getattr(exc, "response", None), "text", "N/A")
            byte_len = len(image_bytes) if image_bytes else 0
            logger.error(
                "[WhatsApp Image Gemini Analysis FAILURE] media_id=%s | mime_type=%s | byte_len=%d | status=%s | body=%s | exc=%s",
                media_id, image_mime, byte_len, status_code, resp_body, exc, exc_info=True,
            )
            print(
                f"[WhatsApp Image Gemini Analysis FAILURE] media_id={media_id} | mime_type={image_mime} | byte_len={byte_len} | status={status_code} | body={resp_body} | exc={type(exc).__name__}: {exc}",
                flush=True,
            )
            reply_text = ERROR_MESSAGES.get(detected_lang, ERROR_MESSAGES["en-IN"])
            metadata["language"] = detected_lang
            metadata["status"] = "error"
            metadata["error"] = str(exc)

        try:
            reply_audio_b64 = await _send_voice_note_text(
                from_number, reply_text, detected_lang, dry_run=dry_run
            )
            if reply_audio_b64:
                metadata["reply_audio_base64"] = reply_audio_b64
                metadata["voice"] = True
        except Exception as tts_exc:
            logger.error(
                "[WhatsApp Image Voice Reply ERROR] media_id=%s | lang=%s | exc=%s",
                media_id, detected_lang, tts_exc, exc_info=True,
            )
            print(
                f"[WhatsApp Image Voice Reply ERROR] media_id={media_id} | lang={detected_lang} | exc={type(tts_exc).__name__}: {tts_exc}",
                flush=True,
            )

        send_status = await _deliver_text(from_number, reply_text, dry_run)
        metadata["reply_text"] = reply_text
        metadata["send_status"] = send_status
        return metadata

    # ── 5. UNSUPPORTED MESSAGE TYPE ───────────────────────────────────────────
    reply_text = (
        "Namaskara! Please send a text query, voice note, crop/bottle photo, "
        "or share your WhatsApp Location pin for live farm advisory."
    )
    send_status = await _deliver_text(from_number, reply_text, dry_run)
    metadata["reply_text"] = reply_text
    metadata["send_status"] = send_status
    return metadata


# ───────────────────────── ROUTE ENDPOINTS ───────────────────────────────────

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta Webhook Verification."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    expected_token = config.WHATSAPP_VERIFY_TOKEN or "krishimitra_verify"

    if mode == "subscribe" and token == expected_token:
        try:
            challenge_int = int(challenge) if challenge else 0
            return Response(content=str(challenge_int), media_type="text/plain", status_code=status.HTTP_200_OK)
        except Exception:
            return Response(content=str(challenge or ""), media_type="text/plain", status_code=status.HTTP_200_OK)

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")


@router.post("/webhook")
async def incoming_webhook(request: Request, background_tasks: BackgroundTasks):
    """Meta WhatsApp Cloud API incoming webhook handler."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    entries = payload.get("entry", [])
    if not entries:
        return {"status": "ignored", "reason": "No entry found"}

    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                msg_id = msg.get("id")
                from_num = msg.get("from", "919876543210")
                if msg_id and config.has_whatsapp():
                    background_tasks.add_task(mark_whatsapp_message_read, msg_id)
                    msg["_read_marked"] = True
                background_tasks.add_task(process_whatsapp_incoming_message, msg=msg, from_number=from_num)

    return {"status": "received"}


@router.post("/simulate")
async def simulate_whatsapp_webhook(payload: WhatsAppSimulateRequest):
    """
    Local simulation endpoint for testing WhatsApp text, voice, image, and location workflows.
    """
    body = payload.model_dump(by_alias=True, exclude_unset=False)

    if body.get("entry"):
        entries = body.get("entry", [])
        processed = []
        for entry in entries:
            for change in entry.get("changes", []):
                val = change.get("value", {})
                for msg in val.get("messages", []):
                    from_num = msg.get("from", "919876543210")
                    res = await process_whatsapp_incoming_message(msg=msg, from_number=from_num, dry_run=True)
                    processed.append(res)
        return {"status": "success", "processed": processed}

    msg_type = payload.type or "text"
    from_number = payload.from_number or "919876543210"

    raw_audio = None
    if payload.audio_base64:
        try:
            raw_audio = base64.b64decode(payload.audio_base64)
        except Exception:
            raw_audio = None

    raw_image = None
    if payload.image_base64:
        try:
            raw_image = base64.b64decode(payload.image_base64)
        except Exception:
            raw_image = None

    synthetic_msg: Dict[str, Any] = {"type": msg_type, "id": "sim_msg_001"}
    if msg_type == "text":
        synthetic_msg["text"] = {"body": payload.text or payload.query or ""}
    elif msg_type == "audio":
        synthetic_msg["audio"] = {"id": "sim_audio_media_id"}
    elif msg_type == "image":
        synthetic_msg["image"] = {
            "id": "sim_image_media_id",
            "caption": payload.caption or "",
        }
    elif msg_type == "location":
        synthetic_msg["location"] = {
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "name": payload.location_name,
        }

    res = await process_whatsapp_incoming_message(
        msg=synthetic_msg,
        from_number=from_number,
        raw_audio_bytes=raw_audio,
        raw_image_bytes=raw_image,
        dry_run=True,
    )
    return {"status": "success", "result": res}
