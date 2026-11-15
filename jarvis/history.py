"""Persistent dictation and command history store backed by SQLite."""

import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

DB_DIR = Path.home() / ".local" / "share" / "jarvis"
DB_PATH = DB_DIR / "history.sqlite3"


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = db_path or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                mode TEXT NOT NULL,
                provider TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                formatted_text TEXT NOT NULL,
                duration_sec REAL DEFAULT 0.0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_time ON history(timestamp DESC)")
        # Migrate schema if columns were added later
        try:
            cur = conn.execute("PRAGMA table_info(history)")
            existing_cols = {row["name"] for row in cur.fetchall()}
            if "duration_sec" not in existing_cols:
                conn.execute("ALTER TABLE history ADD COLUMN duration_sec REAL DEFAULT 0.0")
        except Exception:
            pass
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Explicitly initializes the database schema."""
    conn = get_db_connection(db_path)
    conn.close()


def save_history_item(
    raw_text: str,
    formatted_text: str,
    mode: str = "transcribe",
    provider: str = "groq",
    duration_sec: float = 0.0,
    db_path: Optional[Path] = None,
) -> int:
    """Saves a transcription / dictation item to local SQLite history."""
    if not formatted_text and not raw_text:
        return -1
    conn = get_db_connection(db_path)
    with conn:
        cur = conn.execute(
            """
            INSERT INTO history (timestamp, mode, provider, raw_text, formatted_text, duration_sec)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (time.time(), mode, provider, raw_text, formatted_text, duration_sec),
        )
        return cur.lastrowid


# Alias for backward and server compatibility
add_history_entry = save_history_item


def list_history(limit: int = 100, query: str = "", db_path: Optional[Path] = None) -> List[Dict]:
    """Retrieves recent dictation history items, optionally filtered by query."""
    conn = get_db_connection(db_path)
    with conn:
        if query.strip():
            wildcard = f"%{query.strip()}%"
            cur = conn.execute(
                """
                SELECT id, timestamp, mode, provider, raw_text, formatted_text, duration_sec
                FROM history
                WHERE formatted_text LIKE ? OR raw_text LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (wildcard, wildcard, limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, timestamp, mode, provider, raw_text, formatted_text, duration_sec
                FROM history
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
        return [dict(row) for row in cur.fetchall()]


def delete_history_item(item_id: int, db_path: Optional[Path] = None) -> None:
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("DELETE FROM history WHERE id = ?", (item_id,))


def clear_all_history(db_path: Optional[Path] = None) -> None:
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("DELETE FROM history")
