"""Small compositional regional risk lexicon, not translation or proof of fraud.
A warning requires co-occurring concepts and an affirmative action request.
All entries are synthetic development vocabulary; native-speaker review pending.
"""
import re
from functools import lru_cache

# arrest, job, prize, fee, money, pay verb, receive, PIN-entry verb, negated advice
LEXICON = {
 'hi': (r'गिरफ्तार|गिरफ्तारी|गिरफ़्तारी|अरेस्ट|अटक|जेल',r'नौकरी|भर्ती|रोजगार',r'लॉटरी|इनाम|पुरस्कार',r'शुल्क|फीस|फ़ीस|चार्ज',r'पैसे|रकम|राशि|रुपये|रु\.?',r'भेजें|भेजो|जमा\s*करें|भरें|भुगतान\s*करें|चुकाएं|दें',r'पाने|प्राप्त\s*करने|मिलने|लेने',r'डालें|भरें|दर्ज\s*करें|बताएं|दें',r'नहीं|मत\s|न\s+(?:दें|भेजें|करें)|जरूरत\s*नहीं'),
 'mr': (r'अटक|तुरुंग|गुन्हा',r'नोकरी|भरती|रोजगार',r'लॉटरी|बक्षीस|पुरस्कार',r'शुल्क|फी',r'पैसे|रक्कम|रुपये',r'पाठवा|भरा|जमा\s*करा|द्या',r'मिळवण्यासाठी|मिळण्यासाठी|घेण्यासाठी|स्वीकारण्यासाठी',r'टाका|द्या|भरा|नोंदवा',r'नका|नाही|नसते|नसल्यास'),
 'bn': (r'গ্রেফতার|গ্রেপ্তার|জেল|আটক',r'চাকরি|নিয়োগ|নিয়োগ',r'লটারি|লটারী|পুরস্কার',r'ফি|চার্জ|শুল্ক',r'টাকা|অর্থ|রুপি',r'পাঠান|পাঠিয়ে\s*দিন|জমা\s*দিন|জমা\s*করুন|দিন|পরিশোধ\s*করুন',r'পেতে|পাওয়ার|পাওয়ার|গ্রহণ\s*করতে',r'দিন|লিখুন|প্রবেশ\s*করান|দাখিল\s*করুন',r'করবেন\s*না|লিখবেন\s*না|দেবেন\s*না|পাঠাবেন\s*না|লাগে\s*না|প্রয়োজন\s*নেই|দরকার\s*নেই|কোনো\s*ফি\s*নেই'),
 'kn': (r'ಬಂಧನ|ಬಂಧಿಸ|ಅರೆಸ್ಟ್|ಜೈಲು',r'ಕೆಲಸ|ಉದ್ಯೋಗ|ನೇಮಕಾತಿ',r'ಲಾಟರಿ|ಬಹುಮಾನ',r'ಶುಲ್ಕ|ಫೀ',r'ಹಣ|ಮೊತ್ತ|ರೂಪಾಯಿ',r'ಕಳುಹಿಸಿ|ಪಾವತಿಸಿ|ಜಮಾ\s*ಮಾಡಿ|ನೀಡಿ',r'ಪಡೆಯಲು|ಸ್ವೀಕರಿಸಲು|ಪಡೆದುಕೊಳ್ಳಲು',r'ನಮೂದಿಸಿ|ಹಾಕಿ|ನೀಡಿ',r'ಬೇಡಿ|ಇಲ್ಲ|ಅಗತ್ಯವಿಲ್ಲ|ಬೇಕಾಗಿಲ್ಲ'),
 'te': (r'అరెస్టు|అరెస్ట్|జైలు|నిర్బంధ',r'ఉద్యోగం|ఉద్యోగ|నియామక',r'లాటరీ|బహుమతి|ప్రైజ్',r'ఫీజు|రుసుము|చార్జీ',r'డబ్బు|రూపాయ|మొత్తం',r'పంపండి|చెల్లించండి|జమ\s*చేయండి|ఇవ్వండి',r'పొందడానికి|పొందేందుకు|స్వీకరించడానికి|తీసుకోవడానికి',r'నమోదు\s*చేయండి|ఎంటర్\s*చేయండి|ఇవ్వండి',r'వద్దు|అవసరం\s*లేదు|అక్కరలేదు|చేయకండి'),
 'or': (r'ଗିରଫ|ଆରେଷ୍ଟ|ଜେଲ',r'ଚାକିରି|ନିଯୁକ୍ତି',r'ଲଟେରି|ଲଟରି|ପୁରସ୍କାର',r'ଶୁଳ୍କ|ଫିସ|ଫି',r'ଟଙ୍କା|ରାଶି',r'ପଠାନ୍ତୁ|ଦିଅନ୍ତୁ|ଜମା\s*କରନ୍ତୁ|ଦେୟ\s*ଦିଅନ୍ତୁ',r'ପାଇବାକୁ|ପାଇବା\s*ପାଇଁ|ଗ୍ରହଣ\s*କରିବାକୁ',r'ଦିଅନ୍ତୁ|ଲେଖନ୍ତୁ|ପ୍ରବେଶ\s*କରନ୍ତୁ|ଭରନ୍ତୁ',r'ନାହିଁ|କରନ୍ତୁ\s*ନାହିଁ|ଦିଅନ୍ତୁ\s*ନାହିଁ|ଆବଶ୍ୟକ\s*ନାହିଁ'),
 'ta': (r'கைது|சிறை',r'வேலை|பணி\s*நியமனம்|வேலைவாய்ப்பு',r'லாட்டரி|பரிசு',r'கட்டணம்|பதிவுக்\s*கட்டணம்|கட்டண',r'பணம்|ரூபாய்|ரூ\.?|தொகை',r'அனுப்புங்கள்|அனுப்பவும்|செலுத்துங்கள்|செலுத்தவும்|கொடுங்கள்|கட்டுங்கள்',r'பெற|பெறுவதற்கு|பெறுவதற்காக|வாங்க',r'உள்ளிடுங்கள்|பதிவிடுங்கள்|உள்ளிடவும்|கொடுங்கள்',r'வேண்டாம்|கூடாது|தேவையில்லை|இல்லை|செலுத்தாதீர்கள்|அனுப்பாதீர்கள்'),
 'ml': (r'അറസ്റ്റ്|അറസ്റ്റു|ജയിൽ',r'ജോലി|നിയമനം|തൊഴിൽ',r'ലോട്ടറി|സമ്മാനം',r'ഫീസ്|ചാർജ്|തുക',r'പണം|രൂപ|തുക',r'അയയ്ക്കുക|അയക്കുക|അടയ്ക്കുക|അടക്കുക|നൽകുക|തരുക',r'ലഭിക്കാൻ|ലഭിക്കുന്നതിന്|ലഭിക്കാനായി|സ്വീകരിക്കാൻ|കിട്ടാൻ',r'നൽകുക|രേഖപ്പെടുത്തുക|എന്റർ\s*ചെയ്യുക|ടൈപ്പ്\s*ചെയ്യുക',r'വേണ്ട|അരുത്|പാടില്ല|ആവശ്യമില്ല|ഇല്ല'),
 'gu': (r'ધરપકડ|ગિરફ્તારી|જેલ',r'નોકરી|ભરતી|રોજગાર',r'લોટરી|ઇનામ|ઈનામ|પુરસ્કાર',r'ફી|શુલ્ક|ચાર્જ',r'પૈસા|રકમ|રૂપિયા',r'મોકલો|ભરો|ચૂકવો|ચુકવો|જમા\s*કરો|આપો',r'મેળવવા|મેળવવા\s*માટે|લેવા|પ્રાપ્ત\s*કરવા|સ્વીકારવા',r'દાખલ\s*કરો|ભરો|નાખો|આપો',r'નહીં|નહી|નથી|જરૂર\s*નથી|જરૂરિયાત\s*નથી|કરશો\s*નહીં|ન\s+(?:આપો|મોકલો|ભરો)'),
 'pa': (r'ਗ੍ਰਿਫ਼ਤਾਰੀ|ਗ੍ਰਿਫਤਾਰੀ|ਗ੍ਰਿਫ਼ਤਾਰ|ਗ੍ਰਿਫਤਾਰ|ਜੇਲ੍ਹ',r'ਨੌਕਰੀ|ਭਰਤੀ|ਰੁਜ਼ਗਾਰ',r'ਲਾਟਰੀ|ਇਨਾਮ',r'ਫੀਸ|ਫ਼ੀਸ|ਚਾਰਜ',r'ਪੈਸੇ|ਰਕਮ|ਰੁਪਏ',r'ਭੇਜੋ|ਭਰੋ|ਜਮ੍ਹਾਂ\s*ਕਰੋ|ਦਿਓ|ਅਦਾ\s*ਕਰੋ',r'ਪ੍ਰਾਪਤ\s*ਕਰਨ|ਲੈਣ|ਮਿਲਣ|ਪਾਉਣ',r'ਦਰਜ\s*ਕਰੋ|ਭਰੋ|ਪਾਓ|ਦਿਓ',r'ਨਹੀਂ|ਨਹੀ|ਨਾ\s+(?:ਦਿਓ|ਭਰੋ|ਭੇਜੋ|ਕਰੋ)|ਲੋੜ\s*ਨਹੀਂ'),
}
PIN = re.compile(r'\bUPI\s*PIN\b|यूपीआई\s*पिन|यूपीआय\s*पिन|ইউপিআই\s*পিন|ಯುಪಿಐ\s*ಪಿನ್|యూపీఐ\s*పిన్|ୟୁପିଆଇ\s*ପିନ|யுபிஐ\s*பின்|യുപിഐ\s*പിൻ|યુપીઆઈ\s*પિન|ਯੂਪੀਆਈ\s*ਪਿੰਨ?', re.I)

@lru_cache(maxsize=1)
def patterns():
    return {lang: tuple(re.compile(p, re.I) for p in values) for lang, values in LEXICON.items()}


MIXED_NEGATION = re.compile(r"\b(?:do not|don.t|never|no need to)\b", re.I)

def regional_context_findings(text):
    """Inspect short clauses and adjacent positive clauses, never whole-message negation.

    A regional phrase and explicit action must be nearby; no bare keyword alarms.
    Return at most one finding per behavior. Offsets refer to original input.
    """
    clauses = [m for m in re.finditer(r'[^.!?;।॥\n]+', text) if m.group().strip()]
    results = {}
    for lang, (arrest, job, prize, fee, money, pay, receive, enter, neg) in patterns().items():
        for i, clause in enumerate(clauses):
            if neg.search(clause.group()) or MIXED_NEGATION.search(clause.group()):
                continue
            # Cross-sentence context only if both clauses are affirmative and close.
            start, end = clause.span()
            if i and not neg.search(clauses[i-1].group()) and not MIXED_NEGATION.search(clauses[i-1].group()) and start - clauses[i-1].end() < 8:
                start = clauses[i-1].start()
            window = text[start:end]
            if len(window) > 240:
                window = clause.group(); start = clause.start()
            action = pay.search(clause.group())
            if action:
                if arrest.search(window) and (money.search(window) or fee.search(window)):
                    candidate = ('regional_context_arrest', 'Arrest claim with a payment request', 6, 'Digital arrest', 'A payment demand linked to arrest is a serious warning sign.', 'Do not pay to avoid arrest; verify independently with the authorities.')
                elif prize.search(window) and (fee.search(window) or money.search(window)):
                    candidate = ('regional_context_prize', 'Prize claim with an upfront payment request', 4, 'Prize scam', 'A fee demanded to receive a prize can indicate advance-fee fraud.', 'Do not pay to claim an unexpected prize; verify the organizer independently.')
                elif job.search(window) and fee.search(window):
                    candidate = ('regional_context_job', 'Job offer with a fee request', 3, 'Job / task scam', 'Upfront recruitment fees can indicate fraud; a fee alone does not prove fraud.', 'Verify the employer independently before paying any recruitment fee.')
                else:
                    candidate = None
                if candidate:
                    code, title, weight, category, explanation, advice = candidate
                    results.setdefault(code, dict(id=code, title=title, weight=weight, _category=category, explanation=explanation, advice=advice, start=start, end=end, evidence=text[start:end][:160]))
            if receive.search(window) and money.search(window) and PIN.search(window) and enter.search(clause.group()):
                code='regional_context_receive_pin'
                results.setdefault(code, dict(id=code, title='UPI PIN requested to receive money', weight=6, _category='UPI fraud', explanation='A UPI PIN is not needed simply to receive money.', advice='Do not enter a PIN or approve an unexpected payment request to receive money.', start=start, end=end, evidence=text[start:end][:160]))
    return list(results.values())
