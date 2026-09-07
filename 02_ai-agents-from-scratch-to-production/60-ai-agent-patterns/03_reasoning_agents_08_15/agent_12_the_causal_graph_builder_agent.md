# Agent 12 — The Causal Graph Builder Agent

### Agent 12 — The Causal Graph Builder Agent

*Induces a causal structure from observational data and uses it for intervention reasoning.*

#### The Problem

Most analytics agents stop at correlation. They tell you that two variables move together. They can't answer the question the user actually has: *what happens if I change one of them?*

That question requires a causal model: an explicit graph of which variables cause which. But constructing one from observational data is a real technical problem the agent has to solve, not a property the data inherently exposes.

The general problem is **causal-versus-associational confusion**: an agent's outputs that read as causal claims when they are only associational. The asymmetry matters because users *act* on causal claims and *understand* associational ones. Conflating them produces actions that don't have the expected effect.

#### Why Naïve Approaches Fail

- 

*"Report correlations as if they were causes."* The advertising channel that "drives" conversions because the data shows correlation. Later experiments show no causal effect, and the marketing budget is wasted.

- 

*"Run a regression and call the coefficients causal."* They aren't, except under specific identification assumptions the regression alone doesn't verify.

- 

*"Ask the model to figure out what causes what."* The model has reasonable priors from training, no formal causal-discovery method, and tends to confidently produce graphs that fit the surface story rather than the data.

#### The Mechanism

The causal graph builder uses observational data, prior knowledge elicited from domain experts (or the LLM as a stand-in), and formal causal-discovery methods (PC, FCI, or score-based methods) to construct an explicit causal graph. The graph carries explicit edge strengths and explicit "unknown" markers for relationships the data is insufficient to resolve. The graph is then used for intervention reasoning, where a downstream policy can ask "if I set X to value Y, what is the expected effect on Z?"

![Pattern 036 — Agent 12 — The Causal Graph Builder Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd38cc36c96237ad491_codex-pattern-036-agent-12-the-causal-graph-builder-agent-the-mechanism.png)

```python
# reasoning/causal_graph.py
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx

class EdgeType(Enum):
    DIRECTED = "directed"        # X -> Y
    UNDIRECTED = "undirected"    # X -- Y (cannot orient from data)
    BIDIRECTED = "bidirected"    # X <-> Y (latent confounder)

@dataclass
class CausalEdge:
    source: str
    target: str
    type: EdgeType
    strength: float              # standardized effect size where applicable
    evidence: str                # "data" | "prior" | "data+prior"
    confidence: float

@dataclass
class CausalGraph:
    nodes: list[str]
    edges: list[CausalEdge]
    
    def parents(self, node: str) -> list[str]:
        return [e.source for e in self.edges
                if e.target == node and e.type == EdgeType.DIRECTED]
    
    def is_identifiable(self, treatment: str, outcome: str) -> bool:
        """Does the back-door criterion hold?"""
        ...

class CausalGraphBuilderAgent:
    def __init__(self, discovery_method="pc", prior_elicitor=None):
        self.method = discovery_method
        self.prior_elicitor = prior_elicitor   # LLM or human-curated knowledge source
    
    def build(self, data, variables: list[str]) -> CausalGraph:
        # 1. Elicit priors (which edges are domain-known)
        priors = self.prior_elicitor.elicit(variables) if self.prior_elicitor else []
        # 2. Run causal discovery on the data, respecting priors
        edges = self._discover(data, variables, priors)
        # 3. Score-based refinement
        edges = self._refine(edges, data)
        # 4. Annotate identifiability
        return CausalGraph(nodes=variables, edges=edges)
    
    def estimate_effect(self, graph: CausalGraph, treatment: str,
                        outcome: str, data) -> dict:
        if not graph.is_identifiable(treatment, outcome):
            return {"identifiable": False, "reason": "back-door criterion fails"}
        # Use the do-calculus identifiability result to construct an estimator
        adjustment_set = self._find_adjustment_set(graph, treatment, outcome)
        estimate = self._adjusted_estimate(data, treatment, outcome, adjustment_set)
        return {
            "identifiable": True,
            "estimate": estimate.value,
            "ci_95": estimate.ci_95,
            "adjustment_set": adjustment_set,
        }
```

#### Trade-offs and Alternatives

Causal discovery from observational data is a hard problem with well-known limits. The graph you get is always provisional, and the patterns in this chapter alone don't guarantee causal claims survive randomized experimentation. For high-stakes decisions, the causal graph is the substrate for *designing experiments*, not the final answer.

A simpler alternative is *expert-elicited graphs*: skip the discovery and let domain experts draw the graph by hand. This is appropriate when the domain is well-understood and the experts are credible. The data-driven discovery is what you need when the domain is new, when experts disagree, or when the variables are numerous enough that hand-drawing is impractical.

#### Production Failure Modes

- 

**Hidden confounders:** A common cause of two variables is unmeasured. The discovery method confidently orients an edge between them that doesn't reflect direct causation. Mitigate by using methods that explicitly model latent confounders (FCI rather than PC) and by surfacing bidirected edges to the user.

- 

**Cycle artifacts:** The data is too noisy for the discovery method to consistently orient edges. Cycles appear in the output. Mitigate by reporting the partial DAG and the undirected segments separately.

- 

**Prior contamination:** The elicited priors are wrong (the expert believes A causes B when the data clearly shows the opposite). Mitigate by checking each prior against data conditional-independence tests before incorporation and surface conflicts explicitly.

#### Case Study

A marketing-attribution agent at a direct-to-consumer brand replaced the standard last-touch attribution model with a causal-graph attribution model. The graph was built from twelve months of channel-spend and conversion data, with priors elicited from the marketing team about channels they believed couldn't directly cause conversions (only assist).

The new attribution shifted approximately 23% of the budget away from the channels last-touch had credited toward those the causal graph identified as actual drivers. Subsequent randomized holdout tests confirmed roughly 80% of the shift produced the predicted incremental lift.

**Pairs with:** Counterfactual Reasoner (Agent 9), Probabilistic Belief Updater (Agent 14), Constraint-Satisfaction (Agent 11).

#### Reality Check

This pattern is the most over-promised in the book and one of the hardest to ship well. Causal discovery from observational data is a research-grade problem: hidden confounders break identifiability, conditional-independence tests have low power on small samples, and even well-validated edges generalize poorly across distribution shifts.

A useful production deployment usually combines (a) expert-elicited graph priors that constrain the search, (b) randomized-experiment data on the most consequential edges, and (c) explicit refusal on queries that aren't identifiable from the current graph.

Teams that attempt this pattern on observational data alone, without the experiment-validation loop, usually produce graphs that look reasonable and don't survive the first holdout test.

Treat the pattern as a *design discipline for thinking causally about your data*, not as an autonomous capability the agent can do well unaided.



