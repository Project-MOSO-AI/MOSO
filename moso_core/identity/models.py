from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IdentityLevel(str, Enum):
    UNKNOWN = "unknown"
    GUEST = "guest"
    LIKELY_OWNER = "likely_owner"
    OWNER = "owner"


class PermissionFlags(str, Enum):
    FULL_ACCESS = "full_access"
    STANDARD_ACCESS = "standard_access"
    LIMITED_ACCESS = "limited_access"
    GUEST_ONLY = "guest_only"


@dataclass
class SignalResult:
    signal_name: str
    confidence: float
    weight: float
    details: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def weighted_score(self) -> float:
        return self.confidence * self.weight


@dataclass
class IdentityState:
    current_user: str = "unknown"
    level: IdentityLevel = IdentityLevel.UNKNOWN
    confidence: float = 0.0
    permission: PermissionFlags = PermissionFlags.GUEST_ONLY
    last_verified: float = 0.0
    session_start: float = 0.0
    signal_history: list[SignalResult] = field(default_factory=list)
    active: bool = False

    def to_dict(self) -> dict:
        return {
            "current_user": self.current_user,
            "level": self.level.value,
            "confidence": self.confidence,
            "permission": self.permission.value,
            "last_verified": self.last_verified,
            "session_start": self.session_start,
            "active": self.active,
        }


@dataclass
class IdentityResult:
    verified: bool
    level: IdentityLevel = IdentityLevel.UNKNOWN
    confidence: float = 0.0
    permission: PermissionFlags = PermissionFlags.GUEST_ONLY
    signals: list[SignalResult] = field(default_factory=list)
    primary_signal: Optional[str] = None
    session: Optional[IdentityState] = None
    error: Optional[str] = None


WEIGHT_VOICE = 0.35
WEIGHT_LIVENESS = 0.20
WEIGHT_BEHAVIOR = 0.20
WEIGHT_DEVICE = 0.15
WEIGHT_HISTORICAL = 0.10
