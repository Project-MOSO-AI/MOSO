from __future__ import annotations

import logging
import subprocess
from typing import Optional

from moso_core.system_intelligence.models import NetworkConfig

logger = logging.getLogger(__name__)


class NetworkIntelligence:
    def get_config(self) -> NetworkConfig:
        adapters = self._get_adapters()
        dns = self._get_dns_servers()
        vpn = self._detect_vpn()
        connections = self._get_active_connections()
        ports = self._get_listening_ports()

        return NetworkConfig(
            adapters=adapters,
            dns_servers=dns,
            vpn_active=vpn,
            active_connections=connections,
            listening_ports=ports,
        )

    @staticmethod
    def _get_adapters() -> list[dict]:
        adapters = []
        try:
            import psutil
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            for name, addr_list in addrs.items():
                info = {"name": name, "addresses": [], "isup": False}
                if name in stats:
                    info["isup"] = stats[name].isup
                for addr in addr_list:
                    entry = {"family": str(addr.family), "address": addr.address}
                    if addr.netmask:
                        entry["netmask"] = addr.netmask
                    if addr.broadcast:
                        entry["broadcast"] = addr.broadcast
                    info["addresses"].append(entry)
                    if addr.family == 2 and addr.address:
                        info.setdefault("ip", addr.address)
                if info.get("ip") or info.get("addresses"):
                    adapters.append(info)
        except Exception as e:
            logger.debug("Failed to get network adapters: %s", e)
        return adapters

    @staticmethod
    def _get_dns_servers() -> list[str]:
        servers = []
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-DnsClientServerAddress | Select-Object -ExpandProperty ServerAddresses"],
                capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                servers = [s.strip() for s in result.stdout.strip().splitlines() if s.strip()]
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("PowerShell DNS query failed: %s", e)

        if not servers:
            try:
                result = subprocess.run(
                    ["ipconfig", "/all"],
                    capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "DNS Servers" in line:
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                val = parts[1].strip()
                                if val:
                                    servers = [val]
                                break
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
                logger.debug("ipconfig DNS query failed: %s", e)

        if not servers:
            try:
                import psutil
                addrs = psutil.net_if_addrs()
                for name, addr_list in addrs.items():
                    for addr in addr_list:
                        if hasattr(addr, "address") and addr.address and "." in addr.address:
                            if addr.address.startswith(("8.8.", "1.1.", "208.67.")):
                                servers.append(addr.address)
            except Exception:
                pass

        return servers

    @staticmethod
    def _detect_vpn() -> bool:
        try:
            import psutil
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            vpn_keywords = ["vpn", "tunnel", "tap", "openvpn", "wireguard", "nordvpn",
                            "protonvpn", "expressvpn", "tailscale", "zerotier", "ciscovpn"]
            for name in addrs:
                name_lower = name.lower()
                if any(kw in name_lower for kw in vpn_keywords):
                    if name in stats and stats[name].isup:
                        return True
                for addr in addrs[name]:
                    ip = getattr(addr, "address", "") or ""
                    if ip.startswith(("10.8.", "10.10.", "10.0.8.", "172.16.")):
                        return True
        except Exception as e:
            logger.debug("VPN detection failed: %s", e)
        return False

    @staticmethod
    def _get_active_connections() -> int:
        try:
            import psutil
            conns = psutil.net_connections()
            return len(conns)
        except (psutil.AccessDenied, Exception) as e:
            logger.debug("Failed to get connections: %s", e)
            return 0

    @staticmethod
    def _get_listening_ports() -> list[int]:
        ports = []
        try:
            import psutil
            conns = psutil.net_connections(kind="inet")
            for conn in conns:
                if conn.status == "LISTEN" and hasattr(conn.laddr, "port"):
                    ports.append(conn.laddr.port)
        except (psutil.AccessDenied, Exception) as e:
            logger.debug("Failed to get listening ports: %s", e)
        return sorted(set(ports))
