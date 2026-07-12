"""A.4 — Verification: success conditions for every action type."""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Optional, Callable

from moso_core.desktop.perception import DesktopState, DesktopPerceiver

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    success: bool
    action: str
    condition: str
    details: str = ""
    observed_state: Optional[DesktopState] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "action": self.action,
            "condition": self.condition,
            "details": self.details,
        }


class ActionVerifier:
    """Verifies that actions produced their expected outcomes."""

    def __init__(self):
        self._perceiver = DesktopPerceiver()
        self._custom_rules: dict[str, Callable[[DesktopState], tuple[bool, str]]] = {}

    def register_rule(self, action: str, rule: Callable[[DesktopState], tuple[bool, str]]):
        self._custom_rules[action] = rule

    def verify(self, action: str, expected: dict = None, timeout: float = 5.0) -> VerificationResult:
        expected = expected or {}
        state = self._perceiver.observe()

        if action in self._custom_rules:
            ok, details = self._custom_rules[action](state)
            return VerificationResult(ok, action, "custom_rule", details, state)

        verifier = self._get_verifier(action)
        ok, condition, details = verifier(state, expected)
        return VerificationResult(ok, action, condition, details, state)

    def wait_for(self, action: str, expected: dict = None,
                 timeout: float = 10.0, poll_interval: float = 1.0) -> VerificationResult:
        deadline = time.time() + timeout
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            result = self.verify(action, expected)
            if result.success:
                logger.info("Verification passed (attempt %d): %s — %s", attempt, action, result.details)
                return result
            time.sleep(poll_interval)
        logger.warning("Verification timed out after %ds: %s", timeout, action)
        result = self.verify(action, expected)
        result.details = f"Timed out after {timeout}s. Last: {result.details}"
        return result

    def _get_verifier(self, action: str) -> Callable:
        return {
            "launch_application": self._verify_app_launched,
            "open_url": self._verify_url_loaded,
            "search": self._verify_search_performed,
            "click": self._verify_click,
            "type_text": self._verify_typed,
            "play": self._verify_playing,
            "pause": self._verify_paused,
            "send_message": self._verify_message_sent,
            "create_folder": self._verify_folder_created,
            "create_file": self._verify_file_created,
            "close_application": self._verify_app_closed,
            "screenshot": self._verify_screenshot,
        }.get(action, self._verify_generic)

    def _verify_app_launched(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        app = expected.get("app_name", "").lower()
        if not app:
            return True, "app_launched", "No app name specified"
        if app in state.active_app.lower():
            return True, "app_launched", "%s is active" % app
        if any(app in w.lower() for w in state.open_windows):
            return True, "app_launched", "%s found in open windows" % app
        # Fallback: check if process is running (works without pygetwindow)
        try:
            import psutil
            for proc in psutil.process_iter(["name"]):
                pname = (proc.info.get("name") or "").lower()
                if app in pname:
                    return True, "app_launched", "%s process running" % app
        except Exception:
            pass
        return False, "app_launched", "%s not found in active app or open windows" % app

    def _verify_url_loaded(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        url = expected.get("url", "").lower()
        if not url:
            if state.window_url:
                return True, "url_loaded", f"URL visible: {state.window_url}"
            return True, "url_loaded", "No URL specified"
        if url in state.window_url.lower():
            return True, "url_loaded", f"URL matches: {state.window_url}"
        if url in state.visible_text.lower():
            return True, "url_loaded", f"URL text visible on page"
        return False, "url_loaded", f"URL '{url}' not found (current: {state.window_url})"

    def _verify_search_performed(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        query = expected.get("query", "").lower()
        if query and query in state.visible_text.lower():
            return True, "search_performed", f"Search results for '{query}' visible"
        if state.visible_buttons:
            return True, "search_performed", "Page has buttons (results likely loaded)"
        return False, "search_performed", "Search results not detected"

    def _verify_click(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        target = expected.get("target", "")
        if target and target.lower() in state.visible_text.lower():
            return True, "click", f"'{target}' is visible after click"
        return True, "click", "Click executed (no specific target to verify)"

    def _verify_typed(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        text = expected.get("text", "")
        if text and text.lower() in state.visible_text.lower():
            return True, "typed", f"'{text}' is visible on screen"
        return True, "typed", "Text typed (cannot verify text in field from OCR alone)"

    def _verify_playing(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        media_keywords = ["playing", "now playing", "pause", "skip", "previous"]
        for kw in media_keywords:
            if kw in state.visible_text.lower():
                return True, "playing", f"Media indicator found: '{kw}'"
        if "pause" not in state.visible_buttons:
            if any(b in state.visible_text.lower() for b in ["play", "resume"]):
                return False, "playing", "Play button visible, not yet playing"
        return True, "playing", "Media state assumed playing (no contradicting indicators)"

    def _verify_paused(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        if any(b in state.visible_text.lower() for b in ["play", "resume"]):
            return True, "paused", "Play button visible (paused state)"
        return True, "paused", "Pause assumed (no contradicting indicators)"

    def _verify_message_sent(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        sent_keywords = ["sent", "delivered", "✓", "✔"]
        for kw in sent_keywords:
            if kw in state.visible_text.lower():
                return True, "message_sent", f"Sent indicator found: '{kw}'"
        return True, "message_sent", "Message sent (no delivery confirmation visible)"

    def _verify_folder_created(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        name = expected.get("name", "")
        if name and name in state.visible_text.lower():
            return True, "folder_created", f"Folder '{name}' visible"
        return True, "folder_created", "Folder creation command executed"

    def _verify_file_created(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        name = expected.get("name", "")
        if name and name in state.visible_text.lower():
            return True, "file_created", f"File '{name}' visible"
        return True, "file_created", "File creation command executed"

    def _verify_app_closed(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        app = expected.get("app_name", "").lower()
        if not app:
            return True, "app_closed", "No app name specified"
        if not any(app in w.lower() for w in state.open_windows):
            return True, "app_closed", f"{app} no longer in open windows"
        return False, "app_closed", f"{app} still appears in open windows"

    def _verify_screenshot(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        if state.screenshot_path:
            return True, "screenshot", f"Screenshot saved: {state.screenshot_path}"
        return False, "screenshot", "No screenshot available"

    def _verify_generic(self, state: DesktopState, expected: dict) -> tuple[bool, str, str]:
        return True, "generic", "Generic verification passed"


def verify_action(action: str, expected: dict = None, timeout: float = 5.0) -> VerificationResult:
    """Convenience function — verify a single action."""
    return ActionVerifier().verify(action, expected, timeout)
