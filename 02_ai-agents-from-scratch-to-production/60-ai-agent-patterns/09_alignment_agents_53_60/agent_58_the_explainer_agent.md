# Agent 58 — The Explainer Agent

### Agent 58 — The Explainer Agent

*Produces post-hoc explanations of its own decisions that survive expert scrutiny.*

#### The Problem

After the agent has acted, it should be able to say why. The default behavior ("let the model summarize its reasoning") produces explanations that look plausible but often diverge from what actually happened. The user accepts the explanation, but the explanation is wrong.

The general problem is **honest post-hoc explanation**: producing a structured rationale that genuinely reflects the inputs, the policy, and the constraints that drove the decision, not a fabricated reasoning chain reconstructed after the fact.

#### Why Naïve Approaches Fail

- 

*"Ask the model to explain itself."* Produces a plausible-sounding explanation, but often it's not what actually drove the decision.

- 

*"Show the chain-of-thought trace."* Closer to honest, but still depends on the trace being a true record (and the user being able to read it).

- 

*"Include audit logs."* Captures what happened, but doesn't translate it into a user-comprehensible rationale.

#### The Mechanism

A structured-rationale schema that names the inputs, the policy applied, and the principal alternatives considered. A generation step that produces the rationale from the actual execution trace rather than confabulating after the fact. A validation step that checks the rationale against the trace to catch divergence. A user-facing rendering at a level of detail appropriate to the consumer.

![Pattern 082 — Agent 58 — The Explainer Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df16c87334148154d25_codex-pattern-082-agent-58-the-explainer-agent-the-mechanism.png)

```python
# alignment/explainer.py
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
```

#### Trade-offs and Alternatives

The explainer adds two LLM calls per decision: the explainer and the validator. For high-volume agents, this is real cost. The pattern is justified for decisions where the user must understand *why* (regulatory contexts, adverse-action notices, recommendations of consequence) and unnecessary for decisions where the user only needs the output.

For decisions where a chain-of-thought trace is itself acceptable to the user (technical audience, debugging context), surface the trace directly and skip the explainer.

#### Production Failure Modes

- 

**Validation false negatives:** The validator marks an unfaithful explanation as faithful and the divergence ships. Mitigate by sampling validations for human review and recalibrating.

- 

**Explainer over-paraphrase:** The explainer paraphrases the rationale enough that it no longer precisely matches the trace, even though the substance is faithful. Mitigate by requiring more direct quoting of trace elements.

- 

**Audience mismatch:** The "general audience" rendering is inscrutable to actual users. Mitigate by testing explanations on representative users and tuning.

#### Case Study

A credit-decisioning agent at a fintech pairs every adverse-action notice with an explainer-produced rationale that survives auditor review at a rate of 98%. The rationale lists the specific credit-data inputs (for example, "debt-to-income ratio of 0.51 exceeds the policy threshold of 0.45 for this product tier"), the policies in effect, and the alternatives considered (for example, "lower credit-line amount was considered, but the applicant's stated need exceeded the maximum amount that would have approved"). The pattern replaced a hand-written explanation process at roughly one-quarter the per-decision labor cost.

**Pairs with:** Chain-of-Thought Auditor (Agent 8), Provenance Tracker (Agent 55), Constitution-Bound (Agent 53).
