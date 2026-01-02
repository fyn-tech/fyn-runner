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
from fyn_runner.server.server_proxy import ServerProxy
from fyn_runner.utilities.file_manager import FileManager
from fyn_runner.utilities.logging_utilities import create_logger 
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

def install(args, unknown_args):

    if unknown_args is not None:
        print(f"Unknown args parsed: {unknown_args}")

    print("Welcome to the Fynbos Technologies Runner, Fyn-Runner, installation!")
    print("Begining setup...")

    # 1. Get User to Create Config
    try:
        yaml_name = input("Enter name of this runner, "
                          "(recommended to use registration name): ").strip()
        
    except Exception as e: 
        print(f"error {e} \nAborting setup")
        exit(1)
      
    new_config = ConfigManager(Path(f"./{yaml_name}.yaml"), RunnerConfig)
    new_config.generate_interactively(args.use_defaults, args.description)

    # 2. Bootstrap the File Manager, and create the directories
    file_manager = None
    try:
        print(f"Setting up runner install directory...")
        file_manager = FileManager(**new_config.file_manager.model_dump())
        new_config.config_path = file_manager.config_dir / Path(f"./{yaml_name}.yaml")
        file_manager.init_directories(False, True) # Ok if we simulation directory exists.
        print(f"completed")
    except Exception as e:
        print(f"Error while setting install directory:\n{e}")
        print("Aborting setup.")
        exit(1)
    
    # 3. Create a Logger    
    logger = create_logger(file_manager.log_dir, **new_config.logging.model_dump())

    # 4. Register
    try:
        print(f"Attempting to contact Fyn-Tech server and register runner...")
        server_proxy = ServerProxy(logger, file_manager, new_config.server_proxy, False)
        runner_api = server_proxy.create_runner_manager_api()
        request = RunnerManagerRunnerRegisterCreateRequest(id=server_proxy.id, 
                                                           token=server_proxy.token)
        runner_info = runner_api.runner_manager_runner_register_create( request )
        new_config._config.server_proxy.name = runner_info.name
        new_config._config.server_proxy.token = runner_info.token
        print(f"completed")
    except Exception as e:
        print(f"Error registering with remote server:\n{e}")
        file_manager.remove_directories()
        print("Aborting setup.")
        exit(1) 

    # 5. Save the config, and set the default config path
    new_config.save()
    file_manager.create_default_config_path_file(file_manager.config_dir)

    # 6. Setup application serveice, add startup apps
    add_to_startup = input("Add Fyn-Runner to startup apps [y/n]:").strip() or None


    print("Setup completed successfully.")

def uninstall(args, unknown_args):

    if unknown_args is not None:
        print(f"Unknown args parsed: {unknown_args}")

    remove_simulation_directory = input("Remove simulation directory "
                                        "(potential to lose data!) [y/n]:").strip() or None


    print("Begining uninstall...")


    # 1. Get the associated config, and create the required objects.
    try:
        yaml_name = input("Enter name of this runner, "
                          "(recommended to use registration name): ").strip()
        
    except Exception as e: 
        print(f"error {e} \n FIXME")
        exit(1)
      
    new_config = ConfigManager(Path(f"./{yaml_name}.yaml"), RunnerConfig)
    file_manager = FileManager(**new_config.file_manager.model_dump())
    logger = create_logger(file_manager.log_dir, **new_config.logging.model_dump())

    # 2. Deregister/delete the runner from the server
    try:
        print(f"Attempting to delete/register runner with Fyn-Tech server...")
        server_proxy = ServerProxy(logger, file_manager, new_config.server_proxy, False)
        runner_api = server_proxy.create_runner_manager_api()
        runner_info = runner_api.runner_manager_runner_destroy( server_proxy.id )
        print(f"completed")
    except Exception as e:
        print(f"Error deleteing with remote server:\n{e}")
        print(f"Manual removal of remote runner, though the web UI, is requried.")


    # 3. Remove all assocaiated directories
    try:
        print(f"Removing runner directories...")
        file_manager.remove_directories(remove_simulation_directory)
        file_manager.delete_default_config_path_file()
        print(f"completed")
    except Exception as e:
        print(f"Error while removing runner directories:\n{e}")
        print(f"Manual removal of directories required.")
        
    # 4. Remove the service from the machine

    print("Uninstall completed successfully.")
    pass
