import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from .embeddings import cosine_similarity
from ..config import config
from ..utils.logger import create_module_logger

logger = create_module_logger("vectorstore")

@dataclass
class VectorDocument:
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]

@dataclass
class SearchResult:
    document: VectorDocument
    score: float

class VectorStore:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or config.app.vectorstore_path)
        self.documents: Dict[str, VectorDocument] = {}
        self._load()

    def _load(self) -> None:
        """Load vector documents from local JSON file."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for item in raw_data:
                    doc = VectorDocument(
                        id=item["id"],
                        text=item["text"],
                        embedding=item["embedding"],
                        metadata=item.get("metadata", {})
                    )
                    self.documents[doc.id] = doc
            logger.info(f"Loaded {len(self.documents)} vector documents from {self.storage_path}")
        except Exception as e:
            logger.error(f"Error loading vector store from disk: {e}")

    def save(self) -> None:
        """Persist vector documents to local JSON file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = [
                {
                    "id": doc.id,
                    "text": doc.text,
                    "embedding": doc.embedding,
                    "metadata": doc.metadata
                }
                for doc in self.documents.values()
            ]
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f)
            logger.info(f"Saved {len(self.documents)} vector documents to {self.storage_path}")
        except Exception as e:
            logger.error(f"Error saving vector store to disk: {e}")

    def add_documents(self, docs: List[VectorDocument]) -> None:
        for doc in docs:
            self.documents[doc.id] = doc
        self.save()

    def count(self) -> int:
        return len(self.documents)

    def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        min_score: float = 0.65,
        channel_name: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[SearchResult]:
        results: List[SearchResult] = []

        for doc in self.documents.values():
            meta = doc.metadata or {}

            # Filter by channel
            if channel_name and meta.get("channelName", "").lower() != channel_name.lower():
                continue
            if channel_id and meta.get("channelId") != channel_id:
                continue

            # Filter by user
            if user_id and meta.get("userId") != user_id:
                continue

            score = cosine_similarity(query_embedding, doc.embedding)
            if score >= min_score:
                results.append(SearchResult(document=doc, score=score))

        # Sort by similarity score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def clear(self) -> None:
        self.documents.clear()
        if self.storage_path.exists():
            try:
                self.storage_path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete vector store file: {e}")

_global_store: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    global _global_store
    if _global_store is None:
        _global_store = VectorStore()
    return _global_store

def initialize_vector_store() -> VectorStore:
    return get_vector_store()

def get_document_count() -> int:
    return get_vector_store().count()
