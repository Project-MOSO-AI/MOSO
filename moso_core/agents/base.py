from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from moso_core.inference.base import ModelBackend

logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.parameters.keys()),
                },
            },
        }


@dataclass
class AgentResult:
    output: str
    tool_calls: list[dict] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)


class Agent(ABC):
    def __init__(self, name: str, backend: ModelBackend, system_prompt: str):
        self.name = name
        self._backend = backend
        self._system_prompt = system_prompt
        self._tools: dict[str, ToolSpec] = {}

    @abstractmethod
    def run(self, task: str, **kwargs) -> AgentResult:
        ...

    def register_tool(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def register_tools(self, specs: list[ToolSpec]) -> None:
        for spec in specs:
            self.register_tool(spec)

    @property
    def tools(self) -> dict[str, ToolSpec]:
        return dict(self._tools)


class SimpleAgent(Agent):
    def __init__(self, name: str, backend: ModelBackend, system_prompt: Optional[str] = None):
        super().__init__(
            name=name,
            backend=backend,
            system_prompt=system_prompt
            or f"You are {name}, an autonomous AI agent. Decompose complex tasks into steps and use available tools to accomplish them.",
        )
        self._messages: list[dict] = [{"role": "system", "content": self._system_prompt}]
        self._max_steps = 10

    def run(self, task: str, **kwargs) -> AgentResult:
        self._messages.append({"role": "user", "content": task})
        tool_calls: list[dict] = []
        steps: list[str] = []
        step_count = 0

        while step_count < self._max_steps:
            response = self._backend.chat(self._messages, **kwargs)
            content = response.text.strip()

            self._messages.append({"role": "assistant", "content": content})
            steps.append(content)
            step_count += 1

            if self._tool_call_detected(content):
                parsed = self._parse_tool_call(content)
                if parsed:
                    tool_calls.append(parsed)
                    tool_result = self._execute_tool(parsed)
                    self._messages.append({
                        "role": "tool",
                        "content": json.dumps(tool_result),
                        "name": parsed.get("name", ""),
                    })
                    continue

            if self._task_complete(content):
                break

        return AgentResult(
            output=steps[-1] if steps else "",
            tool_calls=tool_calls,
            steps=steps,
        )

    def reset(self) -> None:
        self._messages = [{"role": "system", "content": self._system_prompt}]

    def _tool_call_detected(self, content: str) -> bool:
        return "TOOL_CALL:" in content or "```tool" in content

    def _parse_tool_call(self, content: str) -> Optional[dict]:
        import re
        match = re.search(r"TOOL_CALL:\s*(\w+)\s*\n(.*?)(?:\n|$)", content, re.DOTALL)
        if match:
            name = match.group(1).strip()
            try:
                args = json.loads(match.group(2).strip())
            except json.JSONDecodeError:
                args = {"input": match.group(2).strip()}
            return {"name": name, "arguments": args}
        return None

    def _execute_tool(self, call: dict) -> Any:
        name = call.get("name", "")
        args = call.get("arguments", {})
        spec = self._tools.get(name)
        if spec is None:
            return {"error": f"Unknown tool: {name}"}
        logger.info("Executing tool '%s' with args: %s", name, args)
        return {"status": "executed", "tool": name, "result": f"Tool {name} executed successfully."}

    @staticmethod
    def _task_complete(content: str) -> bool:
        markers = ["TASK_COMPLETE", "DONE", "finished.", "completed.", "Final Answer:"]
        return any(marker in content for marker in markers)
