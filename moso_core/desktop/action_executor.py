"""Action Executor — dispatches planner steps to real functions."""
from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes planner steps by dispatching to existing MOSO modules."""

    def __init__(self):
        self._app_tool = None
        self._keyboard = None
        self._mouse = None

    def _ensure_modules(self):
        if self._app_tool is not None:
            return
        try:
            from moso_core.tools.app_tool import AppTool
            self._app_tool = AppTool()
        except Exception:
            logger.warning("AppTool not available")
        try:
            from moso_core.computer_use.keyboard import KeyboardController
            self._keyboard = KeyboardController()
        except Exception:
            logger.warning("KeyboardController not available")
        try:
            from moso_core.computer_use.mouse import MouseController
            self._mouse = MouseController()
        except Exception:
            logger.warning("MouseController not available")

    def __call__(self, action: str, params: dict) -> str:
        self._ensure_modules()
        handler = getattr(self, "_do_" + action, None)
        if handler:
            return handler(params)
        logger.warning("Unknown planner action: %s", action)
        return f"Unknown action: {action}"

    def _do_launch_application(self, params: dict) -> str:
        app_name = params.get("app_name", "")
        if not app_name:
            return "No app name specified"
        if self._app_tool:
            result = self._app_tool.launch_application(app_name)
            if result.success:
                log = result.result or {}
                name = log.get("matched_alias", app_name)
                # Track in desktop memory
                try:
                    from moso_core.desktop.desktop_memory import DesktopMemory
                    mem = DesktopMemory()
                    mem.load()
                    mem.update_active_app(name)
                    mem.record_action("launch %s" % name)
                    mem.save()
                except Exception:
                    pass
                return "Launched %s" % name
            return result.error or "Failed to launch %s" % app_name
        return "Cannot launch %s: AppTool not available" % app_name

    def _do_close_application(self, params: dict) -> str:
        app_name = params.get("app_name", "")
        if not app_name:
            return "No app name specified"
        if self._app_tool:
            result = self._app_tool.close_application(app_name)
            if result.success:
                return f"Closed {app_name}"
            return result.error or f"Failed to close {app_name}"
        return f"Cannot close {app_name}: AppTool not available"

    def _do_type_text(self, params: dict) -> str:
        text = params.get("text", "")
        if not text:
            return "No text to type"
        if self._keyboard and self._keyboard.available:
            self._keyboard.type_text(text)
            return f"Typed: {text}"
        return "Keyboard not available"

    def _do_press_key(self, params: dict) -> str:
        key = params.get("key", "")
        if not key:
            return "No key specified"
        if self._keyboard and self._keyboard.available:
            self._keyboard.press(key)
            return f"Pressed: {key}"
        return "Keyboard not available"

    def _do_click(self, params: dict) -> str:
        target = params.get("target", "")
        if self._mouse and self._mouse.available:
            try:
                from moso_core.desktop.perception import DesktopPerceiver
                state = DesktopPerceiver().observe()
                for elem in state.ui_elements:
                    if target.lower() in elem.text.lower():
                        cx, cy = elem.center
                        self._mouse.click(cx, cy)
                        return "Clicked '%s' at (%d,%d)" % (elem.text, cx, cy)
            except Exception:
                pass
            try:
                import pyautogui
                w, h = pyautogui.size()
                self._mouse.click(w // 2, h // 2)
                return "Clicked center (target '%s' not found)" % target
            except Exception:
                pass
        return "Mouse not available"

    def _do_open_url(self, params: dict) -> str:
        url = params.get("url", "")
        if not url:
            return "No URL specified"
        import subprocess
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", url],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True,
            )
            return "Opened %s" % url
        except Exception as e:
            return "Failed to open URL: %s" % e

    def _do_execute_goal(self, params: dict) -> str:
        goal = params.get("goal", "")
        try:
            from moso_core.desktop.smart_controllers import get_smart_controller
            from moso_core.desktop.perception import DesktopPerceiver
            state = DesktopPerceiver().observe()
            if state.active_app:
                ctrl = get_smart_controller(state.active_app)
                if ctrl:
                    return ctrl.handle("general", goal, state)
        except Exception:
            pass
        return "Goal noted: %s" % goal

    def _do_focus_window(self, params: dict) -> str:
        app_name = params.get("app_name", "")
        if not app_name:
            return "No app name specified"
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(app_name)
            if windows:
                win = windows[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                return "Focused: %s" % win.title
        except Exception as e:
            return "Focus failed: %s" % e
        return "Window not found: %s" % app_name

    def _do_screenshot(self, params: dict) -> str:
        try:
            import mss
            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[1])
                path = params.get("path", "screenshot.png")
                mss.tools.to_png(shot.rgb, shot.size, output=path)
                return "Screenshot saved: %s" % path
        except Exception as e:
            return "Screenshot failed: %s" % e

    def _do_double_click(self, params: dict) -> str:
        target = params.get("target", "")
        if self._mouse and self._mouse.available:
            try:
                from moso_core.desktop.perception import DesktopPerceiver
                state = DesktopPerceiver().observe()
                for elem in state.ui_elements:
                    if target.lower() in elem.text.lower():
                        cx, cy = elem.center
                        self._mouse.double_click(cx, cy)
                        return "Double-clicked '%s' at (%d,%d)" % (elem.text, cx, cy)
            except Exception:
                pass
        return "Mouse not available"

    def _do_scroll(self, params: dict) -> str:
        direction = params.get("direction", "down")
        if self._mouse and self._mouse.available:
            clicks = 3 if direction == "down" else -3
            self._mouse.scroll(clicks)
            return "Scrolled %s" % direction
        return "Mouse not available"

    def _do_play_media(self, params: dict) -> str:
        target = params.get("target", "")
        if not target:
            return "No media target specified"
        # Try smart controllers first (Spotify, etc.)
        try:
            from moso_core.desktop.smart_controllers import get_smart_controller
            from moso_core.desktop.perception import DesktopPerceiver
            state = DesktopPerceiver().observe()
            # Check if Spotify is active
            if state.active_app and "spotify" in state.active_app.lower():
                ctrl = get_smart_controller("spotify")
                if ctrl:
                    return ctrl.handle("search", target, state)
            # Try launching Spotify and searching
            from moso_core.tools.app_tool import AppTool
            result = AppTool().launch_application("spotify")
            if result.success:
                import time
                time.sleep(3)
                state = DesktopPerceiver().observe()
                ctrl = get_smart_controller("spotify")
                if ctrl:
                    return ctrl.handle("search", target, state)
        except Exception as e:
            return "Play media failed: %s" % e
        return "No media player available"

    def _do_play(self, params: dict) -> str:
        target = params.get("target", "")
        if not target:
            return "No target specified"
        try:
            from moso_core.desktop.smart_controllers import get_smart_controller
            from moso_core.desktop.perception import DesktopPerceiver
            state = DesktopPerceiver().observe()
            # Try Spotify
            ctrl = get_smart_controller("spotify")
            if ctrl:
                return ctrl.handle("search", target, state)
        except Exception as e:
            return "Play failed: %s" % e
        return "No media player available"

    def _do_pause(self, params: dict) -> str:
        if self._keyboard and self._keyboard.available:
            self._keyboard.press("playpause")
            return "Paused playback"
        return "Keyboard not available"

    def _do_resume(self, params: dict) -> str:
        return self._do_pause(params)

    def _do_next_track(self, params: dict) -> str:
        if self._keyboard and self._keyboard.available:
            self._keyboard.press("nexttrack")
            return "Next track"
        return "Keyboard not available"

    def _do_prev_track(self, params: dict) -> str:
        if self._keyboard and self._keyboard.available:
            self._keyboard.press("prevtrack")
            return "Previous track"
        return "Keyboard not available"
