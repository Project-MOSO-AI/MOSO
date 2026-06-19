from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from moso_core.memory.models import SemanticMemory

logger = logging.getLogger(__name__)


class SemanticStore:
    def __init__(self, db):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                category TEXT DEFAULT 'general',
                owner_id TEXT NOT NULL DEFAULT 'default',
                source TEXT DEFAULT 'conversation',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_owner
            ON semantic_memory(owner_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_category
            ON semantic_memory(category)
        """)
        self.db.commit()

    def store(self, memory: SemanticMemory) -> int:
        now = datetime.utcnow().isoformat()
        cursor = self.db.execute(
            """INSERT INTO semantic_memory (fact, confidence, category, owner_id, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (memory.fact, memory.confidence, memory.category, memory.owner_id, memory.source, now, now),
        )
        self.db.commit()
        memory_id = cursor.lastrowid
        logger.debug("Stored semantic memory #%d: %s", memory_id, memory.fact[:60])
        return memory_id

    def get(self, memory_id: int) -> Optional[SemanticMemory]:
        row = self.db.execute(
            "SELECT * FROM semantic_memory WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            return None
        return SemanticMemory.from_row(dict(row))

    def search(self, query: str, owner_id: Optional[str] = None, limit: int = 10) -> list[SemanticMemory]:
        sql = "SELECT * FROM semantic_memory WHERE fact LIKE ?"
        params = [f"%{query}%"]
        if owner_id:
            sql += " AND owner_id = ?"
            params.append(owner_id)
        sql += " ORDER BY confidence DESC, updated_at DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, params).fetchall()
        return [SemanticMemory.from_row(dict(r)) for r in rows]

    def list_by_category(self, category: str, owner_id: Optional[str] = None, limit: int = 20) -> list[SemanticMemory]:
        sql = "SELECT * FROM semantic_memory WHERE category = ?"
        params = [category]
        if owner_id:
            sql += " AND owner_id = ?"
            params.append(owner_id)
        sql += " ORDER BY confidence DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, params).fetchall()
        return [SemanticMemory.from_row(dict(r)) for r in rows]

    def list_recent(self, limit: int = 10, owner_id: Optional[str] = None) -> list[SemanticMemory]:
        sql = "SELECT * FROM semantic_memory"
        params: list = []
        if owner_id:
            sql += " WHERE owner_id = ?"
            params.append(owner_id)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, params).fetchall()
        return [SemanticMemory.from_row(dict(r)) for r in rows]

    def update(self, memory_id: int, fact: Optional[str] = None, confidence: Optional[float] = None):
        now = datetime.utcnow().isoformat()
        updates = ["updated_at = ?"]
        params = [now]
        if fact is not None:
            updates.append("fact = ?")
            params.append(fact)
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)
        params.append(memory_id)
        self.db.execute(
            f"UPDATE semantic_memory SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        self.db.commit()

    def delete(self, memory_id: int):
        self.db.execute("DELETE FROM semantic_memory WHERE id = ?", (memory_id,))
        self.db.commit()

    def count(self, owner_id: Optional[str] = None) -> int:
        sql = "SELECT COUNT(*) FROM semantic_memory"
        params: list = []
        if owner_id:
            sql += " WHERE owner_id = ?"
            params.append(owner_id)
        return self.db.execute(sql, params).fetchone()[0]
