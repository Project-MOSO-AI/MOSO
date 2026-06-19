from __future__ import annotations

import logging
from typing import Optional

from moso_core.resources.models import BatteryStatus

logger = logging.getLogger(__name__)


class BatteryMonitor:
    def get_status(self) -> BatteryStatus:
        import psutil

        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return BatteryStatus.desktop()
            return BatteryStatus(
                plugged_in=battery.power_plugged or False,
                percent=battery.percent,
                time_remaining=battery.secsleft if battery.secsleft is not None and battery.secsleft >= 0 else None,
                power_plugged=battery.power_plugged,
            )
        except Exception:
            return BatteryStatus.desktop()
