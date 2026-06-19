from __future__ import annotations

import logging
import time
from typing import Optional

from moso_core.resources.models import NetworkStatus

logger = logging.getLogger(__name__)


class NetworkMonitor:
    def __init__(self):
        self._last_counters: Optional[tuple] = None
        self._last_time: Optional[float] = None

    def get_usage(self) -> NetworkStatus:
        import psutil

        counters = psutil.net_io_counters()
        now = time.time()
        sent = counters.bytes_sent
        recv = counters.bytes_recv

        upload_speed: Optional[float] = None
        download_speed: Optional[float] = None

        if self._last_counters is not None and self._last_time is not None:
            elapsed = now - self._last_time
            if elapsed > 0:
                last_sent, last_recv = self._last_counters
                upload_speed = max(0, (sent - last_sent) / elapsed)
                download_speed = max(0, (recv - last_recv) / elapsed)

        self._last_counters = (sent, recv)
        self._last_time = now

        return NetworkStatus(
            bytes_sent=sent,
            bytes_recv=recv,
            upload_speed=upload_speed,
            download_speed=download_speed,
        )
