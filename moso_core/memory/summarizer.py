from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from moso_core.memory.models import EpisodicMemory, SemanticMemory

logger = logging.getLogger(__name__)


class MemorySummarizer:
    def __init__(self, episodic, semantic):
        self._episodic = episodic
        self._semantic = semantic

    def extract_facts_from_events(
        self,
        owner_id: str = "default",
        max_age_days: int = 30,
        min_importance: float = 0.3,
        max_per_batch: int = 20,
    ) -> list[SemanticMemory]:
        events = self._episodic.list_recent(limit=100, owner_id=owner_id)
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        new_facts: list[SemanticMemory] = []

        for event in events:
            if event.importance < min_importance:
                continue
            event_time = event.timestamp
            if event_time:
                try:
                    et = datetime.fromisoformat(event_time)
                    if et < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass

            facts = self._derive_facts(event)
            new_facts.extend(facts)

            if len(new_facts) >= max_per_batch:
                break

        stored = 0
        for fact in new_facts:
            existing = self._semantic.search(fact.fact[:40], owner_id=owner_id, limit=1)
            if not existing:
                fact.owner_id = owner_id
                self._semantic.store(fact)
                stored += 1

        if stored:
            logger.info("Summarizer extracted %d new facts from %d events", stored, len(new_facts))
        return new_facts[:stored] if stored else []

    def _derive_facts(self, event: EpisodicMemory) -> list[SemanticMemory]:
        facts: list[SemanticMemory] = []
        title_lower = event.title.lower()
        desc_lower = event.description.lower()

        if "created" in title_lower or "built" in title_lower or "made" in title_lower:
            obj = event.title.replace("Created", "").replace("Built", "").replace("Made", "").strip()
            if obj:
                facts.append(SemanticMemory(
                    fact=f"Owner has created {obj}",
                    confidence=0.7,
                    category="project",
                    source="summarized",
                ))

        if "installed" in title_lower:
            tool = event.title.replace("Installed", "").strip()
            if tool:
                facts.append(SemanticMemory(
                    fact=f"Owner uses {tool}",
                    confidence=0.8,
                    category="tool",
                    source="summarized",
                ))

        if "prefer" in desc_lower or "like" in desc_lower or "favorite" in desc_lower:
            facts.append(SemanticMemory(
                fact=f"Owner expressed preference: {event.description[:200]}",
                confidence=0.5,
                category="preference",
                source="summarized",
            ))

        return facts

    def summarize_events_to_text(
        self,
        owner_id: str = "default",
        max_events: int = 20,
    ) -> str:
        events = self._episodic.list_recent(limit=max_events, owner_id=owner_id)
        if not events:
            return ""

        lines: list[str] = ["## Recent Activity Summary"]
        for e in events:
            tag_str = f" [{', '.join(e.tags)}]" if e.tags else ""
            lines.append(f"- {e.title}{tag_str} ({e.timestamp})")

        return "\n".join(lines)

    def get_stats(
        self,
        owner_id: str = "default",
    ) -> dict:
        recent_events = self._episodic.list_recent(limit=5, owner_id=owner_id)
        recent_facts = self._semantic.list_recent(limit=5, owner_id=owner_id)
        return {
            "total_events": self._episodic.count(owner_id),
            "total_facts": self._semantic.count(owner_id),
            "recent_events": [e.title for e in recent_events],
            "recent_facts": [f.fact[:80] for f in recent_facts],
        }
