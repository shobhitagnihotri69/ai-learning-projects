# Agent 10 — The Analogical Mapping Agent

### Agent 10 — The Analogical Mapping Agent

*Finds structural parallels between a current problem and previously solved ones.*

#### The Problem

Engineers solve problems by reference. The third time you write a rate-limiter you don't derive it, you remember which of the previous two designs to copy. An agent without analogical retrieval re-derives every problem from scratch, which is wasteful, slow, and produces worse solutions than the team's existing repertoire would.

The general problem is **same-structure-different-surface retrieval**: finding the prior case that maps to the current case at the level of mechanism, even when the surface vocabulary is different. Embedding-based retrieval (the default in most RAG systems) gives you surface similarity. Analogical mapping gives you structural similarity.

#### Why Naïve Approaches Fail

- 

*"Embed the problem statement and retrieve nearest neighbors."* Finds cases with similar words, but misses cases with the same structure but different vocabulary. A "thundering-herd retry storm against a downstream payments API" will not embedding-retrieve "request stampede against the billing service" reliably.

- 

*"Maintain a hand-curated playbook."* Works until the playbook gets stale or covers only a fraction of the problem space.

- 

*"Ask the model to recall a similar case."* The model's recall is biased toward whatever was in its training corpus, not toward the team's actual prior cases.

#### The Mechanism

The analogical mapping agent stores prior cases as structured graphs (nodes = entities and relationships, not text), encodes the current case the same way, retrieves library entries by graph similarity rather than embedding similarity, aligns variables between the current and retrieved case, and translates the retrieved solution to the current case's variables.

![Pattern 034 — Agent 10 — The Analogical Mapping Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd32f5c607539ef294a_codex-pattern-034-agent-10-the-analogical-mapping-agent-the-mechanism.png)

```python
# reasoning/analogical_mapping.py
from dataclasses import dataclass
import networkx as nx

@dataclass
class CaseGraph:
    case_id: str
    nodes: list[dict]       # [{id, type, attributes}, ...]
    edges: list[dict]       # [{from, to, relation, attributes}, ...]
    solution: dict          # the resolved solution
    metadata: dict          # date, author, success_rating

@dataclass
class StructuralMatch:
    case: CaseGraph
    structural_similarity: float
    variable_alignment: dict[str, str]   # current_variable -> retrieved_variable
    confidence: float

class AnalogicalMappingAgent:
    def __init__(self, case_library: list[CaseGraph], encoder_llm):
        self.library = case_library
        self.encoder = encoder_llm
        self._graphs = {c.case_id: self._to_nx(c) for c in case_library}
    
    def find_analogues(self, problem_description: str, k: int = 3) -> list[StructuralMatch]:
        # 1. Encode the current problem as a graph
        current = self._encode_problem(problem_description)
        current_g = self._to_nx(current)
        # 2. Score each library entry by structural similarity
        scored = []
        for case_id, g in self._graphs.items():
            sim, alignment = self._structural_similarity(current_g, g)
            scored.append((sim, case_id, alignment))
        scored.sort(key=lambda t: t[0], reverse=True)
        # 3. Return top-k with variable alignment
        return [
            StructuralMatch(
                case=next(c for c in self.library if c.case_id == case_id),
                structural_similarity=sim,
                variable_alignment=alignment,
                confidence=self._confidence(sim, alignment),
            )
            for sim, case_id, alignment in scored[:k]
        ]
    
    def _structural_similarity(self, g1: nx.Graph, g2: nx.Graph) -> tuple[float, dict]:
        """Graph edit distance + role-typed node matching."""
        # In production use a proper graph kernel (Weisfeiler-Lehman, NetSimile,
        # or a learned graph embedding). Simplified here.
        node_match = lambda a, b: a.get("type") == b.get("type")
        edge_match = lambda a, b: a.get("relation") == b.get("relation")
        try:
            gm = nx.algorithms.isomorphism.GraphMatcher(
                g1, g2, node_match=node_match, edge_match=edge_match)
            best_mapping = max(gm.subgraph_isomorphisms_iter(),
                              key=lambda m: len(m), default={})
            sim = len(best_mapping) / max(g1.number_of_nodes(), 1)
            return sim, best_mapping
        except Exception:
            return 0.0, {}
    
    def adapt_solution(self, match: StructuralMatch,
                       current_problem: str) -> dict:
        """Translate the retrieved solution to the current variables."""
        retrieved_solution = match.case.solution
        # Substitute aligned variables
        adapted = {}
        for k, v in retrieved_solution.items():
            adapted[k] = self._substitute(v, match.variable_alignment)
        return adapted
```

#### Trade-offs and Alternatives

Analogical mapping requires a case library encoded as structured graphs. That encoding is itself work: it has to be done at case-capture time or retroactively, and it has to be maintained. For agents whose problem domain is narrow and stable enough that a small playbook suffices, the encoding overhead is not justified.

A useful intermediate is *hybrid retrieval*: do embedding-based retrieval first, then re-rank by structural similarity on the top-k. This avoids encoding the entire library and gives most of the benefit at a fraction of the implementation cost.

#### Production Failure Modes

- 

**Library staleness:** Cases age out of relevance, and the library returns matches that worked five years ago but don't fit current systems. Mitigate by attaching a recency-weighted score and decaying old cases unless they have been refreshed.

- 

**Alignment errors:** The variable alignment between the current and retrieved case is wrong, and the adapted solution maps the wrong variable to the wrong slot. Mitigate by requiring the alignment to be validated by the user before the adapted solution is used.

- 

**Over-confident structural matches:** The graph similarity is high but the cases are actually unlike, so the structure was incidental. Mitigate by adding semantic checks at the node level (do the node *types* in the match really mean the same thing in the two cases?) before adapting.

#### Case Study

A SOC analyst co-pilot at a managed-security provider maintains a library of approximately 26,000 prior incident graphs encoded across the customer base (anonymized cross-customer, richly encoded per-customer). Given a new alert pattern, the analogical mapper surfaces the three structurally closest historical incidents and proposes an adapted response.

Median triage time on first-touch incidents dropped from twenty-four minutes to seven, and the rate at which analysts reused (rather than overrode) the adapted response was 71%.

**Pairs with:** Skill-Library Builder (Agent 48), Few-Shot Prompt Tuner (Agent 50), Semantic Memory Curator (Agent 24).

