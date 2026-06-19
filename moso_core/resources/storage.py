from __future__ import annotations

import logging
from typing import Optional

from moso_core.resources.models import StorageStatus

logger = logging.getLogger(__name__)


class StorageMonitor:
    def __init__(self, include_paths: Optional[list[str]] = None):
        self._include_paths = include_paths

    def get_usage(self) -> list[StorageStatus]:
        import psutil

        results: list[StorageStatus] = []
        partitions = psutil.disk_partitions()

        for part in partitions:
            if self._include_paths and part.mountpoint not in self._include_paths:
                continue
            if self._is_pseudo_fs(part.fstype):
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                results.append(StorageStatus(
                    mount_point=part.mountpoint,
                    total=usage.total,
                    used=usage.used,
                    free=usage.free,
                    percent=usage.percent,
                    filesystem=part.fstype,
                ))
            except PermissionError:
                continue

        return results

    def get_usage_for(self, path: str) -> Optional[StorageStatus]:
        import psutil

        try:
            usage = psutil.disk_usage(path)
            return StorageStatus(
                mount_point=path,
                total=usage.total,
                used=usage.used,
                free=usage.free,
                percent=usage.percent,
            )
        except (PermissionError, FileNotFoundError):
            return None

    @staticmethod
    def _is_pseudo_fs(fstype: str) -> bool:
        pseudo = {"tmpfs", "devtmpfs", "squashfs", "overlay", "proc", "sysfs", "cgroup", "cgroup2", "devpts", "none", "autofs"}
        return fstype.lower() in pseudo or fstype == ""
