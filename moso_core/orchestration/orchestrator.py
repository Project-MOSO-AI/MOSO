import logging
from enum import Enum
from typing import Iterator, Optional, Type, Union

from typing import TYPE_CHECKING, Optional

from moso_core.inference.base import InferenceConfig, ModelBackend
try:
    from moso_core.inference.llama_cpp.backend import LlamaCPPBackend
except ImportError:
    LlamaCPPBackend = None  # noqa: F811
from moso_core.pipelines.base import Pipeline, PipelineResult
from moso_core.pipelines.text.pipeline import TextPipeline
from moso_core.safety.guardrails import OutputGuard, PromptGuard

if TYPE_CHECKING:
    from moso_core.agents.manager import AgentManager
    from moso_core.computer_use.automation import AutomationEngine
    from moso_core.llm.manager import LLMManager
    from moso_core.memory.manager import MemoryManager
    from moso_core.resources.manager import ResourceManager
    from moso_core.system_intelligence.manager import SystemIntelligenceManager
    from moso_core.tools.registry import ToolRegistry
    from moso_core.vision.manager import VisionManager
    from moso_core.voice.pipeline import VoicePipeline
    from moso_core.identity.verifier import IdentityVerifier

logger = logging.getLogger(__name__)

BACKEND_REGISTRY: dict[str, Type[ModelBackend]] = {}

try:
    from moso_core.inference.llama_cpp.backend import LlamaCPPBackend
    BACKEND_REGISTRY["llama"] = LlamaCPPBackend
except ImportError:
    pass

try:
    from moso_core.inference.onnx_runtime.backend import OnnxRuntimeBackend
    BACKEND_REGISTRY["onnx"] = OnnxRuntimeBackend
except ImportError:
    pass


def register_backend(name: str, backend_cls: Type[ModelBackend]) -> None:
    BACKEND_REGISTRY[name] = backend_cls


class Modality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    MULTIMODAL = "multimodal"
    REASONING = "reasoning"


class Orchestrator:
    def __init__(
        self,
        config: InferenceConfig,
        system_prompt: Optional[str] = None,
        enable_safety: bool = True,
        backend: Union[str, Type[ModelBackend], ModelBackend, None] = None,
    ):
        self._config = config
        self._backend: Optional[ModelBackend] = None
        self._backend_source = backend
        self._pipelines: dict[Modality, Pipeline] = {}
        self._prompt_guard = PromptGuard() if enable_safety else None
        self._output_guard = OutputGuard() if enable_safety else None

        self._text_pipeline = TextPipeline(
            backend=self._get_or_create_backend(),
            system_prompt=system_prompt or "You are M0S0, a privacy-first, local-first adaptive AI assistant.",
        )
        self._pipelines[Modality.TEXT] = self._text_pipeline

        self._voice_pipeline = None
        self._identity_verifier = None
        self._memory: Optional[MemoryManager] = None
        self._resources: Optional[ResourceManager] = None
        self._tool_registry: Optional[ToolRegistry] = None
        self._agent_manager: Optional[AgentManager] = None
        self._computer_use: Optional[AutomationEngine] = None
        self._vision: Optional[VisionManager] = None
        self._system_intelligence: Optional[SystemIntelligenceManager] = None
        self._llm: Optional[LLMManager] = None

    def process(self, prompt: str, modality: Modality = Modality.TEXT, **kwargs) -> PipelineResult:
        if self._prompt_guard:
            guard_result = self._prompt_guard.check(prompt)
            if not guard_result.allowed:
                logger.warning("Prompt blocked: %s", guard_result.reason)
                return PipelineResult(
                    text=f"I cannot process that request. {guard_result.reason}",
                    generation=None,
                )

        owner_id = None
        if self._identity_verifier:
            identity = self._identity_verifier.verify(text=prompt)
            if not identity.verified and modality == Modality.VOICE:
                logger.info("Voice processed with identity: %.1f%%", identity.confidence)
            if identity.session and identity.session.current_user:
                owner_id = identity.session.current_user

        if self._memory and owner_id:
            context = self._memory.build_context(prompt, owner_id=owner_id)
            if context:
                enriched = f"[Memory]\n{context}\n\n[Query]\n{prompt}"
                logger.debug("Memory context injected for %s", owner_id)
            else:
                enriched = prompt
        else:
            enriched = prompt

        pipeline = self._resolve_pipeline(modality)
        result = pipeline.run(enriched, **kwargs)

        if self._memory:
            self._memory.store_event(
                title=f"Query: {prompt[:80]}",
                description=prompt,
                tags=["conversation"],
                owner_id=owner_id or "default",
            )

        if self._output_guard:
            result = self._output_guard.sanitize(result)

        return result

    def process_stream(
        self, prompt: str, modality: Modality = Modality.TEXT, **kwargs
    ) -> Iterator[str]:
        if self._prompt_guard:
            guard_result = self._prompt_guard.check(prompt)
            if not guard_result.allowed:
                yield f"I cannot process that request. {guard_result.reason}"
                return

        if self._identity_verifier:
            self._identity_verifier.verify(text=prompt)

        pipeline = self._resolve_pipeline(modality)
        yield from pipeline.run_stream(prompt, **kwargs)

    def enable_voice(
        self,
        stt_model=None,
        tts_model=None,
        speaker_verifier=None,
        audio_config=None,
    ) -> None:
        from moso_core.voice.pipeline import VoicePipeline
        from moso_core.voice.input import AudioStream
        from moso_core.voice.stt import WhisperSTT
        from moso_core.voice.tts import PiperTTS
        from moso_core.voice.speaker import SpeakerVerifier
        from moso_core.voice.models import AudioConfig

        self._voice_pipeline = VoicePipeline(
            backend=self._get_or_create_backend(),
            audio_config=audio_config or AudioConfig(),
            stt_model=stt_model or WhisperSTT(),
            tts_model=tts_model or PiperTTS(),
            speaker_verifier=speaker_verifier or SpeakerVerifier(),
            system_prompt=self._text_pipeline._system_prompt,
        )
        self._pipelines[Modality.VOICE] = self._voice_pipeline
        logger.info("Voice pipeline enabled")

        self._init_identity()

    def _init_identity(self) -> None:
        try:
            from moso_core.identity.verifier import IdentityVerifier
            self._identity_verifier = IdentityVerifier()
            self._identity_verifier.load_models()
            logger.info("Identity engine integrated with orchestrator")
        except Exception as e:
            logger.warning("Identity engine not available: %s", e)

    def enable_identity(
        self,
        voice_verifier=None,
        anti_spoof=None,
        behavior=None,
        device=None,
        historical=None,
    ) -> None:
        from moso_core.identity.verifier import IdentityVerifier

        self._identity_verifier = IdentityVerifier(
            voice=voice_verifier,
            anti_spoof=anti_spoof,
            behavior=behavior,
            device=device,
            historical=historical,
        )
        self._identity_verifier.load_models()
        logger.info("Identity engine enabled with custom components")

    def process_voice(self, audio, sample_rate: int = 16000):
        if self._voice_pipeline is None:
            raise RuntimeError(
                "Voice pipeline not enabled. Call enable_voice() first."
            )
        return self._voice_pipeline.process_voice(audio, sample_rate)

    def listen_and_respond(self, audio_stream=None):
        if self._voice_pipeline is None:
            raise RuntimeError(
                "Voice pipeline not enabled. Call enable_voice() first."
            )
        return self._voice_pipeline.listen_and_respond(audio_stream)

    @property
    def voice_pipeline(self):
        return self._voice_pipeline

    @property
    def identity_verifier(self):
        return self._identity_verifier

    def enable_resources(self) -> None:
        try:
            from moso_core.resources.manager import ResourceManager
            self._resources = ResourceManager()
            logger.info("Resource manager enabled")
        except Exception as e:
            logger.warning("Resource manager not available: %s", e)

    @property
    def resources(self) -> Optional[ResourceManager]:
        return self._resources

    def enable_memory(self, db_path: Optional[str] = None) -> None:
        try:
            from moso_core.memory.manager import MemoryManager
            self._memory = MemoryManager(db_path=db_path)
            logger.info("Memory engine enabled at %s", db_path or "default location")
        except Exception as e:
            logger.warning("Memory engine not available: %s", e)

    def enable_tools(self) -> None:
        try:
            from moso_core.tools.file_tool import FileTool
            from moso_core.tools.app_tool import AppTool
            from moso_core.tools.browser_tool import BrowserTool
            from moso_core.tools.terminal_tool import TerminalTool
            from moso_core.tools.registry import ToolRegistry

            self._tool_registry = ToolRegistry()
            self._tool_registry.register_tool(FileTool())
            self._tool_registry.register_tool(AppTool())
            self._tool_registry.register_tool(BrowserTool())
            self._tool_registry.register_tool(TerminalTool())
            logger.info("Tool engine enabled with %d tools", len(self._tool_registry.list_tools()))
        except Exception as e:
            logger.warning("Tool engine not available: %s", e)

    @property
    def tools(self) -> Optional[ToolRegistry]:
        return self._tool_registry

    def enable_agents(self) -> None:
        try:
            from moso_core.agents.manager import AgentManager
            self._agent_manager = AgentManager(
                tool_registry=self._tool_registry,
                identity=self._identity_verifier,
                memory=self._memory,
                resources=self._resources,
                automation_engine=self._computer_use,
            )
            logger.info("Agent planner enabled (computer_use routing: %s)", self._computer_use is not None)
        except Exception as e:
            logger.warning("Agent planner not available: %s", e)

    @property
    def agents(self) -> Optional[AgentManager]:
        return self._agent_manager

    def enable_computer_use(self) -> None:
        try:
            from moso_core.computer_use.automation import AutomationEngine
            self._computer_use = AutomationEngine(
                identity=self._identity_verifier,
                memory=self._memory,
                resources=self._resources,
            )
            logger.info("Computer use engine enabled")
        except Exception as e:
            logger.warning("Computer use engine not available: %s", e)
        if self._agent_manager is not None:
            self._agent_manager._executor._automation_engine = self._computer_use
            logger.info("Reconnected computer_use to existing agent manager")

    @property
    def computer_use(self) -> Optional[AutomationEngine]:
        return self._computer_use

    def enable_vision(self) -> None:
        try:
            from moso_core.vision.manager import VisionManager
            self._vision = VisionManager(
                identity=self._identity_verifier,
                memory=self._memory,
                resources=self._resources,
            )
            logger.info("Vision engine enabled")
        except Exception as e:
            logger.warning("Vision engine not available: %s", e)

    @property
    def vision(self) -> Optional[VisionManager]:
        return self._vision

    def enable_system_intelligence(self) -> None:
        try:
            from moso_core.system_intelligence.manager import SystemIntelligenceManager
            self._system_intelligence = SystemIntelligenceManager(
                identity=self._identity_verifier,
                memory=self._memory,
                resources=self._resources,
            )
            logger.info("System intelligence engine enabled")
        except Exception as e:
            logger.warning("System intelligence engine not available: %s", e)

    @property
    def system_intelligence(self) -> Optional[SystemIntelligenceManager]:
        return self._system_intelligence

    def enable_llm(self, model_path: str = "", n_ctx: int = 2048, server_port: int = 8081) -> None:
        try:
            from moso_core.llm.models import LLMConfig
            from moso_core.llm.manager import LLMManager
            config = LLMConfig(
                model_path=model_path,
                n_ctx=n_ctx,
                server_port=server_port,
            )
            self._llm = LLMManager(config)
            logger.info("LLM engine enabled (model: %s)", model_path or "not set")
        except Exception as e:
            logger.warning("LLM engine not available: %s", e)

    @property
    def llm(self) -> Optional[LLMManager]:
        return self._llm

    def llm_complete(self, prompt: str, system_prompt: str = "") -> str:
        if self._llm is None:
            return "LLM engine not enabled. Call enable_llm() first."
        resp = self._llm.complete(prompt, system_prompt=system_prompt)
        return resp.text

    def get_identity_confidence(self) -> float:
        if self._identity_verifier is None:
            return 0.0
        return self._identity_verifier.get_confidence()

    def get_identity_level(self):
        if self._identity_verifier is None:
            return None
        return self._identity_verifier.get_identity_level()

    def is_owner(self) -> bool:
        if self._identity_verifier is None:
            return False
        return self._identity_verifier.is_owner()

    @property
    def memory(self) -> Optional[MemoryManager]:
        return self._memory

    def reset_conversation(self, modality: Modality = Modality.TEXT) -> None:
        pipeline = self._pipelines.get(modality)
        if pipeline:
            pipeline.reset()

    def load(self) -> None:
        self._get_or_create_backend().load()

    def unload(self) -> None:
        if self._backend is not None:
            self._backend.unload()

    @property
    def backend(self) -> ModelBackend:
        return self._get_or_create_backend()

    @property
    def text_pipeline(self) -> TextPipeline:
        return self._text_pipeline

    def _resolve_pipeline(self, modality: Modality) -> Pipeline:
        if modality not in self._pipelines:
            supported = list(self._pipelines.keys())
            raise ValueError(
                f"Unsupported modality '{modality.value}'. "
                f"Supported: {[m.value for m in supported]}"
            )
        return self._pipelines[modality]

    def _get_or_create_backend(self) -> ModelBackend:
        if self._backend is not None:
            return self._backend

        if isinstance(self._backend_source, ModelBackend):
            self._backend = self._backend_source
        elif isinstance(self._backend_source, str):
            cls = BACKEND_REGISTRY.get(self._backend_source)
            if cls is None:
                raise ValueError(
                    f"Unknown backend '{self._backend_source}'. "
                    f"Available: {list(BACKEND_REGISTRY.keys())}"
                )
            self._backend = cls(self._config)
        elif isinstance(self._backend_source, type) and issubclass(self._backend_source, ModelBackend):
            self._backend = self._backend_source(self._config)
        else:
            if BACKEND_REGISTRY:
                cls = next(iter(BACKEND_REGISTRY.values()))
                self._backend = cls(self._config)
            else:
                raise ValueError("No model backends available. Install llama-cpp-python or onnxruntime.")

        return self._backend

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, *args):
        self.unload()
