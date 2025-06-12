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

from logging import Logger
from pathlib import Path

from fyn_api_client.models.status_enum import StatusEnum
from fyn_api_client.models.job_info_runner import JobInfoRunner
from fyn_api_client.models.app import App
from fyn_api_client.models.type_enum import TypeEnum
from fyn_api_client.models.patched_job_info_runner_request import PatchedJobInfoRunnerRequest
from fyn_runner.server.server_proxy import ServerProxy
from fyn_runner.job_manager.job_activity_tracking import ActiveJobTracker
from fyn_runner.utilities.file_manager import FileManager
from fyn_runner.job_manager.job_activity_tracking import ActiveJobTracker, ActivityState


class Job:  # this is the SimulationMonitor (in its own thread)
    def __init__(self, job: JobInfoRunner, server_proxy: ServerProxy, file_manager: FileManager,
                 logger: Logger, activtiy_tracker:ActiveJobTracker):
        self.file_manager: FileManager = file_manager
        self.case_directory: Path
        self.job: JobInfoRunner = job
        self.application: App
        self.logger: Logger = logger
        self.server_proxy: ServerProxy = server_proxy
        self._app_reg_api = server_proxy.create_application_registry_api()
        self._job_api = server_proxy.create_job_manager_api()
        self._job_activity_tracker: ActiveJobTracker = activtiy_tracker

    def launch(self):
        try:
            self._setup()
            self._run()
            self._clean_up()
            self._update_status(StatusEnum.SD)
        except Exception as e:
            self.logger.error(f"Job {self.job.id} suffered a runner exception: {e}")
            self._update_status(StatusEnum.FE)

    def _setup(self):
        """
        Don't catch in this function  -> catch either in launch or in the sub fuctions.
        """
        self.logger.info(f"Job {self.job.id} is in setup")
        self._update_status(StatusEnum.PR)
        self.application = self._app_reg_api.application_registry_retrieve(self.job.application_id)

        # 1. Create job directoy
        self._setup_local_simulation_directory()

        # 2. Go to the backend to get job files/resources
        self._fetching_simulation_resources()

        # 3. add listeners for commands from server

    def _run(self):
        """
        Don't catch in this function -> catch either in launch or in the sub fuctions.
        """
        # 1. launch job
        self.logger.info(f"Job {self.job.id} is in run")
        self._update_status(StatusEnum.RN)
        # 2. Loop
        # 2. report progress
        # 3. terminate/update if requested (via handlers)

    def _clean_up(self):
        """
        Don't catch in this function -> catch either in launch or in the sub fuctions.
        """

        self.logger.info(f"Job {self.job.id} is in clean up")
        self._update_status(StatusEnum.CU)
        # 1. report progress
        # 2. deregister listeners

    # ----------------------------------------------------------------------------------------------
    #  Setup Functions
    # ----------------------------------------------------------------------------------------------
    
    def _setup_local_simulation_directory(self):
        """ Create a simulation directory. """
        
        self.logger.debug(f"Job {self.job.id}: local directory creation")
        try: 
            self.case_directory = self.file_manager.request_simulation_directory(self.job.id)
        except Exception as e:
            raise RuntimeError(f"Could not setup a simulation directory: {e}")

    def _fetching_simulation_resources(self):
        """  """
        self.logger.debug(f"Job {self.job.id}: fetching program and other remote resources")
        self._update_status(StatusEnum.FR)
        
        try:
            file = self._app_reg_api.application_registry_program_retrieve(self.job.application_id)
            self._handle_applicaition(file)
        except Exception as e:
            raise Exception(f"Failed to fetch application: {e}")
        
        # 2. Fetch other files
        try:
            print(self.job.resources)
        except Exception as e:
            raise Exception(f"Failed to fetch application: {e}")


    def _handle_applicaition(self, file):

        match self.application.type:
            case TypeEnum.PYTHON:
                with open(self.case_directory / (self.application.name + ".py"), "w") as f:
                    f.write(file.decode('utf-8'))
            case TypeEnum.SHELL:
                raise NotImplemented("Shell script handling not yet supported.")
            case TypeEnum.LINUX_BINARY:
                raise NotImplemented("Linux binary handling not yet supported.")
            case TypeEnum.WINDOWS_BINARY:
                raise NotImplemented("Windows binary handling not yet supported.")
            case TypeEnum.UNKNOWN:
                raise NotImplemented("Cannot process received binary file, consult backend.")
            case _:
                raise NotImplemented("Undefined binary case type.")


    # ----------------------------------------------------------------------------------------------
    #  Misc Functions
    # ----------------------------------------------------------------------------------------------
    
    def _update_status(self, status):

        try:
            self.job.status = status

            # Report status to server
            jir = PatchedJobInfoRunnerRequest(status=status)
            self._job_api.job_manager_runner_partial_update(self.job.id,
                                                            patched_job_info_runner_request=jir)

            # Update local status
            if self._job_activity_tracker.is_tracked(self.job.id):
                self._job_activity_tracker.update_job_status(self.job.id, jir.status)
            else:
                self._job_activity_tracker.add_job(self.job)

            self.logger.debug(f"Job {self.job.id} reported status: {status.value}")
        except Exception as e:
            self.logger.error(f"Job {self.job.id} failed to report status: {e}")
