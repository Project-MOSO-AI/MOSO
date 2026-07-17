"""A.1 — Desktop Perception: screen capture + OCR + UI metadata → structured DesktopState."""
from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    text: str
    role: str  # button, text_field, link, label, icon, menu_item, tab, image, other
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    focused: bool = False

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_dict(self) -> dict:
        return {
            "text": self.text, "role": self.role,
            "x": self.x, "y": self.y,
            "width": self.width, "height": self.height,
            "focused": self.focused,
        }


@dataclass
class DesktopState:
    timestamp: float = 0.0
    active_app: str = ""
    window_title: str = ""
    window_url: str = ""  # for browsers
    resolution: tuple[int, int] = (0, 0)
    visible_text: str = ""
    visible_buttons: list[str] = field(default_factory=list)
    text_fields: list[str] = field(default_factory=list)
    clickable_elements: int = 0
    ui_elements: list[UIElement] = field(default_factory=list)
    open_windows: list[str] = field(default_factory=list)
    dialogs: list[str] = field(default_factory=list)
    notifications: list[str] = field(default_factory=list)
    screenshot_path: str = ""
    active_window_bounds: tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "active_app": self.active_app,
            "window_title": self.window_title,
            "window_url": self.window_url,
            "resolution": list(self.resolution),
            "visible_text": self.visible_text[:500],
            "visible_buttons": self.visible_buttons,
            "text_fields": self.text_fields,
            "clickable_elements": self.clickable_elements,
            "ui_elements": [e.to_dict() for e in self.ui_elements[:30]],
            "open_windows": self.open_windows,
            "dialogs": self.dialogs,
            "notifications": self.notifications,
            "active_window_bounds": list(self.active_window_bounds),
        }

    def summary(self) -> str:
        lines = [f"Active: {self.active_app} — {self.window_title}"]
        if self.window_url:
            lines.append(f"URL: {self.window_url}")
        if self.visible_buttons:
            lines.append(f"Buttons: {', '.join(self.visible_buttons[:8])}")
        if self.text_fields:
            lines.append(f"Text fields: {', '.join(self.text_fields[:4])}")
        lines.append(f"Clickable elements: {self.clickable_elements}")
        if self.open_windows:
            lines.append(f"Windows ({len(self.open_windows)}): {', '.join(self.open_windows[:5])}")
        if self.dialogs:
            lines.append(f"Dialogs: {', '.join(self.dialogs)}")
        return "\n".join(lines)


# ponytail: keyword heuristics, not a trained classifier — good enough for 90% of UI
_BUTTON_KEYWORDS = {
    "button", "btn", "submit", "search", "sign in", "log in", "login", "send",
    "close", "ok", "cancel", "yes", "no", "next", "back", "play", "pause",
    "resume", "stop", "skip", "like", "follow", "subscribe", "download",
    "upload", "save", "edit", "delete", "copy", "paste", "undo", "redo",
    "share", "refresh", "reload", "menu", "settings", "options",
}

_TEXT_FIELD_KEYWORDS = {
    "search", "type", "input", "enter", "write", "email", "password",
    "username", "name", "address", "phone", "query", "find", "box",
}

_LINK_KEYWORDS = {"http", "www", ".com", ".org", ".net", ".io", "link"}


def _classify_element(text: str) -> str:
    t = text.lower().strip()
    if not t:
        return "label"
    if len(t) <= 2:
        return "icon"
    if any(kw in t for kw in _BUTTON_KEYWORDS):
        return "button"
    if any(kw in t for kw in _TEXT_FIELD_KEYWORDS):
        return "text_field"
    if any(kw in t for kw in _LINK_KEYWORDS):
        return "link"
    if len(t) > 50:
        return "label"
    return "label"


def _extract_url_from_ocr(text: str) -> str:
    url_match = re.search(r'https?://\S+', text)
    if url_match:
        return url_match.group(0)
    addr_match = re.search(r'[\w.-]+\.(com|org|net|io|edu|gov)[/\w]*', text)
    if addr_match:
        return addr_match.group(0)
    return ""


def _is_dialog(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in [
        "error", "warning", "confirm", "alert", "dialog",
        "permission", "denied", "failed", "save changes",
    ])


class DesktopPerceiver:
    """Captures and interprets the desktop into a structured DesktopState."""

    def __init__(self):
        self._screen = None
        self._wm = None
        self._ocr = None
        self._init_modules()

    def _init_modules(self):
        try:
            from moso_core.computer_use.screen import ScreenCapturer
            self._screen = ScreenCapturer()
        except Exception:
            pass
        try:
            from moso_core.computer_use.windows import WindowManager
            self._wm = WindowManager()
        except Exception:
            pass
        try:
            from moso_core.vision.ocr import extract_text, extract_text_regions
            self._ocr = (extract_text, extract_text_regions)
        except Exception:
            pass

    def observe(self) -> DesktopState:
        state = DesktopState(timestamp=time.time())

        # 1. Capture screen
        screenshot_path, resolution = self._capture_screen()
        state.screenshot_path = screenshot_path
        state.resolution = resolution

        # 2. Get window info
        state.active_app, state.window_title, state.open_windows, state.active_window_bounds = self._get_window_info()

        # 3. Run OCR
        if self._ocr and screenshot_path:
            state.visible_text, state.ui_elements = self._run_ocr(screenshot_path)

        # 4. Classify elements
        for elem in state.ui_elements:
            if elem.role == "button":
                state.visible_buttons.append(elem.text)
            elif elem.role == "text_field":
                state.text_fields.append(elem.text)
            if elem.role in ("button", "link", "text_field", "menu_item", "tab"):
                state.clickable_elements += 1

        # 5. Extract URL from text (for browsers)
        state.window_url = self._extract_url(state.active_app, state.visible_text)

        # 6. Detect dialogs
        for line in state.visible_text.split("\n"):
            line = line.strip()
            if line and _is_dialog(line):
                state.dialogs.append(line[:100])

        # 7. Detect notifications (system tray area text at screen edges)
        state.notifications = self._detect_notifications(state.visible_text, state.resolution)

        return state

    def _capture_screen(self) -> tuple[str, tuple[int, int]]:
        if not self._screen or not self._screen.available:
            return "", (0, 0)
        result = self._screen.capture_screen()
        if not result.success:
            return "", (0, 0)
        r = result.result
        path = r.get("image_path", "")
        res = tuple(r.get("resolution", (0, 0)))
        return path, res

    def _get_window_info(self) -> tuple[str, str, list[str], tuple[int, int, int, int]]:
        active_app = ""
        window_title = ""
        windows = []
        bounds = (0, 0, 0, 0)
        if not self._wm or not self._wm.available:
            return active_app, window_title, windows, bounds
        try:
            r = self._wm.get_active_window()
            if r.success and r.result:
                window_title = r.result.get("title", "")
                active_app = self._parse_app_name(window_title)
                bounds = tuple(r.result.get("bounds", (0, 0, 0, 0)))
            r2 = self._wm.list_windows()
            if r2.success and r2.result:
                windows = r2.result.get("windows", [])
        except Exception as e:
            logger.debug("Window info failed: %s", e)
        return active_app, window_title, windows, bounds

    def _parse_app_name(self, title: str) -> str:
        if not title:
            return ""
        title_lower = title.lower()
        known = {
            "chrome": ["chrome", "google chrome"],
            "firefox": ["firefox"],
            "edge": ["edge", "microsoft edge"],
            "spotify": ["spotify"],
            "vscode": ["visual studio code", "vscode", "vs code"],
            "notepad": ["notepad"],
            "explorer": ["file explorer", "windows explorer"],
            "discord": ["discord"],
            "whatsapp": ["whatsapp"],
            "vlc": ["vlc"],
            "teams": ["teams", "microsoft teams"],
            "word": ["microsoft word"],
            "excel": ["microsoft excel"],
            "powerpoint": ["microsoft powerpoint"],
        }
        for app, keywords in known.items():
            if any(kw in title_lower for kw in keywords):
                return app
        # fallback: first word of the title
        return title.split(" - ")[0].split(" | ")[0].strip()[:30]

    def _run_ocr(self, image_path: str) -> tuple[str, list[UIElement]]:
        if not self._ocr:
            return "", []
        try:
            from PIL import Image
            img = Image.open(image_path)
            extract_text, extract_text_regions = self._ocr
            text = extract_text(img)
            regions = extract_text_regions(img)
            img.close()

            elements = []
            for r in regions:
                bbox = r.bounding_box
                role = _classify_element(r.text)
                elements.append(UIElement(
                    text=r.text,
                    role=role,
                    x=bbox.left, y=bbox.top,
                    width=bbox.width, height=bbox.height,
                ))
            return text, elements
        except Exception as e:
            logger.debug("OCR failed: %s", e)
            return "", []

    def _extract_url(self, app: str, text: str) -> str:
        if app not in ("chrome", "firefox", "edge"):
            return ""
        return _extract_url_from_ocr(text)

    def _detect_notifications(self, text: str, resolution: tuple[int, int]) -> list[str]:
        if not text or resolution == (0, 0):
            return []
        notifications = []
        for line in text.split("\n"):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            t = line.lower()
            if any(kw in t for kw in ["notification", "new message", "alert", "update available"]):
                notifications.append(line[:100])
        return notifications[:5]


def observe() -> DesktopState:
    """Convenience function — one-shot desktop observation."""
    return DesktopPerceiver().observe()
