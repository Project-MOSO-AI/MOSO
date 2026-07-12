from __future__ import annotations

import logging
import sys
import threading

from PySide6.QtCore import QCoreApplication, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QInputDialog, QMenu

from moso_ui.conversation import ConversationBubble
from moso_ui.settings import AuraSettings
from moso_ui.tray import SystemTray
from moso_ui.voice_interaction import VoiceInteraction

logger = logging.getLogger(__name__)


class AuraApp:
    def __init__(self):
        self._app = QApplication(sys.argv)
        self._app.setApplicationName("MOSO Aura")
        self._app.setQuitOnLastWindowClosed(False)

        self._settings = AuraSettings()
        self._bubble = ConversationBubble()
        self._tray = SystemTray()
        self._voice = VoiceInteraction()

        self._setup_connections()
        self._load_position()
        self._init_modules()

    def _setup_connections(self):
        self._tray.show_action.triggered.connect(self._show_bubble)
        self._tray.quit_action.triggered.connect(self._quit)
        self._tray.settings_action.triggered.connect(self._show_about)
        self._bubble.text_submitted.connect(self._on_text_submitted)
        self._bubble.feedback_submitted.connect(self._on_feedback_submitted)
        self._voice.set_state_callback(self._on_voice_state)
        self._voice.set_text_callback(self._on_voice_text)
        self._voice.set_input_callback(self._request_text_input)
        self._setup_global_hotkeys()

    def _on_text_submitted(self, text: str):
        # Run in background to prevent UI freeze
        t = threading.Thread(target=self._voice._on_text_input, args=(text,), daemon=True)
        t.start()

    def _on_feedback_submitted(self, fb_type: str, msg: str):
        if hasattr(self._voice, "handle_feedback"):
            t = threading.Thread(target=self._voice.handle_feedback, args=(fb_type, msg), daemon=True)
            t.start()

    def _setup_global_hotkeys(self):
        self._ptt_shortcut = QShortcut(QKeySequence("Space"), self._bubble)
        self._ptt_shortcut.activated.connect(self._toggle_voice)

    def _load_position(self):
        screen = self._app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            # Center the bubble
            x = geo.center().x() - (self._bubble.width() // 2)
            y = geo.center().y() - (self._bubble.height() // 2)
            self._bubble.move(x, y)

    def _init_modules(self):
        self._bubble.set_status("loading")
        self._bubble.append_system("Initializing MOSO modules...", "#8A2BE2")
        # Run orchestrator init in background so UI stays responsive
        def _bg_init():
            self._voice._init_orchestrator()
            # Schedule UI update back on main thread
            from PySide6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self._bubble, "update", Qt.ConnectionType.QueuedConnection)
            QMetaObject.invokeMethod(self._bubble, "update", Qt.ConnectionType.QueuedConnection)
        t = threading.Thread(target=_bg_init, daemon=True)
        t.start()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self._check_ready(t))

    def _save_position(self):
        pass

    def _show_bubble(self):
        self._bubble.show()
        self._bubble.raise_()

    def _toggle_bubble(self):
        if self._bubble.isVisible():
            self._bubble.hide()
        else:
            self._bubble.show()
            self._bubble.raise_()

    def _toggle_voice(self):
        if self._voice.is_listening:
            self._voice.stop_listening()
        else:
            self._bubble.show()
            self._bubble.raise_()
            self._bubble.set_status("listening")
            self._voice.start_listening()

    def _request_text_input(self) -> str:
        text, ok = QInputDialog.getText(self._bubble, "MOSO", "Type your message:")
        return text if ok else ""

    def _on_voice_state(self, state):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda s=state: self._do_voice_state(s))

    def _do_voice_state(self, state):
        self._bubble.set_status(state.value)
        if state.value == "thinking":
            self._bubble.show_thinking()
        elif state.value == "analyzing":
            self._bubble.show_analyzing()

    def _on_voice_text(self, text: str):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda t=text: self._do_voice_text(t))

    def _do_voice_text(self, text: str):
        if text.startswith("You:"):
            self._bubble.append_message("user", text[4:].strip())
        elif text.startswith("MOSO:"):
            self._bubble.append_message("assistant", text[5:].strip())
        else:
            self._bubble.append_system(text, "#f59e0b")
        self._bubble.show()
        self._bubble.raise_()

    def _check_ready(self, thread: threading.Thread):
        if thread.is_alive():
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, lambda: self._check_ready(thread))
            return
        self._on_modules_ready()

    def _on_modules_ready(self):
        self._bubble.set_status("idle")
        orch = self._voice.orchestrator
        if orch:
            enabled = []
            if orch.memory: enabled.append("Memory")
            if orch.resources: enabled.append("Resources")
            if orch.tools: enabled.append("Tools")
            if orch.agents: enabled.append("Agents")
            if orch.computer_use: enabled.append("Computer Use")
            if orch.vision: enabled.append("Vision")
            if orch.system_intelligence: enabled.append("System Intelligence")
            if orch.risk: enabled.append("Risk Engine")
            if orch.realtime: enabled.append("Realtime Research")
            if orch.identity_verifier: enabled.append("Identity")
            if orch.llm: enabled.append("LLM")
            if enabled:
                self._bubble.append_system(f"MOSO ready — {' · '.join(enabled)}", "#22c55e")
            else:
                self._bubble.append_system("MOSO started in fallback mode (no LLM model configured)", "#f59e0b")
        else:
            self._bubble.append_system("MOSO started — modules not available", "#f97316")

    def _show_about(self):
        self._bubble.set_text("MOSO AI - Aura UI\n\n"
                              "Privacy-first local AI assistant.\n\n"
                              "Click the orb or press Space to talk.\n\n"
                              "Integrated modules:\n"
                              "Memory · System Intelligence · Tools\n"
                              "Risk Engine · Agents · Vision\n"
                              "Computer Use · Realtime Research\n\n"
                              "Version: 1.0.0")
        self._toggle_bubble()

    def _quit(self):
        self._save_position()
        self._voice.shutdown()
        self._bubble.close()
        self._app.quit()

    def run(self):
        self._bubble.show()
        self._tray.show()
        return self._app.exec()


def main():
    app = AuraApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
