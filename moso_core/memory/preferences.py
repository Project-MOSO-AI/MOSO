from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from moso_core.memory.models import PreferenceMemory

logger = logging.getLogger(__name__)


class PreferenceStore:
    def __init__(self, db):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                owner_id TEXT NOT NULL DEFAULT 'default',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(category, owner_id)
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_preferences_owner
            ON preferences(owner_id)
        """)
        self.db.commit()

    def store(self, memory: PreferenceMemory) -> int:
        now = datetime.utcnow().isoformat()
        cursor = self.db.execute(
            """INSERT OR REPLACE INTO preferences (category, value, confidence, owner_id, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (memory.category, memory.value, memory.confidence, memory.owner_id, now),
        )
        self.db.commit()
        memory_id = cursor.lastrowid
        logger.debug("Stored preference %s=%s for owner %s", memory.category, memory.value, memory.owner_id)
        return memory_id

    def get(self, category: str, owner_id: str = "default") -> Optional[PreferenceMemory]:
        row = self.db.execute(
            "SELECT * FROM preferences WHERE category = ? AND owner_id = ?",
            (category, owner_id),
        ).fetchone()
        if row is None:
            return None
        return PreferenceMemory.from_row(dict(row))

    def list_all(self, owner_id: str = "default") -> list[PreferenceMemory]:
        rows = self.db.execute(
            "SELECT * FROM preferences WHERE owner_id = ? ORDER BY category",
            (owner_id,),
        ).fetchall()
        return [PreferenceMemory.from_row(dict(r)) for r in rows]

    def set_value(self, category: str, value: str, confidence: float = 1.0, owner_id: str = "default") -> int:
        memory = PreferenceMemory(category=category, value=value, confidence=confidence, owner_id=owner_id)
        return self.store(memory)

    def delete(self, category: str, owner_id: str = "default"):
        self.db.execute(
            "DELETE FROM preferences WHERE category = ? AND owner_id = ?",
            (category, owner_id),
        )
        self.db.commit()

    def count(self, owner_id: Optional[str] = None) -> int:
        sql = "SELECT COUNT(*) FROM preferences"
        params: list = []
        if owner_id:
            sql += " WHERE owner_id = ?"
            params.append(owner_id)
        return self.db.execute(sql, params).fetchone()[0]
