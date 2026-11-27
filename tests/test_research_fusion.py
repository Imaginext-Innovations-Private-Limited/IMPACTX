"""Research tools only. Fixture examples are not external benchmark evidence."""
import csv, sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'benchmark/research/external'),str(ROOT/'benchmark')]
from fusion import VoteFusion
import train_mixed_research as mixed
import train_balanced_offline as bal
from scamshield import engine

class Stub:
    def __init__(self, score):self.score=score
    def decision_function(self, texts):return np.full(len(texts),self.score)

@pytest.mark.parametrize('scores,required,expected', [([.19,.19,.19],1,False),([.2,-2,-2],1,True),([.2,-2,-2],2,False),([.2,.3,-2],2,True),([.2,.2,.2],3,True)])
def test_fixed_votes(scores,required,expected):
    model=VoteFusion([Stub(x) for x in scores],required)
    assert [bool(v>=engine.SVM_REVIEW_MARGIN) for v in model.decision_function(['alpha','beta'])]==[expected,expected]

@pytest.mark.parametrize('models,required', [([],1),([Stub(.5)],0),([Stub(.5)],2)])
def test_bad_vote_requirement(models,required):
    with pytest.raises(ValueError):VoteFusion(models,required)

def test_nonfinite_rejected():
    with pytest.raises(ValueError):VoteFusion([Stub(float('nan'))],1).decision_function(['test'])

def test_fusion_keeps_rules_and_otp_safeguard():
    with patch.object(engine,'_model',return_value=VoteFusion([Stub(.9),Stub(.1)],1)):
        assert engine.analyze('Your OTP is 482193. Do not share it with anyone.')['level']=='no_clear_signal'
    with patch.object(engine,'_model',return_value=VoteFusion([Stub(-.9),Stub(-.1)],1)):
        assert engine.analyze('Send your OTP immediately to claim your lottery prize.')['level']=='high'

def test_research_full_pipeline_fixture(tmp_path,monkeypatch):
    # Use invented miniature rows, not real source data. Exercise fitting,
    # split hygiene, full engine evaluation and CSV output without the network.
    project=tmp_path/'ScamShield_AI';project.mkdir()
    def cached(repo, split, cache, config=None):
        rows=[]
        if repo==mixed.old.MIT:
            for name in ('English','Hindi'):
                for label,kind in [(0,'benign appointment'),(1,'suspicious request')]:
                    rows.append(dict(language=name,text=f'fixture mit {split} {name} {kind} notice',label=label))
        else:
            for lang in ('en','hi','ta'):
                for label,kind in [(0,'benign meeting'),(1,'suspicious deposit')]:
                    rows.append(dict(language=lang,text=f'fixture bsis {split} {lang} {kind} request',label=label,lineage_id=f'{split}-{lang}-{label}',vector=kind))
        return rows,'123456abcdef'
    monkeypatch.setattr(bal,'cached_rows',cached)
    monkeypatch.setattr(sys,'argv',['train_mixed_research.py','--project',str(project),'--ensemble'])
    monkeypatch.setattr(sys,'path',sys.path[:])
    mixed.main()
    out=tmp_path/'Semantic_Research/large_dataset_experiment/ensemble_research'
    with (out/'ensemble_comparison.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    assert {r['model'] for r in rows}=={'baseline_394','mit_weighted_reference','bsis_balanced_research','mixed_source_research','baseline_or_mit_research','all_three_or_research','all_three_majority_research'}
    assert 'new_synthetic_challenge' in {r['dataset'] for r in rows}
    assert not list(out.glob('*.pkl')) and not list(out.glob('*.joblib'))
