from __future__ import annotations

import logging
import os
from typing import Any, Optional

from moso_core.risk.models import RiskAssessment, RiskLevel
from moso_core.risk.network_analysis import NetworkAnalysis
from moso_core.risk.reputation import ReputationChecker

logger = logging.getLogger(__name__)

CREDENTIAL_PATHS: frozenset[str] = frozenset({
    ".env", ".env.local", ".env.production",
    "id_rsa", "id_ed25519", "id_ecdsa",
    "authorized_keys", "known_hosts",
    "credentials", "credentials.json",
    "key.pem", "key.ppk", "private.key",
    "secret", "secrets.json", "secrets.yml",
    "password", "passwords.txt",
    "token", "tokens.json",
    ".aws/credentials", ".azure/credentials",
    ".netrc", ".pgpass",
    "config.json", "settings.json",
})

SYSTEM_PATHS: frozenset[str] = frozenset({
    "C:\\Windows", "C:\\Windows\\System32", "C:\\Program Files",
    "C:\\Program Files (x86)", "/etc", "/usr", "/bin", "/boot",
    "/System", "/Library", "/Applications",
})

SENSITIVE_USER_PATHS: frozenset[str] = frozenset({
    "Documents", "Desktop", "Downloads", "Pictures", "Videos",
    "AppData", "Application Support", ".ssh", ".gnupg",
})


class RiskEngine:
    def __init__(self):
        self._network = NetworkAnalysis()
        self._reputation = ReputationChecker()

    def assess(
        self,
        action: str,
        tool: str,
        params: dict[str, Any],
        resources: Any = None,
    ) -> RiskAssessment:
        factors: list[str] = []
        score = 0.0

        dest_score, dest_factors = self._assess_destination(action, tool, params)
        score += dest_score
        factors.extend(dest_factors)

        file_score, file_factors = self._assess_file_impact(action, tool, params)
        score += file_score
        factors.extend(file_factors)

        cred_score, cred_factors = self._assess_credential_exposure(action, tool, params)
        score += cred_score
        factors.extend(cred_factors)

        perm_score, perm_factors = self._assess_permission_requirement(action, tool, params)
        score += perm_score
        factors.extend(perm_factors)

        resource_score, resource_factors = self._assess_resource_impact(action, tool, params, resources)
        score += resource_score
        factors.extend(resource_factors)

        score = min(score, 1.0)
        level = RiskLevel.LOW
        if score >= 0.8:
            level = RiskLevel.CRITICAL
        elif score >= 0.5:
            level = RiskLevel.HIGH
        elif score >= 0.2:
            level = RiskLevel.MEDIUM

        explanation = self._build_explanation(level, score, factors)
        recommendation = self._build_recommendation(level, factors)

        return RiskAssessment(
            level=level,
            score=score,
            factors=factors,
            explanation=explanation,
            recommendation=recommendation,
        )

    def _assess_destination(self, action: str, tool: str, params: dict[str, Any]) -> tuple[float, list[str]]:
        factors: list[str] = []
        url = params.get("url") or params.get("path") or ""
        port = params.get("port")

        if not url and tool in ("browser_tool", "terminal_tool"):
            return 0.0, []

        analysis = self._network.analyze_destination(url, port)
        if analysis["reputation_score"] >= 0.7:
            factors.append(f"destination has high reputation risk: {analysis['reputation_reason']}")
            return 0.4, factors
        elif analysis["reputation_score"] >= 0.3:
            factors.append(f"destination has medium reputation risk: {analysis['reputation_reason']}")
            return 0.2, factors
        elif not analysis["is_tls"] and not analysis["is_local"]:
            factors.append("non-TLS connection to remote destination")
            return 0.15, factors

        return 0.0, []

    def _assess_file_impact(self, action: str, tool: str, params: dict[str, Any]) -> tuple[float, list[str]]:
        factors: list[str] = []
        path = params.get("path", "")
        if not path:
            return 0.0, []

        path_lower = path.lower()
        for sys_path in SYSTEM_PATHS:
            if path_lower.startswith(sys_path.lower()):
                factors.append(f"affects system directory: {sys_path}")
                return 0.5, factors

        for cred_path in CREDENTIAL_PATHS:
            if cred_path.lower() in path_lower:
                factors.append(f"affects credential/config file: {cred_path}")
                return 0.7, factors

        for user_path in SENSITIVE_USER_PATHS:
            if user_path.lower() in path_lower:
                factors.append(f"affects user data directory: {user_path}")
                return 0.3, factors

        return 0.0, []

    def _assess_credential_exposure(self, action: str, tool: str, params: dict[str, Any]) -> tuple[float, list[str]]:
        factors: list[str] = []
        action_lower = action.lower()
        params_str = str(params.values()).lower()

        if action_lower in ("read_file", "run_command"):
            for cred_path in CREDENTIAL_PATHS:
                if cred_path.lower() in params_str:
                    factors.append(f"potential credential access: {cred_path}")
                    return 0.6, factors

        sensitive_cmds = ["type ", "cat ", "get-content", "more ", "findstr"]
        cmd = params.get("command", "")
        for sc in sensitive_cmds:
            if cmd.lower().startswith(sc):
                for cred_path in CREDENTIAL_PATHS:
                    if cred_path.lower() in cmd.lower():
                        factors.append(f"command reads credential file: {cred_path}")
                        return 0.6, factors

        return 0.0, []

    def _assess_permission_requirement(self, action: str, tool: str, params: dict[str, Any]) -> tuple[float, list[str]]:
        factors: list[str] = []
        from moso_core.tools.registry import ToolRegistry
        registry = ToolRegistry()
        tool_obj = registry.get_tool(tool)
        if tool_obj is None:
            return 0.0, []

        required_level = tool_obj.get_permission_level(action)
        if required_level == "owner":
            factors.append(f"requires owner-level permission for action: {action}")
            return 0.3, factors
        elif required_level == "trusted":
            factors.append(f"requires trusted-level permission for action: {action}")
            return 0.1, factors

        return 0.0, []

    def _assess_resource_impact(self, action: str, tool: str, params: dict[str, Any], resources: Any = None) -> tuple[float, list[str]]:
        factors: list[str] = []
        if resources is None:
            return 0.0, []

        try:
            status = resources.get_system_status()
            cpu = getattr(status.cpu, "usage_percent", 0) if status.cpu else 0
            ram = getattr(status.ram, "percent", 0) if status.ram else 0
            if cpu > 90 and ram > 90:
                factors.append(f"system resources critical (CPU={cpu}%, RAM={ram}%)")
                return 0.5, factors
            elif cpu > 80 or ram > 80:
                factors.append(f"system resources high (CPU={cpu}%, RAM={ram}%)")
                return 0.2, factors
        except Exception as e:
            logger.warning("Resource check failed: %s", e)

        return 0.0, []

    def _build_explanation(self, level: RiskLevel, score: float, factors: list[str]) -> str:
        if not factors:
            return "No risk factors detected."
        prefix = {
            RiskLevel.LOW: "Low risk.",
            RiskLevel.MEDIUM: "Medium risk identified.",
            RiskLevel.HIGH: "High risk! Proceed with caution.",
            RiskLevel.CRITICAL: "CRITICAL risk! Action is blocked.",
        }.get(level, "Risk assessment completed.")
        return f"{prefix} Score: {score:.2f}. Factors: {'; '.join(factors)}"

    def _build_recommendation(self, level: RiskLevel, factors: list[str]) -> str:
        if level == RiskLevel.LOW:
            return "Action appears safe to execute."
        if level == RiskLevel.MEDIUM:
            return "Review the risk factors above before proceeding."
        if level == RiskLevel.HIGH:
            return "Strongly consider alternatives. If proceeding, confirm manually."
        if level == RiskLevel.CRITICAL:
            return "Action is blocked. This operation is too risky to execute automatically."
        return ""
