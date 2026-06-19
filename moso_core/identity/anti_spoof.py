import logging
from typing import Optional

import numpy as np

from moso_core.identity.models import SignalResult, WEIGHT_LIVENESS

logger = logging.getLogger(__name__)


class AntiSpoofDetector:
    def __init__(self, liveness_threshold: float = 0.85, device: str = "cpu"):
        self._threshold = liveness_threshold
        self._device = device
        self._loaded = False

    def load_model(self) -> None:
        self._loaded = True
        logger.info("Anti-spoof detector ready (threshold=%.2f)", self._threshold)

    def analyze(self, audio: np.ndarray, sample_rate: int = 16000) -> SignalResult:
        spectral_score = self._check_spectral_consistency(audio)
        energy_score = self._check_energy_distribution(audio)
        noise_score = self._check_noise_floor(audio)
        harmonic_score = self._check_harmonic_structure(audio)

        combined = 0.4 * spectral_score + 0.3 * energy_score + 0.2 * noise_score + 0.1 * harmonic_score
        is_live = combined >= self._threshold

        return SignalResult(
            signal_name="liveness_detection",
            confidence=combined,
            weight=WEIGHT_LIVENESS,
            details={
                "is_live": is_live,
                "spectral_score": spectral_score,
                "energy_score": energy_score,
                "noise_score": noise_score,
                "harmonic_score": harmonic_score,
                "threshold": self._threshold,
                "replay_suspected": spectral_score < 0.3,
                "synthetic_suspected": harmonic_score < 0.2,
            },
        )

    def _check_spectral_consistency(self, audio: np.ndarray) -> float:
        if len(audio) < 512:
            return 0.5
        from scipy import signal as sg
        _, _, Sxx = sg.spectrogram(audio, nperseg=256)
        energy_per_band = np.sum(Sxx, axis=1)
        energy_per_band = energy_per_band / (np.sum(energy_per_band) + 1e-10)
        entropy = -np.sum(energy_per_band * np.log(energy_per_band + 1e-10))
        max_entropy = np.log(len(energy_per_band))
        normalized = 1.0 - (entropy / max_entropy)
        return float(max(0.0, min(1.0, normalized)))

    def _check_energy_distribution(self, audio: np.ndarray) -> float:
        if len(audio) < 4:
            return 0.5
        envelope = np.abs(audio)
        chunks = np.array_split(envelope, max(4, len(envelope) // 1024))
        variances = [float(np.var(chunk)) for chunk in chunks]
        energy_variance = float(np.std(variances))
        natural_level = min(1.0, energy_variance / 0.01)
        return float(max(0.0, min(1.0, natural_level)))

    def _check_noise_floor(self, audio: np.ndarray) -> float:
        if len(audio) < 256:
            return 0.5
        silent = audio[: min(512, len(audio) // 4)]
        noise_floor = float(np.sqrt(np.mean(silent**2)))
        signal_peak = float(np.max(np.abs(audio)))
        if signal_peak < 1e-6:
            return 0.0
        snr = 20 * np.log10(signal_peak / (noise_floor + 1e-10))
        snr_score = min(1.0, max(0.0, (snr + 10) / 40))
        return snr_score

    def _check_harmonic_structure(self, audio: np.ndarray) -> float:
        if len(audio) < 2048:
            return 0.5
        fft_mag = np.abs(np.fft.rfft(audio))
        freqs = np.fft.rfftfreq(len(audio), d=1.0 / 16000)
        fft_mag = fft_mag / (np.sum(fft_mag) + 1e-10)
        peaks = []
        for f0 in [100, 200, 300, 400]:
            idx = np.argmin(np.abs(freqs - f0))
            peak = float(fft_mag[idx]) if idx < len(fft_mag) else 0.0
            peaks.append(peak)
        harmonic_strength = float(np.std(peaks) / (np.mean(peaks) + 1e-10))
        score = min(1.0, harmonic_strength * 5)
        return score

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def threshold(self) -> float:
        return self._threshold
