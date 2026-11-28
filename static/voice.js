'use strict';
let currentDictation=null;
function cancelDictation(){
 if(currentDictation)currentDictation.cancel();
}
window.addEventListener('pagehide',cancelDictation);

async function pcmBlob(chunks,rate){
 const count=chunks.reduce((sum,chunk)=>sum+chunk.length,0);
 if(count<rate*.18)throw Error('No microphone audio captured. Speak a short answer, then press Stop.');
 const offline=new OfflineAudioContext(1,Math.min(45*16000,Math.ceil(count*16000/rate)),16000);
 const source=offline.createBufferSource(),buffer=offline.createBuffer(1,count,rate);
 let offset=0;
 for(const chunk of chunks){buffer.copyToChannel(chunk,0,offset);offset+=chunk.length}
 source.buffer=buffer;source.connect(offline.destination);source.start();
 const samples=(await offline.startRendering()).getChannelData(0);
 for(let i=0;i<samples.length;i++)samples[i]=Math.max(-1,Math.min(1,samples[i]));
 return new Blob([samples],{type:'application/octet-stream'});
}
async function record(button,target,transform=value=>value){
 if(currentDictation?.button===button){currentDictation.stop?.();return}
 if(currentDictation)throw Error('Finish the current recording first.');
 if(!navigator.mediaDevices?.getUserMedia || !window.AudioContext)
  throw Error('Open the local project address in Chrome or Edge to enable the microphone.');
 const initial=button.textContent,lang=S.lang,member=S.pid,chunks=[];
 let stream,context,node,timer,cancelled=false,finishAudio;
 const session={button,cancel};
 currentDictation=session;
 function release(){
  clearTimeout(timer);
  if(node){node.port.onmessage=null;node.disconnect()}
  stream?.getTracks().forEach(track=>track.stop());
  if(context && context.state!=='closed')context.close().catch(()=>{});
 }
 function restore(){
  if(currentDictation===session)currentDictation=null;
  button.disabled=false;button.textContent=initial;button.removeAttribute('aria-pressed');
 }
 function cancel(){cancelled=true;finishAudio?.();release();restore()}
 const valid=()=>!cancelled && target.isConnected && member===S.pid;
 button.disabled=true;button.textContent='Starting mic…';
 try{
  context=new AudioContext();
  const resume=context.resume();
  resume.catch(()=>{});
  stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1}});
  if(!valid())return;
  await resume;
  if(!context.audioWorklet)throw Error('Open the local address in an up-to-date Chrome or Edge browser.');
  await context.audioWorklet.addModule('/static/mic-worklet.js?v=voice3');
  if(!valid())return;
  const rate=context.sampleRate,source=context.createMediaStreamSource(stream);
  node=new AudioWorkletNode(context,'welfare-microphone',{channelCount:1,channelCountMode:'explicit'});
  const silent=context.createGain();silent.gain.value=0;
  source.connect(node);node.connect(silent);silent.connect(context.destination);
  const stopped=new Promise(resolve=>{finishAudio=resolve});
  node.port.onmessage=e=>{if(e.data==='done')finishAudio();else chunks.push(e.data)};
  session.stop=()=>{
   if(button.disabled)return;
   button.disabled=true;
   node.port.postMessage('stop');
   clearTimeout(timer);timer=setTimeout(finishAudio,500);
  };
  stream.getAudioTracks()[0].onended=session.stop;
  button.disabled=false;button.setAttribute('aria-pressed','true');
  button.textContent=t('Stop recording','రికార్డింగ్ ఆపు','रिकॉर्डिंग रोकें');
  timer=setTimeout(session.stop,40000);
  await stopped;
  if(!valid())return;
  release();button.textContent=t('Transcribing…','వచనంగా మారుస్తోంది…','लिख रहे हैं…');
  const form=new FormData();form.append('file',await pcmBlob(chunks,rate),'samples.f32');form.append('lang',lang);
  if(!valid())return;
  const response=await api('/api/voice',form,true);
  if(!valid())return;
  target.value=transform(response.text);
  target.dispatchEvent(new Event('input',{bubbles:true}));
  target.dispatchEvent(new Event('change',{bubbles:true}));
  target.focus();msg('Review the value, then use the save or continue button.');
 }catch(error){
  if(!cancelled){
   const help={NotAllowedError:'Allow microphone access in the browser and Windows microphone privacy settings.',
    NotFoundError:'Connect a microphone and select it in your browser settings.',
    NotReadableError:'Windows could not open the microphone. Check the selected input device.'};
   throw Error(help[error.name]||error.message);
  }
 }finally{release();restore()}
}

function normalizeSpeech(value){
 return String(value).normalize('NFKC').toLowerCase()
  .replace(/[०-९౦-౯]/gu,c=>String(c.codePointAt(0)-(c>='౦'?0x0c66:0x0966)))
  .replace(/[.,!?।॥]+$/gu,'').trim().replace(/\s+/gu,' ');
}
const smallNumbers='zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(' ');
const tens='twenty thirty forty fifty sixty seventy eighty ninety'.split(' ');
function ageWords(n){
 if(n<20)return smallNumbers[n];
 if(n<100)return tens[Math.floor(n/10)-2]+(n%10?' '+smallNumbers[n%10]:'');
 return 'one hundred'+(n%100?' '+ageWords(n%100):'');
}
function spokenAnswer(text,key){
 const q=S.cat.questions[key],raw=normalizeSpeech(text.trim());
 if(q.options.length){
  const entries=new Map(opts(q).map(([v,label])=>[v,[v,label]]));
  for(const [code,...labels] of q.options)entries.get(code)?.push(...labels,hiOpt[code]||'');
  const phrase=raw.replace(/^(?:i live in|i am from|my state is|my answer is)\s+/u,'');
  for(const [code,labels] of entries)if(labels.some(label=>label && normalizeSpeech(label)===phrase))return code;
  throw Error('Could not match “'+text+'”. Choose a listed answer or repeat the option.');
 }
 let value=raw.replace(/^i(?: am|'m) |^my age is /u,'').replace(/\s*(?:years? old|years?|సంవత్సరాలు|साल)$/u,'').trim();
 if(/^\d{1,3}(?:,\d{2,3})+$/u.test(value))value=value.replace(/,/g,'');
 if(key==='age' && !/^\d+$/u.test(value)){
  value=value.replace(/-/g,' ').replace(/ hundred and /,' hundred ');
  for(let n=0;n<=125;n++)if(ageWords(n)===value)return String(n);
 }
 if(/^\d+$/u.test(value) && Number(value)<=(key==='age'?125:1e9))return String(Number(value));
 throw Error('Could not match “'+text+'”. Enter the number in digits and save.');
}
function addDictation(field,key=''){
 if(!field)return;
 const label=field.closest('label'),wrapper=document.createElement('div'),button=document.createElement('button');
 wrapper.className='dictation-field';label.before(wrapper);wrapper.append(label,button);
 button.className='secondary';button.type='button';button.textContent=t('Dictate','మాట్లాడండి','बोलें');
 button.setAttribute('aria-label',button.textContent+' · '+label.childNodes[0].textContent.trim());
 button.addEventListener('click',()=>record(button,field,text=>key?spokenAnswer(text,key):text.trim()).catch(problem));
}
