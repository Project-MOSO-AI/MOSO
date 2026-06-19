from __future__ import annotations

import logging

from moso_core.resources.models import RAMStatus

logger = logging.getLogger(__name__)


class RAMMonitor:
    def get_usage(self) -> RAMStatus:
        import psutil

        mem = psutil.virtual_memory()
        return RAMStatus(
            total=mem.total,
            available=mem.available,
            used=mem.used,
            percent=mem.percent,
        )
