# Agent 14 — The Probabilistic Belief Updater Agent

### Agent 14 — The Probabilistic Belief Updater Agent

*Maintains and revises posterior beliefs over hypotheses as new evidence arrives.*

#### The Problem

The agent is faced with a question whose answer it can't determine from a single observation, but for which evidence will accumulate over time: for example, which of these three vendors is the actual source of a quality issue, which of these five customer-segment hypotheses best explains a usage spike, or which of seven candidate root causes is responsible for an incident.

Without explicit belief tracking, every new piece of evidence is interpreted in isolation, sometimes flipping the agent's "conclusion" entirely, sometimes ignored when it should have updated the picture.

The general problem is **multi-evidence integration**: combining evidence from multiple sources, accounting for dependencies between them, and surfacing both the current best estimate and the precision of that estimate.

#### Why Naïve Approaches Fail

- 

*"Ask the model to weigh the evidence and produce an answer."* Works once. On the next piece of evidence the model re-weighs everything from scratch, sometimes flipping. The "weighing" has no calibrated meaning.

- 

*"Count the evidence on each side."* Treats all evidence as equally informative. Ignores how much each piece actually changes the picture.

- 

*"Use a simple majority of independent predictions."* Reasonable for ensembling, but insufficient when evidence types and confidences differ.

#### The Mechanism

The belief updater holds an explicit distribution over candidate hypotheses, updates it Bayesian-style as evidence arrives, surfaces the current best estimate and its precision, and computes expected information gain for prospective evidence-gathering actions.

![Pattern 038 — Agent 14 — The Probabilistic Belief Updater Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd3c6a7cb88a5c22323_codex-pattern-038-agent-14-the-probabilistic-belief-updater-agent-the-mechanis.png)

```python
# reasoning/belief_updater.py
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
```

#### Trade-offs and Alternatives

Bayesian belief tracking requires likelihoods, which someone has to estimate or learn. For domains where likelihood estimation is unstable, the pattern can introduce false precision: the posterior looks confident because the math says so, not because the world warrants it.

Mitigate by surfacing the posterior's *width* (entropy, credible interval) alongside the point estimate, and by refusing to act on a hypothesis below a confidence threshold.

For domains where likelihoods are extremely hard to elicit, a coarser alternative is *evidence-counting with weights*. Sum the evidence weights for each hypothesis, and normalize. This is mathematically equivalent to a very strong independence assumption but is more intuitive to operators.

#### Production failure modes

- 

**Likelihood mis-elicitation:** The likelihoods the agent uses are wrong, the posterior is correspondingly wrong. Mitigate by calibrating likelihoods against historical outcomes and reporting calibration metrics in operational dashboards.

- 

**Hidden hypothesis:** The true cause is not in the enumerated hypothesis space. The agent assigns confidently to whichever is least wrong. Mitigate with an explicit "none-of-the-above" hypothesis and a high prior on it when the data is unusual.

- 

**Dependency cascade:** Evidence that looks independent is correlated. Multiple confirming pieces multiply incorrectly. Mitigate by explicitly modeling independence classes (as the code does) and discounting dependent evidence.

#### Case Study

A customer-support diagnosis agent at a consumer-electronics company holds beliefs over likely root causes of incoming hardware tickets across a hypothesis space of approximately forty failure classes per device line. It asks the user the single question most likely to discriminate among current top-ranked hypotheses, drawn from the expected-information-gain ranking.

Average tickets-to-resolution dropped from 3.4 to 1.9 (a 44% reduction) and the proportion of tickets resolved without human escalation rose from 22% to 51% in the year following deployment.

**Pairs with:** Active Learner (Agent 52), Drift Detector (Agent 59), Counterfactual Reasoner (Agent 9).
