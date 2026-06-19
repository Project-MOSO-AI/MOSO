"""
MOSO Core - AI Inference Runtime

The core inference engine supporting:
- llama.cpp (CPU-optimized)
- ONNX Runtime (cross-platform)
"""

__version__ = "0.2.0"

from moso_core.inference.base import GenerationResult, GenerationStats, InferenceConfig, ModelBackend
from moso_core.inference.llama_cpp.backend import LlamaCPPBackend

try:
    from moso_core.inference.onnx_runtime.backend import OnnxRuntimeBackend
except ImportError:
    OnnxRuntimeBackend = None  # noqa: F811

from moso_core.orchestration.orchestrator import Modality, Orchestrator
from moso_core.pipelines.base import Pipeline, PipelineResult
from moso_core.pipelines.text.pipeline import TextPipeline
from moso_core.safety.guardrails import OutputGuard, PromptGuard

try:
    from moso_core.voice import (
        AudioConfig,
        AudioStream,
        CoquiTTS,
        ContinuousAuth,
        EnrollmentManager,
        PiperTTS,
        SpeakerEmbedder,
        SpeakerStore,
        SpeakerVerifier,
        VAD,
        VoicePipeline,
        VoicePipelineResult,
        VoiceSession,
        WakeWordDetector,
        WhisperSTT,
    )
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    from moso_core.identity import (
        IdentityLevel,
        IdentityResult,
        IdentityScorer,
        IdentitySessionManager,
        IdentityState,
        IdentityVerifier,
        PermissionFlags,
        PermissionResolver,
        VoiceBiometrics,
        AntiSpoofDetector,
        BehavioralBiometrics,
        DevicePresence,
        HistoricalContext,
    )
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False

try:
    from moso_core.memory import MemoryManager, MEMORY_AVAILABLE as _mem_flag
    MEMORY_AVAILABLE = _mem_flag
except ImportError:
    MEMORY_AVAILABLE = False

__all__ = [
    "InferenceConfig",
    "ModelBackend",
    "GenerationResult",
    "GenerationStats",
    "LlamaCPPBackend",
    "OnnxRuntimeBackend",
    "Pipeline",
    "PipelineResult",
    "TextPipeline",
    "Orchestrator",
    "Modality",
    "PromptGuard",
    "OutputGuard",
    "VOICE_AVAILABLE",
    "IDENTITY_AVAILABLE",
    "MEMORY_AVAILABLE",
    "MemoryManager",
]
