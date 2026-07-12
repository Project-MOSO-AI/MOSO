from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class StoreEntry:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = sum(ai * ai for ai in a) ** 0.5
    norm_b = sum(bi * bi for bi in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


_default_model = None

def _default_embedder(text: str) -> list[float]:
    global _default_model
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise RuntimeError("No embedder configured and sentence-transformers is not installed; semantic search unavailable")
    
    if _default_model is None:
        _default_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _default_model.encode(text).tolist()


class VectorStore:
    def __init__(self, db_path: str | Path = "vector_store.db", embedder: Optional[Callable[[str], list[float]]] = None):
        self._db_path = Path(db_path)
        self._embedder = embedder or _default_embedder
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                embedding TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                id UNINDEXED, text, content=entries, content_rowid=rowid
            )
        """)
        self._conn.execute("""
            CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
                INSERT INTO entries_fts(rowid, id, text) VALUES (new.rowid, new.id, new.text);
            END
        """)
        self._conn.execute("""
            CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
                INSERT INTO entries_fts(entries_fts, rowid, id, text) VALUES ('delete', old.rowid, old.id, old.text);
            END
        """)
        self._conn.execute("""
            CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
                INSERT INTO entries_fts(entries_fts, rowid, id, text) VALUES ('delete', old.rowid, old.id, old.text);
                INSERT INTO entries_fts(rowid, id, text) VALUES (new.rowid, new.id, new.text);
            END
        """)
        self._conn.commit()

    @property
    def has_embedder(self) -> bool:
        return self._embedder is not _default_embedder

    def store(self, entry: StoreEntry) -> None:
        if not entry.embedding and self.has_embedder:
            try:
                entry.embedding = self._embedder(entry.text)
            except Exception as e:
                logger.warning("Embedding failed for %s: %s", entry.id, e)

        now = time.time()
        entry.created_at = entry.created_at or now
        entry.updated_at = now
        emb_json = json.dumps(entry.embedding) if entry.embedding else None

        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO entries (id, text, metadata, embedding, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (entry.id, entry.text, json.dumps(entry.metadata), emb_json, entry.created_at, entry.updated_at),
            )
            self._conn.commit()

    def get(self, entry_id: str) -> Optional[StoreEntry]:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, text, metadata, embedding, created_at, updated_at FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
        if row is None:
            return None
        return StoreEntry(
            id=row[0],
            text=row[1],
            metadata=json.loads(row[2]),
            embedding=json.loads(row[3]) if row[3] else None,
            created_at=row[4],
            updated_at=row[5],
        )

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def list_entries(self, limit: int = 100, offset: int = 0) -> list[StoreEntry]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, text, metadata, embedding, created_at, updated_at FROM entries ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [
            StoreEntry(
                id=r[0],
                text=r[1],
                metadata=json.loads(r[2]),
                embedding=json.loads(r[3]) if r[3] else None,
                created_at=r[4],
                updated_at=r[5],
            )
            for r in rows
        ]

    def search_keyword(self, query: str, limit: int = 10) -> list[tuple[StoreEntry, float]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT e.id, e.text, e.metadata, e.embedding, e.created_at, e.updated_at, rank "
                "FROM entries_fts f JOIN entries e ON e.id = f.id "
                "WHERE entries_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
        return [
            (
                StoreEntry(
                    id=r[0],
                    text=r[1],
                    metadata=json.loads(r[2]),
                    embedding=json.loads(r[3]) if r[3] else None,
                    created_at=r[4],
                    updated_at=r[5],
                ),
                1.0 - float(r[6]) / (1.0 + abs(float(r[6]))),
            )
            for r in rows
        ]

    def search_semantic(self, query: str, limit: int = 10) -> list[tuple[StoreEntry, float]]:
        if not self.has_embedder:
            logger.warning("Semantic search unavailable: no embedder configured")
            return []

        query_emb = self._embedder(query)
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, text, metadata, embedding, created_at, updated_at FROM entries WHERE embedding IS NOT NULL"
            ).fetchall()

        scored: list[tuple[StoreEntry, float]] = []
        for r in rows:
            emb = json.loads(r[3])
            if emb:
                score = _cosine_similarity(query_emb, emb)
                entry = StoreEntry(
                    id=r[0],
                    text=r[1],
                    metadata=json.loads(r[2]),
                    embedding=emb,
                    created_at=r[4],
                    updated_at=r[5],
                )
                scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def search_hybrid(self, query: str, limit: int = 10, alpha: float = 0.5) -> list[tuple[StoreEntry, float]]:
        keyword_results = dict(self.search_keyword(query, limit * 2))
        semantic_results = dict(self.search_semantic(query, limit * 2))

        combined: dict[str, tuple[StoreEntry, float]] = {}
        all_ids = set(keyword_results.keys()) | set(semantic_results.keys())

        for eid in all_ids:
            kw_score = keyword_results.get(eid, 0.0)
            sem_score = semantic_results.get(eid, 0.0)
            combined_score = alpha * sem_score + (1 - alpha) * kw_score
            entry = keyword_results.get(eid) or semantic_results[eid]
            combined[eid] = (entry, combined_score)

        sorted_results = sorted(combined.values(), key=lambda x: x[1], reverse=True)
        return sorted_results[:limit]

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()
            return row[0] if row else 0

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM entries")
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
