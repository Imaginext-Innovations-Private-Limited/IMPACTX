'use strict';
let previousPage='',navigation=0;
async function render(){
 const serial=++navigation;openMenu(false);nav();const parts=location.hash.slice(1).split('/'),page=parts[0]||'home',id=decodeURIComponent(parts[1]||'');
 if(page!=='guide'||previousPage!=='guide'||(id&&id!==S.scope))S.interview=false;previousPage=page;
 const pages={home:homePage,explore,detail,guide:guided,check:id=>manual('check',id),simulate:id=>manual('simulate',id),family:()=>S.me.active?family():familyLogin(),records:memberRecords,compare,scan:scanPage,docs:id=>preparation('docs',id),draft:id=>preparation('draft',id),apps,centres,alerts,report:reportPage};
 try{if(S.pid&&['records','report'].includes(page)){await sync();if(serial!==navigation)return}
 if((page==='admin'||adminPages.includes(page))&&!S.me.active)S.me.admin=(await api('/api/me')).admin;
 if(S.me.active&&!S.pid&&['guide','check','simulate','scan','docs','draft','apps','report','records'].includes(page)){
 mount(pageHead(page)+'<section class="panel"><h2>Choose a family member</h2><p>Select the person above or add a member in Family Profiles.</p>'+link('family',label('family'),'action')+'</section>');return}
 if(page==='admin'||adminPages.includes(page))await adminView(page);else if(pages[page])await pages[page](id);else go('home');
 if(serial===navigation){window.scrollTo(0,0);document.title=(names[page]?label(page):'Welfare Navigator')+' · Welfare Navigator'}}
 catch(e){problem(e);if(!main().querySelector('#errors'))mount('<div class="notice error">'+esc(e.message)+'</div>')}
}
async function boot(){if(sessionStorage.getItem("visit"))await sync();else{S.pid="";S.work=null;sessionStorage.removeItem("profile")}if(!S.cat.languages.includes(S.lang))S.lang='en';$('language').innerHTML=S.cat.languages.map(k=>'<option value="'+k+'">'+({en:'English',te:'తెలుగు',hi:'हिन्दी'}[k])+'</option>').join('');$('language').value=S.lang;
 document.documentElement.style.fontSize=localStorage.getItem('fontSize')||'16px';
 const hcOn=localStorage.getItem('highContrast')==='1';document.documentElement.classList.toggle('hc',hcOn);$('contrast').setAttribute('aria-pressed',String(hcOn));
 on('language','change',()=>{S.lang=$('language').value;localStorage.setItem('language',S.lang);render()});on('font','click',()=>{const old=parseInt(document.documentElement.style.fontSize)||16;const size=(old>=20?16:old+2)+'px';document.documentElement.style.fontSize=size;localStorage.setItem('fontSize',size)});on('contrast','click',()=>{const next=document.documentElement.classList.toggle('hc');localStorage.setItem('highContrast',next?'1':'0');$('contrast').setAttribute('aria-pressed',String(next))});on('menu','click',()=>openMenu(true));on('close','click',()=>openMenu(false));on('veil','click',()=>openMenu(false));on('modalclose','click',()=>$('modal').close());document.addEventListener('keydown',e=>{if(e.key==='Escape')openMenu(false);if(e.key==='Tab'&&!$('drawer').hidden){const controls=$('drawer').querySelectorAll('button,a');if(e.shiftKey&&document.activeElement===controls[0]){e.preventDefault();controls[controls.length-1].focus()}else if(!e.shiftKey&&document.activeElement===controls[controls.length-1]){e.preventDefault();controls[0].focus()}}});
 window.addEventListener('hashchange',render);$('sidenav').addEventListener('click',()=>openMenu(false));if(window.speechSynthesis)speechSynthesis.getVoices();await render()}
launchVisit().catch(e=>{main().textContent='Could not load local application: '+e.message})
async function launchVisit(){
 S.cat=await api('/api/catalog');
 await boot();customerBar();
 let timer;function renew(){clearTimeout(timer);if(S.me.active)timer=setTimeout(endVisit,15*60*1000)}renew();for(const event of ['click','keydown'])document.addEventListener(event,renew);
}
function customerBar(){
 const bar=$('customerbar');bar.hidden=!S.me.active;if(bar.hidden){bar.replaceChildren();return}
 bar.innerHTML='<label>Current family member '+select('currentmember',S.me.profiles.map(p=>[p.id,p.name+' · '+p.id.slice(-4)]),S.pid,'Choose a member')+'</label><div class="member-tools"><a class="secondary" href="#family">Manage family</a> <a class="secondary" href="#records">Member records</a> <button class="secondary" id="endvisit">Log out of family</button></div>';
 on('currentmember','change',()=>{sessionStorage.setItem('profile',$('currentmember').value);location.reload()});on('endvisit','click',endVisit);
}
async function endVisit(){
 try{await api('/api/visit/finish',{})}finally{sessionStorage.clear();localStorage.setItem('visit-change',String(Date.now()));location.replace(location.pathname);location.reload()}
}
window.addEventListener('storage',e=>{if(e.key==='visit-change'){sessionStorage.clear();location.reload()}});
window.addEventListener('pageshow',e=>{if(e.persisted)location.reload()});
document.addEventListener('click',async e=>{
 const link=e.target.closest('a[href^="/api/report/"]');if(!link)return;e.preventDefault();
 try{const r=await fetch(link.href,{headers:{'X-Visit':sessionStorage.getItem('visit')||''}});if(!r.ok)throw Error('Reopen the customer visit to download this report.');
 const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download=(profile()?.name||'Member')+'-'+(link.href.includes('sid=')?'draft':'welfare-report')+'.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000)}catch(err){problem(err)}
});
