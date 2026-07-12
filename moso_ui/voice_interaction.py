from __future__ import annotations

import json
import logging
import os
import queue
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, Callable

import numpy as np

from moso_core.inference.base import InferenceConfig
from moso_core.orchestration.orchestrator import Orchestrator
from moso_core.tools.context_manager import ContextManager
from moso_ui.states import OrbState

# Desktop intelligence (optional, loaded lazily)
_desktop_memory = None
_vision_planner = None


def _load_desktop_intelligence():
    global _desktop_memory, _vision_planner
    if _desktop_memory is not None:
        return
    try:
        from moso_core.desktop.desktop_memory import DesktopMemory
        from moso_core.desktop.vision_planner import VisionPlanner
        from moso_core.desktop.action_executor import ActionExecutor
        _desktop_memory = DesktopMemory()
        _desktop_memory.load()
        _vision_planner = VisionPlanner()
        _vision_planner.set_action_executor(ActionExecutor())
    except Exception:
        pass

logger = logging.getLogger(__name__)

# --- sounddevice ---
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None

# --- faster-whisper (local offline STT) ---
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# --- speech_recognition (legacy fallback) ---
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    sr = None

# --- pyttsx3 (TTS) ---
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    pyttsx3 = None


AUDIO_LEVEL_THRESHOLD = 0.0003
WHISPER_SAMPLE_RATE = 16000
# Dynamic threshold tracking
_recent_levels: list[float] = []
_MAX_RECENT = 20


class ConversationManager:
    def __init__(self, max_messages: int = 20):
        self._messages: list[dict] = []
        self._max_messages = max_messages
        self._active_task: Optional[str] = None
        self._active_plan: Optional[dict] = None

    @property
    def active_task(self) -> Optional[str]:
        return self._active_task

    @active_task.setter
    def active_task(self, value: Optional[str]):
        self._active_task = value

    def add_message(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        if len(self._messages) > self._max_messages:
            self._messages.pop(0)

    def get_history(self, limit: int = 10) -> list[dict]:
        return self._messages[-limit:]

    def build_context(self, query: str) -> str:
        parts = []
        if self._active_task:
            parts.append(f"[Active Task: {self._active_task}]")
        history = self.get_history(6)
        if history:
            parts.append("[Recent Conversation]")
            for msg in history[-4:]:
                tag = "User" if msg["role"] == "user" else "Assistant"
                parts.append(f"{tag}: {msg['content']}")
        parts.append(f"[Query] {query}")
        return "\n".join(parts)

    def clear(self):
        self._messages.clear()
        self._active_task = None
        self._active_plan = None


class VoiceInteraction:
    def __init__(self):
        self._tts_engine: Optional[pyttsx3.Engine] = None
        self._tts_lock = threading.Lock()
        self._listening = False
        self._generating = False
        self._state_callback: Optional[Callable] = None
        self._text_callback: Optional[Callable] = None
        self._input_callback: Optional[Callable] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._orchestrator: Optional[Orchestrator] = None
        self._conversation = ConversationManager()
        self._context = ContextManager()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="moso_audio")
        self._whisper_model = None
        self._device_sample_rate = WHISPER_SAMPLE_RATE
        self._orch_ready = False
        self._notepad_enabled = False

        self._init_tts()
        self._init_whisper()

    # ----- Initialization -----

    def _init_whisper(self):
        self._executor.submit(self._load_whisper)

    def _load_whisper(self):
        if WHISPER_AVAILABLE:
            try:
                self._whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
                logger.info("Whisper model loaded (base, CPU, int8)")
            except Exception as e:
                logger.warning("Whisper init failed (will retry on first use): %s", e)
        else:
            logger.warning("faster-whisper not installed. Install: pip install faster-whisper")

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

    def _init_orchestrator(self):
        try:
            settings_path = os.path.join(os.path.expanduser("~"), ".moso", "aura_settings.json")
            model_path = None
            if os.path.exists(settings_path):
                with open(settings_path) as f:
                    data = json.load(f)
                    model_path = data.get("model_path", "")
            if not model_path or not os.path.exists(model_path):
                logger.warning("No LLM model configured. Set model_path in Aura settings (%s)", settings_path)

            config = InferenceConfig(
                model_path=model_path or "",
                n_ctx=2048,
                max_tokens=512,
                temperature=0.7,
            )
            self._orchestrator = Orchestrator(config=config, enable_safety=True)
            self._orchestrator.enable_all(model_path=model_path or "")
            if self._orchestrator.llm and self._orchestrator.llm.start():
                self._orch_ready = True
                logger.info("Orchestrator fully initialized with all modules")
            else:
                logger.warning("LLM not available — running with fallback modules only")
                self._orch_ready = False

            # Run diagnostics on startup
            self._run_startup_diagnostics()

        except ImportError as e:
            logger.error("Orchestrator modules not available: %s", e)
            self._orch_ready = False
        except Exception as e:
            logger.error("Orchestrator init failed: %s", e)
            self._orch_ready = False

    def _run_startup_diagnostics(self):
        try:
            from moso_core.diagnostics import run_diagnostics
            report = run_diagnostics()
            summary = report.summary()
            logger.info("Startup diagnostics:\n%s", summary)
            fixable = report.fixable_items()
            if fixable and self._text_callback:
                self._text_callback(f"MOSO: {len(fixable)} optional components can be installed")
                for item in fixable[:5]:
                    self._text_callback(f"MOSO:   {item.name} — {item.fix_command}")
        except Exception as e:
            logger.debug("Startup diagnostics skipped: %s", e)

    @property
    def orchestrator(self) -> Optional[Orchestrator]:
        return self._orchestrator

    @property
    def is_orchestrator_ready(self) -> bool:
        return self._orch_ready

    # ----- Callbacks -----

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

    def _ensure_notepad(self) -> bool:
        if not self._notepad_enabled:
            return False
        try:
            import pygetwindow as gw
            wins = gw.getWindowsWithTitle("Notepad")
            if not wins:
                return False
            win = wins[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            import time
            time.sleep(0.3)
            return True
        except Exception:
            return False

    def _mirror_to_notepad(self, user_text: str = "", assistant_text: str = ""):
        if not self._notepad_enabled:
            return
        if not self._ensure_notepad():
            return
        try:
            import pyautogui
            if user_text:
                pyautogui.typewrite("User: " + user_text, interval=0.01)
                pyautogui.press("enter")
                pyautogui.press("enter")
            if assistant_text:
                pyautogui.typewrite("MOSO: " + assistant_text, interval=0.01)
                pyautogui.press("enter")
                pyautogui.press("enter")
        except Exception as e:
            logger.debug("Notepad mirror failed: %s", e)

    @property
    def is_listening(self) -> bool:
        return self._listening

    @property
    def conversation(self) -> ConversationManager:
        return self._conversation

    # ----- Audio capture -----

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
        self._device_sample_rate = sr_rate
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
        default_input = sd.default.device[0] if sd.default.device else None
        for i, info in enumerate(sd.query_devices()):
            if info["max_input_channels"] > 0:
                sr = int(info["default_samplerate"]) if info.get("default_samplerate", 0) > 0 else WHISPER_SAMPLE_RATE
                name = info["name"]
                # Prefer the system default input device
                if i == default_input:
                    return (i, sr)
                if "Headset" in name or "headphone" in name.lower():
                    best = (i, sr)
                elif "Microphone" in name or "mic" in name.lower():
                    if best is None:
                        best = (i, sr)
                elif best is None:
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

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.debug("Audio status: %s", status)
        if self._listening:
            self._audio_queue.put(indata.copy())

    # ----- Audio processing -----

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
        mx = float(np.max(np.abs(audio)))

        # Track recent levels for dynamic threshold
        _recent_levels.append(mx)
        if len(_recent_levels) > _MAX_RECENT:
            _recent_levels.pop(0)

        # Dynamic threshold: 2x median of recent background noise
        if len(_recent_levels) >= 5:
            sorted_levels = sorted(_recent_levels)
            median = sorted_levels[len(sorted_levels) // 2]
            dynamic_threshold = max(median * 3, AUDIO_LEVEL_THRESHOLD)
        else:
            dynamic_threshold = AUDIO_LEVEL_THRESHOLD

        if mx < dynamic_threshold:
            self._show_text("MOSO: Listening... (level: %.4f, threshold: %.4f)" % (mx, dynamic_threshold))
            self._request_text_direct()
            return
        self._executor.submit(self._transcribe_and_respond, audio)

    def _request_text_direct(self):
        self._update_state(OrbState.IDLE)
        self._show_text("MOSO: Click or press Space, then type your message.")
        text = self._request_input()
        if text and text.strip():
            self._on_text_input(text.strip())

    def _request_input(self) -> Optional[str]:
        if self._input_callback:
            return self._input_callback()
        return None

    # ----- Transcription (STT) -----

    def _speech_to_text(self, audio: np.ndarray) -> Optional[str]:
        if WHISPER_AVAILABLE and self._whisper_model is not None:
            try:
                audio_16k = self._resample(audio, self._device_sample_rate, WHISPER_SAMPLE_RATE)
                segments, _ = self._whisper_model.transcribe(audio_16k, language="en")
                text = " ".join(s.text.strip() for s in segments if s.text and s.text.strip()).strip()
                if text:
                    logger.info("Whisper STT: %s", text[:80])
                    return text
                logger.warning("Whisper returned no text")
                return None
            except Exception as e:
                logger.error("Whisper STT error: %s", e)
                return None

        if SR_AVAILABLE and sr:
            try:
                audio_int16 = (audio * 32767).astype(np.int16)
                audio_data = sr.AudioData(audio_int16.tobytes(), self._device_sample_rate, 2)
                text = sr.Recognizer().recognize_google(audio_data)
                return text.strip()
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                logger.error("Google STT error: %s", e)
                return None
            except Exception as e:
                logger.error("STT error: %s", e)
                return None

        logger.warning("No STT backend available (install faster-whisper or speech_recognition)")
        return None

    @staticmethod
    def _resample(audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        if orig_rate == target_rate:
            return audio
        ratio = target_rate / orig_rate
        n_samples = int(len(audio) * ratio)
        indices = (np.arange(n_samples) / ratio).astype(np.int64)
        indices = np.clip(indices, 0, len(audio) - 1)
        return audio[indices]

    # ----- Response generation -----

    def _transcribe_and_respond(self, audio: np.ndarray):
        if self._generating:
            logger.debug("Already generating, dropping input")
            return
        self._generating = True
        self._update_state(OrbState.THINKING)
        try:
            text = self._speech_to_text(audio)
            if text is None:
                self._update_state(OrbState.IDLE)
                return
            if not text.strip():
                self._show_text("MOSO: I didn't catch that. Could you repeat?")
                self._text_to_speech("I didn't catch that. Could you repeat?")
                self._update_state(OrbState.IDLE)
                return
            # Resolve pronouns using desktop memory
            _load_desktop_intelligence()
            if _desktop_memory:
                text = _desktop_memory.resolve_command(text)
            self._conversation.add_message("user", text)
            self._show_text(f"You: {text}")
            response = self._generate_response(text)
            self._conversation.add_message("assistant", response)
            self._show_text(f"MOSO: {response}")
            self._mirror_to_notepad(text, response)
            self._update_state(OrbState.SPEAKING)
            self._text_to_speech(response)
        except Exception as e:
            logger.error("Transcribe and respond failed: %s", e)
        finally:
            self._generating = False
            self._update_state(OrbState.IDLE)

    def _autocorrect_input(self, text: str) -> str:
        if self._orchestrator and self._orchestrator.llm:
            try:
                prompt = f'Fix ONLY obvious spelling mistakes in the following query. Return ONLY the corrected string and nothing else. If it is already correct, return the original string exactly as is. Query: "{text}"'
                result = self._orchestrator.llm.chat(prompt)
                corrected = result.strip()
                if corrected.startswith('"') and corrected.endswith('"'):
                    corrected = corrected[1:-1]
                if corrected.lower() != text.lower() and len(corrected) > 0:
                    notice = f"[Corrected: '{text}' -> '{corrected}']"
                    self._show_text(notice)
                    self._mirror_to_notepad(user_text=notice)
                    return corrected
            except Exception as e:
                logger.debug("Autocorrect failed: %s", e)
        return text

    def _on_text_input(self, text: str):
        if self._generating:
            logger.debug("Already generating, dropping text input")
            return
        self._generating = True
        self._update_state(OrbState.THINKING)
        try:
            self._conversation.add_message("user", text)
            self._show_text(f"You: {text}")
            
            # Autocorrect first
            text = self._autocorrect_input(text)

            # Resolve pronouns using desktop memory
            _load_desktop_intelligence()
            if _desktop_memory:
                text = _desktop_memory.resolve_command(text)
            
            response = self._generate_response(text)
            self._conversation.add_message("assistant", response)
            self._show_text(f"MOSO: {response}")
            self._mirror_to_notepad(text, response)
            self._update_state(OrbState.SPEAKING)
            self._text_to_speech(response)
            
            # Extract preferences in background
            if self._orchestrator and self._orchestrator.memory and self._orchestrator.llm:
                from moso_core.memory.preference_extractor import PreferenceExtractor
                import threading
                def _extract():
                    extractor = PreferenceExtractor(self._orchestrator.memory, self._orchestrator.llm)
                    extractor.extract_from_chat(text, response)
                threading.Thread(target=_extract, daemon=True).start()
        except Exception as e:
            logger.error("Text input failed: %s", e)
        finally:
            self._generating = False
            self._update_state(OrbState.IDLE)
            
    def handle_feedback(self, fb_type: str, msg: str):
        if self._orchestrator and self._orchestrator.memory and self._orchestrator.llm:
            from moso_core.memory.corrections import CorrectionsManager
            cm = CorrectionsManager(self._orchestrator.memory, self._orchestrator.llm)
            result = cm.apply_feedback(fb_type, msg)
            if result:
                self._show_text(f"MOSO: {result}")
                
    def _generate_response(self, text: str) -> str:
        # Conversation mode toggle
        text_lower = text.lower().strip()
        if text_lower in ("conversation mode", "talk in notepad", "chat in notepad", "enable notepad"):
            self._notepad_enabled = not self._notepad_enabled
            state = "ON" if self._notepad_enabled else "OFF"
            return "Conversation mode %s. I'll mirror our chat in Notepad." % state
        if text_lower in ("stop notepad", "disable notepad", "stop conversation"):
            self._notepad_enabled = False
            return "Conversation mode OFF."

        # Teach Mode
        if text_lower.startswith("/teach "):
            task_name = text.strip()[7:].strip()
            from moso_core.computer_use.recorder import WorkflowRecorder
            if not getattr(self, "_recorder", None):
                self._recorder = WorkflowRecorder()
            self._recorder.start_recording(duration=3600, record_keyboard=True, blocking=False)
            self._teaching_task_name = task_name
            return f"Teach Mode ON: Recording steps for '{task_name}'. Type /done when finished."

        if text_lower == "/done" and getattr(self, "_recorder", None) and getattr(self, "_teaching_task_name", None):
            self._recorder.stop_recording()
            seq = self._recorder.export_sequence(self._teaching_task_name)
            task_name = self._teaching_task_name
            self._teaching_task_name = None
            
            # Send to LLM for generalization
            prompt = f"""
You are converting a raw screen recording into a reusable MOSO procedure.

Raw recording:
{json.dumps(seq.to_dict(), indent=2)}

Task:
1. Identify values SPECIFIC to this one instance (a contact name, a search term) — mark as {{variables}}
2. Identify values that are ALWAYS the same (clicking the send button) — keep fixed
3. Write a verify condition for each step (what should be true on screen after)
4. Suggest 3-5 trigger_phrases a user might say to invoke this recipe
5. Set app_category from: browser, media_player, messenger, text_editor, file_manager, other

Output ONLY valid JSON matching this exact schema:
{{
  "task_name": "{task_name}",
  "app_category": "...",
  "app_name": "...",
  "trigger_phrases": ["..."],
  "variables": ["..."],
  "steps": [
    {{ "action": "...", "target": "...", "verify": "..." }}
  ]
}}
"""
            if self._orchestrator and self._orchestrator.llm:
                self._show_text("MOSO: Generalizing recipe using LLM...")
                resp = self._orchestrator.llm.chat(prompt)
                
                # Parse the JSON from the LLM
                import re
                json_match = re.search(r'\{.*\}', resp, re.DOTALL)
                if json_match:
                    try:
                        recipe = json.loads(json_match.group(0))
                        # Save to ProceduralStore
                        self._orchestrator.memory.store_procedure(
                            task_name=recipe.get("task_name", task_name),
                            steps=recipe.get("steps", []),
                            tags=recipe.get("trigger_phrases", [])
                        )
                        # Also update the extra fields manually
                        p_store = self._orchestrator.memory.procedural
                        pm = p_store.get_by_task(recipe.get("task_name", task_name))
                        if pm:
                            pm.app_category = recipe.get("app_category", "other")
                            pm.app_name = recipe.get("app_name", "unknown")
                            pm.trigger_phrases = recipe.get("trigger_phrases", [])
                            pm.variables = recipe.get("variables", [])
                            p_store.store(pm)
                        return f"Successfully learned and saved recipe for '{task_name}'!"
                    except Exception as e:
                        logger.error("Failed to parse recipe JSON: %s", e)
                        return f"I recorded the steps, but couldn't finalize the recipe. {e}"
            return "Teach Mode OFF. Recipe recorded but LLM is not available to generalize it."

        if self._orchestrator is None:
            self._init_orchestrator()
            if self._orchestrator is None:
                return self._fallback_response(text)

        orch = self._orchestrator
        intent = self._detect_intent(text)

        # Route to appropriate module based on intent
        if intent == "memory_retrieval":
            return self._handle_memory_query(text, orch)
        elif intent == "system_hardware" or intent == "system_software" or intent == "system_diagnostics":
            return self._handle_system_query(text, orch, intent)
        elif intent == "research":
            return self._handle_research_query(text, orch)
        elif intent == "vision":
            return self._handle_vision_query(text, orch)
        elif intent == "agent":
            return self._handle_agent_query(text, orch)
        elif intent == "computer_use":
            return self._handle_computer_use_query(text, orch)
        else:
            return self._handle_general_query(text, orch)

    def _detect_intent(self, text: str) -> str:
        from moso_ui.responses import detect_intent
        return detect_intent(text)

    # ----- Module-specific handlers -----

    def _handle_memory_query(self, text: str, orch: Orchestrator) -> str:
        self._update_state(OrbState.ANALYZING)
        if orch.memory is None:
            return "Memory engine is not available right now."
        try:
            context = orch.memory.build_context(text, owner_id="default")
            if not context:
                return "I don't have any relevant memories about that."
            enriched = f"[Memory Context]\n{context}\n\n[Query]\n{text}"
            if orch.llm and self._orch_ready:
                resp = orch.llm.chat(enriched)
                if resp and resp.strip():
                    return resp
            return f"Here's what I found:\n{context}"
        except Exception as e:
            logger.error("Memory query failed: %s", e)
            return "I had trouble recalling that information."

    def _handle_system_query(self, text: str, orch: Orchestrator, intent: str) -> str:
        self._update_state(OrbState.ANALYZING)
        if orch.system_intelligence is None:
            return "System intelligence engine is not available right now."
        try:
            if intent == "system_hardware":
                result = orch.system_intelligence.get_hardware_summary()
            elif intent == "system_software":
                result = orch.system_intelligence.get_software_summary()
            elif intent == "system_diagnostics":
                result = orch.system_intelligence.get_diagnostics_summary()
            else:
                result = orch.system_intelligence.get_hardware_summary()
            self._store_in_memory(orch, "system_query", text, result)
            return result
        except Exception as e:
            logger.error("System query failed: %s", e)
            return "I couldn't retrieve that system information."

    def _handle_research_query(self, text: str, orch: Orchestrator) -> str:
        self._update_state(OrbState.ANALYZING)
        if orch.realtime is None:
            return self._fallback_with_llm(text, orch, "research")
        try:
            self._show_text("MOSO: Researching that topic...")
            response = orch.realtime.research_summary(text)
            self._store_in_memory(orch, "research", text, response)
            return response
        except Exception as e:
            logger.error("Research query failed: %s", e)
            return self._fallback_with_llm(text, orch, "research")

    def _handle_vision_query(self, text: str, orch: Orchestrator) -> str:
        self._update_state(OrbState.ANALYZING)
        if orch.vision is None:
            return "Vision engine is not available right now."
        try:
            result = orch.vision.capture_and_analyze()
            if result.get("error"):
                return result["error"]
            text_content = result.get("text", "")
            active_window = result.get("active_window", "")
            
            # Send to LLM to answer the user's question!
            if orch.llm:
                prompt = (f"The user is asking: '{text}'.\n\n"
                          f"Here is what is currently on their screen:\n"
                          f"- Active Window: {active_window}\n"
                          f"- Visible Text: {text_content[:1500]}\n\n"
                          f"Provide a natural, conversational response answering what they see or what app they are in. Only answer what they asked.")
                resp = orch.llm.chat(prompt)
                if resp and resp.strip():
                    self._store_in_memory(orch, "vision", text, resp)
                    return resp
            
            lines = []
            if active_window:
                lines.append(f"Active window: {active_window}")
            if text_content:
                lines.append(f"Screen text detected: {text_content[:300]}")
            resolution = result.get("resolution", (0, 0))
            lines.append(f"Screen resolution: {resolution[0]}x{resolution[1]}")
            combined = "\n".join(lines) or "I couldn't see anything on your screen."
            self._store_in_memory(orch, "vision", text, combined)
            return combined
        except Exception as e:
            logger.error("Vision query failed: %s", e)
            return "I couldn't analyze your screen right now."

    def _handle_agent_query(self, text: str, orch: Orchestrator) -> str:
        self._update_state(OrbState.ANALYZING)
        if orch.agents is None:
            return self._fallback_with_llm(text, orch, "agent")
        try:
            preview = orch.agents.preview_plan(text)
            self._show_text(f"MOSO: {preview}")
            self._update_state(OrbState.EXECUTING)
            summary = orch.agents.plan_and_execute(text, requester="owner")
            self._store_in_memory(orch, "agent_plan", text, str(summary))
            parts = []
            if summary.overall_status:
                parts.append(f"Status: {summary.overall_status.value}")
            for task_result in summary.task_results:
                status = task_result.get("status", "unknown")
                title = task_result.get("title", "task")
                result = task_result.get("result")
                if result:
                    parts.append(f"✓ {title}: {result[:100]}")
                else:
                    parts.append(f"• {title}: {status}")
            return "\n".join(parts) or "Plan execution completed."
        except Exception as e:
            logger.error("Agent query failed: %s", e)
            return f"I couldn't execute that plan: {e}"

    def _handle_computer_use_query(self, text: str, orch: Orchestrator) -> str:
        self._update_state(OrbState.ANALYZING)
        if orch.computer_use is None:
            return self._fallback_with_llm(text, orch, "computer_use")
        try:
            from moso_ui.responses import detect_command
            cmd = detect_command(text)
            
            tool_name = ""
            params = {}
            if cmd:
                tool_name, params = cmd

            if tool_name == "context_command":
                return self._handle_context_command(params, text)

            # If it's a generic computer use intent without a rigid rule, use VisionPlanner
            if tool_name == "computer_use" or not cmd:
                _load_desktop_intelligence()
                if _vision_planner is None:
                    return "Vision planner is not available."
                if orch.llm:
                    _vision_planner.set_llm(orch.llm)
                if orch.memory:
                    _vision_planner.set_memory(orch.memory)
                
                self._show_text("MOSO: Planning screen interaction...")
                self._update_state(OrbState.EXECUTING)
                plan = _vision_planner.plan_and_execute(text)
                return f"Plan executed:\n{plan.summary()}"

            action = params.get("action", "")
            if orch.tools is None:
                return "Tool engine is not available."

            if params.get("dry_run"):
                self._show_text(f"MOSO: Preview: Would execute {action}")
                return f"[DRY RUN] Would execute: {action} with {params}"

            self._update_state(OrbState.EXECUTING)

            # Risk check
            if orch.risk:
                allowed, report = orch.risk.check_and_block(tool_name, action, params)
                if not allowed:
                    risk_info = f"Risk: {report.max_level.value} — {report.risk.recommendation}" if report else "Blocked by risk engine"
                    self._show_text(f"MOSO: {risk_info}")
                    return risk_info

            from moso_core.tools.models import ToolRequest
            identity = self._get_identity()
            req = ToolRequest(tool_name=tool_name, parameters=params, requester="aura_ui")
            result = orch.tools.execute_tool(req, identity=identity, memory=orch.memory, resources=orch.resources)
            if result.success:
                self._store_in_memory(orch, "tool_execution", text, str(result.result))
                return self._format_result(req, result)
            return f"I ran into an issue: {result.error or 'Something went wrong.'}"
        except Exception as e:
            logger.error("Computer use query failed: %s", e)
            return f"I couldn't perform that action: {e}"

    def _handle_general_query(self, text: str, orch: Orchestrator) -> str:
        self._update_state(OrbState.THINKING)

        # Desktop intelligence path: pronoun resolution + vision planner
        _load_desktop_intelligence()
        if _desktop_memory and _vision_planner:
            resolved = _desktop_memory.resolve_command(text)
            try:
                plan = _vision_planner.create_plan(resolved)
                if plan and plan.steps:
                    self._update_state(OrbState.EXECUTING)
                    # Step-by-step status streaming
                    def _on_step(step):
                        idx = plan.steps.index(step) + 1
                        total = len(plan.steps)
                        self._show_text("MOSO: [%d/%d] %s" % (idx, total, step.description))
                    _vision_planner.set_step_callback(_on_step)
                    self._show_text("MOSO: Planning %d steps..." % len(plan.steps))
                    _vision_planner.execute_plan(plan)
                    _desktop_memory.save()
                    completed = sum(1 for s in plan.steps if s.status.value == "verified")
                    total = len(plan.steps)
                    if plan.failed:
                        return "Partially done (%d/%d steps): %s" % (completed, total, plan.failure_reason)
                    # Build result with per-step details
                    lines = ["Done! %d/%d steps completed." % (completed, total)]
                    for s in plan.steps:
                        icon = "ok" if s.status.value == "verified" else "!"
                        lines.append("  [%s] %s" % (icon, s.description))
                    # Add suggestions
                    if _desktop_memory:
                        suggestions = _desktop_memory.get_suggestions()
                        if suggestions:
                            lines.append("Suggestions: %s" % ", ".join(suggestions))
                    return "\n".join(lines)
            except Exception as e:
                logger.debug("Vision planner could not handle: %s, falling back to legacy", e)

        # Legacy fallback: rule-based + computer use agent
        result = self._try_command(text)
        if result:
            return result

        # Computer Use Agent path: multi-step tasks
        if orch and orch.computer_use:
            try:
                from moso_core.computer_use.agent import ComputerUseAgent
                agent = ComputerUseAgent(orch.computer_use)
                ctx = {"active_app": self._context.get_active_app()}
                agent_result = agent.execute(text, context=ctx)
                if agent_result:
                    self._context.set_app(ctx.get("active_app", ""), "computer_use", text[:50])
                    return agent_result
            except Exception as e:
                logger.debug("Agent could not handle: %s", e)

        # LLM path: only if no rule matched
        if self._orch_ready and orch.llm:
            try:
                context = self._conversation.build_context(text)
                if orch.memory:
                    try:
                        memory_context = orch.memory.build_context(text, owner_id="default")
                        if memory_context:
                            context = f"[Memory]\n{memory_context}\n\n{context}"
                    except Exception:
                        pass

                from moso_core.pipelines.text.pipeline import SYSTEM_PROMPT
                system_prompt = (
                    SYSTEM_PROMPT + "\n\n"
                    "You have access to these tools. When the user asks you to perform an action, "
                    "output a tool call as ```tool\n{\"tool\": \"name\", \"params\": {...}}\n```\n\n"
                    "Available tools:\n"
                    "- launch_application(app_name): Launch an app\n"
                    "- close_application(app_name): Close a running app\n"
                    "- list_running_applications(): List running apps\n"
                    "- search_web(query): Search the web\n"
                    "- open_url(url): Open a URL\n"
                    "- list_directory(path): List files\n"
                    "- read_file(path): Read a file\n"
                    "- run_command(command): Run a terminal command\n"
                    "- create_folder(path): Create a folder\n"
                    "- create_file(path, content): Create a file\n"
                    "- delete_file(path): Delete a file\n\n"
                    "You can also check system info (RAM, CPU, specs), research topics, "
                    "see the screen, and plan multi-step goals.\n\n"
                    "If no tool is needed, just respond conversationally."
                )

                resp = orch.llm.chat(context, system_prompt=system_prompt)
                if resp and resp.strip():
                    result = self._execute_llm_with_tools(resp, orch)
                    self._store_in_memory(orch, "conversation", text, result)
                    return result
            except Exception:
                pass

        return self._fallback_response(text)

    def _fallback_with_llm(self, text: str, orch: Orchestrator, intent: str) -> str:
        if self._orch_ready and orch.llm:
            try:
                context = self._conversation.build_context(text)
                resp = orch.llm.chat(f"[{intent} query] {context}")
                if resp and resp.strip():
                    return resp
            except Exception:
                pass
        result = self._try_command(text)
        if result:
            return result
        return self._fallback_response(text)

    def _handle_context_command(self, params: dict, text: str) -> str:
        app_name = params.get("app_name", "_active_")
        app_action = params.get("app_action", "")
        target = params.get("target", "")

        # Resolve "_active_" to the context's active app
        if app_name == "_active_":
            app_name = self._context.get_active_app()
            if not app_name:
                return "No active application. Open an app first (e.g., 'open Spotify')."

        # Normalize action aliases
        action_map = {
            "stop": "pause",
            "prev": "previous",
            "resume": "play",
        }
        app_action = action_map.get(app_action, app_action)

        # Get controller
        from moso_core.tools.app_controllers import get_controller
        controller = get_controller(app_name)

        if controller is None:
            # No specific controller — try to launch the app
            if app_action == "general":
                orch = self._orchestrator
                if orch and orch.tools:
                    from moso_core.tools.models import ToolRequest
                    req = ToolRequest(tool_name="app_tool",
                                      parameters={"action": "launch_application", "app_name": app_name},
                                      requester="aura_ui")
                    result = orch.tools.execute_tool(req, identity=self._get_identity())
                    if result.success:
                        self._context.set_app(app_name, "launch", "")
                        return self._format_result(req, result)
                    return result.error or f"Could not launch {app_name}."
                return f"No controller for '{app_name}'. Try 'open {app_name}' first."

            return f"No controller available for '{app_name}'."

        # Execute the action
        self._update_state(OrbState.EXECUTING)
        self._context.set_app(app_name, app_action, target)
        result = controller.handle(app_action, target)
        return result

    def _try_command(self, text: str) -> Optional[str]:
        from moso_ui.responses import detect_command
        cmd = detect_command(text)
        if cmd is None:
            return None
        tool_name, params = cmd

        # Context-aware routing: "in spotify play kindness playlist"
        if tool_name == "context_command":
            return self._handle_context_command(params, text)

        orch = self._orchestrator

        # If tools module is available, use it
        if orch is not None and orch.tools is not None:
            if orch.risk:
                self._update_state(OrbState.WARNING)
                allowed, report = orch.risk.check_and_block(tool_name, params.get("action", ""), params)
                if not allowed:
                    risk_info = f"Risk: {report.max_level.value} — {report.risk.recommendation}" if report else "Blocked by risk engine"
                    return risk_info

            self._update_state(OrbState.EXECUTING)
            from moso_core.tools.models import ToolRequest
            req = ToolRequest(tool_name=tool_name, parameters=params, requester="aura_ui")
            result = orch.tools.execute_tool(req, identity=self._get_identity(), memory=orch.memory, resources=orch.resources)
            if result.success:
                # Set context when launching an app
                if params.get("action") == "launch_application":
                    self._context.set_app(params.get("app_name", ""), "launch", "")
                self._store_in_memory(orch, "tool_execution", text, str(result.result))
                return self._format_result(req, result)
            return result.error or "Something went wrong."

        # Tools not loaded yet — use rule-based response
        action = params.get("action", "")
        if action == "launch_application":
            return f"I'd launch {params.get('app_name', 'it')} but the tool engine is still loading. Try again in a moment."
        if action == "close_application":
            return f"I'd close {params.get('app_name', 'it')} but tools are loading."
        if action == "search_web":
            return f"I'd search for that but tools are loading."
        from moso_ui.responses import chat_response
        return chat_response(text)

    def _execute_llm_with_tools(self, response: str, orch: Orchestrator) -> str:
        tool_call_pattern = r'```tool\n(.*?)\n```'
        match = re.search(tool_call_pattern, response, re.DOTALL)
        if not match:
            return response
        try:
            tool_spec = json.loads(match.group(1).strip())
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse tool call: %s", e)
            return response

        tool_name = tool_spec.get("tool")
        params = tool_spec.get("params", {})
        if not tool_name:
            return response

        clean_response = re.sub(r'```tool\n.*?\n```\n?', '', response, flags=re.DOTALL).strip()
        if orch.tools is None:
            return clean_response if clean_response else "I can't execute tools right now."

        if orch.risk:
            self._update_state(OrbState.WARNING)
            allowed, report = orch.risk.check_and_block(tool_name, params.get("action", ""), params)
            if not allowed:
                risk_info = f"Risk: {report.max_level.value} — {report.risk.recommendation}" if report else "Blocked"
                return f"{clean_response}\n\n{risk_info}" if clean_response else risk_info

        self._update_state(OrbState.EXECUTING)
        from moso_core.tools.models import ToolRequest
        action = params.get("action", "execute")
        req = ToolRequest(tool_name=tool_name, parameters=params, requester="aura_ui")
        result = orch.tools.execute_tool(req, identity=self._get_identity(), memory=orch.memory, resources=orch.resources)
        if result.success:
            result_text = self._format_result(req, result)
            self._store_in_memory(orch, "tool_execution", action, result_text)
            return f"{clean_response}\n\n{result_text}" if clean_response else result_text
        error_msg = result.error or "Something went wrong."
        return f"{clean_response}\n\nI ran into an issue: {error_msg}" if clean_response else f"Sorry, I couldn't do that: {error_msg}"

    def _store_in_memory(self, orch: Orchestrator, category: str, query: str, response: str):
        if orch.memory is None:
            return
        try:
            orch.memory.store_event(
                title=f"{category}: {query[:80]}",
                description=f"Query: {query[:200]}\nResponse: {response[:500]}",
                tags=[category, "aura_ui"],
                owner_id="default",
            )
        except Exception as e:
            logger.debug("Failed to store memory event: %s", e)

    # ----- Tool result formatting -----

    @staticmethod
    def _get_identity():
        class _OwnerIdentity:
            @staticmethod
            def get_identity_level():
                return "owner"
            @staticmethod
            def is_owner():
                return True
        return _OwnerIdentity()

    @staticmethod
    def _format_result(req, result) -> str:
        action = req.parameters.get("action", "")
        if action == "launch_application":
            r = result.result
            if isinstance(r, dict):
                name = r.get("matched_alias") or r.get("requested", "it")
                status = r.get("result", "")
                if status == "NOT_FOUND":
                    return f"Could not find '{r.get('requested', 'app')}' installed on this system."
                if "FAILED" in status:
                    return f"Failed to launch {name}: {status}"
                return f"Done! Launched {name}."
            return "Done! I launched %s." % req.parameters.get("app_name", "it")
        if action == "play_media":
            return "Done! Playing media." if result.result else "Done!"
        if action == "close_application":
            return "Closed %s." % req.parameters.get("app_name", "it")
        if action == "list_running_applications":
            apps = result.result
            if isinstance(apps, list) and apps:
                names = [a["name"] for a in apps[:10]]
                return "Running apps: %s" % ", ".join(names)
            return "No apps found."
        if action in ("search_web", "open_url"):
            return "Opened in your browser."
        if action == "list_directory":
            items = result.result
            if isinstance(items, list):
                names = [i.get("name", str(i)) for i in items[:15]]
                return "Files: %s" % ", ".join(names)
            return str(result.result)
        if action == "read_file":
            content = result.result
            if isinstance(content, str):
                return content[:300]
            return str(result.result)[:300]
        if action == "run_command":
            output = result.result
            if isinstance(output, str):
                return output[:300]
            return str(result.result)[:300]
        if action == "capture_screen":
            return "Screenshot captured."
        if action == "get_active_window":
            return f"Active window: {result.result}" if result.result else "No active window detected."
        return str(result.result)[:300] if result.result else "Done."

    # ----- Fallback -----

    def _fallback_response(self, text: str) -> str:
        from moso_ui.responses import chat_response
        fallback = chat_response(text)
        logger.info("Fallback response used for: %s", text[:50])
        return fallback

    # ----- TTS -----

    def _text_to_speech(self, text: str):
        def _speak():
            import asyncio
            import tempfile
            import os
            try:
                import edge_tts
            except ImportError:
                logger.error("edge-tts not installed")
                return

            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
            except ImportError:
                pygame = None

            async def _do_tts():
                # Split into sentences for pseudo-streaming if needed, but for now just speak the full string.
                # Since edge_tts generates a file quickly, the latency is much lower than pyttsx3 loading
                communicate = edge_tts.Communicate(text, "en-IN-NeerjaNeural", rate="+10%")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    temp_path = fp.name
                await communicate.save(temp_path)
                
                if pygame:
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        await asyncio.sleep(0.1)
                    pygame.mixer.music.unload()
                else:
                    # Fallback
                    os.system(f'start /wait /min "" "{temp_path}"')
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            try:
                asyncio.run(_do_tts())
            except Exception as e:
                logger.error("edge-tts playback error: %s", e)

        # Run TTS in a background thread so it doesn't block the UI
        self._executor.submit(_speak)

    # ----- Cleanup -----

    def shutdown(self):
        _load_desktop_intelligence()
        if _desktop_memory:
            _desktop_memory.save()
        self._executor.shutdown(wait=False)
        if self._orchestrator:
            try:
                if self._orchestrator.llm:
                    self._orchestrator.llm.stop()
                if self._orchestrator.memory:
                    self._orchestrator.memory.close()
            except Exception:
                pass
            self._orchestrator = None
        if self._tts_engine:
            try:
                self._tts_engine.stop()
            except Exception:
                pass
            self._tts_engine = None
        logger.info("VoiceInteraction shutdown complete")
