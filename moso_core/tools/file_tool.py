from __future__ import annotations

import glob as glob_module
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from moso_core.tools.base import Tool
from moso_core.tools.models import ToolResult

logger = logging.getLogger(__name__)

SAFE_DIRS = [
    os.path.expanduser("~"),
]

if os.name == "nt":
    SAFE_DIRS.append(os.environ.get("USERPROFILE", ""))
    SAFE_DIRS.append(os.environ.get("TEMP", ""))
    SAFE_DIRS.append(os.environ.get("TMP", ""))
else:
    SAFE_DIRS.append("/home")
    SAFE_DIRS.append("/tmp")


class FileTool(Tool):
    name = "file_tool"
    description = "Find, read, create, move, delete, and list files and directories"
    category = "file"
    permission_level = "guest"
    requires_confirmation = False

    _permission_map = {
        "read_file": "guest",
        "list_directory": "guest",
        "find_files": "guest",
        "create_file": "trusted",
        "create_folder": "trusted",
        "move_file": "trusted",
        "delete_file": "owner",
    }

    _confirm_map = {
        "delete_file": True,
    }

    def get_permission_level(self, action: str) -> str:
        return self._permission_map.get(action, "guest")

    def validate(self, **kwargs) -> tuple[bool, str]:
        return True, ""

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "list_directory")
        method = getattr(self, action, None)
        if method is None:
            return ToolResult(False, self.name, action, error=f"Unknown file action: {action}")
        return method(**{k: v for k, v in kwargs.items() if k != "action"})

    def _safe_resolve(self, path: str) -> Optional[Path]:
        try:
            p = Path(path).resolve()
            for safe in SAFE_DIRS:
                safe_p = Path(safe).resolve()
                if not safe_p.exists():
                    continue
                try:
                    if safe_p in p.parents or p == safe_p or p.is_relative_to(safe_p):
                        return p
                except ValueError:
                    if safe_p in p.parents or p == safe_p:
                        return p
            return p
        except (OSError, RuntimeError, ValueError):
            return None

    def read_file(self, path: str) -> ToolResult:
        resolved = self._safe_resolve(path)
        if resolved is None:
            return ToolResult(False, self.name, "read_file", error=f"Invalid path: {path}")
        try:
            content = resolved.read_text(encoding="utf-8")
            return ToolResult(True, self.name, "read_file", result=content)
        except Exception as e:
            return ToolResult(False, self.name, "read_file", error=str(e))

    def create_file(self, path: str, content: str = "") -> ToolResult:
        resolved = self._safe_resolve(path)
        if resolved is None:
            return ToolResult(False, self.name, "create_file", error=f"Invalid path: {path}")
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return ToolResult(True, self.name, "create_file", result=f"Created {resolved}")
        except Exception as e:
            return ToolResult(False, self.name, "create_file", error=str(e))

    def create_folder(self, path: str) -> ToolResult:
        resolved = self._safe_resolve(path)
        if resolved is None:
            return ToolResult(False, self.name, "create_folder", error=f"Invalid path: {path}")
        try:
            resolved.mkdir(parents=True, exist_ok=True)
            return ToolResult(True, self.name, "create_folder", result=f"Created folder {resolved}")
        except Exception as e:
            return ToolResult(False, self.name, "create_folder", error=str(e))

    def delete_file(self, path: str) -> ToolResult:
        resolved = self._safe_resolve(path)
        if resolved is None:
            return ToolResult(False, self.name, "delete_file", error=f"Invalid path: {path}")
        try:
            if resolved.is_dir():
                shutil.rmtree(resolved)
            else:
                resolved.unlink()
            return ToolResult(True, self.name, "delete_file", result=f"Deleted {resolved}")
        except Exception as e:
            return ToolResult(False, self.name, "delete_file", error=str(e))

    def find_files(self, pattern: str, path: str = ".") -> ToolResult:
        try:
            resolved = Path(path).resolve()
            search_path = str(resolved / pattern)
            matches = glob_module.glob(search_path, recursive=True)
            return ToolResult(True, self.name, "find_files", result=matches[:100])
        except Exception as e:
            return ToolResult(False, self.name, "find_files", error=str(e))

    def list_directory(self, path: str = ".") -> ToolResult:
        try:
            resolved = Path(path).resolve()
            if not resolved.is_dir():
                return ToolResult(False, self.name, "list_directory", error=f"Not a directory: {path}")
            entries = []
            for entry in sorted(resolved.iterdir()):
                kind = "dir" if entry.is_dir() else "file"
                entries.append({"name": entry.name, "kind": kind})
            return ToolResult(True, self.name, "list_directory", result=entries)
        except Exception as e:
            return ToolResult(False, self.name, "list_directory", error=str(e))

    def move_file(self, source: str, dest: str) -> ToolResult:
        src_resolved = self._safe_resolve(source)
        dst_resolved = self._safe_resolve(dest)
        if src_resolved is None:
            return ToolResult(False, self.name, "move_file", error=f"Invalid source: {source}")
        if dst_resolved is None:
            return ToolResult(False, self.name, "move_file", error=f"Invalid dest: {dest}")
        try:
            dst_resolved.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_resolved), str(dst_resolved))
            return ToolResult(True, self.name, "move_file", result=f"Moved {source} -> {dest}")
        except Exception as e:
            return ToolResult(False, self.name, "move_file", error=str(e))
