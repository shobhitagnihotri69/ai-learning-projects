"""
Agent 14 — The Probabilistic Belief Updater Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# reasoning/belief_updater.py
from dataclasses import dataclass, field
import math

@dataclass
class Hypothesis:
    name: str
    description: str
    prior_probability: float

@dataclass
class Evidence:
    evidence_id: str
    description: str
    likelihoods: dict[str, float]    # P(evidence | hypothesis), per hypothesis
    independence_class: str          # for dependent-evidence handling

@dataclass
class BeliefState:
    hypotheses: list[Hypothesis]
    posteriors: dict[str, float]
    evidence_history: list[str] = field(default_factory=list)
    
    def best_hypothesis(self) -> tuple[Hypothesis, float]:
        h_name = max(self.posteriors, key=self.posteriors.get)
        h = next(h for h in self.hypotheses if h.name == h_name)
        return h, self.posteriors[h_name]
    
    @property
    def entropy(self) -> float:
        return -sum(p * math.log(p) for p in self.posteriors.values() if p > 0)
    
    @property
    def precise(self) -> bool:
        """Are we confident enough to act?"""
        return self.best_hypothesis()[1] > 0.85

class ProbabilisticBeliefUpdaterAgent:
    def __init__(self, hypotheses: list[Hypothesis]):
        priors = {h.name: h.prior_probability for h in hypotheses}
        total = sum(priors.values())
        self.state = BeliefState(
            hypotheses=hypotheses,
            posteriors={k: v/total for k, v in priors.items()},
        )
        self._seen_independence_classes: set[str] = set()
    
    def update(self, evidence: Evidence) -> BeliefState:
        if evidence.independence_class in self._seen_independence_classes:
            # Dependent evidence — discount likelihood weight
            weight = 0.3
        else:
            weight = 1.0
            self._seen_independence_classes.add(evidence.independence_class)
        new_posteriors = {}
        for h_name, prior in self.state.posteriors.items():
            lik = evidence.likelihoods.get(h_name, 0.5) ** weight
            new_posteriors[h_name] = prior * lik
        z = sum(new_posteriors.values())
        new_posteriors = {k: v/z for k, v in new_posteriors.items()}
        self.state.posteriors = new_posteriors
        self.state.evidence_history.append(evidence.evidence_id)
        return self.state
    
    def expected_information_gain(self, candidate_evidence: list[Evidence]) -> list[tuple[Evidence, float]]:
        """For each candidate evidence, compute expected entropy reduction."""
        current_entropy = self.state.entropy
        gains = []
        for ev in candidate_evidence:
            expected_entropy = 0.0
            for h in self.state.hypotheses:
                p_h = self.state.posteriors[h.name]
                p_ev_given_h = ev.likelihoods.get(h.name, 0.5)
                # Simulate the update; compute resulting entropy
                hypothetical = {n: self.state.posteriors[n] * ev.likelihoods.get(n, 0.5)
                                for n in self.state.posteriors}
                z = sum(hypothetical.values())
                hypothetical = {k: v/z for k, v in hypothetical.items()}
                h_entropy = -sum(p * math.log(p) for p in hypothetical.values() if p > 0)
                expected_entropy += p_h * p_ev_given_h * h_entropy
            gains.append((ev, current_entropy - expected_entropy))
        gains.sort(key=lambda eg: eg[1], reverse=True)
        return gains

