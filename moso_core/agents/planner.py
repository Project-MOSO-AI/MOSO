from __future__ import annotations

import logging
import re
from typing import Optional

from moso_core.agents.models import Goal, Plan, Task

logger = logging.getLogger(__name__)

TEMPLATE_SCORE_THRESHOLD = 2


class PlanTemplate:
    def __init__(self, name: str, keywords: list[str], description: str):
        self.name = name
        self.keywords = [k.lower() for k in keywords]
        self.description = description

    def score(self, goal_text: str) -> int:
        lower = goal_text.lower()
        return sum(1 for kw in self.keywords if kw in lower)

    def generate(self, goal: Goal) -> list[Task]:
        raise NotImplementedError


class PythonProjectTemplate(PlanTemplate):
    def __init__(self):
        super().__init__(
            name="python_project",
            keywords=["python", "project", "script", "module", "package", "create", "app"],
            description="Create a Python project structure",
        )

    def generate(self, goal: Goal) -> list[Task]:
        match = re.search(r"(?:python|project|app|script)\s+(\w+)", goal.description, re.IGNORECASE)
        name = match.group(1) if match else "new_project"
        return [
            Task(goal_id=0, title="Create project folder", description=f"Create {name} directory", tool_name="file", parameters={"action": "create_folder", "path": name}, order=0, verification_method="folder_exists", verification_target=name),
            Task(goal_id=0, title="Create __init__.py", description="Create package init", tool_name="file", parameters={"action": "create_file", "path": f"{name}/__init__.py"}, order=1, verification_method="file_exists", verification_target=f"{name}/__init__.py"),
            Task(goal_id=0, title="Create main.py", description="Create main entry point", tool_name="file", parameters={"action": "create_file", "path": f"{name}/main.py", "content": "def main():\n    print('Hello from MOSO')\n\nif __name__ == '__main__':\n    main()\n"}, order=2, verification_method="file_exists", verification_target=f"{name}/main.py"),
        ]


class CreateFolderTemplate(PlanTemplate):
    def __init__(self):
        super().__init__(
            name="create_folder",
            keywords=["folder", "directory", "mkdir", "create folder", "new folder", "make directory", "create"],
            description="Create a folder",
        )

    def generate(self, goal: Goal) -> list[Task]:
        match = re.search(r"(?:folder|directory)\s+([\w/\\\-\.]+)", goal.description, re.IGNORECASE)
        path = match.group(1) if match else "new_folder"
        return [
            Task(goal_id=0, title="Create folder", description=f"Create {path}", tool_name="file", parameters={"action": "create_folder", "path": path}, order=0, verification_method="folder_exists", verification_target=path),
        ]


class OpenAppTemplate(PlanTemplate):
    def __init__(self):
        super().__init__(
            name="open_app",
            keywords=["open", "launch", "start", "run", "app", "application", "program", "chrome", "browser", "editor", "notepad"],
            description="Open or launch an application",
        )

    def generate(self, goal: Goal) -> list[Task]:
        match = re.search(r"(?:open|launch|start|run)\s+([\w\s]+)", goal.description, re.IGNORECASE)
        app = match.group(1).strip() if match else "notepad"
        return [
            Task(goal_id=0, title="Launch application", description=f"Launch {app}", tool_name="app", parameters={"action": "open", "app_name": app}, order=0, verification_method="process_running", verification_target=app),
        ]


class SearchWebTemplate(PlanTemplate):
    def __init__(self):
        super().__init__(
            name="search_web",
            keywords=["search", "find", "look up", "google", "browse", "web", "internet", "website"],
            description="Search the web or browse a URL",
        )

    def generate(self, goal: Goal) -> list[Task]:
        url_match = re.search(r"https?://\S+", goal.description)
        if url_match:
            url = url_match.group(0)
            return [
                Task(goal_id=0, title="Browse URL", description=f"Open {url}", tool_name="browser", parameters={"action": "browse", "url": url}, order=0, verification_method="content_not_empty", verification_target=""),
            ]
        search_match = re.search(r"(?:search|find|look up)\s+(.+?)(?:\.|$)", goal.description, re.IGNORECASE)
        query = search_match.group(1).strip() if search_match else goal.description
        return [
            Task(goal_id=0, title="Search web", description=f"Search for {query}", tool_name="browser", parameters={"action": "search_web", "query": query}, order=0, verification_method="content_not_empty", verification_target=""),
        ]


class ReadFileTemplate(PlanTemplate):
    def __init__(self):
        super().__init__(
            name="read_file",
            keywords=["read", "open file", "view", "show", "display", "cat", "print", "file", "content"],
            description="Read a file",
        )

    def generate(self, goal: Goal) -> list[Task]:
        match = re.search(r"(?:read|open|view|show|display|cat)\s+([\w/\\\-\.]+)", goal.description, re.IGNORECASE)
        path = match.group(1) if match else "README.md"
        return [
            Task(goal_id=0, title="Read file", description=f"Read {path}", tool_name="file", parameters={"action": "read_file", "path": path}, order=0, verification_method="content_not_empty", verification_target=""),
        ]


class CreateFileTemplate(PlanTemplate):
    def __init__(self):
        super().__init__(
            name="create_file",
            keywords=["create", "make", "write", "add", "file", "text", "document"],
            description="Create a file",
        )

    def generate(self, goal: Goal) -> list[Task]:
        match = re.search(r"(?:create|make|write|add)\s+(?:a\s+)?file\s+([\w/\\\-\.]+)", goal.description, re.IGNORECASE)
        path = match.group(1) if match else "new_file.txt"
        content_match = re.search(r"containing\s+(.+?)(?:\.|$)", goal.description, re.IGNORECASE)
        content = content_match.group(1) if content_match else ""
        return [
            Task(goal_id=0, title="Create file", description=f"Create {path}", tool_name="file", parameters={"action": "create_file", "path": path, "content": content}, order=0, verification_method="file_exists", verification_target=path),
        ]


class DesktopAutomationTemplate(PlanTemplate):
    def __init__(self):
        super().__init__(
            name="desktop_automation",
            keywords=["click", "mouse", "type", "screenshot", "capture", "screen", "press", "key", "scroll", "focus", "window", "desktop", "switch to", "move"],
            description="Perform desktop automation actions via Computer Use",
        )

    def generate(self, goal: Goal) -> list[Task]:
        desc = goal.description.lower()

        if "screenshot" in desc or ("capture" in desc and "screen" in desc):
            return [
                Task(
                    goal_id=0, title="Take screenshot", description="Capture the screen",
                    tool_name="computer_use",
                    parameters={"action": "capture_screen"},
                    order=0, verification_method="content_not_empty",
                )
            ]

        if "type" in desc:
            text_match = re.search(r"type\s+(.+?)(?:\.|$)", desc, re.IGNORECASE)
            text = text_match.group(1).strip() if text_match else "hello"
            return [
                Task(
                    goal_id=0, title="Type text", description=f"Type: {text}",
                    tool_name="computer_use",
                    parameters={"action": "type_text", "text": text},
                    order=0,
                )
            ]

        if "press" in desc or ("hit" in desc and "key" in desc):
            key_match = re.search(r"(?:press|hit)\s+(?:the\s+)?(?:key\s+)?(.+?)(?:\.|$)", desc, re.IGNORECASE)
            key = key_match.group(1).strip() if key_match else "enter"
            return [
                Task(
                    goal_id=0, title="Press key", description=f"Press {key}",
                    tool_name="computer_use",
                    parameters={"action": "press", "key": key},
                    order=0,
                )
            ]

        if "scroll" in desc:
            direction = "down" if "down" in desc else ("up" if "up" in desc else "down")
            amount = 3 if direction == "down" else -3
            return [
                Task(
                    goal_id=0, title="Scroll", description=f"Scroll {direction}",
                    tool_name="computer_use",
                    parameters={"action": "scroll", "amount": amount},
                    order=0,
                )
            ]

        if "move" in desc and "mouse" in desc:
            coord_match = re.search(r"(?:to\s+)?\(?(\d+)\s*,?\s*(\d+)\)?", desc)
            x = int(coord_match.group(1)) if coord_match else 500
            y = int(coord_match.group(2)) if coord_match else 500
            return [
                Task(
                    goal_id=0, title="Move mouse", description=f"Move to ({x}, {y})",
                    tool_name="computer_use",
                    parameters={"action": "move_to", "x": x, "y": y},
                    order=0,
                )
            ]

        if "click" in desc:
            coord_match = re.search(r"(?:at\s+)?\(?(\d+)\s*,?\s*(\d+)\)?", desc)
            x = int(coord_match.group(1)) if coord_match else None
            y = int(coord_match.group(2)) if coord_match else None
            params = {"action": "click"}
            if x is not None and y is not None:
                params["x"] = x
                params["y"] = y
            return [
                Task(
                    goal_id=0, title="Click", description=f"Click at ({x}, {y})" if x else "Click",
                    tool_name="computer_use",
                    parameters=params,
                    order=0,
                )
            ]

        if "focus" in desc or ("switch" in desc and "window" in desc):
            title_pattern = r"(?:focus|switch to)\s+(.+?)(?:\.|$)"
            title_match = re.search(title_pattern, desc, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "untitled"
            return [
                Task(
                    goal_id=0, title="Focus window", description=f"Focus: {title}",
                    tool_name="computer_use",
                    parameters={"action": "focus_window", "window_title": title},
                    order=0,
                )
            ]

        return [
            Task(
                goal_id=0, title="Execute desktop action", description=desc,
                tool_name="computer_use",
                parameters={"action": desc.split()[0] if desc.split() else "move_to"},
                order=0,
            )
        ]


class Planner:
    def __init__(self):
        self._templates: list[PlanTemplate] = [
            PythonProjectTemplate(),
            CreateFolderTemplate(),
            OpenAppTemplate(),
            SearchWebTemplate(),
            ReadFileTemplate(),
            CreateFileTemplate(),
            DesktopAutomationTemplate(),
        ]

    def create_plan(self, description: str, owner_id: str = "default") -> Plan:
        goal = Goal(description=description, owner_id=owner_id)
        best_template: Optional[PlanTemplate] = None
        best_score = 0
        for template in self._templates:
            score = template.score(goal.description)
            logger.info("Template '%s' scored %d", template.name, score)
            if score > best_score:
                best_score = score
                best_template = template
        if best_template and best_score >= TEMPLATE_SCORE_THRESHOLD:
            tasks = best_template.generate(goal)
            logger.info("Matched template '%s' with score %d", best_template.name, best_score)
        else:
            tasks = [
                Task(goal_id=0, title="Execute command", description=f"Run: {description}", tool_name="terminal", parameters={"action": "execute", "command": self._to_shell_command(description)}, order=0, verification_method="exit_code_zero", verification_target=""),
            ]
            logger.info("No template matched, using terminal fallback")
        return Plan(goal=goal, tasks=tasks, estimated_steps=len(tasks))

    def _to_shell_command(self, description: str) -> str:
        if "list" in description.lower() and ("file" in description.lower() or "directory" in description.lower() or "folder" in description.lower()):
            return "ls -la"
        if "disk" in description.lower() or "space" in description.lower() or "storage" in description.lower():
            return "df -h"
        if "memory" in description.lower() or "ram" in description.lower():
            return "free -h"
        if "process" in description.lower():
            return "ps aux"
        return description.strip()
