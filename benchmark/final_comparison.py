"""Compare uploaded v2.1 (350 examples) and release candidate (394).
Synthetic development/holdout/regression sets; not real-world validation.
Run from project root: python benchmark/final_comparison.py
"""
import csv
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scamshield import engine, training_data, regional_context
from offline_engine_comparison import SELECTION, HOLDOUT, cases
from regional_audit_cases import CASES


def main():
    sets = {'prior_selection': SELECTION, 'prior_holdout': HOLDOUT, 'regional_development': CASES}
    suspicious, benign = training_data.SUSPICIOUS[:], training_data.BENIGN[:]
    norm = lambda t: ' '.join(t.casefold().split())
    assert not ({norm(t) for t in suspicious + benign} & {norm(t) for table in sets.values() for _,t,_ in cases(table)}), 'Exact overlap with training data'
    rows = []
    try:
        for name in ('uploaded_350', 'candidate_394'):
            baseline = name == 'uploaded_350'
            training_data.SUSPICIOUS[:] = suspicious[:175] if baseline else suspicious
            training_data.BENIGN[:] = benign[:175] if baseline else benign
            engine._model.cache_clear()
            rules = (lambda text: []) if baseline else regional_context.regional_context_findings
            with patch.object(regional_context, 'regional_context_findings', rules):
                for dataset, table in sets.items():
                    for lang, text, expected in cases(table):
                        result = engine.analyze(text)
                        rows.append(dict(model=name,dataset=dataset,language=lang,text=text,expected_suspicious=expected,level=result['level'],flagged=int(result['level'] in {'review','caution','high'})))
    finally:
        training_data.SUSPICIOUS[:] = suspicious
        training_data.BENIGN[:] = benign
        engine._model.cache_clear()
    summary = []
    for dataset in sets:
        for model in ('uploaded_350','candidate_394'):
            r = [x for x in rows if x['dataset']==dataset and x['model']==model]
            tp = sum(x['expected_suspicious'] and x['flagged'] for x in r)
            fn = sum(x['expected_suspicious'] and not x['flagged'] for x in r)
            fp = sum(not x['expected_suspicious'] and x['flagged'] for x in r)
            tn = sum(not x['expected_suspicious'] and not x['flagged'] for x in r)
            div = lambda a,b: round(100*a/b,2) if b else 0
            summary.append(dict(dataset=dataset,model=model,scams_flagged=tp,scams_missed=fn,benign_flagged=fp,benign_unflagged=tn,accuracy_pct=div(tp+tn,len(r)),precision_pct=div(tp,tp+fp),recall_pct=div(tp,tp+fn),f1_pct=div(2*tp,2*tp+fp+fn),high_risk_scams=sum(x['expected_suspicious'] and x['level']=='high' for x in r)))
            print(dataset, model, f'flagged={tp}/{tp+fn}, missed={fn}, benign flags={fp}/{fp+tn}')
    for filename,data in [('final_comparison.csv',summary),('final_predictions.csv',rows)]:
        with Path(__file__).with_name(filename).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    print('Saved final_comparison.csv and final_predictions.csv')

if __name__ == '__main__':
    main()
