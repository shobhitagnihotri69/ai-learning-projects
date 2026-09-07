# Agent 9 — The Counterfactual Reasoner Agent

### Agent 9 — The Counterfactual Reasoner Agent

*Runs "what-if" branches against the current state to surface alternatives.*

#### The Problem

The user has a plan, a draft, a decision, and a code change. The user is about to commit. Without a counterfactual analysis, the commit goes ahead...and is rolled back two days later, when a load-bearing assumption turned out to be wrong.

The general failure mode the pattern addresses is **confirmation-bias collapse**: single-chain reasoning that defends the first plausible position the model produced, leaving no surface for the user to inspect alternatives.

#### Why Naïve Approaches Fail

- 

*"Ask the model to consider alternatives."* The model produces a perfunctory list, then returns to defending its original answer.

- 

*"Generate three options at the start, pick the best."* Treats the alternatives as candidates to choose from, not as branches whose consequences are worth tracing. The "options" are usually variations of the same answer.

- 

*"Run the analysis twice with different phrasings."* Catches stochastic noise but misses systematic bias.

#### The Mechanism

The counterfactual agent identifies the load-bearing variable in the user's situation, generates one or more counterfactual states with the variable flipped, propagates the flip through whatever model of the world the agent has, and produces a comparison output. The agent doesn't advocate, it enumerates.

![Pattern 033 — Agent 9 — The Counterfactual Reasoner Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd22f5c607539ef292a_codex-pattern-033-agent-9-the-counterfactual-reasoner-agent-the-mechanism.png)

```python
# reasoning/counterfactual.py
from dataclasses import dataclass, field

@dataclass
class CounterfactualBranch:
    name: str
    variable_flipped: str
    counterfactual_value: object
    propagation_steps: list[str]
    final_state: dict
    likelihood_estimate: float       # how likely this branch is in reality
    severity_if_realized: str        # "low" | "medium" | "high"

@dataclass
class CounterfactualAnalysis:
    original_state: dict
    load_bearing_variables: list[str]
    branches: list[CounterfactualBranch]
    recommendation: str              # "proceed" | "hedge" | "reconsider"

class CounterfactualReasonerAgent:
    def __init__(self, identifier_llm, propagator_llm, world_model=None):
        self.identifier = identifier_llm
        self.propagator = propagator_llm
        self.world_model = world_model    # optional structured model for propagation
    
    def analyze(self, state: dict, decision: str) -> CounterfactualAnalysis:
        # 1. Identify load-bearing variables
        load_bearing = self._identify_load_bearing(state, decision)
        # 2. Generate counterfactual values for each
        branches = []
        for var in load_bearing:
            for cf_value in self._counterfactual_values(state, var):
                branch = self._propagate(state, var, cf_value, decision)
                branches.append(branch)
        # 3. Recommend based on severity * likelihood across branches
        return CounterfactualAnalysis(
            original_state=state,
            load_bearing_variables=load_bearing,
            branches=branches,
            recommendation=self._recommend(branches),
        )
    
    def _identify_load_bearing(self, state: dict, decision: str) -> list[str]:
        """Which variables, if flipped, would change the decision?"""
        result = self.identifier.call(
            messages=[
                {"role": "system", "content": LOAD_BEARING_PROMPT},
                {"role": "user", "content": f"State: {state}\nDecision: {decision}"}
            ],
            schema={"type": "object", "properties": {
                "load_bearing_variables": {"type": "array", "items": {"type": "string"}}
            }}
        )
        return result["load_bearing_variables"]
    
    def _propagate(self, state, var, cf_value, decision) -> CounterfactualBranch:
        cf_state = {**state, var: cf_value}
        if self.world_model:
            return self.world_model.propagate(state, cf_state, decision)
        # LLM-based propagation as fallback
        result = self.propagator.call(
            messages=[
                {"role": "system", "content": PROPAGATION_PROMPT},
                {"role": "user", "content": format_propagation_input(state, cf_state, decision)}
            ],
            schema=PROPAGATION_SCHEMA,
        )
        return CounterfactualBranch(**result)
```

#### Trade-offs and Alternatives

Counterfactual reasoning is expensive (typically three to ten times the cost of a single forward pass) because each branch requires propagation through whatever world model is available.

The cost is justified for decisions where reversibility is low and consequence is high (investments, hiring, regulatory positions, irreversible production changes). For decisions that are easily undone, the pattern is overhead.

A lighter-weight alternative is *adversarial prompting*: running the same reasoning with a "now argue the opposite" instruction. This catches the most blatant cases. The full counterfactual pattern is what you need when the alternatives matter enough to be propagated, not just stated.

#### Production Failure Modes

- 

**Insufficient counterfactual diversity:** The branches are minor variations of the original. Mitigate by requiring branches to flip categorically different variables, and by sampling counterfactual values from a deliberately wide distribution.

- 

**Propagator over-confidence:** The propagator declares a counterfactual "would have no effect" because it can't easily trace second-order consequences. Mitigate by requiring the propagator to enumerate at least three downstream effects per branch, with explicit "I can't determine" allowed.

- 

**Likelihood-estimate fabrication:** The likelihood estimates per branch are not calibrated. The recommendation reflects the model's vibes more than any evidence. Mitigate by deriving likelihoods from a separately-calibrated belief model (Agent 14) rather than asking the propagator to estimate them.

#### Case Study

An investment-committee agent at a long-short equity manager runs every recommended position through three counterfactuals: rate up two hundred basis points, sector down ten percent, and a named competitor doubles share. They attach the survivability of the position under each to the recommendation memo. Positions whose recommendation reverses under any of the three counterfactuals get a "hedge" flag and are sized down by half by default.

The pattern was credited with a 1.8 percentage point improvement in the fund's risk-adjusted return over the eighteen months after introduction, primarily by sizing down positions that would have lost catastrophically when the relevant counterfactual was realized.

**Pairs with:** Constraint-Satisfaction (Agent 11), Probabilistic Belief Updater (Agent 14), Causal Graph Builder (Agent 12).
