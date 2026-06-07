import logging
from enum import Enum
from typing import Iterator, Optional

from moso_core.inference.base import InferenceConfig, ModelBackend
from moso_core.inference.llama_cpp.backend import LlamaCPPBackend
from moso_core.pipelines.base import Pipeline, PipelineResult
from moso_core.pipelines.text.pipeline import TextPipeline
from moso_core.safety.guardrails import OutputGuard, PromptGuard

logger = logging.getLogger(__name__)


class Modality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    MULTIMODAL = "multimodal"
    REASONING = "reasoning"


class Orchestrator:
    def __init__(
        self,
        config: InferenceConfig,
        system_prompt: Optional[str] = None,
        enable_safety: bool = True,
    ):
        self._config = config
        self._backend: Optional[ModelBackend] = None
        self._pipelines: dict[Modality, Pipeline] = {}
        self._prompt_guard = PromptGuard() if enable_safety else None
        self._output_guard = OutputGuard() if enable_safety else None

        self._text_pipeline = TextPipeline(
            backend=self._get_or_create_backend(),
            system_prompt=system_prompt or "You are M0S0, a privacy-first, local-first adaptive AI assistant.",
        )
        self._pipelines[Modality.TEXT] = self._text_pipeline

    def process(self, prompt: str, modality: Modality = Modality.TEXT, **kwargs) -> PipelineResult:
        if self._prompt_guard:
            guard_result = self._prompt_guard.check(prompt)
            if not guard_result.allowed:
                logger.warning("Prompt blocked: %s", guard_result.reason)
                return PipelineResult(
                    text=f"I cannot process that request. {guard_result.reason}",
                    generation=None,
                )

        pipeline = self._resolve_pipeline(modality)
        result = pipeline.run(prompt, **kwargs)

        if self._output_guard:
            result = self._output_guard.sanitize(result)

        return result

    def process_stream(
        self, prompt: str, modality: Modality = Modality.TEXT, **kwargs
    ) -> Iterator[str]:
        if self._prompt_guard:
            guard_result = self._prompt_guard.check(prompt)
            if not guard_result.allowed:
                yield f"I cannot process that request. {guard_result.reason}"
                return

        pipeline = self._resolve_pipeline(modality)
        yield from pipeline.run_stream(prompt, **kwargs)

    def reset_conversation(self, modality: Modality = Modality.TEXT) -> None:
        pipeline = self._pipelines.get(modality)
        if pipeline:
            pipeline.reset()

    def load(self) -> None:
        self._get_or_create_backend().load()

    def unload(self) -> None:
        if self._backend is not None:
            self._backend.unload()

    @property
    def backend(self) -> ModelBackend:
        return self._get_or_create_backend()

    @property
    def text_pipeline(self) -> TextPipeline:
        return self._text_pipeline

    def _resolve_pipeline(self, modality: Modality) -> Pipeline:
        if modality not in self._pipelines:
            supported = list(self._pipelines.keys())
            raise ValueError(
                f"Unsupported modality '{modality.value}'. "
                f"Supported: {[m.value for m in supported]}"
            )
        return self._pipelines[modality]

    def _get_or_create_backend(self) -> ModelBackend:
        if self._backend is None:
            self._backend = LlamaCPPBackend(self._config)
        return self._backend

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, *args):
        self.unload()
