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

import threading
from enum import Enum

from fyn_api_client.models.status_enum import StatusEnum


class ActivityState(Enum):
    """Activity status (local) for jobs."""
    PENDING = 'pending'
    ACTIVE = 'active'
    COMPLETE = 'complete'


def job_status_to_activity_status(status):
    """Map between API status and local activity status.

    Converts OpenAPI client status enumerators to local ActivityState enums for internal tracking.
    This mapping helps determine whether a job should be considered as using active system
    resources. Note that the runner is not designed to support/or fetch  jobs in the 'uploading
    input resources' state.

    Args:
        status(StatusEnum): The OpenAPI client job status enumerator.

    Returns:
        ActivityState: The corresponding local activity status enum.

    Raises:
        RuntimeError: If an job status enumerator is in the Uploading Input Resources state.
        ValueError: If an unknown job status enumerator is provided.
    """
    match (status):
        case StatusEnum.UI:
            raise RuntimeError("The runner is does not support jobs which are in the "
                               f"uploading input resources state: {status}")

        case StatusEnum.QD:
            return ActivityState.PENDING

        case StatusEnum.PR:
            return ActivityState.ACTIVE
        case StatusEnum.FR:
            return ActivityState.ACTIVE
        case StatusEnum.RN:
            return ActivityState.ACTIVE
        case StatusEnum.PD:
            return ActivityState.ACTIVE
        case StatusEnum.CU:
            return ActivityState.ACTIVE
        case StatusEnum.UR:
            return ActivityState.ACTIVE

        case StatusEnum.SD:
            return ActivityState.COMPLETE
        case StatusEnum.FD:
            return ActivityState.COMPLETE
        case StatusEnum.FS:
            return ActivityState.COMPLETE
        case StatusEnum.FM:
            return ActivityState.COMPLETE
        case StatusEnum.FO:
            return ActivityState.COMPLETE
        case StatusEnum.FE:
            return ActivityState.COMPLETE
        case _:
            raise ValueError(f"Unknown Status: {status}")


class ActiveJobTracker:
    """Thread-safe tracker for monitoring job states and resource usage across the runner system.

    The activity tracker manages jobs in two main categories: actively running jobs that are
    consuming system resources, and completed jobs that have finished execution. This helps the
    runner determine resource allocation and cleanup requirements.

    Jobs progress through three activity states:
    1. Pending: Jobs waiting to start (managed by external queue, not tracked here)
    2. Active: Jobs currently using system resources (tracked in _active_jobs)
    3. Complete: Jobs that have finished execution (tracked in _completed_jobs)

    Note:
        All operations are thread-safe using RLock to handle concurrent access from multiple job
        execution threads. The tracker does not handle pending jobs - these should be managed by a
        separate job queue system.

    Warning:
        Jobs cannot be in both active and completed states simultaneously. The tracker will raise
        RuntimeError if data corruption is detected during status updates.

    Todo:
        - Add job priority tracking for resource scheduling
        - Implement job timeout monitoring
        - Add resource usage metrics per job
    """

    def __init__(self):
        """Initialize the activity tracker with empty job collections and thread lock.

        Creates thread-safe collections for active and completed jobs using RLock for concurrent
        access protection.
        """

        self._lock = threading.RLock()
        self._active_jobs = {}    # job_id -> job
        self._completed_jobs = {}  # job_id -> job

    def add_job(self, job):
        """Add a job to tracking based on its current status.

        Automatically determines the appropriate collection (active or completed) based on the job's
        current status and adds it to tracking.

        Args:
            job: Job object with a status attribute to be tracked.

        Raises:
            RuntimeError: If attempting to add a job with PENDING status, which should
                be managed by the job queue instead.
        """

        with self._lock:
            status = job_status_to_activity_status(job.status)
            match (status):
                case ActivityState.PENDING:
                    raise RuntimeError(f"Cannot add pending job {job.id} - use queue instead")
                case ActivityState.ACTIVE:
                    self._active_jobs[job.id] = job
                case ActivityState.COMPLETE:
                    self._completed_jobs[job.id] = job

    def update_job_status(self, job_id, new_status):
        """Update a job's status and move between collections if needed.

        Updates the job's status and automatically moves it between active and completed collections
        based on the new status. Ensures data integrity by validating the job exists and is not in
        multiple collections simultaneously.

        Args:
            job_id: Unique identifier of the job to update.
            new_status: New StatusEnum value for the job.

        Raises:
            RuntimeError: If the job is found in both active and completed collections
                (data corruption).
            RuntimeError: If the job is not found in either collection.
        """

        with self._lock:
            is_active = self.is_active(job_id)
            is_complete = self.is_completed(job_id)

            if is_active and is_complete:
                raise RuntimeError(f"Job {job_id} is both active and complete - data corruption!")

            if not is_active and not is_complete:
                raise RuntimeError(f"Unknown job {job_id} - cannot update status")

            new_activity_state = job_status_to_activity_status(new_status)

            if new_activity_state == ActivityState.ACTIVE and is_complete:
                job = self._completed_jobs.pop(job_id)
                job.status = new_status
                self._active_jobs[job_id] = job

            elif new_activity_state == ActivityState.COMPLETE and is_active:
                job = self._active_jobs.pop(job_id)
                job.status = new_status
                self._completed_jobs[job_id] = job

            elif is_active and new_activity_state == ActivityState.ACTIVE:
                self._active_jobs[job_id].status = new_status
            elif is_complete and new_activity_state == ActivityState.COMPLETE:
                self._completed_jobs[job_id].status = new_status

    def remove_job(self, job_id):
        """Remove job from tracking entirely for cleanup.

        Removes the job from both active and completed collections. Used for final cleanup when jobs
        are no longer needed for monitoring.

        Args:
            job_id: Unique identifier of the job to remove.

        Returns:
            bool: True if the job was found and removed, False if not found.
        """

        with self._lock:
            removed = False
            if job_id in self._active_jobs:
                del self._active_jobs[job_id]
                removed = True
            if job_id in self._completed_jobs:
                del self._completed_jobs[job_id]
                removed = True
            return removed

    def get_active_job_ids(self):
        """Get list of active job IDs.

        Returns:
            list: List of job IDs currently in active state.
        """

        with self._lock:
            return list(self._active_jobs.keys())

    def get_active_jobs(self):
        """Get all currently active jobs.

        Returns:
            list: List of job objects currently in active state.
        """

        with self._lock:
            return list(self._active_jobs.values())

    def is_active(self, job_id):
        """Check if job is currently active.

        Args:
            job_id: Unique identifier of the job to check.

        Returns:
            bool: True if the job is in active state, False otherwise.
        """

        with self._lock:
            return job_id in self._active_jobs

    def get_completed_job_ids(self):
        """Get list of completed job IDs.

        Returns:
            list: List of job IDs currently in completed state.
        """

        with self._lock:
            return list(self._completed_jobs.keys())

    def get_completed_jobs(self):
        """Get all completed jobs.

        Returns:
            list: List of job objects currently in completed state.
        """

        with self._lock:
            return list(self._completed_jobs.values())

    def is_completed(self, job_id):
        """Check if job is completed.

        Args:
            job_id: Unique identifier of the job to check.

        Returns:
            bool: True if the job is in completed state, False otherwise.
        """

        with self._lock:
            return job_id in self._completed_jobs

    def get_job_count(self):
        """Get job counts for system monitoring and resource planning.

        Returns:
            dict: Dictionary containing 'active', 'completed', and 'total' job counts.
        """
        with self._lock:
            return {
                'active': len(self._active_jobs),
                'completed': len(self._completed_jobs),
                'total': len(self._active_jobs) + len(self._completed_jobs)
            }

    def is_tracked(self, job_id):
        """Check if the job is being tracked in either active or completed collections.

        Args:
            job_id: Unique identifier of the job to check.

        Returns:
            bool: True if the job is being tracked, False otherwise.
        """
        return self.is_active(job_id) or self.is_completed(job_id)
