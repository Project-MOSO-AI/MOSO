from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class HardwareSummary:
    cpu_model: str
    cpu_architecture: str
    cpu_cores: int
    cpu_threads: int
    cpu_frequency_mhz: float
    gpu_model: str
    gpu_vram_mb: int
    motherboard: str
    ram_total_gb: float
    ram_form_factor: str
    os_version: str

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return (
            f"{self.cpu_model} ({self.cpu_cores}C/{self.cpu_threads}T), "
            f"{self.gpu_model or 'No discrete GPU'}, "
            f"{self.ram_total_gb:.1f} GB RAM, "
            f"{self.os_version}"
        )


@dataclass
class SoftwareEntry:
    name: str
    version: str
    publisher: str
    install_date: str
    install_location: str

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return f"{self.name} {self.version}"


@dataclass
class ServiceEntry:
    name: str
    display_name: str
    status: str
    start_type: str

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return f"{self.display_name} ({self.status})"


@dataclass
class NetworkConfig:
    adapters: list[dict]
    dns_servers: list[str]
    vpn_active: bool
    active_connections: int
    listening_ports: list[int]

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        adapters_str = ", ".join(a.get("name", "?") for a in self.adapters[:3])
        dns_str = ", ".join(self.dns_servers[:3])
        return (
            f"Adapters: {adapters_str} | "
            f"DNS: {dns_str} | "
            f"VPN: {'active' if self.vpn_active else 'inactive'} | "
            f"{self.active_connections} active connections"
        )


@dataclass
class SecurityStatus:
    firewall_enabled: bool
    firewall_profile: str
    antivirus_active: bool
    antivirus_name: str
    pending_updates: int
    suspicious_startup_entries: list[str]

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        parts = [
            f"Firewall: {'ON' if self.firewall_enabled else 'OFF'} ({self.firewall_profile})",
            f"Antivirus: {'Active' if self.antivirus_active else 'Inactive'} ({self.antivirus_name})",
            f"Pending updates: {self.pending_updates}",
        ]
        if self.suspicious_startup_entries:
            parts.append(f"Suspicious startups: {', '.join(self.suspicious_startup_entries)}")
        return " | ".join(parts)


@dataclass
class DiagnosticIssue:
    component: str
    issue: str
    severity: str
    explanation: str
    suggestion: str

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        sev_icon = {"critical": "CRIT", "warning": "WARN", "info": "INFO"}.get(self.severity, "INFO")
        return f"[{sev_icon}] {self.component}: {self.issue}"


@dataclass
class SystemSnapshot:
    timestamp: str
    hardware: HardwareSummary
    software: list[SoftwareEntry]
    services: list[ServiceEntry]
    network: NetworkConfig
    security: SecurityStatus

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["hardware"] = self.hardware.to_dict()
        d["software"] = [s.to_dict() for s in self.software]
        d["services"] = [s.to_dict() for s in self.services]
        d["network"] = self.network.to_dict()
        d["security"] = self.security.to_dict()
        return d


@dataclass
class InventoryDiff:
    timestamp: str
    new_software: list[SoftwareEntry]
    removed_software: list[SoftwareEntry]
    hardware_changed: bool
    hardware_before: Optional[HardwareSummary]
    hardware_after: Optional[HardwareSummary]
    new_services: list[ServiceEntry]
    removed_services: list[ServiceEntry]

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    def has_changes(self) -> bool:
        return bool(
            self.new_software or self.removed_software or self.hardware_changed
            or self.new_services or self.removed_services
        )

    def __str__(self) -> str:
        parts = []
        if self.hardware_changed:
            parts.append("Hardware changed")
        if self.new_software:
            parts.append(f"New apps ({len(self.new_software)})")
        if self.removed_software:
            parts.append(f"Removed apps ({len(self.removed_software)})")
        if self.new_services:
            parts.append(f"New services ({len(self.new_services)})")
        if self.removed_services:
            parts.append(f"Removed services ({len(self.removed_services)})")
        return ", ".join(parts) if parts else "No changes detected"
