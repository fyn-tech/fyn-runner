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
import sys
import subprocess
import shutil
import platform

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
    file_manager.create_default_config_path_file(new_config.config_path)

    # 6. Setup application service, add startup apps
    add_to_startup = input("Add Fyn-Runner to startup apps [y/n]: ").strip().lower()

    if add_to_startup == 'y' or add_to_startup == 'yes':
        try:
            setup_auto_start()
            print("Auto-start enabled successfully.")
        except Exception as e:
            print(f"Warning: Could not enable auto-start: {e}")
            print("You can manually enable auto-start later.")

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
    try:
        print("Removing auto-start configuration...")
        remove_auto_start()
        print("completed")
    except Exception as e:
        print(f"Warning: Could not remove auto-start: {e}")
        print("You may need to manually remove the startup configuration.")

    print("Uninstall completed successfully.")


# ----------------------------------------------------------------------------------------------
#  Auto-start Configuration Functions
# ----------------------------------------------------------------------------------------------

def setup_auto_start():
    """
    Configure the runner to start automatically on system boot.

    Raises:
        Exception: If auto-start setup fails
    """
    system = platform.system()

    if system == "Linux":
        _setup_systemd_service()
    elif system == "Darwin":
        _setup_launchd_service()
    elif system == "Windows":
        _setup_windows_task()
    else:
        raise Exception(f"Unsupported platform: {system}")


def remove_auto_start():
    """
    Remove auto-start configuration.

    Raises:
        Exception: If removal fails
    """
    system = platform.system()

    if system == "Linux":
        _remove_systemd_service()
    elif system == "Darwin":
        _remove_launchd_service()
    elif system == "Windows":
        _remove_windows_task()
    else:
        raise Exception(f"Unsupported platform: {system}")


def _setup_systemd_service():
    """Setup systemd user service for Linux."""
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    service_file = systemd_dir / "fyn-runner.service"

    # Get the path to fyn-runner executable
    fyn_runner_path = shutil.which('fyn-runner')
    if not fyn_runner_path:
        raise Exception("fyn-runner executable not found in PATH")

    service_content = f"""[Unit]
Description=Fyn Runner Daemon
After=network.target

[Service]
Type=simple
ExecStart={fyn_runner_path} service start
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=default.target
"""

    service_file.write_text(service_content)

    # Enable the service (don't start immediately)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "fyn-runner.service"], check=True)


def _remove_systemd_service():
    """Remove systemd user service."""
    service_file = Path.home() / ".config" / "systemd" / "user" / "fyn-runner.service"

    # Stop and disable the service
    subprocess.run(["systemctl", "--user", "stop", "fyn-runner.service"], check=False)
    subprocess.run(["systemctl", "--user", "disable", "fyn-runner.service"], check=False)

    # Remove the service file
    if service_file.exists():
        service_file.unlink()

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)


def _setup_launchd_service():
    """Setup launchd service for macOS."""
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)

    plist_file = launch_agents_dir / "com.fynbos.fyn-runner.plist"

    # Get the path to fyn-runner executable
    fyn_runner_path = shutil.which('fyn-runner')
    if not fyn_runner_path:
        raise Exception("fyn-runner executable not found in PATH")

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fynbos.fyn-runner</string>
    <key>ProgramArguments</key>
    <array>
        <string>{fyn_runner_path}</string>
        <string>service</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/Library/Logs/fyn-runner-error.log</string>
    <key>StandardOutPath</key>
    <string>{Path.home()}/Library/Logs/fyn-runner.log</string>
</dict>
</plist>
"""

    plist_file.write_text(plist_content)


def _remove_launchd_service():
    """Remove launchd service."""
    plist_file = Path.home() / "Library" / "LaunchAgents" / "com.fynbos.fyn-runner.plist"

    # Unload the service
    if plist_file.exists():
        subprocess.run(["launchctl", "unload", str(plist_file)], check=False)
        plist_file.unlink()


def _setup_windows_task():
    """Setup Windows Task Scheduler task."""
    # Get the path to fyn-runner executable
    fyn_runner_path = shutil.which('fyn-runner')
    if not fyn_runner_path:
        raise Exception("fyn-runner executable not found in PATH")

    # Create task using schtasks command
    task_name = "FynRunner"

    # Create the task
    subprocess.run([
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'"{fyn_runner_path}" service start',
        "/sc", "onlogon",
        "/rl", "highest",
        "/f"  # Force create (overwrite if exists)
    ], check=True, shell=True)


def _remove_windows_task():
    """Remove Windows Task Scheduler task."""
    task_name = "FynRunner"

    # Delete the task
    subprocess.run([
        "schtasks", "/delete",
        "/tn", task_name,
        "/f"  # Force delete
    ], check=False, shell=True)
