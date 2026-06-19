from __future__ import annotations

import logging
import queue
import threading
from typing import Optional, Callable

import numpy as np

from moso_ui.states import OrbState

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    sr = None

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    pyttsx3 = None


AUDIO_LEVEL_THRESHOLD = 0.005


class VoiceInteraction:
    def __init__(self):
        self._recognizer = sr.Recognizer() if sr else None
        self._tts_engine: Optional[pyttsx3.Engine] = None
        self._tts_lock = threading.Lock()
        self._listening = False
        self._state_callback: Optional[Callable] = None
        self._text_callback: Optional[Callable] = None
        self._input_callback: Optional[Callable] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._stream: Optional[sd.InputStream] = None

        self._init_tts()

    def _init_tts(self):
        if TTS_AVAILABLE:
            try:
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty("rate", 180)
                self._tts_engine.setProperty("volume", 0.9)
                voices = self._tts_engine.getProperty("voices")
                if voices:
                    self._tts_engine.setProperty("voice", voices[0].id)
                logger.info("TTS initialized")
            except Exception as e:
                logger.warning("TTS init failed: %s", e)
                self._tts_engine = None

    def set_state_callback(self, callback: Callable):
        self._state_callback = callback

    def set_text_callback(self, callback: Callable):
        self._text_callback = callback

    def set_input_callback(self, callback: Callable):
        self._input_callback = callback

    def _update_state(self, state: OrbState):
        if self._state_callback:
            self._state_callback(state)

    def _show_text(self, text: str):
        if self._text_callback:
            self._text_callback(text)

    @property
    def is_listening(self) -> bool:
        return self._listening

    def start_listening(self):
        if self._listening:
            return
        if not SOUNDDEVICE_AVAILABLE or not sd:
            self._request_text_direct()
            return

        self._audio_queue = queue.Queue()

        device = self._find_best_device()
        if device is None:
            self._request_text_direct()
            return

        dev_id, sr_rate = device
        try:
            self._stream = sd.InputStream(
                samplerate=sr_rate,
                channels=1,
                dtype="float32",
                device=dev_id,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._listening = True
            self._update_state(OrbState.LISTENING)
            logger.info("Listening on device %d @ %d Hz", dev_id, sr_rate)
        except Exception as e:
            logger.error("Failed to start mic: %s", e)
            self._request_text_direct()

    def _find_best_device(self):
        if not sd:
            return None
        best = None
        for i, info in enumerate(sd.query_devices()):
            if info["max_input_channels"] > 0:
                sr = int(info["default_samplerate"]) if info.get("default_samplerate", 0) > 0 else 44100
                name = info["name"]
                if "Microphone" in name or "mic" in name.lower():
                    return (i, sr)
                if best is None:
                    best = (i, sr)
        return best

    def stop_listening(self):
        if not self._listening:
            return
        self._listening = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._process_audio()

    def _request_text_direct(self):
        self._update_state(OrbState.IDLE)
        self._show_text("MOSO: Click or press Space, then type your message.")
        text = self._request_input()
        if text and text.strip():
            self._on_text_input(text.strip())

    def _process_audio(self):
        chunks = []
        while True:
            try:
                chunks.append(self._audio_queue.get_nowait())
            except queue.Empty:
                break
        if not chunks:
            self._update_state(OrbState.IDLE)
            return
        audio = np.concatenate(chunks, axis=0).flatten()
        mx = np.max(np.abs(audio))
        if mx < AUDIO_LEVEL_THRESHOLD:
            self._show_text("MOSO: I didn't hear anything. Type instead?")
            self._request_text_direct()
            return
        threading.Thread(target=self._transcribe_and_respond, args=(audio,), daemon=True).start()

    def _on_text_input(self, text: str):
        self._update_state(OrbState.THINKING)
        self._show_text("You: %s" % text)
        response = self._generate_response(text)
        self._show_text("MOSO: %s" % response)
        self._update_state(OrbState.SPEAKING)
        self._text_to_speech(response)
        self._update_state(OrbState.IDLE)

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.debug("Audio status: %s", status)
        if self._listening:
            self._audio_queue.put(indata.copy())

    def _transcribe_and_respond(self, audio: np.ndarray):
        self._update_state(OrbState.THINKING)
        text = self._speech_to_text(audio)
        if text is None:
            self._update_state(OrbState.IDLE)
            return
        if not text.strip():
            self._show_text("MOSO: I didn't catch that. Could you repeat?")
            self._text_to_speech("I didn't catch that. Could you repeat?")
            self._update_state(OrbState.IDLE)
            return
        self._show_text("You: %s" % text)
        response = self._generate_response(text)
        self._show_text("MOSO: %s" % response)
        self._update_state(OrbState.SPEAKING)
        self._text_to_speech(response)
        self._update_state(OrbState.IDLE)

    def _speech_to_text(self, audio: np.ndarray) -> Optional[str]:
        if not SR_AVAILABLE or not self._recognizer:
            return None
        try:
            audio_int16 = (audio * 32767).astype(np.int16)
            audio_data = sr.AudioData(audio_int16.tobytes(), 16000, 2)
            text = self._recognizer.recognize_google(audio_data)
            return text.strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logger.error("Google STT error: %s", e)
            return None
        except Exception as e:
            logger.error("STT error: %s", e)
            return None

    def _request_input(self) -> Optional[str]:
        if self._input_callback:
            return self._input_callback()
        return None

    def _generate_response(self, text: str) -> str:
        try:
            import os, json
            from moso_core.orchestration.orchestrator import MOSOOrchestrator
            settings_path = os.path.join(os.path.expanduser("~"), ".moso", "aura_settings.json")
            model_path = None
            if os.path.exists(settings_path):
                with open(settings_path) as f:
                    model_path = json.load(f).get("model_path")
            if model_path and os.path.exists(model_path):
                orch = MOSOOrchestrator()
                orch.enable_llm(model_path=model_path)
                if orch.llm and orch.llm.start():
                    return orch.llm.chat(text).text
        except ImportError:
            pass
        except Exception:
            pass
        return "You said: %s" % text

    def _text_to_speech(self, text: str):
        if not TTS_AVAILABLE or not self._tts_engine:
            return
        with self._tts_lock:
            try:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
            except Exception as e:
                logger.error("TTS error: %s", e)
