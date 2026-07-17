"""Perception outcome log — closes the feedback loop for Eyes.

Every action's verify result gets stored here so the vision system
can learn from yesterday's mistakes instead of repeating them.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".moso", "perception_outcomes.db")


@dataclass
class PerceptionOutcome:
    id: Optional[int] = None
    timestamp: float = 0.0
    app_name: str = ""
    element_text: str = ""
    element_role: str = ""
    element_bbox: str = ""
    screenshot_hash: str = ""
    action_taken: str = ""
    action_params: str = ""
    success: int = 0
    verification_details: str = ""
    resolution: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "app_name": self.app_name,
            "element_text": self.element_text,
            "element_role": self.element_role,
            "element_bbox": self.element_bbox,
            "screenshot_hash": self.screenshot_hash,
            "action_taken": self.action_taken,
            "action_params": self.action_params,
            "success": self.success,
            "verification_details": self.verification_details,
            "resolution": self.resolution,
        }


def hash_region(image_path: str, bbox: tuple[int, int, int, int] | None = None) -> str:
    """Cheap perceptual fingerprint of a screenshot region."""
    if not image_path or not os.path.isfile(image_path):
        return ""
    try:
        from PIL import Image
        img = Image.open(image_path)
        if bbox:
            x, y, w, h = bbox
            img = img.crop((x, y, x + w, y + h))
        # Resize to tiny thumbnail for stable hash
        img = img.resize((16, 16)).convert("L")
        h = hashlib.sha256(img.tobytes()).hexdigest()[:16]
        img.close()
        return h
    except Exception:
        return ""


class PerceptionLog:
    """SQLite log of perception-action-verification outcomes."""

    def __init__(self, db_path: str | Path = _DEFAULT_DB):
        self._db_path = Path(db_path)
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS perception_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                app_name TEXT DEFAULT '',
                element_text TEXT DEFAULT '',
                element_role TEXT DEFAULT '',
                element_bbox TEXT DEFAULT '',
                screenshot_hash TEXT DEFAULT '',
                action_taken TEXT DEFAULT '',
                action_params TEXT DEFAULT '',
                success INTEGER DEFAULT 0,
                verification_details TEXT DEFAULT '',
                resolution TEXT DEFAULT ''
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_app_element
            ON perception_outcomes(app_name, element_text)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON perception_outcomes(timestamp)
        """)
        self._conn.commit()

    def log_outcome(
        self,
        app_name: str = "",
        element_text: str = "",
        element_role: str = "",
        element_bbox: tuple[int, int, int, int] | None = None,
        screenshot_path: str = "",
        action_taken: str = "",
        action_params: dict | None = None,
        success: bool = False,
        verification_details: str = "",
        resolution: tuple[int, int] = (0, 0),
    ) -> int:
        bbox_str = json.dumps({"x": element_bbox[0], "y": element_bbox[1],
                                "w": element_bbox[2], "h": element_bbox[3]}) if element_bbox else ""
        screenshot_hash = hash_region(screenshot_path, element_bbox) if screenshot_path else ""

        outcome = PerceptionOutcome(
            timestamp=time.time(),
            app_name=app_name,
            element_text=element_text,
            element_role=element_role,
            element_bbox=bbox_str,
            screenshot_hash=screenshot_hash,
            action_taken=action_taken,
            action_params=json.dumps(action_params or {}),
            success=1 if success else 0,
            verification_details=verification_details,
            resolution=f"{resolution[0]}x{resolution[1]}",
        )

        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO perception_outcomes
                   (timestamp, app_name, element_text, element_role, element_bbox,
                    screenshot_hash, action_taken, action_params, success,
                    verification_details, resolution)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (outcome.timestamp, outcome.app_name, outcome.element_text,
                 outcome.element_role, outcome.element_bbox, outcome.screenshot_hash,
                 outcome.action_taken, outcome.action_params, outcome.success,
                 outcome.verification_details, outcome.resolution),
            )
            self._conn.commit()
            return cur.lastrowid or 0

    def get_outcomes(
        self,
        app_name: str = "",
        element_role: str = "",
        limit: int = 100,
    ) -> list[PerceptionOutcome]:
        clauses = []
        params: list = []
        if app_name:
            clauses.append("app_name = ?")
            params.append(app_name)
        if element_role:
            clauses.append("element_role = ?")
            params.append(element_role)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

        with self._lock:
            rows = self._conn.execute(
                f"SELECT id, timestamp, app_name, element_text, element_role, "
                f"element_bbox, screenshot_hash, action_taken, action_params, "
                f"success, verification_details, resolution "
                f"FROM perception_outcomes{where} ORDER BY timestamp DESC LIMIT ?",
                params + [limit],
            ).fetchall()
        return [
            PerceptionOutcome(id=r[0], timestamp=r[1], app_name=r[2],
                              element_text=r[3], element_role=r[4],
                              element_bbox=r[5], screenshot_hash=r[6],
                              action_taken=r[7], action_params=r[8],
                              success=r[9], verification_details=r[10],
                              resolution=r[11])
            for r in rows
        ]

    def get_confidence(self, app_name: str, element_text: str) -> float:
        """Success rate for a specific element in a specific app. 0.0–1.0."""
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*), SUM(success) FROM perception_outcomes "
                "WHERE app_name = ? AND element_text = ?",
                (app_name, element_text),
            ).fetchone()
        if not row or not row[0]:
            return 0.0
        return (row[1] or 0) / row[0]

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM perception_outcomes").fetchone()
            return row[0] if row else 0

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
