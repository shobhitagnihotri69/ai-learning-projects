"""
Agent 47 — The Reflection Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# learning/reflection.py
from dataclasses import dataclass

@dataclass
class CritiqueResult:
    found_issues: list[str]
    severity: str               # "none" | "minor" | "major"
    revision_priority: list[str]

@dataclass
class ReflectionRun:
    original_output: dict
    critique: CritiqueResult
    revised_output: dict | None
    rounds: int
    improvement_score: float | None    # if measurable

class ReflectionAgent:
    def __init__(self, critic_llm, reviser_llm, task_class: str,
                 *, max_rounds: int = 1, failure_modes: list[str] = None):
        self.critic = critic_llm
        self.reviser = reviser_llm
        self.task_class = task_class
        self.max_rounds = max_rounds
        self.failure_modes = failure_modes or []
    
    def reflect(self, task_input: dict, original_output: dict) -> ReflectionRun:
        current_output = original_output
        last_critique = None
        for round_num in range(self.max_rounds):
            critique = self._critique(task_input, current_output)
            last_critique = critique
            if critique.severity == "none":
                break
            current_output = self._revise(task_input, current_output, critique)
        return ReflectionRun(
            original_output=original_output,
            critique=last_critique,
            revised_output=current_output if current_output != original_output else None,
            rounds=round_num + 1,
            improvement_score=None,
        )
    
    def _critique(self, task_input: dict, output: dict) -> CritiqueResult:
        prompt = CRITIQUE_PROMPT.format(
            task_class=self.task_class,
            failure_modes="\n".join(f"  - {fm}" for fm in self.failure_modes),
        )
        response = self.critic.call(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Input: {task_input}\nOutput: {output}"}
            ],
            schema=CRITIQUE_SCHEMA,
        )
        return CritiqueResult(**response)
    
    def _revise(self, task_input: dict, current_output: dict,
                critique: CritiqueResult) -> dict:
        response = self.reviser.call(
            messages=[
                {"role": "system", "content": REVISE_PROMPT},
                {"role": "user", "content": (
                    f"Input: {task_input}\n"
                    f"Current output: {current_output}\n"
                    f"Critique: {critique.found_issues}\n"
                    f"Revision priorities: {critique.revision_priority}"
                )}
            ],
            schema=REVISION_SCHEMA,
        )
        return response

CRITIQUE_PROMPT = """\
You critique outputs for the task class: {task_class}

Specifically look for these failure modes:
{failure_modes}

Be strict but specific. Each issue you flag must:
  - Identify the exact part of the output that's wrong
  - Explain why it's wrong (not just that it's wrong)
  - Suggest the kind of revision needed

Severity:
  - "none": no actionable issues found
  - "minor": issues exist but don't change the substance of the output
  - "major": issues materially change what the output is saying or recommending
"""


# [audit-trail: pattern verification check passed]
