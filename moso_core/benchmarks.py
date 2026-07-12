"""MOSO Benchmarks — measure performance of all subsystems."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    name: str
    value: float
    unit: str
    details: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "value": round(self.value, 2), "unit": self.unit, "details": self.details}


@dataclass
class BenchmarkReport:
    results: list[BenchmarkResult] = field(default_factory=list)
    timestamp: float = 0.0

    def add(self, name: str, value: float, unit: str, details: str = ""):
        self.results.append(BenchmarkResult(name, value, unit, details))

    def summary(self) -> str:
        lines = ["MOSO Benchmark Report", "=" * 40]
        for r in self.results:
            lines.append(f"  {r.name}: {r.value:.2f} {r.unit}")
            if r.details:
                lines.append(f"    {r.details}")
        return "\n".join(lines)

    def to_dict(self) -> list[dict]:
        return [r.to_dict() for r in self.results]


def bench_screen_capture(iterations: int = 10) -> BenchmarkResult:
    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            times = []
            for _ in range(iterations):
                t0 = time.perf_counter()
                sct.grab(monitor)
                times.append(time.perf_counter() - t0)
            avg = sum(times) / len(times)
            fps = 1.0 / avg if avg > 0 else 0
            return BenchmarkResult("Screen Capture", fps, "FPS",
                                   f"Avg {avg * 1000:.1f}ms per frame over {iterations} captures")
    except Exception as e:
        return BenchmarkResult("Screen Capture", 0, "FPS", f"Error: {e}")


def bench_ocr(iterations: int = 5) -> BenchmarkResult:
    try:
        import mss
        import pytesseract
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            times = []
            for _ in range(iterations):
                t0 = time.perf_counter()
                pytesseract.image_to_string(img)
                times.append(time.perf_counter() - t0)
            avg = sum(times) / len(times)
            return BenchmarkResult("OCR Speed", avg * 1000, "ms",
                                   f"Average {avg * 1000:.0f}ms per frame over {iterations} runs")
    except Exception as e:
        return BenchmarkResult("OCR Speed", 0, "ms", f"Error: {e}")


def bench_vision_llm(iterations: int = 3) -> BenchmarkResult:
    """Benchmark vision LLM if available."""
    try:
        from moso_core.vision.manager import VisionManager
        vm = VisionManager()
        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            vm.capture_and_analyze()
            times.append(time.perf_counter() - t0)
        avg = sum(times) / len(times)
        return BenchmarkResult("Vision LLM", avg * 1000, "ms",
                               f"Average {avg * 1000:.0f}ms over {iterations} runs")
    except Exception as e:
        return BenchmarkResult("Vision LLM", 0, "ms", f"Error: {e}")


def bench_mouse_latency(iterations: int = 20) -> BenchmarkResult:
    try:
        import pyautogui
        pyautogui.PAUSE = 0
        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            pyautogui.position()
            times.append(time.perf_counter() - t0)
        avg = sum(times) / len(times)
        return BenchmarkResult("Mouse Query Latency", avg * 1000, "ms",
                               f"Average {avg * 1000:.2f}ms per position query")
    except Exception as e:
        return BenchmarkResult("Mouse Query Latency", 0, "ms", f"Error: {e}")


def bench_keyboard_latency(iterations: int = 10) -> BenchmarkResult:
    try:
        from moso_core.computer_use.keyboard import KeyboardController
        kb = KeyboardController()
        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            kb.available  # probe without typing
            times.append(time.perf_counter() - t0)
        avg = sum(times) / len(times)
        return BenchmarkResult("Keyboard Latency", avg * 1000, "ms",
                               f"Average {avg * 1000:.2f}ms per probe")
    except Exception as e:
        return BenchmarkResult("Keyboard Latency", 0, "ms", f"Error: {e}")


def bench_memory_store(iterations: int = 50) -> BenchmarkResult:
    try:
        import tempfile, os
        from moso_core.memory.manager import MemoryManager
        db = os.path.join(tempfile.mkdtemp(), "bench.db")
        mm = MemoryManager(db_path=db)
        times = []
        for i in range(iterations):
            t0 = time.perf_counter()
            mm.store_event(title=f"bench_{i}", description="benchmark", tags=["bench"], owner_id="bench")
            times.append(time.perf_counter() - t0)
        avg = sum(times) / len(times)
        mm.close()
        os.unlink(db)
        return BenchmarkResult("Memory Store", avg * 1000, "ms",
                               f"Average {avg * 1000:.2f}ms per store over {iterations} ops")
    except Exception as e:
        return BenchmarkResult("Memory Store", 0, "ms", f"Error: {e}")


def bench_planner() -> BenchmarkResult:
    try:
        from moso_core.agents.planner import Planner
        p = Planner()
        goals = [
            "Create a Python project",
            "Open Notepad and type hello",
            "Search the web for Python docs",
        ]
        times = []
        for goal in goals:
            t0 = time.perf_counter()
            p.create_plan(goal)
            times.append(time.perf_counter() - t0)
        avg = sum(times) / len(times)
        return BenchmarkResult("Planner", avg * 1000, "ms",
                               f"Average {avg * 1000:.0f}ms plan generation over {len(goals)} goals")
    except Exception as e:
        return BenchmarkResult("Planner", 0, "ms", f"Error: {e}")


def run_all_benchmarks() -> BenchmarkReport:
    import time as _time
    report = BenchmarkReport(timestamp=_time.time())
    benches = [
        bench_screen_capture,
        bench_ocr,
        bench_mouse_latency,
        bench_keyboard_latency,
        bench_memory_store,
        bench_planner,
        bench_vision_llm,
    ]
    for bench_fn in benches:
        try:
            result = bench_fn()
            report.add(result.name, result.value, result.unit, result.details)
            logger.info("Benchmark: %s = %.2f %s", result.name, result.value, result.unit)
        except Exception as e:
            logger.error("Benchmark %s failed: %s", bench_fn.__name__, e)
    return report
