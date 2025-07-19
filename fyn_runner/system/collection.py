# Copyright (C) 2025 Fyn-Runner Authors
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
#  see <https://www.gnu.org/licenses/>.

import json
import platform
import re

from cpuinfo import get_cpu_info
import psutil

from fyn_runner.server.message import HttpMethod, Message


def report_current_system_info(logger, file_manager, server_proxy):
    """
    Collects system information, saves it to a cache file, and sends it to the server.

    Args:
        logger: Logger object for recording status and debug information
        file_manager: Manager for file operations and accessing directories
        server_proxy: Proxy for communicating with the server
    """

    logger.info("Collecting system information.")
    hw_file = file_manager.cache_dir / 'system_data.json'
    current_hw_data = _get_system_data(file_manager, logger)
    logger.debug(f"System data:{current_hw_data}")
    server_proxy.push_message(
        Message.json_message(api_path=f"{server_proxy.api_url}:{server_proxy.api_port}/"
                             f"runner_manager/update_system/{server_proxy.id}",
                             method=HttpMethod.PUT, json_data=current_hw_data)
    )
    with open(hw_file, 'w', encoding='utf-8') as writer:
        json.dump(current_hw_data, writer, ensure_ascii=False, indent=4)


def _get_system_data(file_manager, logger):
    """
    Aggregates all system information by combining OS, CPU, RAM, disk, and GPU data.

    Args:
        file_manager: Manager for file operations
        logger: Logger object for recording status

    Returns:
        dict: Combined dictionary of all system information
    """

    info = _get_os_info()
    info |= _get_cpu_data()
    info |= _get_ram_data()
    info |= _get_disk_data(file_manager, logger)
    info |= _get_gpu_data()
    return info


def _get_os_info():
    """
    Collects operating system information.

    Returns:
        dict: Dictionary containing OS name, release, version, and architecture
    """
    return {
        'system_name': platform.system(),
        'system_release': platform.release(),
        'system_version': platform.version(),
        'system_architecture': platform.machine(),
    }


def _parse_cache_size(cache_str):
    """
    Parse cache size string (e.g., "11.5 MiB") and convert to bytes.

    Args:
        cache_str: String representation of cache size

    Returns:
        int: Cache size in bytes, or None if parsing fails
    """
    if not cache_str or cache_str == 'None':
        return None

    # Handle cases where it's already a number
    if isinstance(cache_str, (int, float)):
        return int(cache_str)

    # Parse string like "11.5 MiB", "512 KiB", "32 MB", etc.
    match = re.match(r'(\d+(?:\.\d+)?)\s*([KMGT]i?B?)', str(cache_str), re.IGNORECASE)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2).upper()

    # Convert to bytes
    multipliers = {
        'B': 1,
        'KB': 1000, 'KIB': 1024,
        'MB': 1000**2, 'MIB': 1024**2,
        'GB': 1000**3, 'GIB': 1024**3,
        'TB': 1000**4, 'TIB': 1024**4,
        # Handle cases without 'B'
        'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4
    }

    multiplier = multipliers.get(unit, 1)
    return int(value * multiplier)


def _get_cpu_data():
    """
    Collects CPU information using cpuinfo and psutil.

    Returns:
        dict: Dictionary containing CPU model, clock speeds, core counts, and cache sizes
    """
    cpu_info = get_cpu_info()
    return {
        'cpu_model': cpu_info['brand_raw'],
        'cpu_clock_speed_advertised': cpu_info['hz_advertised'][0],
        'cpu_clock_speed_actual': cpu_info['hz_actual'][0],
        'cpu_logical_cores': psutil.cpu_count(),
        'cpu_physical_cores': psutil.cpu_count(logical=False),
        'cpu_cache_l1_size': _parse_cache_size(cpu_info['l1_data_cache_size']),
        'cpu_cache_l2_size': _parse_cache_size(cpu_info['l2_cache_size']),
        'cpu_cache_l3_size': _parse_cache_size(cpu_info['l3_cache_size']),
    }


def _get_ram_data():
    """
    Collects system RAM information.

    Returns:
        dict: Dictionary containing total RAM size
    """
    return {'ram_size_total': psutil.virtual_memory().total}


def _get_disk_data(file_manager, logger):
    """
    Collects disk information for the simulation directory.

    Args:
        file_manager: Manager object containing simulation directory path
        logger: Logger object for recording errors

    Returns:
        dict: Dictionary containing total and available disk size
    """
    sim_path = file_manager.simulation_dir

    try:
        usage = psutil.disk_usage(str(sim_path))
        return {
            "disk_size_total": usage.total,
            "disk_size_available": usage.free
        }
    except Exception as e:
        logger.error(f"Could not assess storage: {str(e)}")
        return {
            'disk_size_total': None,
            'disk_size_available': None
        }


def _get_gpu_data():
    """
    TODO:
    Placeholder function for collecting GPU information.

    Returns:
        dict: Empty dictionary (to be implemented in the future)
    """
    # 'gpu_vendor': self.gpu_vendor,
    # 'gpu_model': self.gpu_model,
    # 'gpu_memory_size': self.gpu_memory_size,
    # 'gpu_clock_speed': self.gpu_clock_speed,
    # 'gpu_compute_units': self.gpu_compute_units,
    # 'gpu_core_count': self.gpu_core_count,
    # 'gpu_driver_version': self.gpu_driver_version

    return {}
