"""MOSO Diagnostics — self-check system scanning all modules, deps, and runtime health."""
from __future__ import annotations

import importlib
import logging
import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    UNKNOWN = "unknown"


@dataclass
class ComponentCheck:
    name: str
    status: HealthStatus
    message: str = ""
    fixable: bool = False
    fix_command: str = ""


@dataclass
class DiagnosticReport:
    python_version: str = ""
    platform_info: str = ""
    components: list[ComponentCheck] = field(default_factory=list)
    timestamp: float = 0.0

    @property
    def overall(self) -> HealthStatus:
        statuses = [c.status for c in self.components]
        if any(s == HealthStatus.RED for s in statuses):
            return HealthStatus.RED
        if any(s == HealthStatus.YELLOW for s in statuses):
            return HealthStatus.YELLOW
        return HealthStatus.GREEN

    def summary(self) -> str:
        total = len(self.components)
        green = sum(1 for c in self.components if c.status == HealthStatus.GREEN)
        yellow = sum(1 for c in self.components if c.status == HealthStatus.YELLOW)
        red = sum(1 for c in self.components if c.status == HealthStatus.RED)
        lines = [
            f"MOSO Diagnostics — {self.overall.value.upper()}",
            f"Python {self.python_version} on {self.platform_info}",
            f"{green} OK / {yellow} warn / {red} fail  (of {total})",
            "",
        ]
        for c in self.components:
            icon = {"green": "[OK]", "yellow": "[!!]", "red": "[X]", "unknown": "[?]"}[c.status.value]
            line = f"  {icon} {c.name}"
            if c.message:
                line += f" — {c.message}"
            if c.fixable:
                line += f"  (fix: {c.fix_command})"
            lines.append(line)
        return "\n".join(lines)

    def fixable_items(self) -> list[ComponentCheck]:
        return [c for c in self.components if c.fixable and c.status != HealthStatus.GREEN]

    def to_dict(self) -> dict:
        return {
            "overall": self.overall.value,
            "python": self.python_version,
            "platform": self.platform_info,
            "components": [
                {"name": c.name, "status": c.status.value, "message": c.message,
                 "fixable": c.fixable, "fix_command": c.fix_command}
                for c in self.components
            ],
        }


def _check_import(module_name: str) -> tuple[bool, str]:
    try:
        mod = importlib.import_module(module_name)
        ver = getattr(mod, "__version__", "")
        return True, ver
    except ImportError:
        return False, ""


def _check_binary(name: str) -> tuple[bool, str]:
    path = shutil.which(name)
    if path:
        return True, path
    return False, ""


def run_diagnostics() -> DiagnosticReport:
    import time
    report = DiagnosticReport(
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform_info=f"{platform.system()} {platform.release()}",
        timestamp=time.time(),
    )
    comps = report.components

    # --- Python version ---
    if sys.version_info < (3, 10):
        comps.append(ComponentCheck("Python", HealthStatus.RED,
                                    f"Need 3.10+, found {report.python_version}"))
    else:
        comps.append(ComponentCheck("Python", HealthStatus.GREEN, report.python_version))

    # --- Core dependencies ---
    pip_deps = [
        ("llama_cpp", "llama-cpp-python", "Inference (llama.cpp)"),
        ("onnxruntime", "onnxruntime", "Inference (ONNX)"),
        ("transformers", "transformers", "Model loading"),
        ("pydantic", "pydantic", "Data validation"),
        ("numpy", "numpy", "Numerical computing"),
        ("psutil", "psutil", "System resources"),
        ("pyautogui", "pyautogui", "Desktop automation"),
        ("mss", "mss", "Screen capture"),
        ("sounddevice", "sounddevice", "Audio capture"),
        ("faster_whisper", "faster-whisper", "Speech-to-text"),
        ("pyttsx3", "pyttsx3", "Text-to-speech"),
        ("speech_recognition", "speech-recognition", "STT fallback"),
        ("aiohttp", "aiohttp", "Async HTTP"),
        ("bs4", "beautifulsoup4", "HTML parsing"),
        ("networkx", "networkx", "Knowledge graph"),
    ]

    for mod_name, pip_name, desc in pip_deps:
        ok, ver = _check_import(mod_name)
        if ok:
            comps.append(ComponentCheck(desc, HealthStatus.GREEN, f"{pip_name} {ver}"))
        else:
            comps.append(ComponentCheck(desc, HealthStatus.YELLOW,
                                        f"{pip_name} not installed",
                                        fixable=True,
                                        fix_command=f"pip install {pip_name}"))

    # --- Vision deps ---
    vision_deps = [
        ("pytesseract", "pytesseract", "OCR (Tesseract)"),
        ("pygetwindow", "pygetwindow", "Window management"),
    ]
    for mod_name, pip_name, desc in vision_deps:
        ok, ver = _check_import(mod_name)
        if ok:
            comps.append(ComponentCheck(desc, HealthStatus.GREEN, f"{pip_name} {ver}"))
        else:
            comps.append(ComponentCheck(desc, HealthStatus.YELLOW,
                                        f"{pip_name} not installed",
                                        fixable=True,
                                        fix_command=f"pip install {pip_name}"))

    # --- Tesseract binary ---
    tess_ok, tess_path = _check_binary("tesseract")
    if tess_ok:
        comps.append(ComponentCheck("Tesseract OCR", HealthStatus.GREEN, tess_path))
    else:
        comps.append(ComponentCheck("Tesseract OCR", HealthStatus.YELLOW,
                                    "Not found in PATH",
                                    fixable=True,
                                    fix_command="Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki"))

    # --- Chromium browsers (for CDP) ---
    browser_names = ["chrome", "msedge"]
    for bname in browser_names:
        ok, path = _check_binary(bname)
        if ok:
            comps.append(ComponentCheck(f"Browser ({bname})", HealthStatus.GREEN, path))
        else:
            # Check common install paths
            found = False
            for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
                base = os.environ.get(env_var, "")
                if base:
                    candidate = os.path.join(base, bname, f"{bname}.exe")
                    if os.path.isfile(candidate):
                        comps.append(ComponentCheck(f"Browser ({bname})", HealthStatus.GREEN, candidate))
                        found = True
                        break
            if not found:
                comps.append(ComponentCheck(f"Browser ({bname})", HealthStatus.YELLOW,
                                            "Not found",
                                            fixable=True,
                                            fix_command=f"Install {bname} from Microsoft"))

    # --- Voice deps ---
    torch_ok, torch_ver = _check_import("torch")
    if torch_ok:
        comps.append(ComponentCheck("PyTorch", HealthStatus.GREEN, f"torch {torch_ver}"))
    else:
        comps.append(ComponentCheck("PyTorch", HealthStatus.YELLOW,
                                    "Not installed (voice pipeline needs it)",
                                    fixable=True,
                                    fix_command="pip install torch"))

    whisper_ok, whisper_ver = _check_import("whisper")
    if whisper_ok:
        comps.append(ComponentCheck("OpenAI Whisper", HealthStatus.GREEN, f"whisper {whisper_ver}"))
    else:
        # faster_whisper is already checked above; this is the original whisper
        comps.append(ComponentCheck("OpenAI Whisper", HealthStatus.YELLOW,
                                    "Not installed (faster-whisper is fine)",
                                    fixable=True,
                                    fix_command="pip install openai-whisper"))

    # --- Identity deps ---
    scipy_ok, scipy_ver = _check_import("scipy")
    if scipy_ok:
        comps.append(ComponentCheck("SciPy", HealthStatus.GREEN, f"scipy {scipy_ver}"))
    else:
        comps.append(ComponentCheck("SciPy", HealthStatus.YELLOW,
                                    "Not installed (identity engine needs it)",
                                    fixable=True,
                                    fix_command="pip install scipy"))

    # --- MOSO core modules ---
    module_checks = [
        ("moso_core.inference.base", "Inference Engine", True),
        ("moso_core.pipelines.text.pipeline", "Text Pipeline", True),
        ("moso_core.safety.guardrails", "Safety Guardrails", True),
        ("moso_core.memory.manager", "Memory Engine", True),
        ("moso_core.resources.manager", "Resource Monitor", True),
        ("moso_core.tools.registry", "Tool Registry", True),
        ("moso_core.agents.manager", "Agent Planner", False),
        ("moso_core.computer_use.automation", "Computer Use", False),
        ("moso_core.vision.manager", "Vision Engine", False),
        ("moso_core.system_intelligence.manager", "System Intelligence", False),
        ("moso_core.risk.manager", "Risk Engine", False),
        ("moso_core.realtime.manager", "Realtime Research", False),
        ("moso_core.llm.manager", "LLM Manager", False),
        ("moso_core.voice.pipeline", "Voice Pipeline", False),
        ("moso_core.identity.verifier", "Identity Engine", False),
    ]

    for mod_path, display_name, critical in module_checks:
        ok, ver = _check_import(mod_path)
        if ok:
            comps.append(ComponentCheck(display_name, HealthStatus.GREEN, "loaded"))
        else:
            status = HealthStatus.RED if critical else HealthStatus.YELLOW
            comps.append(ComponentCheck(display_name, status, "import failed"))

    # --- Model files ---
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    if os.path.isdir(models_dir):
        ggufs = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
        if ggufs:
            size_mb = sum(
                os.path.getsize(os.path.join(models_dir, f)) for f in ggufs
            ) // (1024 * 1024)
            comps.append(ComponentCheck("Local Models", HealthStatus.GREEN,
                                        f"{len(ggufs)} model(s), {size_mb} MB"))
        else:
            comps.append(ComponentCheck("Local Models", HealthStatus.YELLOW,
                                        "No .gguf models found in models/",
                                        fixable=True,
                                        fix_command="Run: python scripts/download_model.py"))
    else:
        comps.append(ComponentCheck("Local Models", HealthStatus.YELLOW,
                                    "models/ directory missing",
                                    fixable=True,
                                    fix_command="Create models/ and download a model"))

    # --- Disk space for models ---
    try:
        usage = shutil.disk_usage(models_dir if os.path.isdir(models_dir) else ".")
        free_gb = usage.free / (1024 ** 3)
        if free_gb < 2:
            comps.append(ComponentCheck("Disk Space", HealthStatus.RED,
                                        f"{free_gb:.1f} GB free (need 2+ GB for models)"))
        elif free_gb < 5:
            comps.append(ComponentCheck("Disk Space", HealthStatus.YELLOW,
                                        f"{free_gb:.1f} GB free"))
        else:
            comps.append(ComponentCheck("Disk Space", HealthStatus.GREEN,
                                        f"{free_gb:.1f} GB free"))
    except Exception:
        pass

    # --- RAM ---
    try:
        import psutil
        total_gb = psutil.virtual_memory().total / (1024 ** 3)
        if total_gb < 4:
            comps.append(ComponentCheck("RAM", HealthStatus.YELLOW,
                                        f"{total_gb:.1f} GB (8+ GB recommended)"))
        else:
            comps.append(ComponentCheck("RAM", HealthStatus.GREEN, f"{total_gb:.1f} GB"))
    except Exception:
        pass

    # --- GPU ---
    gpu_ok, gpu_ver = _check_import("torch")
    if gpu_ok:
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                vram_gb = torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
                comps.append(ComponentCheck("GPU", HealthStatus.GREEN,
                                            f"{gpu_name} ({vram_gb:.1f} GB VRAM)"))
            else:
                comps.append(ComponentCheck("GPU", HealthStatus.YELLOW,
                                            "No CUDA GPU detected (CPU-only mode)"))
        except Exception:
            comps.append(ComponentCheck("GPU", HealthStatus.UNKNOWN, "Could not detect"))
    else:
        comps.append(ComponentCheck("GPU", HealthStatus.UNKNOWN, "PyTorch not installed"))

    return report


def fix_all(report: DiagnosticReport) -> list[str]:
    """Attempt to fix all fixable components. Returns list of results."""
    results = []
    for item in report.fixable_items():
        if item.fix_command.startswith("pip install"):
            try:
                import subprocess
                pkg = item.fix_command.split("pip install ")[-1].strip()
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg],
                    capture_output=True, text=True, timeout=120,
                )
                if r.returncode == 0:
                    results.append(f"[FIXED] {item.name}: installed {pkg}")
                else:
                    results.append(f"[FAILED] {item.name}: {r.stderr[:200]}")
            except Exception as e:
                results.append(f"[ERROR] {item.name}: {e}")
        else:
            results.append(f"[MANUAL] {item.name}: {item.fix_command}")
    return results


def demo():
    report = run_diagnostics()
    print(report.summary())
    print()
    fixable = report.fixable_items()
    if fixable:
        print(f"{len(fixable)} items can be auto-fixed. Call diagnostics.fix_all(report) to fix.")
    else:
        print("Everything looks good!")


if __name__ == "__main__":
    demo()
