from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from threading import Thread
from typing import Optional

from moso_core.computer_use.models import AutomationSequence, ComputerUseResult, RecordedEvent

logger = logging.getLogger(__name__)


class WorkflowRecorder:
    def __init__(self, output_dir: Optional[str] = None):
        self._output_dir = output_dir or os.path.join(os.path.expanduser("~"), ".moso", "workflows")
        os.makedirs(self._output_dir, exist_ok=True)
        self._events: list[RecordedEvent] = []
        self._recording = False
        self._thread: Optional[Thread] = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def record_mouse(self, duration: float = 10.0, interval: float = 0.1) -> ComputerUseResult:
        try:
            import pyautogui
            start = time.time()
            count = 0
            while time.time() - start < duration and self._recording:
                x, y = pyautogui.position()
                self._events.append(RecordedEvent(
                    event_type="mouse_move",
                    data={"x": x, "y": y, "timestamp": time.time()},
                ))
                count += 1
                time.sleep(interval)
            return ComputerUseResult(True, "record_mouse", {"events": count})
        except ImportError:
            return ComputerUseResult(False, "record_mouse", error="pyautogui not available")
        except Exception as e:
            return ComputerUseResult(False, "record_mouse", error=str(e))

    def record_keyboard(self, duration: float = 10.0) -> ComputerUseResult:
        try:
            import keyboard as kb
            start = time.time()
            recorded: list[dict] = []

            def on_key(event):
                if self._recording:
                    recorded.append({"key": event.name, "event_type": event.event_type, "timestamp": time.time()})

            kb.hook(on_key)
            time.sleep(duration)
            kb.unhook_all()

            for ev in recorded:
                self._events.append(RecordedEvent(
                    event_type="keyboard_" + ev["event_type"],
                    data={"key": ev["key"]},
                ))
            return ComputerUseResult(True, "record_keyboard", {"events": len(recorded)})
        except ImportError:
            return ComputerUseResult(False, "record_keyboard", error="keyboard library not available")
        except Exception as e:
            return ComputerUseResult(False, "record_keyboard", error=str(e))

    def export_sequence(self, description: str = "") -> AutomationSequence:
        actions = []
        for event in self._events:
            if event.event_type == "mouse_move":
                actions.append({
                    "action": "move_to",
                    "x": event.data.get("x", 0),
                    "y": event.data.get("y", 0),
                })
            elif event.event_type == "mouse_click":
                actions.append({
                    "action": "click",
                    "x": event.data.get("x", 0),
                    "y": event.data.get("y", 0),
                    "button": event.data.get("button", "left"),
                })
            elif event.event_type in ("keyboard_down", "keyboard_press"):
                key = event.data.get("key", "")
                if key.lower() in ("ctrl", "alt", "shift", "win", "command"):
                    continue
                actions.append({
                    "action": "press",
                    "key": key,
                })
        sequence = AutomationSequence(actions=actions, description=description)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self._output_dir, f"workflow_{timestamp}.json")
        with open(path, "w") as f:
            json.dump(sequence.to_dict(), f, indent=2)
        logger.info("Exported workflow to %s (%d actions)", path, len(actions))
        self._events.clear()
        return sequence

    def start_recording(self, duration: float = 10.0, record_keyboard: bool = True, blocking: bool = True) -> ComputerUseResult:
        self._recording = True
        self._events.clear()
        threads = []
        mouse_result: list[ComputerUseResult] = []

        def run_mouse():
            mouse_result.append(self.record_mouse(duration=duration))

        t = Thread(target=run_mouse)
        t.start()
        threads.append(t)

        if record_keyboard:
            kb_result: list[ComputerUseResult] = []
            def run_keyboard():
                kb_result.append(self.record_keyboard(duration=duration))
            t2 = Thread(target=run_keyboard)
            t2.start()
            threads.append(t2)
            
            if blocking:
                for th in threads:
                    th.join()
                self._recording = False
                return ComputerUseResult(True, "start_recording", {"mouse": str(mouse_result[0]), "keyboard": str(kb_result[0]) if kb_result else "none"})
            else:
                return ComputerUseResult(True, "start_recording", {"status": "recording_async"})

        if blocking:
            for th in threads:
                th.join()
            self._recording = False
            return ComputerUseResult(True, "start_recording", {"mouse": str(mouse_result[0])})
        return ComputerUseResult(True, "start_recording", {"status": "recording_async"})

    def stop_recording(self) -> ComputerUseResult:
        self._recording = False
        return ComputerUseResult(True, "stop_recording", {"events": len(self._events)})
