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

import psutil
from cpuinfo import get_cpu_info

from fyn_runner.server.message import HttpMethod, Message


def collect_system_info(logger, file_manager, server_proxy):

    logger.info("Checking system")
    hw_file = file_manager.cache_dir / 'system_data.json'

    reader = open(hw_file, 'r', encoding='utf-8') if hw_file.exists() else None
    saved_hw_data = json.load(reader) if hw_file.exists() else None
    if reader:
        reader.close()
    current_hw_data = _get_system_data(file_manager, logger)

    if current_hw_data != saved_hw_data:
        logger.info("System has been updated, updating server data.")
        logger.debug(f"System data:{current_hw_data}")

        server_proxy.push_message(
            Message.json_message(api_path=f"{server_proxy.api_url}:{server_proxy.api_port}/"
                                 f"update_system/{server_proxy.id}", method=HttpMethod.PUT,
                                 json_data=current_hw_data, header=None, priority=0, params=None)
        )
    else:
        logger.debug("No change to system info")

    with open(hw_file, 'w', encoding='utf-8') as writer:
        json.dump(current_hw_data, writer, ensure_ascii=False, indent=4)


def _get_system_data(file_manager, logger):
    info = _get_os_info()
    info |= _get_cpu_data()
    info |= _get_ram_data()
    info |= _get_disk_data(file_manager, logger)
    info |= _get_gpu_data()
    return info


def _get_os_info():
    return {
        'system_name': platform.system(),
        'system_release': platform.release(),
        'system_version': platform.version(),
        'system_architecture': platform.machine(),
    }


def _get_cpu_data():
    cpu_info = get_cpu_info()
    return {
        'cpu_model': cpu_info['brand_raw'],
        'cpu_clock_speed_advertised': cpu_info['hz_advertised'][0],
        'cpu_clock_speed_actual': cpu_info['hz_actual'][0],
        'cpu_logical_cores': psutil.cpu_count(),
        'cpu_physical_cores': psutil.cpu_count(logical=False),
        'cpu_cache_l1_size': cpu_info['l1_data_cache_size'],
        'cpu_cache_l2_size': cpu_info['l2_cache_size'],
        'cpu_cache_l3_size': cpu_info['l3_cache_size'],
    }


def _get_ram_data():
    return {'ram_size_total': psutil.virtual_memory().total}


def _get_disk_data(file_manager, logger):
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
    TODO: This is a bit involved, will do later
    """
    # 'gpu_vendor': self.gpu_vendor,
    # 'gpu_model': self.gpu_model,
    # 'gpu_memory_size': self.gpu_memory_size,
    # 'gpu_clock_speed': self.gpu_clock_speed,
    # 'gpu_compute_units': self.gpu_compute_units,
    # 'gpu_core_count': self.gpu_core_count,
    # 'gpu_driver_version': self.gpu_driver_version

    return {}
