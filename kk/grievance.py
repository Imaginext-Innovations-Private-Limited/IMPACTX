"""Complaint routing and letters.

Letters are assembled from fixed templates and rendered findings only (no free LLM text),
so every amount in a letter is a verified figure. The patient reviews and sends them;
the system never files anything on the patient's behalf.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .compose.render import plain, render_finding
from .models import AuditResult, Channel, Verdict

BASIS_LABEL = {"en": "Basis", "hi": "आधार", "kn": "ಆಧಾರ", "gu": "આધાર", "ta": "அடிப்படை", "te": "ఆధారం"}


def _basis(source_ids, data_dir):
    import yaml
    from pathlib import Path
    srcs = yaml.safe_load((Path(data_dir) / "sources.yaml").read_text(encoding="utf-8")) if data_dir else {}
    out = []
    for sid in source_ids or []:
        src = (srcs or {}).get(sid) or {}
        if src.get("rule_quote"):
            out.append({"quote": " ".join(str(src["rule_quote"]).split()), "title": src.get("title", sid),
                        "ref": src.get("rule_ref", "")})
    return out


LETTER = {
    "en": {
        "subject": {"hospital_desk": "Request to review and correct my hospital bill",
                    "scheme_grievance": "Grievance: charged at an empanelled hospital despite scheme coverage",
                    "nppa": "Complaint: price above the NPPA ceiling / MRP",
                    "consumer": "Complaint: overcharging on a hospital bill"},
        "to": "To",
        "intro": "I was treated at {hospital} from {admission} to {discharge}. I request a review of the following charges on my bill:",
        "close": "Please correct the bill and refund any excess. A copy of the bill and the evidence sheet are attached.",
        "sign": "Name: ____________    Phone: ____________    Date: ____________",
    },
    "hi": {
        "subject": {"hospital_desk": "मेरे अस्पताल बिल की समीक्षा और सुधार हेतु अनुरोध",
                    "scheme_grievance": "शिकायत: योजना में शामिल अस्पताल में योजना कवर होते हुए भी शुल्क लिया गया",
                    "nppa": "शिकायत: NPPA की अधिकतम कीमत / MRP से ज़्यादा कीमत",
                    "consumer": "शिकायत: अस्पताल बिल में अधिक वसूली"},
        "to": "सेवा में",
        "intro": "मेरा इलाज {hospital} में {admission} से {discharge} तक हुआ। कृपया मेरे बिल के इन शुल्कों की समीक्षा करें:",
        "close": "कृपया बिल ठीक करें और अधिक ली गई राशि लौटाएँ। बिल की प्रति और साक्ष्य पत्र संलग्न हैं।",
        "sign": "नाम: ____________    फ़ोन: ____________    तारीख: ____________",
    },
    "kn": {
        "subject": {"hospital_desk": "ನನ್ನ ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಪರಿಶೀಲನೆ ಮತ್ತು ತಿದ್ದುಪಡಿಗಾಗಿ ಮನವಿ",
                    "scheme_grievance": "ದೂರು: ಯೋಜನೆ ಒಳಗೊಂಡಿದ್ದರೂ ಯೋಜನೆಯ ಆಸ್ಪತ್ರೆಯಲ್ಲಿ ಶುಲ್ಕ ವಿಧಿಸಲಾಗಿದೆ",
                    "nppa": "ದೂರು: NPPA ಗರಿಷ್ಠ ಬೆಲೆ / MRP ಗಿಂತ ಹೆಚ್ಚು ಬೆಲೆ",
                    "consumer": "ದೂರು: ಆಸ್ಪತ್ರೆ ಬಿಲ್‌ನಲ್ಲಿ ಹೆಚ್ಚುವರಿ ಶುಲ್ಕ"},
        "to": "ಗೆ",
        "intro": "ನನಗೆ {hospital} ನಲ್ಲಿ {admission} ರಿಂದ {discharge} ರವರೆಗೆ ಚಿಕಿತ್ಸೆ ನೀಡಲಾಯಿತು. ನನ್ನ ಬಿಲ್‌ನ ಈ ಶುಲ್ಕಗಳನ್ನು ಪರಿಶೀಲಿಸಲು ವಿನಂತಿಸುತ್ತೇನೆ:",
        "close": "ದಯವಿಟ್ಟು ಬಿಲ್ ಸರಿಪಡಿಸಿ ಮತ್ತು ಹೆಚ್ಚುವರಿ ಮೊತ್ತವನ್ನು ಮರುಪಾವತಿಸಿ. ಬಿಲ್ ಪ್ರತಿ ಮತ್ತು ಸಾಕ್ಷ್ಯ ಪತ್ರ ಲಗತ್ತಿಸಲಾಗಿದೆ.",
        "sign": "ಹೆಸರು: ____________    ಫೋನ್: ____________    ದಿನಾಂಕ: ____________",
    },
    "gu": {
        "subject": {"hospital_desk": "મારા હોસ્પિટલ બિલની સમીક્ષા અને સુધારા માટે વિનંતી",
                    "scheme_grievance": "ફરિયાદ: યોજના કવર હોવા છતાં યોજનાની હોસ્પિટલમાં ચાર્જ લેવાયો",
                    "nppa": "ફરિયાદ: NPPA મહત્તમ કિંમત / MRP કરતાં વધુ કિંમત",
                    "consumer": "ફરિયાદ: હોસ્પિટલ બિલમાં વધુ વસૂલાત"},
        "to": "પ્રતિ",
        "intro": "મારી સારવાર {hospital}માં {admission}થી {discharge} સુધી થઈ. મારા બિલના આ ચાર્જની સમીક્ષા કરવા વિનંતી:",
        "close": "કૃપા કરીને બિલ સુધારો અને વધારાની રકમ પરત કરો. બિલની નકલ અને પુરાવા પત્રક સાથે જોડેલા છે.",
        "sign": "નામ: ____________    ફોન: ____________    તારીખ: ____________",
    },
    "ta": {
        "subject": {"hospital_desk": "என் மருத்துவமனை பில்லை மறுபரிசீலனை செய்து திருத்தக் கோரிக்கை",
                    "scheme_grievance": "புகார்: திட்டக் காப்பீடு இருந்தும் திட்டத்தில் இணைந்த மருத்துவமனையில் கட்டணம் வசூலிக்கப்பட்டது",
                    "nppa": "புகார்: NPPA உச்சவரம்பு / MRP-ஐ விட அதிக விலை",
                    "consumer": "புகார்: மருத்துவமனை பில்லில் அதிகக் கட்டணம்"},
        "to": "பெறுநர்",
        "intro": "நான் {hospital} இல் {admission} முதல் {discharge} வரை சிகிச்சை பெற்றேன். என் பில்லில் உள்ள பின்வரும் கட்டணங்களை மறுபரிசீலனை செய்யக் கோருகிறேன்:",
        "close": "தயவுசெய்து பில்லைத் திருத்தி, கூடுதலாக வசூலித்த தொகையைத் திருப்பித் தரவும். பில்லின் நகலும் ஆதாரத் தாளும் இணைக்கப்பட்டுள்ளன.",
        "sign": "பெயர்: ____________    தொலைபேசி: ____________    தேதி: ____________",
    },
    "te": {
        "subject": {"hospital_desk": "నా ఆసుపత్రి బిల్లును సమీక్షించి సరిచేయమని విన్నపం",
                    "scheme_grievance": "ఫిర్యాదు: పథకం కవరేజీ ఉన్నా పథకంలోని ఆసుపత్రిలో ఛార్జీ వసూలు చేశారు",
                    "nppa": "ఫిర్యాదు: NPPA గరిష్ఠ ధర / MRP కంటే ఎక్కువ ధర",
                    "consumer": "ఫిర్యాదు: ఆసుపత్రి బిల్లులో అధిక వసూలు"},
        "to": "కు",
        "intro": "నేను {hospital} లో {admission} నుండి {discharge} వరకు చికిత్స పొందాను. నా బిల్లులోని ఈ ఛార్జీలను సమీక్షించమని కోరుతున్నాను:",
        "close": "దయచేసి బిల్లును సరిచేసి, అదనంగా వసూలు చేసిన మొత్తాన్ని తిరిగి ఇవ్వండి. బిల్లు ప్రతి మరియు సాక్ష్య పత్రం జతచేయబడ్డాయి.",
        "sign": "పేరు: ____________    ఫోన్: ____________    తేదీ: ____________",
    },
}


def channels(data_dir: Path) -> dict:
    return yaml.safe_load((data_dir / "channels.yaml").read_text(encoding="utf-8"))


def letters(result: AuditResult, lang: str, data_dir: Path) -> list[dict]:
    """One letter per channel that has red or amber findings, in the user's language and English."""
    chans = channels(data_dir)
    by_channel: dict[str, list] = {}
    for f in result.findings:
        if f.verdict in (Verdict.RED, Verdict.AMBER) and f.channel != Channel.NONE:
            # amber findings always go to the hospital desk first, never to a regulator
            ch = f.channel.value if f.verdict == Verdict.RED else Channel.HOSPITAL_DESK.value
            by_channel.setdefault(ch, []).append(f)
    h = result.bill.header
    out = []
    order = ["hospital_desk", "scheme_grievance", "nppa", "consumer"]
    for ch in sorted(by_channel, key=order.index):
        versions, subjects = {}, {}
        for lg in dict.fromkeys([lang, "en"]):
            L = LETTER.get(lg, LETTER["en"])
            items = []
            for f in by_channel[ch]:
                r = render_finding(f, result, lg)
                items.append(f"- {r['title']}: {plain(r['text'])}")
                for b in _basis(f.source_ids, data_dir):
                    items.append(f"  {BASIS_LABEL.get(lg, 'Basis')}: {b['quote']} ({b['title']}; {b['ref']})")
            body = "\n".join([
                f"{L['to']}: {chans[ch]['name']}",
                "",
                L["subject"][ch],
                "",
                L["intro"].format(hospital=h.hospital_name or "________",
                                  admission=h.admission_date.isoformat() if h.admission_date else "________",
                                  discharge=h.discharge_date.isoformat() if h.discharge_date else "________"),
                "",
                *items,
                "",
                L["close"],
                "",
                L["sign"],
            ])
            versions[lg] = body
            subjects[lg] = L["subject"][ch]
        info = chans[ch]
        out.append({"channel": ch, "name": info["name"], "phone": info.get("phone"), "url": info.get("url"),
                    "escalation": info.get("escalation"), "how": info.get("how"), "letters": versions, "subjects": subjects,
                    "findings": [f.rule_id for f in by_channel[ch]]})
    return out
