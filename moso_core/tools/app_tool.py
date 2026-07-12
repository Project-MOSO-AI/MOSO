from __future__ import annotations

import glob
import json
import logging
import os
import subprocess
import sys
import time
from typing import Optional

import psutil

from moso_core.tools.base import Tool
from moso_core.tools.models import ToolResult

logger = logging.getLogger(__name__)

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus"}
MEDIA_DIRS = [
    os.path.join(os.path.expanduser("~"), "Videos"),
    os.path.join(os.path.expanduser("~"), "Music"),
    os.path.join(os.path.expanduser("~"), "Downloads"),
    os.path.join(os.path.expanduser("~"), "Desktop"),
    "D:\\",
    "E:\\",
]

MEDIA_PLAYERS = {
    "vlc": {"exe": "vlc", "flag": ""},
    "vlc player": {"exe": "vlc", "flag": ""},
    "windows media player": {"exe": "wmplayer", "flag": ""},
    "media player": {"exe": "wmplayer", "flag": ""},
    "windows media": {"exe": "wmplayer", "flag": ""},
    "spotify": {"exe": "spotify", "flag": ""},
    "itunes": {"exe": "itunes", "flag": ""},
    "potplayer": {"exe": "potplayermini64", "flag": ""},
    "potplayermini64": {"exe": "potplayermini64", "flag": ""},
    "mpv": {"exe": "mpv", "flag": ""},
    "media class classic": {"exe": "mplayerc", "flag": ""},
    "mplayerc": {"exe": "mplayerc", "flag": ""},
}

APP_ALIASES: dict[str, list[str]] = {
    "spotify": ["spotify", "spotify music", "spotify music player"],
    "vlc": ["vlc", "vlc player", "videolan", "vlc media player"],
    "chrome": ["chrome", "google chrome"],
    "firefox": ["firefox", "mozilla firefox", "mozilla"],
    "edge": ["edge", "microsoft edge"],
    "explorer": ["explorer", "file explorer", "windows explorer", "files"],
    "notepad": ["notepad", "notepad++", "notepadpp"],
    "calculator": ["calculator", "calc"],
    "paint": ["paint", "mspaint"],
    "word": ["word", "microsoft word", "ms word"],
    "excel": ["excel", "microsoft excel", "ms excel"],
    "powerpoint": ["powerpoint", "microsoft powerpoint", "ms powerpoint"],
    "teams": ["teams", "microsoft teams"],
    "discord": ["discord"],
    "whatsapp": ["whatsapp", "whatsapp desktop"],
    "zoom": ["zoom", "zoom meetings"],
    "obs": ["obs", "obs studio", "obsidian"],
    "terminal": ["terminal", "cmd", "powershell", "windows terminal", "wt"],
    "vscode": ["vscode", "visual studio code", "vs code"],
    "code": ["vscode", "visual studio code", "vs code"],
}


class _WinAppIndex:
    """Builds a lazy index of installed Windows applications."""

    def __init__(self):
        self._index: dict[str, dict] = {}
        self._built = False

    def _ensure_built(self):
        if self._built:
            return
        self._built = True
        t0 = time.perf_counter()
        self._scan_start_menu()
        self._scan_program_files()
        self._scan_store_apps()
        elapsed = time.perf_counter() - t0
        logger.info("App index built: %d apps in %.2fs", len(self._index), elapsed)

    def _add_app(self, canonical: str, entry: dict):
        if canonical not in self._index:
            self._index[canonical] = entry

    def _canonical(self, name: str) -> str:
        return name.lower().strip()

    def _scan_start_menu(self):
        start_dirs = []
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("PROGRAMDATA", "")
        if appdata:
            start_dirs.append(os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"))
        if programdata:
            start_dirs.append(os.path.join(programdata, r"Microsoft\Windows\Start Menu\Programs"))

        for start_dir in start_dirs:
            if not os.path.isdir(start_dir):
                continue
            for root, _dirs, files in os.walk(start_dir):
                for f in files:
                    if not f.lower().endswith(".lnk"):
                        continue
                    shortcut_path = os.path.join(root, f)
                    name = os.path.splitext(f)[0]
                    target = self._resolve_shortcut(shortcut_path)
                    if not target:
                        continue
                    canonical = self._canonical(name)
                    self._add_app(canonical, {
                        "name": name,
                        "exe": target,
                        "method": "shortcut",
                        "source": shortcut_path,
                    })

    def _resolve_shortcut(self, lnk_path: str) -> Optional[str]:
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(lnk_path)
            target = shortcut.Targetpath
            if target and os.path.isfile(target):
                return target
        except Exception:
            pass
        # Fallback: try to find exe near the shortcut name
        return None

    def _scan_program_files(self):
        program_dirs = []
        for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            val = os.environ.get(env_var, "")
            if val and os.path.isdir(val):
                program_dirs.append(val)
        appdata = os.environ.get("APPDATA", "")
        if appdata and os.path.isdir(appdata):
            program_dirs.append(appdata)

        for program_dir in program_dirs:
            try:
                entries = os.listdir(program_dir)
            except OSError:
                continue
            for entry_name in entries:
                entry_path = os.path.join(program_dir, entry_name)
                if not os.path.isdir(entry_path):
                    continue
                exe = self._find_exe_in_dir(entry_path, entry_name)
                if exe:
                    canonical = self._canonical(entry_name)
                    self._add_app(canonical, {
                        "name": entry_name,
                        "exe": exe,
                        "method": "program_files",
                        "source": entry_path,
                    })

    def _find_exe_in_dir(self, directory: str, app_name: str) -> Optional[str]:
        try:
            for f in os.listdir(directory):
                if f.lower().endswith(".exe"):
                    return os.path.join(directory, f)
        except OSError:
            pass
        # Check one level deeper (e.g., AppName/AppName.exe)
        sub = os.path.join(directory, app_name)
        if os.path.isdir(sub):
            try:
                for f in os.listdir(sub):
                    if f.lower().endswith(".exe"):
                        return os.path.join(sub, f)
            except OSError:
                pass
        return None

    def _scan_store_apps(self):
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-StartApps | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=15, creationflags=0x08000000
            )
            if result.returncode != 0:
                return
            apps = json.loads(result.stdout)
            if isinstance(apps, dict):
                apps = [apps]
            for app in apps:
                name = app.get("Name", "")
                app_id = app.get("AppID", "")
                if not name or not app_id:
                    continue
                canonical = self._canonical(name)
                self._add_app(canonical, {
                    "name": name,
                    "app_id": app_id,
                    "exe": None,
                    "method": "store",
                    "source": "Get-StartApps",
                })
        except Exception as e:
            logger.debug("Store app scan failed: %s", e)

    def lookup(self, query: str) -> Optional[dict]:
        self._ensure_built()
        canonical = self._canonical(query)

        # 1. Direct key match
        if canonical in self._index:
            return self._index[canonical]

        # 2. Alias match — find the canonical app name, then find best entry
        alias_target = None
        for key, aliases in APP_ALIASES.items():
            if canonical in aliases or query.lower() in aliases:
                alias_target = key
                break

        if alias_target:
            # Find best entry whose name matches the alias target or any of its aliases
            best = None
            aliases_for_target = APP_ALIASES.get(alias_target, [])
            for entry in self._index.values():
                entry_canonical = self._canonical(entry["name"])
                if alias_target == entry_canonical:
                    return entry  # Exact name match
                # Check if any alias matches the entry name
                for alias in aliases_for_target:
                    if alias == entry_canonical:
                        return entry
                    if alias in entry_canonical and entry_canonical.startswith(alias):
                        if best is None or len(entry_canonical) < len(self._canonical(best["name"])):
                            best = entry
                # Also check substring containment
                if alias_target in entry_canonical:
                    if best is None or len(entry_canonical) < len(self._canonical(best["name"])):
                        best = entry
            if best:
                return best

        # 3. Substring match — prefer shortest name containing the query
        best = None
        for entry in self._index.values():
            entry_canonical = self._canonical(entry["name"])
            if canonical in entry_canonical:
                if best is None or len(entry_canonical) < len(self._canonical(best["name"])):
                    best = entry
        if best:
            return best

        # 4. Reverse substring — query contains an index key
        for app_key, entry in self._index.items():
            if app_key in canonical:
                return entry

        return None

    def list_apps(self) -> list[str]:
        self._ensure_built()
        return sorted(self._index.keys())


# ponytail: module-level singleton, rebuilt once per process lifetime
_app_index = _WinAppIndex()


class AppTool(Tool):
    name = "app_tool"
    description = "Launch, close, and list installed Windows applications"
    category = "app"
    permission_level = "guest"
    requires_confirmation = False

    _permission_map = {
        "launch_application": "trusted",
        "play_media": "trusted",
        "list_running_applications": "guest",
        "close_application": "owner",
    }

    def get_permission_level(self, action: str) -> str:
        return self._permission_map.get(action, "guest")

    def validate(self, **kwargs) -> tuple[bool, str]:
        return True, ""

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "list_running_applications")
        method = getattr(self, action, None)
        if method is None:
            return ToolResult(False, self.name, action, error=f"Unknown app action: {action}")
        return method(**{k: v for k, v in kwargs.items() if k != "action"})

    def launch_application(self, app_name: str, args: Optional[list[str]] = None) -> ToolResult:
        log = {
            "requested": app_name,
            "matched_alias": "",
            "launch_method": "",
            "executable": "",
            "exit_code": None,
            "result": "",
        }

        if os.name != "nt":
            return self._launch_non_windows(app_name, args)

        entry = _app_index.lookup(app_name)
        if not entry:
            log["result"] = "NOT_FOUND"
            logger.warning("App launch: %s | no match in index", app_name)
            return ToolResult(False, self.name, "launch_application",
                              error=f"Could not find '{app_name}' installed on this system.",
                              result=log)

        log["matched_alias"] = entry["name"]
        log["launch_method"] = entry["method"]

        try:
            if entry.get("app_id"):
                log["executable"] = entry["app_id"]
                cmd = ["explorer.exe", f"shell:AppsFolder\\{entry['app_id']}"]
            elif entry.get("exe"):
                log["executable"] = entry["exe"]
                cmd = [entry["exe"]]
            else:
                log["result"] = "NO_EXE"
                return ToolResult(False, self.name, "launch_application",
                                  error=f"Found '{entry['name']}' but no executable path.",
                                  result=log)

            if args:
                cmd.extend(args)

            logger.info("App launch: %s | alias=%s | method=%s | exe=%s",
                        app_name, entry["name"], entry["method"], log["executable"])

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            time.sleep(1.0)

            # Store apps: explorer.exe exits immediately, app runs separately
            if entry.get("app_id"):
                running = self._verify_store_app(entry)
                if running:
                    log["result"] = "LAUNCHED"
                    logger.info("App launch: %s | store app verified", app_name)
                    return ToolResult(True, self.name, "launch_application", result=log)
                log["result"] = "LAUNCHED_UNVERIFIED"
                return ToolResult(True, self.name, "launch_application", result=log)

            # Desktop apps: check exit code and process
            if proc.poll() is not None:
                exit_code = proc.returncode
                if exit_code != 0:
                    # Some launchers exit immediately with non-zero codes (like Opera GX).
                    # Only fail if the app isn't actually running.
                    if not self._verify_running(entry):
                        log["exit_code"] = exit_code
                        log["result"] = f"FAILED(exit={exit_code})"
                        logger.warning("App launch: %s | exited immediately with code %d", app_name, exit_code)
                        return ToolResult(False, self.name, "launch_application",
                                          error=f"Process for '{entry['name']}' exited immediately (code {exit_code}).",
                                          result=log)

            running = self._verify_running(entry)
            if running:
                log["result"] = "LAUNCHED"
                logger.info("App launch: %s | verified running", app_name)
                return ToolResult(True, self.name, "launch_application", result=log)
            else:
                log["result"] = "LAUNCHED_UNVERIFIED"
                logger.info("App launch: %s | started but could not verify process", app_name)
                return ToolResult(True, self.name, "launch_application", result=log)

        except Exception as e:
            log["result"] = f"ERROR: {e}"
            logger.error("App launch: %s | exception: %s", app_name, e)
            return ToolResult(False, self.name, "launch_application",
                              error=str(e), result=log)

    def _verify_running(self, entry: dict) -> bool:
        exe_name = os.path.basename(entry.get("exe", "")) if entry.get("exe") else ""
        if not exe_name:
            return True  # Store apps, can't easily verify
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == exe_name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def _verify_store_app(self, entry: dict) -> bool:
        app_id = entry.get("app_id", "")
        if not app_id:
            return True
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-Process | Where-Object {{$_.Path -like '*{app_id.split('!')[0]}*'}} | Select-Object -First 1 -ExpandProperty Name"],
                capture_output=True, text=True, timeout=10, creationflags=0x08000000
            )
            return bool(result.stdout.strip())
        except Exception:
            return True  # Assume success if we can't check

    def _launch_non_windows(self, app_name: str, args: Optional[list[str]] = None) -> ToolResult:
        try:
            cmd: list[str] = []
            if sys.platform == "darwin":
                cmd = ["open", "-a", app_name]
            else:
                import shutil
                binary = shutil.which(app_name)
                cmd = [binary] if binary else ["xdg-open", app_name]
            if args:
                cmd.extend(args)
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(True, self.name, "launch_application", result=f"Launched {app_name}")
        except Exception as e:
            return ToolResult(False, self.name, "launch_application", error=str(e))

    def play_media(self, media_type: str = "video", player: str = "") -> ToolResult:
        try:
            exts = VIDEO_EXTS if media_type == "video" else AUDIO_EXTS
            found = []
            search_dirs = [d for d in MEDIA_DIRS if os.path.isdir(d)]
            for search_dir in search_dirs:
                for ext in exts:
                    pattern = os.path.join(search_dir, "**", f"*{ext}")
                    for match in glob.iglob(pattern, recursive=False):
                        found.append(match)
                        if len(found) >= 50:
                            break
                if len(found) >= 50:
                    break

            if not found:
                return ToolResult(False, self.name, "play_media",
                                  error=f"No {media_type} files found in common directories")

            file_path = found[0]
            file_name = os.path.basename(file_path)

            player_key = player.lower().strip() if player else ""
            player_info = MEDIA_PLAYERS.get(player_key)

            if player_key == "spotify" and media_type == "audio":
                return self.launch_application("spotify", args=[file_path])
            exe = player_info["exe"] if player_info else ("vlc" if media_type == "video" else "wmplayer")

            if os.name == "nt":
                cmd = ["cmd", "/c", "start", "", exe, file_path]
            else:
                cmd = [exe, file_path]

            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=os.name == "nt")
            return ToolResult(True, self.name, "play_media",
                              result=f"Playing {file_name} in {exe}")
        except Exception as e:
            return ToolResult(False, self.name, "play_media", error=str(e))

    def close_application(self, app_name: str) -> ToolResult:
        try:
            closed = []
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if proc.info["name"] and app_name.lower() in proc.info["name"].lower():
                        proc.terminate()
                        closed.append(proc.info["name"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if closed:
                return ToolResult(True, self.name, "close_application",
                                  result=f"Closed: {', '.join(set(closed))}")
            return ToolResult(False, self.name, "close_application",
                              error=f"No running process found matching '{app_name}'")
        except Exception as e:
            return ToolResult(False, self.name, "close_application", error=str(e))

    def list_running_applications(self) -> ToolResult:
        try:
            apps = []
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if proc.info["name"]:
                        apps.append({"pid": proc.info["pid"], "name": proc.info["name"]})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            apps.sort(key=lambda x: x["name"].lower())
            return ToolResult(True, self.name, "list_running_applications", result=apps[:200])
        except Exception as e:
            return ToolResult(False, self.name, "list_running_applications", error=str(e))
