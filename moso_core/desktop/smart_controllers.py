"""Smart Application Controllers — perception-aware per-app intelligence."""
from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

from moso_core.desktop.perception import DesktopPerceiver, DesktopState, UIElement
from moso_core.desktop.verifier import ActionVerifier

logger = logging.getLogger(__name__)


class SmartController(ABC):
    """Base class for perception-aware app controllers."""
    name: str = ""
    known_apps: list[str] = []

    def __init__(self):
        self._perceiver = DesktopPerceiver()
        self._verifier = ActionVerifier()

    @abstractmethod
    def handle(self, action: str, target: str = "", state: Optional[DesktopState] = None) -> str:
        ...

    def _observe(self) -> DesktopState:
        return self._perceiver.observe()

    def _find_element(self, state: DesktopState, text: str) -> Optional[UIElement]:
        text_lower = text.lower()
        for elem in state.ui_elements:
            if text_lower in elem.text.lower():
                return elem
        return None

    def _find_button(self, state: DesktopState, text: str) -> Optional[UIElement]:
        text_lower = text.lower()
        for elem in state.ui_elements:
            if elem.role == "button" and text_lower in elem.text.lower():
                return elem
        return None

    def _click_element(self, elem: UIElement) -> str:
        cx, cy = elem.center
        try:
            import pyautogui
            pyautogui.click(cx, cy)
            return f"Clicked '{elem.text}' at ({cx},{cy})"
        except Exception as e:
            return f"Failed to click: {e}"

    def _type_and_enter(self, text: str) -> str:
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=0.02)
            time.sleep(0.3)
            pyautogui.press("enter")
            return f"Typed '{text}' and pressed Enter"
        except Exception as e:
            return f"Failed to type: {e}"

    def _kb(self):
        from moso_core.computer_use.keyboard import KeyboardController
        return KeyboardController()

    def matches(self, app_name: str) -> bool:
        app_lower = app_name.lower()
        return any(app_lower in known.lower() for known in self.known_apps)


class SmartSpotifyController(SmartController):
    name = "spotify"
    known_apps = ["spotify"]

    def handle(self, action: str, target: str = "", state: Optional[DesktopState] = None) -> str:
        if state is None:
            state = self._observe()

        actions = {
            "play": self._play,
            "pause": self._pause,
            "resume": self._play,
            "next": self._next,
            "previous": self._previous,
            "shuffle": self._shuffle,
            "search": self._search,
            "play_song": self._play_song,
            "play_playlist": self._play_playlist,
            "what_playing": self._what_playing,
            "suggest": self._suggest,
        }
        handler = actions.get(action, self._play)
        return handler(target, state)

    def _ensure_spotify(self) -> str:
        from moso_core.tools.app_tool import AppTool
        result = AppTool().launch_application("spotify")
        if result.success:
            time.sleep(3)
            return "Spotify launched"
        return "Spotify not found"

    def _play(self, target: str, state: DesktopState) -> str:
        if not state.active_app or "spotify" not in state.active_app.lower():
            self._ensure_spotify()
            state = self._observe()
        elem = self._find_button(state, "play")
        if elem:
            return self._click_element(elem)
        kb = self._kb()
        if kb.available:
            kb.press("playpause")
            return "Toggled playback via media key"
        return "Spotify play control unavailable"

    def _pause(self, target: str, state: DesktopState) -> str:
        return self._play(target, state)

    def _next(self, target: str, state: DesktopState) -> str:
        kb = self._kb()
        if kb.available:
            kb.press("nexttrack")
            return "Next track"
        return "Next track unavailable"

    def _previous(self, target: str, state: DesktopState) -> str:
        kb = self._kb()
        if kb.available:
            kb.press("prevtrack")
            return "Previous track"
        return "Previous track unavailable"

    def _shuffle(self, target: str, state: DesktopState) -> str:
        kb = self._kb()
        if kb.available:
            kb.hotkey("ctrl", "s")
            return "Toggled shuffle"
        return "Shuffle unavailable"

    def _search(self, target: str, state: DesktopState) -> str:
        if not target:
            return "What should I search for?"
        kb = self._kb()
        if kb.available:
            # Ensure Spotify is focused
            if not state.active_app or "spotify" not in state.active_app.lower():
                self._ensure_spotify()
                time.sleep(2)
            # Ctrl+Q opens search in Spotify desktop
            kb.hotkey("ctrl", "q")
            time.sleep(0.5)
            # Clear any existing search text
            kb.hotkey("ctrl", "a")
            time.sleep(0.1)
            return self._type_and_enter(target)
        return "Search unavailable"

    def _play_song(self, target: str, state: DesktopState) -> str:
        if not target:
            return "What song should I play?"
        result = self._search(target, state)
        time.sleep(1)
        kb = self._kb()
        if kb.available:
            kb.press("enter")
            time.sleep(0.5)
            kb.press("enter")
            return f"Playing '{target}'"
        return result

    def _play_playlist(self, target: str, state: DesktopState) -> str:
        return self._play_song(target, state)

    def _what_playing(self, target: str, state: DesktopState) -> str:
        # Look for song title in the visible text
        text = state.visible_text.lower()
        now_playing_idx = text.find("now playing")
        if now_playing_idx >= 0:
            snippet = state.visible_text[now_playing_idx:now_playing_idx + 100]
            return f"Currently: {snippet.strip()}"
        # Look for play/pause button context
        for elem in state.ui_elements:
            if "pause" in elem.text.lower():
                return f"Something is playing (pause button visible)"
            if "play" in elem.text.lower():
                return "Nothing is currently playing"
        return "Can't determine what's playing"

    def _suggest(self, target: str, state: DesktopState) -> str:
        suggestions = []
        for elem in state.ui_elements:
            text = elem.text.lower()
            if any(kw in text for kw in ["liked", "daily mix", "recent", "new release", "playlist"]):
                suggestions.append(elem.text)
        if suggestions:
            return f"I see: {', '.join(suggestions[:5])}. Want me to play one?"
        return "No obvious playlists visible. Try searching for something specific."


class SmartChromeController(SmartController):
    name = "chrome"
    known_apps = ["chrome", "firefox", "edge", "browser"]

    def handle(self, action: str, target: str = "", state: Optional[DesktopState] = None) -> str:
        if state is None:
            state = self._observe()

        actions = {
            "open_url": self._open_url,
            "search": self._search,
            "click": self._click_by_text,
            "read_page": self._read_page,
            "close_tab": self._close_tab,
            "new_tab": self._new_tab,
            "summarize": self._summarize,
        }
        handler = actions.get(action, self._open_url)
        return handler(target, state)

    def _open_url(self, target: str, state: DesktopState) -> str:
        if not target:
            return "What URL should I open?"
        if not target.startswith("http"):
            target = "https://" + target
        import subprocess
        try:
            app = state.active_app.lower() if state.active_app else "chrome"
            subprocess.Popen(["cmd", "/c", "start", app, target],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            time.sleep(3)
            return f"Opened {target}"
        except Exception as e:
            return f"Failed: {e}"

    def _search(self, target: str, state: DesktopState) -> str:
        if not target:
            return "What should I search for?"
        return self._open_url(f"https://duckduckgo.com/?q={target}", state)

    def _click_by_text(self, target: str, state: DesktopState) -> str:
        elem = self._find_element(state, target)
        if elem:
            return self._click_element(elem)
        # Try fuzzy match
        for e in state.ui_elements:
            if target.lower() in e.text.lower():
                return self._click_element(e)
        return f"Couldn't find '{target}' on screen"

    def _read_page(self, target: str, state: DesktopState) -> str:
        text = state.visible_text
        if not text:
            return "No text visible on screen"
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        summary = "\n".join(lines[:20])
        return f"Page content ({len(lines)} lines):\n{summary}"

    def _close_tab(self, target: str, state: DesktopState) -> str:
        kb = self._kb()
        if kb.available:
            kb.hotkey("ctrl", "w")
            return "Closed tab"
        return "Close tab unavailable"

    def _new_tab(self, target: str, state: DesktopState) -> str:
        kb = self._kb()
        if kb.available:
            kb.hotkey("ctrl", "t")
            return "New tab"
        return "New tab unavailable"

    def _summarize(self, target: str, state: DesktopState) -> str:
        text = state.visible_text
        if not text:
            return "No text to summarize"
        # Simple extractive summary: take first meaningful lines
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 15]
        if not lines:
            return "Page has no substantial text content"
        return f"Page summary ({state.window_title}):\n" + "\n".join(lines[:10])


class SmartExplorerController(SmartController):
    name = "explorer"
    known_apps = ["file explorer", "explorer", "files"]

    def handle(self, action: str, target: str = "", state: Optional[DesktopState] = None) -> str:
        if state is None:
            state = self._observe()

        actions = {
            "list_files": self._list_files,
            "suggest": self._suggest,
        }
        handler = actions.get(action, self._suggest)
        return handler(target, state)

    def _list_files(self, target: str, state: DesktopState) -> str:
        files = []
        for elem in state.ui_elements:
            if elem.role in ("label", "other") and "." in elem.text:
                files.append(elem.text)
        if files:
            return f"Visible files: {', '.join(files[:15])}"
        return "No files visible in current view"

    def _suggest(self, target: str, state: DesktopState) -> str:
        suggestions = []
        text = state.visible_text.lower()
        for kw in ["downloads", "documents", "desktop", "pictures", "videos", "music"]:
            if kw in text:
                suggestions.append(f"Open {kw.title()}")
        if suggestions:
            return f"I see: {' | '.join(suggestions)}. Which would you like?"
        return f"Current view: {state.window_title}"


# Registry
SMART_CONTROLLERS: dict[str, type[SmartController]] = {
    "spotify": SmartSpotifyController,
    "chrome": SmartChromeController,
    "firefox": SmartChromeController,
    "edge": SmartChromeController,
    "explorer": SmartExplorerController,
}

_smart_instances: dict[str, SmartController] = {}


def get_smart_controller(app_name: str) -> Optional[SmartController]:
    key = app_name.lower().strip()
    if key in _smart_instances:
        return _smart_instances[key]
    cls = SMART_CONTROLLERS.get(key)
    if cls:
        instance = cls()
        _smart_instances[key] = instance
        return instance
    # Fuzzy match
    for registered, cls in SMART_CONTROLLERS.items():
        if registered in key or key in registered:
            instance = cls()
            _smart_instances[key] = instance
            return instance
    return None
