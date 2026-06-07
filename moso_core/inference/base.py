from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional

from pydantic import BaseModel, Field


class InferenceConfig(BaseModel):
    model_path: str = Field(..., description="Path to the GGUF model file")
    n_ctx: int = Field(default=2048, ge=128, description="Context window size")
    n_gpu_layers: int = Field(default=0, ge=0, description="Number of layers to offload to GPU")
    n_threads: Optional[int] = Field(default=None, ge=1, description="Number of CPU threads")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling threshold")
    top_k: int = Field(default=40, ge=0, description="Top-k sampling")
    repeat_penalty: float = Field(default=1.1, ge=1.0, description="Repeat penalty")
    max_tokens: int = Field(default=512, ge=1, description="Maximum tokens to generate")
    chat_format: Optional[str] = Field(default=None, description="Chat template format")
    seed: int = Field(default=42, description="Random seed")
    verbose: bool = Field(default=False, description="Enable verbose logging")


@dataclass
class GenerationStats:
    tokens_generated: int = 0
    total_time_ms: float = 0.0
    tokens_per_second: float = 0.0
    prompt_tokens: int = 0


@dataclass
class GenerationResult:
    text: str
    stats: GenerationStats = field(default_factory=GenerationStats)


class ModelBackend(ABC):
    def __init__(self, config: InferenceConfig):
        self.config = config
        self._model = None

    @abstractmethod
    def load(self) -> None:
        ...

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> GenerationResult:
        ...

    @abstractmethod
    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        ...

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> GenerationResult:
        ...

    @abstractmethod
    def chat_stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        ...

    @abstractmethod
    def unload(self) -> None:
        ...

    @abstractmethod
    def tokenize(self, text: str) -> list[int]:
        ...

    @abstractmethod
    def detokenize(self, tokens: list[int]) -> str:
        ...

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        ...

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, *args):
        self.unload()
