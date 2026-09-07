# Agent 17 — The ReAct Loop Agent

### Agent 17 — The ReAct Loop Agent

*Interleaves reasoning and action steps until a termination condition is reached.*

#### The Problem

Some agent problems don't have plans that can be sensibly produced upfront. The environment is stochastic enough, the user's intent is open-ended enough, or the action space is dynamic enough that planning ahead is wasted work. By the time the plan is half-executed, the world has changed enough that the remaining plan is wrong. For these problems, the right shape is reactive: think, act, observe, think again.

The general problem is **uncertain-environment progress**: making progress toward a goal in an environment where each step's outcome is informative enough to change the next step's choice.

#### Why Naïve Approaches Fail

- 

*"Plan everything, then execute."* The plan is stale after step three, but the executor blindly follows.

- 

*"Have the model just call tools without reasoning."* Loses the reasoning trace. Debugging becomes opaque, the model picks tools based on local-surface match rather than goal-relevance.

- 

*"Skip the loop and just sample one tool call."* Works for trivially-one-step problems, but fails for anything multi-step.

#### The Mechanism

ReAct (the canonical reactive pattern in agent literature) has an explicit thought-action-observation loop with structural support: bounded steps, observed termination, per-step traceability, and (in this book's version) progress measurement.

![Pattern 041 — Agent 17 — The ReAct Loop Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd4c3c147f0711e5b88_codex-pattern-041-agent-17-the-react-loop-agent-the-mechanism.png)

```python
# planning/react_loop.py
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class ReactStep:
    step: int
    thought: str
    action: dict | None     # None on termination steps
    observation: dict | None

@dataclass
class ReactResult:
    final_answer: object | None
    steps: list[ReactStep]
    terminated: bool
    failure_reason: str | None = None

class ReactLoopAgent:
    def __init__(self, policy_llm, tools: dict, *, max_steps: int = 20,
                 progress_check: Callable[[list[ReactStep]], bool] | None = None):
        self.policy = policy_llm
        self.tools = tools
        self.max_steps = max_steps
        self.progress_check = progress_check or self._default_progress_check
    
    def run(self, goal: str) -> ReactResult:
        steps: list[ReactStep] = []
        for i in range(self.max_steps):
            response = self.policy.call(
                messages=[
                    {"role": "system", "content": REACT_PROMPT},
                    {"role": "user", "content": format_react_input(goal, steps, self.tools)}
                ],
                schema=REACT_SCHEMA,
            )
            step = ReactStep(
                step=i,
                thought=response["thought"],
                action=response.get("action"),
                observation=None,
            )
            if response.get("terminate"):
                step.action = None
                steps.append(step)
                return ReactResult(
                    final_answer=response.get("final_answer"),
                    steps=steps, terminated=True,
                )
            # Execute the action
            tool_name = step.action["tool"]
            if tool_name not in self.tools:
                step.observation = {"error": f"unknown_tool:{tool_name}"}
            else:
                try:
                    step.observation = self.tools[tool_name].invoke(step.action["args"])
                except Exception as e:
                    step.observation = {"error": str(e)}
            steps.append(step)
            # Progress check
            if not self.progress_check(steps):
                return ReactResult(
                    final_answer=None, steps=steps,
                    terminated=False, failure_reason="no_progress",
                )
        return ReactResult(
            final_answer=None, steps=steps,
            terminated=False, failure_reason="step_budget_exhausted",
        )
    
    @staticmethod
    def _default_progress_check(steps: list[ReactStep]) -> bool:
        """Detect simple loops: same (tool, args) repeated 3 times consecutively."""
        if len(steps) < 6:
            return True
        recent_actions = [(s.action["tool"], str(s.action["args"]))
                          for s in steps[-6:] if s.action]
        unique = set(recent_actions)
        return len(unique) > 1
```

#### Trade-offs and Alternatives

ReAct is responsive but has no concept of progress without an explicit progress check. Vanilla ReAct (no progress check, no bound) is the agent pattern most likely to loop forever in production. This book's version always has bounded steps, a default loop-detector, and an externalized failure reason.

For problems where the action space is small and stable, ReAct is overkill. A fixed-form policy (a switch statement plus a model call) gets the same behavior at much lower cost. ReAct earns its complexity when the policy genuinely has to *choose* among many actions per step.

#### Production Failure modes

- 

**Loop-detector evasion:** The model varies its arguments slightly to evade the loop check while still doing the same thing semantically. Mitigate by canonicalizing arguments before the loop check. For free-text arguments, use an embedding-similarity check.

- 

**Premature termination:** The model declares "done" before the goal is actually achieved. Mitigate by adding an explicit goal-check predicate that the harness evaluates independently of the model's self-report.

- 

**Tool-result misinterpretation:** The model's next thought misreads the previous tool's result, and the agent acts on a phantom observation. Mitigate by validating tool results against typed schemas before passing them to the next prompt.

#### Case Study

A customer-support ticket-resolver agent at a fintech runs entire support sessions as forty-step-bounded ReAct loops over a defined toolset (account lookup, transaction search, refund eligibility, escalation creation).

The agent resolves approximately 31% of L1 tickets without escalation. On tickets that escalate, the agent's transcript becomes the starting point for the human, reducing average human handle time by 47%.

**Pairs with:** Tool Selector (Agent 30), Reflection (Agent 47), Adaptive Replanner (Agent 20).
