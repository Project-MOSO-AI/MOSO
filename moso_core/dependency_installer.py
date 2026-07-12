"""Auto-detect and install missing dependencies — pip packages, system tools, PATH fixes."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class InstallMethod(str, Enum):
    PIP = "pip"
    WINGET = "winget"
    CHOCO = "choco"
    MANUAL = "manual"


@dataclass
class InstallTask:
    name: str
    method: InstallMethod
    command: str
    description: str = ""
    installed: bool = False
    error: str = ""


@dataclass
class InstallResult:
    success: bool
    installed: list[InstallTask]
    failed: list[InstallTask]
    skipped: list[InstallTask]

    def summary(self) -> str:
        parts = []
        if self.installed:
            parts.append(f"Installed: {', '.join(t.name for t in self.installed)}")
        if self.skipped:
            parts.append(f"Already present: {', '.join(t.name for t in self.skipped)}")
        if self.failed:
            parts.append(f"Failed: {', '.join(t.name for t in self.failed)}")
        return "; ".join(parts) if parts else "Nothing to do."


def _check_pkg(mod_name: str) -> bool:
    try:
        __import__(mod_name)
        return True
    except ImportError:
        return False


def _check_binary(name: str) -> bool:
    return shutil.which(name) is not None


def _pip_install(package: str, timeout: int = 180) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode == 0:
            return True, ""
        return False, r.stderr[-300:] if r.stderr else "install failed"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def _winget_install(package_id: str, timeout: int = 300) -> tuple[bool, str]:
    if not _check_binary("winget"):
        return False, "winget not found"
    try:
        r = subprocess.run(
            ["winget", "install", "--id", package_id, "--accept-package-agreements",
             "--accept-source-agreements", "--silent"],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode == 0:
            return True, ""
        return False, r.stderr[-300:] if r.stderr else "winget install failed"
    except Exception as e:
        return False, str(e)


def _choco_install(package: str, timeout: int = 300) -> tuple[bool, str]:
    if not _check_binary("choco"):
        return False, "choco not found"
    try:
        r = subprocess.run(
            ["choco", "install", package, "-y"],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode == 0:
            return True, ""
        return False, r.stderr[-300:] if r.stderr else "choco install failed"
    except Exception as e:
        return False, str(e)


# ponytail: flat dict, not a class hierarchy — one install strategy per dep is enough
PIP_PACKAGES: dict[str, tuple[str, str]] = {
    # mod_name: (pip_package, description)
    "llama_cpp": ("llama-cpp-python", "Inference (llama.cpp)"),
    "onnxruntime": ("onnxruntime", "Inference (ONNX)"),
    "transformers": ("transformers", "Model loading"),
    "pydantic": ("pydantic", "Data validation"),
    "numpy": ("numpy", "Numerical computing"),
    "psutil": ("psutil", "System resources"),
    "pyautogui": ("pyautogui", "Desktop automation"),
    "mss": ("mss", "Screen capture"),
    "pygetwindow": ("pygetwindow", "Window management"),
    "sounddevice": ("sounddevice", "Audio capture"),
    "faster_whisper": ("faster-whisper", "Speech-to-text"),
    "pyttsx3": ("pyttsx3", "Text-to-speech"),
    "speech_recognition": ("speech-recognition", "STT fallback"),
    "aiohttp": ("aiohttp", "Async HTTP"),
    "bs4": ("beautifulsoup4", "HTML parsing"),
    "networkx": ("networkx", "Knowledge graph"),
    "scipy": ("scipy", "SciPy"),
    "torch": ("torch", "PyTorch"),
    "pytesseract": ("pytesseract", "OCR (Tesseract wrapper)"),
}

WINGET_PACKAGES: dict[str, tuple[str, str]] = {
    # binary_name: (winget_id, description)
    "tesseract": ("UB-Mannheim.TesseractOCR", "Tesseract OCR"),
    "chrome": ("Google.Chrome", "Google Chrome"),
    "msedge": ("Microsoft.Edge", "Microsoft Edge"),
}


class DependencyInstaller:
    def __init__(self, progress_callback: Optional[Callable[[str, int, int], None]] = None):
        self._progress = progress_callback
        self._tasks: list[InstallTask] = []

    def _report(self, message: str, current: int = 0, total: int = 0):
        if self._progress:
            self._progress(message, current, total)

    def scan_missing_pip(self) -> list[InstallTask]:
        tasks = []
        for mod_name, (pip_name, desc) in PIP_PACKAGES.items():
            if not _check_pkg(mod_name):
                tasks.append(InstallTask(
                    name=pip_name,
                    method=InstallMethod.PIP,
                    command=pip_name,
                    description=desc,
                ))
        return tasks

    def scan_missing_system(self) -> list[InstallTask]:
        tasks = []
        if os.name == "nt":
            for binary, (winget_id, desc) in WINGET_PACKAGES.items():
                if not _check_binary(binary):
                    # Also check common install paths
                    found = False
                    for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
                        base = os.environ.get(env_var, "")
                        if base:
                            candidate = os.path.join(base, binary, f"{binary}.exe")
                            if os.path.isfile(candidate):
                                found = True
                                break
                    if not found:
                        tasks.append(InstallTask(
                            name=binary,
                            method=InstallMethod.WINGET,
                            command=winget_id,
                            description=desc,
                        ))
        return tasks

    def scan_all_missing(self) -> list[InstallTask]:
        tasks = self.scan_missing_pip()
        if os.name == "nt":
            tasks.extend(self.scan_missing_system())
        self._tasks = tasks
        return tasks

    def install_pip_packages(self, packages: Optional[list[str]] = None) -> list[InstallTask]:
        if packages is None:
            packages = [t.command for t in self._tasks if t.method == InstallMethod.PIP]
        results = []
        total = len(packages)
        for i, pkg in enumerate(packages):
            self._report(f"Installing {pkg}...", i + 1, total)
            ok, err = _pip_install(pkg)
            task = InstallTask(
                name=pkg, method=InstallMethod.PIP,
                command=pkg, installed=ok, error=err,
            )
            results.append(task)
            if ok:
                logger.info("Installed %s", pkg)
            else:
                logger.warning("Failed to install %s: %s", pkg, err)
        return results

    def install_system_tools(self, tools: Optional[list[str]] = None) -> list[InstallTask]:
        if tools is None:
            tools = [t.name for t in self._tasks if t.method == InstallMethod.WINGET]
        results = []
        total = len(tools)
        for i, binary in enumerate(tools):
            self._report(f"Installing {binary}...", i + 1, total)
            winget_id = WINGET_PACKAGES.get(binary, (binary, ""))[0]
            ok, err = _winget_install(winget_id)
            task = InstallTask(
                name=binary, method=InstallMethod.WINGET,
                command=winget_id, installed=ok, error=err,
            )
            results.append(task)
            if ok:
                logger.info("Installed %s via winget", binary)
            else:
                logger.warning("Failed to install %s: %s", binary, err)
        return results

    def install_all(self, skip_system: bool = False) -> InstallResult:
        pip_tasks = self.scan_missing_pip()
        pip_installed = self.install_pip_packages([t.command for t in pip_tasks]) if pip_tasks else []

        system_installed = []
        skipped = []
        if not skip_system and os.name == "nt":
            system_tasks = self.scan_missing_system()
            if system_tasks:
                system_installed = self.install_system_tools([t.name for t in system_tasks])
        else:
            skipped = [t for t in self.scan_missing_system()]

        installed = pip_installed + system_installed
        failed = [t for t in installed if not t.installed]
        success = [t for t in installed if t.installed]

        return InstallResult(
            success=len(failed) == 0,
            installed=success,
            failed=failed,
            skipped=skipped,
        )

    def first_launch_check(self) -> InstallResult:
        """Run on first launch — install everything missing."""
        return self.install_all()


def demo():
    installer = DependencyInstaller()
    missing = installer.scan_all_missing()
    if not missing:
        print("All dependencies are installed!")
        return
    print(f"Found {len(missing)} missing dependencies:")
    for t in missing:
        print(f"  [{t.method.value}] {t.name} — {t.description}")
    print()
    result = installer.install_all()
    print(result.summary())


if __name__ == "__main__":
    demo()
