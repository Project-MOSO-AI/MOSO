from __future__ import annotations

import logging
from typing import Optional

from moso_core.resources.battery import BatteryMonitor
from moso_core.resources.cpu import CPUMonitor
from moso_core.resources.models import SystemStatus
from moso_core.resources.network import NetworkMonitor
from moso_core.resources.processes import ProcessMonitor
from moso_core.resources.ram import RAMMonitor
from moso_core.resources.storage import StorageMonitor

logger = logging.getLogger(__name__)


class ResourceManager:
    def __init__(self, cpu: Optional[CPUMonitor] = None, ram: Optional[RAMMonitor] = None,
                 storage: Optional[StorageMonitor] = None, battery: Optional[BatteryMonitor] = None,
                 network: Optional[NetworkMonitor] = None, processes: Optional[ProcessMonitor] = None,
                 gpu: Optional[None] = None):
        self._cpu = cpu or CPUMonitor()
        self._ram = ram or RAMMonitor()
        self._storage = storage or StorageMonitor()
        self._battery = battery or BatteryMonitor()
        self._network = network or NetworkMonitor()
        self._processes = processes or ProcessMonitor()
        self._gpu = gpu

    def get_system_status(self) -> SystemStatus:
        return SystemStatus(
            cpu=self._cpu.get_usage(),
            ram=self._ram.get_usage(),
            storage=self._storage.get_usage(),
            battery=self._battery.get_status(),
            network=self._network.get_usage(),
            top_cpu_processes=self._processes.top_cpu(5),
            top_memory_processes=self._processes.top_memory(5),
            gpu=None,
        )

    def get_resource_summary(self) -> str:
        return self.get_system_status().summary()

    def get_cpu(self):
        return self._cpu.get_usage()

    def get_ram(self):
        return self._ram.get_usage()

    def get_storage(self):
        return self._storage.get_usage()

    def get_battery(self):
        return self._battery.get_status()

    def get_network(self):
        return self._network.get_usage()

    def get_top_cpu_processes(self, n: int = 5):
        return self._processes.top_cpu(n)

    def get_top_memory_processes(self, n: int = 5):
        return self._processes.top_memory(n)

    def find_process(self, name: str):
        return self._processes.find_by_name(name)
