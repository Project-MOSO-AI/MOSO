from __future__ import annotations

import logging
import os
import sqlite3
import threading
from typing import Optional

from moso_core.memory.episodic import EpisodicStore
from moso_core.memory.models import (
    EpisodicMemory,
    PreferenceMemory,
    ProceduralMemory,
    SemanticMemory,
)
from moso_core.memory.preferences import PreferenceStore
from moso_core.memory.procedural import ProceduralStore
from moso_core.memory.retrieval import MemoryRetriever
from moso_core.memory.semantic import SemanticStore
from moso_core.memory.summarizer import MemorySummarizer

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            home = os.path.expanduser("~")
            data_dir = os.path.join(home, ".moso")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "memory.db")
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._episodic = EpisodicStore(self)
        self._semantic = SemanticStore(self)
        self._procedural = ProceduralStore(self)
        self._preferences = PreferenceStore(self)
        self._retriever = MemoryRetriever(self._episodic, self._semantic, self._procedural, self._preferences)
        self._summarizer = MemorySummarizer(self._episodic, self._semantic)
        logger.info("MemoryManager initialized at %s", db_path)

    def _connect(self):
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def execute(self, sql: str, params: tuple = ()):
        with self._lock:
            return self._conn.execute(sql, params)

    def commit(self):
        with self._lock:
            self._conn.commit()

    @property
    def episodic(self) -> EpisodicStore:
        return self._episodic

    @property
    def semantic(self) -> SemanticStore:
        return self._semantic

    @property
    def procedural(self) -> ProceduralStore:
        return self._procedural

    @property
    def preferences(self) -> PreferenceStore:
        return self._preferences

    @property
    def retriever(self) -> MemoryRetriever:
        return self._retriever

    @property
    def summarizer(self) -> MemorySummarizer:
        return self._summarizer

    def store_event(
        self,
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
        owner_id: str = "default",
        importance: float = 0.5,
    ) -> int:
        memory = EpisodicMemory(
            title=title,
            description=description,
            tags=tags or [],
            owner_id=owner_id,
            importance=importance,
        )
        return self._episodic.store(memory)

    def store_fact(
        self,
        fact: str,
        confidence: float = 1.0,
        category: str = "general",
        owner_id: str = "default",
        source: str = "conversation",
    ) -> int:
        memory = SemanticMemory(
            fact=fact,
            confidence=confidence,
            category=category,
            owner_id=owner_id,
            source=source,
        )
        return self._semantic.store(memory)

    def store_preference(
        self,
        category: str,
        value: str,
        confidence: float = 1.0,
        owner_id: str = "default",
    ) -> int:
        return self._preferences.set_value(category, value, confidence, owner_id)

    def store_procedure(
        self,
        task_name: str,
        steps: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        owner_id: str = "default",
    ) -> int:
        memory = ProceduralMemory(
            task_name=task_name,
            steps=steps or [],
            tags=tags or [],
            owner_id=owner_id,
        )
        return self._procedural.store(memory)

    def retrieve_memories(
        self,
        query: str,
        memory_types: Optional[list[str]] = None,
        owner_id: Optional[str] = None,
        limit: int = 5,
    ) -> dict[str, list]:
        if memory_types:
            return self._retriever.search_types(query, memory_types, owner_id=owner_id, limit=limit)
        return self._retriever.search_all(query, owner_id=owner_id, limit=limit)

    def retrieve_preferences(self, owner_id: str = "default") -> list[PreferenceMemory]:
        return self._preferences.list_all(owner_id)

    def retrieve_recent_events(
        self,
        limit: int = 10,
        owner_id: Optional[str] = None,
    ) -> list[EpisodicMemory]:
        return self._episodic.list_recent(limit=limit, owner_id=owner_id)

    def build_context(
        self,
        query: str,
        owner_id: Optional[str] = None,
    ) -> str:
        return self._retriever.build_context(query, owner_id=owner_id)

    def summarize_memory(self, owner_id: str = "default") -> str:
        return self._summarizer.summarize_events_to_text(owner_id=owner_id)

    def run_maintenance(self, owner_id: str = "default"):
        self._summarizer.extract_facts_from_events(owner_id=owner_id)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("MemoryManager closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
