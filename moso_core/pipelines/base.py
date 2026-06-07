from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator

from moso_core.inference.base import GenerationResult


@dataclass
class PipelineResult:
    text: str
    generation: GenerationResult
    messages: list[dict] = field(default_factory=list)


class Pipeline(ABC):
    @abstractmethod
    def run(self, prompt: str, **kwargs) -> PipelineResult:
        ...

    @abstractmethod
    def run_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...

    @property
    @abstractmethod
    def history(self) -> list[dict]:
        ...
