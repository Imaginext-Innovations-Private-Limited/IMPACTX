"""Research-only BSIS training experiment. No model/data export or deployment.
Requires train_large_offline.py and train_balanced_offline.py in project root.
Uses publisher lineage splits, caps training contributions per language/label,
retains full conversation windows (labels depend on earlier context).
"""
import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
import train_large_offline as old
import train_balanced_offline as bal

LANGS = tuple(l for l in old.LANGS.values() if l != 'hi-Latn')
CAP = 250


def prepare(raw):
    result = []
    for r in raw:
        lang = {'od-IN': 'or'}.get(r['language'], r['language'].split('-')[0])
        if lang not in LANGS:
            continue
        if r['label'] not in (0, 1) or not r.get('lineage_id'):
            raise ValueError('Missing lineage or invalid label')
        text = old.sanitize(r['text'])
        if text and len(text) <= 6000:
            result.append((lang, text, int(r['label']), str(r['lineage_id']), str(r['vector'])))
    return result


def clean(rows, blocked=()):
    groups = defaultdict(list)
    for r in rows:
        groups[old.template(r[1])].append(r)
    blocked = set(blocked)
    return [sorted(v)[0] for k,v in sorted(groups.items())
            if k not in blocked and len({r[2] for r in v}) == 1]


def select(rows, cap=CAP):
    """At most one window per lineage per language/label; cycle playbooks."""
    cells = defaultdict(list)
    for r in rows:
        cells[r[0], r[2]].append(r)
    chosen = []
    for key, items in sorted(cells.items()):
        rng = random.Random(42)
        items = sorted(items); rng.shuffle(items)
        lineage = set(); by_vector = defaultdict(list)
        for r in items:
            if r[3] not in lineage:
                lineage.add(r[3]); by_vector[r[4]].append(r)
        n = 0
        while n < cap and any(by_vector.values()):
            for vector in sorted(by_vector):
                if by_vector[vector] and n < cap:
                    chosen.append(by_vector[vector].pop()); n += 1
    return chosen


def as_rows(items):
    return [r[:3] for r in items]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path, default=Path.cwd())
    args=p.parse_args(); project=args.project.resolve()
    root=project.parent/'Semantic_Research'/'large_dataset_experiment'
    out=root/'diverse_research'; out.mkdir(parents=True,exist_ok=True)
    cache=root/'downloads'; cache.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(project),str(project/'benchmark')]
    from scamshield import engine,training_data
    from offline_engine_comparison import SELECTION,HOLDOUT,cases
    from regional_audit_cases import CASES
    base=[('original',t,1) for t in training_data.SUSPICIOUS]+[('original',t,0) for t in training_data.BENIGN]
    if len(base)!=394: raise RuntimeError(f'Expected 394 baseline rows; got {len(base)}')
    sets={'prior_selection':list(cases(SELECTION)), 'prior_holdout':list(cases(HOLDOUT)), 'regional_development':list(cases(CASES))}
    known={old.template(t) for rows in sets.values() for _,t,_ in rows}|{old.template(t) for _,t,_ in base}
    # Use the same MIT split as the preceding experiment, for an outside-source audit.
    mit_train,mrev=bal.cached_rows(old.MIT,'train',cache)
    mit_test,mrev2=bal.cached_rows(old.MIT,'test',cache)
    if mrev!=mrev2: raise RuntimeError('MIT revisions differ')
    mit_extra,mit_eval,_,_=bal.split_source(old.prepare(mit_train),old.prepare(mit_test),known)
    sets['external_mit_group_filtered']=mit_eval
    allrows={}; revs=set()
    for split in ('train','validation','test'):
        raw, rev=old.get_rows(old.BSIS,split,cache,'classifier')
        revs.add(rev); allrows[split]=prepare(raw)
    if len(revs)!=1: raise RuntimeError('BSIS revisions differ; cannot compare safely')
    lineages={k:{r[3] for r in rows} for k,rows in allrows.items()}
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        if lineages[a]&lineages[b]: raise RuntimeError(f'Lineage overlap: {a}/{b}')
    # Remove any normalized template shared with other splits, legacy or MIT audit.
    blocked=known|{old.template(t) for _,t,_ in mit_eval}
    v=clean(allrows['validation'],blocked)
    t=clean(allrows['test'],blocked|{old.template(r[1]) for r in v})
    train=clean(allrows['train'],blocked|{old.template(r[1]) for r in allrows['validation']+allrows['test']})
    chosen=select(train)
    counts=[Counter((r[0],r[2]) for r in rows) for rows in (allrows['train'],train,chosen,v,t)]
    audit=[]
    print('Language label raw_train unique_eligible selected validation test',flush=True)
    for l in LANGS:
        for y in (0,1):
            ns=[c[l,y] for c in counts]
            print(l,y,*ns,flush=True)
            audit.append(dict(language=l,label=y,raw_train=ns[0],eligible_templates=ns[1],selected=ns[2],validation=ns[3],test=ns[4]))
    bal.write_csv(out/'language_audit.csv',audit)
    if not chosen or not v or not t: raise RuntimeError('Insufficient eligible data')
    extra=as_rows(chosen); candidate=base+extra
    sets['bsis_validation']=as_rows(v); sets['bsis_seen_test']=as_rows(t)
    print(f'Baseline: {len(base)} | selected BSIS: {len(extra)} | candidate: {len(candidate)}',flush=True)
    print('Missing cells:',[(l,y) for l in LANGS for y in (0,1) if not counts[2][l,y]],flush=True)
    models={'baseline_394':bal.fit(base),'mit_weighted_reference':bal.fit(base+mit_extra,bal.weights(base,mit_extra)),
            'bsis_balanced_research':bal.fit(candidate,bal.weights(base,extra))}
    results=[]
    for dataset,rows in sets.items():
        for name,model in models.items(): results.extend(old.evaluate(engine,model,rows,dataset,name))
    bal.write_csv(out/'diverse_comparison.csv',results)
    report={'baseline':len(base),'selected_bsis':len(extra),'candidate':len(candidate),'bsis_revision':next(iter(revs)),
            'mit_revision_prefix':mrev,'cap_per_language_label':CAP,'selected_lineages':len({r[3] for r in chosen}),
            'validation_windows':len(v),'test_windows':len(t),'notes':[
            'BSIS research/educational use only. No trained artifact or raw rows exported. Not for public deployment without permission.',
            'Full conversation windows, not equivalent to standalone SMS. Label 0 includes early scam turns.',
            'One lineage per language/label, playbook round-robin, no row duplication. Equal source/language/label sample weights before SVM class weighting.',
            'Previously examined BSIS test and other development sets are not independent final validation. Filtering changes counts; compare within this run.',
            'Synthetic data only; native review and independent real-world validation required. Main app unchanged.']}
    (out/'research_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Saved:',out,flush=True);print('Research only. No production files or model modified.',flush=True)

if __name__=='__main__': main()
