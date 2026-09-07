# Agent 28 — The Vector-Store Curator Agent

### Agent 28 — The Vector-Store Curator Agent

*Manages embedding ingestion, sharding, and retrieval quality over the lifetime of a knowledge base.*

#### The problem

A vector store at week one and a vector store at month twelve are different problems. Drift in the embedding model, growth in the corpus, distribution shift in the queries, and accumulation of stale or duplicate documents all degrade retrieval quality silently.

The standard "ingest documents, query at runtime" framing treats the store as inert. In production, an unmaintained store gets quietly worse every week.

The general problem is **vector-store-as-system**: treating the retrieval substrate as a living system with its own lifecycle (ingestion, re-embedding on model upgrade, sharding for access locality, deduplication, eviction, benchmarking) rather than as a one-time setup.

#### Why Naïve Approaches Fail

- 

*"Ingest once at launch."* Quality decays as the corpus stales.

- 

*"Re-ingest periodically."* Useful but indiscriminate. It doesn't catch the subtler issues (embedding drift, sharding mismatches).

- 

*"Trust the vector-store vendor."* They handle the substrate, they don't curate your content.

#### The Mechanism

A query-set anchored quality benchmark run on cadence. A re-embedding policy keyed to embedding-model versions rather than to a fixed schedule. A deduplication pass that catches semantic duplicates, not only exact ones. A sharding strategy keyed to access patterns. An alarm path when benchmark quality regresses.

![Pattern 052 — Agent 28 — The Vector-Store Curator Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df4bacc91e216d9276a_codex-pattern-052-agent-28-the-vector-store-curator-agent-the-mechanism.png)

```python
# memory/vector_curator.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class BenchmarkQuery:
    query_id: str
    text: str
    expected_doc_ids: list[str]   # the doc(s) the right answer should retrieve

@dataclass
class CurationRun:
    run_at: datetime
    benchmark_pass_rate: float
    duplicates_merged: int
    docs_reembedded: int
    docs_evicted: int

class VectorStoreCuratorAgent:
    def __init__(self, store, embedder, benchmark: list[BenchmarkQuery],
                 *, quality_floor: float = 0.85):
        self.store = store
        self.embedder = embedder
        self.benchmark = benchmark
        self.quality_floor = quality_floor
        self.history: list[CurationRun] = []
    
    def run_curation(self) -> CurationRun:
        run = CurationRun(
            run_at=datetime.utcnow(), benchmark_pass_rate=0.0,
            duplicates_merged=0, docs_reembedded=0, docs_evicted=0,
        )
        # 1. Re-embed on embedder version change
        if self.embedder.version != self.store.metadata.get("embedder_version"):
            run.docs_reembedded = self._reembed_all()
            self.store.metadata["embedder_version"] = self.embedder.version
        # 2. Semantic deduplication
        run.duplicates_merged = self._dedupe()
        # 3. Eviction by recency + access score
        run.docs_evicted = self._evict_low_value()
        # 4. Benchmark
        run.benchmark_pass_rate = self._benchmark()
        # 5. Alarm if below floor
        if run.benchmark_pass_rate < self.quality_floor:
            self._alarm(run)
        self.history.append(run)
        return run
    
    def _reembed_all(self) -> int:
        n = 0
        for doc in self.store.iter_documents():
            doc.embedding = self.embedder.embed(doc.text)
            self.store.update(doc)
            n += 1
        return n
    
    def _dedupe(self) -> int:
        # Find pairs with cosine similarity above threshold; merge older into newer
        clusters = self._cluster_by_similarity(threshold=0.97)
        merged = 0
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            keep = max(cluster, key=lambda d: d.last_accessed)
            for other in cluster:
                if other.id != keep.id:
                    keep.alias_ids.append(other.id)
                    self.store.delete(other.id)
                    merged += 1
        return merged
    
    def _evict_low_value(self) -> int:
        cutoff = datetime.utcnow() - timedelta(days=180)
        evicted = 0
        for doc in self.store.iter_documents():
            if doc.last_accessed < cutoff and doc.access_count < 3:
                self.store.delete(doc.id)
                evicted += 1
        return evicted
    
    def _benchmark(self) -> float:
        hits = 0
        for q in self.benchmark:
            top = self.store.search(q.text, k=10)
            top_ids = [d.id for d in top]
            if any(eid in top_ids for eid in q.expected_doc_ids):
                hits += 1
        return hits / len(self.benchmark)
```

#### Trade-offs and Alternatives

A curator agent costs compute (re-embedding, dedup, benchmarking) and operational attention (someone has to maintain the benchmark query set). The cost is justified when retrieval quality is a load-bearing property of the agent — when the agent's outputs depend critically on retrieving the right document.

For agents where retrieval is incidental (a tool that occasionally checks the knowledge base), running curation on a weekly cadence is sufficient. For agents where retrieval is central (a RAG-based research agent), daily curation and continuous benchmarking are warranted.

#### Production Failure Modes

- 

**Benchmark staleness:** The benchmark query set was assembled at launch. The query distribution has shifted, and the benchmark is no longer representative. Mitigate by sampling production queries into the benchmark on a rolling basis.

- 

**Embedder upgrade catastrophe:** A new embedder version is deployed. Re-embedding takes hours, and queries during the window are answered against a mixed-version store. Mitigate by blue-green re-embedding: build the new index alongside, swap atomically.

- 

**Sharding drift:** Hot shards get hotter, query latency rises on them. Mitigate by monitoring per-shard load and rebalancing on schedule.

#### Case Study

An enterprise documentation assistant at a global software vendor sees retrieval quality improve, rather than decay, over its first year of operation because the curator catches and corrects each source of drift before it becomes a user complaint.

Documented benchmark pass-rate at launch: 81%, at month twelve: 89%. Without the curator, internal estimates put the at-month-twelve rate near 70% based on observed degradation patterns elsewhere.

**Pairs with:** Schema-Inference (Agent 7), Drift Detector (Agent 59), Working-Memory Manager (Agent 25).
