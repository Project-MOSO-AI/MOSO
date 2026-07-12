from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
import datetime
import logging

logger = logging.getLogger(__name__)

BUBBLE_WIDTH = 450
BUBBLE_HEIGHT = 450

AUTO_HIDE_SECONDS = 10


class ConversationBubble(QFrame):
    closed = Signal()
    text_submitted = Signal(str)
    feedback_submitted = Signal(str, str)

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

        self._mode_btn = QPushButton("Desktop Mode")
        self._mode_btn.setFixedSize(90, 20)
        self._mode_btn.setStyleSheet("""
            QPushButton {
                background: rgba(40,100,200,80); color: #fff; border: none;
                border-radius: 8px; font-size: 10px;
            }
            QPushButton:hover { background: rgba(60,120,220,100); }
        """)
        self._mode_btn.clicked.connect(self.toggle_mode)
        header.addWidget(self._mode_btn)
        self._conversation_mode = False

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
        self._display.setOpenExternalLinks(False)
        self._display.anchorClicked.connect(self._on_anchor_clicked)
        layout.addWidget(self._display)

        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Type a message...")
        self._input_field.setStyleSheet("""
            QLineEdit {
                background: rgba(10, 10, 20, 200);
                color: #ffffff;
                border: 1px solid rgba(138, 43, 226, 120);
                border-radius: 12px;
                padding: 10px;
                font-size: 13px;
                font-family: "Segoe UI", sans-serif;
            }
            QLineEdit:focus {
                border: 1px solid rgba(180, 80, 255, 180);
                background: rgba(20, 20, 40, 230);
            }
        """)
        self._input_field.returnPressed.connect(self._on_input_return)
        layout.addWidget(self._input_field)

        self.setStyleSheet("""
            ConversationBubble {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 rgba(25, 25, 45, 240),
                                            stop:1 rgba(15, 10, 30, 250));
                border: 1px solid rgba(138, 43, 226, 80);
                border-radius: 20px;
            }
            QTextBrowser {
                background: transparent;
                color: #e2e8f0;
                border: none;
                padding: 8px;
                font-size: 13px;
                font-family: "Segoe UI", sans-serif;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0);
                width: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(138, 43, 226, 80);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        # Disable auto-hide per user request
        # self._auto_hide_timer.timeout.connect(self.hide)

        self._streaming_buffer = ""
        self._streaming_tag = ""

    def paintEvent(self, event):
        from PySide6.QtWidgets import QStyleOption, QStyle
        from PySide6.QtGui import QPainter
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        super().paintEvent(event)

    def _on_input_return(self):
        text = self._input_field.text().strip()
        if text:
            self.text_submitted.emit(text)
            self._input_field.clear()
            
    def _on_anchor_clicked(self, url):
        url_str = url.toString()
        if url_str.startswith("feedback:"):
            parts = url_str.split(":", 2)
            if len(parts) == 3:
                fb_type, msg = parts[1], parts[2]
                self.feedback_submitted.emit(fb_type, msg)
                self.append_system(f"Feedback recorded: {fb_type}", color="#22c55e")

    def _scroll_to_bottom(self):
        sb = self._display.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def toggle_mode(self):
        self._conversation_mode = not self._conversation_mode
        if self._conversation_mode:
            self._mode_btn.setText("Chat Mode")
            self._mode_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(138,43,226,80); color: #fff; border: none;
                    border-radius: 8px; font-size: 10px;
                }
                QPushButton:hover { background: rgba(158,63,246,100); }
            """)
        else:
            self._mode_btn.setText("Desktop Mode")
            self._mode_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(40,100,200,80); color: #fff; border: none;
                    border-radius: 8px; font-size: 10px;
                }
                QPushButton:hover { background: rgba(60,120,220,100); }
            """)

    def _get_timestamp(self):
        return datetime.datetime.now().strftime("[%H:%M:%S]")

    def append_message(self, sender: str, text: str):
        ts = self._get_timestamp()
        tag = "You" if sender == "user" else "MOSO"
        color = "#8A2BE2" if sender == "assistant" else "#3b82f6"
        
        feedback_html = ""
        if sender == "assistant":
            # Very basic URL encoding to avoid breaking the href
            import urllib.parse
            encoded = urllib.parse.quote(text[:200]) # only encode first 200 chars to avoid huge URLs
            feedback_html = f'&nbsp;&nbsp;<a href="feedback:good:{encoded}" style="text-decoration:none;">👍</a> <a href="feedback:bad:{encoded}" style="text-decoration:none;">👎</a>'
            
        line = f'<span style="color:#666; font-size:10px;">{ts}</span> <b style="color:{color}">{tag}:</b> {text}{feedback_html}'
        self._display.append(line)
        self._scroll_to_bottom()
        self._start_auto_hide()

    def log_step_start(self, text: str):
        ts = self._get_timestamp()
        self._display.append(f'<span style="color:#666; font-size:10px;">{ts}</span> <span style="color:#f59e0b; margin-left: 10px;">▶ Starting: {text}</span>')
        self._scroll_to_bottom()

    def log_step_done(self, text: str):
        ts = self._get_timestamp()
        self._display.append(f'<span style="color:#666; font-size:10px;">{ts}</span> <span style="color:#22c55e; margin-left: 10px;">✓ Done: {text}</span>')
        self._scroll_to_bottom()
        
    def log_step_failed(self, text: str):
        ts = self._get_timestamp()
        self._display.append(f'<span style="color:#666; font-size:10px;">{ts}</span> <span style="color:#ef4444; margin-left: 10px;">✗ Failed: {text}</span>')
        self._scroll_to_bottom()

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
        pass # Disabled

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
