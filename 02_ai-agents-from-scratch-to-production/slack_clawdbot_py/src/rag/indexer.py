import threading
import time
from typing import List, Optional
from datetime import datetime
try:
    from slack_sdk import WebClient
except ImportError:
    WebClient = None
from .embeddings import get_embeddings_batch
from .vectorstore import get_vector_store, VectorDocument
from ..config import config
from ..utils.logger import create_module_logger

logger = create_module_logger("indexer")

_indexer_timer: Optional[threading.Timer] = None
_is_indexing: bool = False

def index_channel(web_client: WebClient, channel_id: str, channel_name: str, limit: int = 100) -> int:
    """Fetch messages from a single Slack channel and index into vector store."""
    try:
        response = web_client.conversations_history(channel=channel_id, limit=limit)
        messages = response.get("messages", [])
        
        valid_messages = []
        for msg in messages:
            text = msg.get("text", "").strip()
            # Skip subtype notifications (channel_join, etc.) or bot's own messages
            if msg.get("subtype") or not text or len(text) < 10:
                continue
            valid_messages.append(msg)

        if not valid_messages:
            return 0

        texts = [m.get("text", "") for m in valid_messages]
        embeddings = get_embeddings_batch(texts)
        
        docs = []
        for msg, emb in zip(valid_messages, embeddings):
            ts = msg.get("ts", "")
            user_id = msg.get("user", "unknown")
            dt = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M") if ts else ""
            
            doc_id = f"slack_{channel_id}_{ts}"
            docs.append(VectorDocument(
                id=doc_id,
                text=msg.get("text", ""),
                embedding=emb,
                metadata={
                    "channelId": channel_id,
                    "channelName": channel_name,
                    "userId": user_id,
                    "timestamp": ts,
                    "dateTime": dt,
                }
            ))

        store = get_vector_store()
        store.add_documents(docs)
        logger.info(f"Indexed {len(docs)} messages from #{channel_name}")
        return len(docs)
    except Exception as e:
        logger.error(f"Failed to index channel #{channel_name} ({channel_id}): {e}")
        return 0

def index_all_channels(web_client: Optional[WebClient] = None) -> int:
    """Index all public channels the bot has access to."""
    global _is_indexing
    if _is_indexing:
        logger.info("Indexing already in progress, skipping")
        return 0

    _is_indexing = True
    total_indexed = 0
    
    try:
        client = web_client or WebClient(token=config.slack.bot_token)
        convs = client.conversations_list(types="public_channel,private_channel", limit=100)
        channels = convs.get("channels", [])

        for chan in channels:
            if chan.get("is_member"):
                c_id = chan["id"]
                c_name = chan.get("name", c_id)
                count = index_channel(client, c_id, c_name)
                total_indexed += count

        logger.info(f"Indexing complete. Total {total_indexed} documents indexed across channels.")
    except Exception as e:
        logger.error(f"Error during channel indexing: {e}")
    finally:
        _is_indexing = False

    return total_indexed

def start_indexer(interval_hours: Optional[int] = None) -> None:
    """Start periodic background indexer."""
    if not config.rag.enabled or not config.rag.auto_index:
        return

    interval = (interval_hours or config.rag.indexer_interval_hours) * 3600
    
    def run_periodically():
        global _indexer_timer
        try:
            index_all_channels()
        except Exception as e:
            logger.error(f"Background indexer error: {e}")
        finally:
            _indexer_timer = threading.Timer(interval, run_periodically)
            _indexer_timer.daemon = True
            _indexer_timer.start()

    # Initial delay before first background crawl (30s)
    global _indexer_timer
    _indexer_timer = threading.Timer(30.0, run_periodically)
    _indexer_timer.daemon = True
    _indexer_timer.start()
    logger.info(f"Started background indexer (interval: {config.rag.indexer_interval_hours}h)")

def stop_indexer() -> None:
    """Stop the background indexer thread."""
    global _indexer_timer
    if _indexer_timer is not None:
        _indexer_timer.cancel()
        _indexer_timer = None
        logger.info("Stopped background indexer")
