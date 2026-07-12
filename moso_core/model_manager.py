"""Model manager — discover, install, delete, and monitor local GGUF models."""
from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# ponytail: curated list, not a full registry — add models as needed
RECOMMENDED_MODELS: dict[str, dict] = {
    "phi-3-mini-4k": {
        "name": "Phi-3 Mini 4K Instruct",
        "repo": "microsoft/Phi-3-mini-4k-instruct-gguf",
        "file": "Phi-3-mini-4k-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_k_m.gguf",
        "size_mb": 2200,
        "context": 4096,
        "params": "3.8B",
        "quant": "Q4_K_M",
        "description": "Fast, small, good for general tasks",
        "category": "general",
    },
    "qwen3-8b": {
        "name": "Qwen3 8B Instruct",
        "repo": "Qwen/Qwen3-8B-GGUF",
        "file": "Qwen3-8B-Q4_K_M.gguf",
        "url": "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf",
        "size_mb": 5000,
        "context": 8192,
        "params": "8B",
        "quant": "Q4_K_M",
        "description": "Strong reasoning, good for complex tasks",
        "category": "general",
    },
    "llama-3.1-8b": {
        "name": "Llama 3.1 8B Instruct",
        "repo": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "file": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size_mb": 4900,
        "context": 8192,
        "params": "8B",
        "quant": "Q4_K_M",
        "description": "Well-rounded, strong instruction following",
        "category": "general",
    },
    "llama-3.2-3b": {
        "name": "Llama 3.2 3B Instruct",
        "repo": "bartowski/Meta-Llama-3.2-3B-Instruct-GGUF",
        "file": "Meta-Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Meta-Llama-3.2-3B-Instruct-GGUF/resolve/main/Meta-Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_mb": 2000,
        "context": 4096,
        "params": "3B",
        "quant": "Q4_K_M",
        "description": "Lightweight, fast, good for low RAM",
        "category": "general",
    },
}


class ModelStatus(str, Enum):
    INSTALLED = "installed"
    DOWNLOADING = "downloading"
    NOT_INSTALLED = "not_installed"
    CORRUPTED = "corrupted"


@dataclass
class ModelInfo:
    key: str
    name: str
    file: str
    path: str = ""
    status: ModelStatus = ModelStatus.NOT_INSTALLED
    size_bytes: int = 0
    context: int = 0
    params: str = ""
    quant: str = ""
    description: str = ""
    category: str = ""
    url: str = ""

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "file": self.file,
            "path": self.path,
            "status": self.status.value,
            "size_mb": round(self.size_mb, 1),
            "context": self.context,
            "params": self.params,
            "quant": self.quant,
            "description": self.description,
        }


@dataclass
class SystemResources:
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    vram_total_gb: float = 0.0
    vram_available_gb: float = 0.0
    gpu_name: str = ""
    disk_free_gb: float = 0.0
    has_gpu: bool = False

    @staticmethod
    def detect() -> SystemResources:
        res = SystemResources()
        if PSUTIL_AVAILABLE:
            vm = psutil.virtual_memory()
            res.ram_total_gb = vm.total / (1024 ** 3)
            res.ram_available_gb = vm.available / (1024 ** 3)
            usage = shutil.disk_usage(".")
            res.disk_free_gb = usage.free / (1024 ** 3)
        if TORCH_AVAILABLE:
            try:
                if torch.cuda.is_available():
                    res.has_gpu = True
                    res.gpu_name = torch.cuda.get_device_name(0)
                    props = torch.cuda.get_device_properties(0)
                    res.vram_total_gb = props.total_mem / (1024 ** 3)
                    res.vram_available_gb = res.vram_total_gb  # approximate
            except Exception:
                pass
        return res

    def can_run_model(self, size_mb: int) -> tuple[bool, str]:
        needed_gb = (size_mb * 1.2) / 1024  # model + 20% overhead
        if self.ram_available_gb > 0 and self.ram_available_gb < needed_gb:
            return False, f"Need ~{needed_gb:.1f} GB RAM, only {self.ram_available_gb:.1f} GB available"
        if self.disk_free_gb > 0 and self.disk_free_gb < size_mb / 1024:
            return False, f"Need ~{size_mb / 1024:.1f} GB disk, only {self.disk_free_gb:.1f} GB free"
        return True, ""

    def estimated_speed(self, params: str) -> str:
        param_num = 0
        try:
            param_num = float(params.replace("B", "").strip())
        except ValueError:
            pass
        if self.has_gpu:
            if param_num <= 3:
                return "~40-60 tok/s"
            elif param_num <= 8:
                return "~20-35 tok/s"
            else:
                return "~8-15 tok/s"
        if param_num <= 3:
            return "~10-20 tok/s"
        elif param_num <= 8:
            return "~5-10 tok/s"
        else:
            return "~2-5 tok/s"


class ModelManager:
    def __init__(self, models_dir: Optional[str] = None):
        self._models_dir = models_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "models"
        )
        os.makedirs(self._models_dir, exist_ok=True)
        self._models: dict[str, ModelInfo] = {}
        self._scan()

    def _scan(self):
        self._models.clear()
        for key, spec in RECOMMENDED_MODELS.items():
            path = os.path.join(self._models_dir, spec["file"])
            installed = os.path.isfile(path)
            size = os.path.getsize(path) if installed else 0
            self._models[key] = ModelInfo(
                key=key,
                name=spec["name"],
                file=spec["file"],
                path=path if installed else "",
                status=ModelStatus.INSTALLED if installed else ModelStatus.NOT_INSTALLED,
                size_bytes=size,
                context=spec.get("context", 0),
                params=spec.get("params", ""),
                quant=spec.get("quant", ""),
                description=spec.get("description", ""),
                category=spec.get("category", ""),
                url=spec.get("url", ""),
            )
        # Also scan for any .gguf files not in recommended list
        for f in os.listdir(self._models_dir):
            if f.endswith(".gguf"):
                if not any(m.file == f for m in self._models.values()):
                    path = os.path.join(self._models_dir, f)
                    self._models[f] = ModelInfo(
                        key=f,
                        name=os.path.splitext(f)[0],
                        file=f,
                        path=path,
                        status=ModelStatus.INSTALLED,
                        size_bytes=os.path.getsize(path),
                        description="Custom model",
                        category="custom",
                    )

    def list_models(self) -> list[ModelInfo]:
        self._scan()
        return list(self._models.values())

    def get_model(self, key: str) -> Optional[ModelInfo]:
        return self._models.get(key)

    def installed_models(self) -> list[ModelInfo]:
        return [m for m in self._models.values() if m.status == ModelStatus.INSTALLED]

    def available_models(self) -> list[ModelInfo]:
        return [m for m in RECOMMENDED_MODELS.values()]

    def delete_model(self, key: str) -> bool:
        model = self._models.get(key)
        if not model or not model.path:
            return False
        try:
            os.remove(model.path)
            self._scan()
            logger.info("Deleted model: %s", model.file)
            return True
        except Exception as e:
            logger.error("Failed to delete %s: %s", model.file, e)
            return False

    def get_download_url(self, key: str) -> Optional[str]:
        spec = RECOMMENDED_MODELS.get(key)
        return spec.get("url") if spec else None

    def resources(self) -> SystemResources:
        return SystemResources.detect()

    def get_model_usage(self) -> list[dict]:
        total_size = sum(m.size_bytes for m in self._models.values() if m.status == ModelStatus.INSTALLED)
        res = self.resources()
        return [
            {"total_models": sum(1 for m in self._models.values() if m.status == ModelStatus.INSTALLED)},
            {"total_size_mb": round(total_size / (1024 * 1024), 1)},
            {"ram_total_gb": round(res.ram_total_gb, 1)},
            {"ram_available_gb": round(res.ram_available_gb, 1)},
            {"disk_free_gb": round(res.disk_free_gb, 1)},
            {"gpu": res.gpu_name or "None"},
            {"vram_gb": round(res.vram_total_gb, 1) if res.has_gpu else 0},
        ]

    def summary(self) -> str:
        installed = self.installed_models()
        total_mb = sum(m.size_mb for m in installed)
        res = self.resources()
        lines = [
            f"Models: {len(installed)} installed, {total_mb:.0f} MB total",
            f"RAM: {res.ram_available_gb:.1f}/{res.ram_total_gb:.1f} GB available",
        ]
        if res.has_gpu:
            lines.append(f"GPU: {res.gpu_name} ({res.vram_total_gb:.1f} GB VRAM)")
        else:
            lines.append("GPU: None (CPU-only)")
        lines.append(f"Disk: {res.disk_free_gb:.1f} GB free")
        return "\n".join(lines)
