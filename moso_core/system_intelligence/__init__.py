from moso_core.system_intelligence.models import (
    DiagnosticIssue,
    HardwareSummary,
    InventoryDiff,
    NetworkConfig,
    SecurityStatus,
    ServiceEntry,
    SoftwareEntry,
    SystemSnapshot,
)

try:
    from moso_core.system_intelligence.hardware import HardwareIntelligence
    from moso_core.system_intelligence.software import SoftwareIntelligence
    from moso_core.system_intelligence.network import NetworkIntelligence
    from moso_core.system_intelligence.storage import StorageIntelligence
    from moso_core.system_intelligence.security import SecurityIntelligence
    from moso_core.system_intelligence.diagnostics import DiagnosticsEngine
    from moso_core.system_intelligence.inventory import InventoryEngine
    from moso_core.system_intelligence.explainer import ExplainerEngine
    from moso_core.system_intelligence.manager import SystemIntelligenceManager

    SYSTEM_INTELLIGENCE_AVAILABLE = True
except ImportError:
    HardwareIntelligence = None  # noqa: F811
    SoftwareIntelligence = None  # noqa: F811
    NetworkIntelligence = None  # noqa: F811
    StorageIntelligence = None  # noqa: F811
    SecurityIntelligence = None  # noqa: F811
    DiagnosticsEngine = None  # noqa: F811
    InventoryEngine = None  # noqa: F811
    ExplainerEngine = None  # noqa: F811
    SystemIntelligenceManager = None  # noqa: F811
    SYSTEM_INTELLIGENCE_AVAILABLE = False

__all__ = [
    "HardwareSummary",
    "SoftwareEntry",
    "ServiceEntry",
    "NetworkConfig",
    "SecurityStatus",
    "DiagnosticIssue",
    "SystemSnapshot",
    "InventoryDiff",
    "HardwareIntelligence",
    "SoftwareIntelligence",
    "NetworkIntelligence",
    "StorageIntelligence",
    "SecurityIntelligence",
    "DiagnosticsEngine",
    "InventoryEngine",
    "ExplainerEngine",
    "SystemIntelligenceManager",
    "SYSTEM_INTELLIGENCE_AVAILABLE",
]
