"""
MOSO Core - AI Inference Runtime

The core inference engine supporting multiple backends:
- llama.cpp (CPU-optimized)
- ONNX Runtime (cross-platform)
- CoreML (Apple Neural Engine)
- MLX (Apple Silicon)
- ExecuTorch (on-device PyTorch)
"""

__version__ = "0.1.0"

from moso_core.inference.base import GenerationResult, GenerationStats, InferenceConfig, ModelBackend
from moso_core.inference.llama_cpp.backend import LlamaCPPBackend
from moso_core.orchestration.orchestrator import Modality, Orchestrator
from moso_core.pipelines.base import Pipeline, PipelineResult
from moso_core.pipelines.text.pipeline import TextPipeline
from moso_core.safety.guardrails import OutputGuard, PromptGuard

__all__ = [
    "InferenceConfig",
    "ModelBackend",
    "GenerationResult",
    "GenerationStats",
    "LlamaCPPBackend",
    "Pipeline",
    "PipelineResult",
    "TextPipeline",
    "Orchestrator",
    "Modality",
    "PromptGuard",
    "OutputGuard",
]
