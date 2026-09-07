"""
Agent 54 — The Refusal-Calibrator Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# alignment/refusal_calibrator.py
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

