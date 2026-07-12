from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from moso_core.llm.models import LLMConfig, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

SERVER_BINARY_NAME = "llama-server.exe"
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")


class DirectLlama:
    """Fallback backend using llama-cpp-python directly (no server binary needed)."""
    def __init__(self, config: Optional[LLMConfig] = None):
        self._config = config or LLMConfig(model_path="")
        self._model = None

    @property
    def config(self) -> LLMConfig:
        return self._config

    @property
    def is_running(self) -> bool:
        return self._model is not None

    def start(self) -> bool:
        if self._model is not None:
            return True
        model_path = self._config.model_path
        if not model_path or not os.path.isfile(model_path):
            logger.error("Model not found: %s", model_path)
            return False
        try:
            from llama_cpp import Llama
            self._model = Llama(
                model_path=model_path,
                n_ctx=self._config.n_ctx,
                n_gpu_layers=self._config.n_gpu_layers,
                verbose=self._config.verbose,
            )
            logger.info("DirectLlama loaded model: %s", model_path)
            return True
        except Exception as e:
            logger.error("Failed to load model directly: %s", e)
            return False

    def complete(self, request: LLMRequest) -> LLMResponse:
        if self._model is None:
            if not self.start():
                return LLMResponse(text="", success=False, error="Model not loaded")
        try:
            start = time.perf_counter()
            response = self._model(
                request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                stop=["<|im_end|>", "<|end|>"],
                echo=False,
            )
            elapsed = (time.perf_counter() - start) * 1000
            text = response.get("choices", [{}])[0].get("text", "")
            tokens = response.get("usage", {}).get("total_tokens", 0)
            text = text.strip()
            # Strip Qwen think tags
            think_start = text.find("<think>")
            if think_start != -1:
                think_end = text.find("</think>", think_start)
                if think_end != -1:
                    text = text[think_end + 8:].strip()
                else:
                    # Incomplete think — strip from start
                    text = ""
            return LLMResponse(text=text.strip(), tokens_generated=tokens, elapsed_ms=elapsed)
        except Exception as e:
            logger.error("Direct completion failed: %s", e)
            return LLMResponse(text="", success=False, error=str(e))

    def stop(self):
        self._model = None
        logger.info("DirectLlama stopped")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


class LlamaServer:
    def __init__(self, config: Optional[LLMConfig] = None):
        self._config = config or LLMConfig(model_path="")
        self._process: Optional[subprocess.Popen] = None
        self._base_url = f"http://{self._config.server_host}:{self._config.server_port}"

    @property
    def config(self) -> LLMConfig:
        return self._config

    def __init__(self, config: Optional[LLMConfig] = None):
        self._config = config or LLMConfig(model_path="")
        self._process: Optional[subprocess.Popen] = None
        self._direct: Optional[DirectLlama] = None
        self._base_url = f"http://{self._config.server_host}:{self._config.server_port}"

    @property
    def is_running(self) -> bool:
        if self._direct is not None:
            return self._direct.is_running
        if self._process is None:
            return False
        return self._process.poll() is None

    def _find_server_binary(self) -> str:
        if self._config.server_binary and os.path.isfile(self._config.server_binary):
            return self._config.server_binary
        repo_root = Path(__file__).resolve().parent.parent.parent
        candidates = [
            str(repo_root / "llama-bin" / SERVER_BINARY_NAME),
            str(repo_root / "bin" / SERVER_BINARY_NAME),
            os.path.join(MODEL_DIR, "..", "llama-bin", SERVER_BINARY_NAME),
            SERVER_BINARY_NAME,
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return SERVER_BINARY_NAME

    def start(self) -> bool:
        if self.is_running:
            logger.info("Server already running")
            return True
        model_path = self._config.model_path
        if not model_path or not os.path.isfile(model_path):
            logger.error("Model not found: %s", model_path)
            return False
        binary = self._find_server_binary()
        if not os.path.isfile(binary):
            logger.warning("Server binary not found: %s. Falling back to DirectLlama (llama-cpp-python).", binary)
            self._direct = DirectLlama(self._config)
            return self._direct.start()
        cmd = [
            binary,
            "--model", model_path,
            "--host", self._config.server_host,
            "--port", str(self._config.server_port),
            "--ctx-size", str(self._config.n_ctx),
            "--n-gpu-layers", str(self._config.n_gpu_layers),
        ]
        logger.info("Starting llama-server: %s", " ".join(cmd))
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
        )
        if not self._wait_for_ready():
            logger.error("Server failed to start, terminating process")
            self.stop()
            return False
        return True

    def _wait_for_ready(self, timeout: float = 30.0) -> bool:
        start = time.perf_counter()
        while time.perf_counter() - start < timeout:
            try:
                req = urllib.request.Request(f"{self._base_url}/health")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        logger.info("Server ready")
                        return True
            except (urllib.error.URLError, urllib.error.HTTPError, OSError):
                pass
            time.sleep(0.5)
        logger.error("Server did not start within %.0fs", timeout)
        return False

    def complete(self, request: LLMRequest) -> LLMResponse:
        if self._direct is not None:
            return self._direct.complete(request)
        if not self.is_running:
            if not self.start():
                return LLMResponse(text="", success=False, error="Server not running")
        payload = {
            "prompt": request.prompt,
            "n_predict": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": False,
        }
        if request.system_prompt:
            payload["system_prompt"] = request.system_prompt
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self._base_url}/completion",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            start = time.perf_counter()
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode())
            elapsed = (time.perf_counter() - start) * 1000
            return LLMResponse(
                text=body.get("content", ""),
                tokens_generated=body.get("tokens_generated", 0),
                total_tokens=body.get("tokens_evaluated", 0),
                elapsed_ms=elapsed,
            )
        except Exception as e:
            logger.error("Completion failed: %s", e)
            return LLMResponse(text="", success=False, error=str(e))

    def stop(self):
        if self._direct is not None:
            self._direct.stop()
            self._direct = None
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    self._process.kill()
                    self._process.wait(timeout=2)
                except Exception:
                    pass
            except Exception:
                pass
            self._process = None
            logger.info("Server stopped")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
