"""Admin workflows, research runs and content-only backup/restore."""
import base64, hashlib, json, re, threading, time, uuid
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import httpx
from . import ai
from .store import *
from .rules import official,validate_scheme
from .media import extract
JOBS={}; JOB_LOCK=threading.Lock()
def job(label,fn):
    with JOB_LOCK:
        if any(v['status']=='running' for v in JOBS.values()):raise ValueError('Another admin job is running.')
        jid=uuid.uuid4().hex[:10];JOBS[jid]={'id':jid,'label':label,'status':'running','time':now()}
        if len(JOBS)>25:del JOBS[next(iter(JOBS))]
    def run():
        try:result=fn();state='complete'
        except Exception as exc:result={'message':str(exc)[:320]};state='failed'
        with JOB_LOCK:JOBS[jid].update(status=state,result=result)
        with db() as c:audit(c,label,state)
    threading.Thread(target=run,daemon=True).start()
    return {'job':jid}
class PlainHTML(HTMLParser):
    def __init__(self):super().__init__();self.text=[];self.hide=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'):self.hide+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'):self.hide=max(0,self.hide-1)
        if tag in ('p','div','li','h1','h2','h3','tr'):self.text.append('\n')
    def handle_data(self,text):
        if not self.hide:self.text.append(text)
def fetch_official(url):
    if not official(url):raise ValueError('Use an official HTTPS source.')
    with httpx.Client(trust_env=False,timeout=15,follow_redirects=False) as cli:
        with cli.stream('GET',url) as resp:
            resp.raise_for_status();buf=bytearray()
            for part in resp.iter_bytes():
                buf.extend(part)
                if len(buf)>8*1024*1024:raise ValueError('Source too large')
            if buf.startswith(b'%PDF'):return bytes(buf),'policy.pdf'
            if 'html' not in resp.headers.get('content-type',''):raise ValueError('Choose an official HTML page or PDF.')
            p=PlainHTML();p.feed(buf.decode('utf8','replace'));return '\n'.join(t.strip() for t in ''.join(p.text).splitlines() if t.strip()).encode(),'official-page.txt'
def ingest(sid,url,title,section,reviewed,effective,data,name,lang):
    if not official(url):raise ValueError('Official HTTPS source required')
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,48}',sid) or not title.strip():raise ValueError('Enter scheme ID and title')
    day=date.fromisoformat(reviewed)
    if day>date.today():raise ValueError('Review date is in the future.')
    if effective:date.fromisoformat(effective)
    sha=hashlib.sha256(data).hexdigest();pages=extract(data,name,lang);records=[]
    for page,txt,_ in pages:
        txt=re.sub(r'\s+',' ',txt).strip()
        for start in range(0,len(txt),740):
            part=txt[start:start+880].strip()
            if len(part)<12:continue
            key='C'+digest('|'.join((sid,url,sha,str(page),str(start))))[:16]
            records.append(dict(id=key,scheme=sid,title=title[:180],url=url,section=f'{section} · page {page}, offset {start}',text=part,reviewed=reviewed,effective=effective,version=sha[:10],kind='Official source text',file_hash=sha))
    if not records:raise ValueError('No readable text was found.')
    with db() as c:
        c.execute('INSERT IGNORE INTO blobs VALUES(?,?,?)',(sha,Path(name).name,data))
        for s in records:
            if not c.execute('SELECT 1 FROM sources WHERE id=?',(s['id'],)).fetchone():insert_source(c,s,False)
        audit(c,'Evidence imported for review',sid,f'{len(records)} chunks')
    return {'chunks':len(records),'file_hash':sha}
def save_scheme(c,s,action,expected):
    known=c.execute('SELECT MAX(version) FROM schemes WHERE sid=?',(s.get('id',''),)).fetchone()[0] or 0
    if known!=int(expected):raise ValueError('A newer version exists. Reload before editing.')
    refs={e['id']:e for e in evidence(c)}
    validate_scheme(s,refs,action=='publish')
    if action=='publish':
        if (date.today()-date.fromisoformat(s['reviewed'])).days>settings(c)['review_days']:raise ValueError('Review this stale version before publishing')
        for r in s['rules']+s['docs']:
            ref=refs[r['source']]
            if ref.get('conflict') or (date.today()-date.fromisoformat(ref['reviewed'])).days>settings(c)['review_days']:raise ValueError('Source needs review')
    if action in ('publish','archive'):c.execute("UPDATE schemes SET status='superseded' WHERE sid=? AND status='published'",(s['id'],))
    s=dict(s,version=known+1)
    status={'publish':'published','archive':'archived','draft':'draft','review':'review'}[action]
    c.execute('INSERT INTO schemes(sid,version,status,body) VALUES(?,?,?,?)',(s['id'],known+1,status,dump(s)));audit(c,'Scheme '+status,s['id'],str(known+1))
    return s
def research(model,top_k,dataset,prompt_version):
    with db() as c:co=settings(c);published={s['id'] for s in policy(c)}
    if model not in ai.model_health(co)['models']:raise ValueError('Pull the selected chat model and start Ollama before running an experiment.')
    if not isinstance(dataset,list) or not 1<=len(dataset)<=40:raise ValueError('Use 1–40 fictional cases.')
    co.update(chat_model=model,top_k=top_k);outputs=[]
    for case in dataset:
        sid=case['sid'];question=str(case['question'])[:500];gold=case.get('source','')
        if sid not in published or not question:raise ValueError('Invalid benchmark case')
        t=time.monotonic();base_prompt='Answer this general welfare question in simple English. Use no tools.'
        if prompt_version=='v2':base_prompt+=' Use short sentences. Preserve exceptions and explicitly identify missing facts.'
        base=ai.chat(co,base_prompt,question);ms=round((time.monotonic()-t)*1000)
        rag=ai.ask(question,sid,'en',{'chat_model':model,'top_k':top_k,'prompt_version':prompt_version})
        outputs.append({'case':case,'baseline':base,'baseline_ms':ms,'rag':rag['answer'],'rag_mode':rag['mode'],'rag_ms':rag['ms'],'retrieved':[e['id'] for e in rag['sources']],'hit':gold in [e['id'] for e in rag['sources']] if gold else None,'support':None,'citation_correct':None,'unsupported':None})
    result={'model':model,'embed_model':co['embed_model'],'top_k':top_k,'prompt_version':prompt_version,'temperature':0,'dataset_hash':digest(dump(dataset)),'outputs':outputs}
    with db() as c:
        result['corpus_hash']=digest(dump(evidence(c)));rid=c.execute('INSERT INTO experiments(time,body) VALUES(?,?)',(now(),dump(result))).lastrowid
    return {'experiment_id':rid}
def backup(c):
    table_names=['schemes','sources','vectors']
    blob_rows=[dict(hash=r[0],name=r[1],base64=base64.b64encode(r[2]).decode()) for r in c.execute('SELECT hash,name,body FROM blobs')]
    data={t:rows(c,'SELECT * FROM '+t) for t in table_names}
    data.update(blobs=blob_rows,settings=settings(c),format='navigator-content-v1')
    audit(c,'Content backup exported');return data
def restore(c,data):
    if data.get('format')!='navigator-content-v1':raise ValueError('Invalid backup')
    source_ids=set();refs={};policies=[]
    for r in data['sources']:
        s=json.loads(r['body'])
        if not official(s['url']) or r['id']!=s['id'] or r['sid']!=s['scheme'] or s['checksum']!=digest(s['text']):raise ValueError('Invalid source in backup')
        date.fromisoformat(s['reviewed']);source_ids.add(s['id'])
        if r['active']:refs[s['id']]=s
    for r in data['schemes']:
        s=json.loads(r['body']);validate_scheme(s,refs,r['status']=='published')
        if r['sid']!=s['id'] or r['version']!=s['version']:raise ValueError('Inconsistent scheme version')
    if not refs or not data['schemes']:raise ValueError('Empty backup')
    for t in ('schemes','sources','vectors','blobs'):c.execute('DELETE FROM '+t)
    for r in data['sources']:c.execute('INSERT INTO sources VALUES(?,?,?,?)',tuple(r[k] for k in ('id','sid','body','active')))
    for r in data['schemes']:c.execute('INSERT INTO schemes(sid,version,status,body) VALUES(?,?,?,?)',tuple(r[k] for k in ('sid','version','status','body')))
    for r in data['vectors']:
        if r['id'] in source_ids:c.execute('INSERT INTO vectors VALUES(?,?,?,?)',tuple(r[k] for k in ('id','model','checksum','body')))
    for b in data.get('blobs',[]):
        raw=base64.b64decode(b['base64'],validate=True)
        if hashlib.sha256(raw).hexdigest()!=b['hash']:raise ValueError('Corrupt original source')
        c.execute('INSERT INTO blobs VALUES(?,?,?)',(b['hash'],Path(b['name']).name,raw))
    cfg=valid_config(data['settings']);c.execute("REPLACE INTO config VALUES('settings',?)",(dump(cfg),))
    audit(c,'Content backup restored');return {'ok':True}
def valid_config(d):
    cfg={k:d.get(k,v) for k,v in DEFAULT.items()}
    for k,lo,hi in [('top_k',1,10),('retention_days',1,3650),('review_days',1,1825),('ollama_port',1,65535)]:
        cfg[k]=int(cfg[k])
        if not lo<=cfg[k]<=hi:raise ValueError('Invalid '+k)
    for k in ['chat_model','embed_model']:
        if not re.fullmatch(r'[\w./:-]{1,100}',cfg[k]) or 'cloud' in cfg[k].lower():raise ValueError('Use a local model tag')
    if not isinstance(cfg['states'],list) or not all(isinstance(x,str) and 0<len(x)<70 for x in cfg['states']):raise ValueError('Invalid states')
    if not isinstance(cfg['languages'],list) or 'en' not in cfg['languages'] or not set(cfg['languages'])<={'en','te','hi'}:raise ValueError('Choose supported languages including English.')
    return cfg
