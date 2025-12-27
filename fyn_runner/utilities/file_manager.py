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


import appdirs
import os
from pathlib import Path
import shutil

from fyn_runner.constants import APP_NAME, APP_AUTHOR, DEFAULT_WORK_DIRECTORY

class FileManager:
    """
    Manages file locations and directory structures for the runner.
    """

    def __init__(self, working_directory, simulation_directory):
        """
        Initialize the FileManager, by setting and then creating the runner's directory structure.
        Existing files/folders are ok.

        Args:
            baseworking_directory_dir: Override for base directory (if None, uses appdirs)
            simulation_directory: Location of the simulation directory (where cases are stored)
        """

        # Set up directories using appdirs if base_dir not specified
        if working_directory == Path(DEFAULT_WORK_DIRECTORY):
            self._runner_dir = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR))
            self._cache_dir = Path(appdirs.user_cache_dir(APP_NAME, APP_AUTHOR))
            self._config_dir = Path(appdirs.user_config_dir(APP_NAME, APP_AUTHOR))
            self._log_dir = Path(appdirs.user_log_dir(APP_NAME, APP_AUTHOR))
        else:
            self._runner_dir = Path(working_directory)
            self._cache_dir = Path(self._runner_dir / "cache")
            self._config_dir = Path(self._runner_dir / "config")
            self._log_dir = Path(self._runner_dir / "logs")

        # Set default simulation directory, or specifed 
        if simulation_directory == Path("simulations"):
            self._simulation_dir = Path(self._runner_dir / simulation_directory)
        else:
            self._simulation_dir = Path(simulation_directory)

    def init_directories(self, runner_exists_ok=True, sim_exists_ok=True):
        """
        Create folder structure for the runner and simulation directories.
        
        Args:
            runner_exists_ok: Is it ok if the runner directory exists (typically false for install)
            sim_exists_ok: Is it ok if the simulation directory exists
        """
        for directory in [
            self.runner_dir,
            self.cache_dir,
            self.config_dir,
            self.log_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=runner_exists_ok)

        self.simulation_dir.mkdir(parents=True, exist_ok=sim_exists_ok)

    def remove_directories(self, sim_delete=False):
        """
        Removes the directories (and their contents) associated with the runner.
        
        Args:
            sim_delete: Must the simulation directory be deteled (must back up unsaved work), 
                defaults to false.

        Warning:
            This method deletes all folders of the runner and subdirectores and files. Use with 
            care. The removing a simulation directory should only be done once data is backed up.
        
        Note:
            If the simulation directory is empty it will be deleted regardless of sim_delete, 
            rational is its tidier and there is no loss of data.
        """
        for directory in [
            self.runner_dir,
            self.cache_dir,
            self.config_dir,
            self.log_dir,
        ]:
            shutil.rmtree(directory)

        # remove the directory if requested, or if its empty
        if sim_delete or (os.listdir(self.simulation_dir) == 0):
            shutil.rmtree(self.simulation_dir)

    @property
    def runner_dir(self):
        """Path to the runner directory."""
        return self._runner_dir

    @property
    def cache_dir(self):
        """Path to the general cache directory."""
        return self._cache_dir

    @property
    def config_dir(self):
        """Path to the configuration directory."""
        return self._config_dir

    @property
    def log_dir(self):
        """Path to the logging directory."""
        return self._log_dir

    @property
    def simulation_dir(self):
        """Path to the simulation directory."""
        return self._simulation_dir

    @simulation_dir.setter
    def simulation_dir(self, path):
        """
        Set the path to the simulation directory.

        Args
          path(Path): Path to the simulation 'root' directory.
        """
        self._simulation_dir = Path(path)
        self._simulation_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------------------------------------
    #  Simulation Directory Methods
    # ----------------------------------------------------------------------------------------------

    def request_simulation_directory(self, job_id: str):
        """
        Given a job id a new simulation directory is created.

        Args:
          job_id(str): The job id hash as a string.

        Returns:
            Path: To the newly created simulation directory.

        Raises:
            ValueError: If the job_id contains 'path seperators'
            RuntimeError: If directory creation fails.
        """
        if '/' in job_id or '\\' in job_id:
            raise ValueError("job_id cannot contain path separators")

        case_directory = self.simulation_dir / job_id

        try:
            case_directory.mkdir(exist_ok=True, parents=True)
            return case_directory
        except Exception as e:
            raise RuntimeError(f"Failed to create directory {case_directory}: {e}") from e

