"""
Agent 58 — The Explainer Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# alignment/explainer.py
from dataclasses import dataclass, field

@dataclass
class DecisionTrace:
    decision_id: str
    decision: dict              # what the agent decided
    inputs_used: list[dict]     # the inputs that drove it
    policies_applied: list[str] # constitutional clauses, evaluation rules
    alternatives_considered: list[dict]
    rationale_steps: list[str]  # raw reasoning trace
    
@dataclass
class StructuredRationale:
    decision: str                       # one-line summary
    key_inputs: list[str]               # human-readable list of load-bearing inputs
    policies_in_effect: list[str]
    alternatives_with_reason_rejected: list[dict]
    plain_language_explanation: str
    confidence: float
    validated_against_trace: bool

class ExplainerAgent:
    def __init__(self, explainer_llm, validator_llm):
        self.explainer = explainer_llm
        self.validator = validator_llm
    
    def explain(self, trace: DecisionTrace,
                audience: str = "general") -> StructuredRationale:
        # 1. Generate the rationale from the trace
        response = self.explainer.call(
            messages=[
                {"role": "system", "content": EXPLANATION_PROMPT.format(audience=audience)},
                {"role": "user", "content": self._format_trace(trace)}
            ],
            schema=EXPLANATION_SCHEMA,
        )
        rationale = StructuredRationale(**response, validated_against_trace=False)
        # 2. Validate the rationale against the trace
        validation = self.validator.call(
            messages=[
                {"role": "system", "content": VALIDATION_PROMPT},
                {"role": "user", "content": self._format_validation_input(trace, rationale)}
            ],
            schema=VALIDATION_SCHEMA,
        )
        if validation["divergence_detected"]:
            # The rationale claims something the trace doesn't support; revise
            rationale = self._revise(rationale, validation, trace)
        rationale.validated_against_trace = not validation["divergence_detected"]
        return rationale
    
    def _format_trace(self, trace: DecisionTrace) -> str:
        return (
            f"Decision: {trace.decision}\n"
            f"Inputs used: {trace.inputs_used}\n"
            f"Policies applied: {trace.policies_applied}\n"
            f"Alternatives considered: {trace.alternatives_considered}\n"
            f"Reasoning steps: {trace.rationale_steps}\n"
        )

EXPLANATION_PROMPT = """\
You explain a decision an agent made, for audience: {audience}

Use ONLY the trace provided. Do not introduce inputs, policies, or alternatives
that are not present in the trace.

Produce:
  - decision: the decision in one line
  - key_inputs: the 3-5 most load-bearing inputs the trace shows were used
  - policies_in_effect: the policies the trace shows applied
  - alternatives_with_reason_rejected: for each alternative the trace shows was considered, why it was rejected
  - plain_language_explanation: a paragraph an intelligent layperson can follow
  - confidence: 0-1, your confidence that this explanation is faithful to the trace
"""

VALIDATION_PROMPT = """\
You check an explanation against the trace it claims to summarize.

For each statement in the explanation, verify it is supported by the trace.
If the explanation claims an input was used that the trace doesn't show, FLAG.
If the explanation claims a policy applied that the trace doesn't show, FLAG.
If the explanation gives a reason for rejecting an alternative that doesn't appear in the trace, FLAG.

Output:
  - divergence_detected: bool
  - divergences: list of {claim_in_explanation, why_unsupported}
"""

