# Agent 54 — The Refusal-Calibrator Agent

### Agent 54 — The Refusal-Calibrator Agent

*Calibrates when to refuse, when to qualify, and when to comply, against a measured baseline.*

#### The Problem

An over-refusing agent is useless. An under-refusing agent is dangerous. The default behavior (let the model decide) produces a refusal rate that varies wildly across deployments and time, and isn't measured. With a calibrator, refusal becomes a designed behavior rather than a habit picked up from the underlying model.

The general problem is **measurable refusal behavior**: ensuring the agent's refusals (and qualifications) reflect the actual risk profile and capability scope, with the behavior measured and tunable.

#### Why Naïve Approaches Fail

- 

*"Add 'refuse if unsafe' to the prompt."* Produces wildly varying refusal behavior under different framings of the same request.

- 

*"Refuse based on keyword filters."* Easy to evade. Over-refuses on benign requests.

- 

*"Have the model produce free-text refusals."* No consistency in why or how it refuses. Impossible to measure.

#### The Mechanism

A refusal taxonomy that distinguishes safety, capability, policy, and identity-based refusals. A per-request classifier that maps the request into the taxonomy and produces a calibrated response. A qualification path that allows the agent to partially answer with explicit caveats. A measurement harness that evaluates the agent's refusal behavior against a labeled evaluation set on a regular cadence.

![Pattern 078 — Agent 54 — The Refusal-Calibrator Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df70318190b4caf85a8_codex-pattern-078-agent-54-the-refusal-calibrator-agent-the-mechanism.png)

```python
# alignment/refusal_calibrator.py
from dataclasses import dataclass, field
from enum import Enum

class RefusalClass(Enum):
    SAFETY = "safety"               # unsafe content / harm
    CAPABILITY = "capability"        # outside agent's competence
    POLICY = "policy"                # constitution or operator policy
    IDENTITY = "identity"            # outside agent's role
    NONE = "none"                    # comply

@dataclass
class RefusalDecision:
    decision: str               # "comply" | "qualify" | "refuse"
    refusal_class: RefusalClass
    rationale: str
    qualification: str | None   # for "qualify" decisions
    alternative_path: str | None  # what the user can do instead

class RefusalCalibratorAgent:
    def __init__(self, classifier_llm, *, safety_threshold: float = 0.85,
                 capability_threshold: float = 0.6):
        self.classifier = classifier_llm
        self.safety_threshold = safety_threshold
        self.capability_threshold = capability_threshold
    
    def decide(self, request: str, context: dict,
               self_model_lookup: callable) -> RefusalDecision:
        analysis = self._analyze(request, context)
        # 1. Safety hard-stop
        if analysis["safety_risk"] >= self.safety_threshold:
            return RefusalDecision(
                decision="refuse",
                refusal_class=RefusalClass.SAFETY,
                rationale=analysis["safety_rationale"],
                qualification=None,
                alternative_path=analysis.get("safe_alternative"),
            )
        # 2. Policy / constitution check (covered by Agent 53; here we surface result)
        if analysis["policy_violation"]:
            return RefusalDecision(
                decision="refuse",
                refusal_class=RefusalClass.POLICY,
                rationale=analysis["policy_rationale"],
                qualification=None,
                alternative_path=analysis.get("policy_alternative"),
            )
        # 3. Capability check via self-model
        capability_confidence = self_model_lookup(analysis["required_capability"])
        if capability_confidence < self.capability_threshold:
            # Try to qualify rather than refuse outright
            if analysis.get("qualified_answer_possible"):
                return RefusalDecision(
                    decision="qualify",
                    refusal_class=RefusalClass.CAPABILITY,
                    rationale=f"I am uncertain on {analysis['required_capability']} (confidence {capability_confidence:.2f})",
                    qualification=analysis["qualification_text"],
                    alternative_path=None,
                )
            return RefusalDecision(
                decision="refuse",
                refusal_class=RefusalClass.CAPABILITY,
                rationale=f"This requires {analysis['required_capability']}, which is outside my measured competence.",
                qualification=None,
                alternative_path=analysis.get("escalation_target"),
            )
        # 4. Identity check
        if analysis["outside_role"]:
            return RefusalDecision(
                decision="refuse",
                refusal_class=RefusalClass.IDENTITY,
                rationale=analysis["identity_rationale"],
                qualification=None,
                alternative_path=analysis.get("redirect_target"),
            )
        return RefusalDecision(
            decision="comply", refusal_class=RefusalClass.NONE,
            rationale="", qualification=None, alternative_path=None,
        )
    
    def _analyze(self, request: str, context: dict) -> dict:
        # The classifier LLM produces a structured analysis
        return self.classifier.call(
            messages=[
                {"role": "system", "content": REFUSAL_ANALYSIS_PROMPT},
                {"role": "user", "content": f"Request: {request}\nContext: {context}"}
            ],
            schema=REFUSAL_ANALYSIS_SCHEMA,
        )

REFUSAL_ANALYSIS_PROMPT = """\
Analyze a request to determine the appropriate response.

For each request, produce:
  - safety_risk (0-1): probability the request seeks unsafe output
  - safety_rationale (string): if risk is high, why
  - safe_alternative (string|null): a safer adjacent request
  - policy_violation (bool): does this violate the operator's policy?
  - policy_rationale (string): if violated, which policy
  - required_capability (string): the capability needed to comply
  - qualified_answer_possible (bool): can we partially help?
  - qualification_text (string): the partial-help framing
  - outside_role (bool): does this fall outside the agent's role?
  - identity_rationale (string): if outside role, why
  - escalation_target (string|null): where to redirect
"""
```

#### Trade-offs and Alternatives

The calibrator adds a classification call per request. For agents with very narrow scope (a customer-service agent for one product), a hand-written refusal policy is simpler. The calibrator earns its keep when the agent's scope is broad enough that refusal-by-rule misses cases.

The measurement harness is the critical companion. Without measuring refusal behavior on a labeled set, the calibrator's settings are guesswork. With the measurement, the trade-off between false-refusals and false-complies becomes a tunable.

#### Production Failure Modes

- 

**Classifier inconsistency:** The same request, asked twice, gets classified differently. Mitigate by sampling-and-voting on classifier outputs for high-stakes requests (Self-Consistency Voter, Agent 15, applied to the refusal classification).

- 

**Threshold drift:** The operator wants to reduce refusals, thresholds get pulled down, and false-comply rate creeps up unobserved. Mitigate by measuring false-comply rate on a labeled set on every threshold change.

- 

**Qualification weasel:** The "qualify" path produces answers with so many caveats they're useless to the user. Mitigate by reviewing qualified outputs against the standard "good qualification" (a partial answer that's still actionable).

#### Case Study

A customer-facing agent at a B2C vendor brought its refusal rate from 8% (pre-calibrator) to 3% and its false-comply rate from 1% to under 0.1% (where "false-comply" is measured against a labeled adversarial test set). The calibrator measurement runs monthly, and thresholds are adjusted quarterly based on the false-refusal and false-comply rate observed.

**Pairs with:** Memory-of-Self (Agent 27), Constitution-Bound (Agent 53), Red-Team Auditor (Agent 56).
