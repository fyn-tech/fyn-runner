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
from fyn_runner.job_management.job_activity_tracking import ActiveJobTracker
from fyn_runner.utilities.file_manager import FileManager


class Job:
    """Manages the complete lifecycle of a remote job execution.

    The Job class orchestrates the full pipeline for executing applications/simulations remotely,
    including resource fetching, execution, and result uploading. It handles communication with a
    backend server through various API clients and manages local file operations through a file
    manager.

    The class implements a three-phase execution model:
    1. Setup: Creates working directory and fetches application files and resources
    2. Execution: Runs the application with proper logging and monitoring
    3. Cleanup: Uploads results and reports final status to the backend

    Note:
        The 'launch' operation is expected to be executed in its own thread since it
        is a blocking operation that can take significant time to complete. The class
        maintains job status throughout execution and reports progress to the backend.

    Warning:
        Currently only Python scripts are fully supported for application execution.
        Other application types (shell scripts, binaries) will raise NotImplementedError.

    Todo:
        - Implement WebSocket listeners for real-time commands (terminate, pause, etc.)
        - Add support for shell scripts and binary applications
        - Implement non-blocking execution with progress reporting
        - Expand result upload to include all output files, not just logs
        - Add job pause/resume functionality
        - Better error handling
    """

    def __init__(self, job: JobInfoRunner, server_proxy: ServerProxy, file_manager: FileManager,
                 logger: Logger, activity_tracker: ActiveJobTracker):

        # Python object attributes
        self._job_result: subprocess.CompletedProcess = None

        # Runner object attributes
        self.file_manager: FileManager = file_manager
        self.case_directory: Path = None
        self.logger: Logger = logger
        self.server_proxy: ServerProxy = server_proxy

        # OpenAPI client attributes
        self.application: App = None
        self.job: JobInfoRunner = job
        self._job_activity_tracker: ActiveJobTracker = activity_tracker
        self._app_reg_api = server_proxy.create_application_registry_api()
        self._job_api = server_proxy.create_job_manager_api()

    def launch(self):
        """ Function to launch the application, this triggers the full 'pipeline' execution of the
        job, including fetching resources, running the application, and uploading results.

        Raises:
            Exception: If anything goes wrong during the execution of the job.

        Note:
            1. Job status changed to 'Runner Exception' if an exception was raised.
            2. Its expected that the Job is fully initialised when the function is called.
        """

        try:
            self._setup()
            self._run()
            self._clean_up()
            self.logger.info(f"Job {self.job.id} completed.")
        except Exception as e:
            self.logger.error(f"Job {self.job.id} suffered a runner exception: {e}")
            self._update_status(StatusEnum.FE)

    def _setup(self):
        """ Control function delegating to various setup operations to other functions to facilitate
        application setup (i.e. pre-execution).

        Note:
            1. Job status changed to 'Preparing'
            2. Do not catch in this function, catch either in launch or in the sub functions.
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
        """ Control function delegating to a further execution functions to facilitate application
        execution.

        Note:
            1. Do not catch in this function, catch either in launch or in the sub functions.

        TODO:
            Presently the run application is blocking, it is desired to rather have it non-blocking
            and have the Job report on progress.
        """

        # 1. launch job
        self.logger.info(f"Job {self.job.id} is in run")
        self._run_application()

        # 2. report progress
        self.logger.warning("Switch to loop and report progress")

    def _clean_up(self):
        """ Control function delegating to various cleanup operations to other functions to
        facilitate post execution uploading and reporting (i.e. post-execution).

        Note:
            1. Job status changed to 'Clean Up'
            2. Do not catch in this function, catch either in launch or in the sub functions.
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
        """Create a simulation directory, using the file manager, reports the local directory to the
        backend.

        Raises:
            RuntimeError: If it fails to either create a local directory or report the status.
        """

        self.logger.debug(f"Job {self.job.id}: local directory creation")
        try:
            self.case_directory = self.file_manager.request_simulation_directory(self.job.id)
            jir = PatchedJobInfoRunnerRequest(working_directory=str(self.case_directory))
            self._job_api.job_manager_runner_partial_update(self.job.id,
                                                            patched_job_info_runner_request=jir)
        except Exception as e:
            raise RuntimeError(f"Could complete a simulation directory setup: {e}") from e

    def _fetching_simulation_resources(self):
        """Fetches both the application file and all related job resources for the application file
        and places them in the Job's working directory.

        Raises:
            RuntimeError: If it fails to fetch the application binary/script.
            RuntimeError: If it fails to fetch a job resource.

        Note:
            1. Job status changed to 'Fetching Resources'
        """

        self.logger.debug(f"Job {self.job.id}: fetching program and other remote resources")
        self._update_status(StatusEnum.FR)

        # 1. Fetch application
        try:
            file = self._app_reg_api.application_registry_program_retrieve(self.job.application_id)
            self._handle_application(file)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch application: {e}") from e

        # 2. Fetch other files
        try:
            for resource in self.job.resources:
                resource_data = self._job_api.job_manager_resources_runner_retrieve(resource)
                file_content = self._download_resource_file(resource_data.id)
                file_path = self.case_directory / resource_data.filename
                with open(file_path, 'wb') as f:
                    f.write(file_content)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch job files: {e}") from e

    def _handle_application(self, file):
        """Function to interpret the received application file and save it to the working directory.

        Raises:
            NotImplementedError: Any thing other than a python script is not yet implemented.
        """

        match self.application.type:
            case TypeEnum.PYTHON:
                with open(self.case_directory / (self.application.name + ".py"), "w",
                          encoding='utf-8') as f:
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

    def _download_resource_file(self, resource_id: str) -> bytearray:
        """Download the actual resource/file contents from the backend and returns the byte array.

        Args:
            resource_id(str): The UUID of the resource to download (should belong to the job).

        Return:
            Byte array of the fetch resource

        Raises:
            RuntimeError: Re-raises any backend fetch into a runtime error.
        """
        try:
            return self._job_api.job_manager_resources_runner_download_retrieve(resource_id)
        except Exception as e:
            raise RuntimeError(e) from e

    # ----------------------------------------------------------------------------------------------
    #  Run/Execution Functions
    # ----------------------------------------------------------------------------------------------

    def _run_application(self):
        """The actual execution of the application. Will block until the execution is over. The
        application logs are piped into an job_id_out.log and job_id_err.log file.

        Raises:
            RuntimeError: If the runner fails to launch the application (not if the application
                crashes).

        Note:
            1. Job status changed to 'Running'
        """

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
                    shell=True,
                    check=False
                )
            self.logger.info(f"Job {self.job.id} completed.")
        except Exception as e:
            raise RuntimeError(f"Exception while executing application: {e}") from e

    # ----------------------------------------------------------------------------------------------
    #  Clean up functions Functions
    # ----------------------------------------------------------------------------------------------

    def _upload_application_results(self):
        """Uploads outputted application files and logs.

        Raises:
            RuntimeError: If the runner fails to launch the application (not if the application
                crashes).

        Notes:
            1. Job status is updated to 'Uploading Resources'.

        TODO:
            1. Currently only log files are updated, but a full system of file collection and
               uploading will be need.
        """

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
            raise RuntimeError(f"Could complete job resource upload: {e}") from e

    def _report_application_result(self):
        """Reports the final state of the run application (determined by the exit code).

        Returns:
            None

        Notes:
            1. Job status is updated to either 'Success' or 'Failed' based on the exit code.
        """

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
        """Sets the local job status and reports the status to the backend server using the Job API
        client.

        Args:
            status(StatusEnum): The new status the job must be placed into.

        Returns:
            None

        Raises:
            Exception: If the runner failed to report the status to the backend. If the job fails to
            report the local status is not updated.
        """

        try:
            jir = PatchedJobInfoRunnerRequest(status=status)
            self._job_api.job_manager_runner_partial_update(self.job.id,
                                                            patched_job_info_runner_request=jir)
            self.logger.debug(f"Job {self.job.id} reported status: {status.value}")
        except Exception as e:
            self.logger.error(f"Job {self.job.id} failed to report status: {e}")
            return

        self.job.status = status
        if self._job_activity_tracker.is_tracked(self.job.id):
            self._job_activity_tracker.update_job_status(self.job.id, jir.status)
        else:
            self._job_activity_tracker.add_job(self.job)
