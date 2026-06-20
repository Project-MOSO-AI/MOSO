from __future__ import annotations

from enum import Enum


class OrbState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ANALYZING = "analyzing"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    WARNING = "warning"
    ERROR = "error"


class StatusColor(str, Enum):
    IDLE = "#6b7280"
    LISTENING = "#3b82f6"
    THINKING = "#22c55e"
    ANALYZING = "#f59e0b"
    EXECUTING = "#eab308"
    SPEAKING = "#a855f7"
    WARNING = "#f97316"
    ERROR = "#ef4444"
