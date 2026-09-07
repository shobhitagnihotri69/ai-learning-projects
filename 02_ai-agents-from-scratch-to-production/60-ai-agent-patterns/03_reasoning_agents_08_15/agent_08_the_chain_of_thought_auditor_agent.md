# Agent 8 — The Chain-of-Thought Auditor Agent

### Agent 8 — The Chain-of-Thought Auditor Agent

*Verifies the validity of each step in a reasoning trace before the conclusion is acted on.*

#### The Problem

A language model emits a reasoning chain. Some of the steps follow from the previous ones, and some do not. The chain ends with a confident conclusion. Without a verification step, the conclusion is acted on — and it's wrong, in roughly one in fifteen chains, in a way that the final answer's surface form doesn't reveal.

The general problem is **local invalidity in plausible reasoning**: a chain that reads coherently but contains a step that doesn't follow, where the model has filled in the apparent connection with vocabulary that sounds like reasoning but is not. The pattern is the difference between an agent that confidently completes a wrong derivation and one that catches itself.

#### Why Naïve Approaches Fail

- 

*"Ask the model to double-check its own reasoning."* Self-evaluation in the same call as the reasoning is unreliable. The model has committed to the conclusion and finds reasons to justify it.

- 

*"Use a second pass of the same model in the same role."* Better than (1), but the model evaluates the chain as a whole rather than step-by-step. It tends to grade lenient on chains it would have produced itself.

- 

*"Run the chain through a different model."* Helps when the two models have uncorrelated failures, often doesn't.

#### The Mechanism

The auditor reads the chain step by step, asks whether each step is supported by what came before, and flags the first invalid step it finds. It doesn't produce its own reasoning, it grades the input one. The output isn't a pass/fail but a *first-invalid-step pointer*, which lets the calling system re-prompt from that point rather than restarting.

![Pattern 032 — Agent 8 — The Chain-of-Thought Auditor Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd22f5c607539ef290a_codex-pattern-032-agent-8-the-chain-of-thought-auditor-agent-the-mechanism.png)

```python
# reasoning/cot_auditor.py
from dataclasses import dataclass
from enum import Enum

class StepValidity(Enum):
    VALID = "valid"
    INVALID_FROM_PREMISES = "invalid_from_premises"
    UNSUPPORTED_FACT = "unsupported_fact"
    INVALID_INFERENCE = "invalid_inference"

@dataclass
class ChainStep:
    step_number: int
    premises_referenced: list[int]    # indices of earlier steps this depends on
    operation: str                    # "fact" | "inference" | "calculation" | "definition"
    statement: str
    cited_sources: list[str]          # for "fact" steps

@dataclass
class AuditResult:
    valid: bool
    first_invalid_step: int | None
    invalid_reason: StepValidity | None
    explanation: str
    suggested_revision_point: int | None   # step from which to re-prompt

class ChainOfThoughtAuditorAgent:
    def __init__(self, auditor_llm):
        self.llm = auditor_llm
    
    def audit(self, chain: list[ChainStep]) -> AuditResult:
        for step in chain:
            verdict = self._audit_step(step, prior_steps=chain[:step.step_number])
            if verdict != StepValidity.VALID:
                return AuditResult(
                    valid=False,
                    first_invalid_step=step.step_number,
                    invalid_reason=verdict,
                    explanation=self._explain(step, prior_steps=chain[:step.step_number]),
                    suggested_revision_point=max(0, step.step_number - 1),
                )
        return AuditResult(valid=True, first_invalid_step=None,
                           invalid_reason=None, explanation="",
                           suggested_revision_point=None)
    
    def _audit_step(self, step: ChainStep,
                    prior_steps: list[ChainStep]) -> StepValidity:
        if step.operation == "fact" and not step.cited_sources:
            return StepValidity.UNSUPPORTED_FACT
        result = self.llm.call(
            messages=[
                {"role": "system", "content": AUDITOR_PROMPT},
                {"role": "user", "content": format_audit_input(step, prior_steps)}
            ],
            schema={"type": "object", "properties": {
                "verdict": {"type": "string", "enum": [v.value for v in StepValidity]},
                "explanation": {"type": "string"}
            }, "required": ["verdict", "explanation"]}
        )
        return StepValidity(result["verdict"])

AUDITOR_PROMPT = """\
You evaluate a single step in a reasoning chain for local validity.
You see the step and ALL previous steps it might depend on.
Verdicts:
  - "valid": the step follows from premises and is well-formed.
  - "invalid_from_premises": premises cited do not support the step.
  - "unsupported_fact": step asserts a fact with no source.
  - "invalid_inference": logical/mathematical/causal error in the step itself.

You do NOT evaluate the final conclusion. You evaluate THIS step.
You are STRICT. A step that is "plausible" but not supported is invalid.
"""
```

#### Trade-offs and Alternatives

Auditing doubles (or more) the cost of producing a reasoning chain. The cost is justified when the cost of a wrong conclusion exceeds the cost of the audit by a significant multiplier. In medical, legal, financial, or operational contexts, this is essentially always true. For low-stakes chains (a model summarizing a casual email), auditing is overhead.

An alternative for very high-stakes chains is *structured proof construction*, where the model is required to produce its reasoning in a formal system (a proof assistant, a Datalog database, a SAT encoding) whose validity is mechanically checked. This is the topic of the Symbolic-Neural Bridge (Agent 13): the auditor is the lighter-weight version for chains that can't easily be formalized.

#### Production Failure Modes

- 

**Auditor lenient on its own training data:** The auditor was trained on similar chains and is reluctant to call them invalid. Mitigate by using a different model family for the auditor than for the reasoner, or by training the auditor on a deliberately adversarial dataset.

- 

**Premise reference errors:** Steps reference premises by number but the chain has been edited or renumbered. Mitigate by normalizing references and validating them before the audit runs.

- 

**First-invalid-step pointer instability:** The auditor flags different first-invalid steps on re-runs. Mitigate with self-consistency voting (Agent 15) on the auditor itself.

#### Case Study

A legal-research agent at a mid-sized firm gates every answer through a Chain-of-Thought Auditor before the answer reaches the attorney. In a six-month measurement window, the auditor caught roughly one in twelve chains as locally invalid (8.3%), with a measured false-positive rate of 2.1% (chains the auditor flagged but expert reviewers ruled valid).

The net effect: invalid-conclusion rate reaching the attorney dropped from approximately 8% in the unaudited baseline to 0.5% with the auditor in place, at a 2.4× cost per answer.

**Pairs with:** Self-Consistency Voter (Agent 15), Reflection (Agent 47), Provenance Tracker (Agent 55).
