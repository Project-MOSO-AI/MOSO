from __future__ import annotations

from typing import Optional

from moso_core.memory.models import (
    EpisodicMemory,
    PreferenceMemory,
    ProceduralMemory,
    SemanticMemory,
)


class MemoryRetriever:
    def __init__(self, episodic, semantic, procedural, preferences):
        self._episodic = episodic
        self._semantic = semantic
        self._procedural = procedural
        self._preferences = preferences

    def search_all(
        self,
        query: str,
        owner_id: Optional[str] = None,
        limit: int = 5,
    ) -> dict[str, list]:
        return {
            "episodic": self._episodic.search(query, owner_id=owner_id, limit=limit),
            "semantic": self._semantic.search(query, owner_id=owner_id, limit=limit),
            "procedural": self._procedural.search(query, owner_id=owner_id, limit=limit),
        }

    def search_types(
        self,
        query: str,
        types: list[str],
        owner_id: Optional[str] = None,
        limit: int = 5,
    ) -> dict[str, list]:
        results: dict[str, list] = {}
        if "episodic" in types:
            results["episodic"] = self._episodic.search(query, owner_id=owner_id, limit=limit)
        if "semantic" in types:
            results["semantic"] = self._semantic.search(query, owner_id=owner_id, limit=limit)
        if "procedural" in types:
            results["procedural"] = self._procedural.search(query, owner_id=owner_id, limit=limit)
        if "preferences" in types:
            prefs = self._preferences.list_all(owner_id or "default")
            results["preferences"] = [
                p for p in prefs if query.lower() in p.category.lower() or query.lower() in p.value.lower()
            ]
        return results

    def recent_all(
        self,
        owner_id: Optional[str] = None,
        limit: int = 5,
    ) -> dict[str, list]:
        return {
            "episodic": self._episodic.list_recent(owner_id=owner_id, limit=limit),
            "semantic": self._semantic.list_recent(owner_id=owner_id, limit=limit),
        }

    def build_context(
        self,
        query: str,
        owner_id: Optional[str] = None,
        max_events: int = 3,
        max_facts: int = 5,
        max_procedures: int = 3,
    ) -> str:
        parts: list[str] = []

        events = self._episodic.search(query, owner_id=owner_id, limit=max_events)
        if events:
            parts.append("## Recent Events")
            for e in events:
                parts.append(f"- {e.title} ({e.timestamp}): {e.description[:120]}")

        facts = self._semantic.search(query, owner_id=owner_id, limit=max_facts)
        if facts:
            parts.append("## Known Facts")
            for f in facts:
                parts.append(f"- {f.fact} (confidence: {f.confidence:.0%})")

        procedures = self._procedural.search(query, owner_id=owner_id, limit=max_procedures)
        if procedures:
            parts.append("## Known Procedures")
            for p in procedures:
                parts.append(f"- {p.task_name} (used {p.times_used}x, {p.success_rate:.0%} success)")

        if owner_id:
            prefs = self._preferences.list_all(owner_id)
            if prefs:
                parts.append("## Preferences")
                for p in prefs:
                    parts.append(f"- {p.category}: {p.value}")

        return "\n".join(parts)
