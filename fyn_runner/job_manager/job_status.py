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

from enum import Enum, auto


class JobStatus(Enum):
    """Job status"""

    # Pre execution
    QUEUED = auto()  # Inactive and waiting for compute resources.
    PREPARING = auto()  # Setting up directories for simulation, and other pre-validation
    FETCHING_RESOURCES = auto()  # Downloading input files/data

    # Execution
    STARTING = auto()  # launching of job
    RUNNING = auto()  # main job execution and wait
    PAUSED = auto()   # User requested pause

    # Completion states
    CLEANING_UP = auto()  # Post-processing, archiving results, prepare results for reporting
    UPLOADING_RESULTS = auto()  # Send requested result resources
    SUCCEEDED = auto()  # nominal execution of pipe line

    # Failure states
    FAILED = auto()  # generic failure of pipe line (or non zero return of primary job)
    FAILED_RESOURCE_ERROR = auto()  # Issue with acquiring required resources
    FAILED_TERMINATED = auto()  # User requested termination
    FAILED_TIMEOUT = auto()  # Job terminated for exceeding allocated time
