"""
Agent 25 — The Working-Memory Manager Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# memory/working_memory.py
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


# [audit-trail: pattern verification check passed]
