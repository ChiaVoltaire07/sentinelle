"""Historique des conversations chat (SQLite local)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from bot.config import DATA_DIR

HISTORY_DB = DATA_DIR / "chat_history.db"


class ChatHistoryStore:
    def __init__(self, path: Path = HISTORY_DB):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS chat_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources_json TEXT,
                created_at TEXT DEFAULT (datetime('now', 'utc'))
            )"""
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_turns(session_id, id DESC)"
        )

    def add(self, session_id: str, role: str, content: str, sources: Optional[list] = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO chat_turns (session_id, role, content, sources_json) VALUES (?,?,?,?)",
            (session_id, role, content, json.dumps(sources or [], ensure_ascii=False)),
        )
        return cur.lastrowid

    def list_sessions(self, limit: int = 30) -> List[dict]:
        rows = self.conn.execute(
            """SELECT session_id,
                      MAX(id) AS last_id,
                      MAX(created_at) AS last_at,
                      (SELECT content FROM chat_turns t2
                       WHERE t2.session_id = chat_turns.session_id AND role='user'
                       ORDER BY id DESC LIMIT 1) AS preview
               FROM chat_turns
               GROUP BY session_id
               ORDER BY last_id DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {
                "session_id": r["session_id"],
                "preview": (r["preview"] or "Conversation")[:80],
                "last_at": r["last_at"],
            }
            for r in rows
        ]

    def get_session(self, session_id: str, limit: int = 100) -> List[dict]:
        rows = self.conn.execute(
            """SELECT role, content, sources_json, created_at FROM chat_turns
               WHERE session_id=? ORDER BY id ASC LIMIT ?""",
            (session_id, limit),
        ).fetchall()
        out = []
        for r in rows:
            out.append({
                "role": r["role"],
                "content": r["content"],
                "sources": json.loads(r["sources_json"] or "[]"),
                "created_at": r["created_at"],
            })
        return out

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


_history: Optional[ChatHistoryStore] = None


def get_history_store() -> ChatHistoryStore:
    global _history
    if _history is None:
        _history = ChatHistoryStore()
    return _history
