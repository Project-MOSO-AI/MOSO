import logging
import time
from collections import deque
from typing import Optional

import numpy as np

from moso_core.identity.models import SignalResult, WEIGHT_BEHAVIOR

logger = logging.getLogger(__name__)


class BehavioralBiometrics:
    def __init__(self, max_history: int = 100):
        self._max_history = max_history
        self._command_times: deque = deque(maxlen=max_history)
        self._command_lengths: deque = deque(maxlen=max_history)
        self._vocabulary: dict[str, int] = {}
        self._speaking_speeds: deque = deque(maxlen=50)
        self._pause_durations: deque = deque(maxlen=50)
        self._baseline_established = False
        self._owner_profile: Optional[dict] = None

    def load_model(self) -> None:
        logger.info("Behavioral biometrics ready")

    def establish_baseline(self, text: str, audio: Optional[np.ndarray] = None, sample_rate: int = 16000) -> None:
        words = text.lower().split()
        for word in words:
            self._vocabulary[word] = self._vocabulary.get(word, 0) + 1
        self._command_lengths.append(len(words))
        self._command_times.append(time.time())
        if audio is not None:
            self._analyze_audio_cadence(audio, sample_rate)

        if len(self._command_times) >= 10:
            self._owner_profile = self._build_profile()
            self._baseline_established = True
            logger.info("Behavioral baseline established (%d commands)", len(self._command_times))

    def analyze(self, text: str, audio: Optional[np.ndarray] = None, sample_rate: int = 16000) -> SignalResult:
        if not self._baseline_established or self._owner_profile is None:
            self.establish_baseline(text, audio, sample_rate)
            return SignalResult(
                signal_name="behavioral_biometrics",
                confidence=0.5,
                weight=WEIGHT_BEHAVIOR,
                details={"baseline_establishing": True, "samples": len(self._command_times)},
            )

        words = text.lower().split()
        vocab_score = self._score_vocabulary(words)
        length_score = self._score_length(len(words))
        timing_score = self._score_timing()

        audio_score = 0.5
        if audio is not None:
            self._analyze_audio_cadence(audio, sample_rate)
            audio_score = self._score_audio_cadence()

        combined = 0.35 * vocab_score + 0.25 * length_score + 0.25 * timing_score + 0.15 * audio_score

        return SignalResult(
            signal_name="behavioral_biometrics",
            confidence=combined,
            weight=WEIGHT_BEHAVIOR,
            details={
                "vocabulary_score": vocab_score,
                "length_score": length_score,
                "timing_score": timing_score,
                "audio_cadence_score": audio_score,
                "baseline_samples": len(self._command_times),
                "consistent": combined > 0.7,
            },
        )

    def _analyze_audio_cadence(self, audio: np.ndarray, sample_rate: int) -> None:
        if len(audio) < sample_rate:
            return
        energy = np.abs(audio)
        chunk_size = int(sample_rate * 0.03)
        speech_chunks = 0
        total_chunks = 0
        pause_chunks = []
        current_pause = 0
        in_pause = False

        for i in range(0, len(energy) - chunk_size, chunk_size):
            chunk_rms = np.sqrt(np.mean(energy[i : i + chunk_size] ** 2))
            is_speech = chunk_rms > 0.01
            total_chunks += 1
            if is_speech:
                speech_chunks += 1
                if in_pause:
                    pause_chunks.append(current_pause)
                    current_pause = 0
                    in_pause = False
            else:
                current_pause += 1
                in_pause = True

        if speech_chunks > 0:
            speed = speech_chunks / total_chunks
            self._speaking_speeds.append(speed)
        if pause_chunks:
            avg_pause = np.mean(pause_chunks) * 0.03
            self._pause_durations.append(avg_pause)

    def _build_profile(self) -> dict:
        return {
            "avg_length": float(np.mean(self._command_lengths)) if self._command_lengths else 0,
            "std_length": float(np.std(self._command_lengths)) if len(self._command_lengths) > 1 else 1,
            "top_words": sorted(self._vocabulary.items(), key=lambda x: -x[1])[:50],
            "avg_speed": float(np.mean(self._speaking_speeds)) if self._speaking_speeds else 0.5,
            "avg_pause": float(np.mean(self._pause_durations)) if self._pause_durations else 0.2,
        }

    def _score_vocabulary(self, words: list[str]) -> float:
        if not self._owner_profile or not words:
            return 0.5
        top_words = set(w for w, _ in self._owner_profile["top_words"])
        matches = sum(1 for w in words if w in top_words)
        return min(1.0, matches / max(1, len(words)))

    def _score_length(self, length: int) -> float:
        if not self._owner_profile:
            return 0.5
        avg = self._owner_profile["avg_length"]
        std = max(self._owner_profile["std_length"], 1)
        deviation = abs(length - avg) / std
        return float(max(0.0, min(1.0, 1.0 - (deviation / 5))))

    def _score_timing(self) -> float:
        if len(self._command_times) < 2:
            return 0.5
        intervals = np.diff(list(self._command_times))
        recent = intervals[-min(5, len(intervals)):]
        consistency = 1.0 - min(1.0, float(np.std(recent)) / 10.0)
        return consistency

    def _score_audio_cadence(self) -> float:
        if not self._owner_profile:
            return 0.5
        if not self._speaking_speeds:
            return 0.5
        avg_speed = float(np.mean(self._speaking_speeds))
        baseline_speed = self._owner_profile["avg_speed"]
        deviation = abs(avg_speed - baseline_speed)
        return float(max(0.0, min(1.0, 1.0 - deviation)))

    @property
    def is_loaded(self) -> bool:
        return self._baseline_established

    def reset(self) -> None:
        self._command_times.clear()
        self._command_lengths.clear()
        self._vocabulary.clear()
        self._speaking_speeds.clear()
        self._pause_durations.clear()
        self._baseline_established = False
        self._owner_profile = None
