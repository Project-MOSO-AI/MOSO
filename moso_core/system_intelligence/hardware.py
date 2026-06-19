from __future__ import annotations

import logging
import platform
import subprocess
from typing import Optional

from moso_core.system_intelligence.models import HardwareSummary

logger = logging.getLogger(__name__)


class HardwareIntelligence:
    def get_summary(self) -> HardwareSummary:
        cpu_model = self._get_cpu_model()
        cpu_arch = platform.machine()
        cpu_cores = self._get_cpu_cores()
        cpu_threads = self._get_cpu_threads()
        cpu_freq = self._get_cpu_frequency()
        gpu_model, gpu_vram = self._get_gpu_info()
        motherboard = self._get_motherboard()
        ram_total_gb, ram_form = self._get_ram_info()
        os_ver = f"{platform.system()} {platform.release()} ({platform.version()})"

        return HardwareSummary(
            cpu_model=cpu_model,
            cpu_architecture=cpu_arch,
            cpu_cores=cpu_cores,
            cpu_threads=cpu_threads,
            cpu_frequency_mhz=cpu_freq,
            gpu_model=gpu_model,
            gpu_vram_mb=gpu_vram,
            motherboard=motherboard,
            ram_total_gb=ram_total_gb,
            ram_form_factor=ram_form,
            os_version=os_ver,
        )

    @staticmethod
    def _get_cpu_model() -> str:
        try:
            import psutil
            brand = platform.processor()
            if brand:
                return brand
            if hasattr(psutil, "cpu_freq"):
                freq = psutil.cpu_freq()
                cores = psutil.cpu_count()
                return f"Unknown CPU ({cores or '?'} cores, {freq.max:.0f} MHz)" if freq else "Unknown CPU"
            return platform.processor() or "Unknown CPU"
        except Exception as e:
            logger.warning("CPU model detection failed: %s", e)
            return platform.processor() or "Unknown CPU"

    @staticmethod
    def _get_cpu_cores() -> int:
        try:
            import psutil
            return psutil.cpu_count(logical=False) or 0
        except Exception:
            return 0

    @staticmethod
    def _get_cpu_threads() -> int:
        try:
            import psutil
            return psutil.cpu_count(logical=True) or 0
        except Exception:
            return 0

    @staticmethod
    def _get_cpu_frequency() -> float:
        try:
            import psutil
            freq = psutil.cpu_freq()
            return freq.current if freq else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _get_gpu_info() -> tuple[str, int]:
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_videocontroller", "get", "name,adapterram"],
                capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().splitlines()
                if len(lines) >= 2:
                    header = lines[0].lower()
                    data = lines[1].strip()
                    parts = data.rsplit(None, 1)
                    name = parts[0] if parts else data
                    vram_str = parts[1] if len(parts) > 1 else "0"
                    try:
                        vram_mb = int(vram_str) // (1024 * 1024) if vram_str.isdigit() else 0
                    except (ValueError, OverflowError):
                        vram_mb = 0
                    return name, vram_mb
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("WMIC GPU query failed: %s", e)

        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().splitlines()[0]
                parts = line.split(",")
                name = parts[0].strip() if parts else ""
                vram_str = parts[1].strip().replace(" MiB", "").replace(" MB", "") if len(parts) > 1 else "0"
                try:
                    vram_mb = int(vram_str)
                except ValueError:
                    vram_mb = 0
                return name, vram_mb
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("nvidia-smi query failed: %s", e)

        return "No discrete GPU detected", 0

    @staticmethod
    def _get_motherboard() -> str:
        try:
            result = subprocess.run(
                ["wmic", "baseboard", "get", "product,manufacturer"],
                capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().splitlines()
                if len(lines) >= 2:
                    parts = lines[1].strip().split(None, 1)
                    manufacturer = parts[0] if parts else ""
                    product = parts[1] if len(parts) > 1 else ""
                    return f"{manufacturer} {product}".strip()
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("WMIC baseboard query failed: %s", e)
        return "Unknown"

    @staticmethod
    def _get_ram_info() -> tuple[float, str]:
        try:
            import psutil
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024 ** 3)
        except Exception:
            total_gb = 0.0

        form_factor = "Unknown"
        try:
            result = subprocess.run(
                ["wmic", "memorychip", "get", "formfactor"],
                capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().splitlines()
                if len(lines) >= 2:
                    ff_code = lines[1].strip()
                    form_map = {"0": "Unknown", "1": "Other", "2": "SIP", "3": "DIP",
                                "4": "ZIP", "5": "SOJ", "6": "Proprietary", "7": "SIMM",
                                "8": "DIMM", "9": "TSOP", "10": "PGA", "11": "RIMM",
                                "12": "SODIMM", "13": "SRIMM", "14": "SMD", "15": "SSMP",
                                "16": "QFP", "17": "TQFP", "18": "SOIC", "19": "LCC",
                                "20": "PLCC", "21": "BGA", "22": "FPBGA", "23": "LGA"}
                    form_factor = form_map.get(ff_code, ff_code)
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("WMIC memory chip query failed: %s", e)

        return round(total_gb, 1), form_factor
