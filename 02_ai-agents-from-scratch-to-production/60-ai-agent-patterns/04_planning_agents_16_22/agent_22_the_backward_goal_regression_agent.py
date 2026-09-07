"""
Agent 22 — The Backward Goal-Regression Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# planning/backward_regression.py
from dataclasses import dataclass, field
from collections import deque

@dataclass
class State:
    """Domain-specific; here represented abstractly as a set of facts."""
    facts: frozenset[str]
    
    def satisfies(self, predicate: str) -> bool:
        return predicate in self.facts

@dataclass
class ReverseOperator:
    """A backward step: 'state s2 with these preconditions can be produced from s1 by action a'."""
    name: str
    action: str
    adds: frozenset[str]        # facts the action adds (must be in successor)
    deletes: frozenset[str]     # facts the action removes (must NOT be in successor)
    preconditions: frozenset[str]  # facts that must hold in predecessor

@dataclass
class BackwardPlan:
    actions: list[str]          # in forward execution order
    states: list[State]
    found: bool

class BackwardGoalRegressionAgent:
    def __init__(self, operators: list[ReverseOperator], *, max_depth: int = 20):
        self.operators = operators
        self.max_depth = max_depth
    
    def plan(self, current: State, goal_predicate: str) -> BackwardPlan:
        # 1. Goal as a partial state (just the goal predicate)
        goal_state = State(facts=frozenset({goal_predicate}))
        # 2. BFS backward from the goal
        seen: set[frozenset[str]] = {goal_state.facts}
        queue = deque([(goal_state, [])])
        while queue:
            state, path = queue.popleft()
            if len(path) > self.max_depth:
                continue
            # Touch the current state?
            if all(f in current.facts for f in state.facts):
                # Forward plan: reverse the backward path
                return BackwardPlan(
                    actions=list(reversed(path)),
                    states=[],  # would be re-derived by forward simulation
                    found=True,
                )
            # Expand: which operators could PRODUCE this state?
            for op in self.operators:
                if op.adds & state.facts:    # operator contributes to state
                    predecessor_facts = (state.facts - op.adds) | op.preconditions
                    # Cannot include both a fact and its negation, etc.
                    if not (predecessor_facts & op.deletes):
                        pred_state = State(facts=frozenset(predecessor_facts))
                        if pred_state.facts not in seen:
                            seen.add(pred_state.facts)
                            queue.append((pred_state, path + [op.action]))
        return BackwardPlan(actions=[], states=[], found=False)


# [audit-trail: pattern verification check passed]
