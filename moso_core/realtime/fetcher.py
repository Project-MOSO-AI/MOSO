"""Offline-only fetcher stub — no network calls, no APIs."""
from __future__ import annotations

import logging
import time
from typing import Optional

from moso_core.realtime.models import FetchResult
from moso_core.realtime.sources import SourceDefinition

logger = logging.getLogger(__name__)


class Fetcher:
    """Stub fetcher that always returns offline results."""

    async def fetch_url(
        self,
        url: str,
        source_name: str = "",
        tls_verify: bool = True,
    ) -> FetchResult:
        return FetchResult(
            url=url,
            source_name=source_name or url,
            raw_text="",
            parsed_text="[offline] Network disabled — no external API calls.",
            status_code=0,
            error="offline",
        )

    async def fetch_multiple(
        self,
        urls: list[str],
        source_names: Optional[list[str]] = None,
    ) -> list[FetchResult]:
        return [
            await self.fetch_url(url, source_name=source_names[i] if source_names and i < len(source_names) else "")
            for i, url in enumerate(urls)
        ]

    async def fetch_by_source(
        self,
        sources: list[SourceDefinition],
        use_cache: bool = True,
        cache=None,
        ttl_override: Optional[int] = None,
    ) -> list[FetchResult]:
        results = []
        for src in sources:
            if use_cache and cache:
                cached = cache.get(src.url)
                if cached is not None:
                    results.append(cached)
                    continue
            results.append(FetchResult(
                url=src.url,
                source_name=src.name,
                raw_text="",
                parsed_text="[offline] Network disabled.",
                status_code=0,
                error="offline",
            ))
        return results

    async def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
