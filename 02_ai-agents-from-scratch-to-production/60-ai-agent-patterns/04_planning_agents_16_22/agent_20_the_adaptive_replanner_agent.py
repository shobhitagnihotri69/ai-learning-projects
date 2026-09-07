"""
Agent 20 — The Adaptive Replanner Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# planning/adaptive_replanner.py
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

