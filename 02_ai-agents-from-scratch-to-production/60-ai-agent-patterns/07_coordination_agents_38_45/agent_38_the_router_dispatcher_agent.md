# Agent 38 — The Router/Dispatcher Agent

### Agent 38 — The Router/Dispatcher Agent

*Routes incoming tasks to the specialist agent best suited to handle them.*

#### The Problem

When the system contains more than one specialist agent, something has to decide which one gets a given task. Without an explicit router, the routing logic ends up in the user-facing prompt ("if the question is about billing, use the billing agent"), which is fragile, hard to evaluate, and impossible to instrument. With an explicit router, routing is a first-class function: typed input, typed output, measurable accuracy, and replaceable independently of the specialists.

The general problem is **load-balanced specialist dispatch**: matching tasks to specialists in a way that is fast, accurate, observable, and resilient to specialist availability.

#### Why Naïve Approaches Fail

- 

*"Have one big agent handle everything."* Quality is lower than per-specialist for any non-trivial agent collection. Cost is higher because the catch-all prompt is heavy.

- 

*"Use the user's first message to pick the agent and stick with it."* Misses topic shifts mid-session.

- 

*"Let the model pick the agent on every turn."* Adds a model call per turn. The model is overqualified for the job.

#### The Mechanism

A typed task description as the routing input. A registry of specialists with both capability descriptions and historical performance attached. A routing policy that combines task-type matching with load and cost considerations. An "ambiguous task" escape hatch that surfaces to a clarification flow rather than forcing a routing decision under uncertainty.

![Pattern 062 — Agent 38 — The Router/Dispatcher Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5def3d68cad31e737f57_codex-pattern-062-agent-38-the-router-dispatcher-agent-the-mechanism.png)

```python
# coordination/router.py
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
```

#### Trade-offs and Alternatives

The router adds one classification call per turn. For agents with two or three specialists and stable task types, a hand-written routing function (regex on intent keywords, plus a fallback) outperforms a model-based classifier in latency and reliability.

The pattern earns its keep when the specialist registry is larger than five, when task types aren't cleanly enumerable, or when the routing decision benefits from per-specialist accuracy data.

For sessions with sticky topics, route at session start and stick. Re-route only on detected topic shift, not on every message. This halves the routing-call volume.

#### Production Failure Modes

- 

**Classifier drift:** The task-type distribution shifts, the classifier's training set is stale, and routing accuracy degrades. Mitigate by sampling routing decisions for human review and retraining on production traffic.

- 

**Capacity-blind routing:** The best specialist is overloaded, and routing forces queueing instead of falling over to alternatives. Mitigate with explicit `current_load` in the scoring function (the code shows this).

- 

**Specialist-set drift:** A specialist is deprecated, the router still routes to it, and calls fail. Mitigate by versioning the specialist registry and refusing to route to deprecated entries.

#### Case Study

A customer-facing enterprise assistant at a B2B vendor routes between a billing-specialist agent, a product-specialist agent, an integration-specialist agent, and a human-escalation path. The router runs on a small fine-tuned classifier (not a frontier model), with sub-100ms latency per routing decision.

Measured accuracy against a labeled evaluation set: 96%. The 4% routing errors most often involved tasks that genuinely overlapped two specialists, and the alternative-specialist list captured the correct second choice in 91% of misrouting cases.

**Pairs with:** Memory-of-Self (Agent 27), Supervisor-Worker (Agent 45), Auctioneer (Agent 44).
