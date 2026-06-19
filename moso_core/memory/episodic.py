from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from moso_core.memory.models import EpisodicMemory

logger = logging.getLogger(__name__)


class EpisodicStore:
    def __init__(self, db):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                owner_id TEXT NOT NULL DEFAULT 'default',
                importance REAL DEFAULT 0.5,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodic_owner
            ON episodic_memory(owner_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodic_timestamp
            ON episodic_memory(timestamp DESC)
        """)
        self.db.commit()

    def store(self, memory: EpisodicMemory) -> int:
        if not memory.timestamp:
            memory.timestamp = datetime.utcnow().isoformat()
        tags_json = json.dumps(memory.tags) if isinstance(memory.tags, list) else memory.tags
        cursor = self.db.execute(
            """INSERT INTO episodic_memory (timestamp, title, description, tags, owner_id, importance)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (memory.timestamp, memory.title, memory.description, tags_json, memory.owner_id, memory.importance),
        )
        self.db.commit()
        memory_id = cursor.lastrowid
        logger.debug("Stored episodic memory #%d: %s", memory_id, memory.title)
        return memory_id

    def get(self, memory_id: int) -> Optional[EpisodicMemory]:
        row = self.db.execute(
            "SELECT * FROM episodic_memory WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            return None
        return EpisodicMemory.from_row(dict(row))

    def search(self, query: str, owner_id: Optional[str] = None, limit: int = 10) -> list[EpisodicMemory]:
        sql = "SELECT * FROM episodic_memory WHERE (title LIKE ? OR description LIKE ?)"
        params = [f"%{query}%", f"%{query}%"]
        if owner_id:
            sql += " AND owner_id = ?"
            params.append(owner_id)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, params).fetchall()
        return [EpisodicMemory.from_row(dict(r)) for r in rows]

    def list_recent(self, limit: int = 10, owner_id: Optional[str] = None) -> list[EpisodicMemory]:
        sql = "SELECT * FROM episodic_memory"
        params: list = []
        if owner_id:
            sql += " WHERE owner_id = ?"
            params.append(owner_id)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, params).fetchall()
        return [EpisodicMemory.from_row(dict(r)) for r in rows]

    def list_by_tags(self, tags: list[str], owner_id: Optional[str] = None, limit: int = 10) -> list[EpisodicMemory]:
        sql = "SELECT * FROM episodic_memory WHERE ("
        clauses = []
        params: list = []
        for tag in tags:
            clauses.append("tags LIKE ?")
            params.append(f"%{tag}%")
        sql += " OR ".join(clauses) + ")"
        if owner_id:
            sql += " AND owner_id = ?"
            params.append(owner_id)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, params).fetchall()
        return [EpisodicMemory.from_row(dict(r)) for r in rows]

    def update_importance(self, memory_id: int, importance: float):
        self.db.execute(
            "UPDATE episodic_memory SET importance = ? WHERE id = ?",
            (importance, memory_id),
        )
        self.db.commit()

    def delete(self, memory_id: int):
        self.db.execute("DELETE FROM episodic_memory WHERE id = ?", (memory_id,))
        self.db.commit()

    def count(self, owner_id: Optional[str] = None) -> int:
        sql = "SELECT COUNT(*) FROM episodic_memory"
        params: list = []
        if owner_id:
            sql += " WHERE owner_id = ?"
            params.append(owner_id)
        return self.db.execute(sql, params).fetchone()[0]
