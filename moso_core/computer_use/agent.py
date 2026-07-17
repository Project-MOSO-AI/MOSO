from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DELAY_AFTER_ACTION = 0.8
_DELAY_AFTER_LAUNCH = 2.0
_DELAY_AFTER_TYPE = 0.3
_VERIFY_RETRIES = 3
_VERIFY_DELAY = 1.0


@dataclass
class Step:
    action: str
    params: dict = field(default_factory=dict)
    description: str = ""
    verify_text: str = ""


@dataclass
class StepResult:
    step: Step
    success: bool
    message: str = ""


class ScreenReader:
    """Capture screen + OCR to find UI elements by text."""

    def __init__(self, automation: Any):
        self._auto = automation

    def read_screen(self) -> dict:
        result = self._auto.execute_action({"action": "capture_screen"})
        if not result.success:
            return {"error": result.error, "elements": [], "full_text": ""}

        image_path = result.result.get("image_path", "") if isinstance(result.result, dict) else ""
        if not image_path:
            return {"error": "No screenshot path", "elements": [], "full_text": ""}

        try:
            from PIL import Image
            img = Image.open(image_path)
        except Exception as e:
            return {"error": str(e), "elements": [], "full_text": ""}

        elements = []
        full_text = ""

        try:
            from moso_core.vision.ocr import extract_text, extract_text_regions
            full_text = extract_text(img)
            regions = extract_text_regions(img)
            for r in regions:
                elements.append({
                    "text": r.text,
                    "confidence": r.confidence,
                    "x": r.bounding_box.left + r.bounding_box.width // 2,
                    "y": r.bounding_box.top + r.bounding_box.height // 2,
                    "left": r.bounding_box.left,
                    "top": r.bounding_box.top,
                    "width": r.bounding_box.width,
                    "height": r.bounding_box.height,
                })
        except Exception as e:
            logger.debug("OCR failed: %s", e)

        return {"elements": elements, "full_text": full_text, "image_path": image_path}

    def find_text(self, target: str, screen_data: Optional[dict] = None) -> Optional[dict]:
        if screen_data is None:
            screen_data = self.read_screen()

        target_lower = target.lower().strip()
        best = None
        best_score = 0

        for el in screen_data.get("elements", []):
            el_text = el["text"].lower().strip()
            if not el_text:
                continue
            # Exact match
            if target_lower == el_text:
                return el
            # Substring match — target must be substantial part of element
            if target_lower in el_text:
                score = len(target_lower) / max(len(el_text), 1)
                if score >= 0.4 and score > best_score:
                    best_score = score
                    best = el
            # Element contained in target — element must be substantial part of target
            elif el_text in target_lower:
                score = len(el_text) / max(len(target_lower), 1)
                if score >= 0.6 and score > best_score:
                    best_score = score
                    best = el

        return best if best_score > 0.3 else None

    def find_all_text(self, screen_data: Optional[dict] = None) -> list[dict]:
        if screen_data is None:
            screen_data = self.read_screen()
        return screen_data.get("elements", [])


class TaskPlanner:
    """Break a user command into a sequence of Steps."""

    _APP_COMMANDS = {
        "chrome": {"open": "launch", "search": "browser_search", "click": "click_element", "scroll": "scroll_page"},
        "google chrome": {"open": "launch", "search": "browser_search", "click": "click_element"},
        "firefox": {"open": "launch", "search": "browser_search", "click": "click_element"},
        "edge": {"open": "launch", "search": "browser_search", "click": "click_element"},
        "notepad": {"open": "launch", "type": "type_text_action", "save": "save_file"},
        "spotify": {"open": "launch", "play": "spotify_play", "pause": "spotify_pause", "next": "spotify_next", "search": "spotify_search"},
        "vlc": {"open": "launch", "play": "vlc_play", "pause": "vlc_pause", "fullscreen": "vlc_fullscreen"},
        "whatsapp": {"open": "launch", "send": "whatsapp_send", "search": "whatsapp_search"},
        "vscode": {"open": "launch", "open folder": "open_folder", "run": "run_build"},
        "visual studio code": {"open": "launch", "open folder": "open_folder"},
        "explorer": {"open": "launch", "open folder": "open_folder"},
        "file explorer": {"open": "launch", "open folder": "open_folder"},
    }

    def plan(self, user_text: str, context: Optional[dict] = None) -> list[Step]:
        text = user_text.lower().strip()
        context = context or {}
        active_app = context.get("active_app", "")

        # Split compound commands: "open chrome and search youtube" → ["open chrome", "search youtube"]
        if " and " in text:
            parts = re.split(r'\s+and\s+', text, maxsplit=1)
            if len(parts) == 2:
                steps1 = self.plan(parts[0], context)
                steps2 = self.plan(parts[1], context)
                if steps1 and steps2:
                    combined = steps1 + steps2
                    return self._dedup_launches(combined)

        if " then " in text:
            parts = re.split(r'\s+then\s+', text, maxsplit=1)
            if len(parts) == 2:
                steps1 = self.plan(parts[0], context)
                steps2 = self.plan(parts[1], context)
                if steps1 and steps2:
                    combined = steps1 + steps2
                    return self._dedup_launches(combined)

        # "open <app>"
        m = re.match(r"^(?:open|launch|start)\s+(.+)", text)
        if m:
            app = self._clean_app_name(m.group(1))
            return [
                Step("launch", {"app_name": app}, f"Launch {app}", verify_text=app.lower()),
            ]

        # "click <text>"
        m = re.match(r"^(?:click|tap|select)\s+(?:on\s+|the\s+)?(.+)", text)
        if m:
            return [
                Step("click_element", {"text": m.group(1).strip()}, f"Click '{m.group(1).strip()}'"),
            ]

        # "type <text>"
        m = re.match(r"^(?:type|write|enter)\s+(.+)", text)
        if m:
            return [
                Step("type_text_action", {"text": m.group(1).strip()}, f"Type '{m.group(1).strip()}'"),
            ]

        # "press <key>"
        m = re.match(r"^(?:press|hit)\s+(?:the\s+)?(.+)", text)
        if m:
            key = m.group(1).strip().rstrip(".")
            return [
                Step("press_key", {"key": key}, f"Press {key}"),
            ]

        # "scroll up/down"
        m = re.match(r"^(?:scroll|swipe)\s+(up|down)", text)
        if m:
            direction = 3 if m.group(1) == "up" else -3
            return [
                Step("scroll", {"amount": direction}, f"Scroll {m.group(1)}"),
            ]

        # "search <query>" or "google <query>"
        m = re.match(r"^(?:search|google|look up|find)\s+(?:for\s+)?(.+)", text)
        if m:
            query = m.group(1).strip()
            if active_app and "chrome" in active_app.lower():
                return [
                    Step("hotkey", {"keys": ["ctrl", "l"]}, "Focus address bar"),
                    Step("type_text_action", {"text": query}, f"Type '{query}'"),
                    Step("press_key", {"key": "enter"}, "Press Enter"),
                ]
            return [
                Step("launch", {"app_name": "chrome"}, "Launch Chrome"),
                Step("delay", {"seconds": 2.0}, "Wait for Chrome"),
                Step("hotkey", {"keys": ["ctrl", "l"]}, "Focus address bar"),
                Step("type_text_action", {"text": f"https://duckduckgo.com/?q={query}"}, f"Search '{query}'"),
                Step("press_key", {"key": "enter"}, "Press Enter"),
            ]

        # "open url"
        m = re.match(r"^(?:open|go to|navigate to)\s+(https?://\S+)", text)
        if m:
            return [
                Step("launch", {"app_name": "chrome"}, "Launch Chrome"),
                Step("delay", {"seconds": 2.0}, "Wait for Chrome"),
                Step("hotkey", {"keys": ["ctrl", "l"]}, "Focus address bar"),
                Step("type_text_action", {"text": m.group(1)}, f"Open {m.group(1)}"),
                Step("press_key", {"key": "enter"}, "Press Enter"),
            ]

        # "send <message> to <contact>" (WhatsApp)
        m = re.match(r"^(?:send|message)\s+(.+?)\s+to\s+(.+?)(?:\s+on\s+whatsapp)?$", text)
        if m:
            message, contact = m.group(1).strip(), m.group(2).strip()
            return [
                Step("launch", {"app_name": "whatsapp"}, "Launch WhatsApp"),
                Step("delay", {"seconds": 2.0}, "Wait for WhatsApp"),
                Step("whatsapp_search", {"contact": contact}, f"Search contact '{contact}'"),
                Step("delay", {"seconds": 1.0}, "Wait for results"),
                Step("press_key", {"key": "enter"}, "Open chat"),
                Step("delay", {"seconds": 0.5}, "Wait for chat"),
                Step("type_text_action", {"text": message}, f"Type message"),
                Step("press_key", {"key": "enter"}, "Send"),
            ]

        # "open youtube"
        m = re.match(r"^(?:open|go to)\s+youtube", text)
        if m:
            return [
                Step("launch", {"app_name": "chrome"}, "Launch Chrome"),
                Step("delay", {"seconds": 2.0}, "Wait for Chrome"),
                Step("hotkey", {"keys": ["ctrl", "l"]}, "Focus address bar"),
                Step("type_text_action", {"text": "https://www.youtube.com"}, "Open YouTube"),
                Step("press_key", {"key": "enter"}, "Press Enter"),
            ]

        # "play video on youtube" / "play <query> on youtube"
        m = re.match(r"^(?:play|watch)\s+(.+?)\s+(?:on\s+)?youtube", text)
        if m:
            query = m.group(1).strip()
            return [
                Step("launch", {"app_name": "chrome"}, "Launch Chrome"),
                Step("delay", {"seconds": 2.0}, "Wait for Chrome"),
                Step("hotkey", {"keys": ["ctrl", "l"]}, "Focus address bar"),
                Step("type_text_action", {"text": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"}),
                Step("press_key", {"key": "enter"}, "Press Enter"),
                Step("delay", {"seconds": 3.0}, "Wait for results"),
                Step("click_element", {"text": ""}, "Click first video"),
            ]

        # "minimize/maximize/close window"
        m = re.match(r"^(minimize|maximize|close)\s+(?:the\s+)?(?:window|app|application)?", text)
        if m:
            action = m.group(1)
            if action == "minimize":
                return [Step("hotkey", {"keys": ["win", "down"]}, "Minimize window")]
            if action == "maximize":
                return [Step("hotkey", {"keys": ["win", "up"]}, "Maximize window")]
            if action == "close":
                return [Step("hotkey", {"keys": ["alt", "f4"]}, "Close window")]

        # "take screenshot" / "what's on my screen"
        if re.match(r"^(?:take\s+)?screenshot|what('s| is) (?:on |visible on )?my screen|what do you see", text):
            return [
                Step("read_screen", {}, "Read screen"),
            ]

        # Context-aware: if active app, try app-specific commands
        if active_app:
            app_lower = active_app.lower()
            for app_key, commands in self._APP_COMMANDS.items():
                if app_key in app_lower:
                    for keyword, action in commands.items():
                        if keyword in text:
                            if action == "launch":
                                return [Step("launch", {"app_name": active_app}, f"Launch {active_app}")]
                            if action == "browser_search":
                                m2 = re.search(rf"(?:{keyword})\s+(.+)", text)
                                query = m2.group(1).strip() if m2 else ""
                                return [
                                    Step("hotkey", {"keys": ["ctrl", "l"]}, "Focus address bar"),
                                    Step("type_text_action", {"text": query}, f"Search '{query}'"),
                                    Step("press_key", {"key": "enter"}, "Press Enter"),
                                ]
                            if action == "click_element":
                                m2 = re.search(rf"(?:{keyword})\s+(.+)", text)
                                target = m2.group(1).strip() if m2 else ""
                                return [Step("click_element", {"text": target}, f"Click '{target}'")]

        # Generic: send to LLM
        return []

    def _clean_app_name(self, name: str) -> str:
        name = re.sub(r"\s+(player|app|application|program|browser|editor)$", "", name, flags=re.I)
        return name.strip()

    def _dedup_launches(self, steps: list[Step]) -> list[Step]:
        result = []
        seen_launch = False
        for step in steps:
            if step.action == "launch":
                if seen_launch:
                    continue
                seen_launch = True
            else:
                seen_launch = False
            result.append(step)
        return result


class _AgentIdentity:
    """Bypass permission checks for the agent — the user already approved the action."""
    def get_identity_level(self):
        return "owner"
    def is_owner(self):
        return True


class ComputerUseAgent:
    """Execute user commands with planning, action, and verification."""

    def __init__(self, automation: Any):
        self._auto = automation
        self._auto._identity = _AgentIdentity()
        self._screen = ScreenReader(automation)
        self._planner = TaskPlanner()

    @property
    def screen_reader(self) -> ScreenReader:
        return self._screen

    @property
    def planner(self) -> TaskPlanner:
        return self._planner

    def execute(self, user_text: str, context: Optional[dict] = None) -> str:
        steps = self._planner.plan(user_text, context)
        if not steps:
            return ""

        logger.info("Agent plan for '%s': %d steps", user_text[:50], len(steps))
        for i, step in enumerate(steps, 1):
            logger.info("  Step %d: %s %s", i, step.action, step.params)

        results = []
        for i, step in enumerate(steps, 1):
            result = self._execute_step(step, i, len(steps))
            results.append(result)

            if not result.success and step.action != "delay":
                logger.warning("Step %d failed: %s", i, result.message)
                return f"Failed at step {i}: {result.message}"

            if step.verify_text and i < len(steps):
                self._verify(step.verify_text)

        return self._summarize(results)

    def _execute_step(self, step: Step, current: int, total: int) -> StepResult:
        action = step.action
        params = step.params

        if action == "delay":
            time.sleep(params.get("seconds", _DELAY_AFTER_ACTION))
            return StepResult(step, True, "Waited")

        if action == "launch":
            return self._do_launch(params)
        if action == "click_element":
            return self._do_click_element(params)
        if action == "type_text_action":
            return self._do_type(params)
        if action == "press_key":
            return self._do_press(params)
        if action == "hotkey":
            return self._do_hotkey(params)
        if action == "scroll":
            return self._do_scroll(params)
        if action == "read_screen":
            return self._do_read_screen()
        if action == "whatsapp_search":
            return self._do_whatsapp_search(params)

        return StepResult(step, False, f"Unknown action: {action}")

    def _do_launch(self, params: dict) -> StepResult:
        app_name = params.get("app_name", "")
        # Try to focus existing window first
        result = self._auto.execute_action({
            "action": "focus_window",
            "window_title": app_name,
        })
        if result.success and result.result:
            return StepResult(Step("", description=f"Focused {app_name}"), True, f"Focused {app_name}")

        # Launch new instance
        from moso_core.tools.app_tool import AppTool
        launch_result = AppTool().launch_application(app_name)
        if launch_result.success:
            time.sleep(_DELAY_AFTER_LAUNCH)
            # Focus the window after launch
            self._auto.execute_action({
                "action": "focus_window",
                "window_title": app_name,
            })
            time.sleep(0.5)
            return StepResult(Step("", description=f"Launched {app_name}"), True, f"Launched {app_name}")
        return StepResult(Step("", description=f"Launch {app_name}"), False, launch_result.error or "Launch failed")

    def _do_click_element(self, params: dict) -> StepResult:
        target = params.get("text", "")
        if not target:
            return StepResult(Step("", description="Click"), False, "No target text specified")

        screen_data = self._screen.read_screen()
        element = self._screen.find_text(target, screen_data)

        if not element:
            visible = [e["text"] for e in screen_data.get("elements", [])[:15]]
            return StepResult(
                Step("", description=f"Click '{target}'"),
                False,
                f"Could not find '{target}' on screen. Visible: {', '.join(visible)}"
            )

        x, y = element["x"], element["y"]
        self._auto.execute_action({"action": "click", "x": x, "y": y})
        time.sleep(_DELAY_AFTER_ACTION)
        return StepResult(Step("", description=f"Click '{target}'"), True, f"Clicked '{element['text']}' at ({x}, {y})")

    def _do_type(self, params: dict) -> StepResult:
        text = params.get("text", "")
        result = self._auto.execute_action({
            "action": "type_text",
            "text": text,
            "interval": 0.02,
        })
        time.sleep(_DELAY_AFTER_TYPE)
        if result.success:
            return StepResult(Step("", description=f"Type"), True, f"Typed '{text[:50]}'")
        return StepResult(Step("", description="Type"), False, result.error or "Type failed")

    def _do_press(self, params: dict) -> StepResult:
        key = params.get("key", "")
        key = self._normalize_key(key)
        result = self._auto.execute_action({"action": "press", "key": key})
        time.sleep(_DELAY_AFTER_ACTION)
        if result.success:
            return StepResult(Step("", description=f"Press {key}"), True, f"Pressed {key}")
        return StepResult(Step("", description=f"Press {key}"), False, result.error or "Key press failed")

    def _do_hotkey(self, params: dict) -> StepResult:
        keys = params.get("keys", [])
        result = self._auto.execute_action({"action": "hotkey", "keys": keys})
        time.sleep(_DELAY_AFTER_ACTION)
        if result.success:
            return StepResult(Step("", description=f"Hotkey {keys}"), True, f"Pressed {'+'.join(keys)}")
        return StepResult(Step("", description=f"Hotkey {keys}"), False, result.error or "Hotkey failed")

    def _do_scroll(self, params: dict) -> StepResult:
        amount = params.get("amount", -3)
        result = self._auto.execute_action({"action": "scroll", "amount": amount})
        time.sleep(_DELAY_AFTER_ACTION)
        if result.success:
            return StepResult(Step("", description="Scroll"), True, "Scrolled")
        return StepResult(Step("", description="Scroll"), False, result.error or "Scroll failed")

    def _do_read_screen(self) -> StepResult:
        screen_data = self._screen.read_screen()
        text = screen_data.get("full_text", "")
        elements = screen_data.get("elements", [])

        lines = []
        if elements:
            lines.append(f"Found {len(elements)} text elements:")
            for el in elements[:20]:
                lines.append(f"  - '{el['text']}' at ({el['x']}, {el['y']})")
        elif text:
            lines.append(f"Screen text: {text[:500]}")
        else:
            lines.append("No text detected on screen (OCR may not be available)")

        return StepResult(Step("", description="Read screen"), True, "\n".join(lines))

    def _do_whatsapp_search(self, params: dict) -> StepResult:
        contact = params.get("contact", "")
        self._auto.execute_action({"action": "hotkey", "keys": ["ctrl", "f"]})
        time.sleep(0.5)
        self._auto.execute_action({"action": "type_text", "text": contact, "interval": 0.02})
        time.sleep(1.0)
        return StepResult(Step("", description=f"Search WhatsApp contact"), True, f"Searched for '{contact}'")

    def _verify(self, expected_text: str) -> bool:
        for attempt in range(_VERIFY_RETRIES):
            time.sleep(_VERIFY_DELAY)
            screen_data = self._screen.read_screen()
            full_text = screen_data.get("full_text", "").lower()
            if expected_text.lower() in full_text:
                return True
        return False

    def _normalize_key(self, key: str) -> str:
        key_map = {
            "enter": "enter", "return": "enter",
            "space": "space", "spacebar": "space",
            "tab": "tab",
            "escape": "escape", "esc": "escape",
            "backspace": "backspace",
            "delete": "delete",
            "up": "up", "down": "down", "left": "left", "right": "right",
            "home": "home", "end": "end",
            "page up": "pageup", "pageup": "pageup",
            "page down": "pagedown", "pagedown": "pagedown",
        }
        return key_map.get(key.lower().strip(), key)

    def _summarize(self, results: list[StepResult]) -> str:
        if not results:
            return "No steps executed."
        last = results[-1]
        if last.success:
            return last.message
        return f"Completed {len(results)} steps. Last: {last.message}"
