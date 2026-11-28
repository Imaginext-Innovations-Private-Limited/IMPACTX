"""Explainable hybrid fraud screening (rules + a small text model).

All scores are heuristic relative risk indicators, NOT fraud probabilities.
Signals are deliberately conservative; absence of signals cannot certify safety.
The bundled ML model is trained on synthetic examples and is not production validated.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

MAX_TEXT = 6000
OFFICIAL_REPORTING = {
    "cybercrime": "https://cybercrime.gov.in/",
    "chakshu": "https://sancharsaathi.gov.in/",
    "helpline": "1930",
}

@dataclass(frozen=True)
class Rule:
    code: str
    label: str
    weight: int
    pattern: str
    category: str
    explanation: str
    advice: str
    label_hi: str

RULES: tuple[Rule, ...] = (
    Rule("arrest", "Digital arrest or police-threat language", 6,
         r"\b(?:digital\s+arrest|arrest\s+warrant|under\s+arrest|video\s+call\s+arrest)\b|डिजिटल\s*अरेस्ट|गिरफ्तार\s*(?:कर|हो)",
         "Digital arrest", "Scammers may misuse legal threats to intimidate victims.", "End the conversation and verify independently through official channels.", "डिजिटल अरेस्ट या गिरफ्तारी की धमकी"),
    Rule("authority", "Authority impersonation", 2,
         r"\b(?:cbi\s+officer|\bcbi\b|cyber\s*cell|inspector\s+\w+\s+from\s+\w+|enforcement\s+directorate|cyber\s*police|police\s+department|customs\s+officer|narcotics\s+department|supreme\s+court|crime\s+branch)\b|सीबीआई|पुलिस\s+अधिकारी",
         "Digital arrest", "Mentioning an authority is not proof that the sender is genuine.", "Contact the organization using an independently found official number.", "अधिकारी होने का दावा"),
    Rule("legal_threat", "Threats of prosecution or imprisonment", 3,
         r"\b(?:money\s+laundering|legal\s+action|will\s+be\s+arrested|jail\s+sentence|criminal\s+case|avoid\s+arrest|court\s+case)\b|मनी\s*लॉन्ड्रिंग|जेल\s*(?:भेज|होगी)",
         "Digital arrest", "Fear and intimidation can pressure people into unsafe decisions.", "Do not pay a fine or disclose information based on a threatening message.", "कानूनी कार्रवाई की धमकी"),
    Rule("courier", "Courier or parcel seizure allegation", 4,
         r"\b(?:parcel|courier|fedex|delivery)\b.{0,90}\b(?:drugs|narcotics|illegal|seized|customs|contraband|police)\b|\b(?:seized|customs|narcotics)\b.{0,70}\b(?:parcel|courier)\b|पार्सल.{0,40}(?:जब्त|ड्रग्स|कस्टम)",
         "Courier fraud", "False parcel-crime claims are a common impersonation tactic.", "Verify with the courier through its independently sourced official app or website.", "पार्सल या कूरियर जब्ती का दावा"),
    Rule("kyc", "KYC suspension or account-blocking pressure", 3,
         r"\b(?:kyc|pan\s+update|aadhaar\s+update)\b.{0,75}\b(?:expire|expired|suspend|suspended|blocked|block|immediate|urgent|update\s+now)\b|\b(?:account|sim)\b.{0,35}\b(?:blocked|deactivated)\b.{0,30}\bkyc\b|केवाईसी.{0,45}(?:बंद|ब्लॉक|अपडेट)",
         "KYC fraud", "A deadline or suspension claim needs independent verification.", "Open your bank's official app yourself; don't use a link from the message.", "KYC बंद या ब्लॉक होने की चेतावनी"),
    Rule("credential", "Request for OTP, PIN or CVV", 6,
         r"\b(?:send|share|tell|give|provide|enter|reply\s+with|verify\s+using|disclose)\b.{0,35}\b(?:otp|one.time.password|upi\s*pin|pin|cvv|password)\b|\b(?:otp|upi\s*pin|cvv)\b.{0,30}\b(?:send|share|tell|give|provide|reply)\b|(?:ओटीपी|पिन).{0,20}(?:भेज|बताएं|शेयर)",
         "Credential theft", "A request to disclose authentication secrets is a critical red flag.", "Never share OTPs, UPI PINs, passwords, or CVV; contact your bank if already shared.", "OTP या PIN माँगा जा रहा है"),
    Rule("receive_pin", "UPI PIN requested to receive money", 7,
         r"\b(?:receive|collect|refund|cashback|claim|credit)\b.{0,95}\b(?:enter|type|share|use|provide)\b.{0,30}\b(?:upi\s*)?pin\b|\b(?:upi\s*)?pin\b.{0,50}\b(?:receive|refund|cashback|credit)\b|पैसे\s*पाने.{0,50}पिन",
         "UPI fraud", "You do not enter your UPI PIN simply to receive money.", "Do not approve a collect request or enter a PIN to receive a payment.", "पैसे पाने के लिए UPI PIN माँगा गया"),
    Rule("collect_request", "Unexpected UPI collect/payment approval request", 4,
         r"\b(?:approve|accept|authorize|confirm)\b.{0,55}\b(?:collect\s+request|upi\s+request|payment\s+request|mandate)\b|\bcollect\s+request\b.{0,45}\b(?:money|payment|approve|accept)\b",
         "UPI fraud", "Approving a payment collection request can debit your account.", "Open your UPI app directly and reject unfamiliar collection requests.", "UPI कलेक्ट रिक्वेस्ट को मंजूरी देने का दबाव"),
    Rule("remote_control", "Remote-access or screen-sharing request", 5,
         r"\b(?:anydesk|teamviewer|rustdesk|quick\s+support|screen\s*share|share\s+your\s+screen|remote\s+access|install\s+(?:this\s+)?app)\b|स्क्रीन\s*शेयर|एनीडेस्क",
         "Remote access fraud", "Remote-access tools can expose financial activity and private data.", "Do not install remote-control apps or share your screen for unsolicited support.", "स्क्रीन शेयर या रिमोट एक्सेस की मांग"),
    Rule("remote_install", "Unsolicited remote-app installation request", 3,
         r"\b(?:install|download|open)\b.{0,45}\b(?:anydesk|teamviewer|rustdesk|remote\s+app)\b|\b(?:anydesk|teamviewer|rustdesk)\b.{0,45}\b(?:install|download)\b",
         "Remote access fraud", "Unsolicited instructions to install remote-control tools add significant risk.", "Do not install an app at an unknown caller's direction.", "रिमोट ऐप इंस्टॉल करने का निर्देश"),
    Rule("pay", "Payment demand to settle a threat or claim", 4,
         r"\b(?:transfer|deposit|pay|send)\b.{0,65}\b(?:fine|penalty|verification\s+fee|security\s+deposit|to\s+avoid\s+(?:arrest|jail|legal|case|penalt|prosecution|action)|to\s+release|account|inr|rs\.?|₹)\b|\b(?:fine|penalty|verification\s+fee|security\s+deposit)\b.{0,60}\b(?:pay|transfer|deposit|send)\b|(?:जुर्माना|पैसे).{0,40}(?:भेजें|जमा|ट्रांसफर)",
         "Payment coercion", "Requests to transfer money under pressure can indicate fraud.", "Do not transfer money until you independently verify the demand.", "धमकी या दावे के बदले भुगतान की मांग"),
    Rule("urgency", "Artificial urgency or secrecy", 2,
         r"\b(?:immediately|within\s+(?:10|15|30)\s+minutes|last\s+chance|act\s+now|do\s+not\s+tell|keep\s+this\s+secret|right\s+now|urgent\s+action|final\s+warning|urgently|warna\s+(?:jail|arrest|case)|kisi\s+ko\s+(?:mat\s+)?bata(?:na|o))\b|तुरंत|अभी\s*(?:भेज|करें)|किसी\s+को\s+मत\s+बताओ",
         "Pressure tactics", "Urgent language alone does not prove fraud, but it increases risk alongside other signals.", "Pause and independently verify before taking action.", "जल्दी या गोपनीयता का दबाव"),
    Rule("unverified_link", "Link requiring independent verification", 1,
         r"\b(?:click|visit|open|tap)\s+(?:(?:on|in)\s+)?(?:the\s+|this\s+|below\s+)?link\b",
         "Suspicious link", "A link or URL shortener is not proof of a scam; its destination must be verified.", "Do not open unfamiliar links; navigate independently to the official website.", "लिंक को अलग से सत्यापित करें"),
    Rule("arrest_hinglish", "Arrest or jail threat (Hinglish)", 6,
         r"\barrest\s+(?:karenge|karegi|karega|kar\s+denge|ho\s+jaoge|ho\s+jayega|hoge)\b|\baapko\s+arrest\b|\bjail\s+(?:hogi|jaoge|jaana\s+padega|bhej)\b|\bwarrant\s+(?:nikla|jaari)\b",
         "Digital arrest", "Threatening arrest or jail over a call or message is a classic digital-arrest tactic.", "End the call. Real agencies do not arrest people over video calls or demand money.", "गिरफ्तारी या जेल की धमकी"),
    Rule("pay_hinglish", "Demand to send money now (Hinglish)", 4,
         r"\b(?:paise|paisa|rupaye|raqam|amount)\s+(?:abhi\s+)?(?:transfer|bhejo|bhejiye|bhej\s+do|bhejna|jama)\b|\b(?:transfer|bhejo)\s+karo\b",
         "Payment coercion", "Demanding an immediate transfer under threat is a strong fraud signal.", "Do not transfer money until you verify the demand independently.", "तुरंत पैसे भेजने की मांग"),
    Rule("stay_on_call", "Told to stay on a video call or move to another app", 4,
         r"\b(?:do\s+not|don't|dont)\s+(?:disconnect|cut|end|hang\s+up)\b.{0,30}\b(?:call|video)\b|\bstay\s+on\s+(?:the\s+)?(?:video\s+)?(?:call|line)\b|\bkeep\s+(?:your\s+)?(?:camera|video)\s+on\b|\bmove\s+to\s+(?:skype|whatsapp\s+video|video\s+call)\b",
         "Digital arrest", "Scammers keep victims on a call so they cannot check the story with anyone.", "Hang up. Call a family member or the police on a number you find yourself.", "वीडियो कॉल पर बने रहने का दबाव"),
    Rule("safe_account", "Request to move money to a 'safe' or 'verification' account", 6,
         r"\b(?:rbi\s+(?:safe|secure)\s+account|safe\s+account|(?:verification|escrow|government)\s+account)\b|\btransfer\b.{0,40}\b(?:your\s+)?(?:savings|entire\s+balance|all\s+(?:your\s+)?money)\b",
         "Digital arrest", "No government agency or bank asks you to move money to a safe account.", "Never transfer money to a 'safe' account. Call your bank on its official number.", "'सुरक्षित खाते' में पैसे भेजने की मांग"),
    Rule("account_block", "Account, SIM or card blocking threat", 2,
         r"\b(?:account|sim|card|upi|wallet)\b.{0,45}\b(?:blocked|suspended|deactivated|frozen)\b.{0,60}\b(?:today|tonight|tomorrow|now|immediately|hours?)\b|\b(?:today|tonight|tomorrow|within\s+\d+\s+hours?)\b.{0,50}\b(?:account|sim|card)\b.{0,30}\b(?:blocked|suspended|deactivated)\b",
         "KYC fraud", "Threatening to block your account unless you act quickly is a common phishing tactic.", "Open your bank's official app yourself and check; do not use links in the message.", "खाता बंद होने की धमकी"),
    Rule("mistake_return", "'Sent by mistake, please return it' request", 5,
         r"\b(?:by\s+mistake|wrongly|wrong\s+number|galti\s+se)\b.{0,100}\b(?:return|send\s+back|refund|give\s+back|wapas)\b|\b(?:return|send\s+back|refund|wapas)\b.{0,60}\b(?:by\s+mistake|wrongly|wrong\s+number|galti\s+se)\b",
         "UPI fraud", "Scammers claim a wrong transfer and pressure you to 'return' it, often through a fake or reversible payment.", "Do not send money back yourself. Ask your bank to handle any reversal.", "'गलती से भेजा, वापस करें' का दबाव"),
    Rule("just_accept", "Pressure to simply accept a payment request", 3,
         r"\b(?:just|simply)\s+(?:accept|approve)\b|\b(?:i\s+will|i'll)\s+send\s+(?:you\s+)?a\s+(?:collect\s+)?request\b",
         "UPI fraud", "Accepting a UPI request takes money OUT of your account.", "Reject unexpected UPI requests. You never need to accept a request to receive money.", "बस 'Accept' करने का दबाव"),
    Rule("job_income", "Unrealistic daily earnings offer", 3,
         r"\b(?:earn|income|salary)\b.{0,40}\b(?:daily|per\s+day|a\s+day|every\s+day|per\s+hour|weekly)\b|\b(?:rs\.?|₹|inr)\s*\d[\d,]*\s*(?:daily|per\s+day|a\s+day)\b",
         "Job / task scam", "Easy high daily pay is the hook in task and work-from-home scams.", "Do not pay any 'deposit' or 'registration fee' for a job.", "रोज़ की भारी कमाई का लालच"),
    Rule("job_channel", "Job or task offer requiring verification", 3,
         r"\bwork(?:ing)?\s+from\s+home\b|\bpart[\s-]?time\s+job\b|\blike\s+(?:youtube|videos?|reels|posts)\b|\b(?:join|message|contact|dm)\s+(?:us\s+)?(?:on\s+|via\s+)?telegram\b|\btelegram\s+(?:group|channel|id)\b",
         "Job / task scam", "Unverified job or task offers can be used to solicit deposits; a part-time offer alone is not proof of fraud.", "Ignore it. Genuine employers do not hire through random messages or ask you to pay.", "टेलीग्राम पर काम का ऑफर"),
    Rule("lottery", "Prize or lottery claim that needs a fee", 5,
         r"\b(?:you\s+(?:have\s+)?won|congratulations|lucky\s+draw|lottery|kbc|winner)\b.{0,120}\b(?:processing|registration|claim|tax|delivery|release)\s*(?:fee|charge|charges|amount)\b|\b(?:pay|deposit|send)\b.{0,50}\b(?:to\s+claim|claim\s+(?:your\s+)?(?:prize|reward|winnings?))\b",
         "Prize scam", "Real prizes never require you to pay a fee first.", "Ignore the message and do not pay anything.", "इनाम पाने के लिए फीस माँगना"),
    Rule("utility_threat", "Electricity, gas or SIM disconnection threat with a deadline", 4,
         r"\b(?:electricity|power|gas|water|sim|mobile\s+number|connection)\b.{0,45}\b(?:disconnect(?:ed|ion)?|cut|blocked|suspended|deactivated)\b.{0,50}\b(?:tonight|today|\d{1,2}[:.]\d{2}\s*(?:am|pm)|\d{1,2}\s*(?:am|pm)|within\s+\d+\s+(?:hours?|minutes?))\b",
         "Utility scam", "A same-day disconnection threat is a pressure tactic used in bill-payment scams.", "Check your bill in the provider's official app or at its office.", "आज रात कनेक्शन कटने की धमकी"),
    Rule("callback_officer", "Told to call an 'officer' on a personal number", 2,
         r"\b(?:call|contact|whatsapp)\s+(?:the\s+)?(?:officer|executive|agent|our\s+officer|this\s+number|me)\b.{0,25}(?:\+?\d[\d\sxX*-]{7,})",
         "Callback scam", "Scammers want you to call a number they control.", "Look up the official number yourself.", "किसी 'अधिकारी' को निजी नंबर पर कॉल करने को कहना"),
    Rule("apk_install", "Request to download an APK or unknown app", 5,
         r"\b(?:download|install|open)\b.{0,50}\bapk\b|\S+\.apk\b|\bapk\s+file\b",
         "Malware / remote access", "APK files from messages can steal OTPs and take over your phone.", "Install apps only from the Play Store or App Store.", "APK या अनजान ऐप डाउनलोड करने को कहना"),
    Rule("attachment_context", "Unexpected attachment opening or forwarding request", 4,
         r"^(?=.*\b[\w.-]+\.(?:zip|rar|7z|exe|msi|scr|bat|cmd|js|vbs|lnk|iso)\b)(?=.*\b(?:open|run|execute|extract|unzip)\b)(?:(?=.*\b(?:unknown\s+sender|not\s+a\s+contact)\b)|(?=.*\b(?:finance\s+(?:manager|department|team)|accounts\s+(?:team|department))\b)(?=.*\bforward\b)(?=.*\b(?:computer|pc|laptop)\b)).*?\b[\w.-]+\.(?:zip|rar|7z|exe|msi|scr|bat|cmd|js|vbs|lnk|iso)\b",
         "Suspicious attachment", "A file combined with a request targeting finance staff or an unknown sender may be social engineering. The file itself has not been scanned.", "Do not open or forward the attachment before verifying the sender independently; ask your IT security team.", "संदिग्ध अटैचमेंट खोलने या भेजने का अनुरोध"),
    Rule("url_shortener", "Shortened link hides the real website", 2,
         r"\b(?:bit\.ly|tinyurl\.com|t\.co|is\.gd|cutt\.ly|shorturl\.at|rb\.gy|tiny\.cc|goo\.gl|ow\.ly|bit\.do|t\.ly)/\S*",
         "Suspicious link", "A shortened link hides where it leads.", "Do not open it; go to the official website yourself.", "छोटा लिंक असली वेबसाइट छिपाता है"),
)

# Extra regional-language phrases supplement (not replace) the existing detector.
from .multilingual_signals import REGIONAL_RULES, REGIONAL_AWARENESS
from .languages import LANGUAGE_NAMES, localize_result
RULES += tuple(Rule(*fields) for fields in REGIONAL_RULES)
_COMPILED = [(r, re.compile(r.pattern, re.IGNORECASE | re.UNICODE)) for r in RULES]
_NEGATION = re.compile(r"\b(?:scam\s+alert|fraud\s+awareness|do\s+not\s+share|never\s+share|don't\s+share|beware\s+of|warning\s+about|example\s+of\s+a\s+scam)\b", re.I)


_OTP_NOTICE = re.compile(r"\b\d{4,8}\s+is\s+(?:your|the)\s+(?:otp|one.time|verification|login)|\b(?:otp|verification\s+code)\s+(?:is|for)\b.{0,40}\b\d{4,8}\b", re.I)
_DO_NOT_SHARE = re.compile(r"\b(?:do\s+not|don't|never)\s+share\b", re.I)

# ---- URL, phone and UPI-ID analysis -------------------------------------------------
URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"'()]+|"
    r"\b(?:bit\.ly|tinyurl\.com|t\.co|is\.gd|cutt\.ly|shorturl\.at|rb\.gy|tiny\.cc|goo\.gl|ow\.ly|bit\.do|t\.ly)/[^\s<>\"'()]+|"
    r"\b[a-z0-9][a-z0-9\-]{1,60}(?:\.[a-z0-9\-]{1,40})*\.(?:xyz|top|icu|click|link|online|site|shop|live|vip|cfd|sbs|buzz|rest|monster|work|cc|tk|ml|ga|cf)\b(?:/[^\s<>\"'()]*)?",
    re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
UPI_RE = re.compile(r"\b[\w.\-]{2,}@(?:ok(?:axis|sbi|hdfcbank|icici)|ybl|ibl|axl|paytm|apl|upi|sbi|fbl|pnb|barodampay|aubank|ikwik|freecharge|jupiter|slice|airtel|jio)\b", re.I)
SUSPICIOUS_TLDS = {"xyz", "top", "icu", "click", "link", "online", "site", "shop", "live", "vip", "cfd", "sbs", "buzz", "rest", "monster", "work", "cc", "tk", "ml", "ga", "cf"}
BRANDS = ("sbi", "hdfc", "icici", "axis", "kotak", "pnb", "paytm", "phonepe", "gpay", "googlepay", "npci", "bhim", "upi", "kyc",
          "irctc", "indiapost", "fedex", "dhl", "bluedart", "amazon", "flipkart", "uidai", "aadhaar", "epfo", "incometax",
          "rbi", "cbi", "customs", "police")
OFFICIAL_DOMAINS = {
    "sbi.co.in", "onlinesbi.sbi", "onlinesbi.com", "hdfcbank.com", "icicibank.com", "axisbank.com", "kotak.com",
    "pnbindia.in", "bankofbaroda.in", "canarabank.com", "idfcfirstbank.com", "yesbank.in", "indusind.com",
    "paytm.com", "phonepe.com", "google.com", "npci.org.in", "bhimupi.org.in", "amazon.in", "amazon.com",
    "flipkart.com", "irctc.co.in", "fedex.com", "dhl.com", "bluedart.com", "delhivery.com", "jio.com",
    "jiomart.com", "airtel.in", "whatsapp.com", "wa.me", "indiapost.gov.in", "indiapost.in",
}
_URL_TEXT = {
    "url_shortener": ("Shortened link hides the real website", "छोटा लिंक असली वेबसाइट छिपाता है"),
    "url_tld": ("Link uses a domain ending often seen in scams", "संदिग्ध डोमेन वाला लिंक"),
    "url_lookalike": ("Link imitates a bank or service but is not its official site", "बैंक या सेवा की नकल करता नकली लिंक"),
    "url_ip": ("Link points to a raw IP address", "IP पते वाला लिंक"),
    "url_obfuscated": ("Link is disguised or obfuscated", "छिपाया हुआ लिंक"),
}
_URL_WEIGHT = {"url_tld": 3, "url_lookalike": 4, "url_ip": 4, "url_obfuscated": 3}


def _split_url(raw: str) -> tuple[str, str]:
    u = re.sub(r"^(?:https?://)", "", raw.strip().rstrip(".,;:!?"), flags=re.I)
    netloc, _, path = u.partition("/")
    host = netloc.rsplit("@", 1)[-1].split(":")[0].lower()
    return host, path.lower()


def _registered(host: str) -> str:
    labels = host.split(".")
    if len(labels) >= 3 and labels[-2] in {"co", "com", "gov", "org", "ac", "nic", "net"} and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _is_official(host: str) -> bool:
    return host.endswith((".gov.in", ".nic.in")) or _registered(host) in OFFICIAL_DOMAINS


def _url_findings(text: str, language: str) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for m in URL_RE.finditer(text):
        raw = m.group(0).rstrip(".,;:!?")
        host, _path = _split_url(raw)
        if not host or "." not in host:
            continue
        flags = []
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
            flags.append("url_ip")
        if "xn--" in host or ("@" in raw.split("/")[0] and "://" in raw):
            flags.append("url_obfuscated")
        official = _is_official(host)
        if not official:
            if host.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS:
                flags.append("url_tld")
            tokens = [t for t in re.split(r"[.\-]", host) if t]
            if any(t.startswith(b) for t in tokens for b in BRANDS):
                flags.append("url_lookalike")
        for fid in flags:
            if fid in found:
                continue
            title_en, title_hi = _URL_TEXT[fid]
            found[fid] = {
                "id": fid, "title": title_hi if language == "hi" else title_en,
                "explanation": "Scammers register look-alike or throwaway websites to steal logins, OTPs and card details.",
                "weight": _URL_WEIGHT[fid], "evidence": raw[:160], "start": m.start(), "end": m.start() + len(raw),
                "advice": "Do not open it. Type the official website address yourself or use the official app.",
                "_category": "Suspicious link",
            }
        # Offline URL-only ML classifier and local verified-threat DB lookup
        from .url_classifier import SHORTENER_DOMAINS, classify_url, registered_domain
        url_info = classify_url(raw)
        is_shortener = registered_domain(host) in SHORTENER_DOMAINS
        if url_info["threat_db_match"] and "url_threat_db" not in found:
            found["url_threat_db"] = {
                "id": "url_threat_db",
                "title": "Link matches a verified phishing threat database" if language != "hi" else "लिंक सत्यापित फ़िशिंग डेटाबेस से मेल खाता है",
                "explanation": f"This link matches a verified phishing entry in the local {url_info['threat_db_source']} database.",
                "weight": 7, "evidence": raw[:160], "start": m.start(), "end": m.start() + len(raw),
                "advice": "Do not open this link. Navigate independently to the official website or app.",
                "_category": "Verified phishing link",
            }
        elif not flags and not is_shortener and url_info["ml_flag"] in {"high", "review"}:
            fid = "url_ml_phishing" if url_info["ml_flag"] == "high" else "url_ml_review"
            if fid not in found:
                reasons = ", ".join(url_info["reasons"][:3]) or "suspicious URL structure"
                found[fid] = {
                    "id": fid,
                    "title": "Offline URL model flagged suspicious link" if language != "hi" else "ऑफ़लाइन URL मॉडल ने संदिग्ध लिंक पहचाना",
                    "explanation": f"URL-only classifier flagged lexical patterns ({reasons}). Absence of a flag never guarantees safety.",
                    "weight": 4 if fid == "url_ml_phishing" else 2,
                    "evidence": raw[:160], "start": m.start(), "end": m.start() + len(raw),
                    "advice": "Do not open unfamiliar links; verify the domain independently.",
                    "_category": "Suspicious link",
                }
    return list(found.values())


def extract_entities(text: str) -> dict[str, list[str]]:
    def uniq(items):
        out = []
        for i in items:
            i = i.rstrip(".,;:!?")
            if i not in out:
                out.append(i)
        return out
    return {
        "urls": uniq(m.group(0) for m in URL_RE.finditer(text)),
        "phones": uniq(m.group(0).strip() for m in PHONE_RE.finditer(text)),
        "upi_ids": uniq(m.group(0) for m in UPI_RE.finditer(text)),
    }


def redact_secrets(text: str) -> str:
    """Best-effort masking of common secrets in exported or displayed user-supplied content.

    Redaction is not guaranteed for every secret format; users must still review drafts.
    """
    # Query parameters often contain codes, tokens or passwords. Mask the value while
    # retaining the host/path as useful evidence of a suspicious link.
    text = re.sub(
        r"(?i)([?&](?:otp|upi[_-]?pin|pin|cvv|cvc|password|passcode|verification[_-]?code|"
        r"security[_-]?code|code|token|auth|access[_-]?token|api[_-]?key)=)[^&#\s]+",
        r"\1[REDACTED]", text,
    )
    text = re.sub(r"(?i)(\botp\b[^\d]{0,20})\d{4,8}", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)\b((?:one[ -]?time|verification|security|authentication)\s+code\s*(?::|is)?\s*)\d{4,8}\b", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)\b\d{4,8}(?=\s+is\s+(?:your|the)\s+(?:otp|one.time|verification|login))", "[REDACTED]", text)
    text = re.sub(r"(?i)\b(upi\s*pin|pin|cvv|cvc)\b([^\d]{0,12})\d{3,6}\b", r"\1\2[REDACTED]", text)
    text = re.sub(r"(?i)\b(password|passcode)\b(\s*(?:is|:|=)?\s*)(?!(?:with|to|and|for|the|on|in|of|or|from|so|we|our|is)\b)[^\s,;]{3,}", r"\1\2[REDACTED]", text)
    text = re.sub(r"\b\d(?:[ -]?\d){12,18}\b", "[CARD-REDACTED]", text)
    return re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[AADHAAR-REDACTED]", text)


def build_complaint(text: str, level: str, categories: list[str], indicators: list[dict[str, Any]], entities: dict[str, list[str]]) -> str:
    ist = timezone(timedelta(hours=5, minutes=30))
    shown = {"high": "high-risk scam indicators", "caution": "several warning signs", "review": "a possible warning sign",
             "no_clear_signal": "no clear pattern", "unknown": "not enough context"}[level]
    lines = [
        "COMPLAINT DRAFT: suspected online fraud attempt",
        "(Generated by ScamShield AI from the text you pasted. Check every detail before submitting.)",
        f"Date noted: {datetime.now(ist).strftime('%d-%m-%Y %H:%M IST')}",
        "Suspected type: " + (", ".join(categories[:3]) if categories else "Not determined"),
        f"Automated screening result: {shown} (an assistant's screening, not a confirmed verdict)",
        "",
        "Warning signs found:",
        *([f"- {i['title']}: \"{i['evidence']}\"" for i in indicators] or ["- None detected automatically"]),
        "",
        "Suspicious details seen:",
        "- Phone numbers: " + (", ".join(entities["phones"]) or "none found"),
        "- Links: " + (", ".join(entities["urls"]) or "none found"),
        "- UPI IDs: " + (", ".join(entities["upi_ids"]) or "none found"),
        "",
        "Message / transcript received (OTP, card and Aadhaar numbers removed):",
        redact_secrets(text),
        "",
        "Money lost? Yes / No   Amount: ____   Transaction ID: ____   Date and time: ____   Bank: ____",
        "",
        "Where to report: call 1930 immediately if money was lost; file at https://cybercrime.gov.in/; "
        "report the number or message at https://sancharsaathi.gov.in/ (Chakshu); inform your bank.",
    ]
    return redact_secrets("\n".join(lines))


@lru_cache(maxsize=1)
def _model():
    """Tiny offline lexical ML model: a secondary weak signal only."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import LinearSVC
        from sklearn.pipeline import make_pipeline
        from .training_data import SUSPICIOUS, BENIGN
        if not SUSPICIOUS or not BENIGN:
            return None
        pipe = make_pipeline(TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=1,
                                            max_features=14000, lowercase=True),
                             LinearSVC(max_iter=10000, class_weight="balanced", random_state=42))
        pipe.fit(SUSPICIOUS + BENIGN, [1] * len(SUSPICIOUS) + [0] * len(BENIGN))
        return pipe
    except ImportError:
        return None


# Signed margin, NOT a probability. Candidate selected on training-only
# scenario-grouped five-fold out-of-fold scores; ML remains Review-only.
SVM_REVIEW_MARGIN = 0.20


def _ml_suspicious(model, text: str) -> bool:
    return float(model.decision_function([text])[0]) >= SVM_REVIEW_MARGIN


def analyze(
    text: str,
    channel: str = "message",
    language: str = "en",
    qr_payloads: list[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(text, str):
        raise ValueError("Message must be text.")
    text = text.strip()
    has_qr = bool(qr_payloads and any(isinstance(p, str) and p.strip() for p in qr_payloads))
    if not text and not has_qr:
        raise ValueError("Enter a message or transcript to analyze.")
    if len(text) > MAX_TEXT:
        raise ValueError(f"Text must be at most {MAX_TEXT} characters.")
    if channel not in {"message", "sms", "whatsapp", "call", "upi", "image"}:
        raise ValueError("Invalid channel.")
    if language not in LANGUAGE_NAMES:
        raise ValueError("Invalid language.")

    # OCR wraps sentences at arbitrary positions. Preserve original character offsets
    # for evidence and reports while making the rule scan insensitive to line breaks.
    rule_text = re.sub(r"[\r\n\t\v\f\u0085\u2028\u2029]", " ", text)
    matched = []
    total = 0
    cat_scores: dict[str, int] = defaultdict(int)
    from .context_rules import mask_negated_fees
    awareness_notice = bool(REGIONAL_AWARENESS.search(rule_text))
    for rule, regex in _COMPILED:
        # "Do not share OTP" is advice, not a request to disclose a code.
        # This context guard is limited and must be evaluated with native speakers.
        if rule.code == "regional_credential" and awareness_notice:
            continue
        # Mask only an exact, standalone UPI safety instruction (preserve offsets).
        scan_text = re.sub(r"(?:^|(?<=[.!?]))\s*(?:never|do\s+not|don't)\s+enter\s+(?:your\s+)?upi\s*pin\s+to\s+receive\s+money\s*(?=[.!?]|$)", lambda m: " " * len(m.group()), rule_text, flags=re.I) if rule.code in {"credential", "receive_pin"} else rule_text
        if rule.code in {"pay", "job_channel"}:
            scan_text = mask_negated_fees(scan_text)
        match = regex.search(scan_text)
        if not match and rule.code == "attachment_context" and channel == "image":
            # OCR may separate the filename and extension. Require corroborating
            # forwarding, finance/verification and opening language before flagging.
            match = re.search(
                r"^(?=.*\b(?:zip|rar|7z|apk|exe)\b)"
                r"(?=.*\b(?:finance\s+(?:manager|department|team)|accounts\s+(?:team|department))\b)"
                r"(?=.*\bverification\b)(?=.*\bforward\b)(?=.*\b(?:open|run|extract|unzip)\b)"
                r".*?\b(?:zip|rar|7z|apk|exe)\b.{0,120}", scan_text, re.I)
            if not match:
                # OCR can also drop the dot entirely (e.g. AB7Czip). Require
                # a digit-bearing filename token and nearby corroborating context.
                match = re.search(
                    r"\b[a-z0-9_-]*\d[a-z0-9_-]*(?:zip|rar|7z|apk|exe)\b"
                    r"(?=.{0,240}\b(?:finance\s+(?:manager|department|team)|accounts\s+(?:team|department))\b)"
                    r"(?=.{0,240}\bverification\b)(?=.{0,240}\bforward\b)"
                    r"(?=.{0,240}\b(?:open|run|extract|unzip)\b).{0,120}", scan_text, re.I)
        if not match:
            continue
        total += rule.weight
        cat_scores[rule.category] += rule.weight
        matched.append({
            "id": rule.code,
            "title": rule.label_hi if language == "hi" else rule.label,
            "explanation": rule.explanation,
            "weight": rule.weight,
            "evidence": text[match.start(): match.end()][:160],
            "start": match.start(), "end": match.end(),
            "advice": rule.advice,
        })

    for finding in _url_findings(text, language):
        total += finding["weight"]
        cat_scores[finding.pop("_category")] += finding["weight"]
        matched.append(finding)

    qr_analysis = None
    clean_qr = [p.strip()[:1024] for p in (qr_payloads or []) if isinstance(p, str) and p.strip()]
    if clean_qr:
        from .qr_decoder import analyze_qr_payloads
        from .url_classifier import classify_url

        qr_analysis = analyze_qr_payloads(clean_qr, surrounding_text=text)
        for finding in qr_analysis["indicators"]:
            total += finding["weight"]
            cat_scores[finding.pop("_category")] += finding["weight"]
            matched.append(finding)
        for item in qr_analysis["payloads"]:
            if item["type"] in {"url", "apk_download"}:
                url_info = classify_url(item["url"])
                item["url_assessment"] = {
                    "official_domain": url_info["official_domain"],
                    "threat_db_match": url_info["threat_db_match"],
                    "phishing_probability": url_info["phishing_probability"],
                    "ml_flag": url_info["ml_flag"],
                    "reasons": url_info["reasons"],
                }
                if url_info["threat_db_match"]:
                    total += 7
                    cat_scores["Verified phishing link"] += 7
                    matched.append({
                        "id": "qr_url_threat_db",
                        "title": "QR link matches a verified phishing database",
                        "explanation": f"Decoded QR URL matches a verified phishing entry in {url_info['threat_db_source']}.",
                        "weight": 7, "evidence": item["url"][:160], "start": 0, "end": 0,
                        "advice": "Do not open the QR link. Navigate independently to the official site.",
                    })
                elif url_info["ml_flag"] in {"high", "review"}:
                    w = 4 if url_info["ml_flag"] == "high" else 2
                    total += w
                    cat_scores["Quishing"] += w
                    matched.append({
                        "id": "qr_url_ml_phishing" if w == 4 else "qr_url_ml_review",
                        "title": "Offline URL model flagged decoded QR link",
                        "explanation": "URL-only classifier flagged suspicious lexical patterns in the decoded QR destination.",
                        "weight": w, "evidence": item["url"][:160], "start": 0, "end": 0,
                        "advice": "Do not open this QR link; verify the domain independently.",
                    })

    # The combination is riskier than a short URL or a KYC reminder alone.
    ids = {m["id"] for m in matched}
    if {"kyc", "url_shortener", "unverified_link"} <= ids:
        relevant = [m for m in matched if m["id"] in {"kyc", "url_shortener", "unverified_link"}]
        start, end = min(m["start"] for m in relevant), max(m["end"] for m in relevant)
        matched.append({"id": "kyc_short_link_combo", "title": "KYC pressure combined with a shortened link",
                        "explanation": "A suspension warning directing you to a hidden link destination is a strong phishing indicator.",
                        "weight": 2, "evidence": text[start:end][:160], "start": start, "end": end,
                        "advice": "Do not use the link; open your bank's official app or contact the bank independently."})
        total += 2
        cat_scores["KYC fraud"] += 2

    # Corroborating context can identify threats beyond individual keywords.
    from .context_rules import contextual_findings
    context = contextual_findings(rule_text, _is_official)
    for finding in context:
        # A compound finding already represents its constituent evidence. Ensure
        # at least the intended combined severity without requiring a second rule.
        if finding["id"] in {"government_apk_context", "reward_context"}:
            relevant = {"apk_install", "remote_install", "remote_control"} if finding["id"] == "government_apk_context" else {"url_tld", "url_lookalike", "url_ip", "url_shortener", "unverified_link"}
            related_weight = sum(m["weight"] for m in matched if m["id"] in relevant)
            finding["weight"] = max(finding["weight"], 7 - related_weight)
        if finding["id"] == "credential_reward_context":
            # Do not double-count the same credential request; raise the compound
            # to the high-risk boundary, with separately inspectable evidence.
            credential_weight = sum(m["weight"] for m in matched if m["id"] == "credential")
            finding["weight"] = max(1, 7 - credential_weight)
        # Restore original evidence, including the exact original offsets.
        finding["evidence"] = text[finding["start"]:finding["end"]][:160]
        total += finding["weight"]
        cat_scores[finding.pop("_category")] += finding["weight"]
        matched.append(finding)

    # A generic part-time/work-from-home phrase by itself is not a scam sign
    # of the same strength as a corroborated easy-income or task offer.
    if len(matched) == 1 and matched[0]["id"] == "job_channel" and re.fullmatch(
        r"(?:part[\s-]?time\s+job|work(?:ing)?\s+from\s+home)", matched[0]["evidence"], re.I
    ):
        matched[0]["weight"] = total = 1
        cat_scores["Job / task scam"] = 1

    # Add compositional native-script evidence only when existing rules have not
    # already established caution/high. Never double-count a strong rule.
    if total < 3:
        from .regional_context import regional_context_findings
        regional = regional_context_findings(rule_text)
        if regional:
            finding = max(regional, key=lambda m: m['weight'])
            finding['evidence'] = text[finding['start']:finding['end']][:160]
            total += finding['weight']
            cat_scores[finding.pop('_category')] += finding['weight']
            matched.append(finding)
            context.append(finding)

    # ML is a weak signal, not a fraud-certification engine. No claimed calibrated confidence.
    ml = _model()
    model_signal = "unavailable" if ml is None else "not_triggered"
    if ml is not None and len(text.split()) >= 5:
        # This model is trained on bundled synthetic examples, so require a conservative margin.
        if _ml_suspicious(ml, text):
            model_signal = "suspicious_wording"
            if total == 0:
                total += 2  # No rule -> at most 'review' on a model signal alone.
        else:
            model_signal = "not_triggered"

    otp_notice = False
    if _OTP_NOTICE.search(rule_text) and _DO_NOT_SHARE.search(rule_text) and \
            all(m["id"] in {"credential", "urgency"} for m in matched):
        # A standard "123456 is your OTP... do not share" SMS is a genuine-looking notice, not a scam request.
        otp_notice = True
        matched = []
        cat_scores.clear()
        total = 0

    if len(matched) == 1 and matched[0]["id"] == "pay" and not re.search(
        r"\b(?:fine|penalty|security\s+deposit|verification\s+fee|avoid\s+arrest|to\s+release)\b", text, re.I
    ):
        # A bare transfer/amount request is not evidence of coercion by itself.
        matched[0].update(weight=1, title="Payment request — verify independently",
                          explanation="A payment request alone does not establish fraud.")
        total = 1
        cat_scores.clear()
        cat_scores["Payment request"] = 1

    safety_education = bool(_NEGATION.search(text) or REGIONAL_AWARENESS.search(text))
    if safety_education and not context and not any(m["id"] in {"receive_pin", "collect_request", "remote_control", "pay", "safe_account", "regional_payment", "url_lookalike", "url_ip", "url_tld", "apk_install", "kyc_short_link_combo", "attachment_context"} for m in matched) and not re.search(r"(?:^|[.!?;]\s*)\s*(?:please\s+)?(?:send|share|enter|provide|tell|give)\b.{0,40}\b(?:otp|pin|password|cvv)\b", text, re.I):
        # Important but limited contextual guard; a standalone awareness message is not a scam.
        total = min(total, 2)

    # A standalone prevention notice may mention the same threat words as a scam.
    # Only clear, complete negative advice clauses qualify; a separate demand must
    # keep its own risk indicators. No global exemption for a claimed disclaimer.
    advisory = re.sub(r'^\s*(?:cybercrime\s+awareness\s+reminder|fraud\s+awareness|scam\s+alert)\s*:\s*', '', text, flags=re.I)
    clauses = [c.strip() for c in re.split(r'[.!?;]+', advisory) if c.strip()]
    prevention = re.compile(r"(?:police|banks?|government\s+agencies|law\s+enforcement)\s+(?:will\s+never|never|do\s+not)\s+(?:place\s+you\s+under\s+digital\s+arrest|demand\s+money\s+to\s+avoid\s+(?:arrest|imprisonment|jail)|ask\s+for\s+(?:your\s+)?(?:otp|pin))(?:\s+or\s+demand\s+money\s+to\s+avoid\s+(?:arrest|imprisonment|jail))?|(?:never|do\s+not|don't)\s+share\s+(?:your\s+)?(?:otp|pin|upi\s*pin|password)(?:\s+with\s+anyone)?", re.I)
    if clauses and all(prevention.fullmatch(c) for c in clauses) and not context:
        matched = []
        cat_scores.clear()
        total = 0

    sufficient_context = (len(text) >= 18 and len(text.split()) >= 3) or bool(clean_qr) or any(
        m["id"] == "credential_reward_context" for m in matched
    )
    strong = any(m["weight"] >= 5 for m in matched)
    if not sufficient_context:
        level = "unknown"
    elif total >= 7 and (strong or len(matched) >= 2):
        level = "high"
    elif total >= 3:
        level = "caution"
    elif total >= 1:
        level = "review"
    else:
        level = "no_clear_signal"

    titles = {
        "en": {"high": "High-risk scam indicators found", "caution": "Several warning signs found",
               "review": "Review this message carefully", "no_clear_signal": "No clear scam pattern detected",
               "unknown": "Not enough context to assess"},
        "hi": {"high": "धोखाधड़ी के गंभीर संकेत मिले", "caution": "चेतावनी के कई संकेत मिले",
               "review": "इस संदेश को सावधानी से जाँचें", "no_clear_signal": "स्पष्ट धोखाधड़ी संकेत नहीं मिले",
               "unknown": "आकलन के लिए जानकारी कम है"},
    }
    descriptions = {
        "en": {"high": "Avoid acting on this request. Verify via an official contact you find yourself.",
               "caution": "Pause before paying, sharing information, or opening any link.",
               "review": "This contains a possible warning sign; confirm the sender independently.",
               "no_clear_signal": "This does NOT establish legitimacy. Scams may use unfamiliar wording.",
               "unknown": "Add the full message or call transcript for a more useful assessment."},
        "hi": {"high": "इस अनुरोध पर कार्रवाई न करें। आधिकारिक माध्यम से स्वतंत्र रूप से जाँचें।",
               "caution": "भुगतान, जानकारी साझा करने या लिंक खोलने से पहले जाँचें।",
               "review": "संभावित चेतावनी है; प्रेषक को स्वतंत्र रूप से सत्यापित करें।",
               "no_clear_signal": "इसका मतलब संदेश सुरक्षित होना नहीं है; धोखाधड़ी के अन्य तरीके भी हो सकते हैं।",
               "unknown": "बेहतर जाँच के लिए पूरा संदेश या कॉल का विवरण डालें।"},
    }
    if otp_notice:
        titles[language if language in {"en", "hi"} else "en"]["no_clear_signal"] = ("This looks like a standard OTP notice" if language == "en"
                                               else "यह सामान्य OTP संदेश जैसा लगता है")
        descriptions[language if language in {"en", "hi"} else "en"]["no_clear_signal"] = (
            "Never share this code with anyone, even someone claiming to be from your bank. Only enter it on a site or app YOU opened."
            if language == "en" else
            "यह कोड किसी को न बताएं, बैंक का कर्मचारी होने का दावा करने वाले को भी नहीं। इसे केवल अपने खोले ऐप या वेबसाइट पर डालें।")
    response_language = language if language in {"en", "hi"} else "en"
    if level in {"high", "caution"}:
        next_steps = (["Stop responding and do not transfer money or share credentials.",
                       "If funds were lost, immediately contact your bank and call 1930.",
                       "Report suspected scam communication through Sanchar Saathi; report a crime through cybercrime.gov.in."]
                     if language == "en" else
                     ["बातचीत रोकें; पैसे या OTP/PIN साझा न करें।",
                      "पैसा चला गया है तो तुरंत बैंक से संपर्क करें और 1930 पर कॉल करें।",
                      "संदिग्ध संचार Sanchar Saathi पर और साइबर अपराध cybercrime.gov.in पर रिपोर्ट करें।"])
    else:
        next_steps = (["Verify the sender through a known official app, website, or phone number.",
                       "Do not share OTPs, PINs or passwords or approve unfamiliar UPI requests.",
                       "If you have lost money, contact your bank and call 1930 promptly."]
                     if language == "en" else
                     ["आधिकारिक ऐप, वेबसाइट या ज्ञात नंबर से प्रेषक की जाँच करें।",
                      "OTP/PIN/पासवर्ड न दें और अपरिचित UPI अनुरोध स्वीकार न करें।",
                      "पैसा चला गया है तो बैंक से संपर्क करें और 1930 पर कॉल करें।"])
    top_cats = [k for k, v in sorted(cat_scores.items(), key=lambda item: -item[1])]
    # Evidence is included in the UI, copied report and complaint draft.
    # Redact secrets from that shared output, not only the transcript section.
    for indicator in matched:
        indicator["evidence"] = redact_secrets(indicator["evidence"].replace("\r", " ").replace("\n", " "))
    # Do not expose secret-bearing query strings in API metadata or copyable drafts.
    entities = {kind: [redact_secrets(value) for value in values]
                for kind, values in extract_entities(text).items()}
    complaint = build_complaint(text, level, top_cats, matched, entities)
    result = {
        "level": level,
        "title": titles[response_language][level],
        "summary": descriptions[response_language][level],
        "score": min(total, 10),
        "score_label": "heuristic risk index, NOT probability",
        "indicators": matched,
        "categories": top_cats,
        "actions": next_steps,
        "model_signal": model_signal,
        "channel": channel,
        "reporting": OFFICIAL_REPORTING,
        "entities": entities,
        "complaint": complaint,
        "otp_notice": otp_notice,
        "qr_analysis": qr_analysis,
        "disclaimer": "Prototype screening only. Not a verdict on the sender's identity, legal advice, or proof of fraud. Always verify independently.",
    }
    result = localize_result(result, language)
    if "attachment_context" in {m["id"] for m in matched}:
        result["actions"].insert(0, "Do not open or forward the attachment. Verify with the sender through a known channel and ask IT security.")
    if language == "en":
        # Put the most relevant compound warning first, without altering cached audio.
        context_ids = {finding["id"] for finding in context}
        relevant = [m for m in matched if m["id"] in context_ids]
        if relevant:
            result["actions"].insert(0, max(relevant, key=lambda m: m["weight"])["advice"])
    from .voice import voice_details
    result["voice_context"] = voice_details(result)
    return result
