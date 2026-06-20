from __future__ import annotations

import json
import math
import os
import sys

from PySide6.QtCore import Qt, QTimer, Signal, QPoint, Property
from PySide6.QtGui import QAction, QColor, QConicalGradient, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QSystemTrayIcon, QVBoxLayout, QWidget

from moso_ui.states import OrbState, StatusColor

ORB_SIZE = 100
ANIMATION_INTERVAL = 50


class AuraOrb(QWidget):
    state_changed = Signal(str)
    single_clicked = Signal()
    double_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = OrbState.IDLE
        self._angle = 0
        self._pulse = 0
        self._dragging = False
        self._drag_pos = QPoint()
        self._drag_start = QPoint()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(ORB_SIZE, ORB_SIZE)

        self._label = QLabel("MOSO", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: white; font-size: 11px; font-weight: bold; background: transparent;")
        self._label.setGeometry(0, 0, ORB_SIZE, ORB_SIZE)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(ANIMATION_INTERVAL)

    def set_state(self, state: OrbState):
        self._state = state
        self.state_changed.emit(state.value)
        self.update()

    def state(self) -> OrbState:
        return self._state

    def _animate(self):
        self._angle = (self._angle + 3) % 360
        if self._state in (OrbState.THINKING, OrbState.LISTENING, OrbState.SPEAKING, OrbState.ANALYZING, OrbState.EXECUTING):
            self._pulse = (self._pulse + 1) % 100
        else:
            self._pulse = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = StatusColor[self._state.name].value
        base = QColor(color)
        rect = self.rect().adjusted(4, 4, -4, -4)

        if self._state == OrbState.IDLE:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base)
            painter.drawEllipse(rect)
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.drawEllipse(rect.adjusted(4, 4, -4, -4))

        elif self._state == OrbState.LISTENING:
            gradient = QConicalGradient(rect.center(), self._angle)
            gradient.setColorAt(0.0, base)
            gradient.setColorAt(0.3, base.lighter(130))
            gradient.setColorAt(0.6, base)
            gradient.setColorAt(1.0, base)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawEllipse(rect)
            glow = base.lighter(150)
            glow.setAlpha(40)
            painter.setBrush(glow)
            r = rect.adjusted(-8, -8, 8, 8)
            painter.drawEllipse(r)

        elif self._state == OrbState.THINKING:
            scale = 1 + 0.05 * (self._pulse / 100.0)
            cx, cy = rect.center().x(), rect.center().y()
            w, h = rect.width() * scale, rect.height() * scale
            scaled = rect.__class__(cx - w // 2, cy - h // 2, w, h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base)
            painter.drawEllipse(scaled)
            dots = 6
            dot_radius = 3
            for i in range(dots):
                a = self._angle + i * 60
                dx = int(math.cos(math.radians(a)) * w * 0.45)
                dy = int(math.sin(math.radians(a)) * w * 0.45)
                painter.setBrush(QColor(255, 255, 255, 180))
                painter.drawEllipse(cx + dx - dot_radius, cy + dy - dot_radius, dot_radius * 2, dot_radius * 2)

        elif self._state == OrbState.ANALYZING:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base)
            painter.drawEllipse(rect)
            segments = 8
            for i in range(segments):
                a = self._angle + i * 45
                dx = int(math.cos(math.radians(a)) * rect.width() * 0.35)
                dy = int(math.sin(math.radians(a)) * rect.height() * 0.35)
                alpha = 80 + int(80 * math.sin(math.radians(self._angle * 3 + i * 45)))
                painter.setBrush(QColor(255, 255, 255, alpha))
                painter.drawEllipse(cx + dx - 2, cy + dy - 2, 4, 4)
            painter.setBrush(base.lighter(130))
            painter.drawEllipse(rect.adjusted(12, 12, -12, -12))

        elif self._state == OrbState.EXECUTING:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base)
            painter.drawEllipse(rect)
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            span = 60 + 30 * math.sin(math.radians(self._angle * 2))
            painter.drawArc(rect.adjusted(6, 6, -6, -6), int(self._angle * 16), int(span * 16))

        elif self._state == OrbState.SPEAKING:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base)
            painter.drawEllipse(rect)
            for i in range(3):
                alpha = 80 - i * 20
                offset = 5 + i * 4 + int(3 * (self._pulse / 100.0))
                ring = rect.adjusted(-offset, -offset, offset, offset)
                painter.setBrush(QColor(color).lighter(120))
                painter.setOpacity(0.3 - i * 0.08)
                painter.drawEllipse(ring)
            painter.setOpacity(1.0)

        elif self._state == OrbState.WARNING:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base)
            painter.drawEllipse(rect)
            painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            c = rect.center()
            off = rect.width() // 5
            painter.drawLine(c.x(), c.y() - off, c.x(), c.y() + off // 2)
            dot_size = 3
            painter.setBrush(QColor(255, 255, 255, 200))
            painter.drawEllipse(c.x() - dot_size, c.y() + off // 2 + 2, dot_size * 2, dot_size * 2)

        elif self._state == OrbState.ERROR:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base)
            painter.drawEllipse(rect)
            painter.setPen(QPen(QColor(255, 255, 255, 200), 3))
            c = rect.center()
            off = rect.width() // 6
            painter.drawLine(c.x() - off, c.y() - off, c.x() + off, c.y() + off)
            painter.drawLine(c.x() + off, c.y() - off, c.x() - off, c.y() + off)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            dist = (event.globalPosition().toPoint() - self._drag_start).manhattanLength()
            if dist < 10:
                self.single_clicked.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.double_clicked.emit()
