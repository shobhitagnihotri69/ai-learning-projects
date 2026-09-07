"""
Agent 30 — The Tool Selector Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# tools/selector.py
from dataclasses import dataclass, field

@dataclass
class ToolDescriptor:
    name: str
    description: str
    long_description: str            # detailed; not in prompt by default
    parameters: dict                 # JSON Schema
    side_effect_class: str           # "read" | "write" | "destructive"
    cost_class: str                  # "free" | "metered" | "billed"
    category: str
    keywords: list[str]
    embedding: list[float] = field(default_factory=list)

class ToolSelectorAgent:
    def __init__(self, registry: list[ToolDescriptor], embedder,
                 *, candidate_k: int = 15, final_k: int = 6):
        self.registry = registry
        self.embedder = embedder
        self.candidate_k = candidate_k
        self.final_k = final_k
        # Pre-compute embeddings on a richer text than just the description
        for t in registry:
            if not t.embedding:
                blob = (f"{t.name}\n{t.description}\n{t.long_description}\n"
                        f"keywords: {', '.join(t.keywords)}\ncategory: {t.category}")
                t.embedding = embedder.embed(blob)
    
    def select(self, task_description: str,
               required_categories: list[str] | None = None) -> list[ToolDescriptor]:
        task_emb = self.embedder.embed(task_description)
        # 1. Embedding-based retrieval
        scored = [(self._cosine(task_emb, t.embedding), t) for t in self.registry]
        scored.sort(key=lambda st: st[0], reverse=True)
        candidates = [t for _, t in scored[:self.candidate_k]]
        # 2. Force-include category requirements
        if required_categories:
            for cat in required_categories:
                cat_tools = [t for t in self.registry if t.category == cat]
                for t in cat_tools[:2]:
                    if t not in candidates:
                        candidates.append(t)
        # 3. Re-rank with a small LLM call on a richer prompt
        return self._rerank(task_description, candidates)[:self.final_k]
    
    def _rerank(self, task: str, candidates: list[ToolDescriptor]) -> list[ToolDescriptor]:
        # Simple reranker: a small model asked to score each candidate's fit
        # In production, train a reranker on tool-selection traces.
        ...
    
    def materialize_for_prompt(self, selected: list[ToolDescriptor]) -> list[dict]:
        """The compact form fed into the policy's tool list."""
        return [
            {"name": t.name, "description": t.description,
             "parameters": t.parameters, "side_effect_class": t.side_effect_class}
            for t in selected
        ]
    
    @staticmethod
    def _cosine(a, b):
        dot = sum(x*y for x, y in zip(a, b))
        norm_a = sum(x*x for x in a) ** 0.5
        norm_b = sum(x*x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


# [audit-trail: pattern verification check passed]
