"""Local LLM provider -- wraps existing LlamaServer/DirectLlama."""
from __future__ import annotations

import logging
import time
from typing import Iterator, Optional

from moso_core.llm.providers.base import LLMProvider, ProviderConfig, ProviderType

logger = logging.getLogger(__name__)


class LocalProvider(LLMProvider):
    """Local llama.cpp inference via LlamaServer or DirectLlama."""

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._server = None
        self._last_latency = 0.0

    @property
    def name(self) -> str:
        return "local"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.LOCAL

    @property
    def latency_ms(self) -> float:
        return self._last_latency

    def _ensure_server(self):
        if self._server is not None:
            return
        from moso_core.llm.models import LLMConfig
        from moso_core.llm.backend import LlamaServer
        llm_config = LLMConfig(
            model_path=self._config.model_path,
            n_ctx=self._config.n_ctx,
            n_gpu_layers=self._config.n_gpu_layers,
            server_port=self._config.server_port,
            server_host=self._config.server_host,
            server_binary=self._config.server_binary,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )
        self._server = LlamaServer(llm_config)

    def start(self) -> bool:
        self._ensure_server()
        return self._server.start()

    def stop(self):
        if self._server:
            self._server.stop()

    @property
    def is_available(self) -> bool:
        self._ensure_server()
        return self._server.is_running

    def chat(self, message, system_prompt="", history=None):
        self._ensure_server()
        history = history or []
        context = self._build_context(message, history)
        start = time.perf_counter()
        result = self._server.complete(context)
        self._last_latency = (time.perf_counter() - start) * 1000
        return result.text

    def chat_stream(self, message, system_prompt="", history=None):
        yield self.chat(message, system_prompt, history)

    def complete(self, prompt, system_prompt="", max_tokens=512):
        self._ensure_server()
        from moso_core.llm.models import LLMRequest
        req = LLMRequest(
            prompt=prompt, system_prompt=system_prompt,
            max_tokens=max_tokens, temperature=self._config.temperature,
        )
        start = time.perf_counter()
        result = self._server.complete(req)
        self._last_latency = (time.perf_counter() - start) * 1000
        return result.text

    def health_check(self):
        try:
            self._ensure_server()
            return self._server.is_running or bool(self._config.model_path)
        except Exception:
            return False
