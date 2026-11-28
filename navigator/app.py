"""Local-only citizen and authenticated administration API."""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI,Request,HTTPException,UploadFile,File,Form
from fastapi.responses import HTMLResponse,JSONResponse,Response,FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from . import ai,ops,store
from .store import *
from .rules import QUESTIONS,validate_answers,evaluate,checklist,official
from .media import scanned,transcribe,pdf_report,MAX_UPLOAD,read_aloud
def reminders(c):
    schemes=policy(c);refs={e['id']:e for e in evidence(c)};today=date.today()
    review_days=settings(c)['review_days']
    for p in rows(c,'SELECT * FROM profiles'):
        pref=json.loads(p['prefs']);ans=json.loads(p['answers'])
        active=set()
        drafts={r['sid']:r['body'] for r in rows(c,'SELECT sid,body FROM drafts WHERE profile=?',(p['id'],))}
        for s in schemes:
            def add(key,msg):
                signature=s['id']+':'+key;active.add(signature)
                c.execute('INSERT IGNORE INTO reminders(profile,signature,body,wake) VALUES(?,?,?,?)',(p['id'],signature,dump({'sid':s['id'],'message':msg}),now()))
            if pref.get('matches') and evaluate(s,ans,refs,review_days)['status']=='preliminary eligible':add('match-v'+str(s['version']),'Matching scheme: '+s['name'])
            draft=drafts.get(s['id'])
            if not draft:continue
            if pref.get('deadlines') and s.get('deadline') and 0<=(date.fromisoformat(s['deadline'])-today).days<=30:add('date-'+s['deadline'],'Application date: '+s['deadline']+' · '+s['name'])
            if pref.get('documents') and json.loads(draft).get('status')=='Documents pending':add('docs','Documents pending: '+s['name'])
        for item in rows(c,'SELECT id,signature FROM reminders WHERE profile=?',(p['id'],)):
            if item['signature'] not in active:c.execute('DELETE FROM reminders WHERE id=?',(item['id'],))
def housekeep():
    with db() as c:cleanup(c);reminders(c)
@asynccontextmanager
async def lifespan(application):
    init()
    async def loop():
        while True:
            try:await asyncio.to_thread(housekeep)
            except Exception:
                with db() as c:audit(c,'Maintenance needs attention')
            await asyncio.sleep(60)
    task=asyncio.create_task(loop())
    try:yield
    finally:
        task.cancel()
        try:await task
        except asyncio.CancelledError:pass
app=FastAPI(title='Welfare Scheme Navigator',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
@app.middleware('http')
async def local_session(req,call):
    if req.method not in ('GET','HEAD'):
        origin=req.headers.get('origin')
        if (origin and urlsplit(origin).netloc!=req.headers.get('host')) or req.headers.get('x-navigator')!='local':
            return JSONResponse({'detail':'Open the application on this laptop to perform this action.'},403)
        try:
            if int(req.headers.get('content-length','0'))>24*1024*1024:return JSONResponse({'detail':'File too large.'},413)
        except ValueError:return JSONResponse({'detail':'Invalid length'},400)
    raw=req.cookies.get('welfare_session','');fresh=False
    if not req.url.path.startswith('/static'):
        with db() as c:
            owner=digest(raw);row=c.execute('SELECT seen FROM sessions WHERE owner=?',(owner,)).fetchone()
            if not row:
                raw=secrets.token_urlsafe(32);owner=digest(raw);fresh=True
                c.execute('INSERT INTO sessions(owner,seen) VALUES(?,?)',(owner,now()))
            elif row[0][:10]!=now()[:10]:c.execute('UPDATE sessions SET seen=? WHERE owner=?',(now(),owner))
        req.state.owner=owner
    res=await call(req)
    if fresh:res.set_cookie('welfare_session',raw,httponly=True,samesite='strict',max_age=365*86400)
    res.headers['Cache-Control']='no-store'
    res.headers['X-Content-Type-Options']='nosniff';res.headers['Referrer-Policy']='no-referrer'
    res.headers['X-Frame-Options']='DENY'
    res.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; script-src 'self'; media-src 'self' blob:; frame-src blob:; object-src 'none'; form-action 'self'; frame-ancestors 'none'"
    if req.url.path.startswith('/api'):res.headers['Cache-Control']='no-store'
    return res
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','[::1]'])
@app.exception_handler(ValueError)
async def bad(req,exc):return JSONResponse({'detail':str(exc)[:360]},422)
@app.get('/vendor/bootstrap.css')
def bootstrap_css():
    path=ROOT/'static'/'vendor'/'bootstrap.min.css'
    return FileResponse(path,media_type='text/css') if path.is_file() else Response(status_code=204)
@app.get('/',response_class=HTMLResponse)
def home():
    with db() as c:n=len(policy(c))
    return (ROOT/'templates'/'index.html').read_text(encoding='utf8').replace('{{count}}',str(n))
@app.get('/api/catalog')
def catalog():
    with db() as c:
        ss=policy(c);source=[e for e in evidence(c) if e['scheme'] in {s['id'] for s in ss}];cfg=settings(c)
        return dict(schemes=ss,sources=source,questions=QUESTIONS,states=cfg['states'],languages=cfg['languages'],review_days=cfg['review_days'],centres=load_file('centres'),demos=load_file('demo_profiles'),karnataka_directory=rows(c,'SELECT slug,name,kind,department,url,official,sid FROM karnataka_directory ORDER BY name,slug'))
def admin(c,req):
    r=c.execute('SELECT admin_until FROM sessions WHERE owner=?',(req.state.owner,)).fetchone()
    if not r or not r[0] or r[0]<now():raise HTTPException(403,'Sign in to the admin portal.')
def household(c,req):
    ticket=digest(req.headers.get('x-visit',''))
    row=c.execute('SELECT owner FROM visits WHERE ticket=? AND browser=? AND expires>?',(ticket,req.state.owner,now())).fetchone()
    if not row:raise HTTPException(401,'Start or unlock a customer visit.')
    expiry=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat(timespec='seconds')
    c.execute('UPDATE visits SET expires=? WHERE ticket=?',(expiry,ticket))
    return row[0]

@app.post('/api/visit/{mode}')
def visit(mode:str,body:dict,req:Request):
    with db() as c:
        if mode=='finish':
            c.execute('DELETE FROM visits WHERE browser=?',(req.state.owner,))
            c.execute("UPDATE sessions SET admin_until='' WHERE owner=?",(req.state.owner,))
            return {'ok':True}
        if mode not in ('register','new','resume'):raise HTTPException(404)
        code=secrets.token_urlsafe(16) if mode in ('register','new') else str(body.get('code','')).strip()
        owner=digest(code)
        if mode in ('register','new'):c.execute('INSERT INTO households VALUES(?,?)',(owner,now()))
        elif not c.execute('SELECT owner FROM households WHERE owner=?',(owner,)).fetchone():
            raise HTTPException(403,'Family code not recognized.')
        if mode=='register':return {'code':code}
        ticket=secrets.token_urlsafe(24)
        c.execute('DELETE FROM visits WHERE browser=? OR expires<=?',(req.state.owner,now()))
        c.execute('INSERT INTO visits VALUES(?,?,?,?)',(digest(ticket),owner,req.state.owner,(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat(timespec='seconds')))
        return {'ticket':ticket,'code':code if mode=='new' else ''}
def owned(c,req,pid):
    r=c.execute('SELECT * FROM profiles WHERE id=? AND owner=?',(pid,household(c,req))).fetchone()
    if not r:raise HTTPException(404,'Profile not found in this browser.')
    return dict(r)
def relevant_schemes(c,answers):
    schemes=policy(c)
    state=answers.get('state')
    if not state or state=='unknown':return schemes
    region={'AP':'Andhra Pradesh','TS':'Telangana','KA':'Karnataka'}.get(state,state)
    return [scheme for scheme in schemes if scheme['level'] in ('Central',region)]

def get_scheme(c,sid):
    row=c.execute("SELECT body FROM schemes WHERE sid=? AND status='published'",(sid,)).fetchone()
    if not row:raise ValueError('Scheme is unavailable or archived.')
    return json.loads(row[0])
def profiles(c,req):
    pp=rows(c,'SELECT id,name,answers,prefs,updated FROM profiles WHERE owner=? ORDER BY name,id',(household(c,req),))
    for p in pp:
        for k in ('answers','prefs'):p[k]=json.loads(p[k])
    return pp
@app.get('/api/me')
def me(req:Request):
    with db() as c:
        active=False
        arr=[]
        if req.headers.get('x-visit'):
            try:
                arr=profiles(c,req)
                active=True
            except HTTPException as error:
                if error.status_code!=401:raise
        try:admin(c,req);auth=True
        except HTTPException:auth=False
        return dict(profiles=arr,admin=auth,active=active)
class Command(BaseModel):
    action:str=Field(min_length=1,max_length=60)
    profile:str=''
    sid:str=''
    data:dict=Field(default_factory=dict)
def validate_text(value,size=120):
    if not isinstance(value,str) or not 0<len(value.strip())<=size:raise ValueError('Enter a valid text value.')
    if re.search(r'\b(?:\d[ -]?){9,18}\b',value):raise ValueError('Keep private identity and account numbers out of this prototype.')
    return value.strip()
def bundle(c,p):
    pid=p['id']
    return dict(profile=dict(id=pid,name=p['name'],answers=json.loads(p['answers']),prefs=json.loads(p['prefs'])),drafts=[dict(sid=r['sid'],updated=r['updated'],**json.loads(r['body'])) for r in rows(c,'SELECT sid,updated,body FROM drafts WHERE profile=? ORDER BY updated DESC',(pid,))],runs=[json.loads(r['body'])|{'time':r['time']} for r in rows(c,'SELECT body,time FROM decisions WHERE profile=? ORDER BY id DESC LIMIT 100',(pid,))],reminders=[dict(id=r['id'],**json.loads(r['body'])) for r in rows(c,'SELECT id,body FROM reminders WHERE profile=? AND dismissed=0 AND wake<=? ORDER BY id DESC',(pid,now()))])
def record_activity(c,pid,kind,sid,payload):
    c.execute('INSERT INTO member_activity(profile,kind,sid,body,created) VALUES(?,?,?,?,?)',
              (pid,kind,sid,dump(payload),now()))

def activities(c,pid):
    return [dict(kind=r['kind'],sid=r['sid'],created=r['created'],data=json.loads(r['body']))
            for r in rows(c,'SELECT kind,sid,created,body FROM member_activity WHERE profile=? ORDER BY id DESC',(pid,))]

@app.post('/api/citizen')
def citizen(x:Command,req:Request):
    d=x.data;a=x.action
    if a=='ask':
        q=validate_text(d.get('question'),600);lang=d.get('lang','en')
        if lang not in ('te','hi','en'):raise ValueError('Unknown language')
        with db() as c:get_scheme(c,x.sid)
        if x.profile:
            with db() as c:owned(c,req,x.profile)
        response=ai.ask(q,x.sid,lang)
        if x.profile:
            with db() as c:
                owned(c,req,x.profile)
                record_activity(c,x.profile,'Scheme question',x.sid,{'question':q,'answer':response['answer']})
        return response
    if a=='extract profile':
        return ai.extract_profile(validate_text(d.get('text'),600))
    with db() as c:
        cfg=settings(c)
        if a=='profile':
            if d.get('consent') is not True:raise ValueError('Consent is required to save a member profile.')
            name=validate_text(d.get('name'),60)
            ans=validate_answers(d.get('answers',{}),cfg['states'])
            if x.profile:
                owned(c,req,x.profile);pid=x.profile
                c.execute('UPDATE profiles SET name=?,answers=?,updated=? WHERE id=?',(name,dump(ans),now(),pid))
            else:
                pid=uuid.uuid4().hex
                c.execute('INSERT INTO profiles VALUES(?,?,?,?,?,?)',(pid,household(c,req),name,dump(ans),'{}',now()))
            return {'profile':pid}
        if a in ('screen','simulate'):
            answers=validate_answers(d.get('answers',{}),cfg['states'])
            candidates=[get_scheme(c,x.sid)] if x.sid else relevant_schemes(c,answers)
            intent=d.get('intent','')
            if intent and not x.sid:candidates=[s for s in candidates if intent in [s['category'],*s.get('tags',[])]]
            refs={e['id']:e for e in evidence(c)}
            results=[evaluate(s,answers,refs,cfg['review_days']) for s in candidates]
            if x.profile and a=='simulate' and d.get('save'):
                member=owned(c,req,x.profile)
                record_activity(c,x.profile,'What-if simulator',x.sid,{'saved answers':json.loads(member['answers']),'trial answers':answers,'results':{r['sid']:r['status'] for r in results}})
            if x.profile and a=='screen' and d.get('save'):
                owned(c,req,x.profile)
                kind='AI Navigator' if d.get('origin')=='navigator' else 'Eligibility checker'
                record_activity(c,x.profile,kind,x.sid,{'answers':answers,'results':{r['sid']:r['status'] for r in results}})
                for r in results:c.execute('INSERT INTO decisions(profile,sid,body,time) VALUES(?,?,?,?)',(x.profile,r['sid'],dump(r),now()))
                c.execute('UPDATE profiles SET answers=?,updated=? WHERE id=?',(dump(answers),now(),x.profile))
                audit(c,'Eligibility check','rules',','.join(r['sid']+'@'+str(r['version'])+' '+r['status'] for r in results))
            pending=list(dict.fromkeys(k for r in results for k in r['pending'] if x.sid or not k.startswith('ka_review_')))
            trace(c,'Simulator' if a=='simulate' else 'Eligibility',{'discovery':[s['id'] for s in candidates],'rule_results':[r['status'] for r in results],'sources':sorted({q['source'] for r in results for q in r['checks']}),'next':pending[:1]})
            return {'results':results,'next':pending[0] if pending else None,'remaining':len(pending)}
        p=owned(c,req,x.profile)
        if a=='navigator progress':
            answers=validate_answers(d.get('answers',{}),cfg['states'])
            c.execute('UPDATE profiles SET answers=?,updated=? WHERE id=?',(dump(answers),now(),x.profile))
            return {'ok':True}
        if a in ('workspace','export'):
            result=bundle(c,p)
            result['activity']=activities(c,x.profile)
            row=c.execute('SELECT body FROM confirmed_scans WHERE profile=?',(x.profile,)).fetchone()
            result['scan']=json.loads(row[0]) if row else {}
            result['reports']=rows(c,'SELECT id,created FROM reports WHERE profile=? ORDER BY created DESC,id DESC LIMIT 25',(x.profile,))
            return result
        if a=='confirm scan':
            values={k:validate_text(v,100) for k,v in d.items() if k in ('name','locality','school','trade') and v}
            record_activity(c,x.profile,'Document scanner','',dict(document=str(d.get('kind','Document'))[:80],fields=values))
            c.execute('REPLACE INTO confirmed_scans VALUES(?,?)',(x.profile,dump(values)))
            return {'ok':True}
        if a=='delete profile':
            c.execute('DELETE FROM profiles WHERE id=?',(x.profile,));return {'ok':True}
        if a=='save draft':
            s=get_scheme(c,x.sid);fields=d.get('fields',{});ready=d.get('ready',[])
            if not isinstance(fields,dict) or not all(k in s['fields'] for k in fields):raise ValueError('Unknown form field.')
            fields={k:validate_text(v,100) for k,v in fields.items() if v}
            if not isinstance(ready,list):raise ValueError('Invalid checklist')
            ans=json.loads(p['answers']);address=d.get('address',ans.get('address','unknown'))
            if address not in ('yes','no','unknown'):raise ValueError('Invalid address response')
            docs=checklist(s,dict(ans,address=address));ready=[item['label'] for item in docs if item['label'] in ready]
            missing=[i['label'] for i in docs if i['label'] not in ready]
            blanks=[k for k in s['fields'] if not fields.get(k)]
            status='Documents pending' if missing else ('Draft' if blanks else 'Ready to apply')
            if d.get('submitted') is True:status='Citizen marked submitted'
            body=dict(fields=fields,ready=ready,address=address,status=status,missing=missing,blanks=blanks,version=s['version'])
            c.execute('INSERT INTO drafts VALUES(?,?,?,?) ON DUPLICATE KEY UPDATE body=VALUES(body),updated=VALUES(updated)',(x.profile,x.sid,dump(body),now()))
            c.execute('DELETE FROM checklist_items WHERE profile=? AND sid=?',(x.profile,x.sid))
            for i,item in enumerate(docs):
                c.execute('INSERT INTO checklist_items VALUES(?,?,?,?,?)',(x.profile,x.sid,i,item['label'],int(item['label'] in ready)))
            record_activity(c,x.profile,'Document checklist' if d.get('origin')=='docs' else 'Application assistant',x.sid,body)
            trace(c,'Application',{'document_agent':len(docs),'application_agent':status,'scheme':x.sid});return body
        if a=='delete draft':
            c.execute('DELETE FROM drafts WHERE profile=? AND sid=?',(x.profile,x.sid));c.execute("UPDATE reminders SET dismissed=1 WHERE profile=? AND signature LIKE ?",(x.profile,x.sid+':%'));return {'ok':True}
        if a=='preferences':
            prefs={k:d.get(k) is True for k in ('matches','deadlines','documents')};c.execute('UPDATE profiles SET prefs=? WHERE id=?',(dump(prefs),x.profile));reminders(c);return {'ok':True}
        if a=='reminder':
            c.execute('UPDATE reminders SET dismissed=?,wake=? WHERE id=? AND profile=?',(int(not d.get('snooze')),(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),int(d['id']),x.profile));return {'ok':True}
        if a=='feedback':
            rating=int(d['rating'])
            if rating not in range(1,6):raise ValueError('Choose a rating from 1 to 5')
            c.execute('INSERT INTO feedback(profile,rating,time) VALUES(?,?,?)',(x.profile,rating,now()));return {'ok':True}
    raise ValueError('Unknown action')
@app.get('/api/report/{pid}')
def report(pid:str,req:Request,sid:str='',lang:str='en'):
    with db() as c:
        p=owned(c,req,pid);b=bundle(c,p);refs={e['id']:e for e in evidence(c)};ans=json.loads(p['answers'])
        sections=[('Selected profile',[p['name']]+[QUESTIONS[k].get(lang,QUESTIONS[k]['en'])+' '+str(v) for k,v in ans.items() if k in ('state','age','area','grade','trade')])]
        schemes=[get_scheme(c,sid)] if sid else relevant_schemes(c,ans)
        if not sid:
            groups={'preliminary eligible':[], 'more information needed':[], 'not eligible':[]}
            for scheme in schemes:
                result=evaluate(scheme,ans,refs,settings(c)['review_days'])
                groups[result['status']].append(scheme.get(lang) or scheme['name'])
            for key,heading in [('preliminary eligible','Possible matches'),('more information needed','More details or official review needed'),('not eligible','Current answers do not meet the rules')]:
                sections.append((heading+' ('+str(len(groups[key]))+')',groups[key] or ['None']))
        for s in schemes:
            r=evaluate(s,ans,refs,settings(c)['review_days']);draft=next((d for d in b['drafts'] if d['sid']==s['id']),{})
            if not sid and r['status']!='preliminary eligible':continue
            lines=[r['status'],s['benefit']]+[f"{v['status']} · {v['label']} [{v['source']}]" for v in r['checks']]
            if sid:lines+=['Prepared field · '+k+': '+v for k,v in draft.get('fields',{}).items()]
            lines+=['Checklist · '+doc['label']+(' [ready]' if doc['label'] in draft.get('ready',[]) else ' [to prepare]') for doc in checklist(s,dict(ans,address=draft.get('address',ans.get('address','unknown'))))]
            lines+=s['steps']+[s['portal']]+[f"{e['id']} · {e['section']} · {e['url']}" for e in refs.values() if e['scheme']==s['id']]
            sections.append((s.get(lang,s['name']),lines))
        if not sid:
            policy_list=policy(c)
            titles={scheme['id']:scheme['name'] for scheme in policy_list}
            if b['drafts']:
                sections.append(('Applications and document checklists',[titles.get(d['sid'],d['sid'])+' — '+d['status']+' — Ready: '+(', '.join(d.get('ready',[])) or 'None') for d in b['drafts']]))
            scan=c.execute('SELECT body FROM confirmed_scans WHERE profile=?',(pid,)).fetchone()
            if scan:sections.append(('Latest confirmed scan fields',[k+' — '+str(v) for k,v in json.loads(scan[0]).items()]))
            for event in activities(c,pid):
                summary=[event['created']]
                if event['sid']:summary.append(next((s['name'] for s in policy_list if s['id']==event['sid']),event['sid']))
                for key,value in event['data'].items():
                    if isinstance(value,dict):
                        summary.extend(str(k)+' — '+str(v) for k,v in value.items())
                    elif isinstance(value,list):summary.append(key+' — '+', '.join(map(str,value)))
                    else:summary.append(key+' — '+str(value))
                sections.append((event['kind'],summary))
        data=pdf_report('Application preparation draft' if sid else 'Welfare report for '+p['name'],sections,lang)
        if not sid:c.execute('INSERT INTO reports VALUES(?,?,?,?,?)',(uuid.uuid4().hex,pid,'',now(),data))
    return Response(data,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="welfare-'+pid+'.pdf"'})
@app.get('/api/report/{pid}/{report_id}')
def previous_report(pid:str,report_id:str,req:Request):
    with db() as c:
        owned(c,req,pid)
        row=c.execute('SELECT body FROM reports WHERE profile=? AND id=?',(pid,report_id)).fetchone()
        if not row:raise HTTPException(404,'Report not found for this member.')
        return Response(row[0],media_type='application/pdf')
@app.post('/api/scan')
def scan(file:UploadFile=File(...),lang:str=Form('en')):
    if lang not in ('en','hi','te','kn'):raise ValueError('Unknown language')
    try:return scanned(file.file.read(MAX_UPLOAD+1),file.filename or '',lang)
    except (OSError,RuntimeError,__import__('subprocess').TimeoutExpired) as e:raise ValueError('Cannot read this file. Try a clear image or unlocked PDF.') from e
@app.post('/api/voice')
def voice(file:UploadFile=File(...),lang:str=Form('en')):
    if lang not in ('en','hi','te'):raise ValueError('Unknown language')
    if file.content_type!='application/octet-stream' or file.filename!='samples.f32':
        raise ValueError('Refresh the project page with Ctrl+F5 and record again.')
    return {'text':transcribe(file.file.read(MAX_UPLOAD+1),lang)}

@app.post('/api/read-aloud')
def speech_output(body:dict):
    return Response(read_aloud(body.get('text'),body.get('lang')),media_type='audio/wav')
attempts=deque();auth_lock=threading.Lock()
@app.post('/api/admin/login')
def login(req:Request,form:dict):
    with auth_lock:
        while attempts and attempts[0]<time.monotonic()-60:attempts.popleft()
        if len(attempts)>=8:raise HTTPException(429,'Wait one minute before retrying.')
        with db() as c:
            salt,expected=c.execute("SELECT value FROM config WHERE id='password'").fetchone()[0].split(':')
            if not hmac.compare_digest(expected,password_hash(str(form.get('password',''))[:500],salt)):
                attempts.append(time.monotonic());audit(c,'Admin login refused');c.commit();raise HTTPException(403,'Incorrect admin password.')
            expiry=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()
            c.execute('UPDATE sessions SET admin_until=? WHERE owner=?',(expiry,req.state.owner));audit(c,'Admin signed in')
    return {'ok':True}
@app.post('/api/admin')
def operations(x:Command,req:Request):
    d=x.data;act=x.action
    with db() as c:
        admin(c,req)
        if act=='logout':
            c.execute("UPDATE sessions SET admin_until='' WHERE owner=?",(req.state.owner,));return {'ok':True}
        if act=='password':
            set_password(c,validate_text(d.get('password'),160))
            marker=store.DATA/'ADMIN_FIRST_LOGIN.txt'
            if marker.exists():marker.unlink()
            audit(c,'Admin credentials changed');return {'ok':True}
        if act=='overview':
            return {'schemes':[dict(sid=r['sid'],version=r['version'],status=r['status'],scheme=json.loads(r['body'])) for r in rows(c,'SELECT * FROM schemes ORDER BY sid,version DESC')],'sources':[dict(active=r['active'],**json.loads(r['body'])) for r in rows(c,'SELECT * FROM sources ORDER BY sid,id')],'settings':settings(c),'jobs':list(ops.JOBS.values()),'traces':[dict(time=r['time'],route=r['route'],**json.loads(r['body'])) for r in rows(c,'SELECT * FROM traces ORDER BY id DESC LIMIT 150')],'events':rows(c,'SELECT * FROM events ORDER BY id DESC LIMIT 500'),'experiments':[dict(id=r['id'],time=r['time'],**json.loads(r['body'])) for r in rows(c,'SELECT * FROM experiments ORDER BY id DESC LIMIT 50')],'metrics':{'profiles':c.execute('SELECT COUNT(*) FROM profiles').fetchone()[0],'drafts':c.execute('SELECT COUNT(*) FROM drafts').fetchone()[0],'decisions':c.execute('SELECT COUNT(*) FROM decisions').fetchone()[0],'feedback':c.execute('SELECT AVG(rating) FROM feedback').fetchone()[0],'completed':c.execute("SELECT COUNT(*) FROM drafts WHERE JSON_UNQUOTE(json_extract(body,'$.status')) IN ('Ready to apply','Citizen marked submitted')").fetchone()[0],'by_scheme':rows(c,'SELECT sid,COUNT(*) AS count FROM decisions GROUP BY sid'),'by_state':rows(c,"SELECT COALESCE(JSON_UNQUOTE(json_extract(answers,'$.state')),'unknown') AS state,COUNT(*) AS count FROM profiles GROUP BY state")},'health':{'db':'MySQL · local server','index_vectors':c.execute('SELECT COUNT(*) FROM vectors WHERE model=?',(settings(c)['embed_model'],)).fetchone()[0],'disk_free_mb':shutil.disk_usage(store.DATA).free//1048576,'data_folder':str(store.DATA),'ollama':ai.model_health(settings(c))},'dataset':load_file('research')}
        if act=='scheme':
            c.execute("SELECT value FROM config WHERE id='seed' FOR UPDATE")
            return ops.save_scheme(c,d['scheme'],d['stage'],d['expected'])
        if act=='source status':
            group=d.get('ids') or [d.get('id')];active=d.get('active') is True
            if active and not d.get('reviewed'):raise ValueError('Confirm review of the original before activating.')
            for key in group:
                row=c.execute('SELECT body FROM sources WHERE id=?',(key,)).fetchone()
                if not row:raise ValueError('Source not found')
                source=json.loads(row[0])
                if active:source['reviewed']=date.today().isoformat()
                if 'conflict' in d:source['conflict']=bool(d['conflict'])
                c.execute('UPDATE sources SET active=?,body=? WHERE id=?',(int(active),dump(source),key))
            audit(c,'Source activated' if active else 'Source deactivated',str(group[0]),str(len(group)));return {'ok':True}
        if act=='import URL':
            url=d['url'];meta=(d['sid'],url,d['title'],d.get('section','Official page'),d['reviewed'],d.get('effective',''))
            if not official(url):raise ValueError('Use an official HTTPS page')
            def import_page():
                data,name=ops.fetch_official(url);return ops.ingest(*meta,data,name,'en')
            return ops.job('Official page import',import_page)
        if act=='index':return ops.job('Embedding index',ai.build_index)
        if act=='inspect retrieval':
            docs,method=ai.rank(validate_text(d['question'],600),evidence(c,x.sid),settings(c))
            return {'method':method,'sources':docs}
        if act=='experiment':
            if d.get('prompt_version') not in ('v1','v2'):raise ValueError('Unsupported prompt version')
            k=int(d['top_k'])
            if k not in range(1,11):raise ValueError('top-k must be 1–10')
            return ops.job('Research comparison',lambda:ops.research(d['model'],k,d['dataset'],d['prompt_version']))
        if act=='review output':
            row=c.execute('SELECT body FROM experiments WHERE id=?',(int(d['id']),)).fetchone()
            if not row:raise ValueError('Run not found')
            run=json.loads(row[0]);output=run['outputs'][int(d['index'])]
            for k in ('support','citation_correct','unsupported'):output[k]=bool(d[k])
            c.execute('UPDATE experiments SET body=? WHERE id=?',(dump(run),int(d['id'])));return {'ok':True}
        if act=='settings':
            cfg=ops.valid_config(d);c.execute("REPLACE INTO config VALUES('settings',?)",(dump(cfg),));audit(c,'Settings updated');return cfg
        if act=='backup':return ops.backup(c)
        if act=='restore':
            if d.get('confirm')!='RESTORE':raise ValueError('Type RESTORE to confirm.')
            c.execute("SELECT value FROM config WHERE id='seed' FOR UPDATE");return ops.restore(c,d['backup'])
        if act=='benchmark':
            refs={e['id']:e for e in evidence(c)};cases=[]
            dataset=d.get('cases') or load_file('benchmark')
            if not isinstance(dataset,list) or not 1<=len(dataset)<=250:raise ValueError('Use between 1 and 250 labelled fictional cases')
            asof=date.fromisoformat(d.get('as_of','2026-11-24'))
            for case in dataset:
                if not isinstance(case,dict) or case.get('expected') not in ('preliminary eligible','more information needed','not eligible'):raise ValueError('A valid expected status is required for each case')
                a=validate_answers(case.get('answers',{}),settings(c)['states'])
                r=evaluate(get_scheme(c,case['sid']),a,refs,settings(c)['review_days'],asof)
                cases.append({**case,'actual':r['status'],'correct':r['status']==case['expected']})
            return {'cases':cases,'correct':sum(i['correct'] for i in cases),'total':len(cases),'as_of':asof.isoformat(),'dataset_hash':digest(dump(dataset))}
        if act=='cleanup':cleanup(c);audit(c,'Retention applied');return {'ok':True}
    raise ValueError('Unknown admin action')
@app.post('/api/admin/upload')
def upload(req:Request,file:UploadFile=File(...),sid:str=Form(...),url:str=Form(...),title:str=Form(...),section:str=Form('Official document'),reviewed:str=Form(...),effective:str=Form(''),lang:str=Form('en')):
    with db() as c:admin(c,req)
    data=file.file.read(MAX_UPLOAD+1);name=file.filename or 'source.pdf'
    if len(data)>MAX_UPLOAD:raise ValueError('8 MB file limit')
    return ops.job('Source ingestion',lambda:ops.ingest(sid,url,title,section,reviewed,effective,data,name,lang))
@app.get('/api/admin/original/{key}')
def original(key:str,req:Request):
    with db() as c:
        admin(c,req);r=c.execute('SELECT name,body FROM blobs WHERE hash=?',(key,)).fetchone()
        if not r:raise HTTPException(404)
        return Response(r[1],media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="source'+Path(r[0]).suffix+'"'})
