"""Research only: audit and balance multilingual template groups. No deployment.
Requires train_large_offline.py next to this file; reuses its dataset cache.
"""
import argparse, csv, hashlib, json, sys, random
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter
import train_large_offline as old

SEED=42
LANGS=tuple(old.LANGS.values())
CELLS=[(l,y) for l in LANGS for y in (0,1)]

def group_rows(rows):
    groups=defaultdict(list)
    for row in rows: groups[old.template(row[1])].append(row)
    return groups

def cell(row): return row[0],row[2]

def rep(rows): return sorted(rows)[0]

def split_source(train,test,blocked):
    # Keep the publisher's original test rows as test-only. Reserve a subset
    # of shared template groups, not every shared group. Unreserved test rows
    # are discarded, never used to fit. All conflicting groups excluded.
    tg,vg=group_rows(train),group_rows(test)
    allkeys=set(tg)|set(vg)
    bad={k for k in allkeys if len({r[2] for r in tg.get(k,[])+vg.get(k,[])})!=1}
    allowed=allkeys-bad-set(blocked)
    trainkeys=set(tg)&allowed; testkeys=set(vg)&allowed
    reserved=testkeys-trainkeys
    for c in CELLS:
        shared=sorted(k for k in trainkeys&testkeys if cell(rep(tg[k]))==c)
        random.Random(SEED).shuffle(shared)
        # reserve 20% of shared families, leaving at least one for training
        n=min(len(shared)-1,max(1,round(len(shared)*.2))) if len(shared)>1 else 0
        reserved.update(shared[:n])
    a=[rep(tg[k]) for k in sorted(trainkeys-reserved)]
    b=[rep(vg[k]) for k in sorted(testkeys&reserved)]
    assert not (set(group_rows(a))&set(group_rows(b)))
    assert not (set(group_rows(a))&set(blocked))
    audit=[]
    counts=[Counter(cell(r) for r in rows) for rows in (train,test,[rep(tg[k]) for k in sorted(trainkeys)],[rep(vg[k]) for k in sorted(testkeys)],a,b)]
    for l,y in CELLS:
        audit.append(dict(language=l,label=y,raw_train=counts[0][l,y],raw_test=counts[1][l,y],eligible_train_templates=counts[2][l,y],eligible_test_templates=counts[3][l,y],retained_train=counts[4][l,y],retained_test=counts[5][l,y]))
    return a,b,audit,len(bad)

def weights(base,extra):
    # Fixed source mixture: half total weight to legacy rows, half to external.
    # Each populated external language/label cell gets equal total weight.
    # Small cells are disclosed; no fabricated examples or duplicated rows.
    counts=Counter(cell(r) for r in extra)
    total=len(base)+len(extra)
    if not counts or not base: raise ValueError('Empty source')
    w=[total*.5/len(base)]*len(base)+[total*.5/len(counts)/counts[cell(r)] for r in extra]
    return w

def fit(rows,w=None):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.svm import LinearSVC
    from sklearn.pipeline import make_pipeline
    model=make_pipeline(TfidfVectorizer(analyzer='char',ngram_range=(3,5),min_df=1,max_features=14000,lowercase=True),LinearSVC(max_iter=10000,class_weight='balanced',random_state=42))
    kw={} if w is None else {'linearsvc__sample_weight':w}
    model.fit([r[1] for r in rows],[r[2] for r in rows],**kw)
    return model

def write_csv(path,rows):
    if not rows: return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def cached_rows(repo,split,cache,config=None):
    import pyarrow.parquet as pq
    prefix=repo.replace('/','_')+'_'
    files=sorted(p for p in cache.glob(prefix+'*.parquet') if p.name.split(prefix,1)[1][13:].startswith((config or 'data')+'_'+split+'-'))
    revs={p.name.split(prefix,1)[1][:12] for p in files}
    if not files or len(revs)!=1: raise RuntimeError(f'Expected one cached revision of {repo} {split}; found {len(files)} files, revisions {revs}')
    return [r for p in files for r in pq.read_table(p).to_pylist()],next(iter(revs))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',type=Path,default=Path.cwd());args=parser.parse_args()
    project=args.project.resolve(); root=project.parent/'Semantic_Research'/'large_dataset_experiment'; out=root/'balanced';out.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(project),str(project/'benchmark')]
    from scamshield import engine,training_data
    from offline_engine_comparison import SELECTION,HOLDOUT,cases
    from regional_audit_cases import CASES
    base=[('original',t,1) for t in training_data.SUSPICIOUS]+[('original',t,0) for t in training_data.BENIGN]
    if len(base)!=394: raise RuntimeError(f'Expected 394 baseline rows; got {len(base)}')
    sets={'prior_selection':list(cases(SELECTION)),'prior_holdout':list(cases(HOLDOUT)),'regional_development':list(cases(CASES))}
    known={old.template(t) for rows in sets.values() for _,t,_ in rows}|{old.template(t) for _,t,_ in base}
    raw_train,rev=cached_rows(old.MIT,'train',root/'downloads');raw_test,rev2=cached_rows(old.MIT,'test',root/'downloads')
    if rev!=rev2: raise RuntimeError('Train/test cached revisions differ')
    extra,test,audit,conflicts=split_source(old.prepare(raw_train),old.prepare(raw_test),known)
    if not extra or not test: raise RuntimeError('No usable external rows')
    write_csv(out/'language_balance_audit.csv',audit)
    print('LANGUAGE     RAW TRAIN     UNIQUE TRAIN     RETAINED TRAIN (ham/scam)     RETAINED TEST',flush=True)
    for l in LANGS:
        a,b=[r for r in audit if r['language']==l]
        print(f"{l:10} {a['raw_train']+b['raw_train']:9} {a['eligible_train_templates']+b['eligible_train_templates']:14} {a['retained_train']:12}/{b['retained_train']:<8} {a['retained_test']+b['retained_test']:10}",flush=True)
    print('Conflicting template groups excluded:',conflicts,flush=True)
    candidate=base+extra; w=weights(base,extra)
    print(f'Baseline {len(base)}; new unique templates {len(extra)}; candidate {len(candidate)}; source test {len(test)}',flush=True)
    print('Small or missing training strata (<10 unique examples):',[(r['language'],r['label'],r['retained_train']) for r in audit if r['retained_train']<10],flush=True)
    print('Weighted candidate sample weight range:',round(min(w),3),round(max(w),3),flush=True)
    sets['external_mit_group_filtered']=test
    try:
        raw,brevision=cached_rows(old.BSIS,'test',root/'downloads','classifier')
        independent=old.dedup(old.prepare(raw,True),known|{old.template(t) for _,t,_ in candidate+test})
        if independent: sets['bsis_research_window_test']=independent
    except Exception as exc:
        print('BSIS audit unavailable:',exc,flush=True)
    models={'baseline_394':fit(base),'expanded_unweighted':fit(candidate),'source_language_weighted':fit(candidate,w)}
    results=[]
    for dataset,rows in sets.items():
        for name,model in models.items(): results.extend(old.evaluate(engine,model,rows,dataset,name))
    write_csv(out/'balanced_comparison.csv',results)
    payload={'source':old.MIT,'revision_prefix':rev,'rows':[dict(language=l,text=t,label=y,sample_weight=weight) for (l,t,y),weight in zip(extra,w[len(base):])],'baseline_sample_weight':w[0]}
    data=json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8');(out/'balanced_candidate_training.json').write_bytes(data)
    report={'baseline':len(base),'candidate':len(candidate),'source_test':len(test),'conflicting_groups':conflicts,'source_revision_prefix':rev,'candidate_sha256':hashlib.sha256(data).hexdigest(),'notes':['Research only; all corpora synthetic; no production files changed.','Source test is a new subset of publisher test; previous selection and BSIS results already seen, so these are development comparisons, not fresh final validation.','Exact normalized template separation only; paraphrase and cross-language scenario overlap may remain.','Equal external language/label total sample weights apply before SVM class weighting; this does not guarantee equal performance or equal feature vocabulary.','Low-count cells may be overweighted; inspect counts and per-language results. No synthetic oversampling.']}
    (out/'balanced_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Saved:',out,flush=True);print('Main application unchanged. Do not deploy without separate validation.',flush=True)

if __name__=='__main__': main()
