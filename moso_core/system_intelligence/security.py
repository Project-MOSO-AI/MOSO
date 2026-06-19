from __future__ import annotations

import logging
import subprocess
from typing import Optional

from moso_core.system_intelligence.models import SecurityStatus

logger = logging.getLogger(__name__)


class SecurityIntelligence:
    def get_status(self) -> SecurityStatus:
        firewall_enabled, firewall_profile = self._check_firewall()
        av_active, av_name = self._check_antivirus()
        pending_updates = self._check_pending_updates()
        suspicious = self._scan_startup_risks()

        return SecurityStatus(
            firewall_enabled=firewall_enabled,
            firewall_profile=firewall_profile,
            antivirus_active=av_active,
            antivirus_name=av_name,
            pending_updates=pending_updates,
            suspicious_startup_entries=suspicious,
        )

    @staticmethod
    def _check_firewall() -> tuple[bool, str]:
        try:
            result = subprocess.run(
                ["netsh", "advfirewall", "show", "allprofiles"],
                capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                enabled = False
                profile = "Unknown"
                for line in result.stdout.splitlines():
                    line_lower = line.strip().lower()
                    if "profile settings:" in line_lower:
                        parts = line.split(":")
                        profile = parts[1].strip() if len(parts) > 1 else profile
                    if "state" in line_lower and "on" in line_lower:
                        enabled = True
                return enabled, profile
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("Firewall check failed: %s", e)
        return False, "Unknown"

    @staticmethod
    def _check_antivirus() -> tuple[bool, str]:
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance -Namespace 'root/SecurityCenter2' -ClassName 'AntivirusProduct' "
                 "| Select-Object DisplayName, ProductState | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip() and "DisplayName" in result.stdout:
                import json
                data = json.loads(result.stdout)
                if isinstance(data, dict):
                    data = [data]
                for av in data:
                    name = av.get("DisplayName", "")
                    state = av.get("ProductState", 0)
                    if name and state:
                        state_str = f"{state:06X}"
                        if len(state_str) >= 4 and state_str[2:4] == "10":
                            return True, name
                if data:
                    return True, data[0].get("DisplayName", "Windows Defender")
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError, OSError) as e:
            logger.debug("Antivirus check failed: %s", e)

        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-MpComputerStatus | Select-Object AntivirusEnabled, AMServiceEnabled | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                import json
                data = json.loads(result.stdout)
                if data.get("AntivirusEnabled") or data.get("AMServiceEnabled"):
                    return True, "Windows Defender"
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError, OSError) as e:
            logger.debug("Defender status check failed: %s", e)

        return False, "Unknown (antivirus)"

    @staticmethod
    def _check_pending_updates() -> int:
        count = 0
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-WindowsUpdate).Count"],
                capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip().isdigit():
                count = int(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("Windows update check failed: %s", e)

        if count == 0:
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     "Get-CimInstance -Namespace 'root/SoftwareDistribution' -ClassName 'UpdateStatus' "
                     "| Measure-Object | Select-Object -ExpandProperty Count"],
                    capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode == 0 and result.stdout.strip().isdigit():
                    count = int(result.stdout.strip())
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
                logger.debug("SoftwareDistribution update check failed: %s", e)

        return count

    @staticmethod
    def _scan_startup_risks() -> list[str]:
        suspicious = []
        try:
            import winreg
            paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            ]
            risk_keywords = ["temp", "download", "crypto", "miner", "unknown", "startup", "svchost"]
            safe_publishers = ["Microsoft", "Google", "Mozilla", "Adobe", "Oracle", "Apple", "Spotify",
                               "Dropbox", "Discord", "Slack", "Zoom", "Notion"]
            for hive, path in paths:
                try:
                    with winreg.OpenKey(hive, path) as key:
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                i += 1
                                val_lower = value.lower()
                                if any(kw in val_lower for kw in risk_keywords):
                                    is_safe = any(safe.lower() in val_lower for safe in safe_publishers)
                                    if not is_safe:
                                        suspicious.append(name)
                            except OSError:
                                break
                except (FileNotFoundError, OSError):
                    continue
        except (ImportError, Exception) as e:
            logger.debug("Startup risk scan failed: %s", e)

        return suspicious
