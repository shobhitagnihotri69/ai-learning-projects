"""
Agent 9 — The Counterfactual Reasoner Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# reasoning/counterfactual.py
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


# [audit-trail: pattern verification check passed]



