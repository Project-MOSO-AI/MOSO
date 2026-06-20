from __future__ import annotations

import logging
import socket
from typing import Optional
from urllib.parse import urlparse

from moso_core.risk.reputation import ReputationChecker

logger = logging.getLogger(__name__)

TLS_PORTS: frozenset[int] = frozenset({443, 8443, 465, 993, 995, 853})
KNOWN_SERVICES: dict[int, str] = {
    80: "HTTP", 443: "HTTPS", 22: "SSH", 21: "FTP", 23: "Telnet",
    25: "SMTP", 53: "DNS", 110: "POP3", 143: "IMAP", 993: "IMAPS",
    995: "POP3S", 3306: "MySQL", 5432: "PostgreSQL", 3389: "RDP",
    6379: "Redis", 27017: "MongoDB", 8443: "HTTPS-alt",
}


class NetworkAnalysis:
    def __init__(self):
        self._reputation = ReputationChecker()

    def analyze_destination(self, url_or_host: str, port: Optional[int] = None) -> dict:
        if not url_or_host or url_or_host.startswith((".", "\\", "/")):
            return {
                "hostname": url_or_host or "",
                "port": port or 0,
                "is_tls": False,
                "service": "unknown",
                "reputation_score": 0.0,
                "reputation_reason": "local path, not a network destination",
                "risk": "low",
                "is_local": True,
                "ip": "",
                "risk_factors": [],
            }
        parsed = urlparse(url_or_host)
        hostname = parsed.hostname or url_or_host
        dest_port = port or parsed.port or (443 if parsed.scheme == "https" else 80)

        result = {
            "hostname": hostname,
            "port": dest_port,
            "is_tls": dest_port in TLS_PORTS,
            "service": KNOWN_SERVICES.get(dest_port, "unknown"),
            "reputation_score": 0.0,
            "reputation_reason": "",
            "risk": "low",
            "is_local": False,
        }

        try:
            ip = socket.gethostbyname(hostname)
            result["ip"] = ip
            result["is_local"] = ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172.16.") or ip == "::1"
        except (OSError, UnicodeError):
            result["ip"] = "unresolved"
            result["is_local"] = False

        score, reason = self._reputation.check_domain(hostname)
        result["reputation_score"] = score
        result["reputation_reason"] = reason

        risk_factors = []
        if score >= 0.7:
            risk_factors.append("high_reputation_risk")
        if not result["is_tls"] and not result["is_local"]:
            risk_factors.append("no_tls")
        if dest_port in (21, 23, 25):
            risk_factors.append("insecure_protocol")
        if score >= 0.3:
            risk_factors.append("medium_reputation_risk")

        if risk_factors:
            result["risk"] = "high" if "high_reputation_risk" in risk_factors else "medium"
        else:
            result["risk"] = "low"

        result["risk_factors"] = risk_factors
        return result

    def estimate_data_size(self, params: dict) -> tuple[int, str]:
        total = 0
        for key, value in params.items():
            if isinstance(value, str):
                total += len(value)
            elif isinstance(value, (list, dict)):
                total += len(str(value))
        if total < 100:
            return total, "small"
        elif total < 10000:
            return total, "medium"
        else:
            return total, "large"

    def is_upload_action(self, action: str) -> bool:
        upload_keywords = ["upload", "send", "post", "put", "write", "create"]
        return any(kw in action.lower() for kw in upload_keywords)

    def is_download_action(self, action: str) -> bool:
        download_keywords = ["download", "fetch", "get", "read", "open_url", "search_web"]
        return any(kw in action.lower() for kw in download_keywords)
