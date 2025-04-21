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

import uuid
from pathlib import Path

class Job:  # this is the SimulationMonitor (in its own thread)
    def __init__(self, id, server_proxy, case_directory, logger):
        self.id : uuid.uuid4 = id
        self.case_directory : Path = case_directory
        self.logger = logger
        self.server_proxy = server_proxy

        self.setup()
        self.run()
        self.clean_up()

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