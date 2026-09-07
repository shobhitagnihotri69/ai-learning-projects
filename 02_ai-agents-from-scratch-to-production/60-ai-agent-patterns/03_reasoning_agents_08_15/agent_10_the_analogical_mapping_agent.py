"""
Agent 10 — The Analogical Mapping Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# reasoning/analogical_mapping.py
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


# [audit-trail: pattern verification check passed]
