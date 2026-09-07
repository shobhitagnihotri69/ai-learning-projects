# Agent 30 — The Tool Selector Agent

### Agent 30 — The Tool Selector Agent

*Picks the right tool from a large registry without overwhelming the model with the full list.*

#### The Problem

A toolset of ten tools fits in a prompt. A toolset of two hundred does not. As the agent's toolset grows past a few dozen entries, two things happen: the prompt gets expensive (every tool description is in every call), and the policy gets worse (the model picks the closest-matching tool even when the right tool is several entries down the list). Without a selection layer, agent toolsets can't grow past a few dozen entries without quality collapse.

The general problem is **scalable tool registries**: making large tool collections usable by an agent without putting all of them in the prompt at once.

#### Why Naïve Approaches Fail

- 

*"Just put them all in the prompt."* Cost scales linearly with toolset size. Quality degrades as the relevant tools get buried.

- 

*"Have the model pick the tool from a categorical menu first."* Adds a turn. The model can't always categorize the user intent into the right bucket.

- 

*"Hard-code which tools are visible per task type."* Works until task types proliferate. Fragile to toolset additions.

#### The Mechanism

A richly-described tool registry with structured fields beyond a one-line description. An embedding-based first-pass retrieval against a representation of the current task. An exact-match second pass for tools known to be required by the task type. And a fall-through behavior that surfaces "I don't have a tool for this" rather than forcing the policy to fabricate one.

![Pattern 054 — Agent 30 — The Tool Selector Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df518437f571ad4fcb0_codex-pattern-054-agent-30-the-tool-selector-agent-the-mechanism.png)

```python
# tools/selector.py
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
```

#### Trade-offs and Alternatives

The selector adds latency before every step (the retrieval pass) and complexity (the registry has to be maintained with rich metadata). For agents with fewer than fifteen tools, the pattern is overhead.

A useful simplification for medium toolsets is *category-based static slicing*: maintain a curated tool set per task type, switch slices at the start of each task, and skip the per-step retrieval. This works when task types are stable and few.

#### Production Failure Modes

- 

**Retrieval miss:** The right tool isn't in the top-K because its description doesn't lexically or semantically match the task. Mitigate by enriching the description (the `long_description` and `keywords` fields exist for this) and by sampling production traces to identify recurring misses.

- 

**Force-inclusion overuse:** Operators add too many `required_categories`. The candidate set is dominated by forced tools and the retrieval signal is lost. Mitigate by capping forced inclusions per call.

- 

**Stale embeddings:** The registry grows, the embedder is upgraded, and the pre-computed embeddings are stale. Mitigate by versioning embeddings alongside the registry and recomputing on embedder change (same lifecycle as the Vector-Store Curator, Agent 28).

#### Case Study

A B2B operations agent at a logistics-platform vendor maintains a four-hundred-tool registry of internal APIs and SaaS connectors. The selector reduces that to a 6-tool prompt per step.

Quality measured against full-registry baselines (over a labeled evaluation set the operations team curates monthly) is within 2 percentage points of the impossible-in-production "show all tools" baseline, at roughly one-twentieth the per-step prompt cost.

**Pairs with:** Side-Effect Auditor (Agent 37), Memory-of-Self (Agent 27), API-Schema Adapter (Agent 31).
