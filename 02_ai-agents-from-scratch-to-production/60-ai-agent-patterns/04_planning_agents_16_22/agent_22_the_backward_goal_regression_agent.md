# Agent 22 — The Backward Goal-Regression Agent

### Agent 22 — The Backward Goal-Regression Agent

*Plans from the goal state backward toward the current state.*

#### The Problem

For goals with a small set of possible final states and a large set of possible intermediate states, forward planning is wasteful: the planner explores enormous regions of state space that never connect to the goal.

The user wants a specific output (a passing compliance audit, a signed contract, a deployed feature flag at 100% traffic). Forward planning from the current state can't help itself spending most of its budget on states that don't reach the goal.

The general problem is **goal-directed search asymmetry**: when goals are narrowly specified and starting states are broad, working backward is exponentially cheaper than working forward.

#### Why Naïve Approaches Fail

- 

*"Forward planning."* Wastes most of the search budget on irrelevant branches.

- 

*"Generate the final answer, then explain how to get there."* The "explanation" is often a rationalization, not a plan.

- 

*"Hard-code the backward plan."* Works for a stable goal shape, but breaks the moment the goal changes.

#### The Mechanism

Backward goal-regression starts from the goal, applies reverse operators (state-action pairs that could produce a given state via a single action), and stops when the regression touches the current state. The result is a forward plan, derived backward.

![Pattern 046 — Agent 22 — The Backward Goal-Regression Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dee95558221b40f5232_codex-pattern-046-agent-22-the-backward-goal-regression-agent-the-mechanism.png)

```python
# planning/backward_regression.py
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
```

#### Trade-offs and Alternatives

Backward regression needs reverse operators, which require domain modeling. For domains where forward operators are easy to write but reversing them is hard (anything with side effects on external systems), backward planning is impractical.

The pattern works best in domains with strong formal structure (compliance frameworks with explicit attestation rules, configuration spaces with declarative dependencies, mathematical proof construction).

For domains where neither forward nor backward search alone is tractable, *meet-in-the-middle* search runs both directions simultaneously and stops when they meet. It's the right pattern when the cost of going either direction is roughly symmetric.

#### Production Failure Modes

- 

**Operator incompleteness:** The reverse operators don't cover all the actions that could produce a given state. The search finds no plan because it can't bridge the gap. Mitigate by validating operator coverage against historical forward executions.

- 

**Pseudo-completion:** The search "touches" the current state via a superficial fact match but the deeper state doesn't actually align. The produced plan is wrong. Mitigate by validating the final plan with a forward simulator before returning.

- 

**Combinatorial blow-up:** The backward fringe grows uncontrollably. Mitigate with heuristic guidance (admissible cost estimates per state) to focus expansion on promising regions.

#### Case Study

A regulatory-compliance agent at a financial-services firm regresses backward from each required attestation (for example, "SOC2 control X is in effect") to produce the minimal task list a compliance officer must complete.

The pattern produced 41% smaller task lists than the prior forward-planner baseline (which over-included tasks), and the time from "audit-requirement landed" to "task list available" dropped from a half-day of manual interpretation to under thirty seconds.

**Pairs with:** Constraint-Satisfaction (Agent 11), Symbolic-Neural Bridge (Agent 13), Tree-of-Thought Explorer (Agent 18).
