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
import subprocess

from fyn_api_client.models.status_enum import StatusEnum
from fyn_api_client.models.resource_type_enum import ResourceTypeEnum
from fyn_api_client.models.job_info_runner import JobInfoRunner
from fyn_api_client.models.app import App
from fyn_api_client.models.type_enum import TypeEnum
from fyn_api_client.models.patched_job_info_runner_request import PatchedJobInfoRunnerRequest

from fyn_runner.server.server_proxy import ServerProxy
from fyn_runner.job_manager.job_activity_tracking import ActiveJobTracker
from fyn_runner.utilities.file_manager import FileManager


class Job:  # this is the SimulationMonitor (in its own thread)
    def __init__(self, job: JobInfoRunner, server_proxy: ServerProxy, file_manager: FileManager,
                 logger: Logger, activity_tracker: ActiveJobTracker):
        self.file_manager: FileManager = file_manager
        self.case_directory: Path
        self.job: JobInfoRunner = job
        self.application: App
        self.logger: Logger = logger
        self.server_proxy: ServerProxy = server_proxy
        self._app_reg_api = server_proxy.create_application_registry_api()
        self._job_api = server_proxy.create_job_manager_api()
        self._job_activity_tracker: ActiveJobTracker = activity_tracker
        self._job_result: subprocess.CompletedProcess = None

    def launch(self):
        try:
            self._setup()
            self._run()
            self._clean_up()
            self.logger.info(f"Job {self.job.id} completed.")
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
        self.logger.warning("Attached listeners to be implemented")

    def _run(self):
        """
        Don't catch in this function -> catch either in launch or in the sub functions.
        """
        # 1. launch job
        self.logger.info(f"Job {self.job.id} is in run")
        self._run_application()

        # 2. report progress
        self.logger.warning("Switch to loop and report progress")

    def _clean_up(self):
        """
        Don't catch in this function -> catch either in launch or in the sub functions.
        """

        self.logger.info(f"Job {self.job.id} is in clean up")
        self._update_status(StatusEnum.CU)

        # 1. Upload results
        self._upload_application_results()

        # 2. report progress
        self._report_application_result()

        # 3. deregister listeners
        self.logger.warning("Deregistration not implemented")

    # ----------------------------------------------------------------------------------------------
    #  Setup Functions
    # ----------------------------------------------------------------------------------------------

    def _setup_local_simulation_directory(self):
        """ Create a simulation directory. """

        self.logger.debug(f"Job {self.job.id}: local directory creation")
        try:
            self.case_directory = self.file_manager.request_simulation_directory(self.job.id)
            jir = PatchedJobInfoRunnerRequest(working_directory=str(self.case_directory))
            self._job_api.job_manager_runner_partial_update(self.job.id,
                                                            patched_job_info_runner_request=jir)
        except Exception as e:
            raise RuntimeError(f"Could complete a simulation directory setup: {e}")

    def _fetching_simulation_resources(self):
        """  """
        self.logger.debug(f"Job {self.job.id}: fetching program and other remote resources")
        self._update_status(StatusEnum.FR)

        try:
            file = self._app_reg_api.application_registry_program_retrieve(self.job.application_id)
            self._handle_application(file)
        except Exception as e:
            raise Exception(f"Failed to fetch application: {e}")

        # 2. Fetch other files
        try:
            for resource in self.job.resources:
                resource_data = self._job_api.job_manager_resources_runner_retrieve(resource)
                file_content = self._download_resource_file(resource_data.id)
                file_path = self.case_directory / resource_data.filename
                with open(file_path, 'wb') as f:
                    f.write(file_content)
        except Exception as e:
            raise Exception(f"Failed to fetch job files: {e}")

    def _handle_application(self, file):

        match self.application.type:
            case TypeEnum.PYTHON:
                with open(self.case_directory / (self.application.name + ".py"), "w") as f:
                    f.write(file.decode('utf-8'))
            case TypeEnum.SHELL:
                raise NotImplementedError("Shell script handling not yet supported.")
            case TypeEnum.LINUX_BINARY:
                raise NotImplementedError("Linux binary handling not yet supported.")
            case TypeEnum.WINDOWS_BINARY:
                raise NotImplementedError("Windows binary handling not yet supported.")
            case TypeEnum.UNKNOWN:
                raise NotImplementedError("Cannot process received binary file, consult backend.")
            case _:
                raise NotImplementedError("Undefined binary case type.")

    def _download_resource_file(self, resource_id: str) -> bytes:
        """Download the actual file content for a resource"""
        try:
            # Option 1: If your auto-generated client has the download method
            return self._job_api.job_manager_resources_runner_download_retrieve(resource_id)
        except AttributeError:
            # Option 2: Direct HTTP request to download endpoint
            import requests

            # Get the base URL and token from your server proxy
            base_url = self.server_proxy.base_url  # Adjust based on your ServerProxy implementation
            token = self.server_proxy.token  # Adjust based on your ServerProxy implementation

            download_url = f"{base_url}/api/job_manager/resources/runner/{resource_id}/download/"
            headers = {'Authorization': f'Token {token}'}

            response = requests.get(download_url, headers=headers)
            response.raise_for_status()

            return response.content

    # ----------------------------------------------------------------------------------------------
    #  Run/Execution Functions
    # ----------------------------------------------------------------------------------------------

    def _upload_application_results(self):
        self._update_status(StatusEnum.UR)
        try:
            for logs in ["_out.log", "_err.log"]:
                file_path = self.case_directory / (str(self.job.id) + logs)
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                self._job_api.job_manager_resources_runner_create(
                    str(self.job.id),
                    file_content,
                    resource_type=ResourceTypeEnum.LOG,
                    description="log file",
                    original_file_path=str(file_path))
        except Exception as e:
            raise RuntimeError(f"Could complete job resource upload: {e}")

    def _run_application(self):

        self._update_status(StatusEnum.RN)
        try:
            command = self.job.executable + " "
            command += " ".join(self.job.command_line_args)
            out_log = self.case_directory / f"{self.job.id}_out.log"
            err_log = self.case_directory / f"{self.job.id}_err.log"

            self.logger.info(f"Launching job {self.job.id}: {command}")
            with open(out_log, "w", encoding="utf-8") as stdout_file, \
                    open(err_log, "w", encoding="utf-8") as stderr_file:
                self._job_result = subprocess.run(
                    command,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    text=True,
                    bufsize=1,
                    cwd=self.case_directory,
                    shell=True
                )
            self.logger.info(f"Job {self.job.id} completed.")
        except Exception as e:
            raise RuntimeError(f"Exception while executing application: {e}")

    # ----------------------------------------------------------------------------------------------
    #  Clean up functions Functions
    # ----------------------------------------------------------------------------------------------

    def _report_application_result(self):

        jir = PatchedJobInfoRunnerRequest(exit_code=self._job_result.returncode)
        self._job_api.job_manager_runner_partial_update(self.job.id,
                                                        patched_job_info_runner_request=jir)

        if self._job_result.returncode == 0:
            self._update_status(StatusEnum.SD)
        else:  # Failed
            self._update_status(StatusEnum.FD)

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
