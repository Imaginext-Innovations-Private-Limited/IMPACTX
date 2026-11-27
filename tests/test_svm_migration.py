"""Migration-specific tests: the SVM is only a weak, non-probabilistic signal."""
import pytest
from sklearn.svm import LinearSVC
from scamshield import engine


def test_production_pipeline_is_linear_svm():
    model = engine._model()
    assert isinstance(model.steps[-1][1], LinearSVC)
    assert model.classes_.tolist() == [0, 1]
    assert model.steps[0][1].ngram_range == (3, 5)


class Margin:
    def __init__(self, value):
        self.value = value
    def decision_function(self, texts):
        return [self.value]


@pytest.mark.parametrize('margin,expected', [(-1, False), (0, False), (.199, False), (.20, True), (1, True)])
def test_signed_margin_gate(margin, expected):
    assert engine._ml_suspicious(Margin(margin), 'test') is expected


def test_model_only_signal_is_capped_at_review(monkeypatch):
    monkeypatch.setattr(engine, '_model', lambda: Margin(999))
    result = engine.analyze('The books on the table are blue today.')
    assert result['level'] == 'review'
    assert result['score'] == 2
    assert result['model_signal'] == 'suspicious_wording'
    assert result['indicators'] == []
    assert result['score_label'] == 'heuristic risk index, NOT probability'


def test_strong_rule_not_downgraded_by_svm(monkeypatch):
    monkeypatch.setattr(engine, '_model', lambda: Margin(-999))
    result = engine.analyze('Share your OTP with our support desk right now to verify your account.')
    assert result['level'] == 'high'


def test_svm_does_not_override_otp_awareness(monkeypatch):
    monkeypatch.setattr(engine, '_model', lambda: Margin(999))
    result = engine.analyze('123456 is your OTP for login. Do not share this OTP with anyone.')
    assert result['otp_notice']
    assert result['level'] == 'no_clear_signal'


def test_missing_model_retains_rules(monkeypatch):
    monkeypatch.setattr(engine, '_model', lambda: None)
    result = engine.analyze('Send OTP WIN MONEY')
    assert result['level'] == 'high'
    assert result['model_signal'] == 'unavailable'


def test_short_text_does_not_invoke_model(monkeypatch):
    class NoCall:
        def decision_function(self, texts):
            raise AssertionError('Short text must not be passed to model')
    monkeypatch.setattr(engine, '_model', lambda: NoCall())
    assert engine.analyze('Send OTP WIN MONEY')['level'] == 'high'
