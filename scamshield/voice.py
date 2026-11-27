"""Bounded, context-specific speech. Only catalog text can leave this process."""
from __future__ import annotations
import base64
import hashlib
import os
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx
from .languages import CONTENT, LANGUAGE_NAMES, LEVELS

TOPICS = ('arrest', 'upi', 'kyc', 'courier', 'phishing', 'remote', 'generic')
# Draft translations: review with fluent speakers before public release.
# Same order across languages. No user-derived interpolation.
TOPIC_TEXT = {
'en': (
    'This may be a digital arrest scam. End the call and verify the authority independently. Do not pay to avoid arrest.',
    'This may be a UPI payment scam. You do not need a UPI PIN to receive money. Reject unexpected payment requests.',
    'This may be fake bank verification. Do not open the message link or share your OTP. Open the official banking app yourself.',
    'This may be a parcel or courier scam. Check with the courier company directly. Do not pay because of threats.',
    'This may be a phishing link. Do not open it or enter personal information. Visit the official website yourself.',
    'This may be a remote access scam. Do not install an unknown app or share your screen with the caller.',
),
'hi': (
    'यह डिजिटल अरेस्ट की धोखाधड़ी हो सकती है। कॉल काटें और खुद आधिकारिक नंबर से जाँच करें। गिरफ्तारी से बचने के लिए पैसे न दें।',
    'यह यूपीआई भुगतान की धोखाधड़ी हो सकती है। पैसे पाने के लिए यूपीआई पिन डालने की जरूरत नहीं होती। अनजान भुगतान अनुरोध ठुकराएँ।',
    'यह बैंक की नकली केवाईसी हो सकती है। संदेश का लिंक न खोलें और ओ टी पी न बताएं। बैंक का आधिकारिक ऐप खुद खोलें।',
    'यह पार्सल या कूरियर की धोखाधड़ी हो सकती है। सीधे कूरियर कंपनी से जाँच करें। धमकी के कारण पैसे न दें।',
    'यह धोखाधड़ी वाला लिंक हो सकता है। इसे न खोलें और निजी जानकारी न दें। आधिकारिक वेबसाइट खुद खोलें।',
    'यह रिमोट एक्सेस की धोखाधड़ी हो सकती है। अनजान ऐप इंस्टॉल न करें और कॉल करने वाले को अपनी स्क्रीन न दिखाएँ।',
),
'bn': (
    'এটি ডিজিটাল অ্যারেস্টের প্রতারণা হতে পারে। ফোন কেটে নিজে সরকারি নম্বরে যাচাই করুন। গ্রেফতার এড়াতে টাকা দেবেন না।',
    'এটি ইউপিআই পেমেন্টের প্রতারণা হতে পারে। টাকা পেতে ইউপিআই পিন দিতে হয় না। অচেনা পেমেন্ট অনুরোধ বাতিল করুন।',
    'এটি ব্যাংকের ভুয়া কেওয়াইসি হতে পারে। বার্তার লিঙ্ক খুলবেন না, ও টি পি বলবেন না। নিজে ব্যাংকের অফিসিয়াল অ্যাপ খুলুন।',
    'এটি পার্সেল বা কুরিয়ারের প্রতারণা হতে পারে। সরাসরি কুরিয়ার কোম্পানির সঙ্গে যোগাযোগ করুন। হুমকির কারণে টাকা দেবেন না।',
    'এটি প্রতারণার লিঙ্ক হতে পারে। লিঙ্ক খুলবেন না বা ব্যক্তিগত তথ্য দেবেন না। নিজে অফিসিয়াল ওয়েবসাইট খুলুন।',
    'এটি রিমোট অ্যাক্সেসের প্রতারণা হতে পারে। অচেনা অ্যাপ ইনস্টল করবেন না এবং ফোন করা ব্যক্তিকে আপনার স্ক্রিন দেখাবেন না।',
),
'kn': (
    'ಇದು ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್ ವಂಚನೆಯಾಗಿರಬಹುದು. ಕರೆ ಮುಗಿಸಿ ಅಧಿಕೃತ ಸಂಖ್ಯೆಯ ಮೂಲಕ ನೀವೇ ಪರಿಶೀಲಿಸಿ. ಬಂಧನ ತಪ್ಪಿಸಲು ಹಣ ಕೊಡಬೇಡಿ.',
    'ಇದು ಯುಪಿಐ ಪಾವತಿ ವಂಚನೆಯಾಗಿರಬಹುದು. ಹಣ ಸ್ವೀಕರಿಸಲು ಯುಪಿಐ ಪಿನ್ ಹಾಕಬೇಕಿಲ್ಲ. ಅಪರಿಚಿತ ಪಾವತಿ ವಿನಂತಿಯನ್ನು ತಿರಸ್ಕರಿಸಿ.',
    'ಇದು ನಕಲಿ ಬ್ಯಾಂಕ್ ಕೆವೈಸಿ ಆಗಿರಬಹುದು. ಸಂದೇಶದ ಲಿಂಕ್ ತೆರೆಯಬೇಡಿ, ಓ ಟಿ ಪಿ ಹೇಳಬೇಡಿ. ಬ್ಯಾಂಕಿನ ಅಧಿಕೃತ ಆ್ಯಪ್ ನೀವೇ ತೆರೆಯಿರಿ.',
    'ಇದು ಪಾರ್ಸೆಲ್ ಅಥವಾ ಕೊರಿಯರ್ ವಂಚನೆಯಾಗಿರಬಹುದು. ಕೊರಿಯರ್ ಕಂಪನಿಯೊಂದಿಗೆ ನೇರವಾಗಿ ಪರಿಶೀಲಿಸಿ. ಬೆದರಿಕೆಗೆ ಹಣ ಕೊಡಬೇಡಿ.',
    'ಇದು ವಂಚನೆಯ ಲಿಂಕ್ ಆಗಿರಬಹುದು. ಲಿಂಕ್ ತೆರೆಯಬೇಡಿ ಅಥವಾ ವೈಯಕ್ತಿಕ ಮಾಹಿತಿ ನೀಡಬೇಡಿ. ಅಧಿಕೃತ ವೆಬ್‌ಸೈಟ್ ನೀವೇ ತೆರೆಯಿರಿ.',
    'ಇದು ರಿಮೋಟ್ ಆಕ್ಸೆಸ್ ವಂಚನೆಯಾಗಿರಬಹುದು. ಅಪರಿಚಿತ ಆ್ಯಪ್ ಸ್ಥಾಪಿಸಬೇಡಿ ಅಥವಾ ಕರೆ ಮಾಡಿದವರಿಗೆ ನಿಮ್ಮ ಸ್ಕ್ರೀನ್ ತೋರಿಸಬೇಡಿ.',
),
 'te': (
    'ఇది డిజిటల్ అరెస్ట్ మోసం కావచ్చు. కాల్ ముగించి అధికారిక నంబర్ ద్వారా మీరే ధృవీకరించుకోండి. అరెస్ట్ తప్పించుకోవడానికి డబ్బు ఇవ్వవద్దు.',
    'ఇది యూపీఐ చెల్లింపు మోసం కావచ్చు. డబ్బు పొందడానికి యూపీఐ పిన్ అవసరం లేదు. తెలియని చెల్లింపు అభ్యర్థనలను తిరస్కరించండి.',
    'ఇది నకిలీ బ్యాంకు కేవైసీ కావచ్చు. సందేశంలోని లింక్ తెరవవద్దు, ఓ టి పి చెప్పవద్దు. బ్యాంకు అధికారిక యాప్ మీరే తెరవండి.',
    'ఇది పార్సిల్ లేదా కొరియర్ మోసం కావచ్చు. కొరియర్ కంపెనీతో నేరుగా ధృవీకరించుకోండి. బెదిరింపులకు డబ్బు ఇవ్వవద్దు.',
    'ఇది మోసపూరిత లింక్ కావచ్చు. దాన్ని తెరవవద్దు లేదా వ్యక్తిగత సమాచారం ఇవ్వవద్దు. అధికారిక వెబ్‌సైట్ మీరే తెరవండి.',
    'ఇది రిమోట్ యాక్సెస్ మోసం కావచ్చు. తెలియని యాప్ ఇన్‌స్టాల్ చేయవద్దు, కాల్ చేసిన వారికి మీ స్క్రీన్ చూపవద్దు.',
),
 'or': (
    'ଏହା ଡିଜିଟାଲ ଆରେଷ୍ଟ ଠକେଇ ହୋଇପାରେ। କଲ୍ କାଟି ନିଜେ ଅଧିକୃତ ନମ୍ବରରେ ଯାଞ୍ଚ କରନ୍ତୁ। ଗିରଫ ଏଡ଼ାଇବାକୁ ଟଙ୍କା ଦିଅନ୍ତୁ ନାହିଁ।',
    'ଏହା ୟୁପିଆଇ ପେମେଣ୍ଟ ଠକେଇ ହୋଇପାରେ। ଟଙ୍କା ପାଇବା ପାଇଁ ୟୁପିଆଇ ପିନ୍ ଦେବା ଦରକାର ନାହିଁ। ଅଜଣା ପେମେଣ୍ଟ ଅନୁରୋଧ ଗ୍ରହଣ କରନ୍ତୁ ନାହିଁ।',
    'ଏହା ବ୍ୟାଙ୍କର ନକଲି କେୱାଇସି ହୋଇପାରେ। ସନ୍ଦେଶର ଲିଙ୍କ ଖୋଲନ୍ତୁ ନାହିଁ, ଓ ଟି ପି କୁହନ୍ତୁ ନାହିଁ। ନିଜେ ବ୍ୟାଙ୍କର ଅଧିକୃତ ଆପ୍ ଖୋଲନ୍ତୁ।',
    'ଏହା ପାର୍ସଲ କିମ୍ବା କୋରିଅର ଠକେଇ ହୋଇପାରେ। କୋରିଅର କମ୍ପାନୀ ସହ ସିଧାସଳଖ ଯାଞ୍ଚ କରନ୍ତୁ। ଧମକରେ ଟଙ୍କା ଦିଅନ୍ତୁ ନାହିଁ।',
    'ଏହା ଠକେଇର ଲିଙ୍କ ହୋଇପାରେ। ଲିଙ୍କ ଖୋଲନ୍ତୁ ନାହିଁ କିମ୍ବା ବ୍ୟକ୍ତିଗତ ସୂଚନା ଦିଅନ୍ତୁ ନାହିଁ। ନିଜେ ଅଧିକୃତ ୱେବସାଇଟ୍ ଖୋଲନ୍ତୁ।',
    'ଏହା ରିମୋଟ ଆକ୍ସେସ ଠକେଇ ହୋଇପାରେ। ଅଜଣା ଆପ୍ ଇନଷ୍ଟଲ୍ କରନ୍ତୁ ନାହିଁ କିମ୍ବା କଲ୍ କରିଥିବା ବ୍ୟକ୍ତିଙ୍କୁ ସ୍କ୍ରିନ୍ ଦେଖାନ୍ତୁ ନାହିଁ।',
),
}
TOPIC_TEXT['mr'] = (
    'ही डिजिटल अटकेची फसवणूक असू शकते. कॉल बंद करा आणि अधिकृत क्रमांकावरून स्वतः खात्री करा. अटक टाळण्यासाठी पैसे देऊ नका.',
    'ही यूपीआय पेमेंटची फसवणूक असू शकते. पैसे स्वीकारण्यासाठी यूपीआय पिन टाकण्याची गरज नसते. अनोळखी पेमेंट विनंती नाकारा.',
    'ही बँकेच्या केवायसीची बनावट विनंती असू शकते. संदेशातील लिंक उघडू नका आणि ओ टी पी सांगू नका. बँकेचे अधिकृत ॲप स्वतः उघडा.',
    'ही पार्सल किंवा कुरिअरची फसवणूक असू शकते. कुरिअर कंपनीशी थेट संपर्क साधून खात्री करा. धमकीमुळे पैसे देऊ नका.',
    'ही फसवणुकीची लिंक असू शकते. लिंक उघडू नका किंवा वैयक्तिक माहिती देऊ नका. अधिकृत वेबसाइट स्वतः उघडा.',
    'ही रिमोट ॲक्सेसची फसवणूक असू शकते. अनोळखी ॲप बसवू नका आणि कॉल करणाऱ्याला तुमची स्क्रीन दाखवू नका.',
)
DIGITS = {'en':'one nine three zero','hi':'एक नौ तीन शून्य','bn':'এক নয় তিন শূন্য','kn':'ಒಂದು ಒಂಬತ್ತು ಮೂರು ಸೊನ್ನೆ','te':'ఒకటి తొమ్మిది మూడు సున్నా','or':'ଏକ ନଅ ତିନି ଶୂନ୍ୟ','mr':'एक नऊ तीन शून्य'}
TOPIC_TEXT.update({'ta': ('இது டிஜிட்டல் கைது மோசடியாக இருக்கலாம். கைது தவிர்க்க பணம் அனுப்பாதீர்கள்.',
        'இது யூ பி ஐ மோசடியாக இருக்கலாம். பணம் பெற பின் எண் தேவையில்லை.',
        'வங்கியின் அதிகாரப்பூர்வ செயலியில் நீங்களே சரிபார்க்கவும்.',
        'கூரியர் நிறுவனத்தை நேரடியாகத் தொடர்புகொள்ளவும்.',
        'சந்தேக இணைப்பைத் திறக்காதீர்கள். அதிகாரப்பூர்வ இணையதளத்தை நீங்களே திறக்கவும்.',
        'அறிமுகமில்லாத செயலியை நிறுவவோ திரையைப் பகிரவோ வேண்டாம்.'),
 'ml': ('ഇത് ഡിജിറ്റൽ അറസ്റ്റ് തട്ടിപ്പാകാം. അറസ്റ്റ് ഒഴിവാക്കാൻ പണം നൽകരുത്.',
        'ഇത് യു പി ഐ തട്ടിപ്പാകാം. പണം സ്വീകരിക്കാൻ പിൻ ആവശ്യമില്ല.',
        'ബാങ്കിന്റെ ഔദ്യോഗിക ആപ്പ് സ്വയം തുറന്ന് പരിശോധിക്കുക.',
        'കൊറിയർ കമ്പനിയുമായി നേരിട്ട് ബന്ധപ്പെടുക.',
        'സംശയകരമായ ലിങ്ക് തുറക്കരുത്. ഔദ്യോഗിക വെബ്സൈറ്റ് സ്വയം തുറക്കുക.',
        'അപരിചിത ആപ്പ് ഇൻസ്റ്റാൾ ചെയ്യുകയോ സ്ക്രീൻ പങ്കിടുകയോ ചെയ്യരുത്.'),
 'gu': ('આ ડિજિટલ ધરપકડની છેતરપિંડી હોઈ શકે છે. ધરપકડ ટાળવા પૈસા આપશો નહીં.',
        'આ યુ પી આઈ છેતરપિંડી હોઈ શકે છે. પૈસા મેળવવા પિનની જરૂર નથી.',
        'બેંકની અધિકૃત એપ જાતે ખોલીને તપાસો.',
        'કુરિયર કંપનીનો સીધો સંપર્ક કરો.',
        'શંકાસ્પદ લિંક ખોલશો નહીં. અધિકૃત વેબસાઇટ જાતે ખોલો.',
        'અજાણી એપ ઇન્સ્ટોલ કરશો નહીં કે સ્ક્રીન શેર કરશો નહીં.'),
 'pa': ('ਇਹ ਡਿਜੀਟਲ ਗ੍ਰਿਫਤਾਰੀ ਦੀ ਠੱਗੀ ਹੋ ਸਕਦੀ ਹੈ। ਗ੍ਰਿਫਤਾਰੀ ਤੋਂ ਬਚਣ ਲਈ ਪੈਸੇ ਨਾ ਦਿਓ।',
        'ਇਹ ਯੂ ਪੀ ਆਈ ਠੱਗੀ ਹੋ ਸਕਦੀ ਹੈ। ਪੈਸੇ ਲੈਣ ਲਈ ਪਿੰਨ ਦੀ ਲੋੜ ਨਹੀਂ।',
        'ਬੈਂਕ ਦੀ ਅਧਿਕਾਰਤ ਐਪ ਆਪ ਖੋਲ੍ਹ ਕੇ ਜਾਂਚ ਕਰੋ।',
        'ਕੁਰੀਅਰ ਕੰਪਨੀ ਨਾਲ ਸਿੱਧਾ ਸੰਪਰਕ ਕਰੋ।',
        'ਸ਼ੱਕੀ ਲਿੰਕ ਨਾ ਖੋਲ੍ਹੋ। ਅਧਿਕਾਰਤ ਵੈੱਬਸਾਈਟ ਆਪ ਖੋਲ੍ਹੋ।',
        'ਅਣਜਾਣ ਐਪ ਇੰਸਟਾਲ ਨਾ ਕਰੋ ਅਤੇ ਸਕਰੀਨ ਸਾਂਝੀ ਨਾ ਕਰੋ।')})
DIGITS.update({'ta': 'ஒன்று ஒன்பது மூன்று பூஜ்ஜியம்', 'ml': 'ഒന്ന് ഒമ്പത് മൂന്ന് പൂജ്യം', 'gu': 'એક નવ ત્રણ શૂન્ય', 'pa': 'ਇੱਕ ਨੌਂ ਤਿੰਨ ਸਿਫ਼ਰ'})
PROVIDER_LANG = {k: v[1] for k,v in LANGUAGE_NAMES.items()} | {'or':'od-IN'}
MODEL = 'bulbul:v3'
SPEAKER = 'shubh'

def speaker_for(language):
    return {'mr':'ratan','ta':'ratan','gu':'ratan','pa':'mani','ml':'shubh'}.get(language, SPEAKER)
CACHE = Path(__file__).resolve().parent.parent / 'voice_cache'
LOCK = threading.Lock()


def choose_topic(result):
    if result['level'] not in ('high','caution'):
        return 'generic'
    ids = {x['id'] for x in result['indicators']}
    # Strong category-specific evidence takes precedence over broad keyword matches.
    groups = (
        ('upi', {'receive_pin','collect_request','mistake_return','just_accept','mr_receive_pin','regional_context_receive_pin'}),
        ('arrest', {'arrest','regional_arrest','arrest_hinglish','safe_account','stay_on_call','mr_arrest','ta_arrest_demand','ml_arrest_demand','gu_arrest_demand','pa_arrest_demand','regional_context_arrest'}),
        ('courier', {'courier','regional_courier','mr_courier'}),
        ('kyc', {'kyc','regional_kyc','account_block','mr_kyc'}),
        ('remote', {'remote_control','remote_install','apk_install'}),
        ('phishing', {'url_lookalike','url_tld','url_ip','url_obfuscated','url_shortener','unverified_link','delivery_context','reward_context'}),
    )
    return next((topic for topic, signals in groups if ids & signals), 'generic')


def voice_text(language, level, topic):
    if language not in CONTENT or level not in LEVELS or topic not in TOPICS:
        raise ValueError('Invalid voice selection')
    if topic != 'generic' and level not in ('high','caution'):
        raise ValueError('Contextual warning requires high or caution level')
    generic = CONTENT[language]['voice'][LEVELS.index(level)]
    for number in ('1930','১৯৩০'):
        generic = generic.replace(number, DIGITS[language])
    prefix = '' if topic == 'generic' else TOPIC_TEXT[language][TOPICS.index(topic)] + ' '
    return prefix + generic


def voice_details(result):
    lang, level = result['language'], result['level']
    topic = choose_topic(result)
    speech = voice_text(lang, level, topic)
    return {'topic':topic, 'text':speech, 'display':speech.replace(DIGITS[lang], '1930')}


def cache_path(language, level, topic):
    script = voice_text(language, level, topic)
    digest = hashlib.sha256(f'{MODEL}|{speaker_for(language)}|{PROVIDER_LANG[language]}|{script}'.encode()).hexdigest()[:20]
    return CACHE / language / f'{level}-{topic}-{digest}.mp3'


def valid_audio(data):
    return len(data) >= 200 and len(data) <= 4*1024*1024 and (data.startswith(b'ID3') or (data[0]==255 and data[1]&224==224))


def cached(language, level, topic):
    path = cache_path(language, level, topic)
    try:
        if path.is_file() and valid_audio(path.read_bytes()):
            return path
    except OSError:
        pass
    return None


def configured():
    return bool(os.environ.get('SARVAM_API_KEY','').strip())


class VoiceError(Exception):
    pass


def synthesize(language, level, topic):
    text = voice_text(language, level, topic)  # validated before any I/O
    with LOCK:
        old = cached(language, level, topic)
        if old:
            return old
        key = os.environ.get('SARVAM_API_KEY','').strip()
        if not key:
            raise VoiceError('No speech API key configured. Use the local fallback or run.bat with your Sarvam key.')
        try:
            response = httpx.post('https://api.sarvam.ai/text-to-speech',
                headers={'api-subscription-key':key},
                json={'text':text,'language_code':PROVIDER_LANG[language], 'model':MODEL,
                      'speaker':speaker_for(language),'output_audio_codec':'mp3'}, timeout=httpx.Timeout(20,connect=5))
            if response.status_code != 200:
                raise VoiceError(f'Speech provider returned HTTP {response.status_code}. Check key, credits or service availability.')
            data = base64.b64decode(response.json()['audios'][0], validate=True)
            if not valid_audio(data):
                raise VoiceError('Speech provider returned invalid audio.')
        except VoiceError:
            raise
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError) as exc:
            raise VoiceError('Speech generation failed. Check internet or use the local fallback.') from exc
        path = cache_path(language, level, topic)
        temp = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=path.parent, suffix='.part', delete=False) as f:
                temp = Path(f.name); f.write(data)
            temp.replace(path)
        except OSError as exc:
            raise VoiceError('Cannot save generated speech. Check project folder permissions.') from exc
        finally:
            if temp: temp.unlink(missing_ok=True)
        return path
