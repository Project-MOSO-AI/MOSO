from __future__ import annotations

import logging
import socket
from typing import Optional

logger = logging.getLogger(__name__)

SAFE_DOMAINS: frozenset[str] = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "google.com",
    "youtube.com",
    "github.com",
    "stackoverflow.com",
    "microsoft.com",
    "windows.com",
    "live.com",
    "bing.com",
    "python.org",
    "pypi.org",
    "docker.com",
    "npmjs.com",
    "docs.python.org",
    "learn.microsoft.com",
    "wikipedia.org",
    "reddit.com",
})

KNOWN_BLOCKED: frozenset[str] = frozenset({
    "malware.example.com",
    "phishing.example.com",
    "c2.example.com",
    "evil.com",
    "hackers.net",
})

SUSPICIOUS_TLDS: frozenset[str] = frozenset({
    ".xyz", ".top", ".club", ".gq", ".ml", ".cf", ".tk", ".work", ".date", ".men",
})

SUSPICIOUS_KEYWORDS: list[str] = [
    "free-", "-free", "download-", "-download", "hack", "crack", "keygen",
    "warez", "torrent", "malware", "trojan", "virus", "exploit",
    "paypal", "banking", "login", "verify", "secure-", "account-",
]


class ReputationChecker:
    def __init__(self):
        self._cache: dict[str, float] = {}

    def check_domain(self, domain: str) -> tuple[float, str]:
        domain = domain.lower().strip()

        if domain in self._cache:
            return self._cache[domain], "cached"

        if domain in KNOWN_BLOCKED:
            self._cache[domain] = 1.0
            return 1.0, "known blocked domain"

        if domain in SAFE_DOMAINS:
            self._cache[domain] = 0.0
            return 0.0, "known safe domain"

        score = 0.0
        reason_parts = []

        for tld in SUSPICIOUS_TLDS:
            if domain.endswith(tld):
                score += 0.3
                reason_parts.append(f"suspicious TLD ({tld})")

        for kw in SUSPICIOUS_KEYWORDS:
            if kw in domain:
                score += 0.2
                reason_parts.append(f"suspicious keyword '{kw}' in domain")

        parts = domain.split(".")
        if len(parts) > 3:
            score += 0.15
            reason_parts.append("unusually many subdomains")

        if len(domain) > 50:
            score += 0.1
            reason_parts.append("unusually long domain")

        score = min(score, 1.0)
        reason = "; ".join(reason_parts) if reason_parts else "unknown domain, no risk signals"
        self._cache[domain] = score
        return score, reason

    def check_ip(self, ip: str) -> tuple[float, str]:
        try:
            if ip in ("127.0.0.1", "::1", "0.0.0.0"):
                return 0.0, "localhost"
            socket.inet_aton(ip)
            if ip.startswith("10.") or ip.startswith("172.16.") or ip.startswith("192.168."):
                return 0.0, "private IP range"
            if ip.startswith("169.254."):
                return 0.3, "link-local address"
            return 0.1, "public IP address, no reputation data"
        except OSError:
            return 0.5, "could not resolve IP"

    def check_url(self, url: str) -> tuple[float, str]:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            if hostname:
                return self.check_domain(hostname)
            return 0.0, "no hostname in URL"
        except Exception as e:
            logger.warning("URL parse failed: %s", e)
            return 0.5, "could not parse URL"

    def clear_cache(self):
        self._cache.clear()
