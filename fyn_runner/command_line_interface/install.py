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

from uuid import UUID
from pathlib import Path

from fyn_api_client.models.runner_manager_runner_register_create_request import RunnerManagerRunnerRegisterCreateRequest

from fyn_runner.config import RunnerConfig
from fyn_runner.server.config import ServerProxyConfig
from fyn_runner.server.server_proxy import ServerProxy
from fyn_runner.utilities.file_manager import FileManager
from fyn_runner.utilities.logging_utilities import create_logger 
from fyn_runner.utilities.config import LoggingConfig 
from fyn_runner.utilities.config_manager import ConfigManager 

def add_subparser_args(sub_parser):
    sub_parser.add_argument('--use_defaults',
        required=False,
        action='store_true',
        help="Skip default options during runner installation")

    sub_parser.add_argument('-d', '--description',
        required=False,
        action='store_true',
        help="Adds context description for each setting")

def install(args):


    
    new_config = ConfigManager(Path("./test.yaml"), RunnerConfig)
    new_config.generate_interactively(args.use_defaults, args.description)
    new_config.save()
    print("\n\nDone")
    exit(1)

    runner_id = input("Enter Runner ID: ").strip()
    try:
        uuid_runner_id = UUID(runner_id)
    except ValueError:
        print("Error: Invalid UUID format")
        print("Aborting setup.")
        exit(1)        


    add_to_startup = input("Add Fyn-Runner to startup apps [y/n]:").strip() or None

    print("Begining setup...")

    # Setup directory
    file_manager = FileManager(work_dirctory)
    try:
        print(f"Setting up working directory: {file_manager.runner_dir}")
        file_manager.init_directories(False)
    except Exception as e:
        print(f"Error while setting update working directory:\n{e}")
        print("Aborting setup.")
        exit(1)

    # Create a Logger    
    logging_config = LoggingConfig()
    logger = create_logger(file_manager.log_dir, **logging_config.model_dump())

    # Register
    try:
        server_proxy_config = ServerProxyConfig(id=uuid_runner_id, token=token)
        server_proxy = ServerProxy(logger, None, server_proxy_config, False)
        runner_api = server_proxy.create_runner_manager_api()
        request = RunnerManagerRunnerRegisterCreateRequest(id=runner_id, token=token)
        runner_info = runner_api.runner_manager_runner_register_create( request )
        
    except Exception as e:
        print(f"Error registering with remote server:\n{e}")
        print("Aborting setup.")
        exit(1) 
    print(f"{runner_info}")


    # Setup config file

    # Add startup apps


    print("Setup completed successfully.")
    # name = input(f"Runner name [{default_name}]: ").strip() or default_name

def uninstall(args):
    pass
