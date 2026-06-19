from __future__ import annotations

import os
import tempfile
import json
from unittest.mock import MagicMock, patch

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


class TestModels:
    def test_hardware_summary_defaults(self):
        hw = HardwareSummary(
            cpu_model="Intel i7-12700H", cpu_architecture="AMD64",
            cpu_cores=14, cpu_threads=20, cpu_frequency_mhz=2700.0,
            gpu_model="NVIDIA RTX 3060", gpu_vram_mb=6144,
            motherboard="ASUS ROG Z690", ram_total_gb=16.0,
            ram_form_factor="SODIMM", os_version="Windows 11 23H2",
        )
        d = hw.to_dict()
        assert d["cpu_model"] == "Intel i7-12700H"
        assert d["gpu_vram_mb"] == 6144
        assert "14C/20T" in str(hw)

    def test_software_entry(self):
        sw = SoftwareEntry(name="VLC", version="3.0.20",
                           publisher="VideoLAN", install_date="20250301",
                           install_location="C:\\Program Files\\VLC")
        d = sw.to_dict()
        assert d["name"] == "VLC"
        assert d["version"] == "3.0.20"
        assert "VLC 3.0.20" == str(sw)

    def test_service_entry(self):
        sv = ServiceEntry(name="Spooler", display_name="Print Spooler",
                          status="RUNNING", start_type="AUTO_START")
        assert sv.name == "Spooler"
        assert sv.status == "RUNNING"
        assert "Print Spooler (RUNNING)" == str(sv)

    def test_network_config(self):
        nc = NetworkConfig(
            adapters=[{"name": "Wi-Fi", "ip": "192.168.1.5", "isup": True}],
            dns_servers=["8.8.8.8", "1.1.1.1"],
            vpn_active=False, active_connections=42, listening_ports=[80, 443],
        )
        d = nc.to_dict()
        assert d["active_connections"] == 42
        assert d["listening_ports"] == [80, 443]
        assert "VPN: inactive" in str(nc)

    def test_security_status(self):
        sec = SecurityStatus(
            firewall_enabled=True, firewall_profile="Domain",
            antivirus_active=True, antivirus_name="Windows Defender",
            pending_updates=3, suspicious_startup_entries=["CryptoMiner.exe"],
        )
        d = sec.to_dict()
        assert d["firewall_enabled"] is True
        assert d["pending_updates"] == 3
        assert "ON" in str(sec)
        assert "CryptoMiner.exe" in str(sec)

    def test_diagnostic_issue(self):
        di = DiagnosticIssue(
            component="RAM", issue="Usage at 95%",
            severity="warning",
            explanation="RAM is nearly full.",
            suggestion="Close some apps.",
        )
        assert di.severity == "warning"
        assert "[WARN]" in str(di)

    def test_diagnostic_issue_critical(self):
        di = DiagnosticIssue(
            component="Disk", issue="Full",
            severity="critical",
            explanation="Drive is completely full.",
            suggestion="Delete files.",
        )
        assert "[CRIT]" in str(di)

    def test_system_snapshot(self):
        hw = HardwareSummary("CPU", "x64", 4, 8, 2400.0, "GPU", 2048,
                             "MB", 8.0, "DIMM", "Win10")
        sw = [SoftwareEntry("App1", "1.0", "Pub", "", "")]
        sv = [ServiceEntry("Svc1", "Service 1", "RUNNING", "AUTO")]
        net = NetworkConfig([], [], False, 0, [])
        sec = SecurityStatus(True, "", True, "AV", 0, [])
        snap = SystemSnapshot("", hw, sw, sv, net, sec)
        assert snap.timestamp
        d = snap.to_dict()
        assert d["hardware"]["cpu_model"] == "CPU"
        assert len(d["software"]) == 1

    def test_inventory_diff_no_changes(self):
        diff = InventoryDiff(
            timestamp="now", new_software=[], removed_software=[],
            hardware_changed=False, hardware_before=None, hardware_after=None,
            new_services=[], removed_services=[],
        )
        assert diff.has_changes() is False
        assert "No changes" in str(diff)

    def test_inventory_diff_with_changes(self):
        sw = SoftwareEntry("NewApp", "2.0", "Pub", "", "")
        diff = InventoryDiff(
            timestamp="now", new_software=[sw], removed_software=[],
            hardware_changed=False, hardware_before=None, hardware_after=None,
            new_services=[], removed_services=[],
        )
        assert diff.has_changes() is True
        assert "New apps" in str(diff)


class TestHardwareIntelligence:
    def test_get_summary_returns_valid(self):
        from moso_core.system_intelligence.hardware import HardwareIntelligence
        hi = HardwareIntelligence()
        hw = hi.get_summary()
        assert isinstance(hw, HardwareSummary)
        assert hw.cpu_model
        assert hw.ram_total_gb > 0

    def test_get_cpu_model(self):
        from moso_core.system_intelligence.hardware import HardwareIntelligence
        model = HardwareIntelligence._get_cpu_model()
        assert model and len(model) > 0

    def test_get_cpu_cores(self):
        from moso_core.system_intelligence.hardware import HardwareIntelligence
        cores = HardwareIntelligence._get_cpu_cores()
        assert cores > 0

    def test_get_gpu_info_fallback(self):
        from moso_core.system_intelligence.hardware import HardwareIntelligence
        gpu, vram = HardwareIntelligence._get_gpu_info()
        assert isinstance(gpu, str)
        assert isinstance(vram, int)


class TestSoftwareIntelligence:
    def test_get_installed_apps(self):
        from moso_core.system_intelligence.software import SoftwareIntelligence
        si = SoftwareIntelligence()
        apps = si.get_installed_apps()
        assert isinstance(apps, list)
        if apps:
            assert isinstance(apps[0], SoftwareEntry)

    def test_get_services(self):
        from moso_core.system_intelligence.software import SoftwareIntelligence
        si = SoftwareIntelligence()
        services = si.get_services()
        assert isinstance(services, list)
        if services:
            assert isinstance(services[0], ServiceEntry)

    def test_get_running_process_count(self):
        from moso_core.system_intelligence.software import SoftwareIntelligence
        si = SoftwareIntelligence()
        count = si.get_running_process_count()
        assert count > 0

    def test_get_startup_items(self):
        from moso_core.system_intelligence.software import SoftwareIntelligence
        si = SoftwareIntelligence()
        items = si.get_startup_items()
        assert isinstance(items, list)


class TestNetworkIntelligence:
    def test_get_config(self):
        from moso_core.system_intelligence.network import NetworkIntelligence
        ni = NetworkIntelligence()
        config = ni.get_config()
        assert isinstance(config, NetworkConfig)
        assert isinstance(config.adapters, list)
        assert isinstance(config.dns_servers, list)
        assert isinstance(config.listening_ports, list)

    def test_get_dns_servers(self):
        from moso_core.system_intelligence.network import NetworkIntelligence
        dns = NetworkIntelligence._get_dns_servers()
        assert isinstance(dns, list)

    def test_detect_vpn(self):
        from moso_core.system_intelligence.network import NetworkIntelligence
        vpn = NetworkIntelligence._detect_vpn()
        assert isinstance(vpn, bool)


class TestSecurityIntelligence:
    def test_get_status(self):
        from moso_core.system_intelligence.security import SecurityIntelligence
        si = SecurityIntelligence()
        status = si.get_status()
        assert isinstance(status, SecurityStatus)
        assert isinstance(status.firewall_enabled, bool)
        assert isinstance(status.antivirus_active, bool)


class TestStorageIntelligence:
    def test_get_storage_details(self):
        from moso_core.system_intelligence.storage import StorageIntelligence
        si = StorageIntelligence()
        details = si.get_storage_details()
        assert isinstance(details, list)

    def test_find_large_files(self):
        from moso_core.system_intelligence.storage import StorageIntelligence
        si = StorageIntelligence()
        files = si.find_large_files(path=os.path.expanduser("~"), min_mb=100, top_n=3)
        assert isinstance(files, list)

    def test_find_large_folders(self):
        from moso_core.system_intelligence.storage import StorageIntelligence
        si = StorageIntelligence()
        folders = si.find_large_folders(path=os.path.dirname(os.path.abspath(__file__)), top_n=3)
        assert isinstance(folders, list)

    def test_get_drive_health(self):
        from moso_core.system_intelligence.storage import StorageIntelligence
        si = StorageIntelligence()
        drives = si.get_drive_health()
        assert isinstance(drives, list)


class TestDiagnosticsEngine:
    def test_run_full_diagnostics(self):
        from moso_core.system_intelligence.diagnostics import DiagnosticsEngine
        de = DiagnosticsEngine()
        issues = de.run_full_diagnostics()
        assert isinstance(issues, list)
        for issue in issues:
            assert isinstance(issue, DiagnosticIssue)

    def test_run_performance_check_with_status(self):
        from moso_core.system_intelligence.diagnostics import DiagnosticsEngine
        mock_resources = MagicMock()
        mock_status = MagicMock()
        mock_status.cpu.usage_percent = 50.0
        mock_status.ram.percent = 60.0
        mock_status.battery.percent = 100.0
        mock_status.battery.plugged_in = True
        mock_resources.get_system_status.return_value = mock_status
        de = DiagnosticsEngine(resources=mock_resources)
        issues = de.run_performance_check()
        assert isinstance(issues, list)

    def test_run_performance_check_high_usage(self):
        from moso_core.system_intelligence.diagnostics import DiagnosticsEngine
        mock_resources = MagicMock()
        mock_status = MagicMock()
        mock_status.cpu.usage_percent = 95.0
        mock_status.ram.percent = 92.0
        mock_status.battery.percent = 15.0
        mock_status.battery.plugged_in = False
        mock_resources.get_system_status.return_value = mock_status
        de = DiagnosticsEngine(resources=mock_resources)
        issues = de.run_performance_check()
        assert len(issues) >= 2

    def test_run_storage_check_high(self):
        from moso_core.system_intelligence.diagnostics import DiagnosticsEngine
        mock_storage = MagicMock()
        mock_detail = MagicMock()
        mock_detail.mount_point = "C:"
        mock_detail.percent = 96.0
        mock_detail.free = 1 * (1024 ** 3)
        mock_detail.total = 256 * (1024 ** 3)
        mock_storage.get_storage_details.return_value = [mock_detail]
        de = DiagnosticsEngine(storage=mock_storage)
        issues = de.run_storage_check()
        assert len(issues) >= 1

    def test_run_network_check_disconnected(self):
        from moso_core.system_intelligence.diagnostics import DiagnosticsEngine
        mock_network = MagicMock()
        mock_config = MagicMock()
        mock_config.adapters = [{"name": "Wi-Fi", "isup": False, "addresses": []}]
        mock_network.get_config.return_value = mock_config
        de = DiagnosticsEngine(network=mock_network)
        issues = de.run_network_check()
        assert len(issues) >= 1

    def test_run_security_check(self):
        from moso_core.system_intelligence.diagnostics import DiagnosticsEngine
        mock_security = MagicMock()
        mock_sec = MagicMock()
        mock_sec.firewall_enabled = False
        mock_sec.antivirus_active = False
        mock_sec.antivirus_name = "None"
        mock_sec.pending_updates = 15
        mock_sec.suspicious_startup_entries = ["Malware.exe"]
        mock_security.get_status.return_value = mock_sec
        de = DiagnosticsEngine(security=mock_security)
        issues = de.run_security_check()
        assert len(issues) >= 3


class TestInventoryEngine:
    def test_capture_and_compare(self):
        from moso_core.system_intelligence.inventory import InventoryEngine
        mock_hw = MagicMock()
        mock_hw.get_summary.return_value = HardwareSummary(
            "CPU", "x64", 4, 8, 2400.0, "GPU", 2048, "MB", 8.0, "DIMM", "Win10",
        )
        mock_sw = MagicMock()
        mock_sw.get_installed_apps.return_value = [
            SoftwareEntry("App1", "1.0", "Pub", "", ""),
        ]
        mock_sw.get_services.return_value = [
            ServiceEntry("Svc1", "Service 1", "RUNNING", "AUTO"),
        ]
        mock_net = MagicMock()
        mock_net.get_config.return_value = NetworkConfig([], [], False, 0, [])
        mock_sec = MagicMock()
        mock_sec.get_status.return_value = SecurityStatus(True, "", True, "Defender", 0, [])

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            ie = InventoryEngine(
                hardware=mock_hw, software=mock_sw,
                network=mock_net, security=mock_sec, db_path=db_path,
            )

            ts1 = ie.capture_snapshot()
            assert ts1 is not None

            mock_sw.get_installed_apps.return_value = [
                SoftwareEntry("App1", "1.0", "Pub", "", ""),
                SoftwareEntry("App2", "2.0", "Pub2", "", ""),
            ]
            mock_sw.get_services.return_value = [
                ServiceEntry("Svc1", "Service 1", "RUNNING", "AUTO"),
                ServiceEntry("Svc2", "Service 2", "STOPPED", "DEMAND"),
            ]

            ts2 = ie.capture_snapshot()
            assert ts2 is not None

            diff = ie.compare_with_last_snapshot()
            assert diff is not None
            assert diff.has_changes() is True
            assert len(diff.new_software) >= 1
        finally:
            try:
                os.unlink(db_path)
            except (OSError, PermissionError):
                pass

    def test_no_previous_snapshot(self):
        from moso_core.system_intelligence.inventory import InventoryEngine
        mock_hw = MagicMock()
        mock_hw.get_summary.return_value = HardwareSummary(
            "CPU", "x64", 4, 8, 2400.0, "GPU", 2048, "MB", 8.0, "DIMM", "Win10",
        )
        mock_sw = MagicMock()
        mock_sw.get_installed_apps.return_value = []
        mock_sw.get_services.return_value = []
        mock_net = MagicMock()
        mock_net.get_config.return_value = NetworkConfig([], [], False, 0, [])
        mock_sec = MagicMock()
        mock_sec.get_status.return_value = SecurityStatus(True, "", True, "Defender", 0, [])

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            ie = InventoryEngine(
                hardware=mock_hw, software=mock_sw,
                network=mock_net, security=mock_sec, db_path=db_path,
            )
            ie.capture_snapshot()
            diff = ie.compare_with_last_snapshot()
            assert diff is None or diff.has_changes() is False
        finally:
            try:
                os.unlink(db_path)
            except (OSError, PermissionError):
                pass

    def test_list_snapshots(self):
        from moso_core.system_intelligence.inventory import InventoryEngine
        mock_hw = MagicMock()
        mock_hw.get_summary.return_value = HardwareSummary(
            "CPU", "x64", 4, 8, 2400.0, "GPU", 2048, "MB", 8.0, "DIMM", "Win10",
        )
        mock_sw = MagicMock()
        mock_sw.get_installed_apps.return_value = []
        mock_sw.get_services.return_value = []
        mock_net = MagicMock()
        mock_net.get_config.return_value = NetworkConfig([], [], False, 0, [])
        mock_sec = MagicMock()
        mock_sec.get_status.return_value = SecurityStatus(True, "", True, "Defender", 0, [])

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            ie = InventoryEngine(
                hardware=mock_hw, software=mock_sw,
                network=mock_net, security=mock_sec, db_path=db_path,
            )
            ie.capture_snapshot()
            ie.capture_snapshot()
            snapshots = ie.list_snapshots(limit=5)
            assert len(snapshots) == 2
        finally:
            try:
                os.unlink(db_path)
            except (OSError, PermissionError):
                pass


class TestExplainerEngine:
    def test_explain_cpu(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_hw = MagicMock()
        mock_hw.get_summary.return_value = HardwareSummary(
            "Intel i7", "x64", 8, 16, 3200.0, "RTX 3060", 6144,
            "ASUS", 32.0, "DIMM", "Windows 11",
        )
        ee = ExplainerEngine(hardware=mock_hw)
        resp = ee.explain("cpu")
        assert "CPU" in resp
        assert "Intel i7" in resp
        assert "8 cores" in resp

    def test_explain_gpu(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_hw = MagicMock()
        mock_hw.get_summary.return_value = HardwareSummary(
            "Intel i7", "x64", 8, 16, 3200.0, "NVIDIA RTX 3060", 6144,
            "ASUS", 32.0, "DIMM", "Windows 11",
        )
        ee = ExplainerEngine(hardware=mock_hw)
        resp = ee.explain("gpu")
        assert "GPU" in resp
        assert "RTX 3060" in resp

    def test_explain_gpu_integrated(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_hw = MagicMock()
        mock_hw.get_summary.return_value = HardwareSummary(
            "Intel i7", "x64", 8, 16, 3200.0, "No discrete GPU detected", 0,
            "ASUS", 32.0, "DIMM", "Windows 11",
        )
        ee = ExplainerEngine(hardware=mock_hw)
        resp = ee.explain("gpu")
        assert "integrated" in resp.lower()

    def test_explain_ram(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_hw = MagicMock()
        mock_hw.get_summary.return_value = HardwareSummary(
            "CPU", "x64", 4, 8, 2400.0, "GPU", 0, "MB", 16.0, "DIMM", "Win10",
        )
        ee = ExplainerEngine(hardware=mock_hw)
        resp = ee.explain("ram")
        assert "RAM" in resp
        assert "16.0" in resp or "16" in resp

    def test_explain_storage(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_storage = MagicMock()
        mock_detail = MagicMock()
        mock_detail.mount_point = "C:"
        mock_detail.free = 100 * (1024 ** 3)
        mock_detail.total = 512 * (1024 ** 3)
        mock_detail.percent = 80.0
        mock_detail.filesystem = "NTFS"
        mock_storage.get_storage_details.return_value = [mock_detail]
        ee = ExplainerEngine(storage=mock_storage)
        resp = ee.explain("storage")
        assert "Storage" in resp
        assert "C:" in resp

    def test_explain_network(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_network = MagicMock()
        mock_config = MagicMock()
        mock_config.adapters = [{"name": "Wi-Fi", "isup": True, "ip": "192.168.1.5", "addresses": []}]
        mock_config.dns_servers = ["8.8.8.8"]
        mock_config.vpn_active = False
        mock_network.get_config.return_value = mock_config
        ee = ExplainerEngine(network=mock_network)
        resp = ee.explain("network")
        assert "Wi-Fi" in resp
        assert "192.168.1.5" in resp

    def test_explain_battery(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_resources = MagicMock()
        mock_status = MagicMock()
        mock_status.battery.percent = 85.0
        mock_status.battery.plugged_in = True
        mock_status.battery.time_remaining = None
        mock_resources.get_system_status.return_value = mock_status
        ee = ExplainerEngine(resources=mock_resources)
        resp = ee.explain("battery")
        assert "battery" in resp.lower() or "Battery" in resp
        assert "85" in resp or "charging" in resp

    def test_explain_firewall(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_security = MagicMock()
        mock_sec = MagicMock()
        mock_sec.firewall_enabled = True
        mock_sec.firewall_profile = "Domain"
        mock_security.get_status.return_value = mock_sec
        ee = ExplainerEngine(security=mock_security)
        resp = ee.explain("firewall")
        assert "ON" in resp or "Firewall" in resp

    def test_explain_os(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_hw = MagicMock()
        mock_hw.get_summary.return_value = HardwareSummary(
            "CPU", "x64", 4, 8, 2400.0, "GPU", 0, "MB", 8.0, "DIMM", "Windows 11 Pro",
        )
        ee = ExplainerEngine(hardware=mock_hw)
        resp = ee.explain("os")
        assert "Windows 11 Pro" in resp

    def test_explain_hardware(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_hw = MagicMock()
        mock_hw.get_summary.return_value = HardwareSummary(
            "Intel i7-12700H", "x64", 14, 20, 2700.0, "RTX 3060", 6144,
            "ASUS ROG", 32.0, "DIMM", "Windows 11",
        )
        ee = ExplainerEngine(hardware=mock_hw)
        resp = ee.explain("hardware")
        assert "Intel i7-12700H" in resp
        assert "14 cores" in resp

    def test_explain_software(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_sw = MagicMock()
        mock_sw.get_installed_apps.return_value = [
            SoftwareEntry("VLC", "3.0", "VideoLAN", "", ""),
            SoftwareEntry("Chrome", "120", "Google", "", ""),
        ]
        mock_sw.get_running_process_count.return_value = 200
        ee = ExplainerEngine(software=mock_sw)
        resp = ee.explain("software")
        assert "2 applications" in resp.lower() or "2" in resp

    def test_explain_services(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_sw = MagicMock()
        mock_sw.get_services.return_value = [
            ServiceEntry("Svc1", "Service 1", "RUNNING", "AUTO"),
            ServiceEntry("Svc2", "Service 2", "STOPPED", "DEMAND"),
            ServiceEntry("Svc3", "Service 3", "RUNNING", "AUTO"),
        ]
        ee = ExplainerEngine(software=mock_sw)
        resp = ee.explain("services")
        assert "services" in resp.lower() or "Services" in resp
        assert "running" in resp.lower()

    def test_explain_startup(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        mock_sw = MagicMock()
        mock_sw.get_startup_items.return_value = [
            {"name": "OneDrive", "command": "onedrive.exe", "source": "HKCU"},
        ]
        ee = ExplainerEngine(software=mock_sw)
        resp = ee.explain("startup")
        assert "startup" in resp.lower() or "Startup" in resp

    def test_explain_unknown_topic(self):
        from moso_core.system_intelligence.explainer import ExplainerEngine
        ee = ExplainerEngine()
        resp = ee.explain("quantum computing")
        assert "don't have a detailed explanation" in resp
        assert "try asking" in resp.lower()


class TestSystemIntelligenceManager:
    def test_manager_initialization(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        assert mgr.hardware is not None
        assert mgr.software is not None
        assert mgr.network is not None
        assert mgr.storage is not None
        assert mgr.security is not None
        assert mgr.diagnostics is not None
        assert mgr.inventory is not None
        assert mgr.explainer is not None

    def test_get_hardware_summary(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        summary = mgr.get_hardware_summary()
        assert isinstance(summary, str)
        assert len(summary) > 10
        assert "I couldn't" not in summary

    def test_get_software_summary(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        summary = mgr.get_software_summary()
        assert isinstance(summary, str)
        assert len(summary) > 5

    def test_get_network_summary(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        summary = mgr.get_network_summary()
        assert isinstance(summary, str)
        assert len(summary) > 5

    def test_get_storage_summary(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        summary = mgr.get_storage_summary()
        assert isinstance(summary, str)
        assert len(summary) > 5

    def test_get_security_summary(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        summary = mgr.get_security_summary()
        assert isinstance(summary, str)
        assert len(summary) > 5

    def test_explain_topic(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        resp = mgr.explain("RAM")
        assert isinstance(resp, str)
        assert "RAM" in resp

    def test_explain_unknown(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        resp = mgr.explain("nonexistent_topic_xyz")
        assert "don't have" in resp

    def test_get_diagnostics_summary(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        summary = mgr.get_diagnostics_summary()
        assert isinstance(summary, str)
        assert len(summary) > 5

    def test_run_diagnostics(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager()
        issues = mgr.run_diagnostics()
        assert isinstance(issues, list)
        for issue in issues:
            assert isinstance(issue, DiagnosticIssue)

    def test_permission_denied(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mock_identity = MagicMock()
        mock_identity.get_identity_level.return_value = "guest"
        mgr = SystemIntelligenceManager(identity=mock_identity)
        result = mgr.capture_snapshot()
        assert "denied" in result.lower() or "Permission" in result

    def test_permission_allowed(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mock_identity = MagicMock()
        mock_identity.get_identity_level.return_value = "owner"
        mock_identity.is_owner.return_value = True
        mgr = SystemIntelligenceManager(identity=mock_identity, memory=MagicMock())
        result = mgr.capture_snapshot()
        # May succeed or fail on snapshot, but shouldn't be permission denied
        assert "denied" not in result.lower()

    def test_store_memory_event(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mock_memory = MagicMock()
        mgr = SystemIntelligenceManager(memory=mock_memory)
        mgr._store_memory_event("test", "description", ["tag"])
        mock_memory.store_event.assert_called_once()

    def test_no_memory_no_error(self):
        from moso_core.system_intelligence.manager import SystemIntelligenceManager
        mgr = SystemIntelligenceManager(memory=None)
        mgr._store_memory_event("test", "desc", ["tag"])
        # Should not raise


class TestOrchestratorIntegration:
    def test_enable_system_intelligence(self):
        from moso_core.orchestration.orchestrator import Orchestrator
        from moso_core.inference.base import InferenceConfig, ModelBackend
        mock_backend = MagicMock(spec=ModelBackend)
        config = InferenceConfig(model_path="", n_ctx=128)
        orch = Orchestrator(config, backend=mock_backend)
        orch.enable_system_intelligence()
        si = orch.system_intelligence
        assert si is not None
        summary = si.get_hardware_summary()
        assert isinstance(summary, str)
        assert len(summary) > 10

    def test_system_intelligence_property_none_by_default(self):
        from moso_core.orchestration.orchestrator import Orchestrator
        from moso_core.inference.base import InferenceConfig, ModelBackend
        mock_backend = MagicMock(spec=ModelBackend)
        config = InferenceConfig(model_path="", n_ctx=128)
        orch = Orchestrator(config, backend=mock_backend)
        assert orch.system_intelligence is None


class TestTopLevelImport:
    def test_system_intelligence_available_flag(self):
        import moso_core
        assert hasattr(moso_core, "SYSTEM_INTELLIGENCE_AVAILABLE")

    def test_import_manager_from_top(self):
        import moso_core
        assert hasattr(moso_core, "system_intelligence")
        # Verify the flag type
        assert isinstance(moso_core.SYSTEM_INTELLIGENCE_AVAILABLE, bool)
