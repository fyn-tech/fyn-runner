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


from pathlib import Path

import appdirs


class FileManager:
    """
    Manages file locations and directory structures for the runner.
    """

    def __init__(self, base_dir=None, app_name="fyn_runner", app_author="Fyn-Tech"):
        """
        Initialize the FileManager, by setting and then creating the runner's directory structure.
        Existing files/folders are ok.

        Args:
            base_dir: Override for base directory (if None, uses appdirs)
            app_name: Name of the application
            app_author: Author/organization name
        """
        self.app_name = app_name
        self.app_author = app_author

        # Set up directories using appdirs if base_dir not specified
        if base_dir is None:
            self._runner_dir = Path(appdirs.user_data_dir(app_name, app_author))
            self._cache_dir = Path(appdirs.user_cache_dir(app_name, app_author))
            self._config_dir = Path(appdirs.user_config_dir(app_name, app_author))
            self._log_dir = Path(appdirs.user_log_dir(app_name, app_author))
        else:
            self._runner_dir = Path(base_dir)
            self._cache_dir = self._runner_dir / "cache"
            self._config_dir = self._runner_dir / "config"
            self._log_dir = self._runner_dir / "logs"

        # Simulation directory is always in user data (place holder)
        self._simulation_dir = self._runner_dir / "simulations"

    def init_directories(self):
        """Create folder structure."""
        for directory in [
            self.runner_dir,
            self.cache_dir,
            self.config_dir,
            self.log_dir,
            self.simulation_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)

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
