"""ScamShield research pilot: same multilingual data, four classifiers, CPU only.
Synthetic examples, not a real-world accuracy estimate. No cloud requests.
Run from Semantic_Research with the downloaded models/indic-sbert directory.
Each row is a (suspicious, benign) pair. Translations of each scenario stay
in the same split. Native-speaker review of these examples is still required.
"""
import csv
import runpy
import time
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

# Training scenarios: credential disclosure, job deposit, coercive investigation.
TRAIN = {
'en': [('Tell our support officer the code you received to restore your account.', 'Your login code is 345678. Keep it private.'), ('A refundable deposit is required before you can start this job.', 'Your job interview is on Monday; no deposit is needed.'), ('Transfer your savings to the investigator to avoid legal action.', 'Contact the police station directly to ask about the case.')],
'hi': [('खाता चालू करने के लिए आया हुआ कोड हमारे कर्मचारी को बताएं।', 'आपका लॉगिन कोड 345678 है। इसे गोपनीय रखें।'), ('नौकरी शुरू करने से पहले वापसी योग्य जमा राशि भेजें।', 'आपका इंटरव्यू सोमवार को है। कोई जमा राशि नहीं चाहिए।'), ('कानूनी कार्रवाई से बचने के लिए अपनी बचत जांच अधिकारी को भेजें।', 'मामले की जानकारी के लिए सीधे पुलिस थाने से संपर्क करें।')],
'bn': [('অ্যাকাউন্ট চালু করতে পাওয়া কোডটি আমাদের কর্মীকে বলুন।', 'আপনার লগইন কোড 345678। এটি গোপন রাখুন।'), ('চাকরি শুরু করার আগে ফেরতযোগ্য জামানত পাঠান।', 'সোমবার আপনার সাক্ষাৎকার। কোনো জামানত লাগবে না।'), ('আইনি ব্যবস্থা এড়াতে আপনার সঞ্চয় তদন্তকারীকে পাঠান।', 'মামলার খবর জানতে সরাসরি থানায় যোগাযোগ করুন।')],
'kn': [('ಖಾತೆಯನ್ನು ಮತ್ತೆ ಸಕ್ರಿಯಗೊಳಿಸಲು ಬಂದ ಕೋಡ್ ಅನ್ನು ನಮ್ಮ ಸಿಬ್ಬಂದಿಗೆ ತಿಳಿಸಿ.', 'ನಿಮ್ಮ ಲಾಗಿನ್ ಕೋಡ್ 345678. ಅದನ್ನು ಗೌಪ್ಯವಾಗಿ ಇಡಿ.'), ('ಕೆಲಸ ಆರಂಭಿಸುವ ಮೊದಲು ಮರುಪಾವತಿಯಾಗುವ ಠೇವಣಿ ಕಳುಹಿಸಿ.', 'ನಿಮ್ಮ ಸಂದರ್ಶನ ಸೋಮವಾರ ಇದೆ. ಠೇವಣಿ ಅಗತ್ಯವಿಲ್ಲ.'), ('ಕಾನೂನು ಕ್ರಮ ತಪ್ಪಿಸಲು ನಿಮ್ಮ ಉಳಿತಾಯವನ್ನು ತನಿಖಾಧಿಕಾರಿಗೆ ಕಳುಹಿಸಿ.', 'ಪ್ರಕರಣದ ಬಗ್ಗೆ ನೇರವಾಗಿ ಪೊಲೀಸ್ ಠಾಣೆಯನ್ನು ಸಂಪರ್ಕಿಸಿ.')],
'te': [('ఖాతాను తిరిగి తెరవడానికి వచ్చిన కోడ్ మా సిబ్బందికి చెప్పండి.', 'మీ లాగిన్ కోడ్ 345678. దానిని రహస్యంగా ఉంచండి.'), ('ఉద్యోగం ప్రారంభించే ముందు తిరిగి ఇచ్చే డిపాజిట్ పంపండి.', 'మీ ఇంటర్వ్యూ సోమవారం ఉంది. డిపాజిట్ అవసరం లేదు.'), ('చట్టపరమైన చర్య తప్పించుకోవడానికి మీ పొదుపును దర్యాప్తు అధికారికి పంపండి.', 'కేసు గురించి నేరుగా పోలీస్ స్టేషన్‌ను సంప్రదించండి.')],
'or': [('ଖାତା ପୁଣି ଚାଲୁ କରିବାକୁ ଆସିଥିବା କୋଡ୍ ଆମ କର୍ମଚାରୀଙ୍କୁ କୁହନ୍ତୁ।', 'ଆପଣଙ୍କ ଲଗଇନ କୋଡ୍ 345678। ଏହାକୁ ଗୋପନ ରଖନ୍ତୁ।'), ('ଚାକିରି ଆରମ୍ଭ ପୂର୍ବରୁ ଫେରସ୍ତ ହେବା ଭଳି ଜମା ଟଙ୍କା ପଠାନ୍ତୁ।', 'ସୋମବାର ଆପଣଙ୍କ ସାକ୍ଷାତକାର। ଜମା ଟଙ୍କା ଦରକାର ନାହିଁ।'), ('ଆଇନଗତ କାର୍ଯ୍ୟାନୁଷ୍ଠାନ ଏଡ଼ାଇବାକୁ ନିଜ ସଞ୍ଚୟ ତଦନ୍ତ ଅଧିକାରୀଙ୍କୁ ପଠାନ୍ତୁ।', 'ମାମଲା ବିଷୟରେ ସିଧାସଳଖ ଥାନାରେ ଯୋଗାଯୋଗ କରନ୍ତୁ।')],
'mr': [('खाते पुन्हा सुरू करण्यासाठी आलेला कोड आमच्या कर्मचाऱ्याला सांगा.', 'तुमचा लॉगिन कोड 345678 आहे. तो गुप्त ठेवा.'), ('नोकरी सुरू करण्यापूर्वी परत मिळणारी अनामत रक्कम पाठवा.', 'तुमची मुलाखत सोमवारी आहे. अनामत रक्कम आवश्यक नाही.'), ('कायदेशीर कारवाई टाळण्यासाठी तुमची बचत तपास अधिकाऱ्याला पाठवा.', 'प्रकरणाची माहिती घेण्यासाठी थेट पोलीस ठाण्याशी संपर्क साधा.')],
'ta': [('கணக்கை மீண்டும் செயல்படுத்த வந்த குறியீட்டை எங்கள் ஊழியரிடம் கூறுங்கள்.', 'உங்கள் உள்நுழைவு குறியீடு 345678. அதை ரகசியமாக வைத்திருங்கள்.'), ('வேலையில் சேரும் முன் திருப்பித் தரப்படும் வைப்புத் தொகையை அனுப்புங்கள்.', 'உங்கள் நேர்காணல் திங்கட்கிழமை. வைப்புத் தொகை தேவையில்லை.'), ('சட்ட நடவடிக்கையைத் தவிர்க்க உங்கள் சேமிப்பை விசாரணை அதிகாரிக்கு அனுப்புங்கள்.', 'வழக்கு குறித்து நேரடியாக காவல் நிலையத்தைத் தொடர்பு கொள்ளுங்கள்.')],
'ml': [('അക്കൗണ്ട് വീണ്ടും പ്രവർത്തനക്ഷമമാക്കാൻ ലഭിച്ച കോഡ് ഞങ്ങളുടെ ജീവനക്കാരനോട് പറയുക.', 'നിങ്ങളുടെ ലോഗിൻ കോഡ് 345678 ആണ്. അത് രഹസ്യമായി സൂക്ഷിക്കുക.'), ('ജോലിയിൽ പ്രവേശിക്കുന്നതിന് മുമ്പ് തിരികെ ലഭിക്കുന്ന നിക്ഷേപത്തുക അയയ്ക്കുക.', 'നിങ്ങളുടെ അഭിമുഖം തിങ്കളാഴ്ചയാണ്. നിക്ഷേപത്തുക ആവശ്യമില്ല.'), ('നിയമനടപടി ഒഴിവാക്കാൻ നിങ്ങളുടെ സമ്പാദ്യം അന്വേഷണ ഉദ്യോഗസ്ഥന് അയയ്ക്കുക.', 'കേസിനെക്കുറിച്ച് നേരിട്ട് പോലീസ് സ്റ്റേഷനുമായി ബന്ധപ്പെടുക.')],
'gu': [('ખાતું ફરી ચાલુ કરવા મળેલો કોડ અમારા કર્મચારીને જણાવો.', 'તમારો લોગિન કોડ 345678 છે. તેને ગુપ્ત રાખો.'), ('નોકરી શરૂ કરતાં પહેલાં પરત મળતી થાપણ મોકલો.', 'તમારો ઇન્ટરવ્યૂ સોમવારે છે. થાપણની જરૂર નથી.'), ('કાયદાકીય કાર્યવાહી ટાળવા તમારી બચત તપાસ અધિકારીને મોકલો.', 'કેસ વિશે સીધો પોલીસ સ્ટેશનનો સંપર્ક કરો.')],
'pa': [('ਖਾਤਾ ਮੁੜ ਚਾਲੂ ਕਰਨ ਲਈ ਮਿਲਿਆ ਕੋਡ ਸਾਡੇ ਕਰਮਚਾਰੀ ਨੂੰ ਦੱਸੋ।', 'ਤੁਹਾਡਾ ਲਾਗਇਨ ਕੋਡ 345678 ਹੈ। ਇਸ ਨੂੰ ਗੁਪਤ ਰੱਖੋ।'), ('ਨੌਕਰੀ ਸ਼ੁਰੂ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਵਾਪਸ ਮਿਲਣ ਵਾਲੀ ਜਮ੍ਹਾਂ ਰਕਮ ਭੇਜੋ।', 'ਤੁਹਾਡੀ ਇੰਟਰਵਿਊ ਸੋਮਵਾਰ ਨੂੰ ਹੈ। ਜਮ੍ਹਾਂ ਰਕਮ ਦੀ ਲੋੜ ਨਹੀਂ।'), ('ਕਾਨੂੰਨੀ ਕਾਰਵਾਈ ਤੋਂ ਬਚਣ ਲਈ ਆਪਣੀ ਬਚਤ ਜਾਂਚ ਅਧਿਕਾਰੀ ਨੂੰ ਭੇਜੋ।', 'ਕੇਸ ਬਾਰੇ ਸਿੱਧਾ ਪੁਲਿਸ ਥਾਣੇ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।')],
}

# Different scenario templates: incoming-payment authorization, parcel fee,
# remote control of a banking device, and family impersonation.
TEST = {
'en': [('Authorize the collect request to release your scholarship payment.', 'Your scholarship payment has arrived. View your statement.'), ('The gift parcel can be released after you pay an unexpected insurance charge.', 'Your parcel is ready for collection at the service counter.'), ('Give the caller remote access to your phone to fix the banking problem.', 'The bank recommends updating its app from the official store.'), ('I lost my phone. Do not call me; send the emergency money to this new account.', 'I lost my phone. Please call my sister to confirm my new number.')],
'hi': [('छात्रवृत्ति की रकम पाने के लिए पैसे मांगने वाला अनुरोध मंजूर करें।', 'आपकी छात्रवृत्ति आ गई है। अपना बैंक विवरण देखें।'), ('उपहार का पार्सल लेने से पहले अचानक मांगा गया बीमा शुल्क भरें।', 'आपका पार्सल सेवा काउंटर से लेने के लिए तैयार है।'), ('बैंक की समस्या ठीक करने के लिए कॉल करने वाले को फोन का रिमोट एक्सेस दें।', 'बैंक ने आधिकारिक स्टोर से ऐप अपडेट करने की सलाह दी है।'), ('मेरा फोन खो गया है। मुझे कॉल मत करना, इस नए खाते में तुरंत पैसे भेजो।', 'मेरा फोन खो गया है। नया नंबर जांचने के लिए मेरी बहन को फोन करो।')],
'bn': [('বৃত্তির টাকা পেতে টাকা চাওয়ার অনুরোধটি অনুমোদন করুন।', 'আপনার বৃত্তির টাকা এসেছে। ব্যাংকের বিবরণ দেখুন।'), ('উপহারের পার্সেল ছাড়াতে হঠাৎ চাওয়া বিমার ফি আগে দিন।', 'আপনার পার্সেল পরিষেবা কাউন্টার থেকে নেওয়ার জন্য প্রস্তুত।'), ('ব্যাংকের সমস্যা ঠিক করতে ফোনকারীকে আপনার ফোনের দূরবর্তী নিয়ন্ত্রণ দিন।', 'ব্যাংক অফিসিয়াল স্টোর থেকে অ্যাপ আপডেট করার পরামর্শ দিয়েছে।'), ('আমার ফোন হারিয়েছে। ফোন কোরো না, এই নতুন অ্যাকাউন্টে জরুরি টাকা পাঠাও।', 'আমার ফোন হারিয়েছে। নতুন নম্বর যাচাই করতে আমার বোনকে ফোন করো।')],
'kn': [('ವಿದ್ಯಾರ್ಥಿವೇತನ ಪಡೆಯಲು ಹಣ ಕೇಳುವ ವಿನಂತಿಯನ್ನು ಅನುಮೋದಿಸಿ.', 'ನಿಮ್ಮ ವಿದ್ಯಾರ್ಥಿವೇತನ ಜಮೆಯಾಗಿದೆ. ಬ್ಯಾಂಕ್ ವಿವರ ಪರಿಶೀಲಿಸಿ.'), ('ಉಡುಗೊರೆ ಪಾರ್ಸೆಲ್ ಬಿಡಿಸಲು ಅನಿರೀಕ್ಷಿತ ವಿಮಾ ಶುಲ್ಕವನ್ನು ಪಾವತಿಸಿ.', 'ನಿಮ್ಮ ಪಾರ್ಸೆಲ್ ಸೇವಾ ಕೌಂಟರ್‌ನಲ್ಲಿ ಪಡೆಯಲು ಸಿದ್ಧವಾಗಿದೆ.'), ('ಬ್ಯಾಂಕಿಂಗ್ ಸಮಸ್ಯೆ ಸರಿಪಡಿಸಲು ಕರೆ ಮಾಡಿದವರಿಗೆ ನಿಮ್ಮ ಫೋನ್‌ನ ದೂರಸ್ಥ ನಿಯಂತ್ರಣ ನೀಡಿ.', 'ಅಧಿಕೃತ ಸ್ಟೋರ್‌ನಿಂದ ಆ್ಯಪ್ ನವೀಕರಿಸಲು ಬ್ಯಾಂಕ್ ಸಲಹೆ ನೀಡಿದೆ.'), ('ನನ್ನ ಫೋನ್ ಕಳೆದುಹೋಗಿದೆ. ಕರೆ ಮಾಡಬೇಡ, ಈ ಹೊಸ ಖಾತೆಗೆ ತುರ್ತು ಹಣ ಕಳುಹಿಸು.', 'ನನ್ನ ಫೋನ್ ಕಳೆದುಹೋಗಿದೆ. ಹೊಸ ಸಂಖ್ಯೆಯನ್ನು ಖಚಿತಪಡಿಸಲು ನನ್ನ ತಂಗಿಗೆ ಕರೆ ಮಾಡು.')],
 'te': [('స్కాలర్‌షిప్ డబ్బు పొందడానికి డబ్బు అడిగే అభ్యర్థనను ఆమోదించండి.', 'మీ స్కాలర్‌షిప్ జమ అయింది. బ్యాంకు స్టేట్‌మెంట్ చూడండి.'), ('బహుమతి పార్సిల్ విడుదలకు అనుకోకుండా అడిగిన బీమా రుసుము చెల్లించండి.', 'మీ పార్సిల్ సేవా కౌంటర్ వద్ద తీసుకోవడానికి సిద్ధంగా ఉంది.'), ('బ్యాంకింగ్ సమస్యను పరిష్కరించడానికి కాల్ చేసిన వ్యక్తికి మీ ఫోన్ రిమోట్ యాక్సెస్ ఇవ్వండి.', 'అధికారిక స్టోర్ నుంచి యాప్‌ను నవీకరించాలని బ్యాంకు సూచించింది.'), ('నా ఫోన్ పోయింది. నాకు కాల్ చేయకు, ఈ కొత్త ఖాతాకు అత్యవసరంగా డబ్బు పంపు.', 'నా ఫోన్ పోయింది. కొత్త నంబర్‌ను నిర్ధారించడానికి నా చెల్లికి కాల్ చేయి.')],
'or': [('ଛାତ୍ରବୃତ୍ତି ଟଙ୍କା ପାଇବାକୁ ଟଙ୍କା ମାଗିବା ଅନୁରୋଧକୁ ଅନୁମୋଦନ କରନ୍ତୁ।', 'ଆପଣଙ୍କ ଛାତ୍ରବୃତ୍ତି ଟଙ୍କା ଜମା ହୋଇଛି। ବ୍ୟାଙ୍କ ବିବରଣୀ ଦେଖନ୍ତୁ।'), ('ଉପହାର ପାର୍ସଲ ପାଇବାକୁ ହଠାତ୍ ମଗାଯାଇଥିବା ବୀମା ଶୁଳ୍କ ଦିଅନ୍ତୁ।', 'ଆପଣଙ୍କ ପାର୍ସଲ ସେବା କାଉଣ୍ଟରରୁ ନେବାକୁ ପ୍ରସ୍ତୁତ।'), ('ବ୍ୟାଙ୍କ ସମସ୍ୟା ଠିକ କରିବାକୁ କଲ କରିଥିବା ବ୍ୟକ୍ତିଙ୍କୁ ଫୋନର ଦୂରସ୍ଥ ନିୟନ୍ତ୍ରଣ ଦିଅନ୍ତୁ।', 'ଅଧିକୃତ ଷ୍ଟୋରରୁ ଆପ୍ ଅପଡେଟ୍ କରିବାକୁ ବ୍ୟାଙ୍କ ପରାମର୍ଶ ଦେଇଛି।'), ('ମୋ ଫୋନ ହଜିଛି। ମୋତେ କଲ କରନି, ଏହି ନୂଆ ଖାତାକୁ ଜରୁରୀ ଟଙ୍କା ପଠାଅ।', 'ମୋ ଫୋନ ହଜିଛି। ନୂଆ ନମ୍ବର ଯାଞ୍ଚ ପାଇଁ ମୋ ଭଉଣୀକୁ କଲ କର।')],
'mr': [('शिष्यवृत्तीचे पैसे मिळवण्यासाठी पैसे मागणारी विनंती मंजूर करा.', 'तुमची शिष्यवृत्ती जमा झाली आहे. बँक विवरण तपासा.'), ('भेटवस्तूचे पार्सल मिळवण्यासाठी अचानक मागितलेले विमा शुल्क भरा.', 'तुमचे पार्सल सेवा काउंटरवर घेण्यासाठी तयार आहे.'), ('बँकिंग समस्या सोडवण्यासाठी फोन करणाऱ्याला तुमच्या फोनचा रिमोट ॲक्सेस द्या.', 'बँकेने अधिकृत स्टोअरमधून ॲप अपडेट करण्याचा सल्ला दिला आहे.'), ('माझा फोन हरवला आहे. फोन करू नकोस, या नव्या खात्यात तातडीने पैसे पाठव.', 'माझा फोन हरवला आहे. नवीन नंबर तपासण्यासाठी माझ्या बहिणीला फोन कर.')],
'ta': [('உதவித்தொகையைப் பெற பணம் கோரும் கோரிக்கையை அங்கீகரியுங்கள்.', 'உங்கள் உதவித்தொகை வரவு வைக்கப்பட்டுள்ளது. வங்கிக் கணக்கு விவரத்தைப் பாருங்கள்.'), ('பரிசுப் பார்சலைப் பெற எதிர்பாராத காப்பீட்டுக் கட்டணத்தைச் செலுத்துங்கள்.', 'உங்கள் பார்சல் சேவை மையத்தில் பெறத் தயாராக உள்ளது.'), ('வங்கிச் சிக்கலைச் சரிசெய்ய அழைப்பவருக்கு உங்கள் தொலைபேசியை தொலைவிலிருந்து இயக்க அனுமதி கொடுங்கள்.', 'அதிகாரப்பூர்வ ஸ்டோரிலிருந்து செயலியைப் புதுப்பிக்க வங்கி அறிவுறுத்தியுள்ளது.'), ('என் போன் தொலைந்துவிட்டது. அழைக்காதே, இந்தப் புதிய கணக்குக்கு அவசரமாக பணம் அனுப்பு.', 'என் போன் தொலைந்துவிட்டது. புதிய எண்ணை உறுதிப்படுத்த என் சகோதரியை அழை.')],
'ml': [('സ്കോളർഷിപ്പ് ലഭിക്കാൻ പണം ആവശ്യപ്പെടുന്ന അഭ്യർത്ഥന അംഗീകരിക്കുക.', 'നിങ്ങളുടെ സ്കോളർഷിപ്പ് തുക ലഭിച്ചു. ബാങ്ക് സ്റ്റേറ്റ്മെന്റ് പരിശോധിക്കുക.'), ('സമ്മാനപ്പാഴ്സൽ ലഭിക്കാൻ അപ്രതീക്ഷിതമായി ആവശ്യപ്പെട്ട ഇൻഷുറൻസ് ഫീസ് അടയ്ക്കുക.', 'നിങ്ങളുടെ പാഴ്സൽ സേവന കൗണ്ടറിൽ നിന്ന് എടുക്കാൻ തയ്യാറാണ്.'), ('ബാങ്കിംഗ് പ്രശ്നം പരിഹരിക്കാൻ വിളിച്ചയാൾക്ക് നിങ്ങളുടെ ഫോണിന്റെ വിദൂര നിയന്ത്രണം നൽകുക.', 'ഔദ്യോഗിക സ്റ്റോറിൽ നിന്ന് ആപ്പ് പുതുക്കാൻ ബാങ്ക് നിർദേശിച്ചു.'), ('എന്റെ ഫോൺ നഷ്ടപ്പെട്ടു. വിളിക്കരുത്, ഈ പുതിയ അക്കൗണ്ടിലേക്ക് അടിയന്തരമായി പണം അയയ്ക്കൂ.', 'എന്റെ ഫോൺ നഷ്ടപ്പെട്ടു. പുതിയ നമ്പർ ഉറപ്പാക്കാൻ എന്റെ സഹോദരിയെ വിളിക്കൂ.')],
'gu': [('શિષ્યવૃત્તિ મેળવવા પૈસા માંગતી વિનંતી મંજૂર કરો.', 'તમારી શિષ્યવૃત્તિ જમા થઈ છે. બેંક સ્ટેટમેન્ટ જુઓ.'), ('ભેટનું પાર્સલ મેળવવા અચાનક માંગેલી વીમાની ફી ભરો.', 'તમારું પાર્સલ સેવા કાઉન્ટર પરથી લેવા તૈયાર છે.'), ('બેંકિંગ સમસ્યા ઉકેલવા ફોન કરનારને તમારા ફોનનું રિમોટ નિયંત્રણ આપો.', 'બેંકે અધિકૃત સ્ટોરમાંથી એપ અપડેટ કરવાની સલાહ આપી છે.'), ('મારો ફોન ખોવાઈ ગયો છે. ફોન ન કરશો, આ નવા ખાતામાં તાત્કાલિક પૈસા મોકલો.', 'મારો ફોન ખોવાઈ ગયો છે. નવો નંબર તપાસવા મારી બહેનને ફોન કરો.')],
'pa': [('ਵਜ਼ੀਫ਼ੇ ਦੀ ਰਕਮ ਲੈਣ ਲਈ ਪੈਸੇ ਮੰਗਣ ਵਾਲੀ ਬੇਨਤੀ ਮਨਜ਼ੂਰ ਕਰੋ।', 'ਤੁਹਾਡਾ ਵਜ਼ੀਫ਼ਾ ਜਮ੍ਹਾਂ ਹੋ ਗਿਆ ਹੈ। ਬੈਂਕ ਸਟੇਟਮੈਂਟ ਵੇਖੋ।'), ('ਤੋਹਫ਼ੇ ਦਾ ਪਾਰਸਲ ਲੈਣ ਲਈ ਅਚਾਨਕ ਮੰਗੀ ਗਈ ਬੀਮਾ ਫੀਸ ਭਰੋ।', 'ਤੁਹਾਡਾ ਪਾਰਸਲ ਸੇਵਾ ਕਾਊਂਟਰ ਤੋਂ ਲੈਣ ਲਈ ਤਿਆਰ ਹੈ।'), ('ਬੈਂਕਿੰਗ ਸਮੱਸਿਆ ਠੀਕ ਕਰਨ ਲਈ ਫੋਨ ਕਰਨ ਵਾਲੇ ਨੂੰ ਆਪਣੇ ਫੋਨ ਦਾ ਰਿਮੋਟ ਕੰਟਰੋਲ ਦਿਓ।', 'ਬੈਂਕ ਨੇ ਅਧਿਕਾਰਤ ਸਟੋਰ ਤੋਂ ਐਪ ਅੱਪਡੇਟ ਕਰਨ ਦੀ ਸਲਾਹ ਦਿੱਤੀ ਹੈ।'), ('ਮੇਰਾ ਫੋਨ ਗੁੰਮ ਗਿਆ ਹੈ। ਫੋਨ ਨਾ ਕਰੀਂ, ਇਸ ਨਵੇਂ ਖਾਤੇ ਵਿੱਚ ਜ਼ਰੂਰੀ ਪੈਸੇ ਭੇਜੀਂ।', 'ਮੇਰਾ ਫੋਨ ਗੁੰਮ ਗਿਆ ਹੈ। ਨਵਾਂ ਨੰਬਰ ਪੱਕਾ ਕਰਨ ਲਈ ਮੇਰੀ ਭੈਣ ਨੂੰ ਫੋਨ ਕਰੀਂ।')],
}


def flatten(data):
    return [(text, label, lang) for lang, pairs in data.items()
            for scam, benign in pairs for text, label in [(scam, 1), (benign, 0)]]


def score(name, lang, y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {'Model': name, 'Language': lang, 'Samples': len(y),
            'Accuracy (%)': round(100*accuracy_score(y, pred), 2),
            'Precision (%)': round(100*precision_score(y, pred, zero_division=0), 2),
            'Recall (%)': round(100*recall_score(y, pred, zero_division=0), 2),
            'F1 (%)': round(100*f1_score(y, pred, zero_division=0), 2),
            'Missed scams': int(fn), 'False alarms': int(fp)}


def main():
    root = Path(__file__).resolve().parent
    train = flatten(TRAIN)
    test = flatten(TEST)
    # Add original training examples equally to ALL four candidate models.
    source = root / 'original_training_data.py'
    original = runpy.run_path(str(source))
    train += [(t, label, 'original') for key, label in [('SUSPICIOUS', 1), ('BENIGN', 0)] for t in original[key]]
    norm = lambda t: ' '.join(t.casefold().split())
    assert not ({norm(t) for t, _, _ in train} & {norm(t) for t, _, _ in test}), 'Exact training/test overlap'
    x, y, _ = zip(*train)
    h, hy, langs = zip(*test)
    print(f'Training: {len(train)} messages | Test: {len(test)} messages | 11 languages', flush=True)
    print('Synthetic pilot only. Standalone classifiers, not whole ScamShield engine.', flush=True)
    rows = []
    def report(name, pred, ms):
        overall = score(name, 'ALL', hy, pred)
        overall['Batch ms/message'] = round(ms, 2)
        rows.append(overall)
        print('\n' + name, flush=True)
        for k, v in overall.items():
            if k not in ('Model', 'Language'):
                print(f'  {k}: {v}', flush=True)
        for lang in TEST:
            ids = [i for i, l in enumerate(langs) if l == lang]
            r = score(name, lang, [hy[i] for i in ids], [pred[i] for i in ids])
            r['Batch ms/message'] = ''
            rows.append(r)
    for name, classifier in [('TF-IDF + Logistic Regression', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)), ('TF-IDF + Linear SVM', LinearSVC(class_weight='balanced', random_state=42, max_iter=10000)), ('TF-IDF + Complement Naive Bayes', ComplementNB())]:
        print('Training ' + name, flush=True)
        model = make_pipeline(TfidfVectorizer(analyzer='char', ngram_range=(3, 5), max_features=14000), classifier)
        model.fit(x, y)
        start = time.perf_counter()
        pred = model.predict(h)
        report(name, pred, (time.perf_counter()-start)*1000/len(h))
    import os
    os.environ['HF_HUB_OFFLINE'] = '1'
    from sentence_transformers import SentenceTransformer
    print('\nLoading local IndicSBERT (CPU)...', flush=True)
    encoder = SentenceTransformer(str(root/'models'/'indic-sbert'), device='cpu', local_files_only=True, trust_remote_code=False)
    print('Encoding training data...', flush=True)
    x_vec = encoder.encode(list(x), batch_size=8, normalize_embeddings=True, show_progress_bar=True)
    svm = LinearSVC(class_weight='balanced', random_state=42, max_iter=10000)
    svm.fit(x_vec, y)
    print('Encoding unseen evaluation messages...', flush=True)
    start = time.perf_counter()
    h_vec = encoder.encode(list(h), batch_size=8, normalize_embeddings=True, show_progress_bar=True)
    pred = svm.predict(h_vec)
    report('IndicSBERT + Linear SVM', pred, (time.perf_counter()-start)*1000/len(h))
    out = root/'semantic_comparison.csv'
    with out.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f'\nSaved: {out}', flush=True)
    print('Review per-language missed scams and false alarms before selecting any model.', flush=True)


if __name__ == '__main__':
    main()
