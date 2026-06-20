from __future__ import annotations

import logging
from typing import Any

from moso_core.risk.models import PrivacyAssessment

logger = logging.getLogger(__name__)

USER_DATA_DIRS: frozenset[str] = frozenset({
    "documents", "desktop", "downloads", "pictures", "videos",
    "music", "appdata", "application data", "localappdata",
    "roaming", "onedrive", "icloud", "dropbox", "google drive",
})

SYSTEM_DATA_DIRS: frozenset[str] = frozenset({
    "windows", "system32", "program files", "programdata",
    "etc", "usr", "var", "bin", "boot",
})


class PrivacyEngine:
    def assess(self, action: str, tool: str, params: dict[str, Any]) -> PrivacyAssessment:
        path = params.get("path", "")
        url = params.get("url", "")
        command = params.get("command", "")
        action_lower = action.lower()

        user_data_accessed = self._check_user_data_access(path, command, action_lower)
        system_files_affected = self._check_system_files(path, action_lower)
        writes_externally = self._check_external_write(action_lower, tool, params)
        credential_exposure = self._check_credential_exposure(path, command, action_lower)
        data_exposure = self._assess_data_exposure(action_lower, path)
        network_exposure = self._assess_network_exposure(action_lower, url, tool)

        recommendation = self._build_recommendation(
            data_exposure, credential_exposure, network_exposure,
            user_data_accessed, system_files_affected, writes_externally,
        )

        return PrivacyAssessment(
            data_exposure=data_exposure,
            credential_exposure=credential_exposure,
            network_exposure=network_exposure,
            user_data_accessed=user_data_accessed,
            system_files_affected=system_files_affected,
            writes_externally=writes_externally,
            recommendation=recommendation,
        )

    def _check_user_data_access(self, path: str, command: str, action: str) -> bool:
        combined = (path + " " + command).lower()
        for d in USER_DATA_DIRS:
            if d in combined:
                return True
        return False

    def _check_system_files(self, path: str, action: str) -> bool:
        path_lower = path.lower()
        for d in SYSTEM_DATA_DIRS:
            if d in path_lower and action in ("delete_file", "write_file", "create_folder", "run_command"):
                return True
        return False

    def _check_external_write(self, action: str, tool: str, params: dict[str, Any]) -> bool:
        if action in ("upload", "send", "post", "put"):
            return True
        if tool == "browser_tool" and action in ("open_url", "search_web"):
            url = params.get("url", "")
            if url and not url.startswith("file://") and not url.startswith("about:"):
                return True
        if tool == "terminal_tool" and action == "run_command":
            cmd = params.get("command", "").lower()
            upload_cmds = ["curl", "wget", "invoke-webrequest", "scp", "ftp", "net use"]
            if any(cmd.startswith(c) for c in upload_cmds):
                return True
        return False

    def _check_credential_exposure(self, path: str, command: str, action: str) -> bool:
        from moso_core.risk.risk_engine import CREDENTIAL_PATHS
        combined = (path + " " + command).lower()
        for cp in CREDENTIAL_PATHS:
            if cp.lower() in combined:
                return True
        return False

    def _assess_data_exposure(self, action: str, path: str) -> str:
        if action in ("read_file", "list_directory", "run_command"):
            if path:
                return "reads file/directory contents"
            return "reads data"
        if action in ("write_file", "create_file", "delete_file", "create_folder"):
            return "modifies filesystem"
        if action in ("launch_application", "close_application"):
            return "manages applications"
        if action in ("search_web", "open_url"):
            return "network access"
        if action == "run_command":
            return "executes arbitrary commands"
        return "none"

    def _assess_network_exposure(self, action: str, url: str, tool: str) -> str:
        if tool == "browser_tool" and url:
            if url.startswith("file://"):
                return "local file access"
            return "external network access"
        if tool == "terminal_tool":
            cmd_lower = url.lower() if url else ""
            network_cmds = ["curl", "wget", "ping", "nslookup", "tracert", "netstat", "ssh", "ftp"]
            for nc in network_cmds:
                if nc in cmd_lower:
                    return "network command execution"
            return "none"
        return "none"

    def _build_recommendation(
        self,
        data_exposure: str,
        credential_exposure: bool,
        network_exposure: str,
        user_data_accessed: bool,
        system_files_affected: bool,
        writes_externally: bool,
    ) -> str:
        warnings = []
        if credential_exposure:
            warnings.append("Potential credential exposure detected")
        if system_files_affected:
            warnings.append("This action affects system files")
        if writes_externally:
            warnings.append("This action sends data externally")
        if user_data_accessed:
            warnings.append("This action accesses user data")
        if network_exposure == "external network access":
            warnings.append("This action connects to an external network")
        if not warnings:
            return "No privacy concerns detected."
        return "Privacy warning: " + ". ".join(warnings) + "."
