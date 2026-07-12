"""Runtime manager — service lifecycle, health monitoring, crash recovery."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    CRASHED = "crashed"
    RESTARTING = "restarting"


@dataclass
class ServiceInfo:
    name: str
    status: ServiceStatus = ServiceStatus.STOPPED
    started_at: float = 0.0
    last_heartbeat: float = 0.0
    restart_count: int = 0
    last_error: str = ""
    health_check_interval: float = 10.0

    @property
    def uptime(self) -> float:
        if self.started_at == 0 or self.status != ServiceStatus.RUNNING:
            return 0.0
        return time.time() - self.started_at

    @property
    def healthy(self) -> bool:
        if self.status != ServiceStatus.RUNNING:
            return False
        if self.health_check_interval > 0 and self.last_heartbeat > 0:
            return (time.time() - self.last_heartbeat) < self.health_check_interval * 3
        return True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "uptime": round(self.uptime, 1),
            "restarts": self.restart_count,
            "healthy": self.healthy,
            "last_error": self.last_error[:200],
        }


class Service:
    """Base service to subclass for actual work."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def start(self):
        pass

    def stop(self):
        pass

    def health_check(self) -> bool:
        return True


class RuntimeManager:
    def __init__(self, max_restarts: int = 3, restart_window: float = 300.0):
        self._services: dict[str, Service] = {}
        self._info: dict[str, ServiceInfo] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._max_restarts = max_restarts
        self._restart_window = restart_window
        self._callbacks: list[Callable[[str, ServiceStatus, ServiceStatus], None]] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False

    def add_callback(self, cb: Callable[[str, ServiceStatus, ServiceStatus], None]):
        self._callbacks.append(cb)

    def _notify(self, name: str, old: ServiceStatus, new: ServiceStatus):
        self._info[name].status = new
        for cb in self._callbacks:
            try:
                cb(name, old, new)
            except Exception:
                pass

    def register(self, service: Service, health_interval: float = 10.0):
        self._services[service.name] = service
        self._info[service.name] = ServiceInfo(
            name=service.name, health_check_interval=health_interval,
        )

    def start(self, name: str) -> bool:
        service = self._services.get(name)
        info = self._info.get(name)
        if not service or not info:
            logger.warning("Unknown service: %s", name)
            return False

        with self._lock:
            if info.status == ServiceStatus.RUNNING:
                return True
            self._notify(name, info.status, ServiceStatus.STARTING)

        try:
            service.start()
            with self._lock:
                info.started_at = time.time()
                info.last_heartbeat = time.time()
                info.last_error = ""
                self._notify(name, ServiceStatus.STARTING, ServiceStatus.RUNNING)
            logger.info("Service started: %s", name)
            return True
        except Exception as e:
            with self._lock:
                info.last_error = str(e)
                self._notify(name, ServiceStatus.STARTING, ServiceStatus.CRASHED)
            logger.error("Service start failed: %s — %s", name, e)
            return False

    def stop(self, name: str) -> bool:
        service = self._services.get(name)
        info = self._info.get(name)
        if not service or not info:
            return False

        with self._lock:
            if info.status == ServiceStatus.STOPPED:
                return True
            self._notify(name, info.status, ServiceStatus.STOPPING)

        try:
            service.stop()
            with self._lock:
                info.status = ServiceStatus.STOPPED
                info.started_at = 0
            logger.info("Service stopped: %s", name)
            return True
        except Exception as e:
            with self._lock:
                info.last_error = str(e)
            logger.error("Service stop failed: %s — %s", name, e)
            return False

    def restart(self, name: str) -> bool:
        info = self._info.get(name)
        if not info:
            return False

        with self._lock:
            # Check restart rate
            now = time.time()
            if info.restart_count >= self._max_restarts:
                # Reset if outside the window
                if info.started_at > 0 and (now - info.started_at) > self._restart_window:
                    info.restart_count = 0
                else:
                    logger.warning("Service %s exceeded max restarts (%d)", name, self._max_restarts)
                    info.last_error = f"Exceeded max restarts ({self._max_restarts})"
                    return False
            info.restart_count += 1
            self._notify(name, info.status, ServiceStatus.RESTARTING)

        self.stop(name)
        time.sleep(0.5)
        return self.start(name)

    def start_all(self):
        for name in self._services:
            self.start(name)

    def stop_all(self):
        for name in reversed(list(self._services.keys())):
            self.stop(name)

    def start_monitoring(self, interval: float = 5.0):
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(interval,), daemon=True,
            name="moso_runtime_monitor",
        )
        self._monitor_thread.start()

    def stop_monitoring(self):
        self._monitoring = False

    def _monitor_loop(self, interval: float):
        while self._monitoring:
            with self._lock:
                for name, service in self._services.items():
                    info = self._info[name]
                    if info.status != ServiceStatus.RUNNING:
                        continue
                    try:
                        if service.health_check():
                            info.last_heartbeat = time.time()
                        else:
                            logger.warning("Service %s failed health check", name)
                            info.last_error = "Health check failed"
                            self._notify(name, ServiceStatus.RUNNING, ServiceStatus.CRASHED)
                    except Exception as e:
                        logger.warning("Service %s health check error: %s", name, e)
                        info.last_error = str(e)
                        self._notify(name, ServiceStatus.RUNNING, ServiceStatus.CRASHED)

                    # Auto-restart crashed services
                    if info.status == ServiceStatus.CRASHED:
                        logger.info("Auto-restarting crashed service: %s", name)
                        threading.Thread(
                            target=self.restart, args=(name,), daemon=True,
                        ).start()
            time.sleep(interval)

    def get_info(self, name: str) -> Optional[ServiceInfo]:
        return self._info.get(name)

    def all_info(self) -> list[dict]:
        return [info.to_dict() for info in self._info.values()]

    def summary(self) -> str:
        lines = []
        for info in self._info.values():
            icon = {
                ServiceStatus.RUNNING: "[RUN]",
                ServiceStatus.STOPPED: "[---]",
                ServiceStatus.CRASHED: "[!!!]",
                ServiceStatus.STARTING: "[...]",
                ServiceStatus.STOPPING: "[...]",
                ServiceStatus.RESTARTING: "[!!!]",
            }[info.status]
            line = f"  {icon} {info.name}"
            if info.status == ServiceStatus.RUNNING:
                line += f" ({info.uptime:.0f}s uptime)"
            if info.last_error:
                line += f" — {info.last_error[:60]}"
            lines.append(line)
        return "\n".join(lines) if lines else "No services registered."

    def __enter__(self):
        self.start_all()
        self.start_monitoring()
        return self

    def __exit__(self, *args):
        self.stop_monitoring()
        self.stop_all()
