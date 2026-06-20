from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    level: RiskLevel = RiskLevel.LOW
    score: float = 0.0
    factors: list[str] = field(default_factory=list)
    explanation: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "score": self.score,
            "factors": self.factors,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
        }


@dataclass
class PrivacyAssessment:
    data_exposure: str = "none"
    credential_exposure: bool = False
    network_exposure: str = "none"
    user_data_accessed: bool = False
    system_files_affected: bool = False
    writes_externally: bool = False
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "data_exposure": self.data_exposure,
            "credential_exposure": self.credential_exposure,
            "network_exposure": self.network_exposure,
            "user_data_accessed": self.user_data_accessed,
            "system_files_affected": self.system_files_affected,
            "writes_externally": self.writes_externally,
            "recommendation": self.recommendation,
        }


@dataclass
class RiskReport:
    action: str = ""
    tool: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    risk: RiskAssessment = field(default_factory=RiskAssessment)
    privacy: PrivacyAssessment = field(default_factory=PrivacyAssessment)
    timestamp: float = 0.0

    @property
    def max_level(self) -> RiskLevel:
        levels = [self.risk.level, self.privacy.credential_exposure and RiskLevel.CRITICAL or RiskLevel.LOW]
        order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return max(levels, key=lambda l: order.index(l))

    @property
    def is_allowed(self) -> bool:
        return self.max_level not in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "tool": self.tool,
            "params": self.params,
            "risk": self.risk.to_dict(),
            "privacy": self.privacy.to_dict(),
            "max_level": self.max_level.value,
            "is_allowed": self.is_allowed,
            "timestamp": self.timestamp,
        }
