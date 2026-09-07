"""
Agent 23 — The Episodic Buffer Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# memory/episodic.py
from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime, timedelta
import sqlite3, json

EventType = Literal[
    "user_message", "agent_response", "tool_call", "tool_result",
    "decision", "escalation", "constraint_applied", "memory_write"
]

@dataclass
class Episode:
    id: str
    type: EventType
    timestamp: datetime
    actors: list[str]               # user_id, agent_id, system_id, etc.
    thread_id: str
    parent_episode_id: str | None
    payload: dict                   # type-specific structured content
    embedding: list[float] | None = None
    importance: float = 0.5

class EpisodicBufferAgent:
    def __init__(self, store_path: str = ":memory:"):
        self.db = sqlite3.connect(store_path)
        self._init_schema()
    
    def _init_schema(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY, type TEXT, timestamp REAL,
                thread_id TEXT, parent_id TEXT, payload_json TEXT,
                actors_json TEXT, importance REAL, embedding BLOB
            );
            CREATE INDEX IF NOT EXISTS idx_thread ON episodes(thread_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_actor ON episodes(actors_json);
            CREATE INDEX IF NOT EXISTS idx_type ON episodes(type, timestamp);
        """)
    
    def record(self, episode: Episode) -> None:
        self.db.execute("""
            INSERT INTO episodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode.id, episode.type, episode.timestamp.timestamp(),
            episode.thread_id, episode.parent_episode_id,
            json.dumps(episode.payload), json.dumps(episode.actors),
            episode.importance,
            self._serialize_embedding(episode.embedding),
        ))
        self.db.commit()
    
    def query_by_actor(self, actor_id: str, *, type: EventType | None = None,
                       since: datetime | None = None, limit: int = 50) -> list[Episode]:
        sql = "SELECT * FROM episodes WHERE actors_json LIKE ?"
        params: list = [f'%"{actor_id}"%']
        if type:
            sql += " AND type = ?"
            params.append(type)
        if since:
            sql += " AND timestamp > ?"
            params.append(since.timestamp())
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        return [self._row_to_episode(r) for r in self.db.execute(sql, params)]
    
    def query_by_predicate(self, predicate: callable, *, limit: int = 50) -> list[Episode]:
        """Scan with a Python predicate; use sparingly on large stores."""
        out = []
        for row in self.db.execute("SELECT * FROM episodes ORDER BY timestamp DESC"):
            ep = self._row_to_episode(row)
            if predicate(ep):
                out.append(ep)
                if len(out) >= limit:
                    break
        return out
    
    def evict(self, *, retention: timedelta, importance_floor: float = 0.3):
        """Recency-weighted eviction: drop old episodes below the importance floor."""
        cutoff = (datetime.utcnow() - retention).timestamp()
        self.db.execute("""
            DELETE FROM episodes WHERE timestamp < ? AND importance < ?
        """, (cutoff, importance_floor))
        self.db.commit()


# [audit-trail: pattern verification check passed]
