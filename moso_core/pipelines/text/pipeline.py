import logging
from typing import Iterator, Optional

from moso_core.inference.base import ModelBackend
from moso_core.pipelines.base import Pipeline, PipelineResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are M0S0, a privacy-first, local-first adaptive AI assistant. "
    "You are helpful, harmless, and honest. You run entirely on the user's device. "
    "Respond concisely and naturally."
)


class TextPipeline(Pipeline):
    def __init__(
        self,
        backend: ModelBackend,
        system_prompt: str = SYSTEM_PROMPT,
        max_history: int = 20,
    ):
        self._backend = backend
        self._system_prompt = system_prompt
        self._max_history = max_history
        self._messages: list[dict] = [{"role": "system", "content": system_prompt}]

    def run(self, prompt: str, **kwargs) -> PipelineResult:
        self._messages.append({"role": "user", "content": prompt})
        result = self._backend.chat(self._messages, **kwargs)
        self._messages.append({"role": "assistant", "content": result.text})
        self._trim_history()
        return PipelineResult(text=result.text, generation=result, messages=list(self._messages))

    def run_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        self._messages.append({"role": "user", "content": prompt})

        collected: list[str] = []
        for chunk in self._backend.chat_stream(self._messages, **kwargs):
            collected.append(chunk)
            yield chunk

        full_reply = "".join(collected)
        self._messages.append({"role": "assistant", "content": full_reply})
        self._trim_history()

    def reset(self) -> None:
        self._messages = [{"role": "system", "content": self._system_prompt}]
        logger.info("Conversation reset")

    def set_system_prompt(self, prompt: str) -> None:
        self._system_prompt = prompt
        if self._messages and self._messages[0]["role"] == "system":
            self._messages[0]["content"] = prompt

    def set_backend(self, backend: ModelBackend) -> None:
        self._backend = backend

    @property
    def history(self) -> list[dict]:
        return list(self._messages)

    @property
    def backend(self) -> ModelBackend:
        return self._backend

    def _trim_history(self) -> None:
        if len(self._messages) > self._max_history * 2 + 1:
            keep = [self._messages[0]]
            keep.extend(self._messages[-(self._max_history * 2) :])
            self._messages = keep
