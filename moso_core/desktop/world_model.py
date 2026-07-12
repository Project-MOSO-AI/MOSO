"""A.2 — World Model: continuous desktop state tracker with history."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from moso_core.desktop.perception import DesktopPerceiver, DesktopState

logger = logging.getLogger(__name__)


@dataclass
class WorldState:
    """Persistent desktop awareness that updates continuously."""
    active_app: str = ""
    window_title: str = ""
    window_url: str = ""
    focused_element: str = ""
    mouse_position: tuple[int, int] = (0, 0)
    open_windows: list[str] = field(default_factory=list)
    active_task: str = ""
    clipboard: str = ""
    visible_buttons: list[str] = field(default_factory=list)
    text_fields: list[str] = field(default_factory=list)
    dialogs: list[str] = field(default_factory=list)
    notifications: list[str] = field(default_factory=list)
    last_observation: Optional[DesktopState] = None
    last_update: float = 0.0

    def to_dict(self) -> dict:
        return {
            "active_app": self.active_app,
            "window_title": self.window_title,
            "window_url": self.window_url,
            "focused_element": self.focused_element,
            "mouse_position": list(self.mouse_position),
            "open_windows": self.open_windows,
            "active_task": self.active_task,
            "visible_buttons": self.visible_buttons[:10],
            "text_fields": self.text_fields[:5],
            "dialogs": self.dialogs,
            "notifications": self.notifications,
            "last_update": self.last_update,
        }

    def summary(self) -> str:
        lines = []
        if self.active_task:
            lines.append(f"Task: {self.active_task}")
        lines.append(f"Active: {self.active_app} — {self.window_title}")
        if self.window_url:
            lines.append(f"URL: {self.window_url}")
        if self.focused_element:
            lines.append(f"Focus: {self.focused_element}")
        if self.open_windows:
            lines.append(f"Windows: {', '.join(self.open_windows[:6])}")
        if self.visible_buttons:
            lines.append(f"Buttons: {', '.join(self.visible_buttons[:8])}")
        if self.dialogs:
            lines.append(f"Dialogs: {', '.join(self.dialogs)}")
        return "\n".join(lines)

    def diff(self, previous: WorldState) -> list[str]:
        changes = []
        if self.active_app != previous.active_app:
            changes.append(f"App changed: {previous.active_app or '(none)'} → {self.active_app}")
        if self.window_title != previous.window_title:
            changes.append(f"Window changed: {previous.window_title or '(none)'} → {self.window_title}")
        if self.window_url != previous.window_url:
            changes.append(f"URL changed: {previous.window_url or '(none)'} → {self.window_url}")
        new_windows = set(self.open_windows) - set(previous.open_windows)
        closed_windows = set(previous.open_windows) - set(self.open_windows)
        for w in new_windows:
            changes.append(f"Window opened: {w}")
        for w in closed_windows:
            changes.append(f"Window closed: {w}")
        new_buttons = set(self.visible_buttons) - set(previous.visible_buttons)
        for b in list(new_buttons)[:3]:
            changes.append(f"New button: {b}")
        if self.dialogs and not previous.dialogs:
            changes.append(f"Dialog appeared: {', '.join(self.dialogs)}")
        return changes


class WorldModel:
    """Continuously updated model of the desktop state."""

    def __init__(self, update_interval: float = 2.0):
        self._perceiver = DesktopPerceiver()
        self._current = WorldState()
        self._history: list[WorldState] = []
        self._max_history = 50
        self._lock = threading.Lock()
        self._update_interval = update_interval
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False
        self._callbacks: list[Callable[[WorldState, list[str]], None]] = []

    @property
    def state(self) -> WorldState:
        return self._current

    @property
    def history(self) -> list[WorldState]:
        return list(self._history[-20:])

    def add_callback(self, cb: Callable[[WorldState, list[str]], None]):
        self._callbacks.append(cb)

    def _notify(self, state: WorldState, changes: list[str]):
        for cb in self._callbacks:
            try:
                cb(state, changes)
            except Exception:
                pass

    def update(self) -> WorldState:
        observation = self._perceiver.observe()
        previous = self._current

        with self._lock:
            self._current = WorldState(
                active_app=observation.active_app,
                window_title=observation.window_title,
                window_url=observation.window_url,
                open_windows=observation.open_windows,
                visible_buttons=observation.visible_buttons,
                text_fields=observation.text_fields,
                dialogs=observation.dialogs,
                notifications=observation.notifications,
                last_observation=observation,
                last_update=time.time(),
                mouse_position=previous.mouse_position,
                active_task=previous.active_task,
                focused_element=previous.focused_element,
            )
            changes = self._current.diff(previous)
            if changes:
                self._history.append(self._current)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]
                self._notify(self._current, changes)
                logger.info("World model updated: %d changes", len(changes))
                for c in changes:
                    logger.debug("  %s", c)

        return self._current

    def set_task(self, task: str):
        with self._lock:
            self._current.active_task = task

    def set_focused_element(self, element: str):
        with self._lock:
            self._current.focused_element = element

    def update_mouse(self, x: int, y: int):
        with self._lock:
            self._current.mouse_position = (x, y)

    def start_monitoring(self):
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="moso_world_model",
        )
        self._monitor_thread.start()
        logger.info("World model monitoring started (interval=%.1fs)", self._update_interval)

    def stop_monitoring(self):
        self._monitoring = False

    def _monitor_loop(self, interval: float):
        while self._monitoring:
            try:
                self.update()
            except Exception as e:
                logger.debug("World model update failed: %s", e)
            time.sleep(interval)

    def find_element(self, text: str) -> Optional[DesktopState]:
        """Search the last observation for a UI element matching text."""
        obs = self._current.last_observation
        if not obs:
            return None
        text_lower = text.lower()
        for elem in obs.ui_elements:
            if text_lower in elem.text.lower():
                return obs
        return None

    def find_button(self, text: str) -> Optional[str]:
        """Find a visible button matching text, return its center coords."""
        obs = self._current.last_observation
        if not obs:
            return None
        text_lower = text.lower()
        for elem in obs.ui_elements:
            if elem.role == "button" and text_lower in elem.text.lower():
                cx, cy = elem.center
                return f"({cx},{cy})"
        return None

    def is_app_running(self, app: str) -> bool:
        app_lower = app.lower()
        return any(app_lower in w.lower() for w in self._current.open_windows)

    def get_context_string(self) -> str:
        """Build a compact context string for LLM consumption."""
        parts = []
        if self._current.active_task:
            parts.append(f"[Task] {self._current.active_task}")
        parts.append(f"[Active] {self._current.active_app} — {self._current.window_title}")
        if self._current.window_url:
            parts.append(f"[URL] {self._current.window_url}")
        if self._current.visible_buttons:
            parts.append(f"[Buttons] {', '.join(self._current.visible_buttons[:8])}")
        if self._current.text_fields:
            parts.append(f"[Fields] {', '.join(self._current.text_fields[:4])}")
        if self._current.open_windows:
            parts.append(f"[Windows] {', '.join(self._current.open_windows[:6])}")
        if self._current.dialogs:
            parts.append(f"[Dialogs] {', '.join(self._current.dialogs)}")
        return "\n".join(parts)

    def __enter__(self):
        self.start_monitoring()
        return self

    def __exit__(self, *args):
        self.stop_monitoring()
