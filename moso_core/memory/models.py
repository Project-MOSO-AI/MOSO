from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class EpisodicMemory:
    title: str
    description: str
    timestamp: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    owner_id: str = "default"
    importance: float = 0.5
    memory_id: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = json.dumps(self.tags) if isinstance(self.tags, list) else self.tags
        return d

    @classmethod
    def from_row(cls, row: dict) -> EpisodicMemory:
        tags = row.get("tags", "[]")
        if isinstance(tags, str):
            tags = json.loads(tags) if tags else []
        return cls(
            memory_id=row["id"],
            title=row["title"],
            description=row.get("description", ""),
            timestamp=row.get("timestamp"),
            tags=tags,
            owner_id=row.get("owner_id", "default"),
            importance=row.get("importance", 0.5),
            created_at=row.get("created_at"),
        )


@dataclass
class SemanticMemory:
    fact: str
    confidence: float = 1.0
    category: str = "general"
    source: str = "conversation"
    owner_id: str = "default"
    memory_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row: dict) -> SemanticMemory:
        return cls(
            memory_id=row["id"],
            fact=row["fact"],
            confidence=row.get("confidence", 1.0),
            category=row.get("category", "general"),
            source=row.get("source", "conversation"),
            owner_id=row.get("owner_id", "default"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )


@dataclass
class ProceduralMemory:
    task_name: str
    steps: list[dict] = field(default_factory=list)
    app_category: str = "other"
    app_name: str = "unknown"
    trigger_phrases: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    times_used: int = 0
    last_used: Optional[str] = None
    owner_id: str = "default"
    tags: list[str] = field(default_factory=list)
    memory_id: Optional[int] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["steps"] = json.dumps(self.steps) if isinstance(self.steps, list) else self.steps
        d["tags"] = json.dumps(self.tags) if isinstance(self.tags, list) else self.tags
        d["trigger_phrases"] = json.dumps(self.trigger_phrases) if isinstance(self.trigger_phrases, list) else self.trigger_phrases
        d["variables"] = json.dumps(self.variables) if isinstance(self.variables, list) else self.variables
        return d

    @classmethod
    def from_row(cls, row: dict) -> ProceduralMemory:
        def _parse_list(val):
            if isinstance(val, str):
                return json.loads(val) if val else []
            return val or []
        return cls(
            memory_id=row["id"],
            task_name=row["task_name"],
            steps=_parse_list(row.get("steps", "[]")),
            app_category=row.get("app_category", "other"),
            app_name=row.get("app_name", "unknown"),
            trigger_phrases=_parse_list(row.get("trigger_phrases", "[]")),
            variables=_parse_list(row.get("variables", "[]")),
            success_count=row.get("success_count", 0),
            failure_count=row.get("failure_count", 0),
            success_rate=row.get("success_rate", 0.0),
            times_used=row.get("times_used", 0),
            last_used=row.get("last_used"),
            owner_id=row.get("owner_id", "default"),
            tags=_parse_list(row.get("tags", "[]")),
        )


@dataclass
class PreferenceMemory:
    category: str
    value: str
    confidence: float = 1.0
    owner_id: str = "default"
    memory_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row: dict) -> PreferenceMemory:
        return cls(
            memory_id=row["id"],
            category=row["category"],
            value=row["value"],
            confidence=row.get("confidence", 1.0),
            owner_id=row.get("owner_id", "default"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
