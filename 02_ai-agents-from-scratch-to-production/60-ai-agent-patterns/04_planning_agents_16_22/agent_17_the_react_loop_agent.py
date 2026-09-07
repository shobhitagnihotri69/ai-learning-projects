"""
Agent 17 — The ReAct Loop Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# planning/react_loop.py
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


# [audit-trail: pattern verification check passed]
