# Agent 20 — The Adaptive Replanner Agent

### Agent 20 — The Adaptive Replanner Agent

*Detects when execution has drifted from the plan and rebuilds the plan from the new state.*

#### The Problem

A plan is a forecast. And forecasts go wrong. Without a replanner, a plan that goes wrong is executed wrong: the executor keeps following the steps even when the world no longer matches the plan's assumptions. The result is a confidently completed action sequence that doesn't reach the goal.

The general problem is **planning under model-execution mismatch**: detecting when the executed-state has diverged from the planned-state enough to invalidate the remaining plan, and rebuilding the plan from the new state.

#### Why Naïve Approaches Fail

- 

*"Replan on every step."* Wasteful and nullifies the benefit of upfront planning.

- 

*"Never replan."* Brittle, any unexpected outcome derails execution.

- 

*"Have the model decide whether to replan on each step."* The model is bad at this decision. It tends to either replan constantly (paranoid mode) or refuse to replan when it should (committed-to-the-plan mode).

#### The Mechanism

The adaptive replanner watches execution against an explicit expected-trajectory model, classifies deviations into recoverable and non-recoverable, applies a replan-trigger policy with hysteresis to prevent thrashing, and hands the new state to the planner with the previous plan and the reason for replanning as context.

![Pattern 044 — Agent 20 — The Adaptive Replanner Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dee0318190b4caf8230_codex-pattern-044-agent-20-the-adaptive-replanner-agent-the-mechanism.png)

```python
# planning/adaptive_replanner.py
from dataclasses import dataclass, field

@dataclass
class TrajectoryExpectation:
    step_id: str
    expected_output_type: str
    expected_output_schema: dict
    expected_state_predicate: str   # what should be true of the world after this step

@dataclass
class DeviationClassification:
    severity: str       # "noise" | "recoverable" | "structural"
    affected_steps: list[str]    # downstream steps invalidated by the deviation
    cause_hypothesis: str
    replan_required: bool

class AdaptiveReplannerAgent:
    def __init__(self, planner_llm, classifier_llm,
                 *, hysteresis: int = 1, max_replans: int = 3):
        self.planner = planner_llm
        self.classifier = classifier_llm
        self.hysteresis = hysteresis
        self.max_replans = max_replans
        self._recent_replans = 0
        self._steps_since_replan = 0
    
    def observe(self, plan, step, actual_outcome) -> DeviationClassification:
        expected = self._expected_trajectory(plan, step)
        classification = self._classify(actual_outcome, expected)
        self._steps_since_replan += 1
        if classification.replan_required and self._recent_replans < self.max_replans:
            if self._steps_since_replan >= self.hysteresis:
                self._recent_replans += 1
                self._steps_since_replan = 0
                return classification
            classification.replan_required = False   # hysteresis veto
        return classification
    
    def replan(self, original_goal, executed_steps, current_state,
               deviation: DeviationClassification) -> dict:
        response = self.planner.call(
            messages=[
                {"role": "system", "content": REPLAN_PROMPT},
                {"role": "user", "content": format_replan_input(
                    original_goal, executed_steps, current_state, deviation)}
            ],
            schema=PLAN_SCHEMA,
        )
        return response
    
    def _classify(self, outcome, expected) -> DeviationClassification:
        if matches_schema(outcome.output, expected.expected_output_schema):
            return DeviationClassification(
                severity="noise", affected_steps=[],
                cause_hypothesis="output_within_schema", replan_required=False,
            )
        # Severity comes from the classifier LLM
        response = self.classifier.call(
            messages=[
                {"role": "system", "content": DEVIATION_PROMPT},
                {"role": "user", "content": format_deviation_input(outcome, expected)}
            ],
            schema=DEVIATION_SCHEMA,
        )
        return DeviationClassification(**response)

REPLAN_PROMPT = """\
The execution of a plan has deviated from expectations.
Given:
  - The original goal
  - The steps already executed (with their outcomes)
  - The current state of the world
  - The deviation classification

Produce a NEW plan that:
  1. Acknowledges the work already done (do not redo successful steps).
  2. Addresses the cause of the deviation if needed.
  3. Reaches the original goal from the current state.

Do not paper over the deviation — if the goal is now unreachable, say so
and propose the closest achievable goal.
"""
```

#### Trade-offs and Alternatives

The replanner adds latency on every replan and risks oscillation between two plans if the deviation classifier is noisy. The hysteresis parameter is the dial: too low and the agent thrashes, too high and it commits to a failing plan too long. Tune empirically against an evaluation set that includes both stable and unstable runs.

For environments where deviations are rare but catastrophic (one-shot deployments, irreversible operations), the right shape is plan-then-execute *with operator-mediated replanning*: deviation triggers an alarm and pauses the agent, and a human authorizes the replan before it runs.

#### Production Failure Modes

- 

**Replan-oscillation:** The replanner produces plan A, hits a deviation, replans to plan B, hits a deviation, replans back to A. Mitigate with a no-repeat constraint on the planner: each new plan must differ structurally from the most recent N rejected plans.

- 

**Deviation underestimation:** The classifier marks structural drift as "noise", and the agent continues executing a doomed plan. Mitigate by sampling deviation classifications for human review and recalibrating.

- 

**State-inference error:** The replanner is given a current state that doesn't reflect reality. The new plan starts from the wrong assumptions. Mitigate by reconstructing the current state from observation (re-query the environment) rather than from internal bookkeeping at replan time.

#### Case Study

A multi-leg travel-booking agent at a corporate-travel vendor combines three carriers and two transfers per trip on average. Flight delays, cancellations, and rebookings produce frequent deviation triggers. The replanner rebuilds the trip plan in under five seconds per replan, and replanning typically completes before the user has noticed the upstream disruption.

The on-time-rebook rate (the customer's flight changes for which the agent presented a valid alternative before the customer asked) rose from 41% to 88% after the replanner was added.

**Pairs with:** Plan-Then-Execute (Agent 19), Drift Detector (Agent 59), Hierarchical Decomposer (Agent 16).
