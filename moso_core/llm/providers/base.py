"""LLM Provider abstraction — unified interface for all backends."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, Optional


class ProviderType(str, Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class ProviderConfig:
    provider_type: ProviderType = ProviderType.LOCAL
    api_key: str = ""
    api_base_url: str = ""
    model: str = ""
    # Local-specific
    model_path: str = ""
    n_ctx: int = 2048
    n_gpu_layers: int = 0
    server_port: int = 8081
    server_host: str = "127.0.0.1"
    server_binary: str = ""
    # Generation
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    timeout: float = 30.0


class LLMProvider(ABC):
    """Unified interface every LLM backend must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        ...

    @abstractmethod
    def chat(
        self,
        message: str,
        system_prompt: str = "",
        history: Optional[list[dict]] = None,
    ) -> str:
        ...

    def chat_stream(
        self,
        message: str,
        system_prompt: str = "",
        history: Optional[list[dict]] = None,
    ) -> Iterator[str]:
        # Default: non-streaming fallback
        yield self.chat(message, system_prompt, history)

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 512,
    ) -> str:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...

    def start(self) -> bool:
        return True

    def stop(self):
        pass

    @property
    def is_available(self) -> bool:
        return self.health_check()

    @property
    def latency_ms(self) -> float:
        return 0.0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
