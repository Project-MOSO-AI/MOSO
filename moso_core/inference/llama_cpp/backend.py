import logging
import time
from typing import Iterator, Optional

from llama_cpp import Llama

from moso_core.inference.base import (
    GenerationResult,
    GenerationStats,
    InferenceConfig,
    ModelBackend,
)

logger = logging.getLogger(__name__)


class LlamaCPPBackend(ModelBackend):
    def __init__(self, config: InferenceConfig):
        super().__init__(config)
        self._model: Optional[Llama] = None
        self._llama_kwargs: dict = {}

    def load(self) -> None:
        if self._model is not None:
            logger.warning("Model already loaded, unloading first")
            self.unload()

        self._llama_kwargs = {
            "model_path": self.config.model_path,
            "n_ctx": self.config.n_ctx,
            "n_gpu_layers": self.config.n_gpu_layers,
            "n_threads": self.config.n_threads,
            "seed": self.config.seed,
            "verbose": self.config.verbose,
            "chat_format": self.config.chat_format,
        }

        logger.info(
            "Loading model %s (ctx=%d, gpu_layers=%d, threads=%s)",
            self.config.model_path,
            self.config.n_ctx,
            self.config.n_gpu_layers,
            self.config.n_threads or "auto",
        )
        start = time.perf_counter()
        self._model = Llama(**self._llama_kwargs)
        elapsed = time.perf_counter() - start
        logger.info("Model loaded in %.2fs", elapsed)

    def generate(self, prompt: str, **kwargs) -> GenerationResult:
        self._require_loaded()
        merged = {**self._sampling_params(), **kwargs}
        start = time.perf_counter()
        output = self._model.create_completion(prompt, **merged)
        elapsed = time.perf_counter() - start
        return self._build_result(output, elapsed, prompt)

    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        self._require_loaded()
        merged = {**self._sampling_params(), **kwargs}
        merged["stream"] = True
        for chunk in self._model.create_completion(prompt, **merged):
            text = chunk.get("choices", [{}])[0].get("text", "")
            if text:
                yield text

    def chat(self, messages: list[dict], **kwargs) -> GenerationResult:
        self._require_loaded()
        merged = {**self._sampling_params(), **kwargs}
        start = time.perf_counter()
        output = self._model.create_chat_completion(messages, **merged)
        elapsed = time.perf_counter() - start

        text = output.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = output.get("usage", {})
        stats = GenerationStats(
            tokens_generated=usage.get("completion_tokens", 0),
            total_time_ms=round(elapsed * 1000, 2),
            tokens_per_second=round(usage.get("completion_tokens", 0) / elapsed, 2)
            if elapsed > 0
            else 0.0,
            prompt_tokens=usage.get("prompt_tokens", 0),
        )
        return GenerationResult(text=text, stats=stats)

    def chat_stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        self._require_loaded()
        merged = {**self._sampling_params(), **kwargs}
        merged["stream"] = True
        for chunk in self._model.create_chat_completion(messages, **merged):
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            text = delta.get("content", "")
            if text:
                yield text

    def unload(self) -> None:
        if self._model is not None:
            logger.info("Unloading model")
            del self._model
            self._model = None

    def tokenize(self, text: str) -> list[int]:
        self._require_loaded()
        return self._model.tokenize(text.encode("utf-8"))

    def detokenize(self, tokens: list[int]) -> str:
        self._require_loaded()
        return self._model.detokenize(tokens).decode("utf-8", errors="replace")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _require_loaded(self) -> None:
        if self._model is None:
            raise RuntimeError(
                "Model is not loaded. Call load() first or use the context manager."
            )

    def _sampling_params(self) -> dict:
        return {
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "repeat_penalty": self.config.repeat_penalty,
            "max_tokens": self.config.max_tokens,
        }

    @staticmethod
    def _build_result(output: dict, elapsed: float, prompt: str) -> GenerationResult:
        text = output.get("choices", [{}])[0].get("text", "")
        usage = output.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        stats = GenerationStats(
            tokens_generated=completion_tokens,
            total_time_ms=round(elapsed * 1000, 2),
            tokens_per_second=round(completion_tokens / elapsed, 2)
            if elapsed > 0
            else 0.0,
            prompt_tokens=prompt_tokens,
        )
        return GenerationResult(text=text, stats=stats)
