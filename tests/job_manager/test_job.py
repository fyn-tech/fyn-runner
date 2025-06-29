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

from unittest.mock import MagicMock, patch
import pytest

from fyn_runner.job_manager.job import Job


class TestJob:
    """Test suite for the Job class functions."""

    @pytest.fixture
    def mock_file_manager(self):
        """Create a mock FileManager."""
        file_manager = MagicMock()
        return file_manager

    @pytest.fixture
    def mock_job_info_runner(self):
        """Create a mock JobInfoRunner."""
        job_info_runner = MagicMock()
        job_info_runner.id = "test-job-123"
        return job_info_runner

    @pytest.fixture
    def mock_server_proxy(self):
        """Create a mock server proxy."""
        server_proxy = MagicMock()
        return server_proxy

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = MagicMock()
        return logger

    @pytest.fixture
    def mock_active_job_tracker(self):
        """Create a mock ActiveJobTracker"""
        active_job_tracker = MagicMock()
        return active_job_tracker

    def test_initialization(self, mock_job_info_runner, mock_server_proxy, mock_file_manager,
                            mock_logger, mock_active_job_tracker):
        """Test default initialisation of Job."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        assert job._job_result is None

        assert job.file_manager == mock_file_manager
        assert job.case_directory is None
        assert job.logger == mock_logger
        assert job.server_proxy == mock_server_proxy

        assert job.application is None
        assert job.job == mock_job_info_runner
        assert job._job_activity_tracker == mock_active_job_tracker
        assert job._app_reg_api == mock_server_proxy.create_application_registry_api.return_value
        assert job._job_api == mock_server_proxy.create_job_manager_api.return_value

        # Ensure the creation objects were called
        mock_server_proxy.create_application_registry_api.assert_called_once()
        mock_server_proxy.create_job_manager_api.assert_called_once()

    def test_launch_nominal(self, mock_job_info_runner, mock_server_proxy, mock_file_manager,
                            mock_logger, mock_active_job_tracker):
        """We just test that the control flow (i.e. we log completion and call all steps)."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        with (patch.object(job, '_setup') as mock_setup, patch.object(job, '_run') as mock_run,
              patch.object(job, '_clean_up') as mock_cleanup):
            job.launch()

            mock_setup.assert_called_once()
            mock_run.assert_called_once()
            mock_cleanup.assert_called_once()

        mock_logger.info.assert_called_once_with(f"Job {mock_job_info_runner.id} completed.")

    def test_launch_exception(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """We just test that the control flow (i.e. an exceptions are caught and reported)."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        with (patch.object(job, '_setup') as mock_setup,
              patch.object(job, '_run') as mock_run,
              patch.object(job, '_clean_up') as mock_cleanup,
              patch.object(job, '_update_status') as mock_update_status,
              patch('fyn_runner.job_manager.job.StatusEnum') as mock_status_enum):

            mock_run.side_effect = Exception("run failed")
            mock_status_enum.FE = "FAILED_EXCEPTION"

            job.launch()
            mock_setup.assert_called_once()
            mock_run.assert_called_once()
            mock_cleanup.assert_not_called()
            mock_update_status.assert_called_once_with(mock_status_enum.FE)

        mock_logger.error.assert_called_once_with(f"Job {mock_job_info_runner.id} "
                                                  f"suffered a runner exception: run failed")
