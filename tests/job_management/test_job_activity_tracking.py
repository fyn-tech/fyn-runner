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

# pylint: disable=protected-access

import threading
import time
from unittest.mock import MagicMock

import pytest

from fyn_api_client.models.status_enum import StatusEnum
from fyn_runner.job_management.job_activity_tracking import (
    ActivityState,
    ActiveJobTracker,
    job_status_to_activity_status
)


class TestJobStatusToActivityStatus:
    """Test suite for job_status_to_activity_status function."""

    def test_pending_status_mapping(self):
        """Test that QUEUED status maps to PENDING activity state."""
        result = job_status_to_activity_status(StatusEnum.QD)
        assert result == ActivityState.PENDING

    def test_active_status_mappings(self):
        """Test that all active statuses map to ACTIVE activity state."""
        active_statuses = [
            StatusEnum.PR,
            StatusEnum.FR,
            StatusEnum.RN,
            StatusEnum.PD,
            StatusEnum.CU,
            StatusEnum.UR
        ]

        for status in active_statuses:
            result = job_status_to_activity_status(status)
            assert result == ActivityState.ACTIVE, f"Status {status} should map to ACTIVE"

    def test_complete_status_mappings(self):
        """Test that all completion statuses map to COMPLETE activity state."""
        complete_statuses = [
            StatusEnum.SD,
            StatusEnum.FD,
            StatusEnum.FS,
            StatusEnum.FM,
            StatusEnum.FO,
            StatusEnum.FE
        ]

        for status in complete_statuses:
            result = job_status_to_activity_status(status)
            assert result == ActivityState.COMPLETE, f"Status {status} should map to COMPLETE"

    def test_uploading_input_resources_status_raises_error(self):
        """Test that uploading input resources status enum raises RuntimeError."""
        with pytest.raises(RuntimeError, match="The runner is does not support jobs "
                           "which are in the uploading input resources state"):
            job_status_to_activity_status(StatusEnum.UI)

    def test_unknown_status_raises_error(self):
        """Test that unknown status enum raises ValueError."""
        # Create a mock unknown status
        unknown_status = MagicMock()
        unknown_status.name = "UNKNOWN_STATUS"

        with pytest.raises(ValueError, match="Unknown Status"):
            job_status_to_activity_status(unknown_status)


class TestActiveJobTracker:
    """Test suite for ActiveJobTracker class."""

    @pytest.fixture
    def job_tracker(self):
        """Create a fresh ActiveJobTracker instance for testing."""
        return ActiveJobTracker()

    @pytest.fixture
    def mock_active_job(self):
        """Create a mock job with active status."""
        job = MagicMock()
        job.id = "active-job-123"
        job.status = StatusEnum.RN
        return job

    @pytest.fixture
    def mock_completed_job(self):
        """Create a mock job with completed status."""
        job = MagicMock()
        job.id = "completed-job-456"
        job.status = StatusEnum.SD
        return job

    @pytest.fixture
    def mock_pending_job(self):
        """Create a mock job with pending status."""
        job = MagicMock()
        job.id = "pending-job-789"
        job.status = StatusEnum.QD
        return job

    def test_initialization(self, job_tracker):
        """Test that ActiveJobTracker initializes correctly."""
        assert isinstance(job_tracker._lock, type(threading.RLock()))
        assert len(job_tracker._active_jobs) == 0
        assert len(job_tracker._completed_jobs) == 0

    def test_add_active_job(self, job_tracker, mock_active_job):
        """Test adding a job with active status."""
        job_tracker.add_job(mock_active_job)

        assert job_tracker.is_active(mock_active_job.id)
        assert not job_tracker.is_completed(mock_active_job.id)
        assert mock_active_job.id in job_tracker.get_active_job_ids()

    def test_add_completed_job(self, job_tracker, mock_completed_job):
        """Test adding a job with completed status."""
        job_tracker.add_job(mock_completed_job)

        assert job_tracker.is_completed(mock_completed_job.id)
        assert not job_tracker.is_active(mock_completed_job.id)
        assert mock_completed_job.id in job_tracker.get_completed_job_ids()

    def test_add_pending_job_raises_error(self, job_tracker, mock_pending_job):
        """Test that adding a pending job raises RuntimeError."""
        with pytest.raises(RuntimeError, match="Cannot add pending job.*use queue instead"):
            job_tracker.add_job(mock_pending_job)

    def test_update_active_to_completed(self, job_tracker, mock_active_job):
        """Test updating job from active to completed status."""
        # Arrange
        job_tracker.add_job(mock_active_job)
        assert job_tracker.is_active(mock_active_job.id)

        # Act
        job_tracker.update_job_status(mock_active_job.id, StatusEnum.SD)

        # Assert
        assert job_tracker.is_completed(mock_active_job.id)
        assert not job_tracker.is_active(mock_active_job.id)
        assert mock_active_job.status == StatusEnum.SD

    def test_update_completed_to_active(self, job_tracker, mock_completed_job):
        """Test updating job from completed to active status."""
        # Arrange
        job_tracker.add_job(mock_completed_job)
        assert job_tracker.is_completed(mock_completed_job.id)

        # Act
        job_tracker.update_job_status(mock_completed_job.id, StatusEnum.RN)

        # Assert
        assert job_tracker.is_active(mock_completed_job.id)
        assert not job_tracker.is_completed(mock_completed_job.id)
        assert mock_completed_job.status == StatusEnum.RN

    def test_update_active_to_active(self, job_tracker, mock_active_job):
        """Test updating job status within active category."""
        # Arrange
        job_tracker.add_job(mock_active_job)
        original_status = mock_active_job.status

        # Act
        job_tracker.update_job_status(mock_active_job.id, StatusEnum.PR)

        # Assert
        assert job_tracker.is_active(mock_active_job.id)
        assert mock_active_job.status == StatusEnum.PR
        assert mock_active_job.status != original_status

    def test_update_completed_to_completed(self, job_tracker, mock_completed_job):
        """Test updating job status within completed category."""
        # Arrange
        job_tracker.add_job(mock_completed_job)
        original_status = mock_completed_job.status

        # Act
        job_tracker.update_job_status(mock_completed_job.id, StatusEnum.FD)

        # Assert
        assert job_tracker.is_completed(mock_completed_job.id)
        assert mock_completed_job.status == StatusEnum.FD
        assert mock_completed_job.status != original_status

    def test_update_unknown_job_raises_error(self, job_tracker):
        """Test that updating unknown job raises RuntimeError."""
        with pytest.raises(RuntimeError, match="Unknown job.*cannot update status"):
            job_tracker.update_job_status("unknown-job-id", StatusEnum.RN)

    def test_update_job_in_both_collections_raises_error(self, job_tracker, mock_active_job):
        """Test that job existing in both collections raises RuntimeError."""
        # Manually create corrupted state for testing
        job_tracker._active_jobs[mock_active_job.id] = mock_active_job
        job_tracker._completed_jobs[mock_active_job.id] = mock_active_job

        with pytest.raises(RuntimeError, match="Job.*is both active and complete.*data corruption"):
            job_tracker.update_job_status(mock_active_job.id, StatusEnum.SD)

    def test_remove_active_job(self, job_tracker, mock_active_job):
        """Test removing an active job."""
        # Arrange
        job_tracker.add_job(mock_active_job)
        assert job_tracker.is_active(mock_active_job.id)

        # Act
        result = job_tracker.remove_job(mock_active_job.id)

        # Assert
        assert result is True
        assert not job_tracker.is_active(mock_active_job.id)
        assert not job_tracker.is_tracked(mock_active_job.id)

    def test_remove_completed_job(self, job_tracker, mock_completed_job):
        """Test removing a completed job."""
        # Arrange
        job_tracker.add_job(mock_completed_job)
        assert job_tracker.is_completed(mock_completed_job.id)

        # Act
        result = job_tracker.remove_job(mock_completed_job.id)

        # Assert
        assert result is True
        assert not job_tracker.is_completed(mock_completed_job.id)
        assert not job_tracker.is_tracked(mock_completed_job.id)

    def test_remove_unknown_job(self, job_tracker):
        """Test removing a job that doesn't exist."""
        result = job_tracker.remove_job("unknown-job-id")
        assert result is False

    def test_get_active_jobs(self, job_tracker, mock_active_job):
        """Test retrieving all active jobs."""
        job_tracker.add_job(mock_active_job)

        active_jobs = job_tracker.get_active_jobs()
        assert len(active_jobs) == 1
        assert mock_active_job in active_jobs

    def test_get_completed_jobs(self, job_tracker, mock_completed_job):
        """Test retrieving all completed jobs."""
        job_tracker.add_job(mock_completed_job)

        completed_jobs = job_tracker.get_completed_jobs()
        assert len(completed_jobs) == 1
        assert mock_completed_job in completed_jobs

    def test_get_job_count_empty(self, job_tracker):
        """Test job count when tracker is empty."""
        counts = job_tracker.get_job_count()

        assert counts['active'] == 0
        assert counts['completed'] == 0
        assert counts['total'] == 0

    def test_get_job_count_with_jobs(self, job_tracker, mock_active_job, mock_completed_job):
        """Test job count with active and completed jobs."""
        # Add multiple jobs
        job_tracker.add_job(mock_active_job)
        job_tracker.add_job(mock_completed_job)

        # Add another active job
        another_active_job = MagicMock()
        another_active_job.id = "active-job-999"
        another_active_job.status = StatusEnum.PR
        job_tracker.add_job(another_active_job)

        counts = job_tracker.get_job_count()

        assert counts['active'] == 2
        assert counts['completed'] == 1
        assert counts['total'] == 3

    def test_is_tracked_active_job(self, job_tracker, mock_active_job):
        """Test is_tracked for active job."""
        job_tracker.add_job(mock_active_job)
        assert job_tracker.is_tracked(mock_active_job.id)

    def test_is_tracked_completed_job(self, job_tracker, mock_completed_job):
        """Test is_tracked for completed job."""
        job_tracker.add_job(mock_completed_job)
        assert job_tracker.is_tracked(mock_completed_job.id)

    def test_is_tracked_unknown_job(self, job_tracker):
        """Test is_tracked for unknown job."""
        assert not job_tracker.is_tracked("unknown-job-id")

    def test_thread_safety_concurrent_access(self, job_tracker):
        """Test thread safety with concurrent operations."""
        results = []
        errors = []

        def add_jobs():
            """Worker function to add jobs concurrently."""
            try:
                for i in range(10):
                    job = MagicMock()
                    job.id = f"thread-job-{threading.current_thread().ident}-{i}"
                    job.status = StatusEnum.RN
                    job_tracker.add_job(job)
                    results.append(job.id)
            except Exception as e:
                errors.append(e)

        def update_jobs():
            """Worker function to update job statuses concurrently."""
            try:
                time.sleep(0.01)  # Small delay to let some jobs be added
                for job_id in list(job_tracker.get_active_job_ids()):
                    if job_tracker.is_active(job_id):
                        job_tracker.update_job_status(job_id, StatusEnum.SD)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=add_jobs)
            threads.append(thread)
            thread.start()

        update_thread = threading.Thread(target=update_jobs)
        threads.append(update_thread)
        update_thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety test failed with errors: {errors}"

        # Verify job counts are reasonable
        counts = job_tracker.get_job_count()
        assert counts['total'] >= 0
        assert counts['active'] >= 0
        assert counts['completed'] >= 0

    def test_thread_safety_remove_operations(self, job_tracker):
        """Test thread safety with concurrent remove operations."""
        # Add initial jobs
        job_ids = []
        for i in range(20):
            job = MagicMock()
            job.id = f"remove-test-job-{i}"
            job.status = StatusEnum.RN if i % 2 == 0 else StatusEnum.SD
            job_tracker.add_job(job)
            job_ids.append(job.id)

        errors = []

        def remove_jobs():
            """Worker function to remove jobs concurrently."""
            try:
                for job_id in job_ids[::2]:  # Remove every other job
                    job_tracker.remove_job(job_id)
            except Exception as e:
                errors.append(e)

        def update_jobs():
            """Worker function to update jobs concurrently."""
            try:
                for job_id in job_ids[1::2]:  # Update the other half
                    if job_tracker.is_tracked(job_id):
                        job_tracker.update_job_status(job_id, StatusEnum.FD)
            except Exception as e:
                errors.append(e)

        # Run concurrent operations
        remove_thread = threading.Thread(target=remove_jobs)
        update_thread = threading.Thread(target=update_jobs)

        remove_thread.start()
        update_thread.start()

        remove_thread.join()
        update_thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent remove test failed with errors: {errors}"

        # Verify final state is consistent
        counts = job_tracker.get_job_count()
        active_ids = job_tracker.get_active_job_ids()
        completed_ids = job_tracker.get_completed_job_ids()

        # No job should be in both collections
        assert len(set(active_ids) & set(completed_ids)) == 0

        # Total count should match sum of collections
        assert counts['total'] == len(active_ids) + len(completed_ids)
