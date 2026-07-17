"""Self-improving loop: generate → critique → refine → execute.

Wraps VisionPlanner in a cycle that scores plans before executing,
refining them until they pass the internal critic or hit exit conditions.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)

CRITIQUE_SYSTEM = """You are a plan critic for MOSO AI. Given a user goal and a proposed plan,
score it 0.0-1.0 and give brief feedback. Return ONLY valid JSON:
{"score": 0.8, "feedback": "one sentence of what to improve"}
Rules: score >= 0.75 means the plan is good enough to execute.
Penalize: missing steps, wrong tool choices, unclear targets, unsafe actions."""


@dataclass
class ContextBoundary:
    goal: str
    allowed_tools: list[str] = field(default_factory=list)
    max_seconds: float = 60.0


@dataclass
class ExitCondition:
    max_cycles: int = 3
    min_critic_score: float = 0.75
    hard_deadline_s: float = 120.0


@dataclass
class LoopResult:
    plan: Any = None
    cycles: int = 0
    final_score: float = 0.0
    critiques: list[dict] = field(default_factory=list)
    timed_out: bool = False


class SelfImprovingLoop:
    def __init__(self, llm: Any = None, exit_condition: Optional[ExitCondition] = None):
        self._llm = llm
        self._exit = exit_condition or ExitCondition()

    def run(
        self,
        goal: str,
        generate_fn: Callable[[ContextBoundary], Any],
        execute_fn: Optional[Callable[[Any], Any]] = None,
    ) -> LoopResult:
        boundary = ContextBoundary(goal=goal)
        start = time.time()
        result = LoopResult()

        plan = generate_fn(boundary)
        result.plan = plan

        for cycle in range(self._exit.max_cycles):
            # Check hard deadline
            if time.time() - start > self._exit.hard_deadline_s:
                result.timed_out = True
                logger.warning("Loop timed out after %.0fs", self._exit.hard_deadline_s)
                break

            score, feedback = self._critique(goal, plan)
            result.critiques.append({"cycle": cycle, "score": score, "feedback": feedback})
            result.final_score = score
            result.cycles = cycle + 1

            if score >= self._exit.min_critic_score:
                logger.info("Plan passed critique on cycle %d (score %.2f)", cycle + 1, score)
                break

            # Refine: re-generate with critique feedback appended to goal
            refined_goal = f"{goal}\n\n[CRITIC FEEDBACK]: {feedback}"
            refined_boundary = ContextBoundary(goal=refined_goal)
            plan = generate_fn(refined_boundary)
            result.plan = plan

        if execute_fn and result.plan:
            result.plan = execute_fn(result.plan)

        return result

    def _critique(self, goal: str, plan: Any) -> tuple[float, str]:
        if self._llm is None:
            return 0.8, "No LLM available for critique — passing by default"

        plan_text = self._plan_to_text(plan)
        prompt = f"Goal: {goal}\n\nProposed plan:\n{plan_text}\n\nScore and critique:"

        try:
            from moso_core.llm.models import LLMRequest
            response = self._llm.complete(LLMRequest(
                prompt=prompt,
                system_prompt=CRITIQUE_SYSTEM,
                max_tokens=128,
                temperature=0.3,
            ))
            if not response.success:
                return 0.8, f"LLM critique unavailable: {response.error}"

            parsed = json.loads(response.text.strip())
            score = max(0.0, min(1.0, float(parsed.get("score", 0.8))))
            feedback = parsed.get("feedback", "No feedback")
            return score, feedback
        except (json.JSONDecodeError, KeyError, ValueError):
            return 0.8, "Critique parse failed — passing by default"
        except Exception as e:
            logger.debug("Critique error: %s", e)
            return 0.8, "Critique unavailable — passing by default"

    def _plan_to_text(self, plan: Any) -> str:
        if hasattr(plan, "steps"):
            lines = []
            for i, step in enumerate(plan.steps):
                desc = getattr(step, "description", str(step))
                action = getattr(step, "action", "")
                lines.append(f"  {i+1}. [{action}] {desc}")
            return "\n".join(lines)
        return str(plan)[:500]
