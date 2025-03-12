# Copyright (C) 2025 Bevan W.S. Jones
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not,
# see <https://www.gnu.org/licenses/>.

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import platform
import logging
import json
from datetime import datetime
import psutil


@dataclass
class GPUInfo:
    id: int
    name: str
    vendor: str
    memory_total: Optional[int] = None  # in bytes
    driver_version: Optional[str] = None
    compute_capability: Optional[tuple] = None  # For NVIDIA
    extra_info: Optional[dict] = None


@dataclass
class SystemInfo:
    hostname: str
    os: str
    platform: str
    python_version: str
    timestamp: str


@dataclass
class HardwareInfo:
    system_info: SystemInfo
    gpus: List[GPUInfo]
    cpu_info: Dict
    memory: Dict
    network: Dict
    timestamp: str


class HardwareData():
    HardwareInfo hw_inf


def detect_gpus() -> List[GPUInfo]:
    """Detect NVIDIA GPUs using nvidia-smi"""
    try:
        import pynvml

        pynvml.nvmlInit()
        devices = []
        for i in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            compute_capability = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
            devices.append(
                GPUInfo(
                    id=i,
                    name=(
                        pynvml.nvmlDeviceGetName(handle).decode("utf-8")
                        if isinstance(pynvml.nvmlDeviceGetName(handle), bytes)
                        else pynvml.nvmlDeviceGetName(handle)
                    ),
                    memory_total=info.total,
                    compute_capability=compute_capability,
                    driver_version=pynvml.nvmlSystemGetDriverVersion().decode("utf-8"),
                )
            )
        return devices
    except ImportError:
        logging.warning("pynvml not installed - GPU detection disabled")
        return []
    except Exception as e:
        logging.error(f"GPU detection failed: {str(e)}")
        return []


def detect_cpu() -> Dict:
    """Detect CPU information"""
    try:
        cpu_freq = psutil.cpu_freq()
        return {
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_total": psutil.cpu_count(logical=True),
            "frequency_max": cpu_freq.max if cpu_freq else None,
            "frequency_min": cpu_freq.min if cpu_freq else None,
            "frequency_current": cpu_freq.current if cpu_freq else None,
            "cpu_percent": psutil.cpu_percent(interval=1),
            "model": platform.processor(),
        }
    except Exception as e:
        logging.error(f"CPU detection failed: {str(e)}")
        return {}


def detect_memory() -> Dict:
    """Detect memory information"""
    try:
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "percent": mem.percent,
            "used": mem.used,
            "free": mem.free,
        }
    except Exception as e:
        logging.error(f"Memory detection failed: {str(e)}")
        return {}


def detect_network() -> Dict:
    """Detect network interfaces"""
    try:
        nics = psutil.net_if_addrs()
        return {
            nic: [addr._asdict() for addr in info]
            for nic, info in nics.items()
            if not nic.startswith("lo")
        }
    except Exception as e:
        logging.error(f"Network detection failed: {str(e)}")
        return {}


def get_system_info() -> SystemInfo:
    """Collect basic system information"""
    return SystemInfo(
        hostname=platform.node(),
        os=platform.system(),
        platform=platform.platform(),
        python_version=platform.python_version(),
        timestamp=datetime.utcnow().isoformat(),
    )


def collect_hardware_info() -> HardwareInfo:
    """Collect all hardware information and return as HardwareInfo instance"""
    return HardwareInfo(
        system_info=get_system_info(),
        gpus=detect_gpus(),
        cpu_info=detect_cpu(),
        memory=detect_memory(),
        network=detect_network(),
        timestamp=datetime.utcnow().isoformat(),
    )


def save_hardware_info(hardware_info: HardwareInfo, filepath: str) -> None:
    """Save hardware information to a JSON file"""
    with open(filepath, "w") as f:
        json.dump(asdict(hardware_info), f, indent=2)


def hardware_info_to_dict(hardware_info: HardwareInfo) -> Dict:
    """Convert HardwareInfo to dictionary"""
    return asdict(hardware_info)


# Setup logging
logging.basicConfig(level=logging.INFO)

# Collect hardware information
hw_info = collect_hardware_info()

# Save to file
save_hardware_info(hw_info, "hardware_info.json")

# Print as JSON
print(json.dumps(hardware_info_to_dict(hw_info), indent=2))

# Access specific information
print(f"CPU cores: {hw_info.cpu_info['cores_total']}")
print(f"Memory total: {hw_info.memory['total'] / (1024**3):.2f} GB")
