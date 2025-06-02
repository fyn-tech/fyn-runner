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
from fyn_api_client.models.job_info import JobInfo
from fyn_api_client.models.patched_job_info_request import PatchedJobInfoRequest
from fyn_runner.server.server_proxy import ServerProxy
from fyn_runner.server.message import Message
from fyn_runner.job_manager.job_activity_tracking import ActiveJobTracker, ActivityState


class Job:  # this is the SimulationMonitor (in its own thread)
    def __init__(self, job: JobInfo, server_proxy: ServerProxy, case_directory: Path,
                 logger: Logger, activtiy_tracker:ActiveJobTracker):
        self.case_directory: Path = case_directory
        self.job: JobInfo = job
        self.logger: Logger = logger
        self.server_proxy: ServerProxy = server_proxy
        self.job_api = server_proxy.create_job_manager_api()
        self._job_activity_tracker: ActiveJobTracker = activtiy_tracker

    def _launch(self):
        self._setup()
        self._run()
        self._clean_up()

    def _setup(self):

        # 1. Create job directoy
        jir = PatchedJobInfoRequest(status=StatusEnum.PR)
        self.job.status = StatusEnum.PR
        self.job_api.job_manager_runner_partial_update(self.job.id, patched_job_info_request=jir)
        self._job_activity_tracker.add_job(self.job) # only update if sever is happy

        # 2. Go to the backend to get job files/resources

        # 3. add listeners for commands from server

        pass

    def _run(self):
        # 1. launch job
        jir =  PatchedJobInfoRequest(status=StatusEnum.RN)
        self.job_api.job_manager_runner_partial_update(self.job.id, patched_job_info_request=jir)
        self._job_activity_tracker.update_job_status(self.job.id, jir.status)
        # 2. Loop
        # 2. report progress
        # 3. terminate/update if requested (via handlers)
        pass

    def _clean_up(self):
        jir =  PatchedJobInfoRequest(status=StatusEnum.CU)
        self.job_api.job_manager_runner_partial_update(self.job.id, patched_job_info_request=jir)
        self._job_activity_tracker.update_job_status(self.job.id, jir.status)
        # 1. report progress
        # 2. deregister listeners
                 
        
        pass
