# Agent 40 — The Consensus-Builder Agent

### Agent 40 — The Consensus-Builder Agent

*Aggregates outputs from a heterogeneous swarm of agents into a single answer.*

#### The Problem

Where the voter (Agent 15) samples one policy multiple times, the consensus-builder runs multiple distinct policies once and aggregates their outputs. The diversity of models — frontier, smaller, fine-tuned, specialist — means the aggregation has to handle disagreement that is structural, not just stochastic. Naïve concatenation produces an unreadable mess, while naïve averaging loses load-bearing detail.

The general problem is **structural-disagreement aggregation**: combining outputs from policies that legitimately disagree, in a way that preserves the disagreement where it's real and resolves it where it's illusory.

#### Why Naïve Approaches Fail

- 

*"Concatenate the answers."* Doesn't address disagreement, presents all of them to the user.

- 

*"Pick the most-confident answer."* Confidence is not calibrated across heterogeneous models.

- 

*"Have a model summarize the answers."* Loses structure, may fabricate consensus that isn't there.

#### The Mechanism

A parser that maps each candidate output to a structured representation. An agreement-and-disagreement decomposition over the structure. An aggregation policy that handles partial agreement (keep agreed parts verbatim, flag disagreed parts with each candidate's position). A surfacing layer that distinguishes consensus from imposed conclusion.

![Pattern 064 — Agent 40 — The Consensus-Builder Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5def8cc36c96237ada62_codex-pattern-064-agent-40-the-consensus-builder-agent-the-mechanism.png)

```python
# coordination/consensus.py
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
```

#### Trade-offs and Alternatives

The consensus builder requires structured outputs from each contributor. For systems where contributors produce free text, an upstream extraction step is needed (this is itself work).

The pattern is heavy. Lighter alternatives include simple voting on a discrete answer space or hierarchical hand-off (one agent's output is the next agent's input, with no parallel disagreement to resolve).

The pattern shines when disagreement is *informative*, that is when knowing that the three policies disagree is itself something the user needs to know. In contexts where the user just wants an answer, the disagreement information is noise.

#### Production Failure Modes

- 

**False consensus:** Different policies use different phrasings for the same claim. The equivalence function clusters too aggressively, declaring agreement where there is partial disagreement. Mitigate by tuning the threshold and by sampling reported consensus for human review.

- 

**Cluster fragmentation:** Different phrasings of the same claim end up in different clusters. The report shows disagreement where there's consensus. Mitigate by improving the equivalence function (embedding-based, not shingle-based).

- 

**Recommendation suppression:** A minority recommendation that's actually correct gets buried below the consensus. Mitigate by always surfacing minority recommendations explicitly, not just as a footnote.

#### Case Study

A medical-decision-support tool at a hospital system runs the same clinical question against three independently maintained policy bases (an internal evidence-based guideline corpus, a literature-retrieval-augmented frontier model, and a specialist-tuned smaller model). The consensus builder presents the clinician with explicit agreed conclusions, disputed points with each policy's position, and any minority recommendations with their rationale.

Adoption studies showed clinicians valued the *disagreement* information at least as much as the consensus. The tool's primary value was surfacing cases where the policy bases disagreed, which historically had been invisible to the clinician.

**Pairs with:** Debate Moderator (Agent 39), Provenance Tracker (Agent 55), Pipeline Orchestrator (Agent 41).

