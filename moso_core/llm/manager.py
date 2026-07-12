from __future__ import annotations

import logging
import threading
from typing import Optional

from moso_core.llm.backend import LlamaServer
from moso_core.llm.models import LLMConfig, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

_CHAT_TIMEOUT = 15.0


class LLMManager:
    def __init__(self, config: LLMConfig):
        self._config = config
        self._server = LlamaServer(config)

    @property
    def config(self) -> LLMConfig:
        return self._config

    @property
    def server(self) -> LlamaServer:
        return self._server

    def start(self) -> bool:
        return self._server.start()

    def stop(self):
        self._server.stop()

    def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 512) -> LLMResponse:
        req = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
        )
        return self._server.complete(req)

    def chat(self, message: str, history: Optional[list[dict]] = None) -> str:
        if history is None:
            history = []
        context = self._build_chat_context(message, history)
        result = [""]

        def _run():
            try:
                resp = self.complete(context, max_tokens=64)
                result[0] = resp.text
            except Exception as e:
                logger.debug("LLM chat error: %s", e)
                result[0] = ""

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=_CHAT_TIMEOUT)
        if t.is_alive():
            logger.warning("LLM chat timed out after %.1fs", _CHAT_TIMEOUT)
            return ""
        return result[0]

    def _build_chat_context(self, message: str, history: list[dict]) -> str:
        lines = []
        for turn in history[-8:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            lines.append(f"<|im_start|>{role}\n{content}\n<|im_end|>")
        lines.append(f"<|im_start|>user\n{message}\n<|im_end|>")
        lines.append("<|im_start|>assistant\n")
        return "\n".join(lines)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
