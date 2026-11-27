"""Conservative, limited regional fraud phrase patterns.

Not a general machine translator or validated multilingual fraud classifier.
For beta review by fluent Bengali/Hindi/Kannada/Telugu/Odia speakers.
Only phrases suggesting coercion, fraud, or actual secret *requests* are targeted.
"""
import re

REGIONAL_RULES = (
    ("regional_arrest", "Arrest threat in an Indian language", 6,
     r"(?:ডিজিটাল\s*অ্যারেস্ট|গ্রেফতার\s*(?:কর|হবেন)|ডিজিটাল\s*গ্রেফতার|"
     r"ಡಿಜಿಟಲ್\s*ಅರೆಸ್ಟ್|ಬಂಧಿಸ(?:ುತ್ತೇವೆ|ಲಾಗುತ್ತದೆ)|"
     r"డిజిటల్\s*అరెస్ట్|అరెస్టు\s*చేస్తాం|"
     r"ଡିଜିଟାଲ\s*ଆରେଷ୍ଟ|ଗିରଫ\s*କରିବା)",
     "Digital arrest", "A threat of arrest by message needs independent official verification.",
     "Never pay to cancel an alleged 'digital arrest'.", "गिरफ्तारी की धमकी"),
    ("regional_kyc", "Account suspension/KYC threat in a regional language", 4,
     r"(?:\bkyc\b|কেওয়াইসি|কে\s*ওয়াই\s*সি|ಕೆವೈಸಿ|ಕೇವೈಸಿ|కేవైసీ|కెవైసి|କେୱାଇସି)"
     r".{0,95}(?:বন্ধ\s*হয়ে\s*যাবে|ব্লক\s*হবে|ನಿರ್ಬಂಧ|ಬ್ಲಾಕ್|ಮುಚ್ಚ|బ్లాక్|నిలిపివేయ|బంద్|ବନ୍ଦ|ବ୍ଲକ|ବନ୍ଦ\s*ହେବ)|"
     r"(?:অ্যাকাউন্ট|ಖಾತೆ|అకౌంట్|ଖାତା).{0,60}(?:ব্লক|বন্ধ|ಬ್ಲಾಕ್|ನಿರ್ಬಂಧ|బ్లాక్|ବନ୍ଦ).{0,50}(?:\bkyc\b|কেওয়াইসি|ಕೆವೈಸಿ|కేవైసీ|କେୱାଇସି)",
     "KYC fraud", "Threats of account blocking may be used to rush verification.",
     "Use the bank's official app yourself rather than message links.", "KYC ब्लॉक होने का दावा"),
    ("regional_credential", "Request to reveal an OTP or PIN", 6,
     r"(?:ওটিপি|ও টি পি|ইউপিআই\s*পিন|ಓಟಿಪಿ|ಒಟಿಪಿ|ಯುಪಿಐ\s*ಪಿನ್|ఓటీపీ|ఓటిపి|యూపీఐ\s*పిన్|ଓଟିପି|ୟୁପିଆଇ\s*ପିନ|\bOTP\b|\bUPI\s*PIN\b)"
     r".{0,55}(?:শেয়ার\s*করুন|পাঠান|বলুন|জানান|ಹಂಚಿ|ಹೇಳಿ|ಕಳುಹಿಸಿ|పంచుకోండి|చెప్పండి|పంపండి|షేర్\s*చేయండి|କୁହନ୍ତୁ|ପଠାନ୍ତୁ|ସେୟାର\s*କରନ୍ତୁ)|"
     r"(?:শেয়ার\s*করুন|পাঠান|বলুন|ಹಂಚಿ|ಹೇಳಿ|కಳುಹಿಸಿ|పంచుకోండి|చెప్పండి|పంపండి|କୁହନ୍ତୁ|ପଠାନ୍ତୁ)"
     r".{0,55}(?:ওটিপি|ইউপিআই\s*পিন|ಓಟಿಪಿ|ಯುಪಿಐ\s*ಪಿನ್|ఓటీపీ|యూపీఐ\s*పిన్|ଓଟିପି|ୟୁପିଆଇ\s*ପିନ|\bOTP\b|\bPIN\b)",
     "Credential theft", "Nobody should ask you to disclose an OTP or UPI PIN.",
     "Never reveal an OTP or PIN.", "OTP या PIN की मांग"),
    ("regional_payment", "Pressure to transfer money in a regional language", 4,
     r"(?:টাকা\s*(?:পাঠান|পাঠিয়ে\s*দিন|ট্রান্সফার)|পয়সা\s*পাঠান|"
     r"ಹಣ\s*(?:ಕಳುಹಿಸಿ|ವರ್ಗಾಯಿಸಿ)|"
     r"డబ్బు(?:లు)?\s*(?:పంపండి|పంపాలి)|"
     r"ଟଙ୍କା\s*(?:ପଠାନ୍ତୁ|ପଠେଇଦିଅନ୍ତୁ|ଟ୍ରାନ୍ସଫର))",
     "Payment coercion", "An unsolicited request to send money must be independently verified.",
     "Do not transfer money under pressure.", "पैसे भेजने का दबाव"),
    ("regional_courier", "Parcel seizure claim in a regional language", 4,
     r"(?:পার্সেল|কুরিয়ার|ಪಾರ್ಸೆಲ್|ಕೊರಿಯರ್|పార్సిల్|కొరియర్|ପାର୍ସଲ|କୋରିଅର)"
     r".{0,65}(?:মাদক|ড্রাগস|জব্দ|ಅಕ್ರಮ|ಡ್ರಗ್ಸ್|ವಶ|డ్రగ్స్|సీజ్|అక్రమ|ଡ୍ରଗ୍ସ|ଜବତ|ଅବୈଧ)",
     "Courier fraud", "Fake parcel-seizure claims may be used to frighten people.",
     "Verify directly with the delivery company.", "पार्सल जब्ती का दावा"),
    ("regional_urgency", "Urgent pressure in a regional language", 2,
     r"(?:এখনই\s*(?:টাকা|পাঠান)|তাড়াতাড়ি\s*পাঠান|"
     r"ತಕ್ಷಣ\s*(?:ಹಣ|ಕಳುಹಿಸಿ)|"
     r"వెంటనే\s*(?:డబ్బులు|పంపండి)|"
     r"ତୁରନ୍ତ\s*(?:ଟଙ୍କା|ପଠାନ୍ତୁ))",
     "Pressure tactics", "A demand to act immediately increases risk when combined with other signals.",
     "Pause and verify independently.", "जल्दी करने का दबाव"),
)

# Explicit anti-scam educational phrasings. A scammer could try to game these;
# they only reduce scores when no coercive/payment-request rule from the main
# engine has fired. This avoids labeling simple awareness posters as crimes.
REGIONAL_AWARENESS = re.compile(
    r"(?:ওটিপি.{0,25}(?:শেয়ার\s*করবেন\s*না|কাউকে\s*বলবেন\s*না)|"
    r"ಓಟಿಪಿ.{0,25}(?:ಹಂಚಿಕೊಳ್ಳಬೇಡಿ|ಹೇಳಬೇಡಿ)|"
    r"ఓటీపీ.{0,25}(?:చెప్పవద్దు|పంచుకోవద్దు)|"
    r"ଓଟିପି.{0,30}(?:କୁହନ୍ତୁ\s*ନାହିଁ|ସେୟାର\s*କରନ୍ତୁ\s*ନାହିଁ))", re.IGNORECASE,
)


# Narrow Marathi phrases; not a full Marathi-language classifier. Do not match
# ordinary "pay the fee" reminders or standalone anti-fraud advice.
REGIONAL_RULES += (
    ("mr_arrest", "Marathi arrest threat", 6,
     r"(?:डिजिटल\s*अटक|तुम्हाला\s*अटक\s*(?:करण्यात\s*आली|करू|होईल|केली\s*जाईल|करण्यात\s*येईल))",
     "Digital arrest", "An arrest threat requires independent verification.", "Do not pay to avoid arrest.", "गिरफ्तारी की धमकी"),
    ("mr_payment", "Marathi urgent payment pressure", 4,
     r"(?:तात्काळ|ताबडतोब|लगेच|आत्ताच)\s*(?:पैसे|रक्कम)\s*(?:पाठवा|जमा\s*करा|ट्रान्सफर\s*करा)",
     "Payment coercion", "An urgent unsolicited money demand needs verification.", "Do not transfer money under pressure.", "पैसे भेजने का दबाव"),
    ("mr_kyc", "Marathi KYC suspension claim", 4,
     r"(?:KYC|केवायसी).{0,70}(?:खाते\s*बंद|खाते\s*ब्लॉक|बंद\s*होईल|ब्लॉक\s*होईल)",
     "KYC fraud", "A claim of account suspension may be used to pressure you.", "Check the bank app independently.", "KYC बंद होने का दावा"),
    ("mr_credential", "Marathi request to disclose an OTP or PIN", 6,
     r"(?:OTP|ओटीपी|ओ\s*टी\s*पी|UPI\s*PIN|यूपीआय\s*पिन)\s*(?:आम्हाला\s*|मला\s*)?(?:सांगा|पाठवा|शेअर\s*करा)(?!\s*नका)",
     "Credential theft", "A request to reveal authentication secrets is suspicious.", "Never disclose OTPs or PINs.", "OTP या PIN की मांग"),
    ("mr_receive_pin", "Marathi UPI PIN requested to receive money", 7,
     r"(?:पैसे\s*(?:मिळवण्यासाठी|मिळण्यासाठी|स्वीकारण्यासाठी)|परतावा\s*मिळवण्यासाठी).{0,40}(?:UPI\s*PIN|यूपीआय\s*पिन)\s*(?:टाका|द्या|भरा)(?!\s*नका)",
     "UPI fraud", "A UPI PIN is not needed to receive money.", "Reject unexpected payment requests.", "पैसे पाने के लिए UPI PIN की मांग"),
    ("mr_courier", "Marathi parcel seizure claim", 4,
     r"(?:पार्सल|कुरिअर|कुरियर).{0,65}(?:अमली\s*पदार्थ|अवैध\s*वस्तू|जप्त\s*केले|जप्त\s*झाले)",
     "Courier fraud", "Parcel crime claims may be used to intimidate.", "Contact the courier company independently.", "पार्सल जब्ती का दावा"),
)

# Limited beta coverage for four additional scripts; the classifier is unchanged.
# Direct requests to disclose an authentication secret to the sender are high risk.
# Require an explicit recipient and affirmative disclosure verb in the same clause.
for lang, arrest, demand, code, noun, recipient, send, negative in (
    ('ta', r'டிஜிட்டல்\s*கைது|கைது\s*செய்வோம்', r'பணம்\s*(?:அனுப்புங்கள்|அனுப்பவும்|செலுத்துங்கள்)', r'OTP|ஓடிபி|ஓ\s*டி\s*பி', r'எண்ணை|குறியீட்டை', r'எங்களுக்கு|எனக்கு|எங்களிடம்|என்னிடம்', r'அனுப்புங்கள்|அனுப்பவும்|சொல்லுங்கள்|சொல்லவும்|தாருங்கள்|கொடுங்கள்', r'வேண்டாம்|கூடாது'),
    ('ml', r'ഡിജിറ്റൽ\s*അറസ്റ്റ്|അറസ്റ്റ്\s*ചെയ്യും', r'പണം\s*(?:അയയ്ക്കുക|അയക്കുക|നൽകുക)', r'OTP|ഒടിപി|ഓടിപി|ഓ\s*ടി\s*പി', r'നമ്പർ|കോഡ്', r'ഞങ്ങൾക്ക്|എനിക്ക്|ഞങ്ങളോട്|എന്നോട്', r'അയയ്ക്കുക|അയക്കുക|പറയുക|നൽകുക|തരുക', r'വേണ്ട|അരുത്|പാടില്ല'),
    ('gu', r'ડિજિટલ\s*ધરપકડ|ધરપકડ\s*કરીશું', r'(?:પૈસા|રકમ)\s*(?:મોકલો|ભરો)', r'OTP|ઓટીપી|ઓ\s*ટી\s*પી', r'નંબર|કોડ', r'અમને|મને', r'મોકલો|જણાવો|આપો|કહો', r'નહીં|નહી|નહિ'),
    ('pa', r'ਡਿਜੀਟਲ\s*ਗ੍ਰਿ?ਫਤਾਰੀ|ਡਿਜੀਟਲ\s*ਗ੍ਰਿਫ਼ਤਾਰੀ|ਗ੍ਰਿਫਤਾਰ\s*ਕਰਾਂਗੇ', r'(?:ਪੈਸੇ|ਰਕਮ)\s*(?:ਭੇਜੋ|ਦਿਓ)', r'OTP|ਓਟੀਪੀ|ਓ\s*ਟੀ\s*ਪੀ', r'ਨੰਬਰ|ਕੋਡ', r'ਸਾਨੂੰ|ਮੈਨੂੰ', r'ਭੇਜੋ|ਦੱਸੋ|ਦਿਓ', r'ਨਹੀਂ|ਨਹੀ|ਨਾ'),
):
    REGIONAL_RULES += (
        (lang+'_arrest_demand', 'Arrest threat and payment demand', 8,
         rf'(?:{arrest}).{{0,100}}(?:{demand})', 'Digital arrest',
         'An arrest claim combined with a demand for money is a serious warning.',
         'Verify independently; do not pay to avoid arrest.', 'गिरफ्तारी और पैसे की मांग'),
        (lang+'_code_request', 'Request for an authentication code', 7,
         rf'(?:{code})\s*(?:(?:{noun})\s*)?(?:{recipient})\s*(?:{send})(?=\s|[.!?।,;:]|$)(?!\s*(?:{negative}))', 'Credential theft',
         'A request to disclose an authentication code is suspicious.',
         'Never reveal your OTP.', 'OTP की मांग'),
    )
