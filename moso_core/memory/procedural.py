from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from moso_core.memory.models import ProceduralMemory

logger = logging.getLogger(__name__)


class ProceduralStore:
    def __init__(self, db):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS procedural_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL UNIQUE,
                steps TEXT DEFAULT '[]',
                success_rate REAL DEFAULT 0.0,
                times_used INTEGER DEFAULT 0,
                last_used TEXT,
                owner_id TEXT NOT NULL DEFAULT 'default',
                tags TEXT DEFAULT '[]'
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_procedural_owner
            ON procedural_memory(owner_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_procedural_task
            ON procedural_memory(task_name)
        """)
        self.db.commit()

    def store(self, memory: ProceduralMemory) -> int:
        steps_json = json.dumps(memory.steps) if isinstance(memory.steps, list) else memory.steps
        tags_json = json.dumps(memory.tags) if isinstance(memory.tags, list) else memory.tags
        now = datetime.utcnow().isoformat()
        cursor = self.db.execute(
            """INSERT OR REPLACE INTO procedural_memory
               (task_name, steps, success_rate, times_used, last_used, owner_id, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (memory.task_name, steps_json, memory.success_rate, memory.times_used, now, memory.owner_id, tags_json),
        )
        self.db.commit()
        memory_id = cursor.lastrowid
        logger.debug("Stored procedural memory #%d: %s", memory_id, memory.task_name)
        return memory_id

    def get(self, memory_id: int) -> Optional[ProceduralMemory]:
        row = self.db.execute(
            "SELECT * FROM procedural_memory WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            return None
        return ProceduralMemory.from_row(dict(row))

    def get_by_task(self, task_name: str) -> Optional[ProceduralMemory]:
        row = self.db.execute(
            "SELECT * FROM procedural_memory WHERE task_name = ?", (task_name,)
        ).fetchone()
        if row is None:
            return None
        return ProceduralMemory.from_row(dict(row))

    def search(self, query: str, owner_id: Optional[str] = None, limit: int = 10) -> list[ProceduralMemory]:
        sql = "SELECT * FROM procedural_memory WHERE task_name LIKE ? OR tags LIKE ?"
        params = [f"%{query}%", f"%{query}%"]
        if owner_id:
            sql += " AND owner_id = ?"
            params.append(owner_id)
        sql += " ORDER BY success_rate DESC, times_used DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, params).fetchall()
        return [ProceduralMemory.from_row(dict(r)) for r in rows]

    def record_use(self, task_name: str, success: bool):
        memory = self.get_by_task(task_name)
        if memory is None:
            return
        now = datetime.utcnow().isoformat()
        new_times = memory.times_used + 1
        new_rate = ((memory.success_rate * memory.times_used) + (1.0 if success else 0.0)) / new_times
        self.db.execute(
            """UPDATE procedural_memory
               SET times_used = ?, success_rate = ?, last_used = ?
               WHERE task_name = ?""",
            (new_times, new_rate, now, task_name),
        )
        self.db.commit()

    def delete(self, memory_id: int):
        self.db.execute("DELETE FROM procedural_memory WHERE id = ?", (memory_id,))
        self.db.commit()

    def list_all(self, owner_id: Optional[str] = None, limit: int = 50) -> list[ProceduralMemory]:
        sql = "SELECT * FROM procedural_memory"
        params: list = []
        if owner_id:
            sql += " WHERE owner_id = ?"
            params.append(owner_id)
        sql += " ORDER BY times_used DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, params).fetchall()
        return [ProceduralMemory.from_row(dict(r)) for r in rows]

    def count(self, owner_id: Optional[str] = None) -> int:
        sql = "SELECT COUNT(*) FROM procedural_memory"
        params: list = []
        if owner_id:
            sql += " WHERE owner_id = ?"
            params.append(owner_id)
        return self.db.execute(sql, params).fetchone()[0]
