from __future__ import annotations

import logging
import os
import subprocess
from typing import Optional

from moso_core.resources.models import StorageStatus

logger = logging.getLogger(__name__)


class StorageIntelligence:
    def get_storage_details(self) -> list[StorageStatus]:
        try:
            from moso_core.resources.storage import StorageMonitor
            monitor = StorageMonitor()
            return monitor.get_usage()
        except Exception as e:
            logger.warning("Storage detail query failed: %s", e)
            return []

    def find_large_files(self, path: str = "C:\\", min_mb: int = 100, top_n: int = 20) -> list[dict]:
        large_files = []
        try:
            for root, dirs, files in os.walk(path):
                for name in files:
                    try:
                        filepath = os.path.join(root, name)
                        try:
                            size = os.path.getsize(filepath)
                        except (OSError, PermissionError):
                            continue
                        if size >= min_mb * 1024 * 1024:
                            large_files.append({
                                "path": filepath,
                                "size_mb": round(size / (1024 * 1024), 1),
                                "size_bytes": size,
                            })
                            if len(large_files) >= top_n:
                                return large_files
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError) as e:
            logger.debug("Large file scan failed for %s: %s", path, e)
        return large_files

    def find_large_folders(self, path: str = "C:\\", top_n: int = 20) -> list[dict]:
        folders = []
        try:
            for name in os.listdir(path):
                try:
                    folder_path = os.path.join(path, name)
                    if not os.path.isdir(folder_path):
                        continue
                    total = 0
                    count = 0
                    for root, dirs, files in os.walk(folder_path):
                        for fname in files:
                            try:
                                total += os.path.getsize(os.path.join(root, fname))
                                count += 1
                            except (OSError, PermissionError):
                                continue
                    if count > 0:
                        folders.append({
                            "path": folder_path,
                            "size_mb": round(total / (1024 * 1024), 1),
                            "size_bytes": total,
                            "file_count": count,
                        })
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError) as e:
            logger.debug("Large folder scan failed for %s: %s", path, e)
        folders.sort(key=lambda f: f["size_bytes"], reverse=True)
        return folders[:top_n]

    def get_drive_health(self) -> list[dict]:
        drives = []
        try:
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "model,size,status"],
                capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().splitlines()
                if len(lines) >= 2:
                    header = lines[0].strip()
                    for line in lines[1:]:
                        if line.strip():
                            parts = line.strip().split(None, 2)
                            if len(parts) >= 2:
                                model = parts[0]
                                size_str = parts[1] if len(parts) > 1 else "0"
                                status = parts[2] if len(parts) > 2 else "Unknown"
                                try:
                                    size_gb = round(int(size_str) / (1024 ** 3), 1) if size_str.isdigit() else 0
                                except (ValueError, OverflowError):
                                    size_gb = 0
                                drives.append({
                                    "model": model,
                                    "size_gb": size_gb,
                                    "status": status,
                                })
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("WMIC diskdrive query failed: %s", e)

        if not drives:
            try:
                import psutil
                for part in psutil.disk_partitions():
                    drives.append({
                        "model": part.device,
                        "size_gb": 0,
                        "status": "Unknown",
                    })
            except Exception as e:
                logger.debug("psutil disk fallback failed: %s", e)

        return drives
