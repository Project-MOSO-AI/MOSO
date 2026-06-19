from __future__ import annotations

import logging
import subprocess
from typing import Optional

from moso_core.system_intelligence.models import SoftwareEntry, ServiceEntry

logger = logging.getLogger(__name__)

_UNINSTALL_PATHS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
]

_STARTUP_PATHS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
]


class SoftwareIntelligence:
    def get_installed_apps(self) -> list[SoftwareEntry]:
        apps: dict[str, SoftwareEntry] = {}
        for path in _UNINSTALL_PATHS:
            self._read_registry_entries(path, apps)
        return sorted(apps.values(), key=lambda a: a.name.lower())

    def get_startup_items(self) -> list[dict]:
        items: list[dict] = {}
        for path in _STARTUP_PATHS:
            self._read_startup_entries(path, items)
        return sorted(items.values(), key=lambda i: i["name"].lower()) if isinstance(next(iter(items.values())), dict) else list(items.values())

    def get_services(self) -> list[ServiceEntry]:
        services = []
        try:
            result = subprocess.run(
                ["sc", "query", "type=", "service", "state=", "all"],
                capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                services = self._parse_sc_query(result.stdout)
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("sc query failed: %s", e)

        if not services:
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     "Get-Service | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode == 0 and result.stdout.strip():
                    services = self._parse_powershell_services(result.stdout)
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
                logger.debug("PowerShell Get-Service failed: %s", e)

        return services

    def get_running_process_count(self) -> int:
        try:
            import psutil
            return len(psutil.pids())
        except Exception:
            return 0

    @staticmethod
    def _read_registry_entries(reg_path: str, apps: dict[str, SoftwareEntry]):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        i += 1
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            except FileNotFoundError:
                                continue
                            try:
                                version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                            except FileNotFoundError:
                                version = ""
                            try:
                                publisher, _ = winreg.QueryValueEx(subkey, "Publisher")
                            except FileNotFoundError:
                                publisher = ""
                            try:
                                install_date, _ = winreg.QueryValueEx(subkey, "InstallDate")
                            except FileNotFoundError:
                                install_date = ""
                            try:
                                install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                            except FileNotFoundError:
                                install_loc = ""
                            if name and name not in apps:
                                apps[name] = SoftwareEntry(
                                    name=name,
                                    version=version,
                                    publisher=publisher,
                                    install_date=install_date,
                                    install_location=install_loc,
                                )
                    except OSError:
                        break
        except (FileNotFoundError, ImportError, OSError) as e:
            logger.debug("Registry read failed for %s: %s", reg_path, e)

    @staticmethod
    def _read_startup_entries(reg_path: str, items: dict[str, dict]):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        i += 1
                        if name and name not in items:
                            items[name] = {"name": name, "command": value, "source": "HKLM"}
                    except OSError:
                        break
        except (FileNotFoundError, ImportError, OSError) as e:
            logger.debug("Startup registry read failed for %s: %s", reg_path, e)

        try:
            import winreg
            user_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, user_path) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        i += 1
                        if name and name not in items:
                            items[name] = {"name": name, "command": value, "source": "HKCU"}
                    except OSError:
                        break
        except (FileNotFoundError, ImportError, OSError) as e:
            logger.debug("User startup registry read failed: %s", e)

    @staticmethod
    def _parse_sc_query(output: str) -> list[ServiceEntry]:
        services = []
        current = {}
        for line in output.splitlines():
            line = line.strip()
            if line.upper().startswith("SERVICE_NAME:"):
                if current.get("name"):
                    services.append(ServiceEntry(
                        name=current["name"],
                        display_name=current.get("display_name", current["name"]),
                        status=current.get("status", "UNKNOWN"),
                        start_type=current.get("start_type", "Unknown"),
                    ))
                current = {"name": line.split(":", 1)[1].strip()}
            elif line.upper().startswith("DISPLAY_NAME:"):
                current["display_name"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("STATE"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    state_part = parts[1].strip()
                    state_codes = {"1": "STOPPED", "2": "START_PENDING", "3": "STOP_PENDING",
                                   "4": "RUNNING", "5": "CONTINUE_PENDING", "6": "PAUSE_PENDING",
                                   "7": "PAUSED"}
                    code = state_part.split()[0] if state_part else "1"
                    current["status"] = state_codes.get(code, state_part)
            elif line.upper().startswith("START_TYPE"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    st_part = parts[1].strip()
                    st_codes = {"1": "SERVICE_BOOT_START", "2": "AUTO_START", "3": "DEMAND_START",
                                "4": "DISABLED"}
                    code = st_part.split()[0] if st_part else "3"
                    current["start_type"] = st_codes.get(code, st_part)
        if current.get("name"):
            services.append(ServiceEntry(
                name=current["name"],
                display_name=current.get("display_name", current["name"]),
                status=current.get("status", "UNKNOWN"),
                start_type=current.get("start_type", "Unknown"),
            ))
        return services

    @staticmethod
    def _parse_powershell_services(json_str: str) -> list[ServiceEntry]:
        try:
            import json
            data = json.loads(json_str)
            if isinstance(data, dict):
                data = [data]
            services = []
            for item in data:
                services.append(ServiceEntry(
                    name=item.get("Name", ""),
                    display_name=item.get("DisplayName", ""),
                    status=item.get("Status", "Unknown"),
                    start_type=item.get("StartType", "Unknown"),
                ))
            return services
        except (json.JSONDecodeError, Exception) as e:
            logger.debug("Failed to parse PowerShell service JSON: %s", e)
            return []
