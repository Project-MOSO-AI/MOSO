import logging
from typing import Optional

import numpy as np

from moso_core.identity.models import (
    IdentityResult,
    IdentityLevel,
    IdentityState,
    SignalResult,
    PermissionFlags,
)
from moso_core.identity.voice_biometrics import VoiceBiometrics
from moso_core.identity.anti_spoof import AntiSpoofDetector
from moso_core.identity.behavior import BehavioralBiometrics
from moso_core.identity.device_presence import DevicePresence
from moso_core.identity.historical_context import HistoricalContext
from moso_core.identity.scoring import IdentityScorer, DEFAULT_WEIGHTS
from moso_core.identity.permissions import PermissionResolver
from moso_core.identity.session import IdentitySessionManager

logger = logging.getLogger(__name__)


class IdentityVerifier:
    def __init__(
        self,
        voice: Optional[VoiceBiometrics] = None,
        anti_spoof: Optional[AntiSpoofDetector] = None,
        behavior: Optional[BehavioralBiometrics] = None,
        device: Optional[DevicePresence] = None,
        historical: Optional[HistoricalContext] = None,
        scorer: Optional[IdentityScorer] = None,
        permissions: Optional[PermissionResolver] = None,
        session_mgr: Optional[IdentitySessionManager] = None,
    ):
        self._voice = voice or VoiceBiometrics()
        self._anti_spoof = anti_spoof or AntiSpoofDetector()
        self._behavior = behavior or BehavioralBiometrics()
        self._device = device or DevicePresence()
        self._historical = historical or HistoricalContext()
        self._scorer = scorer or IdentityScorer()
        self._permissions = permissions or PermissionResolver()
        self._session = session_mgr or IdentitySessionManager()
        self._loaded = False

    def load_models(self) -> None:
        self._voice.load_model()
        self._anti_spoof.load_model()
        self._behavior.load_model()
        self._device.load_model()
        self._historical.load_model()
        self._loaded = True
        logger.info("Identity engine fully loaded")

    def verify(
        self,
        audio: Optional[np.ndarray] = None,
        text: Optional[str] = None,
        sample_rate: int = 16000,
        action: Optional[str] = None,
    ) -> IdentityResult:
        if not self._loaded:
            self.load_models()

        if not self._session.is_active:
            self._session.start_session()

        if self._session.should_reverify() or audio is not None:
            signals = self._collect_signals(audio, text, sample_rate)
            result = self._scorer.calculate(signals)
        else:
            result = IdentityResult(
                verified=self._session.is_owner,
                level=self._session.state.level if self._session.state else IdentityLevel.UNKNOWN,
                confidence=self._session.state.confidence if self._session.state else 0.0,
                permission=self._session.state.permission if self._session.state else PermissionFlags.GUEST_ONLY,
            )

        downgrade = self._session.check_downgrade(result)
        if downgrade:
            logger.warning("Identity downgraded: suspending privileged operations")
            self._session.suspend_privileged_ops()

        self._session.update(result)

        if text and self._behavior.is_loaded:
            self._historical.log_interaction(text)

        if action:
            allowed = self._permissions.resolve(result, action)
            if not allowed:
                logger.info("Action '%s' blocked by permission level %s", action, result.permission.value)

        result.session = self._session.state
        return result

    def verify_voice_only(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        text: Optional[str] = None,
    ) -> IdentityResult:
        return self.verify(audio=audio, text=text, sample_rate=sample_rate)

    def get_confidence(self) -> float:
        if self._session.state is None:
            return 0.0
        return self._session.state.confidence

    def get_identity_level(self) -> IdentityLevel:
        if self._session.state is None:
            return IdentityLevel.UNKNOWN
        return self._session.state.level

    def is_owner(self) -> bool:
        return self._session.is_owner

    def end_session(self) -> None:
        self._session.end_session()

    def _collect_signals(
        self,
        audio: Optional[np.ndarray],
        text: Optional[str],
        sample_rate: int,
    ) -> list[SignalResult]:
        signals: list[SignalResult] = []

        if audio is not None:
            voice_result = self._voice.verify(audio, sample_rate)
            signals.append(voice_result)

            liveness_result = self._anti_spoof.analyze(audio, sample_rate)
            signals.append(liveness_result)

        if text:
            behavior_result = self._behavior.analyze(text, audio, sample_rate)
            signals.append(behavior_result)

        device_result = self._device.scan()
        signals.append(device_result)

        historical_result = self._historical.evaluate()
        signals.append(historical_result)

        return signals

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def session(self):
        return self._session.state

    @property
    def voice(self) -> VoiceBiometrics:
        return self._voice

    @property
    def anti_spoof(self) -> AntiSpoofDetector:
        return self._anti_spoof

    @property
    def behavior(self) -> BehavioralBiometrics:
        return self._behavior

    @property
    def device(self) -> DevicePresence:
        return self._device

    @property
    def historical(self) -> HistoricalContext:
        return self._historical

    @property
    def scorer(self) -> IdentityScorer:
        return self._scorer

    @property
    def permissions(self) -> PermissionResolver:
        return self._permissions

    @property
    def session_manager(self) -> IdentitySessionManager:
        return self._session
