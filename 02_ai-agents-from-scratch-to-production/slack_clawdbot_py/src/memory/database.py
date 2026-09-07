import sqlite3
import json
import time
import secrets
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from ..config import config
from ..utils.logger import create_module_logger

logger = create_module_logger("database")

@dataclass
class Session:
    id: str
    user_id: str
    channel_id: Optional[str]
    thread_ts: Optional[str]
    session_type: str
    created_at: int
    last_activity: int
    metadata: Optional[str] = None

@dataclass
class Message:
    id: int
    session_id: str
    role: str
    content: str
    slack_ts: Optional[str]
    thread_ts: Optional[str]
    created_at: int
    metadata: Optional[str] = None

@dataclass
class ScheduledTask:
    id: int
    user_id: str
    channel_id: str
    thread_ts: Optional[str]
    task_description: str
    cron_expression: Optional[str]
    scheduled_time: Optional[int]
    status: str
    created_at: int
    executed_at: Optional[int] = None
    metadata: Optional[str] = None

_connection: Optional[sqlite3.Connection] = None

def get_db() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        db_path = Path(config.app.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        _connection = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
            isolation_level=None  # autocommit mode
        )
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode = WAL")
        _connection.execute("PRAGMA foreign_keys = ON")
    return _connection

def initialize_database() -> None:
    """Initialize the database schema and indexes."""
    logger.info("Initializing database schema...")
    db = get_db()

    db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            channel_id TEXT,
            thread_ts TEXT,
            session_type TEXT NOT NULL DEFAULT 'dm',
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            last_activity INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            slack_ts TEXT,
            thread_ts TEXT,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            metadata TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            thread_ts TEXT,
            task_description TEXT NOT NULL,
            cron_expression TEXT,
            scheduled_time INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            executed_at INTEGER,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS pairing_codes (
            code TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            expires_at INTEGER NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS approved_users (
            user_id TEXT PRIMARY KEY,
            approved_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            approved_by TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_channel ON sessions(channel_id);
        CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status ON scheduled_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_pairing_codes_user ON pairing_codes(user_id);
    """)
    logger.info("✅ Database schema initialized successfully")

def close_database() -> None:
    global _connection
    if _connection is not None:
        try:
            _connection.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        finally:
            _connection = None

def get_or_create_session(
    user_id: str,
    channel_id: Optional[str] = None,
    thread_ts: Optional[str] = None,
    session_type: str = "dm"
) -> Session:
    db = get_db()
    
    if thread_ts and channel_id:
        session_id = f"thread_{channel_id}_{thread_ts}"
    elif channel_id and session_type == "channel":
        session_id = f"channel_{channel_id}"
    else:
        session_id = f"dm_{user_id}"

    cursor = db.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()

    now = int(time.time())
    if row:
        cursor.execute("UPDATE sessions SET last_activity = ? WHERE id = ?", (now, session_id))
        return Session(**dict(row))

    cursor.execute(
        """
        INSERT INTO sessions (id, user_id, channel_id, thread_ts, session_type, created_at, last_activity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, user_id, channel_id, thread_ts, session_type, now, now)
    )
    return Session(
        id=session_id,
        user_id=user_id,
        channel_id=channel_id,
        thread_ts=thread_ts,
        session_type=session_type,
        created_at=now,
        last_activity=now
    )

def add_message(
    session_id: str,
    role: str,
    content: str,
    slack_ts: Optional[str] = None,
    thread_ts: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    db = get_db()
    cursor = db.cursor()
    now = int(time.time())
    meta_json = json.dumps(metadata) if metadata else None
    
    cursor.execute(
        """
        INSERT INTO messages (session_id, role, content, slack_ts, thread_ts, created_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, role, content, slack_ts, thread_ts, now, meta_json)
    )
    cursor.execute("UPDATE sessions SET last_activity = ? WHERE id = ?", (now, session_id))
    return cursor.lastrowid

def get_session_history(session_id: str, limit: int = 20) -> List[Message]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT * FROM messages 
        WHERE session_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
        """,
        (session_id, limit)
    )
    rows = cursor.fetchall()
    messages = [Message(**dict(row)) for row in reversed(rows)]
    return messages

def get_thread_messages(channel_id: str, thread_ts: str) -> List[Message]:
    session_id = f"thread_{channel_id}_{thread_ts}"
    return get_session_history(session_id, limit=50)

def create_scheduled_task(
    user_id: str,
    channel_id: str,
    task_description: str,
    thread_ts: Optional[str] = None,
    cron_expression: Optional[str] = None,
    scheduled_time: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    db = get_db()
    cursor = db.cursor()
    now = int(time.time())
    meta_json = json.dumps(metadata) if metadata else None

    cursor.execute(
        """
        INSERT INTO scheduled_tasks 
        (user_id, channel_id, thread_ts, task_description, cron_expression, scheduled_time, status, created_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (user_id, channel_id, thread_ts, task_description, cron_expression, scheduled_time, now, meta_json)
    )
    return cursor.lastrowid

def get_pending_tasks() -> List[ScheduledTask]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM scheduled_tasks WHERE status = 'pending' ORDER BY created_at ASC"
    )
    rows = cursor.fetchall()
    return [ScheduledTask(**dict(row)) for row in rows]

def update_task_status(task_id: int, status: str, executed_at: Optional[int] = None) -> None:
    db = get_db()
    cursor = db.cursor()
    now = executed_at or int(time.time())
    cursor.execute(
        "UPDATE scheduled_tasks SET status = ?, executed_at = ? WHERE id = ?",
        (status, now, task_id)
    )

def get_user_tasks(user_id: str) -> List[ScheduledTask]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM scheduled_tasks WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    return [ScheduledTask(**dict(row)) for row in rows]

def delete_task(task_id: int) -> bool:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
    return cursor.rowcount > 0

def generate_pairing_code(user_id: str) -> str:
    db = get_db()
    cursor = db.cursor()
    code = secrets.token_hex(3).upper()  # 6-char hex code
    now = int(time.time())
    expires = now + 600  # 10 minutes

    cursor.execute(
        "INSERT OR REPLACE INTO pairing_codes (code, user_id, created_at, expires_at, approved) VALUES (?, ?, ?, ?, 0)",
        (code, user_id, now, expires)
    )
    return code

def approve_pairing(code: str, approved_by: str) -> bool:
    db = get_db()
    cursor = db.cursor()
    now = int(time.time())

    cursor.execute("SELECT * FROM pairing_codes WHERE code = ? AND expires_at > ? AND approved = 0", (code, now))
    row = cursor.fetchone()
    if not row:
        return False

    user_id = row["user_id"]
    cursor.execute("UPDATE pairing_codes SET approved = 1 WHERE code = ?", (code,))
    cursor.execute(
        "INSERT OR REPLACE INTO approved_users (user_id, approved_at, approved_by) VALUES (?, ?, ?)",
        (user_id, now, approved_by)
    )
    return True

def is_user_approved(user_id: str) -> bool:
    if not config.features.require_approval:
        return True
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM approved_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None
