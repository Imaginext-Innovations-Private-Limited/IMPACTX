'use strict';
const names={
 home:['Dashboard','డాష్‌బోర్డ్','डैशबोर्ड'],guide:['AI Navigator','ఏఐ మార్గదర్శి','एआई मार्गदर्शक'],check:['Eligibility checker','అర్హత తనిఖీ','पात्रता जाँच'],explore:['Explore schemes','పథకాలు చూడండి','योजनाएँ देखें'],family:['Family profiles','కుటుంబ సభ్యులు','परिवार प्रोफाइल'],compare:['Compare schemes','పథకాల పోలిక','योजनाओं की तुलना'],simulate:['What-if simulator','ఊహాత్మక అర్హత','पात्रता सिम्युलेटर'],docs:['Document checklist','పత్రాల జాబితా','दस्तावेज सूची'],scan:['Document scanner','పత్రాల స్కానర్','दस्तावेज स्कैनर'],draft:['Application assistant','దరఖాస్తు సహాయం','आवेदन सहायक'],apps:['My applications','నా దరఖాస్తులు','मेरे आवेदन'],centres:['Service centres','సేవా కేంద్రాలు','सेवा केंद्र'],alerts:['Reminders','రిమైండర్లు','अनुस्मारक'],report:['My welfare report','నా సంక్షేమ నివేదిక','मेरी रिपोर्ट'],
 manage:['Manage schemes','పథకాల నిర్వహణ','योजना प्रबंधन'],kb:['Knowledge base','ఆధార పత్రాలు','ज्ञान संग्रह'],monitor:['Agent monitor','ఏజెంట్ మానిటర్','एजेंट निगरानी'],experiments:['AI experiments','ఏఐ ప్రయోగాలు','एआई प्रयोग'],analytics:['Research & analytics','పరిశోధన','शोध और विश्लेषण'],logs:['Audit logs','ఆడిట్ లాగ్','ऑडिट लॉग'],privacy:['Privacy & security','గోప్యత','गोपनीयता'],settings:['System settings','సెట్టింగులు','सिस्टम सेटिंग्स']};
const citizenPages=[...Object.keys(names).slice(0,14),'records'],adminPages=Object.keys(names).slice(14);
names.records=['Member records','సభ్యుడి రికార్డులు','सदस्य के रिकॉर्ड'];
const S={lang:localStorage.getItem('language')||'en',cat:null,me:{profiles:[]},pid:sessionStorage.getItem('profile')||'',work:null,sid:'',answers:{},interview:false,manualResult:null,past:[],scope:'',ocr:null,ocrURL:'',term:'',category:'',admin:null};
const $=x=>document.getElementById(x), main=()=>$('main'), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function t(en,te,hi){return (S.lang==='te'?te:S.lang==='hi'?hi:en)||en}
const label=id=>names[id]?t(...names[id]):id;
const categories={'Cooking fuel':['Cooking gas','వంట గ్యాస్','रसोई गैस'],'Agriculture':['Farming','వ్యవసాయం','कृषि'],'Healthcare':['Healthcare','ఆరోగ్యం','स्वास्थ्य'],'Social security':['Pension','పెన్షన్','पेंशन'],'Marriage assistance':['Marriage assistance','వివాహ సహాయం','विवाह सहायता'],'Education':['Education','విద్య','शिक्षा'],'Housing':['Housing','గృహ నిర్మాణం','आवास'],'Business & self-employment':['Self-employment','స్వయం ఉపాధి','स्वरोजगार'],'Women welfare':['Women welfare','మహిళా సంక్షేమం','महिला कल्याण'],'Employment & skills':['Skills & employment','నైపుణ్యాలు','रोज़गार और कौशल']};
function catname(c){return categories[c]?t(...categories[c]):c}
const nm=s=>s?.[S.lang]||s?.name||'';
function msg(x){$('toast').textContent=x;$('toast').hidden=false;clearTimeout(msg.timer);msg.timer=setTimeout(()=>$('toast').hidden=true,4500)}
function show(title,html){$('dialogbody').innerHTML='<h2>'+esc(title)+'</h2>'+html;if(!$('modal').open)$('modal').showModal()}
function problem(e){const m=e.message||String(e);msg(m);let el=$('errors');if(el){el.hidden=false;el.textContent=m}}
async function api(url,body,form=false){const opt=body===undefined?{}:{method:'POST',headers:form?{'X-Navigator':'local'}:{'Content-Type':'application/json','X-Navigator':'local'},body:form?body:JSON.stringify(body)};
 opt.headers={...opt.headers,'X-Visit':sessionStorage.getItem('visit')||''};const r=await fetch(url,opt);if(r.status===401&&sessionStorage.getItem('visit')){sessionStorage.clear();location.replace(location.pathname);throw Error('Family login expired.')}let j;try{j=await r.json()}catch{throw Error('Local server unavailable. Check the launcher window.')}
 if(!r.ok)throw Error(typeof j.detail==='string'?j.detail:'Request could not be validated. Check the fields.');return j}
const post=(action,data={},sid='',profile=S.pid)=>api('/api/citizen',{action,data,sid,profile});
const adminPost=(action,data={},sid='')=>api('/api/admin',{action,data,sid});
async function sync(){S.me=await api('/api/me');if(!S.me.active)sessionStorage.removeItem('visit');if(!S.me.profiles.some(p=>p.id===S.pid))S.pid=S.me.profiles.length===1?S.me.profiles[0].id:'';sessionStorage.setItem('profile',S.pid);S.work=S.pid?await post('workspace'):null}
const profile=()=>S.me.profiles.find(p=>p.id===S.pid);
const sby=id=>S.cat.schemes.find(s=>s.id===id);
const src=id=>S.cat.sources.find(e=>e.id===id);
const urlOk=u=>{try{return new URL(u).protocol==='https:'}catch{return false}};
const external=(u,title)=>urlOk(u)?'<a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+esc(title)+' ↗</a>':esc(title);
const link=(page,title,cls='secondary',sid='')=>'<a class="'+cls+'" href="#'+esc(page)+(sid?'/'+encodeURIComponent(sid):'')+'">'+esc(title)+'</a>';
const btn=(id,title,cls='secondary')=>'<button type="button" id="'+id+'" class="btn '+cls+'">'+esc(title)+'</button>';
const select=(id,list,value='',prefix='')=>'<select class="form-select" id="'+id+'">'+(prefix?'<option value="">'+esc(prefix)+'</option>':'')+list.map(x=>{let [v,l]=Array.isArray(x)?x:[x,x];return '<option value="'+esc(v)+'" '+(v===value?'selected':'')+'>'+esc(l)+'</option>'}).join('')+'</select>';
const schemeSelect=(id,val,prefix='')=>select(id,S.cat.schemes.map(s=>[s.id,nm(s)]),val,prefix);
const statusText=s=>({'preliminary eligible':t('Preliminary match','ప్రాథమికంగా అర్హులు','प्रारंभिक पात्र'),'not eligible':t('Condition not met','అర్హత నిబంధన సరిపోలలేదు','शर्त पूरी नहीं हुई'),'more information needed':t('More information needed','మరింత సమాచారం కావాలి','अधिक जानकारी चाहिए'),'pass':t('Pass','సరిపోతుంది','पूरा'),'fail':t('Fail','సరిపోలలేదు','असफल'),'unknown':t('Unknown','తెలియదు','अज्ञात')})[s]||s;
function on(id,event,fn){const el=$(id);if(el)el.addEventListener(event,async e=>{try{await fn(e)}catch(x){problem(x)}})}
function pageHead(page,description=''){return '<div class="crumb">'+link('home',label('home'),'')+' / '+esc(label(page))+'</div><div class="pagehead"><h1>'+esc(label(page))+'</h1>'+(description?'<p class="muted">'+esc(description)+'</p>':'')+'</div>'}
function mount(html){cancelDictation();main().innerHTML='<div id="errors" role="alert" class="notice error" hidden></div>'+html}
function saveFile(name,data,type='application/json'){const raw=typeof data==='string'?data:JSON.stringify(data,null,2),url=URL.createObjectURL(new Blob([raw],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function fmt(e){return '<details><summary>'+esc(e.id+' · '+e.title)+'</summary><p>'+esc(e[S.lang]||e.text)+'</p>'+(S.lang!=='en'?'<p>'+esc(e.text)+'</p>':'')+(e.original?'<blockquote>'+esc(e.original)+'</blockquote>':'')+'<small>'+esc(e.section+' · '+e.reviewed+' · '+(e.kind||''))+'</small><p>'+external(e.url,t('Official source','అధికారిక ఆధారం','आधिकारिक स्रोत'))+'</p></details>'}
function openMenu(open){$('drawer').hidden=!open;$('veil').hidden=!open;$('menu').setAttribute('aria-expanded',String(open));if(open)$('close').focus()}
function nav(){const page=location.hash.slice(1).split('/')[0]||'home';$('topnav').innerHTML=['home','explore','family'].map(i=>link(i,label(i),page===i?'active':'')).join('');const pages=adminPages.includes(page)||page==='admin'?adminPages:citizenPages;$('sidenav').innerHTML=pages.map(i=>link(i,label(i),page===i?'active':'')).join('')+'<hr>'+link(pages===citizenPages?'admin':'home',pages===citizenPages?t('Admin & research','నిర్వాహక విభాగం','प्रशासन'):label('home'),'');$('navtitle').textContent=t('Navigation','విభాగాలు','नेविगेशन');$('foot').textContent=t('Independent academic project · Official authorities make final decisions.','విద్యా ప్రాజెక్టు · తుది నిర్ణయం అధికారిక శాఖదే.','शैक्षणिक परियोजना · अंतिम निर्णय आधिकारिक विभाग का है।');document.documentElement.lang=S.lang}
function go(page,id=''){const target='#'+page+(id?'/'+encodeURIComponent(id):'');if(location.hash===target)render();else location.hash=target}
function activeScheme(id){return sby(id)||sby(S.sid)||S.cat.schemes[0]}
function needProfile(page){if(S.pid)return false;mount(pageHead(page)+'<div class="panel"><h2>'+esc(t('Save a local profile first','ముందుగా స్థానిక ప్రొఫైల్ సేవ్ చేయండి','पहले स्थानीय प्रोफाइल सहेजें'))+'</h2><p>'+esc(t('Choose a nickname and give consent to save progress on this laptop.','ఈ ల్యాప్‌టాప్‌లో సేవ్ చేయడానికి పేరు, సమ్మతి ఇవ్వండి.','इस लैपटॉप पर प्रगति सहेजने के लिए नाम और सहमति दें।'))+'</p>'+link('family',label('family'),'action')+'</div>');return true}
let playingVoice, voiceRequest=0;
async function listenText(text){
 const lang=S.lang, request=++voiceRequest;
 if(playingVoice)playingVoice.pause();
 const synth=window.speechSynthesis;
 if(synth)synth.cancel();
 async function fallback(){
  try{
   const res=await fetch('/api/read-aloud',{method:'POST',headers:{'Content-Type':'application/json','X-Navigator':'local'},body:JSON.stringify({text,lang})});
   if(!res.ok)throw Error((await res.json()).detail||'Local speech unavailable.');
   if(request!==voiceRequest)return;
   const url=URL.createObjectURL(await res.blob()), audio=new Audio(url);
   playingVoice=audio;
   const release=()=>URL.revokeObjectURL(url);
   audio.onended=release;audio.onpause=release;audio.onerror=release;
   try{await audio.play()}catch(e){release();throw e}
  }catch(e){problem(e)}
 }
 const voice=synth?.getVoices().find(v=>v.localService&&v.lang.toLowerCase().split(/[-_]/)[0]===lang);
 if(!voice)return fallback();
 const u=new SpeechSynthesisUtterance(text);u.lang=voice.lang;u.voice=voice;
 u.onerror=e=>{if(request===voiceRequest&&!['canceled','interrupted'].includes(e.error))fallback()};
 synth.speak(u)
}
