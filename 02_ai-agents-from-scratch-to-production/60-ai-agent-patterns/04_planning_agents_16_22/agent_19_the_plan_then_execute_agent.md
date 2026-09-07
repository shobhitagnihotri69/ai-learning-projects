# Agent 19 — The Plan-Then-Execute Agent

### Agent 19 — The Plan-Then-Execute Agent

*Produces a full plan upfront, executes it under monitoring, and only re-plans on deviation.*

#### The Problem

ReAct is responsive but commits one step at a time. Some problems benefit from the opposite shape: think hard upfront, produce a complete plan, and execute it. The shape dominates where the cost of an irreversible action is high (so seeing the whole plan before any action is valuable) and where the cost of latency before the first action is acceptable.

The general problem is **front-loaded planning**: deciding all the actions upfront when doing so produces better decisions than deciding them one-at-a-time during execution.

#### Why Naïve Approaches Fail

- 

*"Just use ReAct."* Loses the upfront-planning benefit. Each step is decided in isolation. The first irreversible step happens early without the full context of what comes after.

- 

*"Plan upfront, then execute blindly."* Plan-Then-Execute without deviation monitoring is brittle. Any unexpected outcome derails execution.

- 

*"Plan in natural language and execute by parsing."* The parsing is unreliable. The plan should be structured, not prose.

#### The Mechanism

The agent produces a complete plan before taking any action: a sequence or DAG of tool calls with expected outcomes. Execution is a separate component that runs the plan with strict typing on inputs and outputs, monitors each step against the expected outcome, and invokes the planner again when deviation exceeds a threshold (which is the Adaptive Replanner, Agent 20).

![Pattern 043 — Agent 19 — The Plan-Then-Execute Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5deea412be96d299aa68_codex-pattern-043-agent-19-the-plan-then-execute-agent-the-mechanism.png)

```python
# planning/plan_then_execute.py
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
```

#### Trade-offs and Alternatives

Plan-Then-Execute is the right pattern when irreversibility and latency-tolerance both favor upfront thinking. It's the wrong pattern when the environment is too uncertain for a plan to survive contact with reality.

The default fall-back is the Adaptive Replanner (Agent 20), which makes Plan-Then-Execute robust by replanning on detected deviation.

For tasks where partial completion is valuable, allow the executor to commit each successful step and persist its result, so a deviation late in the plan doesn't invalidate the work already done.

#### Production Failure Modes

- 

**Plan-execution mismatch on irreversible steps:** A step turns out to be irreversible despite being marked `reversible=true`, and the rollback path fails. Mitigate by treating reversibility as a property of the tool, set by the tool author, not the planner.

- 

**Deviation-threshold over-tuning:** The threshold is too low (constant replanning) or too high (catastrophic drift). Tune empirically: instrument the deviation distribution and pick a threshold at the 90th percentile of "normal" runs.

- 

**Input-binding errors:** A step's `inputs_from` reference produces a value of the wrong shape, and the bound args are wrong. Mitigate with typed input/output schemas on every step.

#### Case Study

An account-migration agent at a SaaS vendor produces a forty-step migration plan, surfaces it to the operator for approval (with the plan rendered as a Gantt-style timeline), and executes the approved plan with per-step deviation monitoring.

Each migration touches multiple internal systems and at least one external vendor. The plan-then-execute shape was chosen because mid-flight surprises are expensive and operator confidence in the plan is critical.

The pattern handled approximately 2,800 migrations in its first year with a measured deviation rate of 12% (requiring replanning) and a hard-failure rate of 0.4%.

**Pairs with:** Hierarchical Decomposer (Agent 16), Side-Effect Auditor (Agent 37), Adaptive Replanner (Agent 20).

