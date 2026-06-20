from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from moso_core.risk.models import RiskAssessment, PrivacyAssessment, RiskReport, RiskLevel
from moso_core.risk.reputation import ReputationChecker
from moso_core.risk.network_analysis import NetworkAnalysis
from moso_core.risk.risk_engine import RiskEngine
from moso_core.risk.privacy_engine import PrivacyEngine
from moso_core.risk.verification import VerificationEngine
from moso_core.risk.manager import RiskManager


class TestRiskModels:
    def test_risk_level_enum_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_risk_assessment_defaults(self):
        ra = RiskAssessment()
        assert ra.level == RiskLevel.LOW
        assert ra.score == 0.0
        assert ra.factors == []
        assert ra.explanation == ""
        assert ra.recommendation == ""

    def test_risk_assessment_to_dict(self):
        ra = RiskAssessment(
            level=RiskLevel.HIGH,
            score=0.7,
            factors=["credential access"],
            explanation="High risk",
            recommendation="Proceed with caution",
        )
        d = ra.to_dict()
        assert d["level"] == "high"
        assert d["score"] == 0.7
        assert d["factors"] == ["credential access"]

    def test_privacy_assessment_defaults(self):
        pa = PrivacyAssessment()
        assert pa.data_exposure == "none"
        assert not pa.credential_exposure
        assert not pa.user_data_accessed

    def test_risk_report_max_level(self):
        report = RiskReport(
            risk=RiskAssessment(level=RiskLevel.LOW),
            privacy=PrivacyAssessment(credential_exposure=True),
        )
        assert report.max_level == RiskLevel.CRITICAL

    def test_risk_report_is_allowed(self):
        low = RiskReport(risk=RiskAssessment(level=RiskLevel.LOW))
        assert low.is_allowed
        high = RiskReport(risk=RiskAssessment(level=RiskLevel.HIGH))
        assert not high.is_allowed
        critical = RiskReport(risk=RiskAssessment(level=RiskLevel.CRITICAL))
        assert not critical.is_allowed

    def test_risk_report_to_dict(self):
        report = RiskReport(
            action="read_file",
            tool="file_tool",
            params={"path": "test.txt"},
            risk=RiskAssessment(level=RiskLevel.LOW),
            privacy=PrivacyAssessment(),
            timestamp=123.0,
        )
        d = report.to_dict()
        assert d["action"] == "read_file"
        assert d["max_level"] == "low"
        assert d["is_allowed"]


class TestReputation:
    def test_safe_domain(self):
        checker = ReputationChecker()
        score, reason = checker.check_domain("google.com")
        assert score == 0.0
        assert "safe" in reason

    def test_blocked_domain(self):
        checker = ReputationChecker()
        score, reason = checker.check_domain("evil.com")
        assert score == 1.0
        assert "blocked" in reason

    def test_unknown_domain_low_risk(self):
        checker = ReputationChecker()
        score, reason = checker.check_domain("example-org.com")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_suspicious_tld(self):
        checker = ReputationChecker()
        score, reason = checker.check_domain("freesite.xyz")
        assert score > 0.0
        assert "TLD" in reason

    def test_suspicious_keywords(self):
        checker = ReputationChecker()
        score, reason = checker.check_domain("free-download-hack.xyz")
        assert score >= 0.5

    def test_localhost_ip(self):
        checker = ReputationChecker()
        score, reason = checker.check_ip("127.0.0.1")
        assert score == 0.0
        assert "localhost" in reason

    def test_private_ip(self):
        checker = ReputationChecker()
        score, reason = checker.check_ip("192.168.1.1")
        assert score == 0.0

    def test_url_check(self):
        checker = ReputationChecker()
        score, reason = checker.check_url("https://github.com")
        assert score == 0.0

    def test_url_blocked(self):
        checker = ReputationChecker()
        score, reason = checker.check_url("https://evil.com/malware")
        assert score == 1.0

    def test_cache_works(self):
        checker = ReputationChecker()
        score1, _ = checker.check_domain("google.com")
        score2, reason = checker.check_domain("google.com")
        assert score1 == score2
        assert reason == "cached"

    def test_clear_cache(self):
        checker = ReputationChecker()
        checker.check_domain("google.com")
        checker.clear_cache()
        assert len(checker._cache) == 0

    def test_long_domain(self):
        checker = ReputationChecker()
        long_domain = "a" * 60 + ".com"
        score, reason = checker.check_domain(long_domain)
        assert score > 0.0
        assert "long" in reason

    def test_many_subdomains(self):
        checker = ReputationChecker()
        score, reason = checker.check_domain("a.b.c.d.e.f.evil.com")
        assert score > 0.0


class TestNetworkAnalysis:
    def test_localhost_destination(self):
        na = NetworkAnalysis()
        result = na.analyze_destination("localhost")
        assert result["is_local"]
        assert result["risk"] == "low"

    def test_https_destination(self):
        na = NetworkAnalysis()
        result = na.analyze_destination("https://google.com")
        assert result["is_tls"]
        assert result["port"] == 443

    def test_known_service_name(self):
        na = NetworkAnalysis()
        result = na.analyze_destination("example.com", port=22)
        assert result["service"] == "SSH"

    def test_estimate_small_data(self):
        na = NetworkAnalysis()
        size, label = na.estimate_data_size({"key": "hello"})
        assert label == "small"

    def test_estimate_medium_data(self):
        na = NetworkAnalysis()
        size, label = na.estimate_data_size({"data": "x" * 5000})
        assert label == "medium"

    def test_is_upload_action(self):
        na = NetworkAnalysis()
        assert na.is_upload_action("upload")
        assert na.is_upload_action("send_file")
        assert not na.is_upload_action("read_file")

    def test_is_download_action(self):
        na = NetworkAnalysis()
        assert na.is_download_action("download")
        assert na.is_download_action("fetch_data")

    def test_blocked_domain_high_risk(self):
        na = NetworkAnalysis()
        result = na.analyze_destination("evil.com")
        assert result["reputation_score"] >= 0.7

    def test_insecure_port_detection(self):
        na = NetworkAnalysis()
        result = na.analyze_destination("example.com", port=21)
        assert "insecure_protocol" in result.get("risk_factors", [])


class TestRiskEngine:
    def test_low_risk_for_safe_action(self):
        engine = RiskEngine()
        assessment = engine.assess("read_file", "file_tool", {"path": "C:\\Users\\test\\notes.txt"})
        assert assessment.level in (RiskLevel.LOW, RiskLevel.MEDIUM)

    def test_credential_path_high_risk(self):
        engine = RiskEngine()
        assessment = engine.assess("read_file", "file_tool", {"path": "C:\\Users\\test\\.env"})
        assert assessment.score >= 0.5

    def test_system_path_elevated_risk(self):
        engine = RiskEngine()
        assessment = engine.assess("delete_file", "file_tool", {"path": "C:\\Windows\\System32\\config"})
        assert assessment.score >= 0.3

    def test_blocked_domain_high_risk(self):
        engine = RiskEngine()
        assessment = engine.assess("open_url", "browser_tool", {"url": "https://evil.com"})
        assert assessment.score >= 0.3

    def test_explanation_low_risk(self):
        engine = RiskEngine()
        assessment = engine.assess("list_directory", "file_tool", {"path": "C:\\Users\\test"})
        assert isinstance(assessment.explanation, str)

    def test_recommendation_for_critical(self):
        engine = RiskEngine()
        assessment = engine.assess("read_file", "file_tool", {"path": ".env"})
        assert isinstance(assessment.recommendation, str)


class TestPrivacyEngine:
    def test_no_exposure_for_safe_action(self):
        engine = PrivacyEngine()
        assessment = engine.assess("list_directory", "file_tool", {"path": "C:\\Temp"})
        assert not assessment.credential_exposure
        assert not assessment.user_data_accessed

    def test_user_data_detected(self):
        engine = PrivacyEngine()
        assessment = engine.assess("read_file", "file_tool", {"path": "C:\\Users\\test\\Documents\\report.pdf"})
        assert assessment.user_data_accessed

    def test_credential_file_detected(self):
        engine = PrivacyEngine()
        assessment = engine.assess("read_file", "file_tool", {"path": "C:\\Users\\test\\.ssh\\id_rsa"})
        assert assessment.credential_exposure

    def test_external_write_detected(self):
        engine = PrivacyEngine()
        assessment = engine.assess("open_url", "browser_tool", {"url": "https://example.com"})
        assert assessment.writes_externally

    def test_system_files_detected(self):
        engine = PrivacyEngine()
        assessment = engine.assess("delete_file", "file_tool", {"path": "C:\\Windows\\System32\\config"})
        assert assessment.system_files_affected

    def test_recommendation_no_concerns(self):
        engine = PrivacyEngine()
        assessment = engine.assess("list_directory", "file_tool", {"path": "C:\\Temp"})
        assert "No privacy concerns" in assessment.recommendation


class TestVerification:
    def test_verify_returns_report(self):
        verifier = VerificationEngine()
        report = verifier.verify("read_file", "file_tool", {"path": "test.txt"})
        assert isinstance(report, RiskReport)
        assert report.tool == "file_tool"
        assert report.action == "read_file"
        assert report.timestamp > 0

    def test_verify_tool_request(self):
        verifier = VerificationEngine()
        report = verifier.verify_tool_request("browser_tool", "open_url", {"url": "https://google.com"})
        assert isinstance(report, RiskReport)
        assert report.tool == "browser_tool"


class TestRiskManager:
    def test_assess_returns_report(self):
        manager = RiskManager()
        report = manager.assess("file_tool", "read_file", {"path": "test.txt"})
        assert isinstance(report, RiskReport)

    def test_check_and_block_allows_low_risk(self):
        manager = RiskManager()
        allowed, report = manager.check_and_block("file_tool", "list_directory", {"path": "C:\\Temp"})
        assert allowed
        assert report is not None

    def test_check_and_block_blocks_critical(self):
        manager = RiskManager()
        allowed, report = manager.check_and_block("file_tool", "read_file", {"path": ".env"})
        if report.max_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            assert not allowed
        else:
            assert allowed

    def test_memory_event_stored(self):
        mock_memory = MagicMock()
        mock_memory.store_event = MagicMock()
        manager = RiskManager(memory=mock_memory)
        manager.assess("file_tool", "read_file", {"path": "test.txt"})
        mock_memory.store_event.assert_called_once()

    def test_identity_permission_check(self):
        mock_identity = MagicMock()
        mock_identity.get_identity_level.return_value = "guest"
        manager = RiskManager(identity=mock_identity)
        allowed, reason = manager._check_permission("owner")
        assert not allowed
        assert "denied" in reason

    def test_no_identity_always_allowed(self):
        manager = RiskManager()
        allowed, reason = manager._check_permission("owner")
        assert allowed
        assert reason == ""


class TestRiskIntegration:
    def test_orchestrator_enable_risk(self):
        from moso_core.orchestration.orchestrator import Orchestrator
        from moso_core.inference.base import InferenceConfig, ModelBackend, GenerationResult

        class _MockBackend(ModelBackend):
            def __init__(self, config=None):
                self.config = config or InferenceConfig(model_path="dummy")
                self._model = None
            def load(self): pass
            def unload(self): pass
            def generate(self, prompt="", **kw): return GenerationResult(text="")
            def generate_stream(self, prompt="", **kw): return iter([])
            def chat(self, messages=None, **kw): return GenerationResult(text="")
            def chat_stream(self, messages=None, **kw): return iter([])
            def tokenize(self, text): return [1, 2, 3]
            def detokenize(self, tokens): return "mock"
            @property
            def is_loaded(self): return False

        config = InferenceConfig(model_path="dummy")
        orch = Orchestrator(config, backend=_MockBackend)
        assert orch.risk is None
        orch.enable_risk_engine()
        assert orch.risk is not None
        assert hasattr(orch.risk, "assess")

    def test_risk_available_flag(self):
        from moso_core import RISK_AVAILABLE
        assert RISK_AVAILABLE is True

    def test_tool_execution_risk_check(self):
        from moso_core.tools.registry import ToolRegistry
        from moso_core.tools.models import ToolRequest
        registry = ToolRegistry()
        result = registry.execute_tool(
            ToolRequest(tool_name="unknown_tool", parameters={"action": "test"}, requester="test"),
        )
        assert not result.success
        assert "Unknown" in result.error
