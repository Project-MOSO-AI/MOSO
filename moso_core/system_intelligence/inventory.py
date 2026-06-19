from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from moso_core.system_intelligence.models import (
    HardwareSummary,
    InventoryDiff,
    SecurityStatus,
    ServiceEntry,
    SoftwareEntry,
    NetworkConfig,
    SystemSnapshot,
)

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".moso", "inventory.db")


class InventoryEngine:
    def __init__(self, hardware=None, software=None, network=None,
                 security=None, db_path: Optional[str] = None):
        self._hardware = hardware
        self._software = software
        self._network = network
        self._security = security
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._lock:
            conn = sqlite3.connect(self._db_path, timeout=5)
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        hardware TEXT NOT NULL,
                        software TEXT NOT NULL,
                        services TEXT NOT NULL,
                        network TEXT NOT NULL,
                        security TEXT NOT NULL
                    )
                """)
                conn.commit()
            except sqlite3.Error as e:
                logger.warning("Failed to init inventory DB: %s", e)
            finally:
                conn.close()

    def capture_snapshot(self) -> str:
        hw = self._hardware.get_summary() if self._hardware else None
        sw = self._software.get_installed_apps() if self._software else []
        sv = self._software.get_services() if self._software else []
        net = self._network.get_config() if self._network else None
        sec = self._security.get_status() if self._security else None

        snapshot = SystemSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            hardware=hw or HardwareSummary(
                cpu_model="", cpu_architecture="", cpu_cores=0, cpu_threads=0,
                cpu_frequency_mhz=0.0, gpu_model="", gpu_vram_mb=0,
                motherboard="", ram_total_gb=0.0, ram_form_factor="", os_version="",
            ),
            software=sw,
            services=sv,
            network=net or NetworkConfig(adapters=[], dns_servers=[], vpn_active=False,
                                         active_connections=0, listening_ports=[]),
            security=sec or SecurityStatus(firewall_enabled=False, firewall_profile="",
                                           antivirus_active=False, antivirus_name="",
                                           pending_updates=0, suspicious_startup_entries=[]),
        )

        with self._lock:
            conn = sqlite3.connect(self._db_path, timeout=5)
            try:
                conn.execute(
                    "INSERT INTO snapshots (timestamp, hardware, software, services, network, security) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        snapshot.timestamp,
                        json.dumps(snapshot.hardware.to_dict()),
                        json.dumps([s.to_dict() for s in snapshot.software]),
                        json.dumps([s.to_dict() for s in snapshot.services]),
                        json.dumps(snapshot.network.to_dict()),
                        json.dumps(snapshot.security.to_dict()),
                    ),
                )
                conn.commit()
            except sqlite3.Error as e:
                logger.warning("Failed to save snapshot: %s", e)
            finally:
                conn.close()

        return snapshot.timestamp

    def get_latest_snapshot(self) -> Optional[SystemSnapshot]:
        with self._lock:
            conn = sqlite3.connect(self._db_path, timeout=5)
            try:
                row = conn.execute(
                    "SELECT timestamp, hardware, software, services, network, security "
                    "FROM snapshots ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if row:
                    return self._row_to_snapshot(row)
                return None
            except sqlite3.Error as e:
                logger.warning("Failed to read snapshot: %s", e)
                return None
            finally:
                conn.close()

    def get_previous_snapshot(self) -> Optional[SystemSnapshot]:
        with self._lock:
            conn = sqlite3.connect(self._db_path, timeout=5)
            try:
                rows = conn.execute(
                    "SELECT timestamp, hardware, software, services, network, security "
                    "FROM snapshots ORDER BY id DESC LIMIT 2 OFFSET 1"
                ).fetchall()
                if rows:
                    return self._row_to_snapshot(rows[0])
                return None
            except sqlite3.Error as e:
                logger.warning("Failed to read previous snapshot: %s", e)
                return None
            finally:
                conn.close()

    def compare_with_last_snapshot(self) -> Optional[InventoryDiff]:
        latest = self.get_latest_snapshot()
        previous = self.get_previous_snapshot()

        if latest is None:
            logger.info("No snapshot to compare against")
            return None

        return self._compute_diff(previous, latest)

    def compare_snapshots(self, before: SystemSnapshot, after: SystemSnapshot) -> InventoryDiff:
        return self._compute_diff(before, after)

    def list_snapshots(self, limit: int = 10) -> list[str]:
        with self._lock:
            conn = sqlite3.connect(self._db_path, timeout=5)
            try:
                rows = conn.execute(
                    "SELECT timestamp FROM snapshots ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [r[0] for r in rows]
            except sqlite3.Error as e:
                logger.warning("Failed to list snapshots: %s", e)
                return []
            finally:
                conn.close()

    def clear_snapshots(self):
        with self._lock:
            conn = sqlite3.connect(self._db_path, timeout=5)
            try:
                conn.execute("DELETE FROM snapshots")
                conn.commit()
            except sqlite3.Error as e:
                logger.warning("Failed to clear snapshots: %s", e)
            finally:
                conn.close()

    @staticmethod
    def _row_to_snapshot(row) -> SystemSnapshot:
        timestamp, hw_json, sw_json, sv_json, net_json, sec_json = row
        hw_dict = json.loads(hw_json)
        sw_list = json.loads(sw_json)
        sv_list = json.loads(sv_json)
        net_dict = json.loads(net_json)
        sec_dict = json.loads(sec_json)

        return SystemSnapshot(
            timestamp=timestamp,
            hardware=HardwareSummary(**hw_dict),
            software=[SoftwareEntry(**s) for s in sw_list],
            services=[ServiceEntry(**s) for s in sv_list],
            network=NetworkConfig(**net_dict),
            security=SecurityStatus(**sec_dict),
        )

    @staticmethod
    def _compute_diff(before: Optional[SystemSnapshot],
                      after: SystemSnapshot) -> InventoryDiff:
        if before is None:
            return InventoryDiff(
                timestamp=datetime.now(timezone.utc).isoformat(),
                new_software=after.software[:],
                removed_software=[],
                hardware_changed=False,
                hardware_before=None,
                hardware_after=after.hardware,
                new_services=after.services[:],
                removed_services=[],
            )

        before_names = {s.name for s in before.software}
        after_names = {s.name for s in after.software}

        new_names = after_names - before_names
        removed_names = before_names - after_names

        new_sw = [s for s in after.software if s.name in new_names]
        removed_sw = [s for s in before.software if s.name in removed_names]

        before_sv_names = {s.name for s in before.services}
        after_sv_names = {s.name for s in after.services}

        new_sv = [s for s in after.services if s.name in after_sv_names - before_sv_names]
        removed_sv = [s for s in before.services if s.name in before_sv_names - after_sv_names]

        hw_changed = (
            before.hardware.cpu_model != after.hardware.cpu_model
            or before.hardware.gpu_model != after.hardware.gpu_model
            or before.hardware.ram_total_gb != after.hardware.ram_total_gb
            or before.hardware.motherboard != after.hardware.motherboard
        )

        return InventoryDiff(
            timestamp=datetime.now(timezone.utc).isoformat(),
            new_software=new_sw,
            removed_software=removed_sw,
            hardware_changed=hw_changed,
            hardware_before=before.hardware,
            hardware_after=after.hardware,
            new_services=new_sv,
            removed_services=removed_sv,
        )
