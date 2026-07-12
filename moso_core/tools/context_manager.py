from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    active_app: str = ""
    last_action: str = ""
    last_target: str = ""
    last_timestamp: float = 0.0

    @property
    def is_recent(self) -> bool:
        return (time.time() - self.last_timestamp) < 300  # 5 min cooldown

    def update(self, app: str, action: str = "", target: str = ""):
        self.active_app = app
        self.last_action = action
        self.last_target = target
        self.last_timestamp = time.time()
        logger.info("Context: app=%s action=%s target=%s", app, action, target)

    def clear(self):
        self.active_app = ""
        self.last_action = ""
        self.last_target = ""
        self.last_timestamp = 0.0


class ContextManager:
    def __init__(self):
        self._state = AppState()

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def active_app(self) -> str:
        return self._state.active_app if self._state.is_recent else ""

    def set_app(self, app: str, action: str = "", target: str = ""):
        self._state.update(app, action, target)

    def clear(self):
        self._state.clear()

    def get_active_app(self) -> str:
        return self.active_app
