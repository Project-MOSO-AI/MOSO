"""
MOSO Core - AI Inference Runtime

The core inference engine supporting:
- llama.cpp (CPU-optimized)
- ONNX Runtime (cross-platform)
"""

__version__ = "0.3.0"

from moso_core.inference.base import GenerationResult, GenerationStats, InferenceConfig, ModelBackend

try:
    from moso_core.inference.llama_cpp.backend import LlamaCPPBackend
except ImportError:
    LlamaCPPBackend = None  # noqa: F811

try:
    from moso_core.inference.onnx_runtime.backend import OnnxRuntimeBackend
except (ImportError, Exception):
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

try:
    from moso_core.resources import ResourceManager, RESOURCES_AVAILABLE as _res_flag
    RESOURCES_AVAILABLE = _res_flag
except ImportError:
    RESOURCES_AVAILABLE = False

try:
    from moso_core.tools import ToolRegistry, TOOLS_AVAILABLE as _tool_flag
    TOOLS_AVAILABLE = _tool_flag
except ImportError:
    TOOLS_AVAILABLE = False

try:
    from moso_core.agents import AGENTS_AVAILABLE as _agents_flag
    AGENTS_AVAILABLE = _agents_flag
except ImportError:
    AGENTS_AVAILABLE = False

try:
    from moso_core.computer_use import COMPUTER_USE_AVAILABLE as _cu_flag
    COMPUTER_USE_AVAILABLE = _cu_flag
except ImportError:
    COMPUTER_USE_AVAILABLE = False

try:
    from moso_core.system_intelligence import SYSTEM_INTELLIGENCE_AVAILABLE as _si_flag
    SYSTEM_INTELLIGENCE_AVAILABLE = _si_flag
except ImportError:
    SYSTEM_INTELLIGENCE_AVAILABLE = False

try:
    from moso_core.risk import RISK_AVAILABLE as _risk_flag
    RISK_AVAILABLE = _risk_flag
except ImportError:
    RISK_AVAILABLE = False

try:
    from moso_core.vision import VISION_AVAILABLE as _vision_flag
    VISION_AVAILABLE = _vision_flag
except ImportError:
    VISION_AVAILABLE = False

try:
    from moso_core.realtime import RealtimeManager, REALTIME_AVAILABLE as _rt_flag
    REALTIME_AVAILABLE = _rt_flag
except ImportError:
    REALTIME_AVAILABLE = False

try:
    from moso_core.llm import LLM_AVAILABLE as _llm_flag, LLMConfig, LLMManager, LlamaServer
    LLM_AVAILABLE = _llm_flag
except ImportError:
    LLM_AVAILABLE = False

# Infrastructure modules — always available
from moso_core.diagnostics import DiagnosticReport, HealthStatus, run_diagnostics
from moso_core.dependency_installer import DependencyInstaller
from moso_core.model_manager import ModelManager, SystemResources
from moso_core.runtime_manager import RuntimeManager, Service, ServiceStatus
from moso_core.download_manager import DownloadManager
from moso_core.benchmarks import BenchmarkReport, run_all_benchmarks

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
    "RESOURCES_AVAILABLE",
    "ResourceManager",
    "TOOLS_AVAILABLE",
    "ToolRegistry",
    "AGENTS_AVAILABLE",
    "COMPUTER_USE_AVAILABLE",
    "SYSTEM_INTELLIGENCE_AVAILABLE",
    "RISK_AVAILABLE",
    "VISION_AVAILABLE",
    "LLM_AVAILABLE",
    "LLMConfig",
    "LLMManager",
    "LlamaServer",
    "REALTIME_AVAILABLE",
    "RealtimeManager",
    # Infrastructure
    "run_diagnostics",
    "DiagnosticReport",
    "HealthStatus",
    "DependencyInstaller",
    "ModelManager",
    "SystemResources",
    "RuntimeManager",
    "Service",
    "ServiceStatus",
    "DownloadManager",
    "BenchmarkReport",
    "run_all_benchmarks",
]
