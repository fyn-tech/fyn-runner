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

from unittest.mock import MagicMock, patch, mock_open, call
from pathlib import Path
import pytest

from fyn_runner.job_management.job import Job
from fyn_api_client.models.status_enum import StatusEnum
from fyn_api_client.models.resource_type_enum import ResourceTypeEnum
from fyn_api_client.models.type_enum import TypeEnum
from fyn_api_client.models.patched_job_info_runner_request import PatchedJobInfoRunnerRequest


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
        job_info_runner.application_id = "test-app-123"
        job_info_runner.executable = "python"
        job_info_runner.command_line_args = ["script.py", "--arg1", "value1"]
        job_info_runner.resources = ["resource-1", "resource-2"]
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
        """We just test the control flow (i.e. we log completion and call all steps)."""
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
        """We just test the control flow (i.e. an exceptions are caught and reported)."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        with (patch.object(job, '_setup') as mock_setup,
              patch.object(job, '_run') as mock_run,
              patch.object(job, '_clean_up') as mock_cleanup,
              patch.object(job, '_update_status') as mock_update_status):

            mock_run.side_effect = Exception("run failed")

            job.launch()
            mock_setup.assert_called_once()
            mock_run.assert_called_once()
            mock_cleanup.assert_not_called()
            mock_update_status.assert_called_once_with(StatusEnum.FE)

        mock_logger.error.assert_called_once_with(f"Job {mock_job_info_runner.id} "
                                                  f"suffered a runner exception: run failed")

    def test_setup_nominal(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """We just test the control flow (i.e. all functions called, and logging messages)."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        with (patch.object(job, '_update_status') as mock_update_status,
              patch.object(job, '_setup_local_simulation_directory') as 
              mock_setup_local_simulation_directory,
              patch.object(job, '_fetching_simulation_resources') as 
              mock_fetching_simulation_resources):

            job._setup()
            mock_update_status.assert_called_once_with(StatusEnum.PR)
            mock_setup_local_simulation_directory.assert_called_once()
            mock_fetching_simulation_resources.assert_called_once()

        job._app_reg_api.application_registry_retrieve.assert_called_once_with(
            mock_job_info_runner.application_id
        )
        mock_logger.info.assert_called_once_with(f"Job {mock_job_info_runner.id} is in setup")

    def test_setup_exception(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """We just test the control flow (i.e. an exceptions are NOT caught)."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        with (patch.object(job, '_update_status') as mock_update_status,
              patch.object(job, '_setup_local_simulation_directory') as 
              mock_setup_local_simulation_directory,
              patch.object(job, '_fetching_simulation_resources') as 
              mock_fetching_simulation_resources):

            mock_setup_local_simulation_directory.side_effect = Exception("failed")
            
            with pytest.raises(Exception, match="failed"):
              job._setup()

            mock_update_status.assert_called_once_with(StatusEnum.PR)
            mock_setup_local_simulation_directory.assert_called_once()
            mock_fetching_simulation_resources.assert_not_called()

        job._app_reg_api.application_registry_retrieve.assert_called_once_with(
            mock_job_info_runner.application_id
        )
        mock_logger.info.assert_called_once_with(f"Job {mock_job_info_runner.id} is in setup")

    def test_run_nominal(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """We just test the control flow (i.e. all functions called, and logging messages)."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        with patch.object(job, '_run_application') as mock_run_application:
            job._run()

            mock_run_application.assert_called_once()
        mock_logger.info.assert_called_once_with(f"Job {mock_job_info_runner.id} is in run")

    def test_run_exception(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """We just test the control flow (i.e. an exceptions are NOT caught)."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        with patch.object(job, '_run_application') as mock_run_application:
            mock_run_application.side_effect = Exception("failed")

            with pytest.raises(Exception, match="failed"):
              job._run()

            mock_run_application.assert_called_once()
        mock_logger.info.assert_called_once_with(f"Job {mock_job_info_runner.id} is in run")

    def test_clean_up_nominal(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """We just test the control flow (i.e. all functions called, and logging messages)."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        with (patch.object(job, '_update_status') as mock_update_status,
              patch.object(job, '_upload_application_results') as mock_upload_application_results,
              patch.object(job, '_report_application_result') as mock_report_application_result):

            job._clean_up()

            mock_update_status.assert_called_once_with(StatusEnum.CU)
            mock_upload_application_results.assert_called_once()
            mock_report_application_result.assert_called_once()

        mock_logger.info.assert_called_once_with(f"Job {mock_job_info_runner.id} is in clean up")

    def test_clean_up_exception(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """We just test the control flow (i.e. an exceptions are NOT caught)."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)

        with (patch.object(job, '_update_status') as mock_update_status,
              patch.object(job, '_upload_application_results') as mock_upload_application_results,
              patch.object(job, '_report_application_result') as mock_report_application_result):

            mock_upload_application_results.side_effect = Exception("failed")

            with pytest.raises(Exception, match="failed"):
              job._clean_up()

            mock_update_status.assert_called_once_with(StatusEnum.CU)
            mock_upload_application_results.assert_called_once()
            mock_report_application_result.assert_not_called()

        mock_logger.info.assert_called_once_with(f"Job {mock_job_info_runner.id} is in clean up")

    # ----------------------------------------------------------------------------------------------
    #  Setup Function Tests
    # ----------------------------------------------------------------------------------------------

    def test_setup_local_simulation_directory_success(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test successful creation of local simulation directory."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        
        mock_case_dir = Path(f"/mock/simulations/{mock_job_info_runner.id}")
        mock_file_manager.request_simulation_directory.return_value = mock_case_dir
        
        job._setup_local_simulation_directory()
        
        # Verify directory creation
        mock_file_manager.request_simulation_directory.assert_called_once_with(
            mock_job_info_runner.id
        )
        
        # Verify API update
        job._job_api.job_manager_runner_partial_update.assert_called_once()
        call_args = job._job_api.job_manager_runner_partial_update.call_args
        assert call_args[0][0] == mock_job_info_runner.id
        request_obj = call_args[1]['patched_job_info_runner_request']
        assert hasattr(request_obj, 'working_directory')
        
        # Verify case_directory is set
        assert job.case_directory == mock_case_dir
        
        mock_logger.debug.assert_called_once_with(
            f"Job {mock_job_info_runner.id}: local directory creation"
        )

    def test_setup_local_simulation_directory_failure(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test failure when creating local simulation directory."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        
        mock_file_manager.request_simulation_directory.side_effect = Exception("Directory error")
        
        with pytest.raises(RuntimeError, match="Could complete a simulation directory setup"):
            job._setup_local_simulation_directory()

    def test_fetching_simulation_resources_success(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test successful fetching of simulation resources."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job.case_directory = Path(f"/mock/simulations/{mock_job_info_runner.id}")
        
        # Mock the application file
        mock_app_file = b"print('Hello World')"
        job._app_reg_api.application_registry_program_retrieve.return_value = mock_app_file
        
        # Mock resources
        mock_resource_1 = MagicMock()
        mock_resource_1.id = "resource-1"
        mock_resource_1.filename = "data1.txt"
        
        mock_resource_2 = MagicMock()
        mock_resource_2.id = "resource-2"
        mock_resource_2.filename = "data2.txt"
        
        job._job_api.job_manager_resources_runner_retrieve.side_effect = [
            mock_resource_1, mock_resource_2
        ]
        
        with (patch.object(job, '_update_status') as mock_update_status,
              patch.object(job, '_handle_application') as mock_handle_app,
              patch.object(job, '_download_resource_file') as mock_download,
              patch('builtins.open', mock_open()) as mock_file):
            
            mock_download.side_effect = [b"resource1 content", b"resource2 content"]
            
            job._fetching_simulation_resources()
            
            # Verify status update
            mock_update_status.assert_called_once_with(StatusEnum.FR)
            
            # Verify application fetch
            job._app_reg_api.application_registry_program_retrieve.assert_called_once_with(
                mock_job_info_runner.application_id
            )
            mock_handle_app.assert_called_once_with(mock_app_file)
            
            # Verify resource fetches
            assert job._job_api.job_manager_resources_runner_retrieve.call_count == 2
            assert mock_download.call_count == 2
            
            # Verify files were written
            expected_calls = [
                call(job.case_directory / "data1.txt", 'wb'),
                call(job.case_directory / "data2.txt", 'wb')
            ]
            mock_file.assert_has_calls(expected_calls, any_order=True)

    def test_fetching_simulation_resources_app_failure(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test failure when fetching application file."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        
        job._app_reg_api.application_registry_program_retrieve.side_effect = Exception("API error")
        
        with patch.object(job, '_update_status'):
            with pytest.raises(RuntimeError, match="Failed to fetch application"):
                job._fetching_simulation_resources()

    def test_fetching_simulation_resources_resource_failure(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test failure when fetching job resources."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job.case_directory = Path(f"/mock/simulations/{mock_job_info_runner.id}")
        
        mock_app_file = b"print('Hello World')"
        job._app_reg_api.application_registry_program_retrieve.return_value = mock_app_file
        job._job_api.job_manager_resources_runner_retrieve.side_effect = Exception("Resource error")
        
        with (patch.object(job, '_update_status'),
              patch.object(job, '_handle_application')):
            
            with pytest.raises(RuntimeError, match="Failed to fetch job files"):
                job._fetching_simulation_resources()

    def test_handle_application_python(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test handling of Python application type."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job.case_directory = Path(f"/mock/simulations/{mock_job_info_runner.id}")
        job.application = MagicMock()
        job.application.name = "test_app"
        job.application.type = TypeEnum.PYTHON
        
        file_content = b"print('Hello World')"
        
        with patch('builtins.open', mock_open()) as mock_file:
            job._handle_application(file_content)
            
            # Verify file was written
            mock_file.assert_called_once_with(
                job.case_directory / "test_app.py", "w", encoding='utf-8'
            )
            mock_file().write.assert_called_once_with("print('Hello World')")

    def test_handle_application_not_implemented(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test handling of non-implemented application types."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job.application = MagicMock()
        
        # Test each unimplemented type
        unimplemented_types = [
            (TypeEnum.SHELL, "Shell script"),
            (TypeEnum.LINUX_BINARY, "Linux binary"),
            (TypeEnum.WINDOWS_BINARY, "Windows binary"),
            (TypeEnum.UNKNOWN, "Cannot process")
        ]
        
        for app_type, expected_msg in unimplemented_types:
            job.application.type = app_type
            with pytest.raises(NotImplementedError, match=expected_msg):
                job._handle_application(b"dummy content")

    def test_download_resource_file_success(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test successful resource file download."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        
        expected_content = b"resource content"
        job._job_api.job_manager_resources_runner_download_retrieve.return_value = expected_content
        
        result = job._download_resource_file("resource-123")
        
        assert result == expected_content
        job._job_api.job_manager_resources_runner_download_retrieve.assert_called_once_with(
            "resource-123"
        )

    def test_download_resource_file_failure(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test failure when downloading resource file."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        
        job._job_api.job_manager_resources_runner_download_retrieve.side_effect = Exception(
            "Download failed"
        )
        
        with pytest.raises(RuntimeError, match="Download failed"):
            job._download_resource_file("resource-123")

    # ----------------------------------------------------------------------------------------------
    #  Run Function Tests
    # ----------------------------------------------------------------------------------------------

    def test_run_application_success(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test successful application execution."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job.case_directory = Path(f"/mock/simulations/{mock_job_info_runner.id}")
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with (patch.object(job, '_update_status') as mock_update_status,
              patch('subprocess.run', return_value=mock_result) as mock_subprocess,
              patch('builtins.open', mock_open()) as mock_file):
            
            job._run_application()
            
            # Verify status update
            mock_update_status.assert_called_once_with(StatusEnum.RN)
            
            # Verify subprocess was called correctly
            expected_command = "python script.py --arg1 value1"
            mock_subprocess.assert_called_once_with(
                expected_command,
                stdout=mock_file.return_value,
                stderr=mock_file.return_value,
                text=True,
                bufsize=1,
                cwd=job.case_directory,
                shell=True,
                check=False
            )
            
            # Verify log files were opened
            expected_log_calls = [
                call(job.case_directory / 
                     f"{mock_job_info_runner.id}_out.log", "w", encoding="utf-8"),
                call(job.case_directory / 
                     f"{mock_job_info_runner.id}_err.log", "w", encoding="utf-8")
            ]
            mock_file.assert_has_calls(expected_log_calls, any_order=True)
            
            # Verify result was stored
            assert job._job_result == mock_result
            
            # Verify logging
            mock_logger.info.assert_any_call(
                f"Launching job {mock_job_info_runner.id}: {expected_command}"
            )
            mock_logger.info.assert_any_call(f"Job {mock_job_info_runner.id} completed.")

    def test_run_application_failure(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test failure during application execution."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job.case_directory = Path(f"/mock/simulations/{mock_job_info_runner.id}")
        
        with (patch.object(job, '_update_status'),
              patch('subprocess.run', side_effect=Exception("Subprocess failed")),
              patch('builtins.open', mock_open())):
            
            with pytest.raises(RuntimeError, match="Exception while executing application"):
                job._run_application()

    # ----------------------------------------------------------------------------------------------
    #  Clean Up Function Tests
    # ----------------------------------------------------------------------------------------------

    def test_upload_application_results_success(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test successful upload of application results."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job.case_directory = Path(f"/mock/simulations/{mock_job_info_runner.id}")
        
        # Mock file contents
        out_log_content = b"Output log content"
        err_log_content = b"Error log content"
        
        with (patch.object(job, '_update_status') as mock_update_status,
              patch('builtins.open', mock_open()) as mock_file):
            
            # Set up different return values for each file
            mock_file.return_value.read.side_effect = [out_log_content, err_log_content]
            
            job._upload_application_results()
            
            # Verify status update
            mock_update_status.assert_called_once_with(StatusEnum.UR)
            
            # Verify files were read
            expected_file_calls = [
                call(job.case_directory / f"{mock_job_info_runner.id}_out.log", 'rb'),
                call(job.case_directory / f"{mock_job_info_runner.id}_err.log", 'rb')
            ]
            mock_file.assert_has_calls(expected_file_calls, any_order=True)
            
            # Verify API calls
            assert job._job_api.job_manager_resources_runner_create.call_count == 2
            
            # Verify the content of API calls
            api_calls = job._job_api.job_manager_resources_runner_create.call_args_list
            for call_args in api_calls:
                assert call_args[0][0] == mock_job_info_runner.id  # job ID
                assert call_args[1]['resource_type'] == ResourceTypeEnum.LOG
                assert call_args[1]['description'] == "log file"

    def test_upload_application_results_failure(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test failure when uploading application results."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job.case_directory = Path(f"/mock/simulations/{mock_job_info_runner.id}")
        
        with (patch.object(job, '_update_status'),
              patch('builtins.open', side_effect=Exception("File error"))):
            
            with pytest.raises(RuntimeError, match="Could complete job resource upload"):
                job._upload_application_results()

    def test_report_application_result_success(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test successful reporting of application result with exit code 0."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job._job_result = MagicMock()
        job._job_result.returncode = 0
        
        with patch.object(job, '_update_status') as mock_update_status:
            job._report_application_result()
            
            # Verify API call
            job._job_api.job_manager_runner_partial_update.assert_called_once()
            call_args = job._job_api.job_manager_runner_partial_update.call_args
            assert call_args[0][0] == mock_job_info_runner.id
            request_obj = call_args[1]['patched_job_info_runner_request']
            assert hasattr(request_obj, 'exit_code')
            
            # Verify status update for success
            mock_update_status.assert_called_once_with(StatusEnum.SD)

    def test_report_application_result_failure(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test reporting of application result with non-zero exit code."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        job._job_result = MagicMock()
        job._job_result.returncode = 1
        
        with patch.object(job, '_update_status') as mock_update_status:
            job._report_application_result()
            
            # Verify API call
            job._job_api.job_manager_runner_partial_update.assert_called_once()
            call_args = job._job_api.job_manager_runner_partial_update.call_args
            assert call_args[0][0] == mock_job_info_runner.id
            request_obj = call_args[1]['patched_job_info_runner_request']
            assert hasattr(request_obj, 'exit_code')
            
            # Verify status update for failure
            mock_update_status.assert_called_once_with(StatusEnum.FD)

    # ----------------------------------------------------------------------------------------------
    #  Misc Function Tests
    # ----------------------------------------------------------------------------------------------

    def test_update_status_success_tracked(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test successful status update when job is tracked."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        
        mock_active_job_tracker.is_tracked.return_value = True
        
        job._update_status(StatusEnum.RN)
        
        # Verify API call
        job._job_api.job_manager_runner_partial_update.assert_called_once()
        call_args = job._job_api.job_manager_runner_partial_update.call_args
        assert call_args[0][0] == mock_job_info_runner.id
        request_obj = call_args[1]['patched_job_info_runner_request']
        assert hasattr(request_obj, 'status')
        
        # Verify local status update
        assert job.job.status == StatusEnum.RN
        
        # Verify activity tracker update
        mock_active_job_tracker.is_tracked.assert_called_once_with(mock_job_info_runner.id)
        mock_active_job_tracker.update_job_status.assert_called_once()
        
        # Verify logging
        mock_logger.debug.assert_called_once_with(
            f"Job test-job-123 reported status: {StatusEnum.RN.value}"
        )

    def test_update_status_success_not_tracked(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test successful status update when job is not tracked."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        
        mock_active_job_tracker.is_tracked.return_value = False
        
        job._update_status(StatusEnum.RN)
        
        # Verify activity tracker adds job when not tracked
        mock_active_job_tracker.is_tracked.assert_called_once_with(mock_job_info_runner.id)
        mock_active_job_tracker.add_job.assert_called_once_with(mock_job_info_runner)
        mock_active_job_tracker.update_job_status.assert_not_called()

    def test_update_status_api_failure(
            self,
            mock_job_info_runner,
            mock_server_proxy,
            mock_file_manager,
            mock_logger,
            mock_active_job_tracker):
        """Test status update when API call fails."""
        job = Job(mock_job_info_runner, mock_server_proxy, mock_file_manager, mock_logger,
                  mock_active_job_tracker)
        
        job._job_api.job_manager_runner_partial_update.side_effect = Exception("API error")
        original_status = mock_job_info_runner.status
        
        # Should not raise exception
        job._update_status(StatusEnum.RN)
        
        # Verify error was logged
        mock_logger.error.assert_called_once_with(
            f"Job test-job-123 failed to report status: API error"
        )
        
        # Verify local status was NOT updated
        assert job.job.status == original_status
        
        # Verify activity tracker was NOT called
        mock_active_job_tracker.is_tracked.assert_not_called()
        mock_active_job_tracker.update_job_status.assert_not_called()