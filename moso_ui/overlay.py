"""Screen attention overlay — yellow for elements AI reads, blue for focused window.

Transparent, click-through, always-on-top PySide6 window. Redraws only
when a new observation lands, not every frame.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import QApplication, QWidget

logger = logging.getLogger(__name__)

# ponytail: constants not config — these don't need tuning
_YELLOW = QColor(255, 230, 60, 70)       # elements AI is reading
_YELLOW_BORDER = QColor(255, 200, 0, 180)
_BLUE = QColor(120, 190, 255, 40)       # focused window fill
_BLUE_BORDER = QColor(120, 190, 255, 220)


class AttentionOverlay(QWidget):
    """Transparent overlay showing what MOSO is looking at on screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._elements: list[dict] = []
        self._focus_bounds: tuple[int, int, int, int] = (0, 0, 0, 0)
        self._visible = False

        # Auto-hide after 3 seconds of no updates
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._auto_hide)

    def update_state(
        self,
        ui_elements: list[dict],
        focus_bounds: tuple[int, int, int, int],
    ) -> None:
        """Update overlay with new perception data. Call from VisionPlanner._on_step."""
        self._elements = ui_elements
        self._focus_bounds = focus_bounds

        if not self._visible:
            # Size to primary screen
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.geometry()
                self.setGeometry(geo)
            self.show()
            self._visible = True

        self.update()
        self._hide_timer.start(3000)

    def _auto_hide(self) -> None:
        self.hide()
        self._visible = False

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Blue box: focused window
        x, y, w, h = self._focus_bounds
        if w > 0 and h > 0:
            p.setPen(QPen(_BLUE_BORDER, 3))
            p.setBrush(QBrush(_BLUE))
            p.drawRoundedRect(x, y, w, h, 6, 6)

        # Yellow boxes: elements AI is reading
        p.setPen(QPen(_YELLOW_BORDER, 1))
        p.setBrush(QBrush(_YELLOW))
        for el in self._elements:
            ex = el.get("x", 0)
            ey = el.get("y", 0)
            ew = el.get("width", 0)
            eh = el.get("height", 0)
            if ew > 0 and eh > 0:
                p.drawRect(ex, ey, ew, eh)

        p.end()

    def close_overlay(self) -> None:
        self._hide_timer.stop()
        self.hide()
        self._visible = False
