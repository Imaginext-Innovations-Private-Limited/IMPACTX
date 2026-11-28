"""
FasalSaarathi — Leaf Disease Vision Doctor (Dual-Engine, Online + Offline)
======================================================================

How a leaf photo is checked (no filename guessing, no fake fallbacks):

1. Photo check (OpenCV, always runs, offline)
   - Finds the leaf in the photo (green plant area) and rejects photos that are
     not a crop leaf (walls, faces, documents, blank images...).
   - Measures the real damaged area inside the leaf: orange powder spots,
     dark/brown spots, yellow rings, yellowing, white powder.
   - Reads the *shape* of the damage (rings around spots, big wet patches,
     many small spots) to decide the type of problem.

2. Online engine (when internet + GEMINI_API_KEY are available)
   - Google Gemini 2.5 Flash looks at the photo and answers in simple farmer
     words in the chosen language. It can recognise any crop.

3. Offline engine (no internet needed)
   - A real trained deep-learning model (MobileNetV2, trained on 54,000+ leaf
     photos of 14 crops / 38 leaf conditions) saved on disk in
     models/leaf_disease_cnn/. Its answer is combined with the OpenCV damage
     reading so it does not call a spotted leaf "healthy" (or the opposite).
   - For crops the offline model was not trained on (coffee, paddy, arecanut,
     cotton, banana...), the answer comes from the damage-pattern reading and
     the crop chosen by the farmer.

Every name and remedy is in plain everyday words (no Latin / scientific names),
in English, Kannada, Hindi, Tamil, Telugu and Marathi.
"""

import base64
import io
import json
import os
import re
import threading
from typing import Any, Dict, Optional, Tuple

import numpy as np
import requests
from PIL import Image, ImageOps

try:
    import cv2
except Exception:  # pragma: no cover - OpenCV is a hard requirement in practice
    cv2 = None

from tools.leaf_care_texts import (
    GROUP_KEYS, LANGS, care_text, crop_name, message, severity_text,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIRS = [
    os.path.join(PROJECT_ROOT, "models", "leaf_disease_cnn_custom"),  # farmer-trained (optional)
    os.path.join(PROJECT_ROOT, "models", "leaf_disease_cnn"),          # default offline model
]

LANG_NAMES_MAP = {"kn": "Kannada", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "mr": "Marathi", "en": "English"}

GEMINI_MODELS = ("gemini-flash-lite-latest", "gemini-3.5-flash", "gemini-flash-latest")

# Pathogen genus words that must never reach the farmer (scrubbed from online answers).
_LATIN_WORDS = (
    "hemileia", "vastatrix", "alternaria", "solani", "phytophthora", "infestans", "capsici",
    "meadii", "cercospora", "xanthomonas", "pseudomonas syringae", "septoria", "fusarium",
    "colletotrichum", "puccinia", "erysiphe", "oidium", "podosphaera", "magnaporthe",
    "pyricularia", "rhizoctonia", "sclerotium", "pythium", "botrytis", "isariopsis",
    "venturia", "gymnosporangium", "exserohilum", "ralstonia", "begomovirus", "tetranychus",
    "candidatus", "liberibacter", "passalora", "fulvia", "corynespora", "uncinula", "plasmopara",
)

# Crop words found in model labels -> crop key (order matters: "bell pepper" before "pepper").
_LABEL_CROP_WORDS = (
    ("bell pepper", "capsicum"), ("pepper", "capsicum"), ("chilli", "chilli"), ("tomato", "tomato"),
    ("potato", "potato"), ("corn", "maize"), ("maize", "maize"), ("grape", "grape"),
    ("apple", "apple"), ("orange", "orange"), ("citrus", "orange"), ("peach", "peach"),
    ("cherry", "cherry"), ("strawberry", "strawberry"), ("soybean", "soybean"), ("squash", "squash"),
    ("blueberry", "blueberry"), ("raspberry", "raspberry"), ("coffee", "coffee"), ("rice", "rice"),
    ("paddy", "rice"), ("cotton", "cotton"), ("banana", "banana"), ("arecanut", "arecanut"),
    ("groundnut", "groundnut"), ("onion", "onion"),
)

# Farmer crop choice -> crops the offline model knows that match it.
_HINT_TO_MODEL_CROPS = {
    "tomato": {"tomato"}, "potato": {"potato"}, "chilli": {"capsicum", "chilli"},
    "capsicum": {"capsicum"}, "maize": {"maize"}, "corn": {"maize"}, "grape": {"grape"},
    "apple": {"apple"}, "orange": {"orange"}, "peach": {"peach"}, "cherry": {"cherry"},
    "strawberry": {"strawberry"}, "soybean": {"soybean"}, "squash": {"squash"},
}

_HINT_ALIASES = {"paddy": "rice", "corn": "maize", "pepper": "chilli", "chili": "chilli", "general": ""}


def _group_from_label(label: str) -> str:
    """Map a model class label to a plain-language problem group (keyword based)."""
    s = label.lower()
    if "healthy" in s:
        return "healthy"
    if "rust" in s:
        return "rust"
    if "late blight" in s or "late_blight" in s:
        return "wet_rot"
    if "early blight" in s or "early_blight" in s or "target spot" in s or "target_spot" in s:
        return "ring_spot"
    if "bacterial" in s:
        return "bacterial_spot"
    if "powdery" in s or "mildew" in s:
        return "white_powder"
    if "virus" in s or "mosaic" in s or "curl" in s or "greening" in s:
        return "yellow_virus"
    if "mite" in s:
        return "mites"
    return "leaf_spot"


def _crop_from_label(label: str) -> str:
    s = label.lower()
    for word, key in _LABEL_CROP_WORDS:
        if word in s:
            return key
    return ""


def _normalize_hint(crop_hint: str) -> str:
    h = (crop_hint or "").strip().lower()
    h = _HINT_ALIASES.get(h, h)
    return h


def _scrub_latin(text: str) -> str:
    """Remove any pathogen Latin words (and the brackets around them) from free text."""
    if not text:
        return ""
    out = str(text)
    for w in _LATIN_WORDS:
        out = re.sub(r"\(\s*[^()]*\b" + re.escape(w) + r"\b[^()]*\)", "", out, flags=re.IGNORECASE)
        out = re.sub(r"\b" + re.escape(w) + r"\b", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).replace(" ,", ",").replace(" .", ".")
    return out.strip(" -–—,;")


# ---------------------------------------------------------------------------
# 1. Image loading + OpenCV leaf / damage reading
# ---------------------------------------------------------------------------
def _load_image(image_input) -> Optional[Image.Image]:
    try:
        if isinstance(image_input, Image.Image):
            img = image_input
        elif isinstance(image_input, (bytes, bytearray)):
            img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, str) and image_input and os.path.isfile(image_input):
            img = Image.open(image_input)
        else:
            return None
        img = ImageOps.exif_transpose(img).convert("RGB")
        if min(img.size) < 32:
            return None
        return img
    except Exception:
        return None


def _analyze_opencv_leaf_features(img: Image.Image) -> Dict[str, Any]:
    """Find the leaf and measure real damage percentages inside it."""
    work = img.copy()
    work.thumbnail((512, 512))
    rgb = np.array(work)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h = hsv[..., 0].astype(np.int16)
    s = hsv[..., 1].astype(np.int16)
    v = hsv[..., 2].astype(np.int16)
    total_px = h.size

    green = (h >= 33) & (h <= 90) & (s >= 50) & (v >= 35)
    green_pct_img = green.mean() * 100.0

    # Leaf region = largest connected green area, filled (so spots inside count as leaf).
    leaf_mask = np.zeros(h.shape, np.uint8)
    largest_frac = 0.0
    if green.any():
        k = max(5, int(min(h.shape) * 0.03)) | 1
        closed = cv2.morphologyEx(green.astype(np.uint8) * 255, cv2.MORPH_CLOSE,
                                  cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            big = max(contours, key=cv2.contourArea)
            largest_frac = cv2.contourArea(big) / float(total_px)
            cv2.drawContours(leaf_mask, [big], -1, 255, thickness=cv2.FILLED)
    leaf = leaf_mask > 0
    leaf_px = max(1, int(leaf.sum()))

    is_leaf = green_pct_img >= 10.0 and largest_frac >= 0.06

    orange = (h >= 5) & (h <= 25) & (s >= 95) & (v >= 105)
    yellow = (h > 25) & (h < 34) & (s >= 85) & (v >= 90)
    brown = (h < 23) & (s >= 60) & (v >= 50) & (v < 150) & ~orange
    dark = (v < 70) & ~((h >= 33) & (h <= 90) & (s >= 80))
    white = (s < 40) & (v > 190)

    def pct(mask):
        return float((mask & leaf).sum()) * 100.0 / leaf_px

    orange_pct, yellow_pct, white_pct = pct(orange), pct(yellow), pct(white)
    spot_mask = ((dark | brown) & leaf).astype(np.uint8)
    spot_pct = float(spot_mask.sum()) * 100.0 / leaf_px
    dark_pct = pct(dark)

    # Shape of dark/brown spots: size of blobs and yellow ring around them.
    ring_yellow_frac = 0.0
    avg_blob_pct = 0.0
    blob_count = 0
    if spot_mask.any():
        n, labels, stats, _ = cv2.connectedComponentsWithStats(spot_mask, connectivity=8)
        areas = [stats[i, cv2.CC_STAT_AREA] for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 12]
        blob_count = len(areas)
        if areas:
            avg_blob_pct = float(np.mean(areas)) * 100.0 / leaf_px
        ring_k = max(5, int(min(h.shape) * 0.025)) | 1
        dil = cv2.dilate(spot_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ring_k, ring_k)))
        ring = (dil > 0) & (spot_mask == 0) & leaf
        if ring.any():
            ring_yellow_frac = float((ring & (yellow | orange)).sum()) / float(ring.sum())

    damaged_pct = min(100.0, orange_pct + spot_pct + white_pct + 0.5 * yellow_pct)

    return {
        "is_leaf": bool(is_leaf),
        "green_leaf_pct": round(green_pct_img, 1),
        "leaf_area_pct": round(leaf_px * 100.0 / total_px, 1),
        "orange_spots_pct": round(orange_pct, 2),
        "dark_spots_pct": round(spot_pct, 2),
        "black_area_pct": round(dark_pct, 2),
        "yellowing_pct": round(yellow_pct, 2),
        "white_powder_pct": round(white_pct, 2),
        "damaged_leaf_area_pct": round(damaged_pct, 1),
        "spot_count": blob_count,
        "avg_spot_size_pct": round(avg_blob_pct, 2),
        "yellow_ring_ratio": round(ring_yellow_frac, 2),
    }


def _symptom_group_from_cv(m: Dict[str, Any]) -> Tuple[str, float]:
    """Decide the problem type from the damage pattern. Returns (group, clarity 0..1)."""
    orange, spots, yellow, white = m["orange_spots_pct"], m["dark_spots_pct"], m["yellowing_pct"], m["white_powder_pct"]
    if m["damaged_leaf_area_pct"] < 1.5 and yellow < 8:
        return "healthy", min(1.0, 0.75 + (1.5 - m["damaged_leaf_area_pct"]) / 6)
    if white >= 4 and white > spots:
        return "white_powder", min(1.0, 0.55 + white / 30)
    if orange >= 1.0 and orange >= 0.6 * spots:
        return "rust", min(1.0, 0.6 + orange / 15)
    if spots >= 1.0:
        if m["yellow_ring_ratio"] >= 0.22:
            return "ring_spot", min(1.0, 0.55 + m["yellow_ring_ratio"])
        if m["avg_spot_size_pct"] >= 1.0 or spots >= 15:
            return "wet_rot", min(1.0, 0.55 + spots / 40)
        return "leaf_spot", min(1.0, 0.5 + spots / 40)
    if yellow >= 12:
        return "yellow_virus", min(1.0, 0.45 + yellow / 60)
    return "leaf_spot", 0.4


def _severity_level(group: str, damaged_pct: float) -> str:
    if group == "healthy":
        return "none"
    if damaged_pct >= 25:
        level = "serious"
    elif damaged_pct >= 8:
        level = "medium"
    else:
        level = "mild"
    if group == "wet_rot" and level == "mild":
        level = "medium"  # spreads very fast — never treat as mild
    return level


# ---------------------------------------------------------------------------
# 2. Offline deep-learning model (PyTorch MobileNetV2, loaded once)
# ---------------------------------------------------------------------------
_CNN_LOCK = threading.Lock()
_CNN_STATE: Dict[str, Any] = {
    "loaded": False, "model": None, "processor": None, "labels": None, "prototypes": None, "error": None,
}


def _load_local_cnn():
    with _CNN_LOCK:
        if _CNN_STATE["loaded"]:
            return _CNN_STATE
        _CNN_STATE["loaded"] = True
        try:
            import torch
            from transformers import AutoModelForImageClassification, MobileNetV2ImageProcessor
            for d in MODEL_DIRS:
                if os.path.isfile(os.path.join(d, "config.json")):
                    proc = MobileNetV2ImageProcessor.from_pretrained(d, local_files_only=True)
                    model = AutoModelForImageClassification.from_pretrained(d, local_files_only=True)
                    model.eval()
                    protos = {}
                    proto_path = os.path.join(d, "indian_crop_prototypes.pt")
                    if os.path.isfile(proto_path):
                        raw_p = torch.load(proto_path, map_location="cpu", weights_only=True)
                        for k, vec in raw_p.items():
                            t = torch.tensor(vec, dtype=torch.float32)
                            protos[k] = t / (t.norm(p=2) + 1e-8)
                    _CNN_STATE.update(model=model, processor=proc,
                                      labels={int(k): v for k, v in model.config.id2label.items()},
                                      prototypes=protos, model_dir=d)
                    break
            else:
                _CNN_STATE["error"] = "offline model files not found"
        except Exception as e:  # torch / transformers missing or broken weights
            _CNN_STATE["error"] = str(e)
        return _CNN_STATE


def _run_local_cnn(img: Image.Image, hint: str) -> Optional[Dict[str, Any]]:
    st = _load_local_cnn()
    if st.get("model") is None:
        return None
    import torch
    import torch.nn.functional as F
    with torch.no_grad():
        inputs = st["processor"](images=img, return_tensors="pt")
        pixel_values = inputs["pixel_values"]
        backbone = st["model"].mobilenet_v2(pixel_values=pixel_values)
        pooled = backbone.pooler_output  # (1, 1280)
        logits = st["model"].classifier(pooled)
        probs = logits.softmax(-1)[0].cpu().numpy()
        emb = F.normalize(pooled, p=2, dim=-1)[0].cpu()

    best_proto_key = ""
    best_proto_sim = 0.0
    for pk, pvec in (st.get("prototypes") or {}).items():
        if ":" not in pk:
            continue
        pcrop, _ = pk.split(":", 1)
        if hint and pcrop not in ("general", hint):
            continue
        sim = float(torch.dot(emb, pvec).item())
        if sim > best_proto_sim:
            best_proto_sim = sim
            best_proto_key = pk

    labels = st["labels"]
    crops = {i: _crop_from_label(lbl) for i, lbl in labels.items()}
    allowed = _HINT_TO_MODEL_CROPS.get(hint)
    hint_used = False
    if allowed:
        idx = [i for i, c in crops.items() if c in allowed]
        if idx:
            sub = np.zeros_like(probs)
            sub[idx] = probs[idx]
            if sub.sum() > 0:
                probs = sub / sub.sum()
                hint_used = True

    group_probs: Dict[str, float] = {g: 0.0 for g in GROUP_KEYS}
    for i, p in enumerate(probs):
        group_probs[_group_from_label(labels[i])] += float(p)

    top = int(np.argmax(probs))
    return {
        "top_prob": float(probs[top]),
        "top_group": _group_from_label(labels[top]),
        "top_crop": crops[top],
        "group_probs": group_probs,
        "hint_used": hint_used,
        "hint_crop_known": bool(allowed),
        "proto_key": best_proto_key,
        "proto_sim": best_proto_sim,
    }


def _analyze_offline(img: Image.Image, m: Dict[str, Any], hint: str) -> Dict[str, Any]:
    """Fuse the offline CNN + 1280-d deep prototypes with the OpenCV damage reading."""
    cv_group, cv_clarity = _symptom_group_from_cv(m)
    cnn = _run_local_cnn(img, hint)
    damaged = m["damaged_leaf_area_pct"]

    crop_key = hint if hint else ""
    group, confidence, source = cv_group, 55.0 + 35.0 * cv_clarity, "symptom_scan"

    if cnn is not None:
        p, g = cnn["top_prob"], cnn["top_group"]
        proto_sim = cnn.get("proto_sim", 0.0)
        proto_key = cnn.get("proto_key", "")
        if proto_sim >= 0.88 and ":" in proto_key:
            pcrop, pgroup = proto_key.split(":", 1)
            if pgroup == cv_group or (proto_sim >= 0.93 and not (pgroup == "healthy" and damaged >= 4)):
                group = pgroup
                if not crop_key and pcrop != "general":
                    crop_key = pcrop
                confidence = min(95.5, 82.0 + (proto_sim - 0.85) * 90.0)
                source = "cnn_prototype"
                return {
                    "group": group,
                    "crop_key": crop_key,
                    "confidence": round(confidence, 1),
                    "decision_source": source,
                    "cnn_available": True,
                    "cnn_top_prob": round(max(p, proto_sim) * 100, 1),
                }

        cv_says_healthy = cv_group == "healthy"
        trusted = p >= 0.60 and (hint == "" or cnn["hint_crop_known"])
        if trusted and not (cv_says_healthy and g != "healthy" and p < 0.90) \
                and not (g == "healthy" and damaged >= 6):
            group, source = g, "cnn"
            agree = 1.0 if g == cv_group else 0.0
            confidence = 100.0 * p * 0.85 + 12.0 * agree
            if not crop_key or cnn["hint_used"]:
                crop_key = hint or cnn["top_crop"]
        else:
            # Suppress Healthy probabilities when visible spots >= 6% and pick best diseased group if strong
            if g == "healthy" and damaged >= 6:
                diseased_groups = {k: v for k, v in cnn["group_probs"].items() if k != "healthy"}
                best_dis_grp = max(diseased_groups, key=diseased_groups.get) if diseased_groups else cv_group
                if diseased_groups.get(best_dis_grp, 0.0) >= 0.35 and best_dis_grp == cv_group:
                    group = best_dis_grp
            support = cnn["group_probs"].get(group, 0.0)
            confidence = 58.0 + 28.0 * cv_clarity + 12.0 * support
            source = "cnn+symptom_scan"
            if not crop_key and p >= 0.60 and g == group:
                crop_key = cnn["top_crop"]

    confidence = round(max(45.0, min(96.0, confidence)), 1)
    return {
        "group": group,
        "crop_key": crop_key,
        "confidence": confidence,
        "decision_source": source,
        "cnn_available": cnn is not None,
        "cnn_top_prob": round(cnn["top_prob"] * 100, 1) if cnn else None,
    }


# ---------------------------------------------------------------------------
# 3. Online engine (Gemini multimodal vision)
# ---------------------------------------------------------------------------
def _analyze_with_gemini_vision(img: Image.Image, hint: str, language: str, m: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    lang_name = LANG_NAMES_MAP.get(language, "English")
    groups = ", ".join(GROUP_KEYS)
    prompt = (
        "You are an experienced Indian crop doctor talking to a farmer with no science background.\n"
        f"Look at this photo. Farmer says the crop is: '{hint or 'not told'}'.\n"
        f"Our camera scan measured: spotted/damaged leaf area {m['damaged_leaf_area_pct']}%, "
        f"orange spots {m['orange_spots_pct']}%, dark/brown spots {m['dark_spots_pct']}%, "
        f"yellowing {m['yellowing_pct']}%, white powder {m['white_powder_pct']}%.\n\n"
        "STRICT LANGUAGE RULES:\n"
        f"- Write every text value in simple, everyday {lang_name} that a village farmer understands.\n"
        "- NEVER use Latin or scientific names of fungi, bacteria, viruses or insects.\n"
        "- NEVER use technical words like necrotic, chlorotic, lesion, pustule, sporulation, oomycete, pathogen, conidia.\n"
        "- Disease name = common farmer name + what it looks like, e.g. 'Leaf Rust (Orange Powder Spots)'.\n"
        "- CRITICAL: Tailor the disease name, symptoms, home care, agri-shop medicine, and care steps SPECIFICALLY to the identified crop (e.g., Coffee Rust vs. Rice Blast vs. Tomato Early Blight vs. Chilli Leaf Curl) — NEVER give generic one-size-fits-all advice.\n"
        "- Medicine amounts must be given per 1 litre of water AND per 15-litre spray pump.\n"
        "- Shop medicine names (like Mancozeb) may stay in English letters.\n\n"
        "Reply ONLY with JSON having exactly these keys:\n"
        "{\n"
        '  "is_leaf": true/false (false if the photo is not a plant leaf or is unreadable),\n'
        '  "crop": "crop name",\n'
        '  "disease_name": "plain name",\n'
        f'  "symptom_group": one of [{groups}, other],\n'
        '  "cause_simple": "e.g. Fungus — spreads in wet weather / Insect damage / Missing nutrients / Healthy",\n'
        '  "confidence_score": number 40-95,\n'
        '  "severity": one of [none, mild, medium, serious],\n'
        '  "symptoms_identified": "what you can see, in plain words",\n'
        '  "organic_prescription": "home / natural remedy with amounts",\n'
        '  "chemical_prescription": "agri-shop medicine with amounts per litre and per 15-litre pump",\n'
        '  "application_protocol": "simple care steps"\n'
        "}"
    )

    # Encode resized leaf photo as compact JPEG for fast HTTPS vision upload
    send_img = img.copy()
    send_img.thumbnail((768, 768))
    buf = io.BytesIO()
    send_img.save(buf, format="JPEG", quality=88)
    b64_jpeg = base64.b64encode(buf.getvalue()).decode("ascii")

    last_err = None
    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        gen_cfg: Dict[str, Any] = {"responseMimeType": "application/json", "temperature": 0.2}
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_jpeg}},
                ]
            }],
            "generationConfig": gen_cfg,
        }
        try:
            resp = requests.post(url, params={"key": api_key}, json=payload, timeout=(2.5, 18.0))
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {resp.text[:160]}"
                continue
            body = resp.json()
            parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            raw = "".join(p.get("text", "") for p in parts).strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed:
                parsed = parsed[0]
            parsed["_model"] = model_name
            return parsed
        except Exception as e:
            last_err = e
            continue
    print(f"[FasalSaarathi] Online leaf check unavailable, using offline model: {last_err}")
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _error(lang: str, key: str, status: str = "error") -> Dict[str, Any]:
    return {"status": status, "language": lang, "message": message(key, lang)}


def _build_result(lang: str, group: str, crop_key: str, crop_display: str, confidence: float,
                  sev_level: str, m: Dict[str, Any], mode: str, extra: Dict[str, Any]) -> Dict[str, Any]:
    t = care_text(group, lang, crop_key=crop_key)
    crop_text = crop_display or (crop_name(crop_key, lang) if crop_key else message("crop_unknown", lang))
    disease_local = t["name"]
    if (crop_key or crop_display) and not t.get("_is_crop_specific"):
        disease_local = f"{t['name']} — {crop_text}"

    def name_in(code):
        tc = care_text(group, code, crop_key=crop_key)
        base = tc["name"]
        if tc.get("_is_crop_specific"):
            return base
        return f"{base} — {crop_name(crop_key, code)}" if crop_key else base

    sev = severity_text(sev_level, lang)
    res = {
        "status": "success",
        "analysis_mode": mode,
        "language": lang,
        "crop": crop_text,
        "crop_identified": bool(crop_key or crop_display),
        "symptom_group": group,
        "is_healthy": group == "healthy",
        "disease_name": disease_local,
        "disease_name_en": name_in("en"),
        "disease_name_kn": name_in("kn"),
        "disease_name_hi": name_in("hi"),
        "scientific_name": "",
        "cause_simple": t["cause"],
        "pathogen_type": t["cause"],
        "confidence_score": confidence,
        "severity_code": sev_level,
        "severity_level": sev,
        "severity": sev,
        "symptoms_identified": t["symptoms"],
        "organic_prescription": t["home"],
        "organic_prescription_kn": care_text(group, "kn", crop_key=crop_key)["home"],
        "organic_prescription_hi": care_text(group, "hi", crop_key=crop_key)["home"],
        "chemical_prescription": t["medicine"],
        "chemical_prescription_kn": care_text(group, "kn", crop_key=crop_key)["medicine"],
        "chemical_prescription_hi": care_text(group, "hi", crop_key=crop_key)["medicine"],
        "application_protocol": t["steps"],
        "visual_metrics": {
            "damaged_leaf_area_pct": m["damaged_leaf_area_pct"],
            "orange_spots_pct": m["orange_spots_pct"],
            "dark_spots_pct": m["dark_spots_pct"],
            "yellowing_pct": m["yellowing_pct"],
            "white_powder_pct": m["white_powder_pct"],
            "green_leaf_pct": m["green_leaf_pct"],
        },
        "disclaimer": message("disclaimer", lang),
    }
    res.update(extra)
    res["summary"] = (
        f"Leaf check: {res['disease_name_en']}. Cause: {care_text(group, 'en')['cause']}. "
        f"Spotted leaf area {m['damaged_leaf_area_pct']}%. Confidence {confidence}%. "
        f"Medicine: {care_text(group, 'en')['medicine']}"
    )
    return res


def analyze_leaf_image(image_input, crop_hint: str = "", language: str = "en",
                       allow_online: bool = True) -> Dict[str, Any]:
    """
    Check a crop leaf photo. Accepts a file path, raw bytes or a PIL image.
    allow_online=False forces the offline engine (local deep-learning model + photo scan).
    """
    lang = (language or "en").lower()
    if lang not in LANGS:
        lang = "en"
    hint = _normalize_hint(crop_hint)

    img = _load_image(image_input)
    if img is None:
        return _error(lang, "unreadable")
    if cv2 is None:
        return {"status": "error", "language": lang, "message": "Image library (OpenCV) is not installed on the server."}

    m = _analyze_opencv_leaf_features(img)
    if not m["is_leaf"]:
        res = _error(lang, "not_leaf", status="not_a_leaf")
        res["visual_metrics"] = {"green_leaf_pct": m["green_leaf_pct"]}
        return res

    # ---------- Online ----------
    if allow_online:
        g = _analyze_with_gemini_vision(img, hint, lang, m)
        if g is not None:
            if g.get("is_leaf") is False:
                res = _error(lang, "not_leaf", status="not_a_leaf")
                res["analysis_mode"] = "gemini_multimodal_vision"
                return res
            group = g.get("symptom_group") if g.get("symptom_group") in GROUP_KEYS else "leaf_spot"
            sev_code = g.get("severity") if g.get("severity") in ("none", "mild", "medium", "serious") \
                else _severity_level(group, m["damaged_leaf_area_pct"])
            try:
                conf = round(max(40.0, min(95.0, float(g.get("confidence_score", 75)))), 1)
            except (TypeError, ValueError):
                conf = 75.0
            res = _build_result(
                lang, group, hint, _scrub_latin(g.get("crop", "")), conf, sev_code, m,
                "gemini_multimodal_vision",
                {"engine_model": g.get("_model", GEMINI_MODELS[0])},
            )
            # Gemini's own plain-language wording (scrubbed of any Latin) replaces the template text.
            for key_out, key_in in (("disease_name", "disease_name"), ("cause_simple", "cause_simple"),
                                    ("symptoms_identified", "symptoms_identified"),
                                    ("organic_prescription", "organic_prescription"),
                                    ("chemical_prescription", "chemical_prescription"),
                                    ("application_protocol", "application_protocol")):
                val = _scrub_latin(g.get(key_in, ""))
                if val:
                    res[key_out] = val
            res["pathogen_type"] = res["cause_simple"]
            for suffix in ("kn", "hi"):
                if lang == suffix:
                    res[f"disease_name_{suffix}"] = res["disease_name"]
                    res[f"organic_prescription_{suffix}"] = res["organic_prescription"]
                    res[f"chemical_prescription_{suffix}"] = res["chemical_prescription"]
            res["summary"] = (
                f"Online leaf check: {res['disease_name']}. {res['cause_simple']}. "
                f"Spotted leaf area {m['damaged_leaf_area_pct']}%. Confidence {conf}%. {res['chemical_prescription']}"
            )
            return res

    # ---------- Offline ----------
    off = _analyze_offline(img, m, hint)
    mode = "local_pytorch_cnn" if off["cnn_available"] else "local_symptom_scan"
    sev_code = _severity_level(off["group"], m["damaged_leaf_area_pct"])
    return _build_result(
        lang, off["group"], off["crop_key"], "", off["confidence"], sev_code, m, mode,
        {"decision_source": off["decision_source"], "model_confidence_pct": off["cnn_top_prob"]},
    )


_TEXT_SYMPTOM_KEYWORDS = (
    ("rust", (
        "rust", "orange powder", "orange spot", "yellow powder",
        "ತುಕ್ಕು", "ಕಿತ್ತಳೆ", "रतुआ", "नारंगी", "गेरुआ", "துரு", "ஆரஞ்சு", "తుప్పు", "నారింజ", "तांबेरा", "नारिंगी",
    )),
    ("wet_rot", (
        "late blight", "wet rot", "black rot", "kole", "mahali", "water soaked", "rotting",
        "ಕೊಳೆ", "ಮಹಾಳಿ", "ಕಪ್ಪು ಕೊಳೆ", "पछेती", "झुलसा", "सड़न", "गलन", "அழுகல்", "தாமத கருகல்", "కుళ్ళు", "कूज", "उशिरा करपा",
    )),
    ("white_powder", (
        "powdery", "white powder", "ash", "mildew",
        "ಬೂದಿ", "ಬಿಳಿ ಪುಡಿ", "चूर्णी", "सफेद पाउडर", "भभूतिया", "சாம்பல்", "வெள்ளை தூள்", "బూడిద", "తెల్ల పొడి", "भुरी", "पांढरी भुकटी",
    )),
    ("yellow_virus", (
        "curl", "mosaic", "wrinkled", "virus", "yellow leaf", "yellowing",
        "ಮುದುಡು", "ನಂಜು", "ಹಳದಿ ಎಲೆ", "मरोड़", "मोज़ेक", "पीलापन", "சுருள்", "தேமல்", "ముడత", "పసుపు", "गुंडाळी", "मोझॅक",
    )),
    ("mites", (
        "mite", "spider", "fine web",
        "ನುಸಿ", "ಜೇಡ", "माइट", "मकड़ी", "சிலந்தி", "பேன்", "నల్లి", "సాలీడు", "कोळी",
    )),
    ("bacterial_spot", (
        "bacterial", "greasy spot", "canker",
        "ಬ್ಯಾಕ್ಟೀರಿಯಾ", "जीवाणु", "பாக்டீரியா", "బ్యాక్టీరియా", "जिवाणू",
    )),
    ("ring_spot", (
        "early blight", "ring spot", "brown spot", "target spot",
        "ಉಂಗುರ", "ಕಂದು ಚುಕ್ಕೆ", "अगेती", "भूरे धब्बे", "வளைய", "கருகல்", "ఉంగర", "लवकर करपा",
    )),
)


def diagnose_text_symptoms(symptom_query: str, crop_hint: str = "", language: str = "en") -> Dict[str, Any]:
    """
    Provide plain-language crop care guidance when a farmer describes leaf symptoms in text/voice
    chat without attaching a photo. Never fabricates pixel metrics; clearly notes it is based on
    described symptoms and invites photo upload for visual confirmation.
    """
    lang = (language or "en").lower()
    if lang not in LANGS:
        lang = "en"
    q = (symptom_query or "").lower()
    hint = _normalize_hint(crop_hint)

    matched_group = "leaf_spot"
    for grp, words in _TEXT_SYMPTOM_KEYWORDS:
        if any(w in q for w in words):
            matched_group = grp
            break

    t = care_text(matched_group, lang)
    crop_disp = crop_name(hint, lang) if hint else ""
    d_title = f"{t['name']} — {crop_disp}" if crop_disp else t["name"]

    photo_tip = {
        "en": "Tip: You can also tap the camera icon to upload a close-up leaf photo for visual AI confirmation.",
        "kn": "ಸೂಚನೆ: ಎಲೆಯ ಹತ್ತಿರದ ಫೋಟೋವನ್ನು 📷 ಕ್ಯಾಮೆರಾ ಬಟನ್ ಒತ್ತಿ ಕಳುಹಿಸಿದರೆ ಇನ್ನಷ್ಟು ನಿಖರವಾಗಿ ಪರಿಶೀಲಿಸಬಹುದು.",
        "hi": "सुझाव: और सटीक जांच के लिए आप 📷 कैमरा बटन दबाकर पत्ती की पास से फोटो भी भेज सकते हैं।",
        "ta": "குறிப்பு: மேலும் துல்லியமான பரிசோதனைக்கு 📷 கேமரா பொத்தானை அழுத்தி இலையின் புகைப்படத்தை அனுப்பலாம்.",
        "te": "సూచన: మరింత ఖచ్చితమైన పరీక్ష కోసం 📷 కెమెರಾ బటన్ నొక్కి ఆకు ఫోటోను కూడా పంపవచ్చు.",
        "mr": "टीप: अधिक अचूक तपासणीसाठी आपण 📷 कॅमेरा बटण दाबून पानाचा जवळून फोटो देखील पाठवू शकता.",
    }[lang]

    return {
        "status": "success",
        "analysis_mode": "text_symptom_guide",
        "language": lang,
        "crop": crop_disp or crop_hint,
        "symptom_group": matched_group,
        "is_healthy": False,
        "disease_name": d_title,
        "disease_name_en": f"{care_text(matched_group, 'en')['name']}" + (f" — {crop_name(hint, 'en')}" if hint else ""),
        "disease_name_kn": f"{care_text(matched_group, 'kn')['name']}" + (f" — {crop_name(hint, 'kn')}" if hint else ""),
        "disease_name_hi": f"{care_text(matched_group, 'hi')['name']}" + (f" — {crop_name(hint, 'hi')}" if hint else ""),
        "scientific_name": "",
        "cause_simple": t["cause"],
        "severity_code": "medium",
        "severity_level": severity_text("medium", lang),
        "severity": severity_text("medium", lang),
        "symptoms_identified": t["symptoms"],
        "organic_prescription": t["home"],
        "organic_prescription_kn": care_text(matched_group, "kn")["home"],
        "organic_prescription_hi": care_text(matched_group, "hi")["home"],
        "chemical_prescription": t["medicine"],
        "chemical_prescription_kn": care_text(matched_group, "kn")["medicine"],
        "chemical_prescription_hi": care_text(matched_group, "hi")["medicine"],
        "application_protocol": f"{t['steps']} {photo_tip}",
        "photo_tip": photo_tip,
        "summary": f"Symptom guide for {d_title}: {t['cause']}. Medicine: {t['medicine']} Home care: {t['home']}",
    }


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJECT_ROOT, "static", "sample_leaves", "coffee_rust.jpg")
    print(json.dumps(analyze_leaf_image(path, allow_online=False), ensure_ascii=False, indent=2))
