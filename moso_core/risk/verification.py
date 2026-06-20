from __future__ import annotations

import logging
import time
from typing import Any, Optional

from moso_core.risk.models import RiskLevel, RiskReport
from moso_core.risk.privacy_engine import PrivacyEngine
from moso_core.risk.risk_engine import RiskEngine

logger = logging.getLogger(__name__)


class VerificationEngine:
    def __init__(self):
        self._risk_engine = RiskEngine()
        self._privacy_engine = PrivacyEngine()

    def verify(
        self,
        action: str,
        tool: str,
        params: dict[str, Any],
        resources: Any = None,
    ) -> RiskReport:
        risk = self._risk_engine.assess(action, tool, params, resources)
        privacy = self._privacy_engine.assess(action, tool, params)

        return RiskReport(
            action=action,
            tool=tool,
            params=params,
            risk=risk,
            privacy=privacy,
            timestamp=time.time(),
        )

    def verify_tool_request(
        self,
        tool_name: str,
        action: str,
        params: dict[str, Any],
        resources: Any = None,
    ) -> RiskReport:
        return self.verify(
            action=action,
            tool=tool_name,
            params=params,
            resources=resources,
        )
