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


import argparse

from fyn_runner.config import RunnerConfig
from fyn_runner.server.server_proxy import ServerProxy
from fyn_runner.system.collection import collect_system_info
from fyn_runner.utilities.config_manager import ConfigManager
from fyn_runner.utilities.file_manager import FileManager
from fyn_runner.utilities.logging_utilities import create_logger


def main():
    """Runner entry point."""

    parser = argparse.ArgumentParser(
        prog='fyn_runner',
        description="Application to execute simulations and interact with the local and remote "
        "fyn-tech infrastructure.")
    parser.add_argument(
        '-c',
        '--config',
        default=FileManager().config_dir /
        "fyn_runner_config.yaml",
        type=str,
        help="The path to the config file")
    args = parser.parse_args()

    # Boot-up of runner
    logger = None
    proxy = None
    try:
        config = ConfigManager(args.config, RunnerConfig)
        config.load()
        file_manager = FileManager(config.file_manager.working_directory)
        logger = create_logger(file_manager.log_dir, config.logging.level, config.logging.develop)
        config.attach_logger(logger)
        proxy = ServerProxy(logger, file_manager, config.server_proxy)
        collect_system_info(logger, file_manager, proxy)
    except Exception as e:
        if logger:
            logger.critical(f"Fatal error encounter on startup: {e}")
        else:
            print(f"Critical error, before logger start: {e}")

    logger.info("Initialisation complete, handing program control to the JobManager")
    import time
    time.sleep(5)

    proxy._running = False
    logger.info("Runner terminating")


if __name__ == "__main__":
    main()
