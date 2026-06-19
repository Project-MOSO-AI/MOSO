from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class CPUStatus:
    usage_percent: float
    cores: int
    threads: int
    frequency: float
    temperature: Optional[float] = None
    per_cpu: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def unavailable(cls) -> CPUStatus:
        return cls(usage_percent=0.0, cores=0, threads=0, frequency=0.0)


@dataclass
class RAMStatus:
    total: int
    available: int
    used: int
    percent: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def unavailable(cls) -> RAMStatus:
        return cls(total=0, available=0, used=0, percent=0.0)


@dataclass
class StorageStatus:
    mount_point: str
    total: int
    used: int
    free: int
    percent: float
    filesystem: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BatteryStatus:
    plugged_in: bool
    percent: float
    time_remaining: Optional[float] = None
    power_plugged: Optional[bool] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def desktop(cls) -> BatteryStatus:
        return cls(plugged_in=True, percent=100.0, power_plugged=True)


@dataclass
class NetworkStatus:
    bytes_sent: int
    bytes_recv: int
    upload_speed: Optional[float] = None
    download_speed: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def empty(cls) -> NetworkStatus:
        return cls(bytes_sent=0, bytes_recv=0)


@dataclass
class ProcessInfo:
    name: str
    pid: int
    cpu_percent: float
    memory_percent: float
    memory_rss: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SystemStatus:
    cpu: CPUStatus
    ram: RAMStatus
    storage: list[StorageStatus]
    battery: Optional[BatteryStatus]
    network: NetworkStatus
    top_cpu_processes: list[ProcessInfo] = field(default_factory=list)
    top_memory_processes: list[ProcessInfo] = field(default_factory=list)
    gpu: Optional[None] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["top_cpu_processes"] = [p.to_dict() for p in self.top_cpu_processes]
        d["top_memory_processes"] = [p.to_dict() for p in self.top_memory_processes]
        d["storage"] = [s.to_dict() for s in self.storage]
        return d

    def summary(self) -> str:
        parts = [f"CPU: {self.cpu.usage_percent:.0f}% ({self.cpu.cores}C/{self.cpu.threads}T)"]
        parts.append(f"RAM: {self._fmt_bytes(self.ram.used)}/{self._fmt_bytes(self.ram.total)} ({self.ram.percent:.0f}%)")
        if self.storage:
            primary = self.storage[0]
            parts.append(f"Storage: {primary.free / (1024**3):.1f}GB free ({100 - primary.percent:.0f}% free)")
        if self.battery:
            parts.append(f"Battery: {self.battery.percent:.0f}%{' (plugged)' if self.battery.plugged_in else ''}")
        parts.append(f"Network: ↑{self._fmt_speed(self.network.upload_speed)} ↓{self._fmt_speed(self.network.download_speed)}")
        return " | ".join(parts)

    @staticmethod
    def _fmt_bytes(b: int) -> str:
        if b >= 1024**3:
            return f"{b / 1024**3:.1f}GB"
        if b >= 1024**2:
            return f"{b / 1024**2:.1f}MB"
        return f"{b / 1024:.0f}KB"

    @staticmethod
    def _fmt_speed(speed: Optional[float]) -> str:
        if speed is None:
            return "N/A"
        if speed >= 1024**2:
            return f"{speed / 1024**2:.1f}MB/s"
        if speed >= 1024:
            return f"{speed / 1024:.0f}KB/s"
        return f"{speed:.0f}B/s"
