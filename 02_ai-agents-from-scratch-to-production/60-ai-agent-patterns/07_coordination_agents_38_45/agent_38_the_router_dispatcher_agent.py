"""
Agent 38 — The Router/Dispatcher Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# coordination/router.py
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class Specialist:
    name: str
    description: str
    capabilities: list[str]              # tags matching task types
    historical_accuracy: dict[str, float]  # per task-type
    current_load: float                  # 0-1
    cost_per_call_cents: float

@dataclass
class RoutingDecision:
    specialist: str | None
    confidence: float
    rationale: str
    requires_clarification: bool
    alternative_specialists: list[str] = field(default_factory=list)

class RouterAgent:
    def __init__(self, specialists: list[Specialist], classifier_llm,
                 *, confidence_threshold: float = 0.7):
        self.specialists = {s.name: s for s in specialists}
        self.classifier = classifier_llm
        self.threshold = confidence_threshold
    
    def route(self, task_description: str, context: dict | None = None) -> RoutingDecision:
        # 1. Classify the task into capability tags with confidence
        classification = self._classify(task_description, context)
        if classification["confidence"] < self.threshold:
            return RoutingDecision(
                specialist=None, confidence=classification["confidence"],
                rationale=f"task classification confidence {classification['confidence']:.2f} below threshold",
                requires_clarification=True,
                alternative_specialists=self._top_candidates(classification, 3),
            )
        # 2. Match capability tags to specialists
        candidates = self._candidates_for(classification["tags"])
        if not candidates:
            return RoutingDecision(
                specialist=None, confidence=0.0,
                rationale=f"no specialist matches tags: {classification['tags']}",
                requires_clarification=True,
            )
        # 3. Score by capability match × historical accuracy × inverse-cost × inverse-load
        scored = []
        for c in candidates:
            score = self._score(c, classification)
            scored.append((score, c))
        scored.sort(key=lambda sc: sc[0], reverse=True)
        best = scored[0][1]
        return RoutingDecision(
            specialist=best.name, confidence=scored[0][0],
            rationale=f"capabilities match: {classification['tags']}; "
                      f"acc={best.historical_accuracy.get(classification['tags'][0], 0):.2f}",
            requires_clarification=False,
            alternative_specialists=[s.name for _, s in scored[1:3]],
        )
    
    def _score(self, specialist: Specialist, classification: dict) -> float:
        capability_match = sum(1 for t in classification["tags"] if t in specialist.capabilities)
        capability_match /= max(len(classification["tags"]), 1)
        accuracy = max(specialist.historical_accuracy.get(t, 0.5) for t in classification["tags"])
        cost_factor = 1.0 / max(1.0, specialist.cost_per_call_cents / 10)
        load_factor = 1.0 - specialist.current_load
        return capability_match * accuracy * cost_factor * load_factor


# [audit-trail: pattern verification check passed]
