"""Pure three-valued policy evaluation used by interview, simulator and research."""
import math
import re
from datetime import date
from urllib.parse import urlsplit
from .store import load_file
QUESTIONS=load_file('questions')
def official(url):
    try:
        u=urlsplit(url); host=(u.hostname or '').lower()
        return u.scheme=='https' and not u.username and not u.password and u.port in (443,None) and (host.endswith(('.gov.in','.nic.in')) or host in {'pmuy.gov.in','telanganaepass.cgg.gov.in','pmkisan.gov.in'})
    except ValueError:return False
def validate_answers(raw, extra_states=()):
    if not isinstance(raw,dict): raise ValueError('Answers must be a map.')
    result={}
    for key,v in raw.items():
        if key not in QUESTIONS:raise ValueError('Unknown question: '+key)
        if v in (None,''):continue
        if v=='unknown':result[key]=v;continue
        opts=[x[0] for x in QUESTIONS[key]['options']]
        if key=='state':
            v={'Andhra Pradesh':'AP','Telangana':'TS','Karnataka':'KA'}.get(v,v) if isinstance(v,str) else v
            opts+=list(extra_states)
        if opts:
            if v not in opts: raise ValueError('Choose a listed answer for '+key)
        else:
            try:n=float(v)
            except (ValueError,TypeError):raise ValueError('Enter a number for '+key)
            if isinstance(v,bool) or not math.isfinite(n) or not n.is_integer() or not 0<=n<=(125 if key=='age' else 10**9):raise ValueError('Invalid value for '+key)
            v=int(n)
        result[key]=v
    return result
def leaves(expr):
    if isinstance(expr,list):return [expr]
    return [leaf for child in next(iter(expr.values())) for leaf in leaves(child)]
def test(expr,answers):
    if isinstance(expr,dict):
        mode,parts=next(iter(expr.items()))
        status=[test(p,answers) for p in parts]
        if mode=='all':return False if False in status else (None if None in status else True)
        return True if True in status else (None if None in status else False)
    field,op,target=expr
    value=answers.get(field)
    if value in (None,'unknown'):return None
    if op=='=':return value==target
    if op=='in':return value in target
    if op=='>=':return value>=target
    if op=='<=':return value<=target
    raise ValueError('Unsupported rule operator')
def relevant_missing(expr,a):
    if test(expr,a) is not None:return []
    if isinstance(expr,list):return [expr[0]] if expr[0] not in a else []
    return [k for part in next(iter(expr.values())) for k in relevant_missing(part,a)]
def evaluate(s,a,sources,review_days=365,as_of=None):
    today=as_of or date.today()
    checks=[];pending=[]
    for rule in s['rules']:
        ref=sources.get(rule['source']); valid=bool(ref) and not ref.get('conflict',False) and (today-date.fromisoformat(s['reviewed'])).days<=review_days
        if valid:
            valid=(today-date.fromisoformat(ref['reviewed'])).days<=review_days and (not ref.get('effective') or ref['effective']<=today.isoformat())
        value=test(rule['test'],a) if valid else None
        if value is False and rule.get('review'):value=None
        if value is None and valid:pending.extend(relevant_missing(rule['test'],a))
        checks.append(dict(label=rule['label'],source=rule['source'],test=rule['test'],status='unknown' if value is None else ('pass' if value else 'fail'),inputs={x[0]:a.get(x[0],'unknown') for x in leaves(rule['test'])},source_current=valid))
    status='not eligible' if any(c['status']=='fail' for c in checks) else 'more information needed' if any(c['status']=='unknown' for c in checks) or not checks else 'preliminary eligible'
    return dict(sid=s['id'],version=s['version'],status=status,checks=checks,pending=list(dict.fromkeys(pending)) if status=='more information needed' else [])
def checklist(s,a):
    return [dict(item,conditional=bool(item.get('when'))) for item in s['docs'] if not item.get('when') or a.get(item['when'])!='no']
def valid_expr(expr,depth=0):
    if depth>6:raise ValueError('Rule too deeply nested')
    if isinstance(expr,dict) and len(expr)==1 and set(expr)<= {'any','all'}:
        children=next(iter(expr.values()))
        if not isinstance(children,list) or not 1<=len(children)<=50:raise ValueError('Empty or excessive rule list')
        for part in children:valid_expr(part,depth+1)
    elif isinstance(expr,list) and len(expr)==3 and expr[0] in QUESTIONS:
        field,op,value=expr
        if op in ('>=','<=') and not QUESTIONS[field]['options'] and isinstance(value,(float,int)) and not isinstance(value,bool):return
        if op=='=' and isinstance(value,(str,int)):return
        if op=='in' and isinstance(value,list) and all(isinstance(v,(str,int)) for v in value):return
        raise ValueError('Invalid threshold or comparison')
    else: raise ValueError('Invalid rule expression')
def validate_scheme(s,refs,publish=False):
    if not isinstance(s,dict) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,48}',s.get('id','')):raise ValueError('Use a short stable scheme ID')
    for k in ['name','department','category','level','benefit','description','reviewed','field_mode']:
        if not isinstance(s.get(k),str) or not s[k].strip():raise ValueError('Missing '+k)
    date.fromisoformat(s['reviewed'])
    if s.get('deadline'):date.fromisoformat(s['deadline'])
    for k in ['portal','field_source']:
        if not official(s.get(k,'')):raise ValueError('Provide an official HTTPS URL for '+k)
    for k in ['rules','docs','fields','steps']:
        if not isinstance(s.get(k),list) or not s[k]:raise ValueError('Provide '+k)
    for r in s['rules']:
        if not isinstance(r,dict) or not r.get('label'):raise ValueError('Rule label required')
        valid_expr(r['test'])
    for item in s['docs']:
        if not isinstance(item,dict) or not item.get('label') or item.get('when') and item['when'] not in QUESTIONS:raise ValueError('Invalid checklist entry')
    if not all(isinstance(x,str) and x.strip() for x in s['fields']+s['steps']):raise ValueError('Invalid field or step')
    if publish:
        for item in s['rules']+s['docs']:
            src=refs.get(item.get('source'))
            if not src or src['scheme']!=s['id']:raise ValueError('Publish reviewed evidence for this scheme first: '+str(item.get('source')))
