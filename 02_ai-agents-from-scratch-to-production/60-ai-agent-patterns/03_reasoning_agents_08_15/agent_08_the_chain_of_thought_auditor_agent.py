"""
Agent 8 — The Chain-of-Thought Auditor Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# reasoning/cot_auditor.py
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

