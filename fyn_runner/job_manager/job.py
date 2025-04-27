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
import uuid

from fyn_runner.job_manager.job_status import JobStatus
from fyn_runner.server.server_proxy import ServerProxy
from fyn_runner.server.message import Message


class Job:  # this is the SimulationMonitor (in its own thread)
    def __init__(self, id, server_proxy: ServerProxy, case_directory: Path, logger: Logger):
        self.id: uuid.uuid4 = id
        self.case_directory: Path = case_directory
        self._status: JobStatus = JobStatus.QUEUED  # We start queued

        self.logger: Logger = logger
        self.server_proxy: ServerProxy = server_proxy

    def launch(self):
        self.setup()
        self.run()
        self.finalize()

    def setup(self):

        # 1. Create job directoy
        # 2. Go to the backend to get job files/resources
        # 3. add listeners for commands from server
        pass

    def run():
        # 1. launch job
        # 2. Loop
        # 2. report progress
        # 3. terminate/update if requested (via handlers)
        pass

    def clean_up():
        # 1. report progress
        # 2. deregister listeners

        pass

    @property
    def status(self):
        return self._status

    @property.setter
    def status(self, new_status):
        old_status = self._status
        self.status = new_status
        if old_status != new_status:
            self._report_status_change()

    def _report_status_change(self):
        """
        Warning -> rather use status setter
        """
        self.server_proxy.push_message(
            Message(
            )
        )
