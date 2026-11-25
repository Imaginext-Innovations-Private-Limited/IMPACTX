"""Project tests assert behaviors, not model accuracy on unseen real-world data."""
import pytest
from scamshield.engine import analyze, MAX_TEXT, OFFICIAL_REPORTING

CASES = [
 ("I am a CBI officer. You are under digital arrest. Transfer ₹20,000 immediately to avoid arrest.", "high", "arrest"),
 ("Your parcel is seized by customs for narcotics. Pay fine to avoid jail and legal action immediately.", "high", "courier"),
 ("To receive your ₹4,000 refund enter your UPI PIN and approve the collect request.", "high", "receive_pin"),
 ("Dear user your KYC has expired and your account will be suspended today. Click link.", "caution", "kyc"),
 ("Share OTP with our support desk right now to verify your wallet account.", "high", "credential"),
 ("Install AnyDesk and share your screen so we can verify the transaction.", "high", "remote_control"),
 ("Your account requires KYC update and will be blocked tomorrow.", "caution", "kyc"),
]
@pytest.mark.parametrize("message,expected,signal", CASES)
def test_scam_categories(message,expected,signal):
    d=analyze(message)
    assert d["level"] == expected
    assert signal in {x["id"] for x in d["indicators"]}
    assert d["score_label"] == "heuristic risk index, NOT probability"

def test_normal_message_not_marked_high():
    d=analyze("Your package has been delivered to reception at 2 pm. Thank you for shopping with us.")
    assert d["level"] in {"no_clear_signal","review"}
    assert d["level"] != "high"

def test_security_awareness_not_fraud():
    d=analyze("Scam alert: never share your OTP or UPI PIN with unknown callers.")
    assert d["level"] != "high"

def test_short_text_not_enough():
    assert analyze("hello")["level"]=="unknown"

def test_generic_legitimate_kyc_reminder_not_high():
    d=analyze("Your bank offers KYC updates in the official banking app. You can review your details there.")
    assert d["level"]!="high"

def test_low_risk_not_certified_safe():
    d=analyze("Please attend our weekly classroom meeting tomorrow at ten in the morning.")
    assert "does NOT establish legitimacy" in d["summary"] if d["level"]=="no_clear_signal" else True

def test_hindi_arrest_detected():
    d=analyze("आपको डिजिटल अरेस्ट किया गया है और पुलिस अधिकारी बात करेंगे। तुरंत पैसे भेजें।", language="hi")
    assert d["level"] in {"caution", "high"}
    assert any(x["id"]=="arrest" for x in d["indicators"])
    assert d["title"]

def test_reporting_links():
    d=analyze("You are under digital arrest and must transfer money right now")
    assert d["reporting"]==OFFICIAL_REPORTING
    assert OFFICIAL_REPORTING["helpline"]=="1930"

def test_lengths_and_errors():
    for kwargs in [{"text":""},{"text":"a"*(MAX_TEXT+1)},{"text":"hello", "channel":"not valid"},{"text":"hello", "language":"fr"}]:
        with pytest.raises(ValueError):analyze(**kwargs)

def test_explanation_includes_real_matched_substring():
    text="Immediately share your OTP with us. We are bank security."
    result=analyze(text)
    assert result["indicators"]
    for indicator in result["indicators"]:
        assert indicator["evidence"] in text
        assert indicator["explanation"] and indicator["advice"]

def test_hard_rule_dominates_uncertain_model():
    d=analyze("Approve the collect request now to release your prize")
    assert d["level"] in {"high", "caution"}

def test_unknown_channel_does_not_crash():
    d=analyze("Your courier parcel is seized and customs suspects narcotics",channel="call")
    assert d["channel"]=="call"


# ---- Added after real-world probing: messages the first rule set missed ----
MISSED_BEFORE = [
 ("kyc_phishing_link", "Dear customer, your SBI YONO account will be blocked today. Update your PAN now: http://sbi-kyc-update.xyz/login", "high", "url_lookalike"),
 ("mistaken_transfer", "Sir I sent Rs 5000 to your number by mistake please return it urgently, I will send you a request, just accept.", "high", "mistake_return"),
 ("job_telegram", "Earn Rs 5000 daily working from home. Just like YouTube videos, message on Telegram to join.", "caution", "job_channel"),
 ("hinglish_arrest", "Aap ka parcel mein drugs mila hai. CBI aapko arrest karegi. Abhi paise transfer karo warna jail hogi.", "high", "arrest_hinglish"),
 ("lottery_fee", "Congratulations! You won Rs 25 lakh in KBC lottery. Pay Rs 5000 processing fee to claim.", "high", "lottery"),
 ("electricity_threat", "Your electricity will be disconnected tonight 9:30 pm. Call officer 98xxxxxx immediately and pay bill.", "caution", "utility_threat"),
 ("apk_install", "Download the SBI rewards app APK from this link to claim your points: http://sbi-rewards.top/app.apk", "high", "apk_install"),
 ("safe_account", "Inspector Rao from Cyber Cell: do not disconnect this video call. Move your savings to the RBI safe account for verification.", "high", "safe_account"),
]

@pytest.mark.parametrize("name,message,minimum,signal", MISSED_BEFORE)
def test_previously_missed_scams(name, message, minimum, signal):
    d = analyze(message)
    order = ["unknown", "no_clear_signal", "review", "caution", "high"]
    assert order.index(d["level"]) >= order.index(minimum), (name, d["level"])
    assert signal in {x["id"] for x in d["indicators"]}

GENUINE = [
 "123456 is your OTP for login to HDFC NetBanking. Do not share this OTP with anyone. -HDFC Bank",
 "Rs 450.00 debited from A/c XX1234 on 23-11-26 via UPI to SWIGGY. If not you, call 1800-123-456. -SBI",
 "Your Amazon order #405 will be delivered today between 2-6 pm. Track it at https://www.amazon.in/progress-tracker",
 "Your KYC is due. Please visit your nearest branch with ID proof before 31 Dec. - Canara Bank",
 "Your SBI statement is ready. Download it from https://www.onlinesbi.sbi or the YONO app.",
 "Hi, I am sending the class notes now. Call me tomorrow on 9876543210 if you have doubts.",
 "Your electricity bill of Rs 820 is due on 28th. Pay in the BESCOM app to avoid late fees.",
]

@pytest.mark.parametrize("message", GENUINE)
def test_genuine_messages_stay_low(message):
    d = analyze(message)
    assert d["level"] in {"no_clear_signal", "review"}, (d["level"], [i["id"] for i in d["indicators"]])

def test_genuine_otp_is_recognised():
    d = analyze("123456 is your OTP for login to HDFC NetBanking. Do not share this OTP with anyone. -HDFC Bank")
    assert d["otp_notice"] is True and d["indicators"] == []

def test_complaint_draft_contents_and_redaction():
    text = "Your SBI account will be blocked today. OTP 482913. Update PAN: http://sbi-kyc-update.xyz/login or call 9876543210"
    d = analyze(text)
    c = d["complaint"]
    assert "http://sbi-kyc-update.xyz/login" in c and "9876543210" in c
    assert "482913" not in c and "[REDACTED]" in c
    assert "1930" in c and "cybercrime.gov.in" in c

def test_entities_extracted():
    d = analyze("Pay to scammer@ybl or call +91 98765 43210, visit bit.ly/abc123 now urgently")
    assert "scammer@ybl" in d["entities"]["upi_ids"]
    assert d["entities"]["phones"]
    assert any("bit.ly" in u for u in d["entities"]["urls"])


def test_secret_redacted_from_indicator_and_complaint():
    msg = "Your OTP is 123456. Share OTP 123456 with our support desk to verify your account immediately."
    result = analyze(msg)
    assert result["level"] == "high"
    assert result["indicators"]
    assert all("123456" not in i["evidence"] for i in result["indicators"])
    assert "123456" not in result["complaint"]
    assert "[REDACTED]" in result["complaint"]


def test_pin_cvv_password_redacted_everywhere():
    cases = [
        ("To receive your refund, enter your UPI PIN 4821 and approve the collect request now", "4821"),
        ("Send your CVV 123 and card 4111 1111 1111 1111 to verify your account immediately", "4111"),
        ("Share your password hunter22 with support desk to verify account", "hunter22"),
    ]
    for msg, secret in cases:
        d = analyze(msg)
        assert secret not in d["complaint"], msg
        assert all(secret not in i["evidence"] for i in d["indicators"]), msg
    assert " 123 " not in analyze(cases[1][0])["complaint"]
    # ordinary words after "PIN" must not be blanked out
    assert "enter your UPI PIN and approve" in analyze("To receive money, enter your UPI PIN and approve the request now")["complaint"]


def test_secret_url_query_redacted_across_outputs():
    msg = "Bank threat: update https://sbi-secure.xyz/verify?otp=452891&token=privateToken12"
    result = analyze(msg)
    for exported in [result["complaint"], str(result["indicators"]), str(result["entities"])]:
        assert "452891" not in exported
        assert "privateToken12" not in exported
        assert "sbi-secure.xyz" in result["complaint"]


def test_other_secret_query_fields_and_spoken_code():
    msg = "Send one time code 765432 to https://security-check.top/?code=765432&password=hunter22"
    result = analyze(msg)
    for exported in [result["complaint"], str(result["indicators"]), str(result["entities"])]:
        assert "765432" not in exported
        assert "hunter22" not in exported
