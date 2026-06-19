import logging
import time
from typing import Optional

from moso_core.identity.models import IdentityLevel, IdentityState, IdentityResult, PermissionFlags

logger = logging.getLogger(__name__)


class IdentitySessionManager:
    def __init__(self, session_timeout_ms: int = 300000, re_verify_interval_ms: int = 60000):
        self._session_timeout_ms = session_timeout_ms
        self._re_verify_interval_ms = re_verify_interval_ms
        self._state: Optional[IdentityState] = None

    def start_session(self) -> IdentityState:
        now = time.time() * 1000
        self._state = IdentityState(
            level=IdentityLevel.UNKNOWN,
            confidence=0.0,
            permission=PermissionFlags.GUEST_ONLY,
            last_verified=now,
            session_start=now,
            active=True,
        )
        logger.info("Identity session started")
        return self._state

    def end_session(self) -> None:
        if self._state:
            self._state.active = False
            logger.info("Identity session ended")
            self._state = None

    def update(self, result: IdentityResult) -> IdentityState:
        if self._state is None:
            self.start_session()

        prev_level = self._state.level
        now = time.time() * 1000

        self._state.level = result.level
        self._state.confidence = result.confidence
        self._state.permission = result.permission
        self._state.last_verified = now

        if result.signals:
            self._state.signal_history.extend(result.signals)
            if len(self._state.signal_history) > 100:
                self._state.signal_history = self._state.signal_history[-50:]

        if prev_level != result.level:
            logger.info(
                "Identity transition: %s -> %s (confidence: %.1f%%)",
                prev_level.value,
                result.level.value,
                result.confidence,
            )

        return self._state

    def should_reverify(self) -> bool:
        if self._state is None:
            return True
        if not self._state.active:
            return True
        elapsed = time.time() * 1000 - self._state.last_verified
        return elapsed > self._re_verify_interval_ms

    def is_session_expired(self) -> bool:
        if self._state is None:
            return True
        if not self._state.active:
            return True
        elapsed = time.time() * 1000 - self._state.session_start
        return elapsed > self._session_timeout_ms

    def has_transitioned_to(self, target_level: IdentityLevel) -> bool:
        if self._state is None:
            return False
        return self._state.level == target_level

    def check_downgrade(self, result: IdentityResult) -> bool:
        if self._state is None:
            return False
        return result.level.value < self._state.level.value

    def suspend_privileged_ops(self) -> None:
        if self._state:
            self._state.permission = PermissionFlags.GUEST_ONLY
            logger.info("Privileged operations suspended")

    def restore_privileges(self, result: IdentityResult) -> None:
        if self._state and result.level in (IdentityLevel.OWNER, IdentityLevel.LIKELY_OWNER):
            self._state.permission = result.permission
            logger.info("Privileges restored: %s", result.permission.value)

    @property
    def state(self) -> Optional[IdentityState]:
        return self._state

    @property
    def is_owner(self) -> bool:
        return self._state is not None and self._state.level == IdentityLevel.OWNER

    @property
    def is_active(self) -> bool:
        return self._state is not None and self._state.active
