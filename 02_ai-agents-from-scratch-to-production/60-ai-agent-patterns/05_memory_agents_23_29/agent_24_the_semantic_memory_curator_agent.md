# Agent 24 — The Semantic Memory Curator Agent

### Agent 24 — The Semantic Memory Curator Agent

*Distills repeated patterns from episodes into long-term, generalized facts.*

#### The Problem

Episodic memory stores instances. Semantic memory stores patterns. When an agent has seen "Bob owns the deploy process" twenty times across different conversations, an episodic store contains twenty events. A semantic store contains the generalized fact "Bob owns the deploy process." Provenance points to the source episodes, queryable as a stable fact rather than a probabilistic inference from twenty events.

The general problem is **promoting recurring patterns into stable knowledge**: turning the episodic into the semantic, with explicit provenance, contradiction handling, and the ability to invalidate when supporting evidence is later refuted.

#### Why Naïve Approaches Fail

- 

*"Run a summarizer over the episode store periodically."* Produces summaries that are unstructured, lose provenance, and conflict with each other across runs.

- 

*"Ask the agent to remember things on demand."* Brittle, depends on the agent's working memory, doesn't accumulate.

- 

*"Fine-tune the model on the episodes."* Slow, expensive, and conflates training-data updates with operational state changes.

#### The Mechanism

A promotion policy that decides when an episodic pattern has accumulated enough support to become a semantic fact. An explicit representation of the fact with supporting evidence. A contradiction-detection step that surfaces conflicts when a new candidate fact disagrees with an existing one. A forgetting path when supporting evidence is later invalidated.

![Pattern 048 — Agent 24 — The Semantic Memory Curator Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5deee2ab14b936ff3e4d_codex-pattern-048-agent-24-the-semantic-memory-curator-agent-the-mechanism.png)

```python
# memory/semantic.py
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import hashlib

@dataclass
class SemanticFact:
    id: str
    subject: str            # the entity the fact is about
    predicate: str          # the relation
    object: str             # the value
    evidence_episode_ids: list[str]
    first_observed: datetime
    last_confirmed: datetime
    confidence: float
    contradicting_facts: list[str] = field(default_factory=list)
    status: str = "active"   # "active" | "deprecated" | "contested"

class SemanticMemoryCuratorAgent:
    def __init__(self, episodic_store, *, promotion_threshold: int = 3):
        self.episodic = episodic_store
        self.promotion_threshold = promotion_threshold
        self.facts: dict[str, SemanticFact] = {}
        self._candidate_counts: dict[tuple, list[str]] = defaultdict(list)
    
    def ingest_episode(self, episode) -> list[SemanticFact]:
        """Extract candidate (subject, predicate, object) triples from an episode."""
        triples = self._extract_triples(episode)
        newly_promoted = []
        for s, p, o in triples:
            key = (s, p, o)
            self._candidate_counts[key].append(episode.id)
            if len(self._candidate_counts[key]) >= self.promotion_threshold:
                fact = self._promote(s, p, o, self._candidate_counts[key])
                newly_promoted.append(fact)
        return newly_promoted
    
    def _promote(self, subject, predicate, object_, evidence_ids) -> SemanticFact:
        fact_id = self._make_id(subject, predicate, object_)
        if fact_id in self.facts:
            existing = self.facts[fact_id]
            existing.evidence_episode_ids.extend(
                eid for eid in evidence_ids if eid not in existing.evidence_episode_ids)
            existing.last_confirmed = datetime.utcnow()
            existing.confidence = min(1.0, existing.confidence + 0.05)
            return existing
        # Check for contradictions
        contradictions = self._find_contradictions(subject, predicate, object_)
        fact = SemanticFact(
            id=fact_id, subject=subject, predicate=predicate, object=object_,
            evidence_episode_ids=list(evidence_ids),
            first_observed=datetime.utcnow(), last_confirmed=datetime.utcnow(),
            confidence=0.6,
            contradicting_facts=[c.id for c in contradictions],
            status="contested" if contradictions else "active",
        )
        self.facts[fact_id] = fact
        for c in contradictions:
            if c.id not in fact.contradicting_facts:
                fact.contradicting_facts.append(c.id)
            if fact.id not in c.contradicting_facts:
                c.contradicting_facts.append(fact.id)
            c.status = "contested"
        return fact
    
    def _find_contradictions(self, subject, predicate, object_) -> list[SemanticFact]:
        # A new fact contradicts an existing one if subject and predicate match
        # but object differs (for predicates that are functional / single-valued).
        if not self._is_functional(predicate):
            return []
        return [f for f in self.facts.values()
                if f.subject == subject and f.predicate == predicate
                and f.object != object_ and f.status == "active"]
    
    def invalidate(self, episode_id: str) -> list[SemanticFact]:
        """If an episode is later determined wrong, recompute affected facts."""
        affected = []
        for fact in self.facts.values():
            if episode_id in fact.evidence_episode_ids:
                fact.evidence_episode_ids.remove(episode_id)
                if len(fact.evidence_episode_ids) < self.promotion_threshold:
                    fact.status = "deprecated"
                    affected.append(fact)
        return affected
    
    def query(self, subject: str | None = None, predicate: str | None = None,
              status: str = "active") -> list[SemanticFact]:
        out = []
        for f in self.facts.values():
            if f.status != status:
                continue
            if subject and f.subject != subject:
                continue
            if predicate and f.predicate != predicate:
                continue
            out.append(f)
        return out
    
    def _is_functional(self, predicate: str) -> bool:
        # Predicates that should only have one value per subject (owns, reports_to, etc.)
        return predicate in {"owns", "reports_to", "is_a", "located_in"}
```

#### Trade-offs and Alternatives

Semantic promotion adds latency on episode ingestion and complexity around contradiction handling. For agents where the "facts" change frequently (a live operations agent observing real-time state), the semantic store creates more problems than it solves. So episodic-only is the right choice.

The pattern earns its keep when facts are mostly stable, when they accumulate over long horizons, and when other agents need to query stable knowledge.

A lighter alternative is *manually-curated semantic memory*: an operator-edited knowledge base that the agent reads from but doesn't write to. This avoids the contradiction-handling complexity at the cost of the operator's time.

#### Production Failure Modes

- 

**Premature promotion:** A predicate is promoted after three observations but the observations are all from the same week and reflect a transient state. Mitigate by requiring temporal spread in the promotion threshold (three observations across three distinct days, not three observations in three minutes).

- 

**Stale active facts:** A fact was promoted, the supporting episodes are pruned by the episodic forgetting policy, and the fact remains active without underlying evidence. Mitigate by reverifying long-active facts against recent episodes on a schedule.

- 

**Predicate explosion:** The triple extractor generates hundreds of distinct predicates per agent (subtle phrasing differences). Mitigate by canonicalizing predicates against a controlled vocabulary on extraction.

#### Case Study

A sales-coaching agent at a SaaS vendor distills, over a quarter of recorded calls per rep, a stable model of each rep's strengths and gaps. Triples include `(rep_X, strong_at, discovery_questioning)`, `(rep_X, weak_at, pricing_objection_handling)`, with promotion threshold at five distinct calls.

Coaches report using the resulting semantic profile as their starting point for one-on-ones. The agent's profile is accepted as accurate (no override) approximately 78% of the time.

**Pairs with:** Episodic Buffer (Agent 23), Provenance Tracker (Agent 55), Persistent Identity (Agent 29).
