from __future__ import annotations

import logging
from typing import Optional

from moso_core.resources.models import CPUStatus

logger = logging.getLogger(__name__)


class CPUMonitor:
    def get_usage(self, interval: float = 0.1) -> CPUStatus:
        import psutil

        usage = psutil.cpu_percent(interval=interval)
        per_cpu = psutil.cpu_percent(interval=0, percpu=True)
        count = psutil.cpu_count()
        logical = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        frequency = freq.current if freq else 0.0
        temperature = self._get_temperature()

        return CPUStatus(
            usage_percent=usage,
            cores=count or 0,
            threads=logical or 0,
            frequency=frequency,
            temperature=temperature,
            per_cpu=per_cpu,
        )

    def get_count(self) -> int:
        import psutil

        return psutil.cpu_count() or 0

    def get_threads(self) -> int:
        import psutil

        return psutil.cpu_count(logical=True) or 0

    def get_frequency(self) -> float:
        import psutil

        freq = psutil.cpu_freq()
        return freq.current if freq else 0.0

    def get_temperature(self) -> Optional[float]:
        return self._get_temperature()

    @staticmethod
    def _get_temperature() -> Optional[float]:
        import psutil

        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return None
            for name, entries in temps.items():
                if entries:
                    return entries[0].current
        except Exception:
            pass
        return None
