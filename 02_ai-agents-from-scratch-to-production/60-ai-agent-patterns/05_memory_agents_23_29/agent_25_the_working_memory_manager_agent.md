# Agent 25 — The Working-Memory Manager Agent

### Agent 25 — The Working-Memory Manager Agent

*Actively reshapes the model's context window for the current step.*

#### The Problem

The context window is a scarce resource and growing slowly relative to demand. Without active management, the prompt for each step is whatever the framework concatenates by default (recent turns, the system prompt, retrieved documents) and it grows monotonically. Context bills grow with it. Quality often falls because relevant information is buried among irrelevant.

The general problem is **per-step prompt composition**: deciding, for each call, exactly which context elements to include based on predicted relevance to the upcoming reasoning, not on recency or framework defaults.

#### Why Naïve Approaches Fail

- 

*"Concatenate everything."* Costs scale linearly with session length, and quality often degrades after the prompt exceeds the model's effective attention window.

- 

*"Use only the last K turns."* Drops information that's no longer recent but is still relevant.

- 

*"Retrieve documents by similarity to the current message."* Misses context that's relevant but not lexically similar, and over-retrieves when the current message is ambiguous.

#### The Mechanism

A per-step composition policy that selects context elements by their predicted relevance to the upcoming reasoning. A budget enforced at the composition layer, not discovered at the model boundary. An eviction policy for elements that have sat in context for several steps without being referenced. An instrumentation surface that lets an operator audit what was in context at each step.

![Pattern 049 — Agent 25 — The Working-Memory Manager Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5deee2ab14b936ff3e6d_codex-pattern-049-agent-25-the-working-memory-manager-agent-the-mechanism.png)

```python
# memory/working_memory.py
from dataclasses import dataclass, field
from typing import Protocol
from collections import OrderedDict

@dataclass
class ContextElement:
    id: str
    source: str        # "system" | "history" | "retrieval" | "tool_result" | ...
    content: str
    tokens: int
    priority: float    # 0-1; baseline relevance
    pinned: bool = False   # cannot be evicted
    last_referenced_step: int = -1

class RelevanceScorer(Protocol):
    def score(self, element: ContextElement, current_step_intent: str) -> float: ...

class WorkingMemoryManagerAgent:
    def __init__(self, scorer: RelevanceScorer, *, token_budget: int = 8000):
        self.scorer = scorer
        self.budget = token_budget
        self.elements: OrderedDict[str, ContextElement] = OrderedDict()
        self._step = 0
    
    def add(self, element: ContextElement) -> None:
        self.elements[element.id] = element
    
    def compose(self, intent: str) -> list[dict]:
        """Compose the prompt for the current step."""
        self._step += 1
        # 1. Score every element against the current intent
        scored = []
        for el in self.elements.values():
            if el.pinned:
                scored.append((1.0, el))
            else:
                rel = self.scorer.score(el, intent)
                # Decay elements not referenced recently
                decay = 0.95 ** (self._step - el.last_referenced_step) if el.last_referenced_step >= 0 else 1.0
                scored.append((rel * decay * el.priority, el))
        # 2. Pack greedily into budget
        scored.sort(key=lambda se: se[0], reverse=True)
        selected: list[ContextElement] = []
        used_tokens = 0
        for _, el in scored:
            if used_tokens + el.tokens <= self.budget:
                selected.append(el)
                used_tokens += el.tokens
                el.last_referenced_step = self._step
        # 3. Emit as messages
        return [{"role": self._role_for(el), "content": el.content} for el in selected]
    
    def evict_stale(self, max_age_steps: int = 20) -> int:
        """Remove elements never referenced in the last N steps."""
        to_remove = [
            eid for eid, el in self.elements.items()
            if not el.pinned and (self._step - el.last_referenced_step) > max_age_steps
        ]
        for eid in to_remove:
            del self.elements[eid]
        return len(to_remove)
    
    def audit_snapshot(self) -> dict:
        return {
            "step": self._step,
            "total_elements": len(self.elements),
            "pinned": sum(1 for el in self.elements.values() if el.pinned),
            "token_total": sum(el.tokens for el in self.elements.values()),
        }
    
    def _role_for(self, el: ContextElement) -> str:
        return {"system": "system", "tool_result": "user"}.get(el.source, "user")
```

#### Trade-offs and Alternatives

Working-memory management adds latency before each model call (the scoring pass) and operational complexity (the scorer has to be calibrated). The trade is worth it once a session exceeds a few thousand tokens. But before that, default concatenation is fine.

The scorer is the central component. For agents where the upcoming intent is hard to predict, the scorer's value collapses. For agents with structured intents (a planner producing typed steps), the scorer can be very accurate. Pick the pattern accordingly.

#### Production Failure Modes

- 

**Pinning errors:** Too few pinned elements: critical context (the goal, the system prompt) is evicted. Too many pinned elements: the budget is consumed by pins. Mitigate by versioning the pin set and reviewing it on each major prompt-version update.

- 

**Scorer brittleness:** The scorer learns a few keywords and stops generalizing. Mitigate by retraining (or re-prompting) the scorer on the agent's actual production traffic, not on a static evaluation set.

- 

**Reference-decay false positives:** An element is not "referenced" in the model's reasoning but is still relevant. It gets decayed and evicted. Mitigate by treating element retention as a soft signal alongside scorer relevance, not a hard rule.

#### Case Study

A long-running research agent at a hedge-fund family rebuilds its context window from scratch every five steps from an external memory store, keeping working context under four thousand tokens regardless of session length.

The pattern is responsible for the agent's ability to sustain hour-long research sessions on a single goal at roughly 20% of the inference cost of a comparable non-managed-memory baseline (which crossed the model's effective attention threshold and degraded in quality). Operator audits of the per-step working memory revealed the scorer was correctly pinning the goal, current hypothesis, and active datasets, while rotating through documents and intermediate findings as needed.

**Pairs with:** Vector-Store Curator (Agent 28), Forgetting-Policy (Agent 26), Hierarchical Decomposer (Agent 16).
