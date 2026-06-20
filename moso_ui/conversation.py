from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

BUBBLE_WIDTH = 400
BUBBLE_HEIGHT = 350

AUTO_HIDE_SECONDS = 10


class ConversationBubble(QFrame):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(BUBBLE_WIDTH, BUBBLE_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("MOSO")
        title.setStyleSheet("color: #8A2BE2; font-weight: bold; font-size: 13px; background: transparent;")
        header.addWidget(title)

        self._status_label = QLabel("idle")
        self._status_label.setStyleSheet("color: #6b7280; font-size: 10px; background: transparent;")
        header.addWidget(self._status_label)

        header.addStretch()
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedSize(40, 20)
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,20); color: #888; border: none;
                border-radius: 8px; font-size: 10px;
            }
            QPushButton:hover { background: rgba(255,255,255,40); color: #ddd; }
        """)
        self._clear_btn.clicked.connect(self.clear)
        header.addWidget(self._clear_btn)

        close_btn = QPushButton("X")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,30); color: #aaa; border: none;
                border-radius: 10px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: rgba(255,80,80,80); color: white; }
        """)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        self._display = QTextBrowser()
        self._display.setOpenExternalLinks(False)
        self._display.setReadOnly(True)
        self._display.setStyleSheet("""
            QTextBrowser {
                background: rgba(20,20,40,200);
                color: #ddd;
                border: 1px solid rgba(138,43,226,80);
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        self._display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self._display)

        self.setStyleSheet("""
            ConversationBubble {
                background: rgba(15,15,35,220);
                border: 1px solid rgba(138,43,226,100);
                border-radius: 16px;
            }
        """)

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

        self._streaming_buffer = ""
        self._streaming_tag = ""

    def _scroll_to_bottom(self):
        sb = self._display.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def append_message(self, sender: str, text: str):
        tag = "You" if sender == "user" else "MOSO"
        color = "#8A2BE2" if sender == "assistant" else "#3b82f6"
        line = f'<b style="color:{color}">{tag}:</b> {text}'
        self._display.append(line)
        self._scroll_to_bottom()
        self._start_auto_hide()

    def append_system(self, text: str, color: str = "#f59e0b"):
        line = f'<i style="color:{color}">⚡ {text}</i>'
        self._display.append(line)
        self._scroll_to_bottom()

    def show_thinking(self):
        self._display.append(
            '<i style="color:#22c55e">MOSO is thinking...</i>'
        )
        self._scroll_to_bottom()

    def show_analyzing(self, detail: str = ""):
        text = f"MOSO is analyzing... {detail}" if detail else "MOSO is analyzing..."
        self._display.append(f'<i style="color:#f59e0b">{text}</i>')
        self._scroll_to_bottom()

    def show_executing(self, detail: str = ""):
        text = f"MOSO is executing... {detail}" if detail else "MOSO is executing..."
        self._display.append(f'<i style="color:#eab308">{text}</i>')
        self._scroll_to_bottom()

    def show_warning(self, text: str):
        self._display.append(f'<b style="color:#f97316">⚠ {text}</b>')
        self._scroll_to_bottom()

    def show_error(self, text: str):
        self._display.append(f'<b style="color:#ef4444">✗ {text}</b>')
        self._scroll_to_bottom()

    def show_risk(self, level: str, explanation: str):
        colors = {"LOW": "#22c55e", "MEDIUM": "#f59e0b", "HIGH": "#f97316", "CRITICAL": "#ef4444"}
        c = colors.get(level.upper(), "#f59e0b")
        self._display.append(f'<b style="color:{c}">🛡 Risk: {level.upper()} — {explanation}</b>')
        self._scroll_to_bottom()

    def start_streaming(self, tag: str = "MOSO"):
        self._streaming_tag = tag
        self._streaming_buffer = ""
        color = "#8A2BE2"
        self._display.append(f'<b style="color:{color}">{tag}:</b> ')
        self._scroll_to_bottom()

    def stream_chunk(self, chunk: str):
        self._streaming_buffer += chunk
        cursor = self._display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self._scroll_to_bottom()

    def end_streaming(self):
        self._streaming_tag = ""
        self._streaming_buffer = ""
        self._scroll_to_bottom()
        self._start_auto_hide()

    def replace_last_line(self, text: str):
        cursor = self._display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(
            QTextCursor.MoveOperation.StartOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.removeSelectedText()
        cursor.insertText(text)
        self._scroll_to_bottom()

    def set_text(self, text: str):
        self._display.clear()
        self._display.setPlainText(text)
        self.show()
        self.raise_()
        self._start_auto_hide()

    def set_status(self, status: str):
        colors = {
            "idle": "#6b7280",
            "listening": "#3b82f6",
            "thinking": "#22c55e",
            "analyzing": "#f59e0b",
            "executing": "#eab308",
            "speaking": "#a855f7",
            "warning": "#f97316",
            "error": "#ef4444",
        }
        color = colors.get(status, "#6b7280")
        self._status_label.setText(status)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")

    def _start_auto_hide(self):
        self._auto_hide_timer.start(AUTO_HIDE_SECONDS * 1000)

    def clear(self):
        self._display.clear()
        self._status_label.setText("idle")
        self._streaming_buffer = ""
        self._streaming_tag = ""

    def set_visible(self, visible: bool):
        if visible:
            self.show()
            self.raise_()
        else:
            self.hide()
            self._auto_hide_timer.stop()
