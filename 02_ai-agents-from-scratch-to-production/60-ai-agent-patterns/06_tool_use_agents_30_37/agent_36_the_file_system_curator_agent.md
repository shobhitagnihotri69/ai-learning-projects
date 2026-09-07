# Agent 36 — The File-System Curator Agent

### Agent 36 — The File-System Curator Agent

*Organizes, deduplicates, and indexes files in a directory the agent is responsible for.*

#### The Problem

When an agent operates against a file system over time, it accumulates files. Without curation, the accumulated files become unnavigable, and the agent itself can't find its own outputs. The user, too, ends up with a directory of inscrutably named files from a year of agent activity.

The general problem is **maintained file-system state**: treating a directory as a living artifact with a classification, deduplication, indexing, and retention policy, not as an accidental log.

#### Why Naïve Approaches Fail

- 

*"Let files accumulate."* Directory becomes unusable, agent and user both lose track.

- 

*"Aggressively delete old files."* Loses valuable history.

- 

*"Hand-organize."* Doesn't scale across users or across agent activity.

#### The Mechanism

A classifier per file type with explicit confidence. A deduplication pass that catches both byte-equal and content-equal files. A search index updated incrementally. A retention policy with both age-based and importance-based decay.

![Pattern 060 — Agent 36 — The File-System Curator Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df5c6a7cb88a5c22c76_codex-pattern-060-agent-36-the-file-system-curator-agent-the-mechanism.png)

```python
# tools/file_curator.py
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

@dataclass
class FileRecord:
    path: Path
    content_hash: str        # SHA256 of bytes
    semantic_hash: str | None  # for media: perceptual hash; for text: shingled hash
    classification: str       # "document" | "code" | "data" | "media" | "other"
    importance: float
    created_at: datetime
    last_accessed: datetime
    size_bytes: int
    embedding: list[float] | None = None

class FileSystemCuratorAgent:
    def __init__(self, root: Path, classifier, embedder,
                 *, dedup_threshold: float = 0.97):
        self.root = root
        self.classifier = classifier
        self.embedder = embedder
        self.dedup_threshold = dedup_threshold
        self.index: dict[str, FileRecord] = {}
    
    def scan_and_update(self) -> dict:
        new_files = []
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            content_hash = self._hash(path)
            if path.name in self.index and self.index[path.name].content_hash == content_hash:
                continue   # unchanged
            classification = self.classifier.classify(path)
            record = FileRecord(
                path=path, content_hash=content_hash,
                semantic_hash=self._semantic_hash(path, classification),
                classification=classification,
                importance=self._estimate_importance(path),
                created_at=datetime.fromtimestamp(path.stat().st_ctime),
                last_accessed=datetime.fromtimestamp(path.stat().st_atime),
                size_bytes=path.stat().st_size,
            )
            if classification in ("document", "code"):
                record.embedding = self.embedder.embed(path.read_text(errors="ignore")[:8000])
            self.index[str(path)] = record
            new_files.append(record)
        return {"new": len(new_files), "total": len(self.index)}
    
    def dedupe(self) -> int:
        # Exact-duplicate pass
        seen_hashes: dict[str, FileRecord] = {}
        exact_dupes = 0
        for record in list(self.index.values()):
            if record.content_hash in seen_hashes:
                # Keep the more-recently-accessed copy
                kept = seen_hashes[record.content_hash]
                if record.last_accessed > kept.last_accessed:
                    record.path.replace(kept.path)
                    del self.index[str(kept.path)]
                else:
                    record.path.unlink()
                    del self.index[str(record.path)]
                exact_dupes += 1
            else:
                seen_hashes[record.content_hash] = record
        # Semantic-duplicate pass (slower; only on documents)
        semantic_dupes = self._dedupe_semantic()
        return exact_dupes + semantic_dupes
    
    def search(self, query: str, k: int = 10) -> list[FileRecord]:
        query_emb = self.embedder.embed(query)
        scored = [(self._cosine(query_emb, r.embedding), r)
                  for r in self.index.values() if r.embedding]
        scored.sort(key=lambda sr: sr[0], reverse=True)
        return [r for _, r in scored[:k]]
    
    def apply_retention(self, max_age: timedelta, importance_floor: float = 0.3) -> int:
        cutoff = datetime.utcnow() - max_age
        evicted = 0
        for record in list(self.index.values()):
            if record.last_accessed < cutoff and record.importance < importance_floor:
                record.path.unlink()
                del self.index[str(record.path)]
                evicted += 1
        return evicted
```

#### Trade-offs and Alternatives

A file-system curator is heavyweight relative to most agents' needs. For agents that produce occasional outputs into a flat directory, default file-system behavior is fine. The pattern earns its keep when the agent operates over long lifetimes, produces many outputs, or shares a directory with the user.

For environments where the file system is replaced by an object store or a content-addressable storage layer, the pattern reduces to maintaining an index over the store rather than the store itself.

#### Production Failure Modes

- 

**Privacy leak via index:** The index contains file metadata that is itself sensitive (like filenames revealing project names or document classifications revealing patient categories). Mitigate by treating the index as having the same privacy class as the most sensitive file it indexes.

- 

**Aggressive deduplication:** Two files that look semantically duplicate aren't actually duplicates (a draft and a final version). Mitigate by requiring near-identical content rather than near-identical embedding for dedup.

- 

**Eviction cascade:** A file is evicted, and an agent that depended on it fails downstream. Mitigate by tracking inter-file dependencies and refusing to evict files in the closure of an active dependency.

#### Case Study

A research-engineer's working directory at a research lab is under continuous curation by a file-system curator agent: every new PDF is classified, deduplicated against the existing collection, and added to a searchable semantic index.

The directory has been under management for two years and contains approximately 3,400 files. The engineer's reported "I can't find that paper" rate dropped from frequent to nearly zero.

**Pairs with:** Forgetting-Policy (Agent 26), Vector-Store Curator (Agent 28), Privacy-Preserving (Agent 57).

