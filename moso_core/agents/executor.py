from __future__ import annotations

import logging
import time
from typing import Any, Optional

from moso_core.agents.models import ExecutionSummary, Goal, GoalStatus, Plan, Task, TaskStatus
from moso_core.agents.verifier import Verifier
from moso_core.tools.models import ToolRequest, ToolResult

logger = logging.getLogger(__name__)

# ponytail: planner uses short names ("file", "app", "browser"), registry uses "_tool" suffix
_TOOL_NAME_MAP = {
    "file": "file_tool",
    "app": "app_tool",
    "browser": "browser_tool",
    "terminal": "terminal_tool",
}


class Executor:
    def __init__(self, tool_registry=None, identity=None, memory=None, resources=None, automation_engine=None):
        self._tool_registry = tool_registry
        self._identity = identity
        self._memory = memory
        self._resources = resources
        self._automation_engine = automation_engine
        self._verifier = Verifier()

    @property
    def verifier(self) -> Verifier:
        return self._verifier

    def execute(self, plan: Plan, requester: str = "owner") -> ExecutionSummary:
        goal = plan.goal
        goal.status = GoalStatus.RUNNING
        task_results = []
        all_succeeded = True
        completed_orders: set[int] = set()
        failed_orders: set[int] = set()

        for task in plan.tasks:
            if task.depends_on:
                skip_task = False
                for dep_order in task.depends_on:
                    if dep_order in failed_orders:
                        task.status = TaskStatus.SKIPPED
                        task.error = f"Dependency task {dep_order + 1} failed"
                        all_succeeded = False
                        task_results.append({
                            "task_id": task.task_id,
                            "title": task.title,
                            "tool_name": task.tool_name,
                            "status": TaskStatus.SKIPPED.value,
                            "result": None,
                            "error": task.error,
                        })
                        logger.warning("Task '%s' skipped: dependency task %d failed", task.title, dep_order + 1)
                        skip_task = True
                        break
                    if dep_order not in completed_orders:
                        task.status = TaskStatus.SKIPPED
                        task.error = f"Dependency task {dep_order + 1} not completed"
                        all_succeeded = False
                        task_results.append({
                            "task_id": task.task_id,
                            "title": task.title,
                            "tool_name": task.tool_name,
                            "status": TaskStatus.SKIPPED.value,
                            "result": None,
                            "error": task.error,
                        })
                        logger.warning("Task '%s' skipped: dependency task %d not completed", task.title, dep_order + 1)
                        skip_task = True
                        break
                if skip_task:
                    continue

            task.status = TaskStatus.RUNNING
            success = self._execute_with_retry(task, requester, task_results)
            if success:
                completed_orders.add(task.order)
            else:
                failed_orders.add(task.order)
                all_succeeded = False

        goal.status = GoalStatus.COMPLETED if all_succeeded else GoalStatus.FAILED
        goal.completed_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        return ExecutionSummary(
            goal=goal,
            task_results=task_results,
            overall_status=goal.status,
            completed_at=goal.completed_at or "",
        )

    def _execute_with_retry(
        self, task: Task, requester: str, task_results: list
    ) -> bool:
        attempts = 0
        max_attempts = max(task.max_retries, 1)
        last_error = None

        while attempts < max_attempts:
            if attempts > 0:
                task.retry_count = attempts
                logger.info("Retrying task '%s' (attempt %d/%d)", task.title, attempts + 1, max_attempts)

            result = self._execute_task(task, requester)
            if result is None:
                task.status = TaskStatus.SKIPPED
                task_results.append({
                    "task_id": task.task_id,
                    "title": task.title,
                    "tool_name": task.tool_name,
                    "status": TaskStatus.SKIPPED.value,
                    "result": None,
                    "error": "No tool_registry available",
                })
                return False

            task.result = str(result.result) if result.success else None
            task.error = result.error

            if not result.success:
                attempts += 1
                last_error = result.error
                if attempts < max_attempts:
                    continue
                task.status = TaskStatus.FAILED
                task_results.append(self._build_failed_result(task, result))
                logger.warning("Task '%s' failed after %d attempts: %s", task.title, max_attempts, last_error)
                return False

            if task.verification_method:
                verification = self._verifier.verify(task, result)
                if verification.success:
                    task.status = TaskStatus.COMPLETED
                    task_results.append(self._build_completed_result(task, result, str(verification)))
                    return True
                else:
                    attempts += 1
                    last_error = f"Verification failed: {verification}"
                    task.error = last_error
                    if attempts < max_attempts:
                        continue
                    task.status = TaskStatus.FAILED
                    task_results.append(self._build_verified_failed_result(task, str(verification)))
                    logger.warning("Task '%s' verification failed after %d attempts", task.title, max_attempts)
                    return False

            task.status = TaskStatus.COMPLETED
            task_results.append({
                "task_id": task.task_id,
                "title": task.title,
                "tool_name": task.tool_name,
                "status": TaskStatus.COMPLETED.value,
                "result": str(result.result) if result.result else None,
                "error": None,
            })
            return True

        return False

    def _build_completed_result(self, task: Task, result, verification: str) -> dict:
        return {
            "task_id": task.task_id,
            "title": task.title,
            "tool_name": task.tool_name,
            "status": TaskStatus.COMPLETED.value,
            "result": str(result.result) if result.result else None,
            "error": None,
            "verification": verification,
        }

    def _build_failed_result(self, task: Task, result) -> dict:
        return {
            "task_id": task.task_id,
            "title": task.title,
            "tool_name": task.tool_name,
            "status": TaskStatus.FAILED.value,
            "result": str(result.result) if result.result else None,
            "error": task.error,
        }

    def _build_verified_failed_result(self, task: Task, verification: str) -> dict:
        return {
            "task_id": task.task_id,
            "title": task.title,
            "tool_name": task.tool_name,
            "status": TaskStatus.FAILED.value,
            "result": str(task.result) if task.result else None,
            "error": task.error,
            "verification": verification,
        }

    def _execute_task(self, task: Task, requester: str):
        if task.tool_name == "computer_use":
            return self._execute_computer_use_task(task, requester)
        if self._tool_registry is None:
            logger.error("Cannot execute task: no tool_registry available")
            return None
        request = ToolRequest(
            tool_name=_TOOL_NAME_MAP.get(task.tool_name, task.tool_name),
            parameters=task.parameters,
            requester=requester,
        )
        return self._tool_registry.execute_tool(
            request=request,
            identity=self._identity,
            memory=self._memory,
            resources=self._resources,
        )

    def _execute_computer_use_task(self, task: Task, requester: str) -> ToolResult | None:
        if self._automation_engine is None:
            logger.error("Cannot execute computer_use task: no automation_engine available")
            return None
        params = task.parameters
        action = params.get("action", "")
        is_sequence = "actions" in params
        if is_sequence:
            sequence = params.get("actions", [])
            dry_run = params.get("dry_run", False)
            cu_results = self._automation_engine.execute_sequence(sequence, dry_run=dry_run)
            all_ok = all(r.success for r in cu_results)
            return ToolResult(
                success=all_ok,
                tool_name="computer_use",
                action=action or "execute_sequence",
                result=[r.to_dict() for r in cu_results] if all_ok else None,
                error=None if all_ok else next((r.error for r in cu_results if not r.success), "sequence failed"),
            )
        dry_run = params.get("dry_run", False)
        cu_result = self._automation_engine.execute_action(params, dry_run=dry_run)
        return ToolResult(
            success=cu_result.success,
            tool_name="computer_use",
            action=cu_result.action,
            result=cu_result.result,
            error=cu_result.error,
        )
