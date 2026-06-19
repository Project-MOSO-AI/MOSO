from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_TOPIC_TEMPLATES: dict[str, str] = {
    "cpu": (
        "The CPU (Central Processing Unit) is your computer's brain. "
        "It handles all the calculations and instructions needed to run programs. "
        "Your CPU is a {cpu_model} with {cores} cores and {threads} threads, "
        "running at {frequency} MHz. "
        "Currently it's {usage}% busy, with {available}% capacity free."
    ),
    "gpu": (
        "The GPU (Graphics Processing Unit) handles visual rendering and parallel compute tasks. "
        "It's essential for displaying graphics on your screen, video playback, gaming, "
        "and increasingly for AI workloads. "
        "Your GPU is: {gpu_model}{vram}.{usage}"
    ),
    "ram": (
        "RAM (Random Access Memory) is your computer's short-term memory. "
        "It temporarily stores data that your CPU needs to access quickly. "
        "Unlike your hard drive, RAM is fast but volatile — it clears when you power off. "
        "You have {total} GB installed.{usage}"
    ),
    "storage": (
        "Storage is where your files live permanently — documents, photos, applications, and the OS itself. "
        "Unlike RAM, storage survives reboots. There are two main types: "
        "SSDs (fast, no moving parts) and HDDs (slower, spinning disks). "
        "Your {drive_type} drive '{mount_point}' has {free_gb} GB free out of {total_gb} GB ({free_pct}% free)."
    ),
    "network": (
        "Networking is how your computer communicates with the internet and other devices. "
        "Your primary adapter is '{adapter}'{ip_info}. "
        "DNS servers: {dns}. "
        "VPN is {vpn_status}."
    ),
    "battery": (
        "The battery powers your laptop when it's not plugged in. "
        "Batteries degrade over time and hold less charge as they age. "
        "Your battery is at {percent}% and is {charging_status}.{time_remaining}"
    ),
    "firewall": (
        "A firewall monitors and controls incoming and outgoing network traffic. "
        "It acts as a barrier between your computer and potential network threats. "
        "Your Windows Firewall is {status}."
    ),
    "os": (
        "Your operating system (OS) is the software that manages all hardware and software on your computer. "
        "It coordinates everything from running applications to managing files and connecting to networks. "
        "You are running {os_version}."
    ),
}


class ExplainerEngine:
    def __init__(self, hardware=None, software=None, network=None,
                 storage=None, security=None, resources=None):
        self._hardware = hardware
        self._software = software
        self._network = network
        self._storage = storage
        self._security = security
        self._resources = resources

    def explain(self, topic: str) -> str:
        topic_lower = topic.strip().lower()

        if topic_lower in ("cpu", "processor", "central processing unit"):
            return self._explain_cpu()
        if topic_lower in ("gpu", "graphics card", "video card", "graphics processing unit"):
            return self._explain_gpu()
        if topic_lower in ("ram", "memory", "random access memory"):
            return self._explain_ram()
        if topic_lower in ("storage", "disk", "drive", "hard drive", "ssd", "hdd"):
            return self._explain_storage()
        if topic_lower in ("network", "internet", "wifi", "ethernet", "networking"):
            return self._explain_network()
        if topic_lower in ("battery", "power", "charge"):
            return self._explain_battery()
        if topic_lower in ("firewall", "security"):
            return self._explain_firewall()
        if topic_lower in ("os", "operating system", "windows", "system"):
            return self._explain_os()
        if topic_lower in ("hardware", "system", "computer", "machine"):
            return self._explain_hardware()
        if topic_lower in ("software", "programs", "applications", "apps"):
            return self._explain_software()
        if topic_lower in ("services", "background services", "daemon"):
            return self._explain_services()
        if topic_lower in ("startup", "startup programs", "autostart"):
            return self._explain_startup()
        if topic_lower in ("diagnostics", "health", "system health"):
            return self._explain_diagnostics()
        if "virtual" in topic_lower:
            return self._explain_virtual_machine()

        return self._explain_generic(topic)

    def _explain_cpu(self) -> str:
        hw = self._hardware.get_summary() if self._hardware else None
        cpu_usage = 0
        cpu_avail = 100
        if self._resources:
            try:
                status = self._resources.get_system_status()
                if status and status.cpu:
                    cpu_usage = status.cpu.usage_percent
                    cpu_avail = 100 - cpu_usage
            except Exception:
                pass
        return _TOPIC_TEMPLATES["cpu"].format(
            cpu_model=hw.cpu_model if hw else "Unknown CPU",
            cores=hw.cpu_cores if hw else "?",
            threads=hw.cpu_threads if hw else "?",
            frequency=f"{hw.cpu_frequency_mhz:.0f}" if hw and hw.cpu_frequency_mhz else "?",
            usage=f"{cpu_usage:.0f}" if cpu_usage else "?",
            available=f"{cpu_avail:.0f}" if cpu_avail else "?",
        )

    def _explain_gpu(self) -> str:
        hw = self._hardware.get_summary() if self._hardware else None
        if hw and hw.gpu_model and "No discrete GPU" not in hw.gpu_model:
            vram = f" with {hw.gpu_vram_mb} MB VRAM" if hw.gpu_vram_mb else ""
            usage = ""
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode == 0:
                    util = result.stdout.strip().replace(" %", "")
                    usage = f" Current utilization is {util}%."
            except Exception:
                pass
            return _TOPIC_TEMPLATES["gpu"].format(
                gpu_model=hw.gpu_model, vram=vram, usage=usage,
            )
        return (
            "Your system uses integrated graphics built into the CPU. "
            "This handles everyday display tasks but isn't optimized for gaming, "
            "3D rendering, or large AI models. For those workloads, "
            "a dedicated GPU (like NVIDIA or AMD) would help."
        )

    def _explain_ram(self) -> str:
        hw = self._hardware.get_summary() if self._hardware else None
        total = hw.ram_total_gb if hw else 0
        usage_str = ""
        if self._resources:
            try:
                status = self._resources.get_system_status()
                if status and status.ram:
                    used_gb = status.ram.used / (1024 ** 3)
                    percent = status.ram.percent
                    usage_str = f" Currently {used_gb:.1f} GB is in use ({percent:.0f}%)."
            except Exception:
                pass
        return _TOPIC_TEMPLATES["ram"].format(total=total, usage=usage_str)

    def _explain_storage(self) -> str:
        mount_point = "C:"
        free_gb = 0
        total_gb = 0
        free_pct = 0
        drive_type = "SSD"

        if self._storage:
            try:
                details = self._storage.get_storage_details()
                if details:
                    d = details[0]
                    mount_point = d.mount_point
                    free_gb = round(d.free / (1024 ** 3), 1)
                    total_gb = round(d.total / (1024 ** 3), 1)
                    free_pct = round(100 - d.percent, 0)
                    if "ssd" in d.filesystem.lower() or "nvme" in d.filesystem.lower():
                        drive_type = "SSD"
                    elif "hdd" in d.filesystem.lower():
                        drive_type = "HDD"
                    else:
                        drive_type = d.filesystem if d.filesystem else "drive"
            except Exception:
                pass

        return _TOPIC_TEMPLATES["storage"].format(
            drive_type=drive_type,
            mount_point=mount_point,
            free_gb=free_gb,
            total_gb=total_gb,
            free_pct=free_pct,
        )

    def _explain_network(self) -> str:
        adapter_name = "Unknown"
        ip_info = ""
        dns = "Unknown"
        vpn_status = "inactive"

        if self._network:
            try:
                config = self._network.get_config()
                for a in config.adapters:
                    if a.get("isup"):
                        ip = a.get("ip", "")
                        if ip:
                            ip_info = f" with IP {ip}"
                            adapter_name = a["name"]
                            break
                if config.dns_servers:
                    dns = ", ".join(config.dns_servers[:3])
                vpn_status = "active" if config.vpn_active else "inactive"
            except Exception:
                pass

        return _TOPIC_TEMPLATES["network"].format(
            adapter=adapter_name, ip_info=ip_info, dns=dns, vpn_status=vpn_status,
        )

    def _explain_battery(self) -> str:
        percent = 0
        charging = "unknown"
        time_remain = ""
        if self._resources:
            try:
                status = self._resources.get_system_status()
                if status and status.battery:
                    percent = status.battery.percent
                    charging = "charging" if status.battery.plugged_in else "not charging"
                    if hasattr(status.battery, "time_remaining") and status.battery.time_remaining:
                        mins = int(status.battery.time_remaining)
                        h, m = divmod(mins, 60)
                        time_remain = f" About {h}h {m}m remaining."
            except Exception:
                pass
        return _TOPIC_TEMPLATES["battery"].format(
            percent=percent, charging_status=charging, time_remaining=time_remain,
        )

    def _explain_firewall(self) -> str:
        status = "unknown"
        if self._security:
            try:
                sec = self._security.get_status()
                status = f"ON ({sec.firewall_profile})" if sec.firewall_enabled else "OFF"
            except Exception:
                pass
        return _TOPIC_TEMPLATES["firewall"].format(status=status)

    def _explain_os(self) -> str:
        hw = self._hardware.get_summary() if self._hardware else None
        os_ver = hw.os_version if hw else "Unknown OS"
        return _TOPIC_TEMPLATES["os"].format(os_version=os_ver)

    def _explain_hardware(self) -> str:
        hw = self._hardware.get_summary() if self._hardware else None
        if not hw:
            return "Hardware information is not available right now."
        gpu = hw.gpu_model if hw.gpu_model and "No discrete GPU" not in hw.gpu_model else "Integrated graphics"
        return (
            f"Here's your system: {hw.cpu_model} with {hw.cpu_cores} cores and {hw.cpu_threads} threads, "
            f"{gpu}, "
            f"{hw.ram_total_gb} GB of {hw.ram_form_factor} RAM, "
            f"motherboard: {hw.motherboard}. "
            f"You're running {hw.os_version}."
        )

    def _explain_software(self) -> str:
        if not self._software:
            return "Software information is not available right now."
        try:
            apps = self._software.get_installed_apps()
            count = len(apps)
            top = [a.name for a in apps[:10]]
            return (
                f"You have {count} applications installed. "
                f"Some of them are: {', '.join(top)}. "
                f"Your system has {self._software.get_running_process_count()} active processes running."
            )
        except Exception as e:
            logger.debug("Software explain error: %s", e)
            return "Software information is temporarily unavailable."

    def _explain_services(self) -> str:
        if not self._software:
            return "Service information is not available right now."
        try:
            services = self._software.get_services()
            running = sum(1 for s in services if s.status == "RUNNING")
            stopped = sum(1 for s in services if s.status == "STOPPED")
            auto = sum(1 for s in services if s.start_type in ("AUTO_START", "Automatic"))
            return (
                f"Your system has {len(services)} services. "
                f"{running} are currently running, {stopped} are stopped. "
                f"{auto} are configured to start automatically."
            )
        except Exception as e:
            logger.debug("Services explain error: %s", e)
            return "Service information is temporarily unavailable."

    def _explain_startup(self) -> str:
        if not self._software:
            return "Startup information is not available right now."
        try:
            items = self._software.get_startup_items()
            count = len(items)
            if count == 0:
                return "No startup programs found. Your system starts lean."
            names = [i["name"] for i in items[:10]]
            return (
                f"You have {count} programs that start automatically with Windows. "
                f"They include: {', '.join(names)}. "
                "These programs run in the background and may affect startup speed."
            )
        except Exception as e:
            logger.debug("Startup explain error: %s", e)
            return "Startup information is temporarily unavailable."

    def _explain_diagnostics(self) -> str:
        return (
            "System diagnostics check your computer's health across several areas: "
            "CPU usage, memory pressure, disk space, network connectivity, "
            "firewall status, antivirus activity, and pending updates. "
            "I can run a full check for you to identify any issues."
        )

    def _explain_virtual_machine(self) -> str:
        hw = self._hardware.get_summary() if self._hardware else None
        if hw:
            return f"Virtualization support is available on your {hw.cpu_model} processor."
        return (
            "A virtual machine (VM) lets you run another operating system inside your current one. "
            "It's useful for testing, running different OS environments, or isolating applications."
        )

    def _explain_generic(self, topic: str) -> str:
        return (
            f"I don't have a detailed explanation for '{topic}' pre-built, "
            f"but I can look into it using system intelligence tools. "
            f"Try asking about CPU, GPU, RAM, storage, network, battery, "
            f"firewall, OS, hardware, software, services, startup, or diagnostics."
        )
