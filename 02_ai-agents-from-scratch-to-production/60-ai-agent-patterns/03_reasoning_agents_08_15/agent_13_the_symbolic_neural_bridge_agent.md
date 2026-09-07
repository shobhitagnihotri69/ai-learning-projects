# Agent 13 — The Symbolic-Neural Bridge Agent

### Agent 13 — The Symbolic-Neural Bridge Agent

*Translates natural-language problems into formal expressions and back.*

#### The Problem

Large language models are bad at arithmetic, logic, and any computation whose answer is determined by a closed-form mechanism. They're very good at converting natural language into the syntax of a formal system.

The asymmetry is the agent-engineering opportunity: the model does the translation, a real solver does the computation, and the model does the translation back.

The general problem is **using the wrong tool for the closed-form parts**: forcing a probabilistic language model to do work a deterministic solver could do in microseconds and get exactly right. Every agent in mathematics, logic, scheduling, optimization, or formal verification needs this pattern.

#### Why Naïve Approaches Fail

- 

*"Have the model do the arithmetic."* Wrong on any non-trivial problem. The model produces plausible-looking but wrong numbers.

- 

*"Use chain-of-thought to step through the math."* Better, still wrong with non-trivial probability.

- 

*"Tool-call a calculator on every arithmetic step."* Works for arithmetic, but doesn't generalize to logic, scheduling, optimization, theorem-proving.

#### The Mechanism

Parse the problem into a target formalism (SMT-LIB for logic, linear programming for optimization, Prolog or Datalog for relational queries, Z3 for satisfiability), invoke the solver with explicit timeouts and bounds, and interpret the solver's output back into natural language with the formal certificate preserved.

![Pattern 037 — Agent 13 — The Symbolic-Neural Bridge Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd3f43a036859343f31_codex-pattern-037-agent-13-the-symbolic-neural-bridge-agent-the-mechanism.png)

```python
# reasoning/symbolic_neural_bridge.py
from dataclasses import dataclass
import z3, time

@dataclass
class FormalEncoding:
    formalism: str                  # "smt-lib" | "lp" | "datalog" | "z3-python"
    source: str                     # the formal expression
    variable_map: dict[str, str]    # natural -> formal name
    confidence: float

@dataclass
class FormalResult:
    success: bool
    result: object                  # solver-specific
    certificate: str                # the formal proof/model
    natural_language_explanation: str

class SymbolicNeuralBridgeAgent:
    def __init__(self, encoder_llm, formalism: str = "z3-python",
                 solver_timeout_s: float = 30):
        self.encoder = encoder_llm
        self.formalism = formalism
        self.timeout = solver_timeout_s
    
    def solve(self, natural_problem: str) -> FormalResult:
        # 1. Translate to formal language
        encoding = self._translate(natural_problem)
        if encoding.confidence < 0.7:
            return FormalResult(
                success=False, result=None, certificate="",
                natural_language_explanation=(
                    f"Translation confidence too low ({encoding.confidence:.2f}); "
                    "the problem may not have a closed-form formulation."
                ),
            )
        # 2. Invoke solver
        solver = self._make_solver()
        exec(encoding.source, {"s": solver, "z3": z3})
        solver.set("timeout", int(self.timeout * 1000))
        check = solver.check()
        # 3. Interpret result
        if check == z3.sat:
            model = solver.model()
            return FormalResult(
                success=True,
                result={name: model[var].as_long() if model[var].is_int() else str(model[var])
                        for name, var in encoding.variable_map.items()
                        if isinstance(var, z3.ExprRef)},
                certificate=str(model),
                natural_language_explanation=self._explain(model, encoding),
            )
        elif check == z3.unsat:
            return FormalResult(
                success=True, result=None,
                certificate=str(solver.unsat_core()),
                natural_language_explanation=self._explain_unsat(solver, encoding),
            )
        else:
            return FormalResult(
                success=False, result=None, certificate="",
                natural_language_explanation="Solver did not converge within timeout.",
            )
    
    def _translate(self, problem: str) -> FormalEncoding:
        result = self.encoder.call(
            messages=[
                {"role": "system", "content": TRANSLATION_PROMPT.format(formalism=self.formalism)},
                {"role": "user", "content": problem}
            ],
            schema=TRANSLATION_SCHEMA,
        )
        return FormalEncoding(**result)
```

#### Trade-offs and Alternatives

The pattern only works for problems that have a formal solution at all. Many real problems (interpretation of intent, qualitative judgment, narrative reasoning) don't. And forcing them through a solver produces nonsense. The pattern includes a confidence check on translation specifically to refuse those cases.

For problems on the boundary (like partially formal or partially qualitative) *hybrid* patterns work better. Solve the formal part with the bridge, the qualitative part with normal reasoning, and have a composer integrate. This is how serious tax-planning, contract-analysis, and trade-execution agents are typically built.

#### Production Failure Modes

- 

**Translation drift:** The LLM produces a formally valid expression that solves a slightly different problem than the user asked. Mitigate by translating back to natural language and asking the user to confirm before solving.

- 

**Solver brittleness:** Z3 is robust but specific solver invocations occasionally crash on unusual inputs. Mitigate with sandboxing of the solver subprocess and graceful degradation to a natural-language fallback.

- 

**Certificate-explanation mismatch:** The natural-language explanation doesn't actually reflect the solver's reasoning. Mitigate by deriving the explanation mechanically from the certificate rather than via LLM paraphrase.

#### Case Study

A tax-planning agent at a wealth-management firm converts a client's facts into a mixed-integer program over the relevant sections of the tax code, solves for the optimal filing strategy, and presents the result with the formal certificate (a list of which deductions apply, which schedules are used, which elections produce which dollar effects).

The pattern handles approximately 84% of client situations end-to-end, and the remaining 16% are flagged as outside the formal model and routed to a human planner. Median planner time per client dropped from 4.2 hours to 38 minutes after deployment, with measured strategy-quality (third-party-reviewer-graded) materially higher than the pre-deployment baseline.

**Pairs with:** Constraint-Satisfaction (Agent 11), Provenance Tracker (Agent 55), Counterfactual Reasoner (Agent 9).

#### Reality Check

The clean diagram (LLM translates, solver solves, and LLM explains) works well on textbook problems and stiffens noticeably on real ones. The translation step is brittle: small natural-language ambiguities map to formally distinct encodings, and the model rarely flags the ambiguity. Solvers time out on non-trivial industrial problems and produce incomprehensible certificates that the explain-back step paraphrases unreliably.

The pattern's most defensible use today is in *narrow, well-bounded sub-problems* (tax filing within a known section of the code, scheduling within a known constraint vocabulary, theorem-proving within a known tactic library) where the translation surface is shallow enough to be reliable.

For open-ended "solve this math problem," the pattern is research-grade and ships at much lower reliability than the abstract description implies.

