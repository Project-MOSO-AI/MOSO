"""Desktop Memory — persistent awareness and context resolution."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from moso_core.desktop.perception import DesktopPerceiver, DesktopState
from moso_core.desktop.world_model import WorldModel

logger = logging.getLogger(__name__)

PERSISTENCE_FILE = "moso_core/desktop/.desktop_memory.json"


@dataclass
class MemoryRecord:
    timestamp: float = 0.0
    active_task: str = ""
    active_app: str = ""
    window_title: str = ""
    media_playing: bool = False
    media_artist: str = ""
    media_title: str = ""
    browser_url: str = ""
    network_connected: bool = True
    battery_percent: float = -1.0
    recent_actions: list[str] = field(default_factory=list)
    open_windows: list[str] = field(default_factory=list)
    focused_element: str = ""
    last_url: str = ""
    last_search: str = ""


class DesktopMemory:
    """Persistent desktop awareness. Resolves pronouns and maintains context."""

    def __init__(self):
        self._perceiver = DesktopPerceiver()
        self._world_model = WorldModel()
        self._record = MemoryRecord(timestamp=time.time())
        self._loaded = False
        self._callbacks: list = []

    def observe(self) -> DesktopState:
        """Take a fresh snapshot and update memory."""
        state = self._perceiver.observe()
        self._update_from_state(state)
        return state

    def _update_from_state(self, state: DesktopState):
        self._record.active_app = state.active_app or ""
        self._record.window_title = state.window_title or ""
        self._record.open_windows = [w.title for w in state.open_windows]
        self._record.focused_element = state.focused_element.text if state.focused_element else ""
        self._record.timestamp = time.time()

        text = state.visible_text.lower()
        self._record.media_playing = any(kw in text for kw in ["pause", "playing", "now playing", "spotify"])

        if "youtube" in text or "spotify" in text:
            self._record.media_playing = True
            self._record.last_url = self._extract_url(state.visible_text)

        for elem in state.ui_elements:
            if elem.url:
                self._record.browser_url = elem.url
                self._record.last_url = elem.url

    def _extract_url(self, text: str) -> str:
        import re
        m = re.search(r'https?://\S+', text)
        return m.group(0) if m else ""

    def update_task(self, task: str):
        self._record.active_task = task
        if len(self._record.recent_actions) > 50:
            self._record.recent_actions = self._record.recent_actions[-50:]

    def record_action(self, action: str):
        self._record.recent_actions.append(f"{time.time():.0f}: {action}")
        if len(self._record.recent_actions) > 50:
            self._record.recent_actions.pop(0)

    def resolve_pronoun(self, pronoun: str) -> str:
        """Resolve 'it', 'this', 'that' to the most likely target."""
        pronoun = pronoun.lower().strip()
        if pronoun in ("it", "this", "that"):
            if self._record.media_playing:
                return "the current media"
            if self._record.active_app:
                return self._record.active_app
            if self._record.last_url:
                return self._record.last_url
        return pronoun

    def resolve_command(self, command: str) -> str:
        """Replace pronouns in a command with resolved context."""
        words = command.split()
        resolved = []
        for w in words:
            if w.lower() in ("it", "this", "that", "there"):
                resolved.append(self.resolve_pronoun(w))
            else:
                resolved.append(w)
        return " ".join(resolved)

    def get_context_string(self) -> str:
        """Human-readable context summary."""
        parts = []
        if self._record.active_app:
            parts.append(f"Active app: {self._record.active_app}")
        if self._record.window_title:
            parts.append(f"Window: {self._record.window_title}")
        if self._record.media_playing:
            media = self._record.media_title or "something"
            if self._record.media_artist:
                media = f"{self._record.media_artist} - {self._record.media_title}"
            parts.append(f"Media: {media}")
        if self._record.browser_url:
            parts.append(f"URL: {self._record.browser_url}")
        if self._record.open_windows:
            parts.append(f"Open windows: {', '.join(self._record.open_windows[:5])}")
        if self._record.recent_actions:
            parts.append(f"Last action: {self._record.recent_actions[-1]}")
        return "\n".join(parts) if parts else "No desktop context"

    def save(self):
        try:
            data = {
                "active_task": self._record.active_task,
                "active_app": self._record.active_app,
                "window_title": self._record.window_title,
                "media_playing": self._record.media_playing,
                "last_url": self._record.last_url,
                "recent_actions": self._record.recent_actions[-20:],
                "timestamp": self._record.timestamp,
            }
            with open(PERSISTENCE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save memory: {e}")

    def load(self):
        try:
            with open(PERSISTENCE_FILE) as f:
                data = json.load(f)
            self._record.active_task = data.get("active_task", "")
            self._record.active_app = data.get("active_app", "")
            self._record.window_title = data.get("window_title", "")
            self._record.media_playing = data.get("media_playing", False)
            self._record.last_url = data.get("last_url", "")
            self._record.recent_actions = data.get("recent_actions", [])
            self._loaded = True
            logger.info("Loaded desktop memory from disk")
        except FileNotFoundError:
            self._loaded = True
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")
            self._loaded = True

    def clear(self):
        self._record = MemoryRecord(timestamp=time.time())
        try:
            import os
            if os.path.exists(PERSISTENCE_FILE):
                os.remove(PERSISTENCE_FILE)
        except Exception:
            pass

    def is_media_playing(self) -> bool:
        return self._record.media_playing

    def get_active_app(self) -> str:
        return self._record.active_app

    def get_active_task(self) -> str:
        return self._record.active_task

    def get_recent_actions(self, n: int = 5) -> list[str]:
        return self._record.recent_actions[-n:]

    def update_active_app(self, app_name: str, window_title: str = ""):
        self._record.active_app = app_name
        if window_title:
            self._record.window_title = window_title
        self._record.timestamp = time.time()

    def get_suggestions(self) -> list[str]:
        suggestions = []
        app = self._record.active_app.lower()
        if "chrome" in app or "edge" in app or "firefox" in app:
            suggestions.extend(["Open Gmail", "Search Google", "Open YouTube", "Open new tab"])
        elif "spotify" in app:
            suggestions.extend(["Play Liked Songs", "Search Artist", "Play Daily Mix", "Next track"])
        elif "notepad" in app:
            suggestions.extend(["Save file", "Select all", "Copy text"])
        elif "explorer" in app or "file" in app:
            suggestions.extend(["Open Downloads", "Open Documents", "Open Desktop", "Open recent file"])
        elif "vs code" in app or "code" in app:
            suggestions.extend(["Open file", "Run code", "Open terminal", "Search files"])
        elif "vlc" in app:
            suggestions.extend(["Play file", "Pause", "Next", "Volume up"])
        elif "discord" in app or "whatsapp" in app:
            suggestions.extend(["Search contact", "Send message", "Open channel"])
        if self._record.media_playing:
            suggestions.extend(["Pause playback", "Next track", "Volume control"])
        return suggestions[:6]
