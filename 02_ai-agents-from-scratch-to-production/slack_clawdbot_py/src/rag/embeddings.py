import math
import numpy as np
from typing import List, Union
from openai import OpenAI
from ..config import config
from ..utils.logger import create_module_logger

logger = create_module_logger("embeddings")

_client = None

def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.ai.openai_api_key)
    return _client

def get_embedding(text: str) -> List[float]:
    """Generate embedding for a single text."""
    client = get_openai_client()
    clean_text = text.replace("\n", " ").strip()
    if not clean_text:
        return [0.0] * 1536

    response = client.embeddings.create(
        input=clean_text,
        model=config.rag.embedding_model
    )
    return response.data[0].embedding

def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a batch of texts."""
    if not texts:
        return []
        
    client = get_openai_client()
    clean_texts = [t.replace("\n", " ").strip() or "empty" for t in texts]
    
    response = client.embeddings.create(
        input=clean_texts,
        model=config.rag.embedding_model
    )
    return [item.embedding for item in response.data]

def cosine_similarity(vec_a: Union[List[float], np.ndarray], vec_b: Union[List[float], np.ndarray]) -> float:
    """Calculate cosine similarity between two vectors using numpy."""
    a = np.asarray(vec_a, dtype=np.float32)
    b = np.asarray(vec_b, dtype=np.float32)
    
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
