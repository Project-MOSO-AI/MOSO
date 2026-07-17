from __future__ import annotations

import logging
import os
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class AppController(ABC):
    name: str = ""

    @abstractmethod
    def handle(self, action: str, target: str = "", **kwargs) -> str:
        ...

    def _kb(self):
        from moso_core.computer_use.keyboard import KeyboardController
        return KeyboardController()

    def _focus_app(self, process_name: str) -> bool:
        try:
            import psutil
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.info["name"] and process_name.lower() in proc.info["name"].lower():
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            pass
        return False


class SpotifyController(AppController):
    name = "spotify"

    def handle(self, action: str, target: str = "", **kwargs) -> str:
        actions = {
            "play": self._play,
            "pause": self._pause,
            "resume": self._resume,
            "next": self._next,
            "previous": self._previous,
            "shuffle": self._shuffle,
            "play_playlist": self._play_playlist,
            "play_song": self._play_song,
            "search": self._search,
            "volume_up": self._volume_up,
            "volume_down": self._volume_down,
        }
        handler = actions.get(action, self._play)
        return handler(target)

    def _ensure_running(self) -> bool:
        if self._focus_app("spotify"):
            return True
        try:
            from moso_core.tools.app_tool import AppTool
            result = AppTool().launch_application("spotify")
            if result.success:
                time.sleep(2)
                return True
        except Exception:
            pass
        return False

    def _play(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available (pyautogui missing)"
        self._ensure_running()
        kb.press("playpause")
        if target:
            return f"Playing on Spotify: {target}"
        return "Resumed playback on Spotify"

    def _pause(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available"
        self._ensure_running()
        kb.press("playpause")
        return "Paused Spotify"

    def _resume(self, target: str = "") -> str:
        return self._play(target)

    def _next(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available"
        self._ensure_running()
        kb.press("nexttrack")
        return "Next track on Spotify"

    def _previous(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available"
        self._ensure_running()
        kb.press("prevtrack")
        return "Previous track on Spotify"

    def _shuffle(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available"
        self._ensure_running()
        kb.hotkey("ctrl", "s")
        return "Toggled shuffle on Spotify"

    def _play_playlist(self, target: str = "") -> str:
        if not target:
            return "What playlist should I play?"
        self._ensure_running()
        time.sleep(1)
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available"
        # Focus search: Ctrl+L in Spotify focuses the search bar
        kb.hotkey("ctrl", "l")
        time.sleep(0.3)
        # Type playlist name
        import pyautogui
        pyautogui.typewrite(target, interval=0.02)
        time.sleep(0.5)
        kb.press("enter")
        time.sleep(1)
        # The first result should be highlighted — press Enter to play
        kb.press("enter")
        return f'Playing "{target}" playlist on Spotify'

    def _play_song(self, target: str = "") -> str:
        if not target:
            return "What song should I play?"
        self._ensure_running()
        time.sleep(1)
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available"
        kb.hotkey("ctrl", "l")
        time.sleep(0.3)
        import pyautogui
        pyautogui.typewrite(target, interval=0.02)
        time.sleep(0.5)
        kb.press("enter")
        time.sleep(1)
        kb.press("enter")
        return f'Playing "{target}" on Spotify'

    def _search(self, target: str = "") -> str:
        if not target:
            return "What should I search for?"
        self._ensure_running()
        time.sleep(1)
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available"
        kb.hotkey("ctrl", "l")
        time.sleep(0.3)
        import pyautogui
        pyautogui.typewrite(target, interval=0.02)
        kb.press("enter")
        return f'Searching Spotify for "{target}"'

    def _volume_up(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available"
        self._ensure_running()
        for _ in range(3):
            kb.press("volumeup")
        return "Volume up on Spotify"

    def _volume_down(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "Spotify control not available"
        self._ensure_running()
        for _ in range(3):
            kb.press("volumedown")
        return "Volume down on Spotify"


class VLCController(AppController):
    name = "vlc"

    def handle(self, action: str, target: str = "", **kwargs) -> str:
        actions = {
            "play": self._play,
            "pause": self._pause,
            "resume": self._resume,
            "next": self._next,
            "previous": self._previous,
            "fullscreen": self._fullscreen,
            "open_file": self._open_file,
            "volume_up": self._volume_up,
            "volume_down": self._volume_down,
            "seek_forward": self._seek_forward,
            "seek_backward": self._seek_backward,
        }
        handler = actions.get(action, self._play)
        return handler(target)

    def _ensure_running(self) -> bool:
        return self._focus_app("vlc")

    def _play(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "VLC control not available"
        self._ensure_running()
        kb.press("space")
        return "Toggled playback on VLC"

    def _pause(self, target: str = "") -> str:
        return self._play(target)

    def _resume(self, target: str = "") -> str:
        return self._play(target)

    def _next(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "VLC control not available"
        self._ensure_running()
        kb.press("n")
        return "Next on VLC"

    def _previous(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "VLC control not available"
        self._ensure_running()
        kb.press("p")
        return "Previous on VLC"

    def _fullscreen(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "VLC control not available"
        self._ensure_running()
        kb.press("f")
        return "Toggled fullscreen on VLC"

    def _open_file(self, target: str = "") -> str:
        if not target:
            return "What file should I open?"
        if not os.path.isfile(target):
            return f"File not found: {target}"
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", "vlc", target],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                shell=True,
            )
            return f"Opening {os.path.basename(target)} in VLC"
        except Exception as e:
            return f"Failed to open in VLC: {e}"

    def _volume_up(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "VLC control not available"
        self._ensure_running()
        kb.press("up")
        return "Volume up on VLC"

    def _volume_down(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "VLC control not available"
        self._ensure_running()
        kb.press("down")
        return "Volume down on VLC"

    def _seek_forward(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "VLC control not available"
        self._ensure_running()
        kb.press("shift+right")
        return "Seeking forward on VLC"

    def _seek_backward(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "VLC control not available"
        self._ensure_running()
        kb.press("shift+left")
        return "Seeking backward on VLC"


class ChromeController(AppController):
    name = "chrome"

    def handle(self, action: str, target: str = "", **kwargs) -> str:
        actions = {
            "open_url": self._open_url,
            "new_tab": self._new_tab,
            "search": self._search,
            "close_tab": self._close_tab,
        }
        handler = actions.get(action, self._open_url)
        return handler(target)

    def _open_url(self, target: str = "") -> str:
        if not target:
            return "What URL should I open?"
        if not target.startswith("http"):
            target = "https://" + target
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "chrome", target],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                shell=True,
            )
            return f"Opened {target} in Chrome"
        except Exception as e:
            return f"Failed to open in Chrome: {e}"

    def _new_tab(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "Chrome control not available"
        kb.hotkey("ctrl", "t")
        return "New tab in Chrome"

    def _search(self, target: str = "") -> str:
        if not target:
            return "What should I search for?"
        return self._open_url(f"https://duckduckgo.com/?q={target}")

    def _close_tab(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "Chrome control not available"
        kb.hotkey("ctrl", "w")
        return "Closed tab in Chrome"


class VSCodeController(AppController):
    name = "vscode"

    def handle(self, action: str, target: str = "", **kwargs) -> str:
        actions = {
            "open_folder": self._open_folder,
            "open_file": self._open_file,
            "run": self._run,
        }
        handler = actions.get(action, self._open_folder)
        return handler(target)

    def _open_folder(self, target: str = "") -> str:
        if not target:
            return "What folder should I open?"
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "code", target],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                shell=True,
            )
            return f"Opened {target} in VS Code"
        except Exception as e:
            return f"Failed to open in VS Code: {e}"

    def _open_file(self, target: str = "") -> str:
        if not target:
            return "What file should I open?"
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "code", target],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                shell=True,
            )
            return f"Opened {target} in VS Code"
        except Exception as e:
            return f"Failed to open in VS Code: {e}"

    def _run(self, target: str = "") -> str:
        kb = self._kb()
        if not kb.available:
            return "VS Code control not available"
        kb.hotkey("ctrl", "shift", "b")
        return "Running build in VS Code"


# Registry
CONTROLLERS: dict[str, type[AppController]] = {
    "spotify": SpotifyController,
    "vlc": VLCController,
    "chrome": ChromeController,
    "google chrome": ChromeController,
    "vscode": VSCodeController,
    "visual studio code": VSCodeController,
    "vs code": VSCodeController,
}

_controller_instances: dict[str, AppController] = {}


def get_controller(app_name: str) -> Optional[AppController]:
    key = app_name.lower().strip()
    if key in _controller_instances:
        return _controller_instances[key]
    cls = CONTROLLERS.get(key)
    if cls:
        instance = cls()
        _controller_instances[key] = instance
        return instance
    return None
