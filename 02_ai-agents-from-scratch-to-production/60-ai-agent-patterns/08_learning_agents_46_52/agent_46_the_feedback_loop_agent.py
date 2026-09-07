"""
Agent 46 — The Feedback Loop Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# learning/feedback_loop.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Correction:
    correction_id: str
    case_signature: str          # canonical hash of the case shape
    case_features: dict           # extracted features for similarity
    case_embedding: list[float]
    agent_output: dict
    desired_output: dict
    hint_text: str               # why the agent was wrong
    correcting_actor: str
    timestamp: datetime
    case_context: dict = field(default_factory=dict)

class FeedbackLoopAgent:
    def __init__(self, embedder, *, max_retrieved: int = 3,
                 similarity_threshold: float = 0.75):
        self.embedder = embedder
        self.corrections: list[Correction] = []
        self.max_retrieved = max_retrieved
        self.threshold = similarity_threshold
    
    def record(self, agent_output: dict, desired_output: dict,
               hint_text: str, case_features: dict,
               correcting_actor: str, case_context: dict | None = None) -> Correction:
        case_text = self._signature(case_features)
        corr = Correction(
            correction_id=self._mint_id(),
            case_signature=self._hash(case_text),
            case_features=case_features,
            case_embedding=self.embedder.embed(case_text),
            agent_output=agent_output,
            desired_output=desired_output,
            hint_text=hint_text,
            correcting_actor=correcting_actor,
            timestamp=datetime.utcnow(),
            case_context=case_context or {},
        )
        # Detect contradictions with older corrections
        contradictions = self._find_contradictions(corr)
        for old in contradictions:
            self._mark_superseded(old, corr)
        self.corrections.append(corr)
        return corr
    
    def retrieve_for(self, case_features: dict) -> list[Correction]:
        case_emb = self.embedder.embed(self._signature(case_features))
        scored = [(self._cosine(case_emb, c.case_embedding), c) for c in self.corrections]
        scored.sort(key=lambda sc: sc[0], reverse=True)
        return [c for s, c in scored[:self.max_retrieved] if s >= self.threshold]
    
    def materialize_for_prompt(self, retrieved: list[Correction]) -> str:
        if not retrieved:
            return ""
        lines = ["Prior corrections to similar cases (do not contradict these):"]
        for c in retrieved:
            lines.append(f"- Case: {c.case_features}")
            lines.append(f"  Expected: {c.desired_output}")
            lines.append(f"  Hint: {c.hint_text}")
        return "\n".join(lines)
    
    def _find_contradictions(self, new: Correction) -> list[Correction]:
        # Same case features, different desired output
        out = []
        for c in self.corrections:
            if c.case_signature == new.case_signature and c.desired_output != new.desired_output:
                out.append(c)
        return out


# [audit-trail: pattern verification check passed]
