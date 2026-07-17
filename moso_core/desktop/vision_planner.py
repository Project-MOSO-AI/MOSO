"""A.3 — Vision Planner: observe→reason→act→verify loop with replanning."""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable

from moso_core.desktop.perception import DesktopPerceiver, DesktopState
from moso_core.desktop.perception_log import PerceptionLog
from moso_core.desktop.world_model import WorldModel
from moso_core.desktop.verifier import ActionVerifier, VerificationResult

logger = logging.getLogger(__name__)

SEARCH_PROVIDER = "https://duckduckgo.com"  # zero-API: no Google, no tracking


class StepStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"

ACTION_PLANNER_PROMPT = """Given the user's goal and the current desktop state, produce a JSON action plan.

Goal: {user_goal}

Desktop state:
  Active window: {active_window}
  All open windows: {window_list}
  Current URL: {current_url}
  Focused element: {focused_element}
  Screen OCR summary: {ocr_summary}

Produce a JSON plan:
{
  "goal_summary": "one line description of the full goal",
  "speak_start": "what to say to the user before starting",
  "steps": [
    {
      "step": 1,
      "action": "open_app | click | type | press_key | scroll | wait | observe",
      "target": "description of what to act on",
      "value": "text to type or key to press (if applicable)",
      "verify": "what to check in screenshot to confirm this step worked",
      "retry_if": "what failure looks like",
      "speak": null  // only set on first and last step
    }
  ],
  "speak_end": "what to say to the user when fully done",
  "fallback": "what to say if something goes wrong"
}

Rules:
- Include EVERY substep, not just the top-level action
- For media: include finding the right content, clicking play, verifying playback
- For messaging: include finding the contact, clicking input, typing, sending, verifying
- For typing tasks: include clicking the text area, typing, verifying text appeared
- For browser tasks: include navigation, finding elements, clicking, verifying page changed
- speak field is null for intermediate steps (only start and end are spoken aloud)
"""


@dataclass
class PlanStep:
    action: str
    description: str
    params: dict = field(default_factory=dict)
    expected_outcome: dict = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: str = ""
    verification: Optional[VerificationResult] = None

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
        }


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    current_step: int = 0
    completed: bool = False
    failed: bool = False
    failure_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "current_step": self.current_step,
            "completed": self.completed,
            "failed": self.failed,
        }

    def summary(self) -> str:
        lines = [f"Goal: {self.goal}"]
        for i, step in enumerate(self.steps):
            marker = ">" if i == self.current_step else " "
            icon = {"pending": "[ ]", "executing": "[>]", "verified": "[x]",
                    "failed": "[!]", "skipped": "[-]"}[step.status.value]
            lines.append(f"  {marker} {icon} {step.description}")
        return "\n".join(lines)


# ponytail: rule-based planner — covers common desktop tasks
# upgrade to LLM-based planning when the planner needs to handle novel goals
_PLANNING_RULES: list[tuple[str, str, list[str]]] = [
    # (pattern, action_template, description_template)
    (r"open\s+(\w[\w\s]*?)\s+and\s+(.+)", "multi_app", "Open {0} and {1}"),
    (r"open\s+(chrome|firefox|edge)\s+and\s+go\s+to\s+(.+)", "open_url_in_browser", "Open browser to {1}"),
    (r"open\s+(chrome|firefox|edge)\s+and\s+search\s+(.+)", "search_in_browser", "Search {1} in browser"),
    (r"open\s+(chrome|firefox|edge)\s+and\s+play\s+(.+)", "play_in_browser", "Play {1} in browser"),
    (r"open\s+(.+)\s+and\s+play\s+(.+)", "play_in_app", "Play {1} in {0}"),
    (r"open\s+(.+)", "launch_app", "Open {0}"),
    (r"go\s+to\s+(.+)", "open_url", "Navigate to {0}"),
    (r"search\s+(?:for\s+)?(.+)", "search_web", "Search for {0}"),
    (r"play\s+(.+?)\s+in\s+spotify", "play_in_spotify", "Play {0} in Spotify"),
    (r"play\s+(.+?)\s+playlist\s+in\s+spotify", "play_playlist_in_spotify", "Play {0} playlist in Spotify"),
    (r"play\s+(.+)", "play_media", "Play {0}"),
    (r"pause", "pause", "Pause playback"),
    (r"stop", "pause", "Stop playback"),
    (r"resume", "resume", "Resume playback"),
    (r"next\s*(?:track|song|video)?", "next_track", "Next track"),
    (r"previous\s*(?:track|song|video)?", "prev_track", "Previous track"),
    (r"take\s+a?\s*screenshot", "screenshot", "Take screenshot"),
    (r"what(?:'s|\s+is)\s+(?:on\s+)?(?:the\s+)?screen", "observe_screen", "Observe screen"),
    (r"what\s+(?:app(?:lication)?|program)\s+(?:am\s+)?(?:i|you)\s+(?:using|looking\s+at|running)", "observe_screen", "Observe current app"),
    (r"which\s+app\s+(?:am\s+)?(?:i|you)\s+using", "observe_screen", "Observe current app"),
    (r"what(?:'s|\s+is)\s+(?:open|running|active)", "observe_screen", "Observe active app"),
    (r"click\s+(.+)", "click_element", "Click '{0}'"),
    (r"type\s+(.+)", "type_text", "Type '{0}'"),
    (r"scroll\s+(up|down)", "scroll", "Scroll {0}"),
    (r"close\s+(.+)", "close_app", "Close {0}"),
    (r"create\s+(?:a\s+)?(?:folder|directory)\s+(.+)", "create_folder", "Create folder {0}"),
    (r"run\s+(.+)", "run_command", "Run command: {0}"),
]


class VisionPlanner:
    """Plans and executes multi-step desktop tasks with observe→reason→act→verify loop."""

    def __init__(self, max_iterations: int = 15, verify_timeout: float = 8.0):
        self._perceiver = DesktopPerceiver()
        self._world = WorldModel()
        self._verifier = ActionVerifier()
        self._max_iterations = max_iterations
        self._verify_timeout = verify_timeout
        self._action_executor: Optional[Callable[[str, dict], str]] = None
        self._on_step: Optional[Callable[[PlanStep], None]] = None
        self._llm = None
        self._memory = None
        self._perception_log = PerceptionLog()

    def set_llm(self, llm):
        self._llm = llm
        
    def set_memory(self, memory):
        self._memory = memory

    def set_action_executor(self, executor: Callable[[str, dict], str]):
        self._action_executor = executor

    def set_step_callback(self, callback: Callable[[PlanStep], None]):
        self._on_step = callback

    def create_plan(self, goal: str, state: Optional[DesktopState] = None) -> Plan:
        if state is None:
            state = self._perceiver.observe()
        plan = Plan(goal=goal)
        goal_lower = goal.lower().strip()

        if self._memory:
            recipes = self._memory.retrieve_memories(goal, memory_types=["procedural"], limit=1)
            if recipes and "procedural" in recipes and recipes["procedural"]:
                recipe = recipes["procedural"][0]
                if self._llm:
                    import json
                    logger.info("Found recipe '%s', adapting with LLM...", recipe.task_name)
                    prompt = f"""
You are adapting a saved MOSO procedure to the user's specific goal.

Goal: {goal}
Base Recipe:
{json.dumps(recipe.to_dict(), indent=2)}

Task:
Map any {{variables}} in the recipe to the specific details in the user's goal.
Output a JSON array of steps:
[
  {{ "action": "...", "target": "...", "value": "...", "verify": "..." }}
]
"""
                    try:
                        resp = self._llm.chat(prompt)
                        import re
                        json_match = re.search(r'\[.*\]', resp, re.DOTALL)
                        if json_match:
                            adapted_steps = json.loads(json_match.group(0))
                            for s in adapted_steps:
                                plan.steps.append(PlanStep(
                                    action=s.get("action", "execute_goal"),
                                    description=s.get("description", f"{s.get('action')} {s.get('target', '')}"),
                                    params={"target": s.get("target"), "text": s.get("value"), "key": s.get("value")},
                                    expected_outcome={"verify": s.get("verify", "")}
                                ))
                            logger.info("Successfully adapted recipe '%s' for goal", recipe.task_name)
                            return plan
                    except Exception as e:
                        logger.error("Failed to adapt recipe with LLM: %s", e)

        if self._llm:
            try:
                import json
                prompt = ACTION_PLANNER_PROMPT.format(
                    user_goal=goal,
                    active_window=getattr(state, 'active_app', '') or 'None',
                    window_list=', '.join(getattr(state, 'open_windows', [])) or 'None',
                    current_url=getattr(state, 'current_url', '') or 'None',
                    focused_element=getattr(state, 'focused_element', '') or 'None',
                    ocr_summary=getattr(state, 'ocr_text', '')[:500] or 'None'
                )
                
                resp = self._llm.chat(prompt)
                
                # Extract JSON from response
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', resp, re.DOTALL)
                if json_match:
                    plan_data = json.loads(json_match.group(1))
                else:
                    # try to parse raw response
                    json_str = resp[resp.find('{'):resp.rfind('}')+1]
                    plan_data = json.loads(json_str)
                    
                # Build steps
                steps = []
                for s in plan_data.get("steps", []):
                    action = s.get("action", "execute_goal")
                    # Map generic actions to what action_executor expects
                    if action == "open_app": action = "launch_application"
                    elif action == "press_key": action = "press_key"
                    
                    params = {}
                    if "target" in s and s["target"]:
                        params["target"] = s["target"]
                        if action == "launch_application": params["app_name"] = s["target"]
                    if "value" in s and s["value"]:
                        params["text"] = s["value"]
                        params["key"] = s["value"]
                        params["url"] = s["value"]

                    steps.append(PlanStep(
                        action=action,
                        description=s.get("description", f"Execute {action}"),
                        params=params,
                        expected_outcome={"verify": s.get("verify", "")}
                    ))
                plan.steps = steps
                logger.info("Created LLM plan with %d steps for: %s", len(plan.steps), goal)
                return plan
            except Exception as e:
                logger.error("Failed to generate plan with LLM: %s. Falling back to rules.", e)

        # Match against planning rules (fallback)
        for pattern, template, desc_template in _PLANNING_RULES:
            m = re.search(pattern, goal_lower)
            if m:
                groups = m.groups()
                steps = self._build_steps(template, groups, state)
                plan.steps = steps
                break

        # If no rules matched, create a single generic step
        if not plan.steps:
            plan.steps = [PlanStep(
                action="execute_goal",
                description=goal,
                params={"goal": goal},
                expected_outcome={"generic": True},
            )]

        logger.info("Created fallback plan with %d steps for: %s", len(plan.steps), goal)
        return plan

    def _build_steps(self, template: str, groups: tuple, state: DesktopState) -> list[PlanStep]:
        steps = []
        g = list(groups)

        if template == "multi_app":
            app_name = g[0] if len(g) > 0 else ""
            sub_action = g[1] if len(g) > 1 else ""
            steps.append(PlanStep(
                action="launch_application",
                description=f"Open {app_name}",
                params={"app_name": app_name},
                expected_outcome={"app_name": app_name},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for app to load",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="observe",
                description=f"Observe {app_name} loaded",
            ))
            # Parse the sub-action
            sub_lower = sub_action.lower()
            if "search" in sub_lower:
                query = re.sub(r"search\s+(?:for\s+)?", "", sub_lower).strip()
                steps.append(PlanStep(
                    action="type_text",
                    description=f"Type search: {query}",
                    params={"text": query},
                ))
                steps.append(PlanStep(
                    action="press_key",
                    description="Press Enter",
                    params={"key": "enter"},
                ))
                steps.append(PlanStep(
                    action="wait",
                    description="Wait for results",
                    params={"wait_seconds": 2.0},
                ))
            elif "play" in sub_lower:
                target = re.sub(r"play\s+", "", sub_lower).strip()
                steps.append(PlanStep(
                    action="type_text",
                    description=f"Search for: {target}",
                    params={"text": target},
                ))
                steps.append(PlanStep(
                    action="press_key",
                    description="Press Enter",
                    params={"key": "enter"},
                ))
                steps.append(PlanStep(
                    action="wait",
                    description="Wait for results",
                    params={"wait_seconds": 2.0},
                ))
                steps.append(PlanStep(
                    action="click",
                    description="Click first result",
                    params={"target": "first_result"},
                ))
            else:
                steps.append(PlanStep(
                    action="type_text",
                    description=f"Do: {sub_action}",
                    params={"text": sub_action},
                ))

        elif template == "open_url_in_browser":
            browser = g[0] if len(g) > 0 else "chrome"
            url = g[1] if len(g) > 1 else ""
            steps.append(PlanStep(
                action="launch_application",
                description=f"Open {browser}",
                params={"app_name": browser},
                expected_outcome={"app_name": browser},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for browser",
                params={"wait_seconds": 2.0},
            ))
            steps.append(PlanStep(
                action="open_url",
                description=f"Navigate to {url}",
                params={"url": url},
                expected_outcome={"url": url},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for page",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="observe",
                description="Verify page loaded",
            ))

        elif template == "search_in_browser":
            browser = g[0] if len(g) > 0 else "chrome"
            query = g[1] if len(g) > 1 else ""
            steps.append(PlanStep(
                action="launch_application",
                description=f"Open {browser}",
                params={"app_name": browser},
                expected_outcome={"app_name": browser},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for browser",
                params={"wait_seconds": 2.0},
            ))
            steps.append(PlanStep(
                action="open_url",
                description=f"Navigate to Google",
                params={"url": f"{SEARCH_PROVIDER}"},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for Google",
                params={"wait_seconds": 2.0},
            ))
            steps.append(PlanStep(
                action="click",
                description="Click search box",
                params={"target": "search"},
            ))
            steps.append(PlanStep(
                action="type_text",
                description=f"Type: {query}",
                params={"text": query},
            ))
            steps.append(PlanStep(
                action="press_key",
                description="Press Enter",
                params={"key": "enter"},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for results",
                params={"wait_seconds": 3.0},
            ))

        elif template == "launch_app":
            app = g[0] if g else ""
            steps.append(PlanStep(
                action="launch_application",
                description=f"Open {app}",
                params={"app_name": app},
                expected_outcome={"app_name": app},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for app",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="observe",
                description="Verify app loaded",
            ))

        elif template == "play_in_browser":
            browser = g[0] if len(g) > 0 else "chrome"
            target = g[1] if len(g) > 1 else ""
            steps.append(PlanStep(
                action="launch_application",
                description=f"Open {browser}",
                params={"app_name": browser},
            ))
            steps.append(PlanStep(
                action="wait", description="Wait for browser",
                params={"wait_seconds": 2.0},
            ))
            steps.append(PlanStep(
                action="open_url",
                description="Go to YouTube",
                params={"url": "https://www.youtube.com"},
            ))
            steps.append(PlanStep(
                action="wait", description="Wait for YouTube",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="click",
                description="Click search",
                params={"target": "Search"},
            ))
            steps.append(PlanStep(
                action="type_text",
                description=f"Search: {target}",
                params={"text": target},
            ))
            steps.append(PlanStep(
                action="press_key", description="Press Enter",
                params={"key": "enter"},
            ))
            steps.append(PlanStep(
                action="wait", description="Wait for results",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="click",
                description="Click first video",
                params={"target": "first_video"},
            ))

        elif template == "play_in_app":
            app = g[0] if len(g) > 0 else ""
            target = g[1] if len(g) > 1 else ""
            steps.append(PlanStep(
                action="launch_application",
                description=f"Open {app}",
                params={"app_name": app},
                expected_outcome={"app_name": app},
            ))
            steps.append(PlanStep(
                action="wait", description="Wait for app",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="observe", description="Observe app",
            ))
            steps.append(PlanStep(
                action="play",
                description=f"Play {target}",
                params={"target": target},
            ))

        elif template == "open_url":
            url = g[0] if g else ""
            steps.append(PlanStep(
                action="open_url",
                description=f"Navigate to {url}",
                params={"url": url},
                expected_outcome={"url": url},
            ))
            steps.append(PlanStep(
                action="wait", description="Wait for page",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="observe", description="Verify page loaded",
            ))

        elif template == "search_web":
            query = g[0] if g else ""
            steps.append(PlanStep(
                action="open_url",
                description=f"Search Google for: {query}",
                params={"url": f"{SEARCH_PROVIDER}/?q={query}"},
            ))
            steps.append(PlanStep(
                action="wait", description="Wait for results",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="observe", description="Verify results",
            ))

        elif template == "click_element":
            target = g[0] if g else ""
            steps.append(PlanStep(
                action="observe", description="Observe screen",
            ))
            steps.append(PlanStep(
                action="click",
                description=f"Click '{target}'",
                params={"target": target},
            ))

        elif template == "type_text":
            text = g[0] if g else ""
            steps.append(PlanStep(
                action="type_text",
                description=f"Type: {text}",
                params={"text": text},
            ))

        elif template == "close_app":
            app_name = g[0] if g else ""
            steps.append(PlanStep(
                action="close_application",
                description=f"Close {app_name}",
                params={"app_name": app_name},
            ))

        elif template == "play_in_spotify":
            target = g[0] if g else ""
            steps.append(PlanStep(
                action="launch_application",
                description="Open Spotify",
                params={"app_name": "spotify"},
                expected_outcome={"app_name": "spotify"},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for Spotify",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="play",
                description=f"Play '{target}' in Spotify",
                params={"target": target},
            ))

        elif template == "play_playlist_in_spotify":
            target = g[0] if g else ""
            steps.append(PlanStep(
                action="launch_application",
                description="Open Spotify",
                params={"app_name": "spotify"},
                expected_outcome={"app_name": "spotify"},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for Spotify",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="play",
                description=f"Play playlist '{target}' in Spotify",
                params={"target": target},
            ))

        elif template == "play_media":
            target = g[0] if g else ""
            steps.append(PlanStep(
                action="launch_application",
                description="Open Spotify",
                params={"app_name": "spotify"},
                expected_outcome={"app_name": "spotify"},
            ))
            steps.append(PlanStep(
                action="wait",
                description="Wait for Spotify",
                params={"wait_seconds": 3.0},
            ))
            steps.append(PlanStep(
                action="play",
                description=f"Play '{target}'",
                params={"target": target},
            ))

        elif template == "observe_screen":
            steps.append(PlanStep(
                action="observe",
                description="Observe current screen",
            ))

        else:
            # Generic single step
            steps.append(PlanStep(
                action="execute_goal",
                description=f"Execute: {' '.join(g)}",
                params={"goal": " ".join(g)},
            ))

        return steps

    def execute_plan(self, plan: Plan) -> Plan:
        self._world.update()
        if plan.steps:
            self._world.set_task(plan.goal)

        for i, step in enumerate(plan.steps):
            plan.current_step = i
            self._notify_step(step)

            if step.status == StepStatus.SKIPPED:
                continue

            # Built-in steps: wait and observe
            if step.action == "wait":
                wait_time = step.params.get("wait_seconds", 2.0)
                time.sleep(wait_time)
                step.status = StepStatus.VERIFIED
                step.result = "Waited %ss" % wait_time
                continue

            if step.action == "observe":
                state = self._world.update()
                step.status = StepStatus.VERIFIED
                step.result = "Observed: %s - %s" % (state.active_app, state.window_title)
                continue

            # Observe BEFORE acting
            pre_state = self._world.update()

            # Execute action
            step.status = StepStatus.EXECUTING
            if not self._action_executor:
                step.result = "No executor configured"
                step.status = StepStatus.FAILED
                plan.failed = True
                plan.failure_reason = "No action executor"
                break

            try:
                result = self._action_executor(step.action, step.params)
                step.result = result
                logger.info("Step %d executed: %s -> %s", i, step.description, result)
            except Exception as e:
                step.status = StepStatus.FAILED
                step.result = str(e)
                plan.failed = True
                plan.failure_reason = "Step %d failed: %s" % (i, e)
                logger.warning("Plan step %d failed: %s", i, e)
                break

            # Wait for app to settle
            settle_time = step.params.get("wait_seconds", 1.5)
            time.sleep(settle_time)

            # Observe AFTER acting
            post_state = self._world.update()

            # Verify
            verification = self._verifier.verify(step.action, step.expected_outcome)
            step.verification = verification

            # Log perception outcome
            self._log_perception(step, pre_state, verification)

            if verification.success:
                step.status = StepStatus.VERIFIED
                logger.info("Step %d verified: %s", i, verification.details)
            else:
                # Retry once
                logger.info("Step %d verification failed, retrying: %s", i, verification.details)
                try:
                    retry_result = self._action_executor(step.action, step.params)
                    time.sleep(settle_time)
                    verification = self._verifier.verify(step.action, step.expected_outcome)
                    step.verification = verification
                except Exception:
                    verification = None

                if verification and verification.success:
                    step.status = StepStatus.VERIFIED
                    step.result = "Retry succeeded: %s" % retry_result
                    # Log the retry success
                    retry_state = self._world.update()
                    self._log_perception(step, retry_state, verification)
                    logger.info("Step %d retry succeeded", i)
                else:
                    step.status = StepStatus.FAILED
                    step.result = "Failed after retry: %s" % (verification.details if verification else "no verification")
                    plan.failed = True
                    plan.failure_reason = "Step %d failed after retry" % i
                    logger.warning("Plan step %d failed after retry", i)
                    break

        plan.completed = not plan.failed
        self._world.set_task("")

        # Auto-learning: generalize successful plans into procedural skills
        if plan.completed and self._llm:
            try:
                self._auto_generalize(plan)
            except Exception as e:
                logger.debug("Auto-generalize failed: %s", e)

        return plan

    def plan_and_execute(self, goal: str) -> Plan:
        state = self._perceiver.observe()
        plan = self.create_plan(goal, state)
        logger.info("Plan:\n%s", plan.summary())
        return self.execute_plan(plan)

    def _notify_step(self, step: PlanStep):
        if self._on_step:
            try:
                self._on_step(step)
            except Exception:
                pass

    def _log_perception(self, step: PlanStep, state: DesktopState, verification: Optional[VerificationResult]):
        """Log a perception-action-verification outcome for the learning loop."""
        target = step.params.get("target", step.description)
        # Try to find the element in pre-state for bbox
        bbox = None
        for elem in state.ui_elements:
            if target.lower() in elem.text.lower():
                bbox = (elem.x, elem.y, elem.width, elem.height)
                break

        try:
            self._perception_log.log_outcome(
                app_name=state.active_app,
                element_text=target[:200],
                element_role="unknown",
                element_bbox=bbox,
                screenshot_path=state.screenshot_path,
                action_taken=step.action,
                action_params=step.params,
                success=verification.success if verification else False,
                verification_details=verification.details if verification else "",
                resolution=state.resolution,
            )
        except Exception as e:
            logger.debug("Failed to log perception outcome: %s", e)

    def _auto_generalize(self, plan: Plan) -> None:
        """Feed a successful plan into the generalization prompt and store as skill."""
        from moso_core.llm.models import LLMRequest

        steps_text = "\n".join(
            f"  {i+1}. [{s.action}] {s.description}"
            for i, s in enumerate(plan.steps)
            if s.status == StepStatus.VERIFIED
        )
        if not steps_text:
            return

        prompt = (
            f"Goal: {plan.goal.description}\n\n"
            f"Steps that worked:\n{steps_text}\n\n"
            "Generalize this into a reusable skill. Return ONLY valid JSON:\n"
            '{"task_name": "short name", "steps": [{"action":"...", "params":{...}}], '
            '"trigger_phrases": ["when user says..."], "app_category": "browser|text_editor|other"}'
        )

        response = self._llm.complete(LLMRequest(
            prompt=prompt,
            system_prompt="You are a skill generalizer for MOSO AI. Convert successful plans into reusable skills.",
            max_tokens=512,
            temperature=0.3,
        ))
        if not response.success:
            return

        try:
            skill = json.loads(response.text.strip())
            if not isinstance(skill, dict) or "task_name" not in skill:
                return
            # Store via memory if available
            if self._memory and hasattr(self._memory, "procedural"):
                self._memory.procedural.store(
                    task_name=skill["task_name"],
                    steps=json.dumps(skill.get("steps", [])),
                    app_category=skill.get("app_category", "other"),
                    app_name=plan.goal.description[:100],
                    trigger_phrases=json.dumps(skill.get("trigger_phrases", [])),
                    variables="[]",
                )
                logger.info("Auto-learned skill: %s", skill["task_name"])
        except (json.JSONDecodeError, KeyError):
            pass

    def get_context(self) -> str:
        return self._world.get_context_string()
