"""Persistent dictation and command history store backed by SQLite."""

import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

DB_DIR = Path.home() / ".local" / "share" / "jarvis"
DB_PATH = DB_DIR / "history.sqlite3"


def get_db_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                mode TEXT NOT NULL,
                provider TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                formatted_text TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_time ON history(timestamp DESC)")
    return conn


def save_history_item(raw_text: str, formatted_text: str, mode: str = "transcribe", provider: str = "groq") -> int:
    """Saves a transcription / dictation item to local SQLite history."""
    if not formatted_text and not raw_text:
        return -1
    conn = get_db_connection()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO history (timestamp, mode, provider, raw_text, formatted_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (time.time(), mode, provider, raw_text, formatted_text),
        )
        return cur.lastrowid


def list_history(limit: int = 100, query: str = "") -> List[Dict]:
    """Retrieves recent dictation history items, optionally filtered by query."""
    conn = get_db_connection()
    with conn:
        if query.strip():
            wildcard = f"%{query.strip()}%"
            cur = conn.execute(
                """
                SELECT id, timestamp, mode, provider, raw_text, formatted_text
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
                SELECT id, timestamp, mode, provider, raw_text, formatted_text
                FROM history
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
        return [dict(row) for row in cur.fetchall()]


def delete_history_item(item_id: int) -> None:
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM history WHERE id = ?", (item_id,))


def clear_all_history() -> None:
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM history")
