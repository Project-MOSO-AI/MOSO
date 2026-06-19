from __future__ import annotations

import logging
from typing import Any, Optional

from moso_core.system_intelligence.diagnostics import DiagnosticsEngine
from moso_core.system_intelligence.explainer import ExplainerEngine
from moso_core.system_intelligence.hardware import HardwareIntelligence
from moso_core.system_intelligence.inventory import InventoryEngine
from moso_core.system_intelligence.models import (
    DiagnosticIssue,
    HardwareSummary,
    InventoryDiff,
    NetworkConfig,
    SecurityStatus,
    SoftwareEntry,
    SystemSnapshot,
)
from moso_core.system_intelligence.network import NetworkIntelligence
from moso_core.system_intelligence.security import SecurityIntelligence
from moso_core.system_intelligence.software import SoftwareIntelligence
from moso_core.system_intelligence.storage import StorageIntelligence

logger = logging.getLogger(__name__)


class SystemIntelligenceManager:
    def __init__(
        self,
        identity: Any = None,
        memory: Any = None,
        resources: Any = None,
    ):
        self._identity = identity
        self._memory = memory
        self._resources = resources

        self._hardware = HardwareIntelligence()
        self._software = SoftwareIntelligence()
        self._network = NetworkIntelligence()
        self._storage = StorageIntelligence()
        self._security = SecurityIntelligence()

        self._diagnostics = DiagnosticsEngine(
            hardware=self._hardware,
            software=self._software,
            network=self._network,
            storage=self._storage,
            security=self._security,
            resources=self._resources,
        )

        self._inventory = InventoryEngine(
            hardware=self._hardware,
            software=self._software,
            network=self._network,
            security=self._security,
        )

        self._explainer = ExplainerEngine(
            hardware=self._hardware,
            software=self._software,
            network=self._network,
            storage=self._storage,
            security=self._security,
            resources=self._resources,
        )

        logger.info("System intelligence engine enabled")

    @property
    def hardware(self) -> HardwareIntelligence:
        return self._hardware

    @property
    def software(self) -> SoftwareIntelligence:
        return self._software

    @property
    def network(self) -> NetworkIntelligence:
        return self._network

    @property
    def storage(self) -> StorageIntelligence:
        return self._storage

    @property
    def security(self) -> SecurityIntelligence:
        return self._security

    @property
    def diagnostics(self) -> DiagnosticsEngine:
        return self._diagnostics

    @property
    def inventory(self) -> InventoryEngine:
        return self._inventory

    @property
    def explainer(self) -> ExplainerEngine:
        return self._explainer

    def _check_permission(self, level: str = "guest") -> tuple[bool, str]:
        if self._identity is None:
            return True, ""
        try:
            identity_level = self._identity.get_identity_level() if hasattr(self._identity, "get_identity_level") else "guest"
            levels = {"guest": 0, "trusted": 1, "owner": 2}
            required = levels.get(level, 0)
            actual = levels.get(identity_level, 0)
            if actual < required:
                return False, f"Permission denied: requires {level}, current level is {identity_level}"
            return True, ""
        except Exception as e:
            logger.warning("Permission check failed: %s", e)
            return False, f"Permission check failed: {e}"

    def _check_resources(self) -> bool:
        if self._resources is None:
            return True
        try:
            status = self._resources.get_system_status()
            cpu = getattr(status.cpu, "usage_percent", 0) if status.cpu else 0
            ram = getattr(status.ram, "percent", 0) if status.ram else 0
            if cpu > 90 and ram > 90:
                logger.warning("System resources too low for intelligence analysis: CPU=%d%%, RAM=%d%%", cpu, ram)
                return False
            return True
        except Exception as e:
            logger.warning("Resource check failed: %s", e)
            return True

    def _store_memory_event(self, title: str, description: str, tags: Optional[list[str]] = None):
        if self._memory is None:
            return
        try:
            if hasattr(self._memory, "store_event"):
                self._memory.store_event(
                    title=title,
                    description=description[:500],
                    tags=tags or ["system-intelligence"],
                    owner_id="default",
                )
        except Exception as e:
            logger.warning("Failed to store system intelligence memory event: %s", e)

    # ----- Public API -----

    def get_hardware_summary(self) -> str:
        allowed, reason = self._check_permission("guest")
        if not allowed:
            return reason
        try:
            hw = self._hardware.get_summary()
            gpu = hw.gpu_model if hw.gpu_model and "No discrete GPU" not in hw.gpu_model else "Integrated graphics"
            return (
                f"You have a {hw.cpu_model} with {hw.cpu_cores} cores and {hw.cpu_threads} threads. "
                f"Your GPU is {gpu}. "
                f"You have {hw.ram_total_gb} GB of {hw.ram_form_factor} RAM. "
                f"Motherboard: {hw.motherboard}. "
                f"You are running {hw.os_version}."
            )
        except Exception as e:
            logger.error("Hardware summary failed: %s", e)
            return "I couldn't retrieve hardware information right now."

    def get_software_summary(self) -> str:
        allowed, reason = self._check_permission("guest")
        if not allowed:
            return reason
        try:
            apps = self._software.get_installed_apps()
            count = len(apps)
            if count == 0:
                return "I couldn't find any installed applications."
            top = [a.name for a in apps[:8]]
            procs = self._software.get_running_process_count()
            return (
                f"You have {count} applications installed. "
                f"Some notable ones: {', '.join(top)}. "
                f"Currently, {procs} processes are running on your system."
            )
        except Exception as e:
            logger.error("Software summary failed: %s", e)
            return "I couldn't retrieve software information right now."

    def get_network_summary(self) -> str:
        allowed, reason = self._check_permission("guest")
        if not allowed:
            return reason
        try:
            config = self._network.get_config()
            active = [a for a in config.adapters if a.get("isup")]
            if active:
                adapter = active[0]
                ip = adapter.get("ip", "an IP address")
                name = adapter["name"]
            else:
                ip = "no active connection"
                name = "No active adapter"
            dns = ", ".join(config.dns_servers[:3]) if config.dns_servers else "not configured"
            vpn = "connected" if config.vpn_active else "not detected"
            return (
                f"Your active network adapter is {name} with IP {ip}. "
                f"DNS servers: {dns}. "
                f"VPN: {vpn}. "
                f"There are {config.active_connections} active network connections "
                f"and {len(config.listening_ports)} ports in listening state."
            )
        except Exception as e:
            logger.error("Network summary failed: %s", e)
            return "I couldn't retrieve network information right now."

    def get_storage_summary(self) -> str:
        allowed, reason = self._check_permission("guest")
        if not allowed:
            return reason
        try:
            details = self._storage.get_storage_details()
            if not details:
                return "I couldn't find any storage devices."
            parts = []
            for d in details:
                free_gb = d.free / (1024 ** 3)
                total_gb = d.total / (1024 ** 3)
                parts.append(
                    f"{d.mount_point}: {free_gb:.1f} GB free of {total_gb:.1f} GB ({100 - d.percent:.0f}% free)"
                )
            return "Storage summary: " + " | ".join(parts)
        except Exception as e:
            logger.error("Storage summary failed: %s", e)
            return "I couldn't retrieve storage information right now."

    def get_security_summary(self) -> str:
        allowed, reason = self._check_permission("guest")
        if not allowed:
            return reason
        try:
            sec = self._security.get_status()
            fw = "ON" if sec.firewall_enabled else "OFF"
            av = "active" if sec.antivirus_active else "inactive"
            return (
                f"Windows Firewall is {fw}. "
                f"Antivirus ({sec.antivirus_name}) is {av}. "
                f"There are {sec.pending_updates} pending system updates. "
                + (f"{len(sec.suspicious_startup_entries)} suspicious startup entries found."
                   if sec.suspicious_startup_entries else "No suspicious startup entries detected.")
            )
        except Exception as e:
            logger.error("Security summary failed: %s", e)
            return "I couldn't retrieve security information right now."

    def run_diagnostics(self) -> list[DiagnosticIssue]:
        allowed, reason = self._check_permission("guest")
        if not allowed:
            return []
        if not self._check_resources():
            return [DiagnosticIssue(
                component="System",
                issue="Resources too low for full diagnostics",
                severity="warning",
                explanation="CPU and RAM usage are both above 90%.",
                suggestion="Close resource-heavy applications and try again.",
            )]
        try:
            issues = self._diagnostics.run_full_diagnostics()
            self._store_memory_event(
                title="System diagnostics completed",
                description=f"Found {len(issues)} issues: "
                           f"{sum(1 for i in issues if i.severity == 'critical')} critical, "
                           f"{sum(1 for i in issues if i.severity == 'warning')} warnings",
                tags=["system-intelligence", "diagnostics"],
            )
            return issues
        except Exception as e:
            logger.error("Diagnostics failed: %s", e)
            return []

    def get_diagnostics_summary(self) -> str:
        issues = self.run_diagnostics()
        if not issues:
            return "No issues found. Your system looks healthy."
        critical = [i for i in issues if i.severity == "critical"]
        warnings = [i for i in issues if i.severity == "warning"]
        info = [i for i in issues if i.severity == "info"]
        parts = []
        if critical:
            parts.append(f"{len(critical)} critical issue(s)")
        if warnings:
            parts.append(f"{len(warnings)} warning(s)")
        if info:
            parts.append(f"{len(info)} note(s)")
        summary = f"Found {', '.join(parts)}. " if parts else "Some minor observations. "
        for issue in issues[:3]:
            summary += f"\n- {issue.component}: {issue.explanation} Suggestion: {issue.suggestion}"
        return summary

    def capture_snapshot(self) -> str:
        allowed, reason = self._check_permission("owner")
        if not allowed:
            return reason
        try:
            ts = self._inventory.capture_snapshot()
            self._store_memory_event(
                title="System snapshot captured",
                description=f"System snapshot at {ts}",
                tags=["system-intelligence", "snapshot"],
            )
            return f"System snapshot captured at {ts}."
        except Exception as e:
            logger.error("Snapshot capture failed: %s", e)
            return "I couldn't capture a system snapshot right now."

    def compare_with_last_snapshot(self) -> str:
        allowed, reason = self._check_permission("owner")
        if not allowed:
            return reason
        try:
            diff = self._inventory.compare_with_last_snapshot()
            if diff is None:
                return "No previous snapshot to compare against. Capture a snapshot first."
            if not diff.has_changes():
                return "No changes detected since the last snapshot."
            parts = []
            if diff.hardware_changed:
                parts.append("Hardware configuration has changed.")
            if diff.new_software:
                names = ", ".join(s.name for s in diff.new_software[:10])
                parts.append(f"New software installed: {names}.")
            if diff.removed_software:
                names = ", ".join(s.name for s in diff.removed_software[:10])
                parts.append(f"Software removed: {names}.")
            if diff.new_services:
                names = ", ".join(s.display_name for s in diff.new_services[:10])
                parts.append(f"New services: {names}.")
            if diff.removed_services:
                names = ", ".join(s.display_name for s in diff.removed_services[:10])
                parts.append(f"Services removed: {names}.")
            return " ".join(parts)
        except Exception as e:
            logger.error("Snapshot comparison failed: %s", e)
            return "I couldn't compare snapshots right now."

    def explain(self, topic: str) -> str:
        allowed, reason = self._check_permission("guest")
        if not allowed:
            return reason
        try:
            explanation = self._explainer.explain(topic)
            self._store_memory_event(
                title=f"Explained: {topic}",
                description=explanation[:200],
                tags=["system-intelligence", "explanation", topic.lower()],
            )
            return explanation
        except Exception as e:
            logger.error("Explanation failed: %s", e)
            return f"I couldn't find information about '{topic}' right now."
