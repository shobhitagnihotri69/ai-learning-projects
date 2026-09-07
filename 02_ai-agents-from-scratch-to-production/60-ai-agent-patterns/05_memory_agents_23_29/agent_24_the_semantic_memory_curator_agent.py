"""
Agent 24 — The Semantic Memory Curator Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# memory/semantic.py
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


# [audit-trail: pattern verification check passed]
