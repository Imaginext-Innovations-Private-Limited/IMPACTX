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
let lastResult=null, pendingRequest=null, groqConfigured=null, currentTab="text", recognition=null, micActive=false;
const supportedVoiceLocales={en:"en-IN",hi:"hi-IN",bn:"bn-IN",kn:"kn-IN",te:"te-IN",or:"or-IN",mr:"mr-IN"};
let speakingUtterance=null, recordingClip=null, clipUrl=null, voiceMode=null, voiceCheck=0, playbackAttempt=0, inputRevision=0, imageRequest=null, audioRequest=null, audioDurationSeconds=null, audioSelection=0;
function setStatus(text,error=false){$("status").textContent=text;$("status").classList.toggle("error",error)}
function setText(t){inputRevision++;$("message").value=t.slice(0,6000);$("char-count").textContent=`${$("message").value.length} / 6000`;}
function make(tag, text, className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el}
function switchTab(tab){if(tab!==currentTab){invalidateAssessment();if(imageRequest){imageRequest.abort();imageRequest=null;}if(audioRequest){audioRequest.abort();audioRequest=null;selectAudio($("audio-input").files?.[0]);}}currentTab=tab;document.querySelectorAll(".tab").forEach(el=>{const selected=el.dataset.tab===tab;el.classList.toggle("active",selected);el.setAttribute("aria-selected",String(selected))});$("image-tools").classList.toggle("hidden",tab!=="image");$("voice-tools").classList.toggle("hidden",tab!=="voice");$("input-language-tools").classList.toggle("hidden",tab==="text");if(tab!=="voice"&&micActive){const old=recognition;recognition=null;micActive=false;old?.abort();$("voice-btn").classList.remove("recording");$("voice-label").textContent="Start microphone transcription";}if(tab==="voice")$("channel").value="call";if(tab==="text")setStatus("Paste or edit text, then click Analyze.")}
async function scan(useCloud=false){
  useCloud=useCloud===true;invalidateAssessment();const text=$("message").value.trim();
  if(!text){setStatus("Enter a message or select a demo first.",true);return;}
  const ctrl=new AbortController(), revision=inputRevision;pendingRequest=ctrl;$("analyze-btn").disabled=true;
  setStatus(useCloud?"Analyzing context with AI and local safety checks…":"Analyzing locally…");
  try{
    const response=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text,channel:$("channel").value,language:$("language").value,cloud_consent:useCloud}),signal:ctrl.signal});
    const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"Analysis failed");
    if(pendingRequest!==ctrl||revision!==inputRevision)return;
    lastResult=data;render(data);setStatus("Analysis complete. Indicators are signals, not proof.");
  }catch(error){if(error.name!=="AbortError"&&pendingRequest===ctrl&&revision===inputRevision)setStatus(error.message||"Could not contact the server.",true)}
  finally{if(pendingRequest===ctrl){pendingRequest=null;$("analyze-btn").disabled=false;}}
}
function resetResult(){stopWarning();voiceCheck++;clipUrl=null;voiceMode=null;lastResult=null;$("empty-result").classList.remove("hidden");$("results").classList.add("hidden");$("listen-warning").disabled=true;}
function invalidateAssessment(){inputRevision++;if(pendingRequest){pendingRequest.abort();pendingRequest=null;}$("analyze-btn").disabled=false;resetResult();}
function readyToAnalyze(){invalidateAssessment();setStatus($("message").value.trim()?"Ready. Click Analyze to check this message.":"Enter a message or select a demo first.");}
function requestAnalysis(){
  if(pendingRequest)return;
  if(imageRequest||audioRequest||micActive){setStatus("Finish text extraction or stop transcription before analyzing.",true);return;}
  if(!$("message").value.trim()){setStatus("Enter a message or select a demo first.",true);return;}
  const useCloud=groqConfigured!==false&&window.confirm("Use Groq AI to analyze this message? Text is sent with best-effort redaction; remove private details first. Only share text you have permission to send.\n\nOK = AI + local safety checks. Cancel = local analysis only.");
  return scan(useCloud);
}
async function loadAnalysisAvailability(){try{const r=await fetch("/api/health",{cache:"no-store"});if(r.ok){const d=await r.json();if(typeof d.groq_configured==="boolean")groqConfigured=d.groq_configured;}}catch{ /* Analysis itself handles outages. */ }}
function render(data){$("empty-result").classList.add("hidden");$("results").classList.remove("hidden");$("analysis-mode").textContent=data.analysis_note||"Local analysis — no Groq request made.";const level=data.level;const names={high:"HIGH RISK",caution:"CAUTION",review:"REVIEW",no_clear_signal:"NO CLEAR SIGNAL",unknown:"INSUFFICIENT"};$("risk-title").textContent=data.title;$("risk-level").textContent=names[level]||level;$("risk-level").className=`risk-badge ${level}`;$("risk-summary").textContent=data.summary;$("risk-fill").className=`risk-fill ${level}`;$("risk-fill").style.width=(data.score*10)+"%";$("risk-score").textContent=`Index ${data.score}/10`;$("indicator-count").textContent=String(data.indicators.length);const indicators=$("indicators");indicators.replaceChildren();if(!data.indicators.length)indicators.append(make("p","No explicit warning indicators found. This does not mean the communication is safe.","no-indicators"));data.indicators.forEach(item=>{const holder=make("div",undefined,"indicator");holder.append(make("h5",item.title),make("p",item.explanation),make("span",`Matched: “${item.evidence}”`,"evidence"));indicators.append(holder)});const acts=$("actions");acts.replaceChildren();data.actions.forEach(t=>acts.append(make("li",t)));const cats=$("categories");cats.replaceChildren();data.categories.slice(0,4).forEach(t=>cats.append(make("span",t)));$("spoken-preview").textContent=data.voice_context?.display||data.display_warning||data.spoken_warning||"";$("spoken-preview").lang=data.voice_lang||"en";updateVoiceAvailability();}
async function extractImage(file){if(!file)return;invalidateAssessment();setText("");if(file.size>4*1024*1024){setStatus("Screenshot must be under 4 MB.",true);return}if(imageRequest)imageRequest.abort();const ctrl=new AbortController();imageRequest=ctrl;const revision=inputRevision;const fd=new FormData();fd.append("file",file);setStatus("Extracting text from screenshot…");try{const response=await fetch("/api/ocr?language="+encodeURIComponent($("input-language").value),{method:"POST",body:fd,signal:ctrl.signal});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"OCR failed");if(imageRequest!==ctrl||revision!==inputRevision)return;setText(data.text);$("channel").value="image";setStatus("Screenshot text extracted. Review and correct the text, then click Analyze.")}catch(err){if(err.name!=="AbortError"&&imageRequest===ctrl)setStatus(err.message,true)}finally{if(imageRequest===ctrl)imageRequest=null}}
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
function copyText(text,okMsg){if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(text).then(()=>setStatus(okMsg)).catch(()=>setStatus("Copy failed. Please select and copy manually.",true));else{const temp=document.createElement("textarea");temp.value=text;document.body.append(temp);temp.select();try{document.execCommand("copy");setStatus(okMsg)}catch{setStatus("Copy failed.",true)}temp.remove()}}
function copyReport(){if(!lastResult)return;const d=lastResult;copyText(["SCAMSHIELD AI — SAFETY SCREENING",d.title,d.summary,d.analysis_note||"Local analysis",`Risk index: ${d.score}/10 (heuristic, NOT a probability)`,"Indicators:",...d.indicators.map(i=>`- ${i.title}: ${i.evidence}`),"Recommended actions:",...d.actions.map((a,i)=>`${i+1}. ${a}`),"Reporting: https://cybercrime.gov.in/ · https://sancharsaathi.gov.in/ · 1930",d.disclaimer].join("\n"),"Safety summary copied.")}
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
window.addEventListener("DOMContentLoaded",()=>{document.querySelectorAll(".tab").forEach(btn=>btn.addEventListener("click",()=>switchTab(btn.dataset.tab)));document.querySelectorAll("[data-demo]").forEach(btn=>btn.addEventListener("click",()=>{const d=examples[btn.dataset.demo];setText(d.text);$("channel").value=d.channel;readyToAnalyze()}));$("message").addEventListener("input",()=>{inputRevision++;$("char-count").textContent=`${$("message").value.length} / 6000`;readyToAnalyze()});$("analyze-btn").addEventListener("click",requestAnalysis);$("channel").addEventListener("change",readyToAnalyze);$("language").addEventListener("change",readyToAnalyze);loadAnalysisAvailability();$("input-language").addEventListener("change",()=>{if(micActive&&recognition){recognition.stop();setStatus("Restart microphone transcription to use the selected input language.");}});$("image-input").addEventListener("change",event=>extractImage(event.target.files?.[0]));$("audio-input").addEventListener("change",event=>selectAudio(event.target.files?.[0]));$("audio-consent").addEventListener("change",()=>{$("transcribe-audio-btn").disabled=!$("audio-consent").checked||!Number.isFinite(audioDurationSeconds)||audioDurationSeconds<=0||audioDurationSeconds>180||!!audioRequest;});$("transcribe-audio-btn").addEventListener("click",transcribeAudio);$("voice-btn").addEventListener("click",startVoice);$("listen-warning").addEventListener("click",speakWarning);$("stop-warning").addEventListener("click",()=>{stopWarning();updateVoiceAvailability()});if(window.speechSynthesis){window.speechSynthesis.addEventListener?.("voiceschanged",()=>{if(!recordingClip&&!speakingUtterance&&$("stop-warning").disabled)updateVoiceAvailability()});window.speechSynthesis.getVoices();}$("copy-report").addEventListener("click",copyReport);$("copy-complaint").addEventListener("click",copyComplaint);$("clear-btn").addEventListener("click",()=>{invalidateAssessment();if(imageRequest){imageRequest.abort();imageRequest=null;}if(audioRequest){audioRequest.abort();audioRequest=null;}if(recognition&&micActive){recognition.abort();recognition=null;micActive=false;$("voice-label").textContent="Start microphone transcription";$("voice-btn").classList.remove("recording");}$("image-input").value="";$("audio-input").value="";selectAudio(null);setText("");resetResult();setStatus("Cleared. No scan history is stored.")});});
