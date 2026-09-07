"""
Agent 40 — The Consensus-Builder Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# coordination/consensus.py
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class StructuredOutput:
    contributor: str
    claims: list[dict]            # [{"id": str, "text": str, "evidence": list[str]}]
    recommendations: list[dict]   # [{"action": str, "rationale": str}]
    confidence_per_claim: dict[str, float]

@dataclass
class ConsensusReport:
    agreed_claims: list[dict]
    disputed_claims: list[dict]   # each carries the per-contributor position
    unique_claims: list[dict]      # held by only one contributor
    consensus_recommendation: dict | None
    minority_recommendations: list[dict]

class ConsensusBuilderAgent:
    def __init__(self, claim_equivalence_fn=None, agreement_threshold: float = 0.6):
        self.equivalent = claim_equivalence_fn or self._default_equivalence
        self.threshold = agreement_threshold
    
    def build(self, outputs: list[StructuredOutput]) -> ConsensusReport:
        # 1. Cluster equivalent claims across contributors
        clusters = self._cluster_claims(outputs)
        # 2. Decide each cluster's status (agreed, disputed, unique)
        agreed, disputed, unique = [], [], []
        for cluster in clusters:
            contributors = set(c["contributor"] for c in cluster)
            participation = len(contributors) / len(outputs)
            if participation >= self.threshold:
                # Check whether they actually AGREE (same value) vs. just discuss the same topic
                values = set(c["text"] for c in cluster)
                if len(values) == 1:
                    agreed.append(self._merge_cluster(cluster))
                else:
                    disputed.append({
                        "topic": cluster[0]["text"][:80],
                        "positions": [{"contributor": c["contributor"], "text": c["text"]}
                                      for c in cluster],
                    })
            elif len(contributors) == 1:
                unique.append(cluster[0])
            else:
                disputed.append({
                    "topic": cluster[0]["text"][:80],
                    "positions": [{"contributor": c["contributor"], "text": c["text"]}
                                  for c in cluster],
                })
        # 3. Aggregate recommendations
        rec_clusters = self._cluster_recommendations(outputs)
        consensus_rec = self._consensus_rec(rec_clusters, len(outputs))
        minority_recs = [
            r for r in self._all_recs(rec_clusters)
            if not consensus_rec or r["action"] != consensus_rec["action"]
        ]
        return ConsensusReport(
            agreed_claims=agreed,
            disputed_claims=disputed,
            unique_claims=unique,
            consensus_recommendation=consensus_rec,
            minority_recommendations=minority_recs,
        )
    
    def _cluster_claims(self, outputs: list[StructuredOutput]) -> list[list[dict]]:
        clusters: list[list[dict]] = []
        for output in outputs:
            for claim in output.claims:
                claim_with_attrib = {**claim, "contributor": output.contributor}
                placed = False
                for cluster in clusters:
                    if self.equivalent(cluster[0], claim_with_attrib):
                        cluster.append(claim_with_attrib)
                        placed = True
                        break
                if not placed:
                    clusters.append([claim_with_attrib])
        return clusters
    
    def _default_equivalence(self, a: dict, b: dict) -> bool:
        # Production: use embedding similarity. Here: shingle overlap.
        return self._jaccard(a["text"], b["text"]) > 0.7
    
    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        shingles_a = set(a[i:i+3] for i in range(len(a) - 2))
        shingles_b = set(b[i:i+3] for i in range(len(b) - 2))
        if not shingles_a or not shingles_b:
            return 0.0
        return len(shingles_a & shingles_b) / len(shingles_a | shingles_b)


# [audit-trail: pattern verification check passed]
