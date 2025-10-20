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

from unittest.mock import MagicMock, patch, call
from queue import Empty
import itertools
import math
import pytest

from fyn_api_client.models.status_enum import StatusEnum
from fyn_runner.job_management.job_manager import JobManager
from fyn_runner.job_management.job_activity_tracking import ActivityState


class TestJobManager:
    """Test suite for the JobManager class."""

    @pytest.fixture
    def mock_server_proxy(self):
        """Create a mock server proxy with API methods."""
        server_proxy = MagicMock()
        job_api = MagicMock()
        server_proxy.create_job_manager_api.return_value = job_api
        return server_proxy

    @pytest.fixture
    def mock_file_manager(self):
        """Create a mock file manager."""
        return MagicMock()

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_configuration(self):
        """Create a mock configuration."""
        config = MagicMock()
        config.max_cpu = 4
        config.max_concurrent_jobs = 2
        config.max_main_loop_count = math.inf
        return config

    @pytest.fixture
    def mock_job_info(self):
        """Create a mock JobInfoRunner."""
        job_info = MagicMock()
        job_info.id = "test-job-123"
        job_info.priority = 5
        job_info.status = MagicMock()
        return job_info

    def test_initialization(self, mock_server_proxy, mock_file_manager, mock_logger,
                            mock_configuration):
        """Test JobManager initialization."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker,
              patch.object(JobManager, '_fetch_jobs') as mock_fetch):

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

            # Verify API creation
            mock_server_proxy.create_job_manager_api.assert_called_once()

            # Verify attributes
            assert manager.job_api == mock_server_proxy.create_job_manager_api.return_value
            assert manager.server_proxy == mock_server_proxy
            assert manager.file_manager == mock_file_manager
            assert manager.logger == mock_logger

            # Verify queue and tracker initialization
            mock_queue.assert_called_once()
            mock_tracker.assert_called_once()

            # Verify state data
            assert manager._is_running is True
            assert manager._max_cpu_usage == 4
            assert manager._max_concurrent_jobs == 2
            assert manager._max_main_loop_count == math.inf

            # Verify fetch jobs was called
            mock_fetch.assert_called_once()

    def test_fetch_jobs_success(self, mock_server_proxy, mock_file_manager, mock_logger,
                                mock_configuration):
        """Test successful job fetching with mixed job statuses."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        # Increment the counter
        counter_start = 3
        manager._counter = itertools.count(start=counter_start)

        # Create mock jobs
        pending_job = MagicMock()
        pending_job.priority = 5
        pending_job.status = StatusEnum.QD

        active_job = MagicMock()
        active_job.status = StatusEnum.RN

        completed_job = MagicMock()
        completed_job.status = StatusEnum.SD

        manager.job_api.job_manager_runner_list.return_value = [pending_job, active_job,
                                                                completed_job]

        # Mock job_status_to_activity_status
        with (patch('fyn_runner.job_management.job_manager.jat.job_status_to_activity_status')
              as mock_status_converter):
            mock_status_converter.side_effect = [
                ActivityState.PENDING,
                ActivityState.ACTIVE,
                ActivityState.COMPLETE]

            # Mock queue size and job count
            mock_queue.qsize.return_value = 1
            mock_tracker.get_job_count.return_value = {
                'active': 1, 'completed': 1, 'total': 2
            }

            manager._fetch_jobs()

            # Verify API call
            manager.job_api.job_manager_runner_list.assert_called_once()

            # Verify pending job was queued
            mock_queue.put.assert_called_once_with((5, counter_start, pending_job))

            # Verify active and completed jobs were added to tracker
            assert mock_tracker.add_job.call_count == 2
            mock_tracker.add_job.assert_any_call(active_job)
            mock_tracker.add_job.assert_any_call(completed_job)

            # Verify logging
            mock_logger.info.assert_any_call("Fetching jobs")
            mock_logger.info.assert_any_call(
                "Loaded: {'active': 1, 'completed': 1, 'queued': 1, 'total': 3}"
            )

    def test_fetch_jobs_api_failure(self, mock_server_proxy, mock_file_manager, mock_logger,
                                    mock_configuration):
        """Test job fetching when API call fails."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue'),
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker'),
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):
            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        manager.job_api.job_manager_runner_list.side_effect = Exception("API error")

        manager._fetch_jobs()

        # Verify error was logged but didn't crash
        mock_logger.info.assert_any_call("Fetching jobs")
        mock_logger.error.assert_called_once()
        assert "API error" in str(mock_logger.error.call_args)

    def test_fetch_jobs_empty_response(self, mock_server_proxy, mock_file_manager, mock_logger,
                                       mock_configuration):
        """Test job fetching with no jobs returned."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        manager.job_api.job_manager_runner_list.return_value = []

        # Mock queue size and job count for empty state
        mock_queue.qsize.return_value = 0
        mock_tracker.get_job_count.return_value = {
            'active': 0, 'completed': 0, 'total': 0
        }

        manager._fetch_jobs()

        # Verify logging
        mock_logger.info.assert_any_call("Fetching jobs")
        mock_logger.info.assert_any_call(
            "Loaded: {'active': 0, 'completed': 0, 'queued': 0, 'total': 0}"
        )

    def test_attached_job_listener(self, mock_server_proxy, mock_file_manager, mock_logger,
                                   mock_configuration):
        """Test WebSocket listener attachment."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        # Verify observer was registered
        mock_server_proxy.register_observer.assert_called_once_with(
            "new_job", manager.fetch_and_add)

    def test_fetch_and_add_success(self, mock_server_proxy, mock_file_manager, mock_logger,
                                   mock_configuration):
        """Test successful fetch and add of new job from WebSocket."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        # Set up counter
        counter_start = 5
        manager._counter = itertools.count(start=counter_start)

        # Create mock job info
        mock_job_info = MagicMock()
        mock_job_info.id = 123
        mock_job_info.priority = 7

        # Mock the API response
        manager.job_api.job_manager_users_retrieve.return_value = mock_job_info

        # Create WebSocket message
        job_ws = {'job_id': 123}

        # Call fetch_and_add
        manager.fetch_and_add(job_ws)

        # Verify API was called with correct job_id
        manager.job_api.job_manager_users_retrieve.assert_called_once_with(id=123)

        # Verify job was added to queue with correct format
        mock_queue.put.assert_called_once_with((7, counter_start, mock_job_info))

    def test_fetch_and_add_missing_job_id(self, mock_server_proxy, mock_file_manager, mock_logger,
                                          mock_configuration):
        """Test fetch_and_add handles missing job_id in WebSocket message."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        manager.fetch_and_add({})

        # Verify error logged and nothing queued
        mock_logger.error.assert_called_once()
        assert "missing 'job_id'" in mock_logger.error.call_args[0][0]
        mock_queue.put.assert_not_called()

    def test_fetch_and_add_api_failure(self, mock_server_proxy, mock_file_manager, mock_logger,
                                       mock_configuration):
        """Test fetch_and_add handles API failure gracefully."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        manager.job_api.job_manager_users_retrieve.side_effect = Exception("API error")

        manager.fetch_and_add({'job_id': 123})

        # Verify error logged and nothing queued
        mock_logger.error.assert_called()
        assert "Failed to retrieve job 123" in mock_logger.error.call_args[0][0]
        mock_queue.put.assert_not_called()

    def test_main_loop_launch_job(self, mock_server_proxy, mock_file_manager, mock_logger,
                                  mock_configuration):
        """Test main loop successfully launching a job."""
        mock_configuration.max_main_loop_count = 2  # Limit loop iterations

        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

            mock_job_info = MagicMock()
            mock_queue.get.return_value = (5, 0, mock_job_info)  # returns infinite mock_job_infos
            mock_tracker.get_active_jobs.return_value = []  # No active jobs

        with (patch.object(manager, '_cleanup_finished_threads') as mock_cleanup,
              patch.object(manager, '_launch_new_job') as mock_launch):

            manager.main()

            # Verify cleanup and launch were called
            assert mock_cleanup.call_count == 2  # Called in each iteration
            mock_launch.assert_has_calls([call(mock_job_info), call(mock_job_info)])

            # Verify logging
            assert mock_logger.debug.call_count >= 2  # "New tick" messages
            mock_logger.info.assert_called_with("Reach max main loop count 2, exiting main loop.")

    def test_main_loop_at_capacity(self, mock_server_proxy, mock_file_manager, mock_logger,
                                   mock_configuration):
        """Test main loop when at maximum concurrent job capacity."""
        mock_configuration.max_main_loop_count = 1
        mock_configuration.max_concurrent_jobs = 2

        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        # Simulate 2 active jobs (at capacity)
        mock_tracker.get_active_jobs.return_value = [MagicMock(), MagicMock()]

        with (patch.object(manager, '_cleanup_finished_threads'),
              patch.object(manager, '_launch_new_job') as mock_launch,
              patch('time.sleep') as mock_sleep):

            manager.main()

            # Verify no job was launched
            mock_launch.assert_not_called()

            # Verify sleep was called
            mock_sleep.assert_called_with(5)

            # Verify capacity message
            mock_logger.debug.assert_any_call("At capacity, number of active jobs: 2")

    def test_main_loop_no_pending_jobs(self, mock_server_proxy, mock_file_manager, mock_logger,
                                       mock_configuration):
        """Test main loop when no pending jobs are available."""
        mock_configuration.max_main_loop_count = 1

        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        mock_tracker.get_active_jobs.return_value = []
        mock_queue.get.side_effect = Empty()

        with (patch.object(manager, '_cleanup_finished_threads'),
              patch.object(manager, '_launch_new_job') as mock_launch):

            manager.main()

            # Verify no job was launched
            mock_launch.assert_not_called()

            # Verify waiting message
            mock_logger.debug.assert_any_call("No pending jobs, waiting...")

    def test_main_loop_exception_handling(self, mock_server_proxy, mock_file_manager, mock_logger,
                                          mock_configuration):
        """Test main loop exception handling."""
        mock_configuration.max_main_loop_count = 1

        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        mock_tracker.get_active_jobs.side_effect = Exception("Tracker error")

        with (patch.object(manager, '_cleanup_finished_threads'),
              patch('time.sleep') as mock_sleep):

            manager.main()

            # Verify error was logged
            mock_logger.error.assert_any_call("Error in main loop: Tracker error")

            # Verify sleep was called after error
            mock_sleep.assert_called_with(5)

    def test_launch_new_job_success(self, mock_server_proxy, mock_file_manager, mock_logger,
                                    mock_configuration, mock_job_info):
        """Test successful job launch."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        with (patch('fyn_runner.job_management.job_manager.Job') as mock_job_class,
              patch('fyn_runner.job_management.job_manager.Thread') as mock_thread_class):

            mock_job = MagicMock()
            mock_job_class.return_value = mock_job

            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            manager._launch_new_job(mock_job_info)

            # Verify Job creation
            mock_job_class.assert_called_once_with(
                mock_job_info, manager.server_proxy, manager.file_manager,
                manager.logger, mock_tracker
            )

            # Verify Thread creation and start
            mock_thread_class.assert_called_once_with(target=mock_job.launch)
            mock_thread.start.assert_called_once()

            # Verify thread tracking
            assert manager._observer_threads[mock_job_info.id] == mock_thread

            # Verify queue task done
            mock_queue.task_done.assert_called_once()

            # Verify logging
            mock_logger.info.assert_called_once_with(f"Launching new job {mock_job_info.id}")

    def test_launch_new_job_failure_with_recovery(self, mock_server_proxy, mock_file_manager,
                                                  mock_logger, mock_configuration, mock_job_info):
        """Test job launch failure with re-queuing."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        # Set up activity tracker
        mock_tracker.is_tracked.return_value = True

        with (patch('fyn_runner.job_management.job_manager.Thread') as mock_thread_class):

            mock_thread = MagicMock()
            mock_thread.start.side_effect = Exception("Thread start error")
            mock_thread_class.return_value = mock_thread

            count_start = 1
            manager._counter = itertools.count(start=count_start)  # check counter is 'maintained'
            manager._launch_new_job(mock_job_info)

            # Verify error was logged
            mock_logger.error.assert_any_call("Failed to launch new job: Thread start error")

            # Verify re-queuing
            manager.job_api.job_manager_runner_partial_update.assert_called_once()
            call_args = manager.job_api.job_manager_runner_partial_update.call_args
            assert call_args[0][0] == mock_job_info.id
            request_obj = call_args[1]['patched_job_info_request']
            assert hasattr(request_obj, 'status')

            # Verify job was re-added to queue
            re_add_item = (mock_job_info.priority, count_start + 1, mock_job_info)
            mock_queue.put.assert_called_once_with(re_add_item)
            assert mock_queue.task_done.call_count == 1  # Ensure only one task done is called.

            # Verify job was removed from tracker
            mock_tracker.remove_job.assert_called_once_with(mock_job_info.id)

            # Verify status was updated
            assert mock_job_info.status == StatusEnum.QD

    def test_launch_new_job_recovery_failure(self, mock_server_proxy, mock_file_manager,
                                             mock_logger, mock_configuration, mock_job_info):
        """Test job launch failure where recovery also fails."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue') as mock_queue_class,
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker') as mock_tracker_class,
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):

            # Create mocked instances
            mock_queue = MagicMock()
            mock_tracker = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_tracker_class.return_value = mock_tracker

            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        with (patch('fyn_runner.job_management.job_manager.Job',
                    side_effect=Exception("Job error")),
              patch('fyn_runner.job_management.job_manager.PatchedJobInfoRunnerRequest',
                    side_effect=Exception("API error"))):

            manager._launch_new_job(mock_job_info)

            # Verify both errors were logged
            mock_logger.error.assert_any_call("Failed to launch new job: Job error")
            assert any("Job manager failed to reset job" in str(call)
                       for call in mock_logger.error.call_args_list)

    def test_cleanup_finished_threads_with_finished_jobs(self, mock_server_proxy, mock_file_manager,
                                                         mock_logger, mock_configuration):
        """Test cleanup of finished job threads."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue'),
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker'),
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):
            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        # Create mock threads
        alive_thread = MagicMock()
        alive_thread.is_alive.return_value = True

        dead_thread1 = MagicMock()
        dead_thread1.is_alive.return_value = False

        dead_thread2 = MagicMock()
        dead_thread2.is_alive.return_value = False

        manager._observer_threads = {
            "job-alive": alive_thread,
            "job-dead-1": dead_thread1,
            "job-dead-2": dead_thread2
        }

        manager._cleanup_finished_threads()

        # Verify only alive thread remains
        assert len(manager._observer_threads) == 1
        assert "job-alive" in manager._observer_threads
        assert "job-dead-1" not in manager._observer_threads
        assert "job-dead-2" not in manager._observer_threads

        # Verify logging
        mock_logger.debug.assert_any_call("Cleaning up finished thread for job job-dead-1")
        mock_logger.debug.assert_any_call("Cleaning up finished thread for job job-dead-2")
        mock_logger.info.assert_called_once_with("Cleaned up 2 finished threads")

    def test_cleanup_finished_threads_no_finished_jobs(self, mock_server_proxy, mock_file_manager,
                                                       mock_logger, mock_configuration):
        """Test cleanup when no threads are finished."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue'),
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker'),
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):
            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        # All threads are alive
        alive_thread1 = MagicMock()
        alive_thread1.is_alive.return_value = True

        alive_thread2 = MagicMock()
        alive_thread2.is_alive.return_value = True

        manager._observer_threads = {
            "job-1": alive_thread1,
            "job-2": alive_thread2
        }

        manager._cleanup_finished_threads()

        # Verify no threads were removed
        assert len(manager._observer_threads) == 2

        # Verify no cleanup logging
        mock_logger.info.assert_not_called()

    def test_cleanup_finished_threads_empty(self, mock_server_proxy, mock_file_manager,
                                            mock_logger, mock_configuration):
        """Test cleanup when no threads exist."""
        with (patch('fyn_runner.job_management.job_manager.PriorityQueue'),
              patch('fyn_runner.job_management.job_manager.ActiveJobTracker'),
              patch.object(JobManager, '_fetch_jobs', lambda self: None)):
            manager = JobManager(mock_server_proxy, mock_file_manager, mock_logger,
                                 mock_configuration)

        manager._observer_threads = {}

        manager._cleanup_finished_threads()

        # Should complete without error
        assert len(manager._observer_threads) == 0
        mock_logger.info.assert_not_called()
