"""ScamShield v2.1 research-only dataset expansion. No production files modified.
Run from the main project with a research Python environment (scikit-learn, pyarrow).
Dataset: anmolshrivastav/scam_ham_india_14_languages (MIT, synthetic).
Optional independent-source audit: harshcasper/bsis classifier test (research use only).
No API keys, no model downloads, no automatic deployment.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter
from urllib.request import Request, urlopen
from unittest.mock import patch

LANGS = dict(zip(['English','Hindi','Bengali','Kannada','Telugu','Odia','Marathi','Tamil','Malayalam','Gujarati','Punjabi','Hinglish'],['en','hi','bn','kn','te','or','mr','ta','ml','gu','pa','hi-Latn']))
MIT = 'anmolshrivastav/scam_ham_india_14_languages'
BSIS = 'harshcasper/bsis'
FLAGS = {'review','caution','high'}


def fetch(url):
    with urlopen(Request(url, headers={'User-Agent':'ScamShield-research/1.0'}), timeout=90) as r:
        return r.read()


def get_rows(repo, split, cache, config=None):
    import pyarrow.parquet as pq
    meta = json.loads(fetch('https://huggingface.co/api/datasets/' + repo))
    rev = meta['sha']
    paths = [x['rfilename'] for x in meta['siblings'] if x['rfilename'].endswith('.parquet')
             and re.search(r'(?:^|/)'+split+r'(?:[-./])', x['rfilename'])
             and (config is None or x['rfilename'].startswith(config + '/'))]
    if not paths:
        raise RuntimeError(f'No {split} parquet files found for {repo}; check dataset file listing.')
    rows = []
    for path in sorted(paths):
        name = cache / (repo.replace('/','_')+'_'+rev[:12]+'_'+path.replace('/','_'))
        if not name.exists():
            print('Downloading', repo, path, flush=True)
            data = fetch(f'https://huggingface.co/datasets/{repo}/resolve/{rev}/{path}')
            if not (data.startswith(b'PAR1') and data.endswith(b'PAR1')):
                raise RuntimeError('Invalid parquet response')
            name.write_bytes(data)
        print('Reading', path, flush=True)
        rows.extend(pq.read_table(name).to_pylist())
    return rows, rev


def sanitize(text):
    text = unicodedata.normalize('NFKC', text).strip()
    text = re.sub(r'(?i)\b(?:https?|hxxps?)://[^\s<>]+', 'https://example.invalid', text)
    text = re.sub(r'(?i)\b[\w.+-]+@[\w.-]+\b', 'account@example.invalid', text)
    text = re.sub(r'(?i)\b(?:[a-z0-9-]+\.)+(?:com|in|net|org|site|online|live|xyz|io|co)(?:/[^\s<>]*)?', 'example.invalid', text)
    text = re.sub(r'(?<!\w)(?:\+?91[- ]?)?\d(?:[ -]?\d){9,18}(?!\w)', '0000000000', text)
    return text


def template(text):
    text = sanitize(text).casefold()
    text = re.sub(r'\d+(?:[.,:/-]\d+)*', '0', text)
    return ' '.join(text.split())


def prepare(rows, external=False):
    out=[]
    for row in rows:
        lang = row['language']
        if external:
            lang = {'od-IN':'or'}.get(lang, lang.split('-')[0])
            if lang not in set(LANGS.values()): continue
        else:
            lang = LANGS.get(lang)
            if lang is None: continue
        label = row['label']
        if label not in (0,1): raise ValueError('Unexpected label')
        text = sanitize(row['text'])
        if not text or len(text)>6000: continue
        out.append((lang,text,int(label)))
    return out


def dedup(rows, blocked=()):
    """One example per normalized template; conflicting labels are discarded."""
    groups=defaultdict(list)
    for row in rows:
        groups[template(row[1])].append(row)
    blocked=set(blocked)
    return [items[0] for key,items in sorted(groups.items()) if key not in blocked and len({r[2] for r in items})==1]


def fit(rows):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.svm import LinearSVC
    from sklearn.pipeline import make_pipeline
    model=make_pipeline(TfidfVectorizer(analyzer='char',ngram_range=(3,5),min_df=1,max_features=14000,lowercase=True),LinearSVC(max_iter=10000,class_weight='balanced',random_state=42))
    model.fit([r[1] for r in rows],[r[2] for r in rows])
    return model


def metrics(rows):
    tp=sum(y==1 and flag for y,flag in rows); fn=sum(y==1 and not flag for y,flag in rows)
    fp=sum(y==0 and flag for y,flag in rows); tn=sum(y==0 and not flag for y,flag in rows)
    pct=lambda n,d: round(100*n/d,2) if d else None
    return dict(samples=len(rows),flagged_scams=tp,missed_scams=fn,benign_flags=fp,benign_unflagged=tn,recall_pct=pct(tp,tp+fn),precision_pct=pct(tp,tp+fp),f1_pct=pct(2*tp,2*tp+fn+fp),accuracy_pct=pct(tp+tn,len(rows)))


def evaluate(engine, model, rows, dataset, name):
    grouped=defaultdict(list); start=perf_counter()
    with patch.object(engine,'_model',return_value=model):
        for lang,text,y in rows:
            flag=engine.analyze(text)['level'] in FLAGS
            grouped[lang].append((y,flag)); grouped['ALL'].append((y,flag))
    result=[]
    for lang,items in sorted(grouped.items()):
        result.append(dict(dataset=dataset,model=name,language=lang,**metrics(items)))
    print(dataset,name,metrics(grouped['ALL']),f'| {perf_counter()-start:.2f}s',flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path.cwd())
    parser.add_argument('--out',type=Path,default=None)
    parser.add_argument('--skip-external',action='store_true')
    args=parser.parse_args(); project=args.project.resolve()
    out=(args.out or project.parent/'Semantic_Research'/'large_dataset_experiment').resolve()
    out.mkdir(parents=True,exist_ok=True); cache=out/'downloads'; cache.mkdir(exist_ok=True)
    sys.path[:0]=[str(project),str(project/'benchmark')]
    from scamshield import engine,training_data
    from offline_engine_comparison import SELECTION,HOLDOUT,cases
    from regional_audit_cases import CASES
    import sklearn
    base=[('original',t,1) for t in training_data.SUSPICIOUS]+[('original',t,0) for t in training_data.BENIGN]
    if len(base)!=394: raise RuntimeError(f'Expected v2.1 with 394 rows, got {len(base)}')
    sets={'prior_selection':list(cases(SELECTION)),'prior_holdout':list(cases(HOLDOUT)),'regional_development':list(cases(CASES))}
    known={template(t) for rows in sets.values() for _,t,_ in rows}
    raw_train, rev=get_rows(MIT,'train',cache); raw_test, rev2=get_rows(MIT,'test',cache)
    if rev!=rev2: raise RuntimeError('Dataset changed during download; rerun.')
    test=dedup(prepare(raw_test),known|{template(t) for _,t,_ in base})
    # Test templates are reserved before training; don't fit on evaluation content.
    blocked=known|{template(t) for _,t,_ in test+base}
    extra=dedup(prepare(raw_train),blocked)
    candidate=base+extra
    if not extra or not test: raise RuntimeError('No usable independent rows')
    assert not ({template(t) for _,t,_ in extra}&{template(t) for _,t,_ in test})
    print('Original training:',len(base),'| Added unique templates:',len(extra),'| Candidate:',len(candidate),'| Source test:',len(test),flush=True)
    print('Added by language and label:',dict(Counter((l,y) for l,_,y in extra)),flush=True)
    sets['external_mit_template_filtered']=test
    external_status='skipped'; external_rev=None
    if not args.skip_external:
        try:
            raw,external_rev=get_rows(BSIS,'test',cache,'classifier')
            # Research-only, no raw rows exported. This is a different source and message-window task.
            external=dedup(prepare(raw,True),{template(t) for _,t,_ in candidate+test}|known)
            if external: sets['bsis_research_window_test']=external; external_status='available'
            else: external_status='no eligible rows'
        except Exception as e:
            external_status=f'unavailable: {type(e).__name__}: {e}'
            print('External research audit unavailable:',external_status,flush=True)
    print('Fitting both unchanged SVM architectures...',flush=True)
    models={'baseline_394':fit(base),'expanded_candidate':fit(candidate)}
    results=[]
    for dataset,rows in sets.items():
        for name,model in models.items(): results.extend(evaluate(engine,model,rows,dataset,name))
    with (out/'large_dataset_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    # Only sanitized MIT training rows; BSIS is evaluation-only, not distributed.
    payload={'source':MIT,'revision':rev,'license_declared':'MIT','rows':[dict(language=l,text=t,label=y) for l,t,y in extra]}
    raw=json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')
    (out/'candidate_training.json').write_bytes(raw)
    report=dict(baseline=len(base),raw_source_train=len(raw_train),raw_source_test=len(raw_test),added=len(extra),candidate=len(candidate),source_revision=rev,source_test=len(test),external_status=external_status,external_revision=external_rev,sklearn=sklearn.__version__,candidate_data_sha256=hashlib.sha256(raw).hexdigest(),notes=['All source examples synthetic; source labels not independently verified.','Template filtering is approximate; paraphrased or translated families may still overlap.','BSIS uses conversation windows, not directly equivalent to SMS; research only.','No deployment performed. Review per-language metrics, regressions, license and native speaker labels before integration.'])
    (out/'large_dataset_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Saved results to',out,flush=True)
    print('Main application unchanged. Candidate requires review before deployment.',flush=True)

if __name__=='__main__': main()
