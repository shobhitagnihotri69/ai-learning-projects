"""
Agent 36 — The File-System Curator Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# tools/file_curator.py
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

