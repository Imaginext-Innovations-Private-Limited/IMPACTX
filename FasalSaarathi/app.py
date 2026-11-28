"""
FasalSaarathi Full-Stack Web Application.
Serves:
1. Voice-First Farmer Web Application
2. Multilingual Agentic Chat & Tool-Calling Pipeline (Gemini API)
3. Leaf Disease Computer Vision Diagnostic
4. Live Agro Tools (Weather, Soil, APMC Mandi) & Terrace Farming Studio
"""

import os
import io
import re
import json
import base64
import urllib.parse
import requests

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; env vars must be set manually

from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from werkzeug.utils import secure_filename
from PIL import Image

from agent.advisor_agent import FarmAdvisorAgent, SUPPORTED_LANGUAGES
from tools.weather_tool import fetch_live_weather
from tools.soil_tool import fetch_soil_health
from tools.mandi_tool import fetch_mandi_prices
from tools.crop_disease_tool import analyze_leaf_image
from tools.terrace_farming_tool import plan_terrace_garden, learn_crop_guide

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "kisanvaani-dev-key")
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB max upload
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

# Initialize Agent (loads GEMINI_API_KEY from env)
agent = FarmAdvisorAgent()

SAMPLE_DEMO_QUERIES = [
    {
        "lang": "en",
        "lang_name": "English",
        "query": "Check live weather and tomato mandi price in Kolar. Should I irrigate today?",
        "label": "🍅 English: Kolar Tomato & Weather"
    },
    {
        "lang": "kn",
        "lang_name": "ಕನ್ನಡ (Kannada)",
        "query": "ಚಿಕ್ಕಮಗಳೂರಿನಲ್ಲಿ ಕಾಫಿ ಎಲೆಗಳಿಗೆ ಕಿತ್ತಳೆ ತುಕ್ಕು ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?",
        "label": "☕ ಕನ್ನಡ: ಚಿಕ್ಕಮಗಳೂರು ಕಾಫಿ ರೋಗ"
    },
    {
        "lang": "hi",
        "lang_name": "हिंदी (Hindi)",
        "query": "शिमोगा में सुपारी का मंडी भाव क्या है? क्या मुझे अभी बेचना चाहिए?",
        "label": "🌴 हिंदी: सुपारी मंडी भाव"
    },
    {
        "lang": "ta",
        "lang_name": "தமிழ் (Tamil)",
        "query": "கோயம்புத்தூரில் தக்காளி சந்தை விலை என்ன, இன்று பாசனம் செய்யலாமா?",
        "label": "🌱 தமிழ்: தக்காளி சந்தை & பாசனம்"
    },
    {
        "lang": "te",
        "lang_name": "తెలుగు (Telugu)",
        "query": "గుంటూరులో ఈరోజు వర్షం పడుతుందా? మిర్చి పంటకు నీరు పెట్టవచ్చా?",
        "label": "🌧️ తెలుగు: వర్షం & నీటిపారుదల"
    },
    {
        "lang": "mr",
        "lang_name": "मराठी (Marathi)",
        "query": "नाशिकमध्ये कांद्याचा बाजारभाव काय आहे आणि आज पाणी द्यावे का?",
        "label": "🧅 मराठी: कांदा भाव & सिंचन"
    }
]


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    gemini_enabled = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return render_template(
        "index.html",
        languages=SUPPORTED_LANGUAGES,
        sample_queries=SAMPLE_DEMO_QUERIES,
        gemini_enabled=gemini_enabled,
        agent_mode="Gemini AI" if gemini_enabled else "Rule-Based Fallback"
    )


@app.route("/api/status")
def api_status():
    """Health check endpoint with capability flags."""
    gemini_ok = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return jsonify({
        "status": "online",
        "gemini_api": "enabled" if gemini_ok else "disabled (rule-based fallback active)",
        "agent_mode": "gemini_api" if gemini_ok else "rule_based_fallback",
        "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
        "tools": [
            "fetch_live_weather",
            "fetch_soil_health",
            "fetch_mandi_prices",
            "diagnose_crop_disease",
            "plan_terrace_garden",
            "learn_crop_guide",
        ]
    })


def _split_tts_phrases(text: str, max_len: int = 165):
    """
    Split full advisory text into natural spoken clauses <= max_len chars
    WITHOUT splitting decimal numbers (e.g. 25.6, 14.7, 2.5).
    """
    cleaned = re.sub(r"[*#_`•🌾🌤️🌱💰🔬📡🕒📍⚠️💧✅📈🌿📷]+", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return []

    # Split only on true sentence/line breaks, never between digits
    raw_sentences = re.split(r"(?:(?<!\d)\.(?!\d)|[!?।\n;:|—–])+", cleaned)
    chunks = []
    for sent in raw_sentences:
        sent = sent.strip(" ,-")
        if not sent:
            continue
        if len(sent) <= max_len:
            chunks.append(sent)
        else:
            # Further split long sentences at commas or word spaces
            words = sent.split(" ")
            buf = ""
            for w in words:
                cand = f"{buf} {w}".strip() if buf else w
                if len(cand) <= max_len:
                    buf = cand
                else:
                    if buf:
                        chunks.append(buf)
                    buf = w[:max_len]
            if buf:
                chunks.append(buf)
    return chunks


@app.route("/api/tts", methods=["GET", "POST"])
def api_tts():
    """
    Generate complete, uninterrupted native speech audio for the entire advisory message.
    Fetches all sentence MP3 segments and concatenates raw MP3 frames into a single stream.
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        text = (payload.get("text") or "").strip()
        lang = (payload.get("lang") or "en").strip().lower()
    else:
        text = request.args.get("text", "").strip()
        lang = request.args.get("lang", "en").strip().lower()

    if not text:
        return jsonify({"status": "error", "message": "Text is required"}), 400

    lang_map = {"kn": "kn", "hi": "hi", "ta": "ta", "te": "te", "mr": "mr", "en": "en"}
    tl = lang_map.get(lang, "en")

    # Sanitize number ranges (3-4 → 3 to 4 / 3 ರಿಂದ 4 etc.)
    range_map = {
        "kn": r"\1 ರಿಂದ \2", "hi": r"\1 से \2", "en": r"\1 to \2",
        "ta": r"\1 முதல் \2", "te": r"\1 నుండి \2", "mr": r"\1 ते \2"
    }
    connector = range_map.get(lang, r"\1 to \2")
    sanitized = re.sub(r"(\d+)\s*[-–—]\s*(\d+)", connector, text)

    phrases = _split_tts_phrases(sanitized, max_len=165)
    if not phrases:
        return jsonify({"status": "error", "message": "Text is empty after cleaning"}), 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://translate.google.com/"
    }

    from concurrent.futures import ThreadPoolExecutor

    def _fetch_one(phrase: str):
        url = (
            f"https://translate.google.com/translate_tts"
            f"?ie=UTF-8&client=tw-ob&tl={tl}&q={urllib.parse.quote(phrase)}"
        )
        r = requests.get(url, headers=headers, timeout=(2.5, 6.0))
        if r.status_code == 200 and len(r.content) > 200:
            return r.content
        return None

    try:
        with ThreadPoolExecutor(max_workers=min(4, len(phrases))) as pool:
            parts = list(pool.map(_fetch_one, phrases[:24]))
        if all(p is not None for p in parts) and parts:
            full_mp3 = b"".join(parts)
            res = Response(full_mp3, mimetype="audio/mpeg")
            res.headers["Cache-Control"] = "public, max-age=3600"
            return res
    except Exception:
        pass

    if request.method == "POST":
        return jsonify({"status": "fallback_webspeech", "full_text": sanitized}), 503
    return jsonify({"status": "fallback_webspeech", "short_text": sanitized[:200]}), 200


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Execute Agentic Reasoning Workflow via Gemini API (or rule-based fallback).
    Accepts: query, language, optional image_path.
    """
    try:
        data = request.json or {}
        query = data.get("query", "").strip()
        lang = data.get("language", "en").lower()
        attached_image = data.get("image_path", None)

        if not query:
            return jsonify({"status": "error", "message": "Query cannot be empty"}), 400

        if lang not in SUPPORTED_LANGUAGES:
            lang = "en"

        res = agent.execute_agentic_workflow(
            user_query=query,
            language=lang,
            attached_image=attached_image
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/upload-leaf", methods=["POST"])
def upload_leaf():
    """
    Upload leaf image from camera or file picker.
    Validates file type and size before analysis.
    """
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"status": "error", "message": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({
                "status": "error",
                "message": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400

        filename = secure_filename(file.filename)
        # Prevent path traversal
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        # Validate it's a real image
        try:
            with Image.open(save_path) as img:
                img.verify()
        except Exception:
            os.remove(save_path)
            return jsonify({"status": "error", "message": "Invalid or corrupted image file"}), 400

        crop_hint = request.form.get("crop_hint", "")
        lang = request.form.get("language", "en")
        diag = analyze_leaf_image(save_path, crop_hint=crop_hint, language=lang)
        diag["image_url"] = f"/static/uploads/{filename}"
        diag["language"] = lang
        return jsonify(diag)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/diagnose-sample", methods=["POST"])
def diagnose_sample():
    """Diagnose a pre-loaded sample leaf image."""
    try:
        data = request.json or {}
        sample_name = data.get("sample_name", "coffee_rust.jpg")
        # Security: only allow known sample files
        allowed_samples = {"coffee_rust.jpg", "healthy_leaf.jpg", "potato_late_blight.jpg", "tomato_blight.jpg"}
        if sample_name not in allowed_samples:
            return jsonify({"status": "error", "message": "Unknown sample image"}), 400

        sample_path = os.path.join(app.static_folder, "sample_leaves", sample_name)
        crop_hint = data.get("crop_hint", "")
        lang = data.get("language", "en")
        diag = analyze_leaf_image(sample_path, crop_hint=crop_hint, language=lang)
        diag["image_url"] = f"/static/sample_leaves/{sample_name}"
        return jsonify(diag)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/tools/weather", methods=["GET"])
def tool_weather():
    loc = (request.args.get("location") or "").strip()
    lat_raw = request.args.get("lat")
    lon_raw = request.args.get("lon")

    if lat_raw is not None and lon_raw is not None and str(lat_raw).strip() != "" and str(lon_raw).strip() != "":
        try:
            lat_f = float(lat_raw)
            lon_f = float(lon_raw)
        except ValueError:
            return jsonify({"status": "invalid_coordinates", "message": "Invalid GPS coordinates"}), 400
        return jsonify(fetch_live_weather(lat=lat_f, lon=lon_f))

    if not loc or len(loc) > 100:
        return jsonify({
            "status": "missing_location" if not loc else "error",
            "message": "Please enter a valid village, taluk, district, PIN code, or use GPS."
        }), 400
    return jsonify(fetch_live_weather(location_query=loc))


@app.route("/api/tools/soil", methods=["GET"])
def tool_soil():
    dist = (request.args.get("district") or request.args.get("location") or "").strip()
    crop = (request.args.get("crop") or "general").strip()
    lat_raw = request.args.get("lat")
    lon_raw = request.args.get("lon")

    if lat_raw is not None and lon_raw is not None and str(lat_raw).strip() != "" and str(lon_raw).strip() != "":
        try:
            lat_f = float(lat_raw)
            lon_f = float(lon_raw)
        except ValueError:
            return jsonify({"status": "invalid_coordinates", "message": "Invalid GPS coordinates"}), 400
        return jsonify(fetch_soil_health(crop=crop, lat=lat_f, lon=lon_f))

    if not dist or len(dist) > 100:
        return jsonify({
            "status": "missing_location" if not dist else "error",
            "message": "Please enter a valid village, taluk, district, PIN code, or use GPS."
        }), 400
    return jsonify(fetch_soil_health(district_query=dist, crop=crop))


@app.route("/api/tools/mandi", methods=["GET"])
def tool_mandi():
    comm = (request.args.get("commodity") or "").strip()
    loc = (request.args.get("location") or request.args.get("district") or "").strip()
    lang = (request.args.get("language") or "en").strip()
    lat_raw = request.args.get("lat")
    lon_raw = request.args.get("lon")

    if not comm or len(comm) > 80:
        return jsonify({
            "status": "missing_commodity" if not comm else "error",
            "message": "Please select or enter a crop name to check APMC market prices."
        }), 400

    if lat_raw is not None and lon_raw is not None and str(lat_raw).strip() != "" and str(lon_raw).strip() != "":
        try:
            lat_f = float(lat_raw)
            lon_f = float(lon_raw)
        except ValueError:
            return jsonify({"status": "invalid_coordinates", "message": "Invalid GPS coordinates"}), 400
        return jsonify(fetch_mandi_prices(comm, location_hint=loc, lat=lat_f, lon=lon_f, language=lang))

    return jsonify(fetch_mandi_prices(comm, location_hint=loc, language=lang))


@app.route("/api/tools/terrace/plan", methods=["GET"])
def tool_terrace_plan():
    loc = (request.args.get("location") or "").strip()
    lat_raw = request.args.get("lat")
    lon_raw = request.args.get("lon")
    length_raw = request.args.get("length_ft")
    width_raw = request.args.get("width_ft")
    sun_raw = request.args.get("sunlight_hours")
    space_type = (request.args.get("space_type") or "open_terrace").strip()
    goal = (request.args.get("goal") or "daily_kitchen").strip()
    lang = (request.args.get("language") or "en").strip().lower()

    lat_f = lon_f = None
    if lat_raw is not None and lon_raw is not None and str(lat_raw).strip() != "" and str(lon_raw).strip() != "":
        try:
            lat_f = float(lat_raw)
            lon_f = float(lon_raw)
        except ValueError:
            return jsonify({"status": "invalid_coordinates", "message": "Invalid GPS coordinates"}), 400

    if not loc and (lat_f is None or lon_f is None):
        return jsonify({
            "status": "missing_location",
            "message": "Please enter your city, town, village, or 6-digit PIN code (or tap 📍 GPS) for live local terrace weather."
        }), 400

    res = plan_terrace_garden(
        location_query=loc,
        lat=lat_f,
        lon=lon_f,
        length_ft=length_raw,
        width_ft=width_raw,
        sunlight_hours=sun_raw,
        space_type=space_type,
        goal=goal,
        language=lang,
    )
    if res.get("status") in ("missing_location", "invalid_dimensions"):
        return jsonify(res), 400
    return jsonify(res)


@app.route("/api/tools/terrace/guide", methods=["GET"])
def tool_terrace_guide():
    crop = (request.args.get("crop") or "").strip()
    loc = (request.args.get("location") or "").strip()
    lat_raw = request.args.get("lat")
    lon_raw = request.args.get("lon")
    lang = (request.args.get("language") or "en").strip().lower()

    if not crop or len(crop) > 80:
        return jsonify({
            "status": "missing_crop",
            "message": "Please choose or type a vegetable, herb, or fruit to view its Seed-to-Harvest guide."
        }), 400

    lat_f = lon_f = None
    if lat_raw is not None and lon_raw is not None and str(lat_raw).strip() != "" and str(lon_raw).strip() != "":
        try:
            lat_f = float(lat_raw)
            lon_f = float(lon_raw)
        except ValueError:
            return jsonify({"status": "invalid_coordinates", "message": "Invalid GPS coordinates"}), 400

    return jsonify(
        learn_crop_guide(
            crop_query=crop,
            location_query=loc,
            lat=lat_f,
            lon=lon_f,
            language=lang,
        )
    )


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    print("=" * 60)
    print("🌾 FasalSaarathi Farm Advisor Starting...")
    print(f"   Gemini API: {'✅ Enabled' if os.getenv('GEMINI_API_KEY') else '⚠️  Disabled (using rule-based fallback)'}")
    print(f"   Debug Mode: {debug}")
    print("   Open: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=debug)
