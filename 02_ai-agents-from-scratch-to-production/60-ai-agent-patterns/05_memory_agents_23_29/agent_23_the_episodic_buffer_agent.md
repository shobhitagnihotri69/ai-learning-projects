# Agent 23 — The Episodic Buffer Agent

### Agent 23 — The Episodic Buffer Agent

*Stores and retrieves recent interaction episodes with explicit time-and-actor structure.*

#### The Problem

The agent needs to remember what just happened. Not the prompt-completion log, but the structured story of which actors did what, in what order, and with what intermediate state.

For example, a user asks the agent about "that conversation last Tuesday with the engineering team about the migration" and the agent, without a structured episodic memory, has either no memory of it (the transcript scrolled out of the context window) or a useless memory of it (an unstructured log that the agent can't query semantically).

The general problem is **typed, queryable history**: making the agent's past interactions available as structured data, with explicit actors and timestamps, queryable by predicates that go beyond "find similar text."

#### Why Naïve Approaches Fail

- 

*"Keep the chat history in context."* Works for short sessions, fails for anything longer than a few hundred turns, explodes in cost.

- 

*"Save the transcript to a vector store."* Retrieves by text similarity, can't answer structural questions ("the last time this user expressed dissatisfaction").

- 

*"Save the transcript as a database row per turn."* Useful for retrieval by keyword, loses the higher-level structure (who said what, what was decided, what changed state).

#### The Mechanism

Structured event capture rather than free-text logging. Time-and-actor indexing as first-class concerns. Eviction policies based on recency-weighted relevance, not pure LRU. A retrieval interface that returns structured events, not free text.

![Pattern 047 — Agent 23 — The Episodic Buffer Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dee3d68cad31e737ecd_codex-pattern-047-agent-23-the-episodic-buffer-agent-the-mechanism.png)

```python
# memory/episodic.py
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
```

#### Trade-offs and Alternatives

A typed episodic store is operationally heavier than a chat-log. The cost is justified for agents that operate across sessions or that need to answer questions about their own past. For single-session agents (search-style or one-shot tools), a flat history is sufficient.

For very high-volume agents, replace SQLite with a real columnar store (Postgres with appropriate indexes, ClickHouse, BigQuery) and project frequent query shapes into materialized views. The interface to the rest of the agent stays the same, only the backend scales.

#### Production Failure Modes

- 

**Index growth:** Indexes scale linearly with episode count. Without partitioning, query latency degrades. Partition by thread_id or by month for older data.

- 

**Privacy contamination:** Episodes record everything they observe, including data the user did not intend to persist. Mitigate by routing every episode through the same redaction layer as the rest of the agent (Section 4.7), with stricter rules for the episodic store than for the in-context state.

- 

**Reactive memory:** The agent records faithfully but never *uses* the episodes, so the buffer becomes write-only. Mitigate by including an explicit "consult episodic memory" step in any planner that benefits from history. Surface episodic recall to the operator in trace events.

#### Case Study

An executive-assistant agent at a venture-capital firm holds a structured episodic memory of every meeting, message, and decision involving its principal. The store contains approximately 18 months of activity (≈140,000 episodes) with per-episode embeddings and full structured payload. Recall queries from the agent typically return in under 200ms. The most-used predicate is "the last time the principal interacted with this entity," which the agent uses to set context for every new outreach.

The principal reports that they reduce their preparation time for new meetings by approximately 60% because the agent surfaces the relevant prior touchpoints unprompted.

**Pairs with:** Memory-of-Self (Agent 27), Persistent Identity (Agent 29), Working-Memory Manager (Agent 25).
