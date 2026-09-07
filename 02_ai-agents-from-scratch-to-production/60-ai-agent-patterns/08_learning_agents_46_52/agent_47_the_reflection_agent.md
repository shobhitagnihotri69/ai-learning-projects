# Agent 47 — The Reflection Agent

### Agent 47 — The Reflection Agent

*Critiques its own output and revises before responding.*

#### The Problem

The agent produces a candidate output. Before that output reaches the user, the reflection agent reads it as if it were someone else's work, looks for the typical failure modes for the task class, and revises.

The pattern is the simplest meta-cognitive move and one of the most reliable improvements available without changing the base model.

The general problem is **single-pass quality ceiling**: outputs that are reasonable on a first attempt but obviously improvable on a second look. Reflection exploits the asymmetry between generating and critiquing — critiquing is easier than generating, and the second pass operates under different constraints (it has the candidate to react to).

#### Why Naïve Approaches Fail

- 

*"Add 'be careful and thorough' to the prompt."* No measurable effect.

- 

*"Use a higher reasoning effort setting."* Helps, but doesn't capture the specific failure modes of the task class.

- 

*"Have the model double-check inside the same call."* Self-review in the same call is unreliable. The model commits to its first answer and defends it.

#### The Mechanism

A critic prompt that names specific failure modes for the task class rather than asking for generic feedback. A revision step that takes both the original output and the critique as input. A stopping condition (typically one or two rounds). A comparison surface that exposes the original and revised versions to the operator so the value of reflection is measurable.

![Pattern 071 — Agent 47 — The Reflection Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df06c87334148154cce_codex-pattern-071-agent-47-the-reflection-agent-the-mechanism.png)

```python
# learning/reflection.py
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
```

#### Trade-offs and Alternatives

Reflection roughly doubles the cost per output. For tasks where the first-pass quality is already very high, the doubling is overhead. The pattern earns its keep when first-pass quality is below acceptable and when the critic can be tuned to catch the specific failure modes of the task.

For very high-stakes outputs, more rounds and more aggressive criticism help up to a point. But beyond that point, the reviser starts incorporating spurious "fixes" for non-issues. Tune the round count empirically.

#### Production Failure Modes

- 

**Critic over-reach:** The critic flags style preferences as issues, revisions degrade clarity to address them. Mitigate by constraining the critic to flag issues only against the named failure modes.

- 

**Revision regression:** A revision fixes one issue and introduces another. Mitigate by running the critic on the revision. Revisions that increase issue count are rejected.

- 

**Cost blow-out:** Operators use reflection for everything, cost doubles across the board. Mitigate by gating reflection on output-class (only certain task classes get reflection by default) and exposing it as a knob.

#### Case Study

A code-review agent at a developer-tooling vendor routes first-pass comments through a reflection step keyed to the failure modes "false-positive style nitpick" and "missed real bug despite plausible-looking comment." The reflection catches roughly one in four false positives before they reach the developer, dramatically improving signal-to-noise as measured by per-comment thumbs-up rates (which rose from 31% to 67% over a quarter).

**Pairs with:** Chain-of-Thought Auditor (Agent 8), Red-Team Auditor (Agent 56), Self-Consistency Voter (Agent 15).
