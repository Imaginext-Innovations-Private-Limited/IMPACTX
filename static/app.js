/* No persistent storage. No analytics. No third-party script. */
"use strict";
const $ = id => document.getElementById(id);
const examples = {
  arrest: {channel:"call", text:"I am a CBI officer. Your Aadhaar is linked to money laundering. You are under digital arrest. Do not tell anyone. Transfer ₹25,000 immediately to avoid arrest."},
  upi: {channel:"upi", text:"Congratulations! Your ₹3,000 cashback is waiting. To receive money, enter your UPI PIN and approve the collect request immediately."},
  kyc: {channel:"sms", text:"Final warning: your bank KYC has expired. Account will be suspended today. Click the link to update now and share OTP with verification desk."},
  courier: {channel:"whatsapp", text:"Your courier parcel has been seized by customs for illegal drugs. You must pay a security deposit within 30 minutes to avoid legal action."},
  phish: {channel:"sms", text:"Dear customer, your SBI YONO account will be blocked today. Update your PAN now: http://sbi-kyc-update.xyz/login"},
  mistake: {channel:"upi", text:"Sir I sent Rs 5000 to your number by mistake please return it urgently, I will send you a request, just accept."},
  hinglish: {channel:"call", text:"Aap ka parcel mein drugs mila hai. CBI aapko arrest karegi. Abhi paise transfer karo warna jail hogi."},
  otp: {channel:"sms", text:"123456 is your OTP for login to HDFC NetBanking. Do not share this OTP with anyone. -HDFC Bank"},
  safe: {channel:"sms", text:"Hi, your parcel has been delivered to the front desk at 2 PM. Thank you for shopping with us."},
};
let cloudPreference=false, cloudFallback=false;
let lastResult=null, pendingRequest=null, groqConfigured=null, currentTab="text", recognition=null, micActive=false;
const supportedVoiceLocales={en:"en-IN",hi:"hi-IN",bn:"bn-IN",kn:"kn-IN",te:"te-IN",or:"or-IN",mr:"mr-IN",ta:"ta-IN",ml:"ml-IN",gu:"gu-IN",pa:"pa-IN"};
let speakingUtterance=null, recordingClip=null, clipUrl=null, voiceMode=null, voiceCheck=0, playbackAttempt=0, inputRevision=0, imageRequest=null, emailRequest=null, audioRequest=null, audioDurationSeconds=null, audioSelection=0, extractedQrPayloads=[], parsedEmailMeta=null, autoTimer=null, lastSignature=null;
function setStatus(text,error=false){$("status").textContent=text;$("status").classList.toggle("error",error)}
function setText(t){inputRevision++;$("message").value=t.slice(0,6000);$("char-count").textContent=`${$("message").value.length} / 6000`;}
function make(tag, text, className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el}
function switchTab(tab){if(tab!==currentTab){invalidateAssessment();if(imageRequest){imageRequest.abort();imageRequest=null;}if(emailRequest){emailRequest.abort();emailRequest=null;}if(audioRequest){audioRequest.abort();audioRequest=null;selectAudio($("audio-input").files?.[0]);}}currentTab=tab;document.querySelectorAll(".tab").forEach(el=>{const selected=el.dataset.tab===tab;el.classList.toggle("active",selected);el.setAttribute("aria-selected",String(selected))});$("image-tools").classList.toggle("hidden",tab!=="image");$("email-tools")?.classList.toggle("hidden",tab!=="email");$("voice-tools").classList.toggle("hidden",tab!=="voice");$("audio-tools").classList.toggle("hidden",tab!=="audio");$("input-language-tools").classList.toggle("hidden",tab==="text"||tab==="email");if(tab!=="voice"&&micActive){const old=recognition;recognition=null;micActive=false;old?.abort();$("voice-btn").classList.remove("recording");$("voice-label").textContent="Start microphone transcription";}if(tab==="voice"||tab==="audio")$("channel").value="call";if(tab==="email")$("channel").value="email";if(tab==="text")setStatus("Paste or edit text, then click Analyze.")}
function setAnalysisBusy(busy){const b=$("analyze-btn");b.disabled=busy;b.setAttribute("aria-busy",String(busy));b.textContent=busy?"Analyzing…":$("cloud-consent").checked?"✦ Analyze with AI →":"Analyze locally →";}
function updateCloudChoice(){
  const choice=$("cloud-consent"), offline=navigator.onLine===false;
  choice.disabled=offline||groqConfigured!==true;
  choice.checked=!choice.disabled&&cloudPreference;
  $("cloud-state").textContent=offline?"No network connection — local protection active":groqConfigured===null?"Checking availability…":groqConfigured===false?"Not configured — local only":choice.checked?(cloudFallback?"Cloud last attempt failed — next Analyze will retry":"On — online AI + local checks"):"Off — local only";
  if(!pendingRequest)setAnalysisBusy(false);
}
function networkChanged(){
  updateCloudChoice();
  if(navigator.onLine!==false&&groqConfigured!==true)loadAnalysisAvailability();
}
function setQrPreview(payloads){extractedQrPayloads=Array.isArray(payloads)?payloads:[];const el=$("qr-preview");if(!el)return;if(!extractedQrPayloads.length){el.textContent="";el.classList.add("hidden");return;}el.textContent=`QR code decoded (${extractedQrPayloads.length}): ${extractedQrPayloads[0].slice(0,120)}`;el.classList.remove("hidden");}
function currentSignature(useCloud){return JSON.stringify({t:$("message").value.trim(),c:$("channel").value,l:$("language").value,q:extractedQrPayloads,e:parsedEmailMeta?.from_raw||"",u:useCloud});}
function scheduleAutoProtect(immediate=false){
  if(autoTimer){clearTimeout(autoTimer);autoTimer=null;}
  if(!$("auto-protect")?.checked)return;
  if(imageRequest||emailRequest||audioRequest||micActive)return;
  if(!$("message").value.trim()&&!extractedQrPayloads.length)return;
  const run=()=>{autoTimer=null;if($("auto-protect")?.checked)requestAnalysis(true);};
  if(immediate)run(); else autoTimer=setTimeout(run,550);
}
async function scan(useCloud=false){
  useCloud=useCloud===true;const sig=currentSignature(useCloud);invalidateAssessment();const text=$("message").value.trim();
  if(!text&&!extractedQrPayloads.length){setStatus("Enter a message or select a demo first.",true);return;}
  const ctrl=new AbortController(), revision=inputRevision;pendingRequest=ctrl;setAnalysisBusy(true);
  setStatus(useCloud?"Analyzing context with AI and local safety checks…":"Analyzing locally…");
  try{
    const response=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text,channel:$("channel").value,language:$("language").value,cloud_consent:useCloud,qr_payloads:extractedQrPayloads.length?extractedQrPayloads:null,email_meta:parsedEmailMeta}),signal:ctrl.signal});
    const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"Analysis failed");
    if(pendingRequest!==ctrl||revision!==inputRevision)return;
    lastSignature=sig;cloudFallback=useCloud&&data.analysis_mode==="offline_fallback";updateCloudChoice();lastResult=data;render(data);$("results").querySelector(".evidence-details").open=false;if(window.matchMedia("(max-width: 760px)").matches)$("results-title").scrollIntoView({block:"start",behavior:"auto"});setStatus("Analysis complete. Indicators are signals, not proof.");
  }catch(error){if(error.name!=="AbortError"&&pendingRequest===ctrl&&revision===inputRevision)setStatus(error.message||"Could not contact the server.",true)}
  finally{if(pendingRequest===ctrl){pendingRequest=null;setAnalysisBusy(false);}}
}
function resetResult(){stopWarning();voiceCheck++;clipUrl=null;voiceMode=null;lastResult=null;$("empty-result").classList.remove("hidden");$("results").classList.add("hidden");$("listen-warning").disabled=true;}
function invalidateAssessment(){inputRevision++;lastSignature=null;if(autoTimer){clearTimeout(autoTimer);autoTimer=null;}if(pendingRequest){pendingRequest.abort();pendingRequest=null;}setAnalysisBusy(false);resetResult();}
function readyToAnalyze(){invalidateAssessment();setStatus($("message").value.trim()?"Ready. Click Analyze to check this message.":"Enter a message or select a demo first.");scheduleAutoProtect(false);}
function requestAnalysis(isAuto=false){
  if(imageRequest||emailRequest||audioRequest||micActive){if(!isAuto)setStatus("Finish text extraction or stop transcription before analyzing.",true);return;}
  if(!$("message").value.trim()&&!extractedQrPayloads.length){if(!isAuto)setStatus("Enter a message or select a demo first.",true);return;}
  updateCloudChoice();
  const useCloud=navigator.onLine!==false&&groqConfigured===true&&$("cloud-consent").checked;
  const sig=currentSignature(useCloud);
  if(isAuto&&sig===lastSignature)return;
  if(pendingRequest)pendingRequest.abort();
  return scan(useCloud);
}
async function loadAnalysisAvailability(){try{const r=await fetch("/api/health",{cache:"no-store"});if(r.ok){const d=await r.json();if(typeof d.groq_configured==="boolean")groqConfigured=d.groq_configured||d.live_reputation_configured===true;const db=d.threat_db, dbEl=$("threat-db-status");if(dbEl&&db){dbEl.textContent=db.present?`Offline threat DB: ${Number(db.unique_hashes||0).toLocaleString()} hashes · age ${db.age_hours ?? "?"}h (${db.source||"PhishTank"})`:"Offline threat DB not loaded.";}}}catch{ /* Stay local if health cannot be checked. */ }finally{if(groqConfigured===null)groqConfigured=false;updateCloudChoice();}}
// A classifier signal is not a literal matched phrase or proof of fraud.
const modelOnlyNotes=Object.freeze({
  en:"The local machine learning model found suspicious text patterns. No specific scam rule matched. Verify the sender independently.",
  hi:"स्थानीय मशीन लर्निंग मॉडल को संदेश में संदिग्ध पैटर्न मिले। किसी खास धोखाधड़ी नियम का मिलान नहीं हुआ। प्रेषक की स्वतंत्र रूप से जाँच करें।",
  bn:"স্থানীয় মেশিন লার্নিং মডেল বার্তায় সন্দেহজনক ধরন শনাক্ত করেছে। কোনো নির্দিষ্ট প্রতারণার নিয়ম মেলেনি। প্রেরককে স্বাধীনভাবে যাচাই করুন।",
  kn:"ಸ್ಥಳೀಯ ಯಂತ್ರ ಕಲಿಕೆ ಮಾದರಿಯು ಸಂದೇಶದಲ್ಲಿ ಅನುಮಾನಾಸ್ಪದ ಮಾದರಿಗಳನ್ನು ಗುರುತಿಸಿದೆ. ಯಾವುದೇ ನಿರ್ದಿಷ್ಟ ವಂಚನೆ ನಿಯಮ ಹೊಂದಿಕೆಯಾಗಿಲ್ಲ. ಕಳುಹಿಸಿದವರನ್ನು ಸ್ವತಂತ್ರವಾಗಿ ಪರಿಶೀಲಿಸಿ।",
  te:"స్థానిక మెషిన్ లెర్నింగ్ నమూనా సందేశంలో అనుమానాస్పద నమూనాలను గుర్తించింది. నిర్దిష్ట మోసం నియమం ఏదీ సరిపోలలేదు. పంపిన వారిని స్వతంత్రంగా ధృవీకరించండి.",
  or:"ସ୍ଥାନୀୟ ମେସିନ୍ ଲର୍ଣ୍ଣିଂ ମଡେଲ୍ ବାର୍ତ୍ତାରେ ସନ୍ଦେହଜନକ ଢାଞ୍ଚା ଚିହ୍ନଟ କରିଛି। କୌଣସି ନିର୍ଦ୍ଦିଷ୍ଟ ଠକେଇ ନିୟମ ମେଳ ଖାଇନାହିଁ। ପ୍ରେରକଙ୍କୁ ସ୍ୱାଧୀନ ଭାବେ ଯାଞ୍ଚ କରନ୍ତୁ।",
  mr:"स्थानिक मशीन लर्निंग मॉडेलला संदेशात संशयास्पद नमुने आढळले. कोणताही विशिष्ट फसवणूक नियम जुळला नाही. पाठवणाऱ्याची स्वतंत्रपणे पडताळणी करा.",
  ta:"உள்ளூர் இயந்திரக் கற்றல் மாதிரி சந்தேகத்திற்குரிய சொல் வடிவங்களைக் கண்டறிந்தது. குறிப்பிட்ட மோசடி விதி பொருந்தவில்லை. அனுப்பியவரை தனியாகச் சரிபார்க்கவும்.",
  ml:"പ്രാദേശിക മെഷീൻ ലേണിങ് മാതൃക സംശയകരമായ എഴുത്ത് രീതികൾ കണ്ടെത്തി. പ്രത്യേക തട്ടിപ്പ് നിയമം പൊരുത്തപ്പെട്ടില്ല. അയച്ചയാളെ സ്വതന്ത്രമായി പരിശോധിക്കുക.",
  gu:"સ્થાનિક મશીન લર્નિંગ મોડેલે શંકાસ્પદ લખાણના નમૂના શોધ્યા છે. છેતરપિંડીનો કોઈ ચોક્કસ નિયમ મળ્યો નથી. મોકલનારની સ્વતંત્ર રીતે તપાસ કરો.",
  pa:"ਸਥਾਨਕ ਮਸ਼ੀਨ ਲਰਨਿੰਗ ਮਾਡਲ ਨੂੰ ਸ਼ੱਕੀ ਲਿਖਤ ਦੇ ਨਮੂਨੇ ਮਿਲੇ ਹਨ। ਕੋਈ ਖਾਸ ਧੋਖਾਧੜੀ ਨਿਯਮ ਨਹੀਂ ਮਿਲਿਆ। ਭੇਜਣ ਵਾਲੇ ਦੀ ਸੁਤੰਤਰ ਜਾਂਚ ਕਰੋ."
});
function modelOnlyNote(data){
  if(data.level!=="review"||data.model_signal!=="suspicious_wording"||data.score!==2||data.indicators.length!==0||data.analysis_mode==="hybrid")return "";
  return modelOnlyNotes[data.language]||modelOnlyNotes.en;
}
// No-signal is not a safety verdict. Keep the assessment and audio levels unchanged.
const safetyUnconfirmedLabels=Object.freeze({en:"SAFETY NOT CONFIRMED",hi:"सुरक्षा की पुष्टि नहीं हुई",bn:"নিরাপত্তা নিশ্চিত নয়",kn:"ಸುರಕ್ಷತೆ ದೃಢಪಟ್ಟಿಲ್ಲ",te:"భద్రత నిర్ధారణ కాలేదు",or:"ସୁରକ୍ଷା ନିଶ୍ଚିତ ନୁହେଁ",mr:"सुरक्षिततेची खात्री नाही",ta:"பாதுகாப்பு உறுதி செய்யப்படவில்லை",ml:"സുരക്ഷ ഉറപ്പാക്കിയിട്ടില്ല",gu:"સુરક્ષાની ખાતરી નથી",pa:"ਸੁਰੱਖਿਆ ਦੀ ਪੁਸ਼ਟੀ ਨਹੀਂ ਹੋਈ"});
const noClearSignalLabels=Object.freeze({en:"NO CLEAR SIGNAL",hi:"कोई स्पष्ट संकेत नहीं",bn:"স্পষ্ট কোনো সংকেত নেই",kn:"ಸ್ಪಷ್ಟ ಸೂಚನೆ ಇಲ್ಲ",te:"స్పష్టమైన సంకేతం లేదు",or:"ସ୍ପଷ୍ଟ ସଙ୍କେତ ନାହିଁ",mr:"स्पष्ट संकेत नाही",ta:"தெளிவான அறிகுறி இல்லை",ml:"വ്യക്തമായ സൂചനയില്ല",gu:"સ્પષ્ટ સંકેત નથી",pa:"ਕੋਈ ਸਪੱਸ਼ਟ ਸੰਕੇਤ ਨਹੀਂ"});
function safetyUnconfirmed(data){return data.level==="no_clear_signal"||data.level==="unknown";}
function safetyNote(data){
  if(!safetyUnconfirmed(data))return "";
  // Reuse the existing localized warning, including the independent-verification advice.
  const warning=data.display_warning||data.spoken_warning||"Safety is not confirmed. Verify the sender independently.";
  return warning;
}
function safetyLabel(data){const labels=data.level==="no_clear_signal"?noClearSignalLabels:safetyUnconfirmedLabels;return labels[data.language]||labels.en;}
function coverageNote(data){
  if(!safetyUnconfirmed(data)||data.analysis_mode==="hybrid")return "";
  return "Offline checks can miss unfamiliar scams, especially in regional or mixed-language messages. If online analysis becomes available, you may choose to run it; still verify independently.";
}
function render(data){$("empty-result").classList.add("hidden");$("results").classList.remove("hidden");$("analysis-mode").textContent=data.analysis_note||"Offline Protection — local checks only (zero external requests).";const ec=data.engine_contributions, ecEl=$("engine-contributions");if(ecEl&&ec){ecEl.textContent=`Engines: Rules=${ec.local_rules?"on":"off"} · TextML=${ec.text_ml} · URL-ML=${ec.url_ml} · ThreatDB=${ec.local_threat_db} · QR=${ec.qr_decoder} · Identity=${ec.identity_verifier} · LiveURL=${ec.live_url_reputation} · CloudAI=${ec.cloud_llm}`;ecEl.classList.remove("hidden");}else if(ecEl){ecEl.textContent="";ecEl.classList.add("hidden");}const level=data.level;const names={high:"HIGH RISK",caution:"CAUTION",review:"REVIEW",no_clear_signal:"NO CLEAR SIGNAL",unknown:"INSUFFICIENT"};$("risk-title").textContent=data.title;$("risk-level").textContent=safetyUnconfirmed(data)?safetyLabel(data):(names[level]||level);$("risk-level").className=`risk-badge ${level}`;$("risk-summary").textContent=data.summary;const unconfirmed=safetyUnconfirmed(data);$("safety-note").textContent=safetyNote(data);$("safety-note").lang=data.language||"en";$("safety-note").classList.toggle("hidden",!unconfirmed);$("coverage-note").textContent=coverageNote(data);$("coverage-note").classList.toggle("hidden",!coverageNote(data));const idInfo=data.identity, idEl=$("identity-note");if(idEl&&idInfo&&(idInfo.from_address||idInfo.claimed_organisations?.length)){const claims=Object.entries(idInfo.authentication_headers?.claims||{}).map(([k,v])=>`${k.toUpperCase()}=${v}`).join(", ");const parts=[idInfo.from_address?`Sender: ${idInfo.from_address}`:"Sender: unknown",idInfo.claimed_organisations?.length?`Claimed org: ${idInfo.claimed_organisations.join(", ")}`:"",idInfo.official_domain_match?"Domain matches registry (NOT independently authenticated)":"",claims?`Header claims (unverified): ${claims}`:"No sender authentication verified"];idEl.textContent=parts.filter(Boolean).join(" · ");idEl.classList.remove("hidden");}else if(idEl){idEl.textContent="";idEl.classList.add("hidden");}$("risk-index-panel").classList.toggle("hidden",unconfirmed);const mlNote=modelOnlyNote(data);$("model-only-note").textContent=mlNote;$("model-only-note").lang=data.language||"en";$("model-only-note").classList.toggle("hidden",!mlNote);$("evidence-label").textContent=mlNote?"Evidence details — ML warning":"Evidence details";$("risk-fill").className=`risk-fill ${level}`;$("risk-fill").style.width=(data.score*10)+"%";$("risk-score").textContent=`Index ${data.score}/10`;$("indicator-count").textContent=String(data.indicators.length);const indicators=$("indicators");indicators.replaceChildren();if(!data.indicators.length)indicators.append(make("p",mlNote||"No explicit warning indicators found. This does not mean the communication is safe.","no-indicators"));data.indicators.forEach(item=>{const holder=make("div",undefined,"indicator");holder.append(make("h5",item.title),make("p",item.explanation),make("span",`Matched: “${item.evidence}”`,"evidence"));indicators.append(holder)});const acts=$("actions");acts.replaceChildren();data.actions.forEach(t=>acts.append(make("li",t)));const cats=$("categories");cats.replaceChildren();data.categories.slice(0,4).forEach(t=>cats.append(make("span",t)));$("spoken-preview").textContent=data.voice_context?.display||data.display_warning||data.spoken_warning||"";$("spoken-preview").lang=data.voice_lang||"en";updateVoiceAvailability();}
async function extractImage(file){if(!file)return;invalidateAssessment();setText("");setQrPreview([]);parsedEmailMeta=null;$("image-file-name").textContent=file.name;if(file.size>4*1024*1024){setStatus("Screenshot must be under 4 MB.",true);return}if(imageRequest)imageRequest.abort();const ctrl=new AbortController();imageRequest=ctrl;const revision=inputRevision;const fd=new FormData();fd.append("file",file);setStatus("Extracting text and QR codes from screenshot…");try{const response=await fetch("/api/ocr?language="+encodeURIComponent($("input-language").value),{method:"POST",body:fd,signal:ctrl.signal});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"OCR failed");if(imageRequest!==ctrl||revision!==inputRevision)return;setText(data.text||"");setQrPreview(data.qr_payloads||[]);$("channel").value="image";setStatus(data.qr_payloads?.length?"QR code decoded from screenshot. Review and click Analyze.":"Screenshot text extracted. Review and correct the text, then click Analyze.");scheduleAutoProtect(true);}catch(err){if(err.name!=="AbortError"&&imageRequest===ctrl)setStatus(err.message,true)}finally{if(imageRequest===ctrl)imageRequest=null}}
async function parseEmailUpload(file){if(!file)return;invalidateAssessment();setText("");setQrPreview([]);parsedEmailMeta=null;if($("email-file-name"))$("email-file-name").textContent=file.name;if(file.size>4*1024*1024){setStatus("Email file must be under 4 MB.",true);return}if(emailRequest)emailRequest.abort();const ctrl=new AbortController();emailRequest=ctrl;const revision=inputRevision;const fd=new FormData();fd.append("file",file);setStatus("Parsing .eml email locally…");try{const response=await fetch("/api/parse-email",{method:"POST",body:fd,signal:ctrl.signal});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"Email parsing failed");if(emailRequest!==ctrl||revision!==inputRevision)return;parsedEmailMeta=data.email_meta||null;setText(data.text||"");$("channel").value="email";setStatus("Email parsed locally. Review and click Analyze.");scheduleAutoProtect(true);}catch(err){if(err.name!=="AbortError"&&emailRequest===ctrl)setStatus(err.message,true)}finally{if(emailRequest===ctrl)emailRequest=null}}
function startVoice(){const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SpeechRecognition){setStatus("Browser dictation is not available in this browser (Brave and Firefox do not support it). Use Chrome or Edge, upload a recording, or paste the call transcript.",true);return}if(micActive){recognition?.stop();return}recognition=new SpeechRecognition();recognition.lang=supportedVoiceLocales[$("input-language").value]||"en-IN";recognition.continuous=true;recognition.interimResults=true;let base=$("message").value.trim(),final="";const activeRecognition=recognition;recognition.onresult=event=>{if(recognition!==activeRecognition)return;let interim="";for(let i=event.resultIndex;i<event.results.length;i++){const transcript=event.results[i][0].transcript;if(event.results[i].isFinal)final+=" "+transcript;else interim+=" "+transcript}setText([base,final.trim(),interim.trim()].filter(Boolean).join(" "));invalidateAssessment();setStatus("Transcribing… stop the microphone, then click Analyze.")};recognition.onerror=e=>setStatus("Microphone transcription issue: "+e.error,true);recognition.onend=()=>{if(recognition!==activeRecognition)return;micActive=false;$("voice-btn").classList.remove("recording");$("voice-label").textContent="Start microphone transcription";setStatus("Transcription ended. Review the text, then click Analyze.")};try{recognition.start();micActive=true;$("voice-btn").classList.add("recording");$("voice-label").textContent="Stop transcription";setStatus("Listening via browser speech service; do not dictate confidential details.")}catch(e){setStatus(e.message,true)}}
async function transcribeAudio(){
  const file=$("audio-input").files?.[0];
  if(!file){setStatus("Choose an audio recording first.",true);return}
  if(!$('audio-consent').checked){setStatus("Confirm permission before sending audio to Sarvam AI.",true);return}
  if(!Number.isFinite(audioDurationSeconds)||audioDurationSeconds<=0||audioDurationSeconds>180){setStatus("Choose a readable recording up to 3 minutes long.",true);return}
  if(file.size>20*1024*1024){setStatus("Audio file limit is 20 MB.",true);return}
  if(micActive){recognition?.abort();recognition=null;micActive=false;$("voice-btn").classList.remove("recording");$("voice-label").textContent="Start microphone transcription";}
  invalidateAssessment();setText("");
  if(audioRequest)audioRequest.abort();
  const ctrl=new AbortController();audioRequest=ctrl;
  const revision=inputRevision, button=$("transcribe-audio-btn");
  const fd=new FormData();fd.append("file",file);
  fd.append("duration_seconds",String(audioDurationSeconds));
  fd.append("consent","true");
  button.disabled=true;button.textContent="Transcribing…";
  setStatus("Sending the recording to Sarvam AI. Longer recordings use batch transcription…");
  try{
    const response=await fetch("/api/transcribe-audio?language="+encodeURIComponent($("input-language").value),{method:"POST",body:fd,signal:ctrl.signal});
    const data=await response.json();
    if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"Audio transcription failed");
    if(audioRequest!==ctrl||revision!==inputRevision)return;
    setText(data.text);$("channel").value="call";
    resetResult();
    setStatus("Transcription complete. Review and correct the text, then click Analyze.");
  }catch(error){if(error.name!=="AbortError"&&audioRequest===ctrl)setStatus(error.message||"Could not transcribe this recording.",true)}
  finally{if(audioRequest===ctrl){audioRequest=null;button.disabled=!$("audio-input").files?.[0]||!$("audio-consent").checked||!audioDurationSeconds||audioDurationSeconds>180;button.textContent="Transcribe recording"}}
}
function selectAudio(file){
  const button=$("transcribe-audio-btn");
  const selection=++audioSelection;
  if(audioRequest){audioRequest.abort();audioRequest=null;}
  audioDurationSeconds=null;button.disabled=true;button.textContent="Transcribe recording";
  $("audio-consent").checked=false;
  if(!file){$("audio-file-name").textContent="No audio file selected.";return}
  invalidateAssessment();setText("");
  $("audio-file-name").textContent=`Selected: ${file.name} · ${(file.size/1024/1024).toFixed(2)} MB`;
  if(file.size>20*1024*1024){button.disabled=true;setStatus("Audio file limit is 20 MB.",true);return}
  const url=URL.createObjectURL(file), probe=new Audio();
  probe.preload="metadata";probe.src=url;
  probe.onloadedmetadata=()=>{URL.revokeObjectURL(url);if(selection!==audioSelection)return;audioDurationSeconds=probe.duration;if(!Number.isFinite(probe.duration)||probe.duration<=0){button.disabled=true;setStatus("Could not read this recording's duration. Choose another audio file.",true)}else if(probe.duration>180){button.disabled=true;setStatus("Choose a recording that is 3 minutes or shorter.",true)}else{button.disabled=!$("audio-consent").checked;setStatus(`Recording selected (${Math.ceil(probe.duration)} seconds). It will be sent to Sarvam AI for transcription.`)}};
  probe.onerror=()=>{URL.revokeObjectURL(url);if(selection!==audioSelection)return;button.disabled=true;setStatus("Could not read this audio file. Choose another recording.",true)};
}
function copyText(text,okMsg){if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(text).then(()=>setStatus(okMsg)).catch(()=>setStatus("Copy failed. Please select and copy manually.",true));else{const temp=document.createElement("textarea");temp.value=text;document.body.append(temp);temp.select();try{if(document.execCommand("copy"))setStatus(okMsg);else setStatus("Copy failed. Please select and copy manually.",true)}catch{setStatus("Copy failed.",true)}temp.remove()}}
function copyReport(){if(!lastResult)return;const d=lastResult;copyText(["SCAMSHIELD AI — SAFETY SCREENING",d.title,d.summary,d.analysis_note||"Local analysis",...(safetyUnconfirmed(d)?[safetyLabel(d),safetyNote(d),...(coverageNote(d)?[coverageNote(d)]:[])]:[`Risk index: ${d.score}/10 (heuristic, NOT a probability)`]),...(modelOnlyNote(d)?[modelOnlyNote(d)]:[]),"Indicators:",...d.indicators.map(i=>`- ${i.title}: ${i.evidence}`),"Recommended actions:",...d.actions.map((a,i)=>`${i+1}. ${a}`),"Reporting: https://cybercrime.gov.in/ · https://sancharsaathi.gov.in/ · 1930",d.disclaimer].join("\n"),"Safety summary copied.")}
function copyComplaint(){if(!lastResult||!lastResult.complaint)return;copyText(lastResult.complaint,"Complaint draft copied. Review it, add amounts and transaction details, then submit at cybercrime.gov.in or call 1930.")}
/* The warning read aloud is prewritten server guidance. NEVER speak the submitted
   SMS, call transcript, indicator evidence or complaint: those may contain secrets. */
function findCompatibleVoice(locale){
  if(!window.speechSynthesis)return null;
  const voices=window.speechSynthesis.getVoices();
  const normalized=(locale||"en-IN").toLowerCase();
  const language=normalized.split("-")[0];
  return voices.find(v=>v.lang.toLowerCase()===normalized)
      ||voices.find(v=>v.lang.toLowerCase().split("-")[0]===language)
      ||null;
}
function voiceParams(result){return {language:result.language,level:result.level,topic:result.voice_context?.topic||"generic"};}
function audioUrl(params){return "/api/voice/audio?"+new URLSearchParams(params);}
function showVoice(mode,path,label,result){
  voiceMode=mode;clipUrl=path;$("voice-ready").textContent=label;$("voice-ready").className="available";
  $("listen-warning").disabled=false;
  $("spoken-preview").textContent=mode==="legacy"?(result.display_warning||result.spoken_warning):result.voice_context?.display||result.display_warning||result.spoken_warning;
}
/* Last-resort bundled clips (static/voices-basic): play in every browser with no internet or key. */
async function findBasicClip(params,current){
  const names=[];
  if(params.topic!=="generic"&&params.level==="high")names.push(`${params.level}-${params.topic}`);
  names.push(`${params.level}-generic`);
  for(const name of names){
    const path=`/static/voices-basic/${params.language}/${name}.mp3`;
    try{const r=await fetch(path,{method:"HEAD",cache:"no-store"});if(!current())return null;
      if(r.ok)return {path,specific:name!==`${params.level}-generic`};
    }catch{/* optional */}
  }
  return null;
}
async function updateVoiceAvailability(skipOnline=false){
  if(!lastResult)return;
  const result=lastResult, check=++voiceCheck, params=voiceParams(result);
  const current=()=>result===lastResult&&check===voiceCheck;
  const status=$("voice-ready"), listen=$("listen-warning");
  clipUrl=null;voiceMode=null;listen.disabled=true;status.textContent="Checking spoken warning options…";
  try{
    const response=await fetch("/api/voice/status?"+new URLSearchParams(params),{cache:"no-store"});
    if(response.ok){const info=await response.json();if(!current())return;
      if(info.cached){showVoice("cache",audioUrl(params),"Ready · saved AI warning",result);return;}
      if(info.configured&&!skipOnline){showVoice("online",null,"Ready · generate AI warning on request",result);return;}
    }
  }catch{/* fall back */}
  if(!current())return;
  const browserVoice=findCompatibleVoice(result.voice_lang);
  // A generic saved clip must not be presented as the context-specific warning.
  if(params.topic!=="generic"&&browserVoice){showVoice("browser",null,"Ready · browser context-specific voice",result);return;}
  if(params.topic!=="generic"){
    const general={...params,topic:"generic"};
    try{const r=await fetch("/api/voice/status?"+new URLSearchParams(general),{cache:"no-store"});
      if(r.ok){const info=await r.json();if(!current())return;if(info.cached){showVoice("legacy",audioUrl(general),"Ready · saved general AI warning (offline fallback)",result);return;}}
    }catch{/* optional */}
  }
  for(const ext of ["webm","mp3","m4a"]){
    const path=`/static/voices/${params.language}/${params.level}.${ext}`;
    try{const response=await fetch(path,{method:"HEAD",cache:"no-store"});if(!current())return;
      if(response.ok){showVoice("legacy",path,"Ready · saved general warning (offline fallback)",result);return;}
    }catch{/* optional */}
  }
  if(!current())return;
  if(browserVoice){showVoice("browser",null,"Ready · browser voice",result);return;}
  const basic=await findBasicClip(params,current);
  if(!current())return;
  if(basic){showVoice(basic.specific?"cache":"legacy",basic.path,basic.specific?"Ready · basic offline voice (works in any browser)":"Ready · basic offline voice, general warning (works in any browser)",result);return;}
  status.textContent="No saved or compatible voice. Launch run.bat with your Sarvam key to generate audio; written guidance remains available.";
  status.className="unsupported";listen.disabled=true;
}
function stopWarning(){
  playbackAttempt++;
  if(window.speechSynthesis)window.speechSynthesis.cancel();
  if(recordingClip){recordingClip.pause();recordingClip.currentTime=0;recordingClip=null;}
  speakingUtterance=null;
  if($("stop-warning"))$("stop-warning").disabled=true;
  if($("listen-warning"))$("listen-warning").textContent="▶ Hear warning";
}
async function speakWarning(){
  if(!lastResult||!voiceMode)return;
  stopWarning();const attempt=playbackAttempt,result=lastResult,mode=voiceMode;
  const current=()=>lastResult===result&&playbackAttempt===attempt;
  let path=clipUrl;
  $("stop-warning").disabled=false;
  if(mode==="online"){
    $("listen-warning").textContent="Generating audio…";$("listen-warning").disabled=true;
    try{
      const params=voiceParams(result);
      const response=await fetch("/api/voice/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(params)});
      if(!response.ok)throw new Error("AI speech is unavailable. Check key, credits and connection.");
      if(!current())return;
      path=audioUrl(params);showVoice("cache",path,"Ready · saved AI warning",result);
    }catch(err){if(current()){stopWarning();await updateVoiceAvailability(true);if(lastResult===result)setStatus(err.message+" Use Hear warning again if a fallback is available.",true);}return;}
  }
  if(path){
    const audio=new Audio(path);recordingClip=audio;
    $("listen-warning").textContent="🔊 Playing…";
    audio.onended=()=>{if(recordingClip===audio)stopWarning()};
    audio.onerror=()=>{if(recordingClip===audio){stopWarning();setStatus("Audio could not play. Check the file or browser.",true)}};
    audio.play().catch(err=>{if(recordingClip===audio){stopWarning();setStatus("Audio playback error: "+err.message,true)}});return;
  }
  const v=findCompatibleVoice(result.voice_lang);
  if(!v){stopWarning();updateVoiceAvailability(true);return;}
  const utterance=new SpeechSynthesisUtterance(result.voice_context?.text||result.spoken_warning);
  utterance.lang=result.voice_lang;utterance.voice=v;utterance.rate=0.9;utterance.pitch=1;
  speakingUtterance=utterance;$("listen-warning").textContent="🔊 Speaking…";
  let started=false;
  const useBasicClip=async why=>{
    const basic=await findBasicClip(voiceParams(result),()=>lastResult===result);
    if(lastResult!==result)return;
    stopWarning();
    if(basic){showVoice(basic.specific?"cache":"legacy",basic.path,"Ready · basic offline voice (browser voice failed)",result);speakWarning();}
    else setStatus(why,true);
  };
  utterance.onstart=()=>{started=true};
  utterance.onend=()=>{if(speakingUtterance===utterance)stopWarning()};
  utterance.onerror=event=>{if(speakingUtterance!==utterance)return;if(["canceled","interrupted"].includes(event.error)){stopWarning();return}useBasicClip("Browser speech failed. Use saved or AI audio.")};
  setTimeout(()=>{if(speakingUtterance===utterance&&!started){window.speechSynthesis.cancel();useBasicClip("This browser's voice did not start. Use saved or AI audio.")}},3000);
  try{window.speechSynthesis.speak(utterance)}catch(err){stopWarning();setStatus("Voice playback error: "+err.message,true)}
}
window.addEventListener("DOMContentLoaded",()=>{document.querySelectorAll(".tab").forEach(btn=>btn.addEventListener("click",()=>switchTab(btn.dataset.tab)));document.querySelectorAll("[data-demo]").forEach(btn=>btn.addEventListener("click",()=>{const d=examples[btn.dataset.demo];setText(d.text);$("channel").value=d.channel;readyToAnalyze()}));$("message").addEventListener("input",()=>{inputRevision++;$("char-count").textContent=`${$("message").value.length} / 6000`;readyToAnalyze()});$("analyze-btn").addEventListener("click",requestAnalysis);$("channel").addEventListener("change",readyToAnalyze);$("language").addEventListener("change",readyToAnalyze);$("cloud-consent").addEventListener("change",()=>{cloudPreference=$("cloud-consent").checked;cloudFallback=false;updateCloudChoice();readyToAnalyze()});window.addEventListener("offline",networkChanged);window.addEventListener("online",networkChanged);updateCloudChoice();loadAnalysisAvailability();$("input-language").addEventListener("change",()=>{if(micActive&&recognition){recognition.stop();setStatus("Restart microphone transcription to use the selected input language.");}});$("image-input").addEventListener("change",event=>extractImage(event.target.files?.[0]));$("email-input")?.addEventListener("change",event=>parseEmailUpload(event.target.files?.[0]));$("auto-protect")?.addEventListener("change",()=>{if($("auto-protect").checked)scheduleAutoProtect(true);});$("audio-input").addEventListener("change",event=>selectAudio(event.target.files?.[0]));$("audio-consent").addEventListener("change",()=>{$("transcribe-audio-btn").disabled=!$("audio-consent").checked||!Number.isFinite(audioDurationSeconds)||audioDurationSeconds<=0||audioDurationSeconds>180||!!audioRequest;});$("transcribe-audio-btn").addEventListener("click",transcribeAudio);$("voice-btn").addEventListener("click",startVoice);$("listen-warning").addEventListener("click",speakWarning);$("stop-warning").addEventListener("click",()=>{stopWarning();updateVoiceAvailability()});if(window.speechSynthesis){window.speechSynthesis.addEventListener?.("voiceschanged",()=>{if(!recordingClip&&!speakingUtterance&&$("stop-warning").disabled)updateVoiceAvailability()});window.speechSynthesis.getVoices();}$("copy-report").addEventListener("click",copyReport);$("copy-complaint").addEventListener("click",copyComplaint);$("clear-btn").addEventListener("click",()=>{invalidateAssessment();if(imageRequest){imageRequest.abort();imageRequest=null;}if(audioRequest){audioRequest.abort();audioRequest=null;}if(recognition&&micActive){recognition.abort();recognition=null;micActive=false;$("voice-label").textContent="Start microphone transcription";$("voice-btn").classList.remove("recording");}$("image-input").value="";$("image-file-name").textContent="";setQrPreview([]);if($("email-input"))$("email-input").value="";if($("email-file-name"))$("email-file-name").textContent="";parsedEmailMeta=null;$("audio-input").value="";selectAudio(null);setText("");resetResult();setStatus("Cleared. No scan history is stored.")});});

// Accessible UI enhancements use the original select and analysis handlers.
const rescueGuidance=Object.freeze({
  none:["Protect yourself before acting", "Do not reply, pay or share secret codes.", "Verify through an official contact you find yourself.", "Keep the message as evidence. Avoid interacting with suspicious content."],
  link:["Stop using the suspicious website", "Close the page; do not download files or enter details.", "If you entered credentials, use the shared-details option.", "If anything downloaded, do not open it; seek trusted security help."],
  credentials:["Secure your accounts immediately", "Contact your bank using its official app or independently verified number. Ask about blocking affected access or cards.", "From a trusted device, change compromised passwords or PINs through official services.", "Check transactions. If money was lost, contact your bank and call 1930 immediately."],
  money:["Act now: contact your bank and call 1930", "Tell your bank immediately about the suspicious transaction and ask it to help protect your account.", "Call 1930 promptly and report through cybercrime.gov.in.", "Keep transaction IDs, payment receipts and suspicious messages. Do not pay anyone promising recovery."],
  app:["Isolate the affected device", "Disconnect its mobile data and Wi-Fi. Do not use it to log in or make payments.", "Use another trusted device to contact your bank and secure affected accounts.", "Seek trusted technical help to remove the suspicious app and check the device; preserve evidence if safe to do so.", "If money was lost, contact your bank and call 1930 immediately."]
});
function showRescue(choice){
  if(!Object.hasOwn(rescueGuidance,choice))return;
  const [heading,...steps]=rescueGuidance[choice];
  $("rescue-heading").textContent=heading;
  $("rescue-steps").replaceChildren(...steps.map(step=>make("li",step)));
}
function setupUsability(){
  const drop=$("image-drop");drop.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();$("image-input").click();}});
  for(const type of ["dragenter","dragover"])drop.addEventListener(type,e=>{e.preventDefault();drop.classList.add("drag-active");});
  for(const type of ["dragleave","drop"])drop.addEventListener(type,e=>{e.preventDefault();drop.classList.remove("drag-active");});
  drop.addEventListener("drop",e=>{const file=e.dataTransfer?.files?.[0];if(!file)return;if(!["image/png","image/jpeg","image/webp"].includes(file.type)){setStatus("Choose a PNG, JPG or WebP screenshot.",true);return;}$("image-input").value="";extractImage(file);});
  document.querySelectorAll('input[name="rescue"]').forEach(input=>input.addEventListener("change",()=>showRescue(input.value)));
  showRescue(document.querySelector('input[name="rescue"]:checked').value);
}
window.addEventListener("DOMContentLoaded",setupUsability);
