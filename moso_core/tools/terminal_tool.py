from __future__ import annotations

import logging
import os
import subprocess
import sys

from moso_core.tools.base import Tool
from moso_core.tools.models import ToolResult

logger = logging.getLogger(__name__)

MAX_OUTPUT_LENGTH = 10240
DEFAULT_TIMEOUT = 30


class TerminalTool(Tool):
    name = "terminal_tool"
    description = "Execute terminal commands with timeout and output capture"
    category = "terminal"
    permission_level = "owner"
    requires_confirmation = True

    def validate(self, **kwargs) -> tuple[bool, str]:
        command = kwargs.get("command", "")
        if not command or not command.strip():
            return False, "Command cannot be empty"
        return True, ""

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "execute_command")
        method = getattr(self, action, None)
        if method is None:
            return ToolResult(False, self.name, action, error=f"Unknown terminal action: {action}")
        return method(**{k: v for k, v in kwargs.items() if k != "action"})

    def execute_command(self, command: str, timeout: int = DEFAULT_TIMEOUT) -> ToolResult:
        forbidden = ["&", "|", ";", "$", "`", "(", ")", "{", "}", "<", ">", "\n"]
        for ch in forbidden:
            if ch in command:
                return ToolResult(False, self.name, "execute_command",
                                  error=f"Command contains forbidden character: {ch!r}")

        import shlex
        try:
            cmd_list = shlex.split(command, posix=(os.name != "nt"))
        except ValueError as e:
            return ToolResult(False, self.name, "execute_command",
                              error=f"Invalid command syntax: {e}")

        if not cmd_list:
            return ToolResult(False, self.name, "execute_command",
                              error="Empty command after parsing")

        try:
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            stdout = result.stdout[:MAX_OUTPUT_LENGTH] if result.stdout else ""
            stderr = result.stderr[:MAX_OUTPUT_LENGTH] if result.stderr else ""

            output = {"exit_code": result.returncode, "stdout": stdout, "stderr": stderr}

            if result.returncode == 0:
                return ToolResult(True, self.name, "execute_command", result=output)
            return ToolResult(True, self.name, "execute_command", result=output,
                              error=f"Exit code {result.returncode}")

        except subprocess.TimeoutExpired:
            return ToolResult(False, self.name, "execute_command",
                              error=f"Command timed out after {timeout}s")
        except FileNotFoundError as e:
            return ToolResult(False, self.name, "execute_command",
                              error=f"Command not found: {e}")
        except Exception as e:
            return ToolResult(False, self.name, "execute_command", error=str(e))
