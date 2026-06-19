from __future__ import annotations

import logging
from typing import Optional

from moso_core.system_intelligence.models import DiagnosticIssue

logger = logging.getLogger(__name__)


class DiagnosticsEngine:
    def __init__(self, hardware=None, software=None, network=None,
                 storage=None, security=None, resources=None):
        self._hardware = hardware
        self._software = software
        self._network = network
        self._storage = storage
        self._security = security
        self._resources = resources

    def run_full_diagnostics(self) -> list[DiagnosticIssue]:
        issues = []
        issues.extend(self._check_performance())
        issues.extend(self._check_storage())
        issues.extend(self._check_network())
        issues.extend(self._check_security())
        issues.extend(self._check_hardware())
        return issues

    def run_performance_check(self) -> list[DiagnosticIssue]:
        return self._check_performance()

    def run_storage_check(self) -> list[DiagnosticIssue]:
        return self._check_storage()

    def run_network_check(self) -> list[DiagnosticIssue]:
        return self._check_network()

    def run_security_check(self) -> list[DiagnosticIssue]:
        return self._check_security()

    def _check_performance(self) -> list[DiagnosticIssue]:
        issues = []
        if self._resources is None:
            return issues
        try:
            status = self._resources.get_system_status()
            cpu = getattr(status.cpu, "usage_percent", 0) if status.cpu else 0
            ram = getattr(status.ram, "percent", 0) if status.ram else 0

            if cpu > 90:
                issues.append(DiagnosticIssue(
                    component="CPU",
                    issue=f"CPU usage at {cpu:.0f}%",
                    severity="warning",
                    explanation="Your CPU is running near maximum capacity, which can slow down your system.",
                    suggestion="Check top CPU processes with `orchestrator.resources.get_top_cpu_processes()` and consider closing unused applications.",
                ))
            elif cpu > 70:
                issues.append(DiagnosticIssue(
                    component="CPU",
                    issue=f"CPU usage at {cpu:.0f}%",
                    severity="info",
                    explanation="CPU usage is elevated.",
                    suggestion="Monitor if this persists. Close unused apps if needed.",
                ))

            if ram > 90:
                issues.append(DiagnosticIssue(
                    component="RAM",
                    issue=f"RAM usage at {ram:.0f}%",
                    severity="warning",
                    explanation="Your RAM is nearly full, which may cause slowdowns and swapping to disk.",
                    suggestion="Close memory-heavy applications or consider adding more RAM.",
                ))
            elif ram > 75:
                issues.append(DiagnosticIssue(
                    component="RAM",
                    issue=f"RAM usage at {ram:.0f}%",
                    severity="info",
                    explanation="RAM usage is moderately high.",
                    suggestion="Monitor if this persists. Consider closing unused browser tabs.",
                ))

            if status.battery and hasattr(status.battery, "percent"):
                batt = status.battery.percent
                if batt is not None and batt < 20 and not status.battery.plugged_in:
                    issues.append(DiagnosticIssue(
                        component="Battery",
                        issue=f"Battery at {batt:.0f}% and not charging",
                        severity="warning",
                        explanation="Your battery is low and not plugged in.",
                        suggestion="Plug in your charger to avoid data loss.",
                    ))
        except Exception as e:
            logger.debug("Performance check error: %s", e)
        return issues

    def _check_storage(self) -> list[DiagnosticIssue]:
        issues = []
        if self._storage is None:
            return issues
        try:
            details = self._storage.get_storage_details()
            for disk in details:
                if disk.percent > 95:
                    issues.append(DiagnosticIssue(
                        component="Storage",
                        issue=f"{disk.mount_point} is {disk.percent:.0f}% full",
                        severity="critical",
                        explanation=f"Your drive {disk.mount_point} is nearly full. Only {disk.free / (1024**3):.1f} GB remaining.",
                        suggestion="Use storage.find_large_files() or storage.find_large_folders() to identify what to clean up.",
                    ))
                elif disk.percent > 85:
                    issues.append(DiagnosticIssue(
                        component="Storage",
                        issue=f"{disk.mount_point} is {disk.percent:.0f}% full",
                        severity="warning",
                        explanation=f"Your drive {disk.mount_point} is running low on space. {disk.free / (1024**3):.1f} GB free.",
                        suggestion="Consider cleaning up temporary files or uninstalling unused applications.",
                    ))
        except Exception as e:
            logger.debug("Storage check error: %s", e)
        return issues

    def _check_network(self) -> list[DiagnosticIssue]:
        issues = []
        if self._network is None:
            return issues
        try:
            config = self._network.get_config()
            has_active = any(
                a.get("isup") and any(
                    addr.get("address", "").count(".") == 3
                    for addr in a.get("addresses", [])
                )
                for a in config.adapters
            )
            if not has_active and config.adapters:
                issues.append(DiagnosticIssue(
                    component="Network",
                    issue="No active network connection detected",
                    severity="warning",
                    explanation="You don't seem to have an active internet connection.",
                    suggestion="Check your WiFi or Ethernet connection.",
                ))
        except Exception as e:
            logger.debug("Network check error: %s", e)
        return issues

    def _check_security(self) -> list[DiagnosticIssue]:
        issues = []
        if self._security is None:
            return issues
        try:
            sec = self._security.get_status()

            if not sec.firewall_enabled:
                issues.append(DiagnosticIssue(
                    component="Firewall",
                    issue="Windows Firewall is disabled",
                    severity="warning",
                    explanation="Your firewall is turned off, which exposes your system to network threats.",
                    suggestion="Enable Windows Firewall: `netsh advfirewall set allprofiles state on`",
                ))

            if not sec.antivirus_active:
                issues.append(DiagnosticIssue(
                    component="Antivirus",
                    issue="No active antivirus detected",
                    severity="critical",
                    explanation="Your system may not have real-time antivirus protection.",
                    suggestion="Enable Windows Defender or install a trusted antivirus solution.",
                ))

            if sec.pending_updates > 10:
                issues.append(DiagnosticIssue(
                    component="Updates",
                    issue=f"{sec.pending_updates} pending updates",
                    severity="warning",
                    explanation=f"There are {sec.pending_updates} system updates waiting to be installed.",
                    suggestion="Run Windows Update to install pending updates for security fixes.",
                ))
            elif sec.pending_updates > 0:
                issues.append(DiagnosticIssue(
                    component="Updates",
                    issue=f"{sec.pending_updates} pending updates",
                    severity="info",
                    explanation=f"There are {sec.pending_updates} pending system updates.",
                    suggestion="Install updates when convenient to keep your system secure.",
                ))

            if sec.suspicious_startup_entries:
                names = ", ".join(sec.suspicious_startup_entries)
                issues.append(DiagnosticIssue(
                    component="Startup",
                    issue=f"{len(sec.suspicious_startup_entries)} suspicious startup entries: {names}",
                    severity="info",
                    explanation="Some programs start automatically that may be unnecessary or risky.",
                    suggestion="Review startup entries in Task Manager > Startup tab.",
                ))
        except Exception as e:
            logger.debug("Security check error: %s", e)
        return issues

    def _check_hardware(self) -> list[DiagnosticIssue]:
        issues = []
        if self._hardware is None:
            return issues
        try:
            hw = self._hardware.get_summary()

            if hw.ram_total_gb < 8:
                issues.append(DiagnosticIssue(
                    component="RAM",
                    issue=f"Only {hw.ram_total_gb:.0f} GB RAM installed",
                    severity="info",
                    explanation="Your system has limited memory, which may affect performance with modern applications.",
                    suggestion="Consider upgrading RAM if you run multiple applications simultaneously.",
                ))

            if not hw.gpu_model or "No discrete GPU" in hw.gpu_model:
                if hw.cpu_cores > 4:
                    issues.append(DiagnosticIssue(
                        component="GPU",
                        issue="No discrete GPU detected",
                        severity="info",
                        explanation="Your system relies on integrated graphics only.",
                        suggestion="For gaming, 3D rendering, or AI workloads, a dedicated GPU would improve performance.",
                    ))
        except Exception as e:
            logger.debug("Hardware check error: %s", e)
        return issues
