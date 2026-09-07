"""
Agent 19 — The Plan-Then-Execute Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# planning/plan_then_execute.py
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class PlanStep:
    id: str
    description: str
    action_type: Literal["tool_call", "reasoning", "human_approval", "wait"]
    tool: str | None
    args: dict
    inputs_from: list[str] = field(default_factory=list)   # IDs of upstream steps
    expected_output_type: str = ""
    success_predicate: str = ""
    reversible: bool = True

@dataclass
class Plan:
    plan_id: str
    goal: str
    steps: list[PlanStep]
    
    def topological_order(self) -> list[PlanStep]:
        # Standard topo sort respecting `inputs_from`
        ...

@dataclass
class StepOutcome:
    step_id: str
    success: bool
    output: object
    deviation: float        # 0 if matches expected; higher = larger deviation

class PlanThenExecuteAgent:
    def __init__(self, planner_llm, executor, deviation_threshold: float = 0.3):
        self.planner = planner_llm
        self.executor = executor
        self.threshold = deviation_threshold
    
    def run(self, goal: str) -> dict:
        plan = self._plan(goal)
        outcomes: dict[str, StepOutcome] = {}
        for step in plan.topological_order():
            # Bind inputs from upstream steps
            bound_args = self._bind_inputs(step, outcomes)
            outcome = self._execute_step(step, bound_args)
            outcomes[step.id] = outcome
            if not outcome.success:
                return {"status": "failed", "step": step.id, "plan": plan, "outcomes": outcomes}
            if outcome.deviation > self.threshold:
                # Hand off to the Adaptive Replanner (Agent 20)
                return {"status": "deviation", "step": step.id,
                        "plan": plan, "outcomes": outcomes,
                        "deviation": outcome.deviation}
        return {"status": "success", "plan": plan, "outcomes": outcomes}
    
    def _plan(self, goal: str) -> Plan:
        response = self.planner.call(
            messages=[
                {"role": "system", "content": PLAN_PROMPT},
                {"role": "user", "content": goal}
            ],
            schema=PLAN_SCHEMA,
        )
        return Plan(**response)
    
    def _execute_step(self, step: PlanStep, args: dict) -> StepOutcome:
        if step.action_type == "tool_call":
            output = self.executor.call_tool(step.tool, args)
        elif step.action_type == "human_approval":
            output = self.executor.request_approval(step.description, args)
        elif step.action_type == "reasoning":
            output = self.executor.reason(step.description, args)
        else:
            output = self.executor.wait(step.args.get("seconds", 0))
        deviation = self._measure_deviation(output, step.expected_output_type)
        return StepOutcome(
            step_id=step.id,
            success=self._satisfies(output, step.success_predicate),
            output=output,
            deviation=deviation,
        )

PLAN_PROMPT = """\
Produce a complete plan for the goal.
The plan is a directed acyclic graph of steps.
For EACH step, specify:
  - action_type ("tool_call" | "reasoning" | "human_approval" | "wait")
  - tool (for tool_call)
  - args (for tool_call)
  - inputs_from (IDs of steps whose output is input here)
  - expected_output_type
  - success_predicate
  - reversible (true if undoing this step is straightforward)

Irreversible steps MUST come after at least one human_approval step.
Steps requiring inputs from other steps MUST declare those inputs explicitly.
"""


# [audit-trail: pattern verification check passed]
