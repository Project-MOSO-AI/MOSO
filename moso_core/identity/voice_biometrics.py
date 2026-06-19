import logging
from typing import Optional

import numpy as np

from moso_core.identity.models import SignalResult, WEIGHT_VOICE

logger = logging.getLogger(__name__)


class VoiceBiometrics:
    def __init__(self, threshold: float = 0.95, embedder=None):
        self._threshold = threshold
        self._embedder = embedder
        self._loaded = False

    def load_model(self) -> None:
        if self._embedder is None:
            from moso_core.voice.speaker import SpeakerEmbedder
            self._embedder = SpeakerEmbedder()
        if not self._embedder.is_loaded:
            self._embedder.load_model()
        self._loaded = True
        logger.info("Voice biometrics ready (threshold=%.2f)", self._threshold)

    def verify(
        self, audio: np.ndarray, sample_rate: int = 16000, profile_name: str = "owner"
    ) -> SignalResult:
        if not self._loaded:
            self.load_model()

        from moso_core.voice.speaker import SpeakerVerifier, SpeakerStore

        verifier = SpeakerVerifier(embedder=self._embedder)
        result = verifier.verify(audio, sample_rate, profile_name)

        return SignalResult(
            signal_name="voice_biometrics",
            confidence=result.confidence,
            weight=WEIGHT_VOICE,
            details={
                "verified": result.verified,
                "auth_level": result.auth_level.value,
                "embedding_match": result.confidence,
                "threshold": self._threshold,
            },
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def embedder(self):
        return self._embedder
