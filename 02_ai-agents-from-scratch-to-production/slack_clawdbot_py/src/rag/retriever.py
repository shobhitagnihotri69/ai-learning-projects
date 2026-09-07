import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .embeddings import get_embedding
from .vectorstore import get_vector_store, SearchResult
from ..config import config
from ..utils.logger import create_module_logger

logger = create_module_logger("retriever")

RAG_TRIGGERS = [
    r"\b(who|what|where|when|why|how)\b",
    r"\b(did|does|is|are|was|were)\b",
    r"\b(remember|recall|find|search|look up)\b",
    r"\b(decision|discussion|channel|thread|meeting)\b",
    r"\b(last week|yesterday|earlier|previously|history)\b",
    r"\b(documentation|doc|deploy|setup|architecture)\b",
]

def should_use_rag(message: str) -> bool:
    """Determine if a user's question warrants RAG search in Slack history."""
    if not config.rag.enabled:
        return False
        
    lower = message.lower()
    
    # Exclude simple commands or greetings
    if len(lower.split()) < 3 and any(lower.startswith(w) for w in ["hi", "hello", "hey", "test", "ping"]):
        return False

    for pattern in RAG_TRIGGERS:
        if re.search(pattern, lower):
            return True
            
    return len(message.split()) > 6

def parse_query_filters(query: str) -> Dict[str, Optional[str]]:
    """Extract filters like #channel-name from query."""
    channel_match = re.search(r"#([a-zA-Z0-9_\-]+)", query)
    channel_name = channel_match.group(1) if channel_match else None
    return {"channel_name": channel_name}

def retrieve(
    query: str,
    limit: Optional[int] = None,
    min_score: Optional[float] = None,
    channel_name: Optional[str] = None
) -> List[SearchResult]:
    """Retrieve relevant Slack context using semantic search."""
    if not config.rag.enabled:
        return []

    limit = limit or config.rag.max_results
    min_score = min_score or config.rag.min_similarity
    
    try:
        query_vec = get_embedding(query)
        store = get_vector_store()
        results = store.search(
            query_embedding=query_vec,
            limit=limit,
            min_score=min_score,
            channel_name=channel_name
        )
        logger.info(f"Retrieved {len(results)} relevant documents for query: '{query[:40]}...'")
        return results
    except Exception as e:
        logger.error(f"Error during RAG retrieval: {e}")
        return []

def build_context_string(results: List[SearchResult]) -> str:
    """Format retrieved Slack messages into context for LLM prompt."""
    if not results:
        return ""

    blocks = []
    for i, res in enumerate(results, 1):
        doc = res.document
        meta = doc.metadata or {}
        user = meta.get("userName", meta.get("userId", "Unknown"))
        channel = meta.get("channelName", "unknown-channel")
        timestamp = meta.get("dateTime", meta.get("timestamp", ""))
        
        blocks.append(
            f"[Source {i}] #{channel} | @{user} ({timestamp}):\n\"{doc.text}\""
        )

    return "\n\n---\n\n".join(blocks)
