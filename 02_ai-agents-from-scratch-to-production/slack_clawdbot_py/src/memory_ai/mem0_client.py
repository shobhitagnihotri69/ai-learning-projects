from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from ..config import config
from ..utils.logger import create_module_logger

logger = create_module_logger("mem0-client")

@dataclass
class MemoryItem:
    id: str
    memory: str
    user_id: Optional[str] = None
    score: Optional[float] = None
    created_at: Optional[str] = None

_memory_client = None
_is_initialized = False

def initialize_memory() -> bool:
    """Initialize the mem0 client (Cloud API or Local)."""
    global _memory_client, _is_initialized
    
    if not config.memory.enabled:
        logger.info("Long-term memory is disabled in configuration")
        _is_initialized = False
        return False

    api_key = config.memory.api_key
    if api_key:
        try:
            from mem0 import MemoryClient
            _memory_client = MemoryClient(api_key=api_key)
            _is_initialized = True
            logger.info("✅ mem0 Cloud client initialized")
            return True
        except ImportError:
            logger.warning("mem0ai library not installed. Run: pip install mem0ai")
        except Exception as e:
            logger.error(f"Failed to initialize mem0 Cloud client: {e}")
    
    # Fallback to local open-source Memory if available
    try:
        from mem0 import Memory
        _memory_client = Memory()
        _is_initialized = True
        logger.info("✅ mem0 Local client initialized")
        return True
    except ImportError:
        logger.info("mem0 not available, continuing without personalized long-term memory")
    except Exception as e:
        logger.warning(f"Could not initialize local mem0 client: {e}")

    _is_initialized = False
    return False

def is_memory_enabled() -> bool:
    return _is_initialized and _memory_client is not None

def add_memory(messages: List[Dict[str, str]], user_id: str) -> List[MemoryItem]:
    if not is_memory_enabled():
        return []

    try:
        # mem0 expects formatted message dicts with role and content
        response = _memory_client.add(messages=messages, user_id=user_id)
        results = []
        if isinstance(response, dict) and "results" in response:
            items = response["results"]
        elif isinstance(response, list):
            items = response
        else:
            items = []

        for item in items:
            results.append(MemoryItem(
                id=str(item.get("id", "")),
                memory=item.get("memory", item.get("text", "")),
                user_id=user_id
            ))
        logger.info(f"Added {len(results)} memory entries for user {user_id}")
        return results
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        return []

def search_memory(query: str, user_id: str, limit: int = 5) -> List[MemoryItem]:
    if not is_memory_enabled():
        return []

    try:
        response = _memory_client.search(query=query, user_id=user_id, limit=limit)
        results = []
        items = response if isinstance(response, list) else response.get("results", [])
        
        for item in items:
            results.append(MemoryItem(
                id=str(item.get("id", "")),
                memory=item.get("memory", item.get("text", "")),
                user_id=user_id,
                score=item.get("score")
            ))
        return results
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        return []

def get_all_memories(user_id: str) -> List[MemoryItem]:
    if not is_memory_enabled():
        return []

    try:
        response = _memory_client.get_all(user_id=user_id)
        results = []
        items = response if isinstance(response, list) else response.get("results", [])
        for item in items:
            results.append(MemoryItem(
                id=str(item.get("id", "")),
                memory=item.get("memory", item.get("text", "")),
                user_id=user_id
            ))
        return results
    except Exception as e:
        logger.error(f"Error getting all memories: {e}")
        return []

def delete_memory(memory_id: str) -> bool:
    if not is_memory_enabled():
        return False
    try:
        _memory_client.delete(memory_id=memory_id)
        return True
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id}: {e}")
        return False

def delete_all_memories(user_id: str) -> bool:
    if not is_memory_enabled():
        return False
    try:
        _memory_client.delete_all(user_id=user_id)
        return True
    except Exception as e:
        logger.error(f"Error deleting all memories for {user_id}: {e}")
        return False

def build_memory_context(memories: List[MemoryItem]) -> Optional[str]:
    if not memories:
        return None
    lines = ["Here are relevant facts remembered about this user:"]
    for mem in memories:
        lines.append(f"• {mem.memory}")
    return "\n".join(lines)
