"""Download manager — fetch model files with progress tracking, ETA, and integrity verification."""
from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import urllib.request
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False


class DownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadTask:
    url: str
    dest_path: str
    filename: str = ""
    expected_sha256: str = ""
    expected_size: int = 0
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed_bps: float = 0.0
    eta_seconds: float = 0.0
    error: str = ""
    start_time: float = 0.0
    end_time: float = 0.0

    def __post_init__(self):
        if not self.filename:
            self.filename = os.path.basename(self.dest_path)

    @property
    def elapsed(self) -> float:
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "dest": self.dest_path,
            "filename": self.filename,
            "status": self.status.value,
            "progress": round(self.progress, 1),
            "downloaded_mb": round(self.downloaded_bytes / (1024 * 1024), 1),
            "total_mb": round(self.total_bytes / (1024 * 1024), 1),
            "speed_mbps": round(self.speed_bps / (1024 * 1024), 2),
            "eta_seconds": round(self.eta_seconds),
            "error": self.error,
        }


class DownloadManager:
    def __init__(self, max_concurrent: int = 2):
        self._max_concurrent = max_concurrent
        self._tasks: list[DownloadTask] = []
        self._callbacks: list[Callable[[DownloadTask], None]] = []
        self._cancelled = False

    def add_callback(self, callback: Callable[[DownloadTask], None]):
        self._callbacks.append(callback)

    def _notify(self, task: DownloadTask):
        for cb in self._callbacks:
            try:
                cb(task)
            except Exception:
                pass

    def download(
        self,
        url: str,
        dest_path: str,
        expected_sha256: str = "",
        expected_size: int = 0,
    ) -> DownloadTask:
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        task = DownloadTask(
            url=url, dest_path=dest_path,
            expected_sha256=expected_sha256, expected_size=expected_size,
        )
        self._tasks.append(task)
        self._do_download(task)
        return task

    def _do_download(self, task: DownloadTask):
        task.status = DownloadStatus.DOWNLOADING
        task.start_time = time.time()
        self._notify(task)

        # Check for partial download (resume support)
        initial_size = 0
        if os.path.isfile(task.dest_path) and task.expected_size > 0:
            initial_size = os.path.getsize(task.dest_path)
            if initial_size >= task.expected_size:
                task.downloaded_bytes = initial_size
                task.total_bytes = task.expected_size
                task.progress = 100.0
                task.status = DownloadStatus.VERIFYING
                self._notify(task)
                if self._verify(task):
                    task.status = DownloadStatus.COMPLETE
                    task.end_time = time.time()
                    self._notify(task)
                    return
                initial_size = 0

        headers = {}
        if initial_size > 0 and task.expected_size > 0:
            headers["Range"] = f"bytes={initial_size}-"

        try:
            req = urllib.request.Request(task.url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                if task.total_bytes == 0:
                    content_length = resp.headers.get("Content-Length")
                    if content_length:
                        task.total_bytes = int(content_length) + initial_size
                    elif task.expected_size > 0:
                        task.total_bytes = task.expected_size

                mode = "ab" if initial_size > 0 and resp.status == 206 else "wb"
                if mode == "wb":
                    task.downloaded_bytes = 0

                sha256 = hashlib.sha256() if task.expected_sha256 else None
                speed_samples = []
                last_report = time.time()

                with open(task.dest_path, mode) as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        task.downloaded_bytes += len(chunk)
                        if sha256:
                            sha256.update(chunk)

                        now = time.time()
                        dt = now - last_report
                        if dt > 0.5:
                            speed_samples.append(task.downloaded_bytes / max(now - task.start_time, 0.01))
                            if len(speed_samples) > 5:
                                speed_samples.pop(0)
                            task.speed_bps = sum(speed_samples) / len(speed_samples)
                            if task.total_bytes > 0:
                                task.progress = min(100.0, task.downloaded_bytes * 100 / task.total_bytes)
                                remaining = task.total_bytes - task.downloaded_bytes
                                task.eta_seconds = remaining / max(task.speed_bps, 1)
                            self._notify(task)
                            last_report = now

                if sha256:
                    task.progress = 100.0
                    task.total_bytes = task.downloaded_bytes
                    self._notify(task)

        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error = str(e)
            task.end_time = time.time()
            self._notify(task)
            logger.error("Download failed %s: %s", task.filename, e)
            return

        task.status = DownloadStatus.VERIFYING
        self._notify(task)

        if task.expected_sha256:
            if not self._verify(task):
                task.status = DownloadStatus.FAILED
                task.error = "SHA256 mismatch"
                task.end_time = time.time()
                self._notify(task)
                return

        task.status = DownloadStatus.COMPLETE
        task.progress = 100.0
        task.end_time = time.time()
        self._notify(task)
        logger.info("Downloaded %s (%.1f MB in %.1fs)",
                     task.filename, task.downloaded_bytes / (1024 * 1024), task.elapsed)

    def _verify(self, task: DownloadTask) -> bool:
        if not task.expected_sha256:
            return True
        try:
            sha256 = hashlib.sha256()
            with open(task.dest_path, "rb") as f:
                while chunk := f.read(65536):
                    sha256.update(chunk)
            actual = sha256.hexdigest()
            if actual.lower() == task.expected_sha256.lower():
                return True
            logger.warning("SHA256 mismatch for %s: expected %s, got %s",
                           task.filename, task.expected_sha256[:16], actual[:16])
            return False
        except Exception as e:
            logger.error("Verification failed for %s: %s", task.filename, e)
            return False

    def cancel_all(self):
        self._cancelled = True

    @property
    def active_tasks(self) -> list[DownloadTask]:
        return [t for t in self._tasks if t.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING)]

    @property
    def completed_tasks(self) -> list[DownloadTask]:
        return [t for t in self._tasks if t.status == DownloadStatus.COMPLETE]

    @property
    def failed_tasks(self) -> list[DownloadTask]:
        return [t for t in self._tasks if t.status == DownloadStatus.FAILED]

    def get_task(self, url: str) -> Optional[DownloadTask]:
        for t in self._tasks:
            if t.url == url:
                return t
        return None

    def summary(self) -> str:
        parts = []
        dl = sum(1 for t in self._tasks if t.status == DownloadStatus.DOWNLOADING)
        done = sum(1 for t in self._tasks if t.status == DownloadStatus.COMPLETE)
        fail = sum(1 for t in self._tasks if t.status == DownloadStatus.FAILED)
        if dl:
            parts.append(f"{dl} downloading")
        if done:
            parts.append(f"{done} complete")
        if fail:
            parts.append(f"{fail} failed")
        return ", ".join(parts) if parts else "No downloads"
