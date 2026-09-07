# Agent 52 — The Active Learner Agent

### Agent 52 — The Active Learner Agent

*Chooses which uncertain examples to ask a human about to maximize the value of labeling.*

#### The Problem

The agent is uncertain on many cases. Asking a human about all of them is unaffordable, while asking about none leaves capacity unused.

The active learner selects the cases on which a human label would produce the largest improvement — not always the most uncertain ones, but the ones where labeling would maximally reduce residual error.

The general problem is **labeling-budget allocation**: deciding which examples are worth a human's time, given a finite labeling budget, to maximize downstream agent improvement.

#### Why Naïve Approaches Fail

- 

*"Label everything."* Affordable for none.

- 

*"Label the most uncertain cases."* Often correct, but misses cases where the uncertainty is structural (the agent will always be uncertain on this kind of input).

- 

*"Label randomly."* Wastes budget on easy cases.

#### The Mechanism

An uncertainty estimate per case that goes beyond model logits (combines self-consistency disagreement, retrieval confidence, historical accuracy on similar cases). A selection policy that targets cases at the boundary between mastered and unmastered. A budgeted-queue discipline that respects the human labeler's capacity. An integration path that flows labeled cases back into the feedback-loop store.

![Pattern 076 — Agent 52 — The Active Learner Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df6a412be96d299ae47_codex-pattern-076-agent-52-the-active-learner-agent-the-mechanism.png)

```python
# learning/active_learner.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class UncertaintyCase:
    case_id: str
    input: dict
    agent_output: dict
    self_consistency_disagreement: float
    retrieval_confidence: float
    similarity_to_historical_failures: float
    similarity_to_historical_successes: float
    proxy_difficulty: float
    captured_at: datetime

@dataclass
class LabelingPriority:
    case_id: str
    score: float
    rationale: str

class ActiveLearnerAgent:
    def __init__(self, similar_case_index, daily_label_budget: int = 50):
        self.index = similar_case_index
        self.daily_budget = daily_label_budget
        self.queue: list[UncertaintyCase] = []
        self.labeled: dict[str, dict] = {}
    
    def consider(self, case: UncertaintyCase) -> None:
        """Decide whether to add the case to the labeling queue."""
        score = self._priority_score(case)
        if score > 0.5:
            self.queue.append(case)
    
    def select_for_labeling(self) -> list[LabelingPriority]:
        """Pick the top-N cases for today's labeling budget."""
        scored = [(self._priority_score(c), c) for c in self.queue]
        scored.sort(key=lambda sc: sc[0], reverse=True)
        return [
            LabelingPriority(
                case_id=c.case_id, score=s,
                rationale=self._explain(c),
            )
            for s, c in scored[:self.daily_budget]
        ]
    
    def _priority_score(self, c: UncertaintyCase) -> float:
        # Cases that are uncertain AND close to historical successes have high learning value
        # Cases close only to historical failures may be structurally unsolvable
        uncertainty = (
            0.4 * c.self_consistency_disagreement
            + 0.3 * (1 - c.retrieval_confidence)
            + 0.3 * c.proxy_difficulty
        )
        boundary_factor = max(
            c.similarity_to_historical_successes - c.similarity_to_historical_failures,
            0,
        )
        return uncertainty * boundary_factor
    
    def record_label(self, case: UncertaintyCase, label: dict) -> None:
        self.labeled[case.case_id] = label
        # Remove from queue
        self.queue = [c for c in self.queue if c.case_id != case.case_id]
    
    def _explain(self, c: UncertaintyCase) -> str:
        return (
            f"disagreement {c.self_consistency_disagreement:.2f}, "
            f"retrieval_conf {c.retrieval_confidence:.2f}, "
            f"boundary {(c.similarity_to_historical_successes - c.similarity_to_historical_failures):.2f}"
        )
```

#### Trade-offs and Alternatives

The active learner is a meta-pattern: it does not produce outputs itself. It needs a label-providing process (humans, in most cases) and a downstream consumer (the Feedback Loop, Agent 46, typically). For agents without either, the pattern has nowhere to live.

For cold-start situations (no historical successes or failures to compare against), active learning degenerates to random sampling. Bootstrap with random labeling first, then switch to active selection.

#### Production Failure Modes

- 

**Selection bias loop.** The active learner samples cases similar to historical labels, the labeled set narrows to a sub-distribution, and the agent gets worse on the un-sampled distribution. Mitigate by reserving a fraction of the budget for random sampling.

- 

**Labeler bias:** The labeler systematically labels in one direction, and the agent learns the labeler's bias. Mitigate by sampling labels for review by a different labeler.

- 

**Queue backlog:** Cases are added faster than labelers can clear them. Mitigate by dropping old un-labeled cases (the Forgetting-Policy applies here) or raising the priority threshold.

#### Case Study

A document-classification agent at a regulatory-compliance vendor reduced its human-labeling budget by 60% while maintaining accuracy, by routing only active-learner-selected cases to the labelers. The selected cases (top 50 per day from a pool of roughly 1,200 daily uncertain cases) covered the agent's actual learning boundary. The labeling team's reported "interesting case rate" rose from 18% to 71%, and the resulting agent improvements were measured against the older random-sampling baseline as roughly 3× faster convergence per labeled case.

**Pairs with:** Feedback Loop (Agent 46), Probabilistic Belief Updater (Agent 14), Curriculum Designer (Agent 49).
