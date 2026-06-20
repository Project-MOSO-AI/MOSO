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
from moso_ui.states import OrbState

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


AUDIO_LEVEL_THRESHOLD = 0.005
WHISPER_SAMPLE_RATE = 16000


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
        self._state_callback: Optional[Callable] = None
        self._text_callback: Optional[Callable] = None
        self._input_callback: Optional[Callable] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._orchestrator: Optional[Orchestrator] = None
        self._conversation = ConversationManager()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="moso_audio")
        self._whisper_model = None
        self._device_sample_rate = WHISPER_SAMPLE_RATE
        self._orch_ready = False

        self._init_tts()
        self._init_whisper()

    # ----- Initialization -----

    def _init_whisper(self):
        if WHISPER_AVAILABLE:
            try:
                self._whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
                logger.info("Whisper model loaded (base, CPU, int8)")
            except Exception as e:
                logger.error("Whisper init failed: %s", e)
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
        except ImportError as e:
            logger.error("Orchestrator modules not available: %s", e)
            self._orch_ready = False
        except Exception as e:
            logger.error("Orchestrator init failed: %s", e)
            self._orch_ready = False

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
        for i, info in enumerate(sd.query_devices()):
            if info["max_input_channels"] > 0:
                sr = int(info["default_samplerate"]) if info.get("default_samplerate", 0) > 0 else WHISPER_SAMPLE_RATE
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
        mx = np.max(np.abs(audio))
        if mx < AUDIO_LEVEL_THRESHOLD:
            self._show_text("MOSO: I didn't hear anything. Type instead?")
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
        if WHISPER_AVAILABLE and self._whisper_model:
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
        self._conversation.add_message("user", text)
        self._show_text(f"You: {text}")
        response = self._generate_response(text)
        self._conversation.add_message("assistant", response)
        self._show_text(f"MOSO: {response}")
        self._update_state(OrbState.SPEAKING)
        self._text_to_speech(response)
        self._update_state(OrbState.IDLE)

    def _on_text_input(self, text: str):
        self._update_state(OrbState.THINKING)
        self._conversation.add_message("user", text)
        self._show_text(f"You: {text}")
        response = self._generate_response(text)
        self._conversation.add_message("assistant", response)
        self._show_text(f"MOSO: {response}")
        self._update_state(OrbState.SPEAKING)
        self._text_to_speech(response)
        self._update_state(OrbState.IDLE)

    def _generate_response(self, text: str) -> str:
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
            if cmd is None:
                return self._fallback_with_llm(text, orch, "computer_use")
            tool_name, params = cmd
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
        if not self._orch_ready or orch.llm is None:
            result = self._try_command(text)
            if result:
                return result
            return self._fallback_response(text)

        try:
            context = self._conversation.build_context(text)

            # Inject memory context if available
            if orch.memory:
                try:
                    memory_context = orch.memory.build_context(text, owner_id="default")
                    if memory_context:
                        context = f"[Memory]\n{memory_context}\n\n{context}"
                except Exception:
                    pass

            system_prompt = (
                "You are MOSO, a privacy-first local AI assistant. "
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
                "Examples:\n"
                "User: Open VLC\n"
                "Assistant: ```tool\n{\"tool\": \"app_tool\", \"params\": {\"action\": \"launch_application\", \"app_name\": \"vlc\"}}\n```\n"
                "Opening VLC now.\n\n"
                "If no tool is needed, just respond conversationally."
            )

            resp = orch.llm.chat(context, system_prompt=system_prompt)
            if resp and resp.strip():
                result = self._execute_llm_with_tools(resp, orch)
                self._store_in_memory(orch, "conversation", text, result)
                return result

            result = self._try_command(text)
            if result:
                return result
            return self._fallback_response(text)
        except Exception as e:
            logger.error("General query failed: %s", e)
            result = self._try_command(text)
            if result:
                return result
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

    def _try_command(self, text: str) -> Optional[str]:
        if self._orchestrator is None or self._orchestrator.tools is None:
            return None
        from moso_ui.responses import detect_command
        cmd = detect_command(text)
        if cmd is None:
            return None
        tool_name, params = cmd
        orch = self._orchestrator

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
            self._store_in_memory(orch, "tool_execution", text, str(result.result))
            return self._format_result(req, result)
        return result.error or "Something went wrong."

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
            return "Done! I launched %s." % req.parameters.get("app_name", "it")
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
        if not TTS_AVAILABLE or not self._tts_engine:
            return
        with self._tts_lock:
            try:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
            except Exception as e:
                logger.error("TTS error: %s", e)

    # ----- Cleanup -----

    def shutdown(self):
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
