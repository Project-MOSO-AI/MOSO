from __future__ import annotations

import logging
import time
from typing import Any, Optional

from moso_core.risk.models import RiskLevel, RiskReport
from moso_core.risk.verification import VerificationEngine

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(
        self,
        identity: Any = None,
        memory: Any = None,
        resources: Any = None,
    ):
        self._identity = identity
        self._memory = memory
        self._resources = resources
        self._verifier = VerificationEngine()
        logger.info("Risk & Privacy Engine enabled")

    def assess(
        self,
        tool: str,
        action: str,
        params: dict[str, Any],
    ) -> RiskReport:
        report = self._verifier.verify_tool_request(
            tool_name=tool,
            action=action,
            params=params,
            resources=self._resources,
        )

        self._store_memory_event(report)
        return report

    def check_and_block(
        self,
        tool: str,
        action: str,
        params: dict[str, Any],
    ) -> tuple[bool, Optional[RiskReport]]:
        report = self.assess(tool, action, params)

        if not report.is_allowed:
            logger.warning(
                "Action blocked by Risk Engine: %s/%s (level=%s, score=%.2f)",
                tool, action, report.max_level.value, report.risk.score,
            )
            return False, report

        return True, report

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

    def _store_memory_event(self, report: RiskReport):
        if self._memory is None:
            return
        try:
            if hasattr(self._memory, "store_event"):
                self._memory.store_event(
                    title=f"Risk check: {report.tool}/{report.action}",
                    description=f"Level={report.max_level.value}, score={report.risk.score:.2f}, "
                                f"factors={'; '.join(report.risk.factors)[:200]}",
                    tags=["risk-engine", report.tool, report.max_level.value],
                    owner_id="default",
                )
        except Exception as e:
            logger.warning("Failed to store risk memory event: %s", e)
