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

import psutil

from fyn_runner.server.message import HttpMethod, Message


def check_hardware(logger, file_manager, server_proxy):

    logger.info("Checking system hardware")
    hw_file = file_manager.cache_dir / 'hardware_data.json'

    reader = open(hw_file, 'r', encoding='utf-8')
    saved_hw_data = json.load(reader) if hw_file.exists() else None
    reader.close()
    current_hw_data = _get_hardware_data()

    if current_hw_data != saved_hw_data:
        logger.info("Hardware has been updated, updating server data.")
        logger.debug(f"Hardware data:{current_hw_data}")

        server_proxy.push_message(
            Message.json_message(api_path=f"{server_proxy.api_url}:{server_proxy.api_port}/"
                                 f"hardware_update/{server_proxy.id}", method=HttpMethod.PUT,
                                 json_data=current_hw_data, header=None, priority=0, params=None)
        )
    else:
        logger.debug("No change to hardware")

    with open(hw_file, 'w', encoding='utf-8') as writer:
        json.dump(current_hw_data, writer, ensure_ascii=False, indent=4)


def _get_hardware_data():
    return {
        "memory": _get_memory_info(),
    }


def _get_memory_info():
    ram_info = psutil.virtual_memory()
    return {
        "total_gb": ram_info.total
    }
