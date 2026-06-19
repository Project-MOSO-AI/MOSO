import logging
import subprocess
from typing import Optional

from moso_core.identity.models import SignalResult, WEIGHT_DEVICE

logger = logging.getLogger(__name__)


class DevicePresence:
    def __init__(self, trusted_bluetooth: Optional[list[str]] = None, trusted_ssid: Optional[list[str]] = None):
        self._trusted_bluetooth = trusted_bluetooth or []
        self._trusted_ssid = trusted_ssid or []
        self._cached_devices: list[dict] = []

    def load_model(self) -> None:
        logger.info("Device presence detector ready")

    def scan(self) -> SignalResult:
        bt_score = self._check_bluetooth_devices()
        wifi_score = self._check_wifi_presence()
        process_score = self._check_trusted_processes()

        combined = 0.4 * bt_score + 0.35 * wifi_score + 0.25 * process_score

        return SignalResult(
            signal_name="device_presence",
            confidence=combined,
            weight=WEIGHT_DEVICE,
            details={
                "bluetooth_score": bt_score,
                "wifi_score": wifi_score,
                "process_score": process_score,
                "detected_devices": len(self._cached_devices),
            },
        )

    def _check_bluetooth_devices(self) -> float:
        score = 0.0
        count = 0
        self._cached_devices = []

        if not self._trusted_bluetooth:
            return 0.0

        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-PnpDevice -Class Bluetooth | Select-Object Status"],
                capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if "OK" in result.stdout:
                score = 0.5 + min(0.5, len(self._trusted_bluetooth) * 0.1)
        except Exception as e:
            logger.debug("Bluetooth scan failed: %s", e)
            score = 0.0

        return min(1.0, score)

    def _check_wifi_presence(self) -> float:
        if not self._trusted_ssid:
            return 0.3

        try:
            result = subprocess.run(
                ["powershell", "-Command", "(Get-NetConnectionProfile).Name"],
                capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            current_ssid = result.stdout.strip()
            if current_ssid in self._trusted_ssid:
                return 1.0
        except Exception as e:
            logger.debug("WiFi scan failed: %s", e)

        return 0.3

    def _check_trusted_processes(self) -> float:
        score = 0.0
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Process -Name 'MOSO', 'moso', 'python' -ErrorAction SilentlyContinue | Select-Object -First 1"],
                capture_output=True, text=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.stdout.strip():
                score = 0.7
        except Exception:
            pass
        return score

    def add_trusted_bluetooth(self, address: str) -> None:
        if address not in self._trusted_bluetooth:
            self._trusted_bluetooth.append(address)

    def add_trusted_ssid(self, ssid: str) -> None:
        if ssid not in self._trusted_ssid:
            self._trusted_ssid.append(ssid)

    @property
    def is_loaded(self) -> bool:
        return True
