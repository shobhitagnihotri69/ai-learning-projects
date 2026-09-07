# Agent 11 — The Constraint-Satisfaction Agent

### Agent 11 — The Constraint-Satisfaction Agent

*Solves problems by progressively narrowing the feasible region.*

#### The Problem

Many agent problems aren't search problems. Rather, they're constraint problems. The user wants a schedule that respects fifteen overlapping rules, a configuration that doesn't violate any of the eight policies, a contract that doesn't introduce any of the seven prohibited clauses, and a code change that compiles and passes the seventeen lint rules. These are problems where "search and check" is exponentially worse than "constrain and propagate."

The general problem is **CSP-shaped reasoning**: problems with a finite set of variables, finite domains, and constraints that interact in non-trivial ways, where the right answer is a witness of feasibility (or a minimal explanation of infeasibility), not a chain-of-thought derivation.

#### Why Naïve Approaches Fail

- 

*"Ask the model to find a valid schedule."* Works on toy cases. On real cases with more than a handful of overlapping constraints, the model produces an answer that violates one or more constraints, and the violation is buried.

- 

*"Ask the model to check the answer against the constraints."* Catches obvious violations, but misses subtle ones and scales poorly with the number of constraints.

- 

*"Have the model write the constraints into Python and run them."* Better, but the constraint encoding step is the hard part. Most constraints in real problems are easy to state in natural language and hard to encode correctly.

#### The Mechanism

The constraint-satisfaction agent encodes the problem as variables with finite domains and constraints between them, runs a solver (a real CSP solver, not an LLM), and emits either a witness or a minimal explanation of infeasibility.

![Pattern 035 — Agent 11 — The Constraint-Satisfaction Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd32f5c607539ef296a_codex-pattern-035-agent-11-the-constraint-satisfaction-agent-the-mechanism.png)

```python
# reasoning/constraint_satisfaction.py
from dataclasses import dataclass
from ortools.sat.python import cp_model   # production CSP solver

@dataclass
class CSPVariable:
    name: str
    domain: list                       # finite enumeration of allowed values
    natural_description: str

@dataclass
class CSPConstraint:
    name: str
    variables: list[str]
    natural_description: str
    encoded: object                    # solver-specific encoding
    confidence: float                  # 0-1, the LLM's confidence in encoding

@dataclass
class CSPResult:
    feasible: bool
    assignment: dict[str, object] | None
    infeasibility_explanation: list[str] | None   # minimal conflicting subset
    encoding_confidence: float

class ConstraintSatisfactionAgent:
    def __init__(self, encoder_llm):
        self.encoder = encoder_llm
    
    def solve(self, problem_statement: str) -> CSPResult:
        # 1. LLM extracts variables and constraints with confidence per constraint
        variables, constraints = self._extract(problem_statement)
        # 2. Refuse to solve if encoding confidence too low
        min_confidence = min(c.confidence for c in constraints)
        if min_confidence < 0.7:
            return CSPResult(
                feasible=False, assignment=None,
                infeasibility_explanation=["encoding_uncertainty"],
                encoding_confidence=min_confidence,
            )
        # 3. Build solver model
        model = cp_model.CpModel()
        var_handles = self._materialize_variables(model, variables)
        for c in constraints:
            self._add_constraint(model, c, var_handles)
        # 4. Solve
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        if status == cp_model.OPTIMAL:
            return CSPResult(
                feasible=True,
                assignment={v.name: solver.Value(var_handles[v.name]) for v in variables},
                infeasibility_explanation=None,
                encoding_confidence=min_confidence,
            )
        # 5. If infeasible, find the minimal unsatisfiable core
        return CSPResult(
            feasible=False, assignment=None,
            infeasibility_explanation=self._minimal_core(model, constraints, var_handles),
            encoding_confidence=min_confidence,
        )
    
    def _extract(self, problem_statement: str):
        # The LLM produces a structured representation of variables + constraints
        # with confidence ratings on each constraint translation.
        result = self.encoder.call(
            messages=[
                {"role": "system", "content": ENCODING_PROMPT},
                {"role": "user", "content": problem_statement}
            ],
            schema=ENCODING_SCHEMA,
        )
        return result["variables"], result["constraints"]
```

#### Trade-offs and Alternatives

Encoding the problem as a CSP costs an extra LLM call (and an extra layer of things that can go wrong). For problems with very few constraints, direct reasoning is cheaper. The pattern earns its cost when constraints are numerous, interact in non-obvious ways, or when the user needs an explanation of infeasibility.

For problems with continuous variables or non-linear constraints, replace the CSP solver with an SMT solver (Z3) or a linear/mixed-integer programming solver (CBC, Gurobi). The pattern is identical, and only the solver changes.

#### Production Failure Modes

- 

**Encoding error:** The LLM translates a constraint into the solver's language incorrectly. The solver returns a "valid" assignment that the user immediately recognizes as wrong. Mitigate by surfacing the encoded constraints back to the user for review on first use, then auto-validating on subsequent runs against a labeled set.

- 

**Constraint omission:** The LLM misses a constraint that was implicit in the problem statement. Mitigate by having a second LLM (or a different prompt) check whether the encoded set captures everything in the original statement.

- 

**Solver timeout:** Real-world problems can be NP-hard. The solver runs out of time. Mitigate by setting explicit timeouts, returning best-effort partial assignments, and providing an "infeasibility under time budget" output distinct from "no solution exists."

#### Case Study

An enterprise meeting-scheduler agent books across three calendars, two physical rooms, four time-zone preferences, and a per-participant maximum daily meeting count. The Constraint-Satisfaction pattern returns either a slot or a precise reason no slot exists ("the conflict is between Alice's no-meetings-Friday rule and the room's morning-availability window").

Before the pattern was introduced, meeting requests with more than three participants failed roughly 35% of the time and the failure mode was opaque to the user. After, the failure rate dropped to 4% and every failure carried an actionable explanation.

**Pairs with:** Symbolic-Neural Bridge (Agent 13), Resource-Aware Scheduler (Agent 21), Counterfactual Reasoner (Agent 9).
