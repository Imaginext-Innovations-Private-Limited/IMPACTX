"""Run new synthetic challenge against unchanged production engine."""
import csv, sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'benchmark/research/external')]
from scamshield import engine,training_data
from release_challenge import CHALLENGE
from train_large_offline import template, metrics, FLAGS

def main():
    base={template(x) for x in training_data.SUSPICIOUS+training_data.BENIGN}
    keys=[template(t) for _,t,_ in CHALLENGE]
    assert len(set(keys))==len(keys) and not (base&set(keys))
    assert len(set(l for l,_,_ in CHALLENGE))==11
    assert set(Counter((l,y) for l,_,y in CHALLENGE).values())=={2}
    rows=[]
    for lang,text,y in CHALLENGE:
        result=engine.analyze(text)
        rows.append(dict(language=lang,expected=y,flagged=int(result['level'] in FLAGS),level=result['level'],text=text))
    with (ROOT/'benchmark/release_challenge_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=[]
    for lang in ['ALL']+sorted({r['language'] for r in rows}):
        score=metrics([(r['expected'],r['flagged']) for r in rows if lang=='ALL' or r['language']==lang])
        summary.append(dict(language=lang,**score)); print(lang,score)
    with (ROOT/'benchmark/release_challenge_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
if __name__=='__main__':main()
