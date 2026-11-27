"""Research-only fusion of already fitted binary SVMs. No production imports.
The engine compares a signed margin with 0.20; these fusion rules combine
threshold votes, not probabilities or calibrated margins. An existing rule
finding or OTP safeguard still takes precedence in the unchanged engine.
"""
import numpy as np

class VoteFusion:
    def __init__(self, models, votes_required, threshold=0.20):
        self.models = tuple(models)
        if not self.models or not 1 <= votes_required <= len(self.models):
            raise ValueError('Invalid fusion vote requirement')
        self.votes_required = votes_required
        self.threshold = float(threshold)

    def decision_function(self, texts):
        texts = list(texts)
        scores = np.asarray([m.decision_function(texts) for m in self.models], dtype=float)
        if scores.shape != (len(self.models), len(texts)) or not np.isfinite(scores).all():
            raise ValueError('Invalid binary classifier margins')
        votes = (scores >= self.threshold).sum(axis=0)
        # A synthetic threshold sentinel, not a confidence score.
        return np.where(votes >= self.votes_required, self.threshold, self.threshold - 1.0)
