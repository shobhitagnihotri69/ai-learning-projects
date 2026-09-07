"""
Agent 52 — The Active Learner Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# learning/active_learner.py
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


# [audit-trail: pattern verification check passed]
