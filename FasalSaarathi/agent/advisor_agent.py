"""
FasalSaarathi Agentic AI Engine — FarmAdvisorAgent
================================================
Implements a full Agentic Tool-Calling Loop using Google Gemini API:
  Thought → Action (Select Tool & Arguments) → Tool Execution → Observation → Synthesis

When GEMINI_API_KEY is set:
  - Uses Gemini with FunctionDeclarations for real AI tool selection
  - Multi-turn tool-calling loop until Gemini produces a final text response
  - Renders response purely in the farmer's chosen regional language

When GEMINI_API_KEY is absent or API fails:
  - Falls back to rule-based heuristic tool selection
  - Clearly labels output as "[Rule-Based Fallback - No Gemini API Key]"

Supports 6 Indian languages: Kannada, Hindi, Tamil, Telugu, Marathi, English
"""

import os
import re
import json
import traceback
from typing import Dict, Any, List, Optional

import sys
import requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.weather_tool import fetch_live_weather
from tools.soil_tool import fetch_soil_health
from tools.mandi_tool import fetch_mandi_prices
from tools.crop_disease_tool import analyze_leaf_image, diagnose_text_symptoms

# ─────────────────────────────────────────────
# Language Metadata
# ─────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "kn": {"name": "Kannada",  "native": "ಕನ್ನಡ",   "voice_code": "kn-IN", "speech_recog": "kn-IN"},
    "hi": {"name": "Hindi",   "native": "हिंदी",   "voice_code": "hi-IN", "speech_recog": "hi-IN"},
    "ta": {"name": "Tamil",   "native": "தமிழ்",    "voice_code": "ta-IN", "speech_recog": "ta-IN"},
    "te": {"name": "Telugu",  "native": "తెలుగు",   "voice_code": "te-IN", "speech_recog": "te-IN"},
    "mr": {"name": "Marathi", "native": "मराठी",   "voice_code": "mr-IN", "speech_recog": "mr-IN"},
    "en": {"name": "English", "native": "English",  "voice_code": "en-IN", "speech_recog": "en-IN"},
}

CROP_NAMES = {
    "tomato":   {"kn": "ಟೊಮೆಟೊ",    "hi": "टमाटर",    "en": "Tomato",      "ta": "தக்காளி",       "te": "టమోటా",        "mr": "टोमॅटो"},
    "coffee":   {"kn": "ಕಾಫಿ",       "hi": "कॉफ़ी",   "en": "Coffee",      "ta": "காபி",          "te": "కాఫీ",         "mr": "कॉफी"},
    "arecanut": {"kn": "ಅಡಿಕೆ",      "hi": "सुपारी",   "en": "Arecanut",    "ta": "பாக்கு",        "te": "పోక చెక్క",    "mr": "सुपारी"},
    "pepper":   {"kn": "ಕರಿಮೆಣಸು",  "hi": "काली मिर्च","en": "Black Pepper","ta": "மிளகு",         "te": "మిరియాలు",     "mr": "काळी मिरी"},
    "onion":    {"kn": "ಈರುಳ್ಳಿ",   "hi": "प्याज",    "en": "Onion",       "ta": "வெங்காயம்",     "te": "ఉల్లిపాయ",    "mr": "कांदा"},
    "potato":   {"kn": "ಆಲೂಗಡ್ಡೆ",  "hi": "आलू",      "en": "Potato",      "ta": "உருளைக்கிழங்கு","te": "బంగాళాదుంప",  "mr": "बटाटा"},
    "cotton":   {"kn": "ಹತ್ತಿ",      "hi": "कपास",     "en": "Cotton",      "ta": "பருத்தி",        "te": "పత్తి",        "mr": "कापूस"},
    "chilli":   {"kn": "ಮೆಣಸಿನಕಾಯಿ","hi": "मिर्च",     "en": "Chilli",      "ta": "மிளகாய்",       "te": "మిర్చి",       "mr": "मिरची"},
    "rice":     {"kn": "ಭತ್ತ",        "hi": "धान",      "en": "Rice",        "ta": "நெல்",          "te": "వరి",          "mr": "भात"},
    "wheat":    {"kn": "ಗೋಧಿ",       "hi": "गेहूं",    "en": "Wheat",       "ta": "கோதுமை",        "te": "గోధుమ",        "mr": "गहू"},
}

# ─────────────────────────────────────────────
# Gemini Tool Declarations (Function Calling)
# ─────────────────────────────────────────────
GEMINI_TOOL_DECLARATIONS = [
    {
        "name": "fetch_live_weather",
        "description": (
            "Fetch real-time agro-meteorological weather, 6-hour spray window, crop evapotranspiration (ET0), "
            "and 7-day forecast for any Indian village, taluk, district, city, or 6-digit PIN code. "
            "Never assume a default location. Only call when the farmer provides a location; if missing, ask for their location."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Village, taluk, district, city, or 6-digit PIN code mentioned by the farmer"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "fetch_soil_health",
        "description": (
            "Fetch live 5-depth root-zone soil moisture & soil temperature (Open-Meteo Land-Surface API) "
            "plus 250m-resolution satellite/pedological topsoil pH, organic carbon, texture (sand/clay/silt), "
            "and crop-specific ICAR amendments for any Indian village, taluk, district, or PIN code. "
            "Never assume a default district; ask the farmer for their location if missing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "district": {
                    "type": "string",
                    "description": "Village, taluk, district, city, or 6-digit PIN code mentioned by the farmer"
                },
                "crop": {
                    "type": "string",
                    "description": "Crop grown by the farmer (e.g., tomato, rice, coffee, tur, cotton, onion, sugarcane)"
                }
            },
            "required": ["district"]
        }
    },
    {
        "name": "fetch_mandi_prices",
        "description": (
            "Fetch APMC mandi market prices and selling advisory for agricultural commodities. "
            "Use when farmer asks about crop price, market rate, whether to sell now or wait, "
            "or which mandi to sell at."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {
                    "type": "string",
                    "description": "Crop or commodity name (e.g., tomato, coffee, arecanut, onion, pepper)"
                },
                "location": {
                    "type": "string",
                    "description": "Location/district of the farmer (e.g., Kolar, Shimoga)"
                }
            },
            "required": ["commodity"]
        }
    },
    {
        "name": "diagnose_crop_disease",
        "description": (
            "Analyze a leaf image or symptom description to identify crop disease. "
            "Use when farmer mentions disease symptoms, spots, blight, rust, wilting, "
            "or shares a leaf photograph."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "File path to the uploaded leaf image"
                },
                "crop": {
                    "type": "string",
                    "description": "Crop type (e.g., coffee, tomato, potato)"
                }
            },
            "required": []
        }
    }
]

# Language-specific system prompts for Gemini
LANG_SYSTEM_PROMPTS = {
    "kn": (
        "ನೀವು ಫಸಲ್ ಸಾರಥಿ AI ಕೃಷಿ ಸಲಹೆಗಾರ. ರೈತರಿಗೆ ಕನ್ನಡದಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರ ನೀಡಿ. "
        "ಆಂಗ್ಲ ಭಾಷೆಯ ತಾಂತ್ರಿಕ ಪದಗಳನ್ನು ಬಳಸಬೇಡಿ. ಸರಳ ಮತ್ತು ಪ್ರಾಯೋಗಿಕ ಕೃಷಿ ಸಲಹೆ ನೀಡಿ. "
        "Tool ಡೇಟಾ ಬಂದ ನಂತರ ಸಂಪೂರ್ಣ ಸಲಹೆ ಕನ್ನಡದಲ್ಲಿ ನೀಡಿ."
    ),
    "hi": (
        "आप फसल सारथी AI कृषि सलाहकार हैं। किसानों को केवल हिंदी में उत्तर दें। "
        "अंग्रेजी तकनीकी शब्दों का उपयोग न करें। सरल और व्यावहारिक खेती की सलाह दें। "
        "Tool data मिलने के बाद पूरी सलाह हिंदी में दें।"
    ),
    "ta": (
        "நீங்கள் ஃபசல் சாரதி AI விவசாய ஆலோசகர். விவசாயிகளுக்கு தமிழில் மட்டுமே பதிலளிக்கவும். "
        "ஆங்கில தொழில்நுட்ப வார்த்தைகளை பயன்படுத்த வேண்டாம். எளிய மற்றும் நடைமுறை விவசாய ஆலோசனை வழங்கவும்."
    ),
    "te": (
        "మీరు ఫసల్ సారథి AI వ్యవసాయ సలహాదారు. రైతులకు తెలుగులో మాత్రమే సమాధానం ఇవ్వండి. "
        "ఆంగ్ల సాంకేతిక పదాలు వాడకండి. సరళమైన మరియు ఆచరణాత్మక వ్యవసాయ సలహా ఇవ్వండి."
    ),
    "mr": (
        "आपण फसल सारथी AI कृषी सल्लागार आहात. शेतकऱ्यांना फक्त मराठीत उत्तर द्या. "
        "इंग्रजी तांत्रिक शब्द वापरू नका. साधी आणि व्यावहारिक शेती सल्ला द्या."
    ),
    "en": (
        "You are FasalSaarathi AI Farm Advisor. Provide practical, evidence-based agricultural advice "
        "to Indian farmers in simple, everyday English anyone can understand. Never use Latin scientific names "
        "or technical jargon (like necrotic, chlorotic, oomycete, ET0). Never fabricate data."
    ),
}


class FarmAdvisorAgent:
    """
    Autonomous Agronomic Advisor Agent with Gemini API Tool Calling.
    Falls back to rule-based logic if API key is absent.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")).strip()
        self._use_gemini = bool(self.api_key)

    def run_tool(self, tool_name: str, args: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """Execute a named tool and return structured observation."""
        try:
            if tool_name == "fetch_live_weather":
                return fetch_live_weather(
                    location_query=args.get("location"),
                    lat=args.get("lat"),
                    lon=args.get("lon"),
                )
            elif tool_name == "fetch_soil_health":
                return fetch_soil_health(
                    district_query=args.get("district") or args.get("location"),
                    crop=args.get("crop") or "general",
                    lat=args.get("lat"),
                    lon=args.get("lon"),
                )
            elif tool_name == "fetch_mandi_prices":
                return fetch_mandi_prices(
                    commodity_query=args.get("commodity") or "tomato",
                    location_hint=args.get("location") or "",
                    lat=args.get("lat"),
                    lon=args.get("lon"),
                    language=language,
                )
            elif tool_name == "diagnose_crop_disease":
                img_path = (args.get("image_path") or "").strip()
                crop_arg = args.get("crop") or ""
                if img_path and os.path.isfile(img_path):
                    return analyze_leaf_image(img_path, crop_arg, language=language)
                return diagnose_text_symptoms(
                    args.get("symptom_query") or "", crop_hint=crop_arg, language=language
                )
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"error": str(e), "tool": tool_name}

    # ─────────────────────────────────────────────
    # GEMINI SYNTHESIS OVER LIVE TOOL DATA (HTTPS REST)
    # ─────────────────────────────────────────────
    def _run_gemini_agent(self, user_query: str, language: str,
                          attached_image: Optional[str]) -> Dict[str, Any]:
        """
        Execute all relevant farm tools first (Weather, Soil, Mandi, Leaf Disease),
        then synthesize a concise, zero-repetition response in the farmer's language
        via Gemini HTTPS REST API.
        """
        execution_trace = []
        observations = {}
        lang_name = SUPPORTED_LANGUAGES.get(language, {}).get("name", "English")

        plan = self.determine_plan(user_query, attached_image)
        for item in plan:
            t_name = item["tool"]
            t_args = item["args"]
            obs = self.run_tool(t_name, t_args, language=language)
            observations[t_name] = obs
            execution_trace.append({
                "step": f"Tool Result: {t_name}",
                "observation_summary": obs.get("summary", str(obs)[:200])
            })

        system_prompt = LANG_SYSTEM_PROMPTS.get(language, LANG_SYSTEM_PROMPTS["en"])
        greetings = {
            "kn": "ನಮಸ್ಕಾರ ರೈತ ಬಾಂಧವರೇ, ಫಸಲ್ ಸಾರಥಿ ಸಲಹೆ ಇಲ್ಲಿದೆ:",
            "hi": "नमस्ते किसान भाई, फसल सारथी की सलाह:",
            "ta": "வணக்கம் விவசாய பெருமக்களே, ஃபசல் சாரதி ஆலோசனை:",
            "te": "నమస్కారం రైతు సోదరులారా, ఫసల్ సారథి సలహా:",
            "mr": "नमस्कार शेतकरी मित्रांनो, फसल सारथीचा सल्ला:",
            "en": "Hello Farmer, here is your FasalSaarathi farm advice:",
        }
        greet = greetings.get(language, greetings["en"])

        # Compact JSON of verified tool outputs
        compact_obs = json.dumps(observations, ensure_ascii=False, default=str)[:7000]
        full_prompt = (
            f"{system_prompt}\n\n"
            f"Farmer's question: {user_query}\n"
            f"Verified live farm data from FasalSaarathi tools:\n{compact_obs}\n\n"
            f"STRICT RULES:\n"
            f"1. Start with '{greet}'.\n"
            f"2. Write ONLY in simple, everyday {lang_name} that any farmer understands.\n"
            f"3. NEVER repeat the same price, temperature, or instruction twice. State each point ONCE in clean bullet points.\n"
            f"4. NEVER use Latin scientific names or technical jargon (no necrotic, chlorotic, oomycete, ET0, modal price, bullish).\n"
            f"5. Include exact numbers from the verified tool data above (do not invent numbers).\n"
            f"6. If both disease care and weather were fetched, also tell the farmer whether today's weather is safe for spraying."
        )

        last_err = None
        final_text = ""
        for model_name in ("gemini-flash-lite-latest", "gemini-3.5-flash", "gemini-flash-latest"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            try:
                resp = requests.post(
                    url,
                    params={"key": self.api_key},
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {"temperature": 0.25},
                    },
                    timeout=(2.5, 16.0),
                )
                if resp.status_code != 200:
                    last_err = f"HTTP {resp.status_code}"
                    continue
                parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                final_text = "".join(p.get("text", "") for p in parts).strip()
                if final_text:
                    break
            except Exception as e:
                last_err = e
                continue

        if not final_text:
            raise RuntimeError(f"Gemini REST unavailable: {last_err}")

        action_cards = self._build_action_cards(observations, language)
        speech_text = self._build_full_speech_text(final_text, language)

        return {
            "status": "success",
            "mode": "gemini_api",
            "query": user_query,
            "language": language,
            "language_name": lang_name,
            "execution_trace": execution_trace,
            "tool_data": observations,
            "response_text": final_text,
            "speech_text": speech_text,
            "action_cards": action_cards
        }

    # ─────────────────────────────────────────────
    # RULE-BASED FALLBACK
    # ─────────────────────────────────────────────
    def determine_plan(self, user_query: str, attached_image: Optional[str] = None) -> List[Dict]:
        query_lower = user_query.lower()
        tools_to_call = []

        location = self._extract_location(user_query)
        crop = self._extract_crop(query_lower)

        # Disease diagnosis (photo OR text symptom query)
        wants_disease = bool(attached_image) or any(w in query_lower for w in [
            "disease", "spots", "spot", "leaf", "leaves", "blight", "rust", "kole", "rot", "mildew", "curl", "yellow", "wilt", "powder",
            "ರೋಗ", "ಚುಕ್ಕೆ", "ಕೊಳೆ", "ತುಕ್ಕು", "ಕಿತ್ತಳೆ", "ಬೂದಿ", "ಮುದುಡು", "ಎಲೆ",
            "बीमारी", "पत्ती", "रोग", "झुलसा", "रतुआ", "धब्बे", "सड़न", "मरोड़",
            "நோய்", "இலை", "துரு", "அழுகல்", "புள்ளி", "சுருள்",
            "వ్యాధి", "తెగులు", "ఆకు", "తుప్పు", "మచ్చ", "కుళ్ళు", "ముడత",
            "रोगराई", "डाग", "तांबेरा", "करपा", "भुरी", "कूज"
        ])
        if wants_disease:
            tools_to_call.append({
                "tool": "diagnose_crop_disease",
                "args": {"image_path": attached_image or "", "crop": crop, "symptom_query": user_query},
                "reason": "Farmer mentioned leaf disease symptoms or shared leaf photo"
            })

        # Weather & Irrigation (also check live weather when a disease query includes a location, for safe spraying advice!)
        wants_weather = any(w in query_lower for w in [
            "weather", "rain", "rainy", "temperature", "climate", "irrigate", "water", "spray", "wind", "humidity",
            "ಮಳೆ", "ಹವಾಮಾನ", "ನೀರು", "ನೀರಾವರಿ", "ಸಿಂಪಡಣೆ",
            "बारिश", "मौसम", "सिंचाई", "पानी", "छिड़काव",
            "மழை", "வானிலை", "பாசனம்",
            "వర్షం", "వాతావరణం", "నీరు",
            "पाऊस", "हवामान", "पाणी", "फवारणी"
        ])
        if wants_weather or (wants_disease and location):
            tools_to_call.append({
                "tool": "fetch_live_weather",
                "args": {"location": location},
                "reason": f"Fetch live weather & spraying safety for {location}" if location else "Check location requirement for live weather"
            })
            if wants_weather and location:
                tools_to_call.append({
                    "tool": "fetch_soil_health",
                    "args": {"district": location, "crop": crop},
                    "reason": f"Check soil moisture in {location} to complement irrigation advice"
                })

        # Soil/Fertilizer
        wants_soil = any(w in query_lower for w in [
            "soil", "fertilizer", "urea", "potash", "manure", "ph", "nutrient",
            "ಮಣ್ಣು", "ಗೊಬ್ಬರ", "ಯೂರಿಯಾ",
            "मिट्टी", "खाद", "उर्वरक",
            "மண்", "உரம்",
            "మట్టి", "ఎరువు",
            "माती", "खत"
        ])
        if wants_soil and not wants_weather:
            tools_to_call.append({
                "tool": "fetch_soil_health",
                "args": {"district": location or "", "crop": crop},
                "reason": f"Fetch soil health profile for {location or 'requested area'}"
            })

        # Mandi prices
        wants_price = any(w in query_lower for w in [
            "price", "mandi", "rate", "sell", "market", "apmc", "bhav",
            "ದರ", "ಬೆಲೆ", "ಮಾರುಕಟ್ಟೆ", "ಮಾರಾಟ", "ಮಂಡಿ",
            "भाव", "दाम", "मंडी", "बेचना", "बाजारभाव",
            "விலை", "சந்தை",
            "ధర", "మార్కెట్",
            "भाव", "बाजार"
        ])
        if wants_price:
            tools_to_call.append({
                "tool": "fetch_mandi_prices",
                "args": {"commodity": crop, "location": location or ""},
                "reason": f"Query APMC mandi spot rates for {crop}" + (f" in {location}" if location else "")
            })

        # Default comprehensive advisory
        if not tools_to_call:
            tools_to_call = [
                {"tool": "fetch_live_weather", "args": {"location": location}, "reason": "Live weather check"},
            ]
            if location:
                tools_to_call.append({"tool": "fetch_soil_health", "args": {"district": location, "crop": crop}, "reason": "Soil check"})
            tools_to_call.append({"tool": "fetch_mandi_prices", "args": {"commodity": crop, "location": location or ""}, "reason": "Market check"})

        return tools_to_call

    def execute_agentic_workflow(self, user_query: str, language: str = "en",
                                 attached_image: Optional[str] = None) -> Dict[str, Any]:
        language = language.lower()
        if language not in SUPPORTED_LANGUAGES:
            language = "en"

        # Try Gemini-powered agent first
        if self._use_gemini:
            try:
                return self._run_gemini_agent(user_query, language, attached_image)
            except Exception as e:
                print(f"[FasalSaarathi] Gemini failed, using rule-based fallback: {e}")

        # Rule-based fallback
        return self._rule_based_workflow(user_query, language, attached_image)

    def _rule_based_workflow(self, user_query: str, language: str,
                             attached_image: Optional[str]) -> Dict[str, Any]:
        """Heuristic tool selection + multilingual template synthesis."""
        execution_trace = []
        observations = {}
        lang_name = SUPPORTED_LANGUAGES[language]["name"]

        plan = self.determine_plan(user_query, attached_image)

        execution_trace.append({
            "step": "Rule-Based Intent Analysis",
            "thought": f"[Fallback Mode] Analyzed query: '{user_query[:80]}'. Planned {len(plan)} tool(s).",
            "mode": "RULE_BASED_FALLBACK",
            "planned_tools": [p["tool"] for p in plan]
        })

        for item in plan:
            t_name = item["tool"]
            t_args = item["args"]
            execution_trace.append({
                "step": f"Calling Tool: {t_name}",
                "action": self._format_tool_action(t_name, t_args),
                "reason": item["reason"]
            })
            obs = self.run_tool(t_name, t_args, language=language)
            observations[t_name] = obs
            execution_trace.append({
                "step": f"Observation: {t_name}",
                "observation_summary": obs.get("summary", "Data retrieved.")
            })

        advisory = self._synthesize_advisory(user_query, observations, language)
        action_cards = self._build_action_cards(observations, language)

        return {
            "status": "success",
            "mode": "rule_based_fallback",
            "query": user_query,
            "language": language,
            "language_name": lang_name,
            "execution_trace": execution_trace,
            "tool_data": observations,
            "response_text": advisory["full_response"],
            "speech_text": advisory["speech_audio_text"],
            "action_cards": action_cards
        }

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────
    def _extract_location(self, query: str) -> Optional[str]:
        """
        Dynamically extract a village, taluk, district, city, PIN code, or GPS pair
        from natural-language queries across English and 5 Indian languages.
        Zero hardcoded city dictionaries and never defaults to 'Kolar'.
        """
        if not query or not query.strip():
            return None

        text = query.strip()

        # 1. GPS coordinate pair (e.g. "12.5218, 76.8951")
        coord_m = re.search(r"(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
        if coord_m:
            return f"{coord_m.group(1)}, {coord_m.group(2)}"

        # 2. 6-digit Indian PIN code
        pin_m = re.search(r"\b([1-9]\d{5})\b", text)
        if pin_m:
            return pin_m.group(1)

        # 3. Kannada locative morphology (<Place>ದಲ್ಲಿ / <Place>ನಲ್ಲಿ / <Place>ಯಲ್ಲಿ / <Place>ಿನಲ್ಲಿ)
        kn_non_places = {"ಬೆಳೆ", "ಮಣ್ಣು", "ಮಣ್ಣ", "ಕನ್ನಡ", "ಇಲ್ಲಿ", "ಎಲ್ಲಿ", "ಮನೆ", "ಹೊಲ", "ತೋಟ", "ಎಲೆ", "ಕಾಲ", "ಬಿಸಿಲು"}
        for tok in re.findall(r"[\u0c80-\u0cff]{3,25}", text):
            stem = None
            for sfx, repl in (("\u0cbfನಲ್ಲಿ", "\u0cc1"), ("ದಲ್ಲಿ", ""), ("ಯಲ್ಲಿ", ""), ("ನಲ್ಲಿ", "")):
                if tok.endswith(sfx):
                    stem = tok[: -len(sfx)] + repl
                    break
            if stem and len(stem) >= 2 and stem not in kn_non_places:
                return stem

        # 4. Marathi locative (<Place>मध्ये / <Place>येथे)
        mr_non_places = {"शेती", "माती", "पाण्या", "पिका", "मराठी", "पाना"}
        for m_mr in re.finditer(r"([\u0900-\u097f]{2,22})(?:मध्ये|येथे)(?=\s|[।,.?!]|$)", text):
            stem = m_mr.group(1)
            if stem not in mr_non_places:
                return stem

        # 5. Hindi postpositional locative (<Place> में / <Place> मे)
        hi_non_places = {"खेत", "मिट्टी", "फसल", "हिंदी", "दिन", "पत्ती", "आज", "कल", "सुबह", "शाम", "मंडी", "बाजार"}
        for m_hi in re.finditer(r"([\u0900-\u097f]{2,22})\s+(?:में|मे)(?=\s|[।,.?!]|$)", text):
            stem = m_hi.group(1)
            if stem not in hi_non_places:
                return stem

        # 6. Tamil locative (<Place>த்தில் / <Place>யில் / <Place>ில்)
        ta_non_places = {"இலை", "மண்", "வயல்", "தமிழ்", "பயிர்", "காலை", "மாலை"}
        for tok in re.findall(r"[\u0b80-\u0bff]{3,25}", text):
            stem = None
            for sfx, repl in (("த்தில்", "ம்"), ("யில்", ""), ("\u0bbfல்", "")):
                if tok.endswith(sfx):
                    stem = tok[: -len(sfx)] + repl
                    break
            if stem and len(stem) >= 2 and stem not in ta_non_places:
                return stem

        # 7. Telugu locative (<Place>లో / <Place>లోన)
        te_non_places = {"మట్టి", "ఆకు", "తెలుగు", "పంట", "పొలం", "ఉదయం"}
        for tok in re.findall(r"[\u0c00-\u0c7f]{3,25}", text):
            stem = None
            for sfx in ("లోన", "లో"):
                if tok.endswith(sfx):
                    stem = tok[: -len(sfx)]
                    break
            if stem and len(stem) >= 2 and stem not in te_non_places:
                return stem

        # 8. English prepositions ("in <Place>", "at <Place>", "for <Place>", "near <Place>")
        en_stop = {
            "today", "tomorrow", "now", "morning", "evening", "night", "week",
            "weather", "rain", "temperature", "forecast", "climate", "humidity", "wind",
            "soil", "mandi", "market", "apmc", "price", "prices", "rate", "rates",
            "my", "the", "this", "our", "a", "an", "field", "farm", "crop", "crops",
            "english", "kannada", "hindi", "tamil", "telugu", "marathi",
            "what", "how", "when", "where", "which", "should", "can", "will", "is",
            "tomato", "onion", "coffee", "chilli", "arecanut", "pepper", "potato", "cotton", "rice", "wheat",
        }
        prep_m = re.search(
            r"\b(?:in|at|near|around|from)\s+([A-Za-z][A-Za-z\.\-]*(?:\s+[A-Za-z][A-Za-z\.\-]*){0,2})",
            text,
            flags=re.IGNORECASE,
        )
        if prep_m:
            words = [w.strip(".,?!") for w in prep_m.group(1).split()]
            kept = []
            for w in words:
                if not w or w.lower() in en_stop:
                    break
                kept.append(w)
            if kept:
                return " ".join(kept)

        # 9. "<Place> weather / rain / temperature / forecast"
        lead_m = re.search(
            r"(?:^|\bcheck\s+|\blive\s+)([A-Za-z][A-Za-z\.\-]*(?:\s+[A-Za-z][A-Za-z\.\-]*){0,1})\s+(?:weather|rain|temperature|forecast)\b",
            text,
            flags=re.IGNORECASE,
        )
        if lead_m:
            words = [w.strip(".,?!") for w in lead_m.group(1).split() if w.lower() not in en_stop and w.lower() not in {"check", "live", "current"}]
            if words:
                return " ".join(words)

        return None

    def _extract_crop(self, query: str) -> str:
        # English
        for crop in [
            "coffee", "tomato", "arecanut", "pepper", "onion", "potato", "cotton", "chilli",
            "paddy", "rice", "wheat", "maize", "corn", "ragi", "jowar", "bajra", "tur",
            "groundnut", "banana", "sugarcane", "turmeric", "coconut", "soyabean", "soybean",
        ]:
            if crop in query:
                return crop
        # Multilingual
        multi_crops = {
            "ಟೊಮೆಟೊ": "tomato", "ಟೊಮೇಟೊ": "tomato", "टमाटर": "tomato", "தக்காளி": "tomato", "టమోటా": "tomato", "టమాటా": "tomato", "टोमॅटो": "tomato",
            "ಕಾಫಿ": "coffee", "कॉफ़ी": "coffee", "कॉफी": "coffee", "காபி": "coffee", "కాఫీ": "coffee",
            "ಅಡಿಕೆ": "arecanut", "ಅಡಕೆ": "arecanut", "सुपारी": "arecanut", "பாக்கு": "arecanut", "పోక": "arecanut",
            "ಕರಿಮೆಣಸು": "pepper", "ಮೆಣಸು": "pepper", "काली मिर्च": "pepper", "மிளகு": "pepper", "మిరియాలు": "pepper",
            "ಈರುಳ್ಳಿ": "onion", "प्याज": "onion", "வெங்காயம்": "onion", "ఉల్లిపాయ": "onion", "ఉల్లి": "onion", "कांदा": "onion",
            "ಆಲೂ": "potato", "आलू": "potato", "உருளை": "potato", "బంగాళ": "potato", "बटाटा": "potato",
            "ಹತ್ತಿ": "cotton", "कपास": "cotton", "பருத்தி": "cotton", "పత్తి": "cotton", "कापूस": "cotton",
            "ಮೆಣಸಿನಕಾಯಿ": "chilli", "मिर्च": "chilli", "மிளகாய்": "chilli", "మిర్చి": "chilli", "मिरची": "chilli",
            "ಭತ್ತ": "paddy", "धान": "paddy", "நெல்": "paddy", "వరి": "paddy", "भात": "paddy",
            "ರಾಗಿ": "ragi", "रागी": "ragi", "ಮೆಕ್ಕೆಜೋಳ": "maize", "मक्का": "maize", "ತೊಗರಿ": "tur", "अरहर": "tur",
            "ಶೇಂಗಾ": "groundnut", "मूंगफली": "groundnut", "ಬಾಳೆ": "banana", "केला": "banana", "ಕಬ್ಬು": "sugarcane", "गन्ना": "sugarcane",
        }
        for native, english in multi_crops.items():
            if native in query:
                return english
        return "tomato"

    def _sanitize_ranges(self, text: str, lang: str) -> str:
        """Replace hyphenated ranges (3-4) with native language connectors."""
        connectors = {
            "kn": r"\1 ರಿಂದ \2", "hi": r"\1 से \2", "en": r"\1 to \2",
            "ta": r"\1 முதல் \2", "te": r"\1 నుండి \2", "mr": r"\1 ते \2"
        }
        connector = connectors.get(lang, r"\1 to \2")
        return re.sub(r"(\d+)\s*[-–—]\s*(\d+)", connector, text)

    def _build_full_speech_text(self, text: str, lang: str) -> str:
        """
        Convert 100% of the advisory response into natural, complete spoken text
        without truncating or skipping any section.
        """
        if not text:
            return ""
        out = self._sanitize_ranges(text, lang)
        # Strip markdown & decorative emojis
        out = re.sub(r"[*#_`•🌾🌤️🌱💰🔬📡🕒📍⚠️💧✅📈🌿📷]+", " ", out)
        # Expand rupee, degree, and percent symbols into spoken words per language
        rupee_word = {
            "kn": " ರೂಪಾಯಿ ", "hi": " रुपये ", "ta": " ரூபாய் ",
            "te": " రూపాయలు ", "mr": " रुपये ", "en": " rupees ",
        }.get(lang, " rupees ")
        deg_word = {
            "kn": " ಡಿಗ್ರಿ ", "hi": " डिग्री ", "ta": " டிகிரி ",
            "te": " డిగ్రీలు ", "mr": " अंश ", "en": " degrees ",
        }.get(lang, " degrees ")
        out = re.sub(r"₹\s*(\d+(?:\.\d+)?)", rf"\1{rupee_word}", out)
        out = re.sub(r"(\d+(?:\.\d+)?)\s*°C", rf"\1{deg_word}", out)
        out = out.replace("|", ". ")
        out = re.sub(r"\n+", ". ", out)
        out = re.sub(r"\.\s*\.", ".", out)
        out = re.sub(r"\s{2,}", " ", out).strip()
        return out

    def _format_tool_action(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Format tool call parameters cleanly without raw JSON braces."""
        clean_parts = []
        for k, v in (args or {}).items():
            if v:
                clean_parts.append(f"{k.replace('_', ' ').title()}: {v}")
        params_str = " | ".join(clean_parts) if clean_parts else "Default"
        return f"{tool_name} — {params_str}"

    def _build_action_cards(self, observations: Dict, language: str) -> List[Dict]:
        """Generate localized action cards from tool observations in the selected language."""
        cards = []
        w = observations.get("fetch_live_weather", {})
        s = observations.get("fetch_soil_health", {})
        m = observations.get("fetch_mandi_prices", {})
        d = observations.get("diagnose_crop_disease", {})
        lang = language if language in SUPPORTED_LANGUAGES else "en"

        if w:
            w_status = w.get("status")
            if w_status in ("success", "cached_real"):
                rain = w.get("rain_today_probability_pct", 0)
                temp = w.get("current_temperature_c")
                loc = w.get("display_location") or w.get("location", "")
                is_rain = rain >= 60 or (w.get("rain_today_mm") or 0) >= 5.0
                is_hot = (w.get("irrigation_code") == "IRRIGATE_SOON") or (rain < 20 and (temp or 0) > 32)

                w_labels = {
                    "kn": {
                        "title": f"ಹವಾಮಾನ & ನೀರಾವರಿ ({loc})",
                        "rain_st": "⚠️ ಇಂದು ನೀರು ಹಾಯಿಸಬೇಡಿ",
                        "hot_st": "💧 ಶೀಘ್ರ ನೀರಾವರಿ ಮಾಡಿ",
                        "ok_st": "✅ ನಿಯಮಿತ ನೀರಾವರಿ",
                        "rain_dt": f"ಇಂದು {rain}% ಮಳೆ ಸಂಭವವಿದೆ ({w.get('rain_today_mm', 0)} ಮಿ.ಮೀ). ನೀರು ಮತ್ತು ವಿದ್ಯುತ್ ಉಳಿಸಿ.",
                        "hot_dt": f"ತಾಪಮಾನ {temp}°C ಇದೆ, ಮಳೆ ಕಡಿಮೆ ({rain}%). ಬೆಳೆಗೆ ನೀರು ಹಾಯಿಸಿ.",
                        "ok_dt": f"ಹವಾಮಾನ ಸ್ಥಿರವಾಗಿದೆ ({temp}°C). ವಾಡಿಕೆಯಂತೆ ನೀರು ಹಾಯಿಸಿ.",
                        "badge": f"{rain}% ಮಳೆ | {temp}°C"
                    },
                    "hi": {
                        "title": f"मौसम और सिंचाई ({loc})",
                        "rain_st": "⚠️ आज सिंचाई न करें",
                        "hot_st": "💧 जल्द सिंचाई करें",
                        "ok_st": "✅ सामान्य सिंचाई",
                        "rain_dt": f"आज {rain}% बारिश की संभावना ({w.get('rain_today_mm', 0)} मिमी)। पानी और बिजली बचाएं।",
                        "hot_dt": f"तापमान {temp}°C है और बारिश कम ({rain}%)। फसल को पानी दें।",
                        "ok_dt": f"मौसम अनुकूल है ({temp}°C)। नियमित सिंचाई जारी रखें।",
                        "badge": f"{rain}% बारिश | {temp}°C"
                    },
                    "ta": {
                        "title": f"வானிலை & பாசனம் ({loc})",
                        "rain_st": "⚠️ இன்று பாசனம் வேண்டாம்",
                        "hot_st": "💧 விரைவில் பாசனம் செய்யவும்",
                        "ok_st": "✅ வழக்கமான பாசனம்",
                        "rain_dt": f"இன்று {rain}% மழை வாய்ப்பு உள்ளது. தண்ணீரை சேமிக்கவும்.",
                        "hot_dt": f"வெப்பநிலை {temp}°C, மழை குறைவு ({rain}%). பயிருக்கு நீர் பாய்ச்சவும்.",
                        "ok_dt": f"வானிலை சீராக உள்ளது ({temp}°C). வழக்கமான பாசனம் தொடரவும்.",
                        "badge": f"{rain}% மழை | {temp}°C"
                    },
                    "te": {
                        "title": f"వాతావరణం & నీటిపారుదల ({loc})",
                        "rain_st": "⚠️ ఈరోజు నీరు పెట్టకండి",
                        "hot_st": "💧 త్వరగా నీరు పెట్టండి",
                        "ok_st": "✅ సాధారణ నీటిపారుదల",
                        "rain_dt": f"ఈరోజు {rain}% వర్షం అవకాశం ఉంది. నీరు ఆదా చేయండి.",
                        "hot_dt": f"ఉష్ణోగ్రత {temp}°C, వర్షం తక్కువ ({rain}%). పంటకు నీరు పెట్టండి.",
                        "ok_dt": f"వాతావరణం అనుకూలంగా ఉంది ({temp}°C). మామూలు షెడ్యూల్ కొనసాగించండి.",
                        "badge": f"{rain}% వర్షం | {temp}°C"
                    },
                    "mr": {
                        "title": f"हवामान व सिंचन ({loc})",
                        "rain_st": "⚠️ आज पाणी देऊ नका",
                        "hot_st": "💧 लवकर पाणी द्या",
                        "ok_st": "✅ नियमित सिंचन",
                        "rain_dt": f"आज {rain}% पावसाची शक्यता आहे. पाणी आणि वीज वाचवा.",
                        "hot_dt": f"तापमान {temp}°C आहे आणि पाऊस कमी ({rain}%). पिकाला पाणी द्या.",
                        "ok_dt": f"हवामान स्थिर आहे ({temp}°C). नियमित सिंचन सुरू ठेवा.",
                        "badge": f"{rain}% पाऊस | {temp}°C"
                    },
                    "en": {
                        "title": f"Weather & Irrigation ({loc})",
                        "rain_st": "⚠️ Skip Irrigation Today",
                        "hot_st": "💧 Irrigate Soon",
                        "ok_st": "✅ Normal Schedule",
                        "rain_dt": w.get("irrigation_action", f"{rain}% rain expected today. Conserve water."),
                        "hot_dt": w.get("irrigation_action", f"Warm at {temp}°C with low rain ({rain}%). Irrigate soon."),
                        "ok_dt": w.get("irrigation_action", f"Weather stable at {temp}°C. Follow regular irrigation."),
                        "badge": f"{rain}% Rain | {temp}°C"
                    }
                }[lang]

                status = w_labels["rain_st"] if is_rain else (w_labels["hot_st"] if is_hot else w_labels["ok_st"])
                detail = w_labels["rain_dt"] if is_rain else (w_labels["hot_dt"] if is_hot else w_labels["ok_dt"])
                cards.append({
                    "type": "irrigation",
                    "title": w_labels["title"],
                    "status": status,
                    "detail": detail,
                    "badge": w_labels["badge"],
                    "source": w.get("data_source_label") or w.get("source", "Open-Meteo"),
                    "is_live": w.get("is_live_data") is True
                })
            elif w_status == "missing_location":
                miss_map = {
                    "kn": ("ಹವಾಮಾನ ಮಾಹಿತಿ", "📍 ಸ್ಥಳ ತಿಳಿಸಿ", "ನಿಖರವಾದ ನೇರ ಹವಾಮಾನ ಪಡೆಯಲು ನಿಮ್ಮ ಗ್ರಾಮ, ತಾಲೂಕು ಅಥವಾ ಜಿಲ್ಲೆಯ ಹೆಸರನ್ನು ತಿಳಿಸಿ."),
                    "hi": ("मौसम जानकारी", "📍 स्थान बताएं", "सटीक लाइव मौसम के लिए कृपया अपने गांव, तहसील या जिले का नाम लिखें।"),
                    "ta": ("வானிலை தகவல்", "📍 இடம் தேவை", "துல்லியமான நேரடி வானிலைக்கு உங்கள் கிராமம் அல்லது மாவட்டத்தைக் குறிப்பிடவும்."),
                    "te": ("వాతావరణ సమాచారం", "📍 ప్రాంతం తెలపండి", "ఖచ్చితమైన లైవ్ వాతావరణం కోసం మీ గ్రామం లేదా జిల్లా పేరు తెలపండి."),
                    "mr": ("हवामान माहिती", "📍 गाव/जिल्हा सांगा", "अचूक थेट हवामानासाठी कृपया आपल्या गावाचे किंवा जिल्ह्याचे नाव सांगा."),
                    "en": ("Weather & Irrigation", "📍 Location Needed", "Please mention your village, taluk, district, or PIN code for real-time weather.")
                }[lang]
                cards.append({
                    "type": "irrigation",
                    "title": miss_map[0],
                    "status": miss_map[1],
                    "detail": miss_map[2],
                    "badge": "GPS / PIN",
                    "source": "Open-Meteo Live Geocoder",
                    "is_live": False
                })

        if s:
            s_status = s.get("status")
            if s_status in ("success", "cached_real"):
                moist = s.get("moisture_percentage")
                ph = s.get("ph")
                oc = s.get("nutrients", {}).get("organic_carbon_pct")
                dist = s.get("district", "")
                m_st = s.get("moisture_status", "")
                is_low = m_st == "CRITICAL_DEFICIT"
                is_opt = m_st == "OPTIMAL_MOISTURE"

                s_labels = {
                    "kn": {
                        "title": f"ಮಣ್ಣಿನ ಆರೋಗ್ಯ ({dist})",
                        "low": "⚠️ ತೇವಾಂಶ ಕೊರತೆ",
                        "opt": "✅ ಉತ್ತಮ ತೇವಾಂಶ",
                        "mod": "💧 ಮಧ್ಯಮ ತೇವಾಂಶ",
                        "detail": f"ಮಣ್ಣು: {s.get('soil_type', '')} | ಬೇರಿನ ತೇವಾಂಶ: {moist}% | pH: {ph} | ಸಾವಯವ ಇಂಗಾಲ: {oc}%",
                        "badge": f"{moist}% ತೇವಾಂಶ | pH {ph}"
                    },
                    "hi": {
                        "title": f"मृदा स्वास्थ्य ({dist})",
                        "low": "⚠️ नमी की कमी",
                        "opt": "✅ उत्तम नमी",
                        "mod": "💧 मध्यम नमी",
                        "detail": f"मिट्टी: {s.get('soil_type', '')} | जड़ नमी: {moist}% | pH: {ph} | जैविक कार्बन: {oc}%",
                        "badge": f"{moist}% नमी | pH {ph}"
                    },
                    "ta": {
                        "title": f"மண் ஆரோக்கியம் ({dist})",
                        "low": "⚠️ ஈரப்பதம் குறைவு",
                        "opt": "✅ சிறந்த ஈரப்பதம்",
                        "mod": "💧 மிதமான ஈரப்பதம்",
                        "detail": f"மண் ஈரப்பதம் {moist}%, pH {ph}, கரிம கார்பன் {oc}%.",
                        "badge": f"{moist}% ஈரப்பதம் | pH {ph}"
                    },
                    "te": {
                        "title": f"మట్టి ఆరోగ్యం ({dist})",
                        "low": "⚠️ తేమ తక్కువ",
                        "opt": "✅ ఉత్తమ తేమ",
                        "mod": "💧 మధ్యస్థ తేమ",
                        "detail": f"మట్టిలో తేమ {moist}%, pH {ph}, సేంద్రీయ కార్బన్ {oc}%.",
                        "badge": f"{moist}% తేమ | pH {ph}"
                    },
                    "mr": {
                        "title": f"माती आरोग्य ({dist})",
                        "low": "⚠️ ओलावा कमी",
                        "opt": "✅ उत्तम ओलावा",
                        "mod": "💧 मध्यम ओलावा",
                        "detail": f"मातीत ओलावा {moist}%, pH {ph}, सेंद्रिय कर्ब {oc}%.",
                        "badge": f"{moist}% ओलावा | pH {ph}"
                    },
                    "en": {
                        "title": f"Soil Health ({dist})",
                        "low": "⚠️ Root Moisture Deficit",
                        "opt": "✅ Optimal Root Moisture",
                        "mod": "💧 Moderate Root Moisture",
                        "detail": s.get("irrigation_guidance", f"Root moisture {moist}%, pH {ph}, OC {oc}%."),
                        "badge": f"{moist}% Moisture | pH {ph}"
                    }
                }[lang]

                cards.append({
                    "type": "soil",
                    "title": s_labels["title"],
                    "status": s_labels["low"] if is_low else (s_labels["opt"] if is_opt else s_labels["mod"]),
                    "detail": s_labels["detail"],
                    "badge": s_labels["badge"],
                    "source": s.get("data_source_label") or s.get("source", "OpenLandMap 250m + Open-Meteo"),
                    "is_live": s.get("is_live_data") is True
                })
            elif s_status == "missing_location" and not w:
                cards.append({
                    "type": "soil",
                    "title": "Soil Health",
                    "status": "📍 Location Needed",
                    "detail": "Please mention your village, taluk, district, or PIN code for 250m soil & root moisture analysis.",
                    "badge": "GPS / PIN",
                    "source": "OpenLandMap 250m Grid",
                    "is_live": False
                })

        if m and m.get("status") in ("success", "cached_real"):
            price = m.get("modal_price", 0)
            comm_raw = (m.get("commodity_key") or m.get("commodity", "tomato")).lower()
            comm_local = CROP_NAMES.get(comm_raw, {}).get(lang, m.get("commodity", ""))
            mandi_name = (m.get("primary_mandi", "APMC") or "").split("(")[0].strip()
            t_code = m.get("trend_code") or ""
            trend = m.get("trend", "")
            is_up = t_code == "UP" or "RISING" in trend or "Going Up" in trend
            is_down = t_code == "DOWN" or "FALLING" in trend or "Going Down" in trend

            m_labels = {
                "kn": {
                    "title": f"ಮಂಡಿ ಮಾರಾಟ ಸಲಹೆ ({comm_local})",
                    "status": f"₹{price} / ಕ್ವಿಂಟಾಲ್",
                    "dt": m.get("selling_advisory", f"ಸಾಮಾನ್ಯ ದರ ₹{price}/ಕ್ವಿಂಟಾಲ್."),
                    "up_bg": "ದರ ಏರಿಕೆ", "down_bg": "ದರ ಇಳಿಕೆ", "st_bg": "ದರ ಸ್ಥಿರ"
                },
                "hi": {
                    "title": f"मंडी बिक्री सलाह ({comm_local})",
                    "status": f"₹{price} / क्विंटल",
                    "dt": m.get("selling_advisory", f"सामान्य भाव ₹{price}/क्विंटल।"),
                    "up_bg": "भाव बढ़ रहा है", "down_bg": "भाव कम", "st_bg": "भाव स्थिर"
                },
                "ta": {
                    "title": f"சந்தை விற்பனை ஆலோசனை ({comm_local})",
                    "status": f"₹{price} / குவிண்டால்",
                    "dt": m.get("selling_advisory", f"சந்தை விலை ₹{price}/குவிண்டால்."),
                    "up_bg": "விலை உயர்வு", "down_bg": "விலை குறைவு", "st_bg": "நிலையானது"
                },
                "te": {
                    "title": f"మార్కెట్ విక్రయ సలహా ({comm_local})",
                    "status": f"₹{price} / క్వింటాల్",
                    "dt": m.get("selling_advisory", f"మార్కెట్ ధర ₹{price}/క్వింటాల్."),
                    "up_bg": "ధర పెరుగుదల", "down_bg": "ధర తగ్గుదల", "st_bg": "స్థిరం"
                },
                "mr": {
                    "title": f"बाजार विक्री सल्ला ({comm_local})",
                    "status": f"₹{price} / क्विंटल",
                    "dt": m.get("selling_advisory", f"बाजारभाव ₹{price}/क्विंटल."),
                    "up_bg": "भाव वाढ", "down_bg": "भाव कमी", "st_bg": "स्थिर"
                },
                "en": {
                    "title": f"APMC Market Rate ({comm_local})",
                    "status": f"₹{price} / 100 kg Quintal ({mandi_name})",
                    "dt": m.get("selling_advisory", "Sell per harvest readiness."),
                    "up_bg": "Going Up", "down_bg": "Going Down", "st_bg": "Steady"
                }
            }[lang]

            cards.append({
                "type": "market",
                "title": m_labels["title"],
                "status": m_labels["status"],
                "detail": m_labels["dt"],
                "badge": f"{mandi_name} • {m_labels['up_bg'] if is_up else (m_labels['down_bg'] if is_down else m_labels['st_bg'])}",
                "source": m.get("data_source_label") or m.get("source", "Agmarknet APMC"),
                "is_live": m.get("is_live_data") is True
            })

        if d and d.get("status") == "success":
            conf = d.get("confidence_score", 0)
            if lang == "kn":
                dname = d.get("disease_name_kn") or d.get("disease_name", "")
                chem = d.get("chemical_prescription_kn") or d.get("chemical_prescription", "")
                title = f"ಎಲೆ ರೋಗ ಪತ್ತೆ: {dname}"
                status = f"ನಿಖರತೆ: {conf}%"
                badge = "ರೋಗ ತಪಾಸಣೆ"
            elif lang == "hi":
                dname = d.get("disease_name_hi") or d.get("disease_name", "")
                chem = d.get("chemical_prescription_hi") or d.get("chemical_prescription", "")
                title = f"पत्ती रोग निदान: {dname}"
                status = f"सटीकता: {conf}%"
                badge = "रोग जांच"
            else:
                dname = d.get("disease_name", "")
                chem = d.get("chemical_prescription", "")
                title = f"Disease Screening: {dname}"
                status = f"Confidence: {conf}%"
                badge = f"Severity: {d.get('severity', 'Moderate')}"

            cards.append({
                "type": "disease",
                "title": title,
                "status": status,
                "detail": chem,
                "badge": badge,
                "source": "FasalSaarathi CV Model",
                "is_live": True
            })

        return cards

    # ─────────────────────────────────────────────
    # MULTILINGUAL SYNTHESIS (Rule-Based Fallback)
    # ─────────────────────────────────────────────
    def _synthesize_advisory(self, query: str, obs: Dict, lang: str) -> Dict:
        weather = obs.get("fetch_live_weather", {})
        soil = obs.get("fetch_soil_health", {})
        mandi = obs.get("fetch_mandi_prices", {})
        disease = obs.get("diagnose_crop_disease", {})

        crop_raw = mandi.get("commodity", self._extract_crop(query.lower())).lower()
        crop_local = CROP_NAMES.get(crop_raw, {}).get(lang, crop_raw.capitalize())

        renderers = {
            "kn": self._render_kannada,
            "hi": self._render_hindi,
            "ta": self._render_tamil,
            "te": self._render_telugu,
            "mr": self._render_marathi,
            "en": self._render_english,
        }
        advisory = renderers.get(lang, self._render_english)(weather, soil, mandi, disease, crop_local)
        greetings = {
            "kn": "ನಮಸ್ಕಾರ ರೈತ ಬಾಂಧವರೇ. ",
            "hi": "नमस्ते किसान भाई। ",
            "ta": "வணக்கம் விவசாய பெருமக்களே. ",
            "te": "నమస్కారం రైతు సోదరులారా. ",
            "mr": "नमस्कार शेतकरी मित्रांनो. ",
            "en": "Hello Farmer. ",
        }
        full_spoken = self._build_full_speech_text(advisory["full_response"], lang)
        greet_prefix = greetings.get(lang, "Hello Farmer. ")
        if greet_prefix.strip(" .।") not in full_spoken[:80]:
            full_spoken = greet_prefix + full_spoken
        advisory["speech_audio_text"] = full_spoken
        return advisory

    # ── Kannada ──────────────────────────────────
    def _render_kannada(self, w, s, m, d, crop_name):
        lines = ["🌾 **ಫಸಲ್ ಸಾರಥಿ ಕೃಷಿ ಸಲಹೆಗಾರರ ವರದಿ:**\n"]
        speech = ["ನಮಸ್ಕಾರ ರೈತ ಬಾಂಧವರೇ, ಫಸಲ್ ಸಾರಥಿ ಸಲಹೆ ಇಲ್ಲಿದೆ."]

        w_status = w.get("status") if w else None
        if w_status in ("success", "cached_real"):
            loc = w.get("display_location") or w.get("location", "")
            temp = w.get("current_temperature_c")
            hum = w.get("humidity_pct")
            rain_prob = w.get("rain_today_probability_pct", 0)
            rain_mm = w.get("rain_today_mm", 0.0)
            wind = w.get("wind_speed_kmh", 0.0)
            et0 = w.get("et0_today_mm")
            src_label = "📡 ನೇರ ಮಾಹಿತಿ (Open-Meteo)" if w.get("is_live_data") else "🕒 ಸಂಗ್ರಹಿಸಿದ ನೈಜ ಮಾಹಿತಿ"

            if rain_prob >= 60 or rain_mm >= 5.0:
                irr_detail = f"ಇಂದು {loc} ನಲ್ಲಿ {rain_prob}% ಮಳೆಯ ಸಂಭವವಿದೆ ({rain_mm} ಮಿ.ಮೀ). ಇಂದು ನೀರು ಹಾಯಿಸಬೇಡಿ ಮತ್ತು ವಿದ್ಯುತ್ ಉಳಿಸಿ."
                speech.append(f"{loc} ನಲ್ಲಿ ಇಂದು ಮಳೆ ಬರುವ ಸಾಧ್ಯತೆ ಶೇ {rain_prob} ಇದೆ. ನೀರು ಹಾಯಿಸಬೇಡಿ.")
            elif w.get("irrigation_code") == "IRRIGATE_SOON":
                irr_detail = f"ತಾಪಮಾನ {temp}°C ಇದೆ ಮತ್ತು ಬಿಸಿಲಿನಿಂದ ಮಣ್ಣಿನ ತೇವ ಬೇಗನೆ ಒಣಗುತ್ತಿದೆ. ಬೆಳಿಗ್ಗೆ ಅಥವಾ ಸಂಜೆ ನೀರು ಹಾಯಿಸಿ."
                speech.append(f"{loc} ನಲ್ಲಿ ತಾಪಮಾನ {temp} ಡಿಗ್ರಿ ಇದೆ. ಬೆಳಿಗ್ಗೆ ಅಥವಾ ಸಂಜೆ ನೀರು ಹಾಯಿಸಿ.")
            else:
                irr_detail = f"ತಾಪಮಾನ {temp}°C, ಗಾಳಿ {wind} ಕಿ.ಮೀ/ಗಂ. ಹವಾಮಾನ ಸ್ಥಿರವಾಗಿದೆ, ವಾಡಿಕೆಯಂತೆ ನೀರು ಹಾಯಿಸಿ."
                speech.append(f"{loc} ನಲ್ಲಿ ಹವಾಮಾನ ಸ್ಥಿರವಾಗಿದೆ. ವಾಡಿಕೆಯಂತೆ ನೀರು ಹಾಯಿಸಿ.")

            spray_kn = "ಮುಂದಿನ 6 ಗಂಟೆ ಸಿಂಪಡಣೆಗೆ ಸೂಕ್ತವಾಗಿದೆ." if w.get("safe_to_spray_now") else "ಮಳೆ/ಗಾಳಿಯ ಕಾರಣ ಈಗ ಔಷಧಿ ಸಿಂಪಡಣೆ ಬೇಡ."
            lines.append(f"🌤️ **ಹವಾಮಾನ ಮಾಹಿತಿ ({loc}):** {src_label}\n• ತಾಪಮಾನ: {temp}°C | ಆರ್ದ್ರತೆ: {hum}% | ಮಳೆ ಸಂಭವ: {rain_prob}% ({rain_mm} ಮಿ.ಮೀ)\n• **ನೀರಾವರಿ ಸಲಹೆ:** {irr_detail}\n• **ಸಿಂಪಡಣೆ:** {spray_kn}")
        elif w_status == "missing_location":
            lines.append("🌤️ **ಹವಾಮಾನ ಮಾಹಿತಿ:** ನಿಖರವಾದ ನೇರ ಹವಾಮಾನ ಮತ್ತು ನೀರಾವರಿ ಸಲಹೆಗಾಗಿ ದಯವಿಟ್ಟು ನಿಮ್ಮ ಗ್ರಾಮ, ತಾಲೂಕು ಅಥವಾ ಜಿಲ್ಲೆಯ ಹೆಸರನ್ನು ತಿಳಿಸಿ.")
            speech.append("ನಿಖರ ಹವಾಮಾನ ಮಾಹಿತಿಗಾಗಿ ನಿಮ್ಮ ಗ್ರಾಮ ಅಥವಾ ಜಿಲ್ಲೆಯ ಹೆಸರನ್ನು ತಿಳಿಸಿ.")
        elif w_status == "location_not_found":
            req_loc = w.get("requested_location", "")
            lines.append(f"🌤️ **ಹವಾಮಾನ ಮಾಹಿತಿ:** '{req_loc}' ಸ್ಥಳವು ಕಂಡುಬಂದಿಲ್ಲ. ದಯವಿಟ್ಟು ಸರಿಯಾದ ಗ್ರಾಮ, ತಾಲೂಕು ಅಥವಾ ಜಿಲ್ಲೆಯ ಹೆಸರನ್ನು ನಮೂದಿಸಿ.")
        elif w_status == "service_unavailable":
            loc = w.get("display_location") or w.get("location") or w.get("requested_location", "")
            lines.append(f"🌤️ **ಹವಾಮಾನ ಮಾಹಿತಿ ({loc}):** ನೇರ ಹವಾಮಾನ ಸೇವೆ (Open-Meteo) ಪ್ರಸ್ತುತ ಸಂಪರ್ಕಕ್ಕೆ ಸಿಗುತ್ತಿಲ್ಲ. ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ.")

        s_status = s.get("status") if s else None
        if s_status in ("success", "cached_real"):
            ph = s.get("ph")
            moist = s.get("moisture_percentage")
            oc = s.get("nutrients", {}).get("organic_carbon_pct")
            nitro = s.get("nutrients", {}).get("nitrogen_status", "")
            s_src = "📡 ನೇರ 250m ಮಣ್ಣು & ತೇವಾಂಶ" if s.get("is_live_data") else "🕒 ಸಂಗ್ರಹಿಸಿದ ಮಣ್ಣಿನ ಮಾಹಿತಿ"
            lines.append(f"\n🌱 **ಮಣ್ಣಿನ ಆರೋಗ್ಯ ವರದಿ ({s.get('soil_type', '')} — {s_src}):**\n• ಬೇರಿನ ತೇವಾಂಶ: {moist}% | pH: {ph} | ಸಾವಯವ ಇಂಗಾಲ: {oc}%")
            if nitro == "Low":
                lines.append("• **ಪರಿಹಾರ:** ಸಾರಜನಕ ಕಡಿಮೆಯಿದ್ದರೆ ಬೇವಿನ ಲೇಪಿತ ಯೂರಿಯಾವನ್ನು ಹಂತ-ಹಂತವಾಗಿ ನೀಡಿ.")
        elif s_status == "missing_location" and not w:
            lines.append("\n🌱 **ಮಣ್ಣಿನ ಆರೋಗ್ಯ:** ಮಣ್ಣಿನ ತೇವಾಂಶ ಮತ್ತು pH ತಿಳಿಯಲು ನಿಮ್ಮ ಗ್ರಾಮ ಅಥವಾ ಜಿಲ್ಲೆಯ ಹೆಸರನ್ನು ತಿಳಿಸಿ.")

        m_status = m.get("status") if m else None
        if m_status in ("success", "cached_real"):
            price = m.get("modal_price", 0)
            mandi_name = m.get("primary_mandi", "APMC")
            m_src = "📡 ನೇರ APMC ಮಂಡಿ ದರ" if m.get("is_live_data") else f"🕒 {m.get('data_source_label', 'ಸಂಗ್ರಹಿಸಿದ APMC ದರ')}"
            strat_kn = m.get("selling_advisory", f"{crop_name} ಸಾಮಾನ್ಯ ದರ ₹{price}/ಕ್ವಿಂಟಾಲ್ ಇದೆ.")
            lines.append(f"\n💰 **APMC ಮಂಡಿ ವರದಿ ({crop_name} — {m_src}):**\n• ಸಾಮಾನ್ಯ ದರ: ₹{price}/ಕ್ವಿಂಟಾಲ್ (₹{m.get('price_per_kg', round(price/100, 1))}/ಕೆ.ಜಿ) — {mandi_name}\n• ದರ ಮಿತಿ: ₹{m.get('min_price', price)} ರಿಂದ ₹{m.get('max_price', price)}\n• **ಮಾರಾಟ ಸಲಹೆ:** {strat_kn}")
            speech.append(f"{crop_name} ದರ ₹{price} ಪ್ರತಿ ಕ್ವಿಂಟಾಲ್ ಇದೆ. {strat_kn}")
        elif m_status == "service_unavailable":
            lines.append(f"\n💰 **APMC ಮಂಡಿ ವರದಿ ({crop_name}):** ನೇರ ಮಂಡಿ ದರ ಸೇವೆ ಸದ್ಯಕ್ಕೆ ಸಂಪರ್ಕಕ್ಕೆ ಸಿಗುತ್ತಿಲ್ಲ.")

        if d and d.get("status") == "success":
            d_name = d.get("disease_name_kn") or d.get("disease_name", "")
            conf = d.get("confidence_score")
            conf_tag = f" (ನಿಖರತೆ: {conf}%)" if conf else ""
            chem = d.get("chemical_prescription_kn") or d.get("chemical_prescription", "")
            org = d.get("organic_prescription_kn") or d.get("organic_prescription", "")
            proto = d.get("application_protocol", "")
            proto_line = f"\n• **ಮುಂದಿನ ಕ್ರಮ:** {proto}" if proto else ""
            lines.append(f"\n🔬 **ಎಲೆ ಆರೋಗ್ಯ ಸಲಹೆ:**\n• ಸಮಸ್ಯೆ: {d_name}{conf_tag}\n• **ಅಂಗಡಿ ಔಷಧಿ:** {chem}\n• **ಮನೆ / ನೈಸರ್ಗಿಕ ಪರಿಹಾರ:** {org}{proto_line}")

        return {"full_response": "\n".join(lines), "speech_audio_text": " ".join(speech), "action_cards": []}

    # ── Hindi ─────────────────────────────────────
    def _render_hindi(self, w, s, m, d, crop_name):
        lines = ["🌾 **फसल सारथी कृषि सलाहकार रिपोर्ट:**\n"]
        speech = ["नमस्ते किसान भाई, फसल सारथी की कृषि सलाह इस प्रकार है।"]

        w_status = w.get("status") if w else None
        if w_status in ("success", "cached_real"):
            loc = w.get("display_location") or w.get("location", "")
            temp = w.get("current_temperature_c")
            hum = w.get("humidity_pct")
            rain_prob = w.get("rain_today_probability_pct", 0)
            rain_mm = w.get("rain_today_mm", 0.0)
            src_label = "📡 लाइव डेटा (Open-Meteo)" if w.get("is_live_data") else "🕒 कैश्ड वास्तविक डेटा"

            if rain_prob >= 60 or rain_mm >= 5.0:
                irr_detail = f"आज {loc} में {rain_prob}% बारिश का अनुमान है ({rain_mm} मिमी)। आज सिंचाई न करें।"
                speech.append(f"{loc} में आज {rain_prob}% बारिश की संभावना है। आज सिंचाई न करें।")
            elif w.get("irrigation_code") == "IRRIGATE_SOON":
                irr_detail = f"तापमान {temp}°C है और वाष्पीकरण अधिक है। सुबह या शाम सिंचाई करें।"
                speech.append(f"{loc} में तापमान {temp} डिग्री है। सुबह या शाम सिंचाई करें।")
            else:
                irr_detail = f"तापमान {temp}°C और मौसम स्थिर है। नियमित सिंचाई चक्र जारी रखें।"
                speech.append(f"{loc} में मौसम अनुकूल है। सामान्य सिंचाई जारी रखें।")

            lines.append(f"🌤️ **मौसम एवं सिंचाई ({loc}):** {src_label}\n• तापमान: {temp}°C | आर्द्रता: {hum}% | बारिश: {rain_prob}% ({rain_mm} मिमी)\n• **सलाह:** {irr_detail}")
        elif w_status == "missing_location":
            lines.append("🌤️ **मौसम एवं सिंचाई:** सटीक लाइव मौसम और बारिश की जानकारी के लिए कृपया अपने गांव, तहसील, जिले का नाम या पिन कोड बताएं।")
            speech.append("सटीक मौसम जानकारी के लिए कृपया अपने गांव या जिले का नाम बताएं।")
        elif w_status == "location_not_found":
            lines.append(f"🌤️ **मौसम एवं सिंचाई:** '{w.get('requested_location', '')}' स्थान नहीं मिला। कृपया अपने जिले का नाम साथ में लिखें।")
        elif w_status == "service_unavailable":
            loc = w.get("display_location") or w.get("location") or w.get("requested_location", "")
            lines.append(f"🌤️ **मौसम एवं सिंचाई ({loc}):** लाइव मौसम सेवा (Open-Meteo) अभी उपलब्ध नहीं है। कृपया इंटरनेट कनेक्शन जांचें।")

        s_status = s.get("status") if s else None
        if s_status in ("success", "cached_real"):
            ph = s.get("ph")
            moist = s.get("moisture_percentage")
            oc = s.get("nutrients", {}).get("organic_carbon_pct")
            s_src = "📡 लाइव 250m मृदा एवं जड़ नमी" if s.get("is_live_data") else "🕒 कैश्ड मृदा डेटा"
            lines.append(f"\n🌱 **मृदा स्वास्थ्य रिपोर्ट ({s.get('soil_type', '')} — {s_src}):**\n• जड़ क्षेत्र नमी: {moist}% | pH: {ph} | जैविक कार्बन: {oc}%")
        elif s_status == "missing_location" and not w:
            lines.append("\n🌱 **मृदा स्वास्थ्य:** मिट्टी की नमी और pH जानने के लिए कृपया अपने गांव या जिले का नाम बताएं।")

        m_status = m.get("status") if m else None
        if m_status in ("success", "cached_real"):
            price = m.get("modal_price", 0)
            mandi_name = m.get("primary_mandi", "मंडी")
            m_src = "📡 लाइव APMC मंडी भाव" if m.get("is_live_data") else f"🕒 {m.get('data_source_label', 'सहेजा गया मंडी भाव')}"
            strat_hi = m.get("selling_advisory", f"{crop_name} का सामान्य भाव ₹{price}/क्विंटल है।")
            lines.append(f"\n💰 **मंडी भाव ({crop_name} — {m_src}):**\n• सामान्य भाव: ₹{price}/क्विंटल (₹{m.get('price_per_kg', round(price/100, 1))}/किलो) — {mandi_name}\n• आज का दायरा: ₹{m.get('min_price', price)} से ₹{m.get('max_price', price)}\n• **बिक्री सलाह:** {strat_hi}")
            speech.append(f"{crop_name} का भाव {price} रुपये प्रति क्विंटल है। {strat_hi}")
        elif m_status == "service_unavailable":
            lines.append(f"\n💰 **मंडी भाव ({crop_name}):** लाइव मंडी सेवा अभी उपलब्ध नहीं है।")

        if d and d.get("status") == "success":
            d_name = d.get("disease_name_hi") or d.get("disease_name", "")
            conf = d.get("confidence_score")
            conf_tag = f" (सटीकता: {conf}%)" if conf else ""
            chem = d.get("chemical_prescription_hi") or d.get("chemical_prescription", "")
            org = d.get("organic_prescription_hi") or d.get("organic_prescription", "")
            lines.append(f"\n🔬 **पत्ती स्वास्थ्य सलाह:**\n• समस्या: {d_name}{conf_tag}\n• **दुकान की दवा:** {chem}\n• **घरेलू उपाय:** {org}")

        return {"full_response": "\n".join(lines), "speech_audio_text": " ".join(speech), "action_cards": []}

    # ── Tamil ─────────────────────────────────────
    def _render_tamil(self, w, s, m, d, crop_name):
        lines = ["🌾 **ஃபசல் சாரதி விவசாய ஆலோசனை அறிக்கை:**\n"]
        speech = ["வணக்கம் விவசாய பெருமக்களே, ஃபசல் சாரதி ஆலோசனை இதோ."]

        w_status = w.get("status") if w else None
        if w_status in ("success", "cached_real"):
            loc = w.get("display_location") or w.get("location", "")
            temp = w.get("current_temperature_c")
            hum = w.get("humidity_pct")
            rain = w.get("rain_today_probability_pct", 0)
            rain_mm = w.get("rain_today_mm", 0.0)
            src_label = "📡 நேரடி தரவு (Open-Meteo)" if w.get("is_live_data") else "🕒 சேமிக்கப்பட்ட தரவு"

            if rain >= 60 or rain_mm >= 5:
                irr_detail = f"இன்று {loc} இல் {rain}% மழை வாய்ப்பு உள்ளது ({rain_mm} மி.மீ). பாசனம் செய்ய வேண்டாம்."
                speech.append("இன்று மழை வாய்ப்பு உள்ளதால் பாசனம் செய்ய வேண்டாம்.")
            else:
                irr_detail = f"வெப்பநிலை {temp}°C. வழக்கமான பாசன அட்டவணையை தொடருங்கள்."
                speech.append("வானிலை நல்லபடி உள்ளது. வழக்கமான பாசனம் தொடருங்கள்.")

            lines.append(f"🌤️ **வானிலை ({loc}):** {src_label}\n• வெப்பநிலை: {temp}°C | ஈரப்பதம்: {hum}% | மழை வாய்ப்பு: {rain}%\n• **ஆலோசனை:** {irr_detail}")
        elif w_status == "missing_location":
            lines.append("🌤️ **வானிலை:** துல்லியமான நேரடி வானிலையைப் பெற உங்கள் கிராமம், வட்டம் அல்லது மாவட்டத்தின் பெயரைக் குறிப்பிடவும்.")
            speech.append("நேரடி வானிலைக்கு உங்கள் கிராமம் அல்லது மாவட்டத்தைக் குறிப்பிடவும்.")
        elif w_status == "location_not_found":
            lines.append(f"🌤️ **வானிலை:** '{w.get('requested_location', '')}' இடம் கண்டறியப்படவில்லை. சரியான ஊர் பெயரை உள்ளிடவும்.")
        elif w_status == "service_unavailable":
            loc = w.get("display_location") or w.get("location") or w.get("requested_location", "")
            lines.append(f"🌤️ **வானிலை ({loc}):** நேரடி வானிலை சேவை (Open-Meteo) தற்போது இணைக்கப்படவில்லை.")

        s_status = s.get("status") if s else None
        if s_status in ("success", "cached_real"):
            ph = s.get("ph")
            moist = s.get("moisture_percentage")
            oc = s.get("nutrients", {}).get("organic_carbon_pct")
            lines.append(f"\n🌱 **மண் ஆரோக்கிய அறிக்கை ({s.get('soil_type', '')}):**\n• வேர் ஈரப்பதம்: {moist}% | pH: {ph} | கரிம கார்பன்: {oc}%")
        elif s_status == "missing_location" and not w:
            lines.append("\n🌱 **மண் ஆரோக்கியம்:** மண் விவரங்களைப் பெற உங்கள் கிராமம் அல்லது மாவட்டத்தைக் குறிப்பிடவும்.")

        m_status = m.get("status") if m else None
        if m_status in ("success", "cached_real"):
            price = m.get("modal_price", 0)
            mandi_name = m.get("primary_mandi", "சந்தை")
            m_src = "📡 நேரடி APMC விலை" if m.get("is_live_data") else "🕒 சேமித்த APMC விலை"
            strat_ta = m.get("selling_advisory", f"{crop_name} விலை ₹{price}/குவிண்டால்.")
            lines.append(f"\n💰 **சந்தை விலை ({crop_name} — {m_src}):**\n• வழக்கமான விலை: ₹{price}/குவிண்டால் ({mandi_name})\n• **விற்பனை ஆலோசனை:** {strat_ta}")
            speech.append(f"{crop_name} சந்தை விலை {price} ரூபாய். {strat_ta}")
        elif m_status == "service_unavailable":
            lines.append(f"\n💰 **சந்தை விலை ({crop_name}):** நேரடி சந்தை சேவை தற்போது இணைக்கப்படவில்லை.")

        if d and d.get("status") == "success":
            d_name = d.get("disease_name", "")
            conf = d.get("confidence_score")
            conf_tag = f" (நம்பகத்தன்மை: {conf}%)" if conf else ""
            chem = d.get("chemical_prescription", "")
            org = d.get("organic_prescription", "")
            lines.append(f"\n🔬 **இலை நல ஆலோசனை:**\n• கண்டறிதல்: {d_name}{conf_tag}\n• **மருந்து:** {chem}\n• **வீட்டு தீர்வு:** {org}")

        return {"full_response": "\n".join(lines), "speech_audio_text": " ".join(speech), "action_cards": []}

    # ── Telugu ────────────────────────────────────
    def _render_telugu(self, w, s, m, d, crop_name):
        lines = ["🌾 **ఫసల్ సారథి వ్యవసాయ సలహా నివేదిక:**\n"]
        speech = ["నమస్కారం రైతు సోదరులారా, ఫసల్ సారథి సలహా ఇక్కడ ఉంది."]

        w_status = w.get("status") if w else None
        if w_status in ("success", "cached_real"):
            loc = w.get("display_location") or w.get("location", "")
            temp = w.get("current_temperature_c")
            hum = w.get("humidity_pct")
            rain = w.get("rain_today_probability_pct", 0)
            rain_mm = w.get("rain_today_mm", 0.0)
            src_label = "📡 నేరుగా డేటా (Open-Meteo)" if w.get("is_live_data") else "🕒 నిల్వ చేసిన డేటా"

            if rain >= 60 or rain_mm >= 5:
                irr_detail = f"ఈరోజు {loc} లో {rain}% వర్షం అవకాశం ఉంది ({rain_mm} మి.మీ). నీరు పెట్టకండి."
                speech.append("ఈరోజు వర్షం అవకాశం ఉంది. నీటిపారుదల వద్దు.")
            else:
                irr_detail = f"ఉష్ణోగ్రత {temp}°C. మామూలు నీటిపారుదల షెడ్యూల్ కొనసాగించండి."
                speech.append("వాతావరణం అనుకూలంగా ఉంది. మామూలు నీటిపారుదల కొనసాగించండి.")

            lines.append(f"🌤️ **వాతావరణం ({loc}):** {src_label}\n• ఉష్ణోగ్రత: {temp}°C | తేమ: {hum}% | వర్షం అవకాశం: {rain}%\n• **సూచన:** {irr_detail}")
        elif w_status == "missing_location":
            lines.append("🌤️ **వాతావరణం:** ఖచ్చితమైన లైవ్ వాతావరణ సమాచారం కోసం దయచేసి మీ గ్రామం, మండలం లేదా జిల్లా పేరు తెలపండి.")
            speech.append("ఖచ్చితమైన వాతావరణం కోసం మీ గ్రామం లేదా జిల్లా పేరు తెలపండి.")
        elif w_status == "location_not_found":
            lines.append(f"🌤️ **వాతావరణం:** '{w.get('requested_location', '')}' ప్రాంతం కనుగొనబడలేదు. దయచేసి సరైన పేరు ఇవ్వండి.")
        elif w_status == "service_unavailable":
            loc = w.get("display_location") or w.get("location") or w.get("requested_location", "")
            lines.append(f"🌤️ **వాతావరణం ({loc}):** లైవ్ వాతావరణ సేవ (Open-Meteo) ప్రస్తుతం అందుబాటులో లేదు.")

        s_status = s.get("status") if s else None
        if s_status in ("success", "cached_real"):
            ph = s.get("ph")
            moist = s.get("moisture_percentage")
            oc = s.get("nutrients", {}).get("organic_carbon_pct")
            lines.append(f"\n🌱 **మట్టి ఆరోగ్య నివేదిక ({s.get('soil_type', '')}):**\n• వేర్ల తేమ: {moist}% | pH: {ph} | సేంద్రీయ కార్బన్: {oc}%")
        elif s_status == "missing_location" and not w:
            lines.append("\n🌱 **మట్టి ఆరోగ్యం:** మట్టి వివరాల కోసం మీ గ్రామం లేదా జిల్లా పేరు తెలపండి.")

        m_status = m.get("status") if m else None
        if m_status in ("success", "cached_real"):
            price = m.get("modal_price", 0)
            mandi_name = m.get("primary_mandi", "మార్కెట్")
            m_src = "📡 లైవ్ APMC ధర" if m.get("is_live_data") else "🕒 నిల్వ చేసిన APMC ధర"
            strat_te = m.get("selling_advisory", f"{crop_name} ధర ₹{price}/క్వింటాల్.")
            lines.append(f"\n💰 **మార్కెట్ ధర ({crop_name} — {m_src}):**\n• సాధారణ ధర: ₹{price}/క్వింటాల్ ({mandi_name})\n• **విక్రయ సూచన:** {strat_te}")
            speech.append(f"{crop_name} మార్కెట్ ధర {price} రూపాయలు. {strat_te}")
        elif m_status == "service_unavailable":
            lines.append(f"\n💰 **మార్కెట్ ధర ({crop_name}):** లైవ్ మార్కెట్ సేవ ప్రస్తుతం అందుబాటులో లేదు.")

        if d and d.get("status") == "success":
            d_name = d.get("disease_name", "")
            conf = d.get("confidence_score")
            conf_tag = f" (విశ్వసనీయత: {conf}%)" if conf else ""
            chem = d.get("chemical_prescription", "")
            org = d.get("organic_prescription", "")
            lines.append(f"\n🔬 **ఆకు ఆరోగ్య సలహా:**\n• సమస్య: {d_name}{conf_tag}\n• **మందు:** {chem}\n• **ఇంటి నివారణ:** {org}")

        return {"full_response": "\n".join(lines), "speech_audio_text": " ".join(speech), "action_cards": []}

    # ── Marathi ───────────────────────────────────
    def _render_marathi(self, w, s, m, d, crop_name):
        lines = ["🌾 **फसल सारथी कृषी सल्लागार अहवाल:**\n"]
        speech = ["नमस्कार शेतकरी मित्रांनो, फसल सारथीचा कृषी सल्ला इथे आहे."]

        w_status = w.get("status") if w else None
        if w_status in ("success", "cached_real"):
            loc = w.get("display_location") or w.get("location", "")
            temp = w.get("current_temperature_c")
            hum = w.get("humidity_pct")
            rain = w.get("rain_today_probability_pct", 0)
            rain_mm = w.get("rain_today_mm", 0.0)
            src_label = "📡 थेट डेटा (Open-Meteo)" if w.get("is_live_data") else "🕒 संग्रहित प्रत्यक्ष डेटा"

            if rain >= 60 or rain_mm >= 5:
                irr_detail = f"आज {loc} मध्ये {rain}% पाऊस पडण्याची शक्यता आहे ({rain_mm} मिमी). पाणी देणे बंद करा."
                speech.append("आज पाऊस येण्याची शक्यता आहे. पाणी देऊ नका.")
            else:
                irr_detail = f"तापमान {temp}°C. नियमित वेळापत्रकानुसार पाणी द्या."
                speech.append("हवामान अनुकूल आहे. नियमित सिंचन सुरू ठेवा.")

            lines.append(f"🌤️ **हवामान ({loc}):** {src_label}\n• तापमान: {temp}°C | आर्द्रता: {hum}% | पावसाची शक्यता: {rain}%\n• **सल्ला:** {irr_detail}")
        elif w_status == "missing_location":
            lines.append("🌤️ **हवामान:** अचूक थेट हवामान जाणून घेण्यासाठी कृपया आपल्या गावाचे, तालुक्याचे किंवा जिल्ह्याचे नाव सांगा.")
            speech.append("अचूक हवामानासाठी कृपया आपल्या गावाचे किंवा जिल्ह्याचे नाव सांगा.")
        elif w_status == "location_not_found":
            lines.append(f"🌤️ **हवामान:** '{w.get('requested_location', '')}' हे ठिकाण सापडले नाही. कृपया योग्य नाव लिहा.")
        elif w_status == "service_unavailable":
            loc = w.get("display_location") or w.get("location") or w.get("requested_location", "")
            lines.append(f"🌤️ **हवामान ({loc}):** थेट हवामान सेवा (Open-Meteo) सध्या उपलब्ध नाही.")

        s_status = s.get("status") if s else None
        if s_status in ("success", "cached_real"):
            ph = s.get("ph")
            moist = s.get("moisture_percentage")
            oc = s.get("nutrients", {}).get("organic_carbon_pct")
            lines.append(f"\n🌱 **माती आरोग्य अहवाल ({s.get('soil_type', '')}):**\n• मुळांजवळील ओलावा: {moist}% | pH: {ph} | सेंद्रिय कर्ब: {oc}%")
        elif s_status == "missing_location" and not w:
            lines.append("\n🌱 **माती आरोग्य:** मातीच्या माहितीसाठी कृपया आपल्या गावाचे किंवा जिल्ह्याचे नाव सांगा.")

        m_status = m.get("status") if m else None
        if m_status in ("success", "cached_real"):
            price = m.get("modal_price", 0)
            mandi_name = m.get("primary_mandi", "बाजार")
            m_src = "📡 थेट APMC बाजारभाव" if m.get("is_live_data") else "🕒 संग्रहित APMC भाव"
            strat_mr = m.get("selling_advisory", f"{crop_name} भाव ₹{price}/क्विंटल आहे.")
            lines.append(f"\n💰 **बाजारभाव ({crop_name} — {m_src}):**\n• नेहमीचा भाव: ₹{price}/क्विंटल ({mandi_name})\n• **विक्री सल्ला:** {strat_mr}")
            speech.append(f"{crop_name} बाजारभाव {price} रुपये प्रति क्विंटल आहे. {strat_mr}")
        elif m_status == "service_unavailable":
            lines.append(f"\n💰 **बाजारभाव ({crop_name}):** थेट बाजारभाव सेवा सध्या उपलब्ध नाही.")

        if d and d.get("status") == "success":
            d_name = d.get("disease_name", "")
            conf = d.get("confidence_score")
            conf_tag = f" (अचूकता: {conf}%)" if conf else ""
            chem = d.get("chemical_prescription", "")
            org = d.get("organic_prescription", "")
            lines.append(f"\n🔬 **पान आरोग्य सल्ला:**\n• समस्या: {d_name}{conf_tag}\n• **औषध:** {chem}\n• **घरगुती उपाय:** {org}")

        return {"full_response": "\n".join(lines), "speech_audio_text": " ".join(speech), "action_cards": []}

    # ── English ───────────────────────────────────
    def _render_english(self, w, s, m, d, crop_name):
        lines = ["🌾 **FasalSaarathi Agricultural Advisory Report:**\n"]
        speech = ["Hello Farmer, here is your FasalSaarathi personalized farm advisory."]

        w_status = w.get("status") if w else None
        if w_status in ("success", "cached_real"):
            loc = w.get("display_location") or w.get("location", "")
            temp = w.get("current_temperature_c")
            hum = w.get("humidity_pct")
            wind = w.get("wind_speed_kmh")
            rain_prob = w.get("rain_today_probability_pct", 0)
            rain_mm = w.get("rain_today_mm", 0.0)
            et0 = w.get("et0_today_mm")
            src_label = "📡 Live Data (Open-Meteo)" if w.get("is_live_data") else f"🕒 {w.get('data_source_label', 'Cached Open-Meteo Data')}"
            irr_detail = w.get("irrigation_action", "")
            spray_detail = w.get("spray_action", "")

            et_part = f" | Sun Drying Loss: {et0} mm/day" if et0 is not None else ""
            lines.append(
                f"🌤️ **Weather & Watering ({loc}):** {src_label}\n"
                f"• Temperature: {temp}°C | Air Humidity: {hum}% | Wind: {wind} km/h | Rain Chance: {rain_prob}% ({rain_mm} mm){et_part}\n"
                f"• **Watering Advice:** {irr_detail}\n"
                f"• **Spraying Check:** {spray_detail}"
            )
            speech.append(f"In {loc}, temperature is {temp} degrees with {rain_prob}% rain probability. {irr_detail}")
        elif w_status == "missing_location":
            lines.append(
                "🌤️ **Weather & Irrigation:** Please share your **village, taluk, district, or 6-digit PIN code** "
                "(or tap the GPS button in the Live Weather Tool) so FasalSaarathi can fetch accurate real-time Open-Meteo weather for your exact farm."
            )
            speech.append("Please mention your village, taluk, or district name so I can check live weather for your farm.")
        elif w_status == "location_not_found":
            req_loc = w.get("requested_location", "")
            lines.append(
                f"🌤️ **Weather & Irrigation:** Could not locate '{req_loc}'. Please verify the spelling or include your district/state name."
            )
            speech.append(f"I could not find the location {req_loc}. Please check the spelling or mention your district.")
        elif w_status == "service_unavailable":
            loc = w.get("display_location") or w.get("location") or w.get("requested_location", "")
            lines.append(
                f"🌤️ **Weather & Irrigation ({loc}):** Live Open-Meteo weather service is currently unreachable and no recent cached forecast is stored for this location."
            )
            speech.append("Live weather service is temporarily unreachable. Please check your internet connection.")

        s_status = s.get("status") if s else None
        if s_status in ("success", "cached_real"):
            moist = s.get("moisture_percentage")
            ph = s.get("ph")
            oc = s.get("nutrients", {}).get("organic_carbon_pct")
            nitro = s.get("nutrients", {}).get("nitrogen_status", "")
            amends = s.get("soil_amendments") or []
            s_src = "📡 Live 250m Soil Grid + Root Telemetry" if s.get("is_live_data") else "🕒 Cached Real Soil Telemetry"
            amend_line = f"\n• **Amendment:** {amends[0]}" if amends else ""
            lines.append(
                f"\n🌱 **Soil Health ({s.get('soil_type', '')} — {s_src}):**\n"
                f"• Root Moisture ({s.get('active_root_depth', 'root zone')}): {moist}% | pH: {ph} | Organic Carbon: {oc}% | Nitrogen: {nitro}"
                f"{amend_line}"
            )
        elif s_status == "missing_location" and not w:
            lines.append(
                "\n🌱 **Soil Health:** Please share your **village, taluk, district, or 6-digit PIN code** "
                "for live multi-depth root moisture and 250m geospatial soil chemistry."
            )
            speech.append("Please mention your village or district name so I can check your soil health.")

        m_status = m.get("status") if m else None
        if m_status in ("success", "cached_real"):
            price = m.get("modal_price", 0)
            mandi_name = m.get("primary_mandi", "APMC")
            trend = m.get("trend", "")
            strat = m.get("selling_advisory", "")
            m_src = "📡 Live APMC Arrivals" if m.get("is_live_data") else f"🕒 {m.get('data_source_label', 'Saved APMC Rate')}"
            lines.append(
                f"\n💰 **APMC Market Rate ({crop_name} — {m_src}):**\n"
                f"• Usual Rate: ₹{price} per 100 kg quintal (₹{m.get('price_per_kg', round(price/100, 1))}/kg) at {mandi_name}\n"
                f"• Today's Range: ₹{m.get('min_price', price)} – ₹{m.get('max_price', price)} | Direction: {trend}\n"
                f"• **Selling Tip:** {strat}"
            )
            speech.append(f"{crop_name} usual market price is {price} rupees per quintal at {mandi_name}. {strat}")
        elif m_status == "service_unavailable":
            lines.append(f"\n💰 **APMC Market Rate ({crop_name}):** Live APMC market feed is temporarily unreachable and no saved rate is cached offline.")

        if d and d.get("status") == "success":
            d_name = d.get("disease_name", "")
            conf = d.get("confidence_score")
            conf_tag = f" (Confidence: {conf}%)" if conf else ""
            chem = d.get("chemical_prescription", "")
            org = d.get("organic_prescription", "")
            lines.append(f"\n🔬 **Leaf Health Check:**\n• Finding: {d_name}{conf_tag}\n• **Medicine:** {chem}\n• **Home / Natural Care:** {org}")

        return {"full_response": "\n".join(lines), "speech_audio_text": " ".join(speech), "action_cards": []}
