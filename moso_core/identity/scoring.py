from dataclasses import dataclass
from typing import Optional

from moso_core.identity.models import SignalResult, IdentityResult, IdentityLevel, PermissionFlags


@dataclass
class WeightConfig:
    voice: float = 0.35
    liveness: float = 0.20
    behavior: float = 0.20
    device: float = 0.15
    historical: float = 0.10

    def validate(self) -> bool:
        total = self.voice + self.liveness + self.behavior + self.device + self.historical
        return abs(total - 1.0) < 0.001


DEFAULT_WEIGHTS = WeightConfig()


class IdentityScorer:
    def __init__(self, weights: Optional[WeightConfig] = None):
        self._weights = weights or DEFAULT_WEIGHTS
        if not self._weights.validate():
            raise ValueError(f"Weights must sum to 1.0, got {self._weights}")

    def calculate(self, signals: list[SignalResult]) -> IdentityResult:
        if not signals:
            return IdentityResult(
                verified=False,
                level=IdentityLevel.UNKNOWN,
                confidence=0.0,
                permission=PermissionFlags.GUEST_ONLY,
            )

        weighted_sum = sum(
            s.confidence * s.weight for s in signals if s.error is None
        )
        total_weight = sum(s.weight for s in signals if s.error is None)
        confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
        confidence = max(0.0, min(100.0, confidence * 100.0))

        level, permission = self._resolve_permissions(confidence)

        primary = max(signals, key=lambda s: s.confidence * s.weight).signal_name if signals else None

        return IdentityResult(
            verified=confidence >= 95.0,
            level=level,
            confidence=confidence,
            permission=permission,
            signals=signals,
            primary_signal=primary,
        )

    def update_weights(self, weights: WeightConfig) -> None:
        if weights.validate():
            self._weights = weights

    def _resolve_permissions(self, confidence: float) -> tuple[IdentityLevel, PermissionFlags]:
        if confidence >= 95:
            return IdentityLevel.OWNER, PermissionFlags.FULL_ACCESS
        if confidence >= 80:
            return IdentityLevel.LIKELY_OWNER, PermissionFlags.STANDARD_ACCESS
        if confidence >= 60:
            return IdentityLevel.GUEST, PermissionFlags.LIMITED_ACCESS
        return IdentityLevel.UNKNOWN, PermissionFlags.GUEST_ONLY

    @property
    def weights(self) -> WeightConfig:
        return self._weights
