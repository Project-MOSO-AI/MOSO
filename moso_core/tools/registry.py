from __future__ import annotations

import logging
import time
from typing import Any, Optional

from moso_core.tools.audit import AuditLogger
from moso_core.tools.base import Tool
from moso_core.tools.models import ToolRequest, ToolResult

logger = logging.getLogger(__name__)


def _check_permission(required: str, identity: Any) -> tuple[bool, str]:
    if required == "guest":
        return True, ""
    if required == "trusted":
        if identity is None:
            return False, "Trusted-level permission requires identity engine"
        level = identity.get_identity_level()
        if level in ("owner", "likely_owner") or (hasattr(level, "value") and level.value in ("owner", "likely_owner")):
            return True, ""
        return False, "Trusted-level permission requires likely_owner or owner identity"
    if required == "owner":
        if identity is None:
            return False, "Owner-level permission requires identity engine"
        if not identity.is_owner():
            return False, "Owner-level permission requires full owner verification"
        return True, ""
    return False, f"Unknown permission level: {required}"


class ToolRegistry:
    def __init__(self, audit: Optional[AuditLogger] = None):
        self._tools: dict[str, Tool] = {}
        self._audit = audit or AuditLogger()

    def register_tool(self, tool: Tool) -> None:
        if tool.name in self._tools:
            logger.warning("Tool '%s' already registered, overwriting", tool.name)
        self._tools[tool.name] = tool
        logger.info("Registered tool: %s (%s)", tool.name, tool.category)

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> list[dict]:
        tools = []
        for tool in self._tools.values():
            if category and tool.category != category:
                continue
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "permission_level": tool.permission_level,
                "requires_confirmation": tool.requires_confirmation,
            })
        return tools

    def get_categories(self) -> list[str]:
        cats: set[str] = set()
        for tool in self._tools.values():
            cats.add(tool.category)
        return sorted(cats)

    def execute_tool(
        self,
        request: ToolRequest,
        identity: Any = None,
        memory: Any = None,
        resources: Any = None,
    ) -> ToolResult:
        tool = self.get_tool(request.tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                tool_name=request.tool_name,
                action="unknown",
                error=f"Unknown tool: {request.tool_name}",
            )

        action = request.parameters.get("action", "execute")
        params = {k: v for k, v in request.parameters.items() if k != "action"}

        valid, reason = tool.validate(**params)
        if not valid:
            return ToolResult(
                success=False,
                tool_name=tool.name,
                action=action,
                error=f"Validation failed: {reason}",
            )

        try:
            from moso_core.risk.manager import RiskManager as _RM
            _risk = _RM(resources=resources) if resources else _RM()
            allowed, report = _risk.check_and_block(tool.name, action, params)
            if not allowed:
                return ToolResult(
                    success=False,
                    tool_name=tool.name,
                    action=action,
                    error=f"Risk Engine blocked: {report.max_level.value} - {report.risk.recommendation}",
                )
        except ImportError:
            if tool.permission_level != "guest":
                return ToolResult(
                    success=False,
                    tool_name=tool.name,
                    action=action,
                    error="Risk engine unavailable — blocking non-guest tool",
                )
        except Exception as e:
            if tool.permission_level != "guest":
                logger.warning("Risk check failed (blocking): %s", e)
                return ToolResult(
                    success=False,
                    tool_name=tool.name,
                    action=action,
                    error=f"Risk check failed — blocking: {e}",
                )

        required_level = tool.get_permission_level(action)
        description = tool.describe_action(**params, _action_name=action)

        if request.dry_run:
            allowed, deny_reason = _check_permission(required_level, identity)
            if not allowed:
                result_msg = f"[DRY RUN] Requires '{required_level}' permission: {deny_reason}"
            else:
                result_msg = f"[DRY RUN] Would execute: {description}"
            return ToolResult(
                success=True,
                tool_name=tool.name,
                action=action,
                result=result_msg,
            )

        allowed, deny_reason = _check_permission(required_level, identity)
        if not allowed:
            return ToolResult(
                success=False,
                tool_name=tool.name,
                action=action,
                error=deny_reason,
            )

        start = time.perf_counter()
        try:
            result = tool.execute(**params, action=action)
        except Exception as e:
            elapsed = time.perf_counter() - start
            result = ToolResult(
                success=False,
                tool_name=tool.name,
                action=action,
                error=str(e),
                execution_time=elapsed,
            )

        target = params.get("path") or params.get("app_name") or params.get("command") or params.get("query") or params.get("url") or ""
        self._audit.log_tool_result(
            result=result,
            tool_name=tool.name,
            action=action,
            target=target,
            owner_id=request.requester,
        )

        if memory and result.success and hasattr(memory, "store_event"):
            try:
                tags = ["tool-execution", tool.name, tool.category, action]
                if target:
                    target_tag = target.lower().replace(" ", "_")[:30]
                    tags.append(target_tag)
                memory.store_event(
                    title=description,
                    description=str(result.result)[:500] if result.result else description,
                    tags=tags,
                    owner_id=request.requester,
                )
            except Exception as e:
                logger.warning("Failed to log tool event to memory: %s", e)

        return result

    @property
    def audit(self) -> AuditLogger:
        return self._audit
