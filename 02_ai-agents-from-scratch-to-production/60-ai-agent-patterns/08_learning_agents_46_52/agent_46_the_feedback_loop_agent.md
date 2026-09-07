# Agent 46 — The Feedback Loop Agent

### Agent 46 — The Feedback Loop Agent

*Accumulates user corrections into a structured signal that future runs are conditioned on.*

#### The Problem

The user corrects the agent. The default behavior (discarding the correction at session end) is the worst possible outcome. The same mistake gets made next session, and the next, eroding user trust at every iteration.

With a feedback loop, every correction becomes a permanent improvement vector for future cases on similar inputs.

The general problem is **production-time learning from corrections**: turning user-supplied counter-evidence into structured data that conditions future runs, without requiring model retraining.

#### Why Naïve Approaches Fail

- 

*"Hope the model learns from context."* It doesn't, across sessions. Context resets.

- 

*"Add corrections to the system prompt."* Bloats the prompt, and corrections become indistinguishable from invariant rules. Also doesn't scale.

- 

*"Retrain the model on corrections."* Slow, expensive, and conflates updates to deployed behavior with updates to training. Most teams can't retrain frequently enough for this to be useful.

#### The Mechanism

A correction-capture step that records what the agent produced, what the user wanted, and the user's hint at why. A case-similarity index that retrieves the most relevant prior corrections when a new case arrives. An in-context injection that surfaces the retrieved corrections to the policy as guidance. A contradiction-detection step when newly-arrived corrections disagree with older ones.

![Pattern 070 — Agent 46 — The Feedback Loop Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df006b2c784575c33f3_codex-pattern-070-agent-46-the-feedback-loop-agent-the-mechanism.png)

```python
# learning/feedback_loop.py
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
```

#### Trade-offs and Alternatives

The pattern is cheap and effective from day one. The trade is operational: someone has to capture corrections — either the user, a reviewer, or an evaluator agent — and the captured signal has to be usefully structured.

For environments where users won't provide corrections in a structured way, infer corrections from behavior signals (user re-asks the same question, user manually edits the output, user dismisses the response). These weaker signals are noisier but better than nothing.

#### Production Failure Modes

- 

**Hint-text noise:** Users write hints that are sarcastic, vague, or contradictory. Mitigate by structuring the correction capture (multiple choice for common error types) rather than open text.

- 

**Contradiction accumulation:** Corrections disagree with each other across users, and the agent oscillates between contradictory hints. Mitigate by partitioning corrections by user or by tenant where appropriate, and by surfacing contradictions explicitly rather than averaging.

- 

**Drift erosion:** As the deployment distribution shifts, old corrections become irrelevant or wrong. Mitigate with the Forgetting-Policy (Agent 26) applied to the correction store.

#### Case Study

A sales-email-drafting agent at an outbound-sales platform sees its hit rate on accepted drafts climb from 60% to 85% over its first month entirely through feedback-loop conditioning, with no underlying model changes. Each rejected draft is captured with a structured "what I'd change" form filled in by the rep. The resulting corrections are retrieved and surfaced on similar future drafts. The product team explicitly doesn't retrain the model. The entire improvement is via context.

**Pairs with:** Skill-Library Builder (Agent 48), Active Learner (Agent 52), Few-Shot Prompt Tuner (Agent 50).

