from __future__ import annotations

import logging
from typing import Optional

from moso_core.resources.models import ProcessInfo

logger = logging.getLogger(__name__)


class ProcessMonitor:
    def get_all(self) -> list[ProcessInfo]:
        import psutil

        results: list[ProcessInfo] = []
        for proc in psutil.process_iter(["name", "pid", "cpu_percent", "memory_percent", "memory_info"]):
            try:
                info = proc.info
                results.append(ProcessInfo(
                    name=info["name"] or "unknown",
                    pid=info["pid"],
                    cpu_percent=info["cpu_percent"] or 0.0,
                    memory_percent=info["memory_percent"] or 0.0,
                    memory_rss=getattr(info.get("memory_info"), "rss", 0) or 0,
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results

    def top_cpu(self, n: int = 5) -> list[ProcessInfo]:
        all_procs = self.get_all()
        all_procs.sort(key=lambda p: p.cpu_percent, reverse=True)
        return all_procs[:n]

    def top_memory(self, n: int = 5) -> list[ProcessInfo]:
        all_procs = self.get_all()
        all_procs.sort(key=lambda p: p.memory_percent, reverse=True)
        return all_procs[:n]

    def find_by_name(self, name: str) -> list[ProcessInfo]:
        import psutil

        results: list[ProcessInfo] = []
        for proc in psutil.process_iter(["name", "pid", "cpu_percent", "memory_percent", "memory_info"]):
            try:
                info = proc.info
                if info["name"] and name.lower() in info["name"].lower():
                    results.append(ProcessInfo(
                        name=info["name"],
                        pid=info["pid"],
                        cpu_percent=info["cpu_percent"] or 0.0,
                        memory_percent=info["memory_percent"] or 0.0,
                        memory_rss=getattr(info.get("memory_info"), "rss", 0) or 0,
                    ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results
