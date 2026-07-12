"""MOSO Desktop Intelligence — perception, world model, planner, verification, smart controllers, memory."""
from moso_core.desktop.perception import DesktopPerceiver, DesktopState, UIElement
from moso_core.desktop.world_model import WorldModel, WorldState
from moso_core.desktop.vision_planner import VisionPlanner
from moso_core.desktop.verifier import ActionVerifier, VerificationResult
from moso_core.desktop.smart_controllers import SmartController, get_smart_controller, SMART_CONTROLLERS
from moso_core.desktop.desktop_memory import DesktopMemory, MemoryRecord
from moso_core.desktop.action_executor import ActionExecutor

__all__ = [
    "DesktopPerceiver", "DesktopState", "UIElement",
    "WorldModel", "WorldState",
    "VisionPlanner",
    "ActionVerifier", "VerificationResult",
    "SmartController", "get_smart_controller", "SMART_CONTROLLERS",
    "DesktopMemory", "MemoryRecord",
    "ActionExecutor",
]
