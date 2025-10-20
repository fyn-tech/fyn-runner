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

"""
Pytest configuration and fixtures.

This module sets up comprehensive mocking for the fyn_api_client package which is not available
during testing. The mocks are established before any test modules are imported to avoid
ModuleNotFoundError exceptions.
"""

import sys
from unittest.mock import MagicMock
from enum import Enum


# Define mock enums that behave like the actual OpenAPI generated enums
class MockStatusEnum(Enum):
    """Mock StatusEnum with all the status values used in the codebase."""
    UI = "UPLOADING_INPUT_RESOURCES"
    QD = "QUEUED"
    PR = "PREPARING"
    FR = "FETCHING_RESOURCES"
    RN = "RUNNING"
    PD = "PAUSED"
    CU = "CLEAN_UP"
    UR = "UPLOADING_RESOURCES"
    SD = "SUCCEEDED"
    FD = "FAILED"
    FS = "FAILED_SETUP"
    FM = "FAILED_MISSING"
    FO = "FAILED_OVERRUN"
    FE = "FAILED_EXCEPTION"


class MockResourceTypeEnum(Enum):
    """Mock ResourceTypeEnum for resource classification."""
    LOG = "LOG"
    DATA = "DATA"
    OUTPUT = "OUTPUT"
    INPUT = "INPUT"


class MockTypeEnum(Enum):
    """Mock TypeEnum for application types."""
    PYTHON = "PYTHON"
    SHELL = "SHELL"
    LINUX_BINARY = "LINUX_BINARY"
    WINDOWS_BINARY = "WINDOWS_BINARY"
    UNKNOWN = "UNKNOWN"


class MockStateEnum(Enum):
    """Mock StateEnum for runner states."""
    ID = "IDLE"
    RN = "RUNNING"
    OF = "OFFLINE"
    ER = "ERROR"


# Create mock classes for OpenAPI model classes
class MockJobInfoRunner(MagicMock):
    """Mock JobInfoRunner model."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "mock-job-id"
        self.application_id = "mock-app-id"
        self.status = MockStatusEnum.QD
        self.priority = 5
        self.executable = "python"
        self.command_line_args = []
        self.resources = []


class MockApp(MagicMock):
    """Mock App model."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "mock-app-id"
        self.name = "mock-app"
        self.type = MockTypeEnum.PYTHON


class MockPatchedJobInfoRunnerRequest(MagicMock):
    """Mock PatchedJobInfoRunnerRequest model."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = kwargs.get('status')
        self.working_directory = kwargs.get('working_directory')
        self.exit_code = kwargs.get('exit_code')


class MockPatchedRunnerInfoRequest(MagicMock):
    """Mock PatchedRunnerInfoRequest model."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = kwargs.get('state')


# Create the main fyn_api_client mock module
mock_fac = MagicMock()

# Mock the main API classes
mock_fac.Configuration = MagicMock
mock_fac.ApiClient = MagicMock
mock_fac.ApplicationRegistryApi = MagicMock
mock_fac.JobManagerApi = MagicMock
mock_fac.RunnerManagerApi = MagicMock

# Mock the enum classes
mock_fac.StateEnum = MockStateEnum
mock_fac.StatusEnum = MockStatusEnum
mock_fac.ResourceTypeEnum = MockResourceTypeEnum
mock_fac.TypeEnum = MockTypeEnum

# Mock the model classes
mock_fac.JobInfoRunner = MockJobInfoRunner
mock_fac.App = MockApp
mock_fac.PatchedJobInfoRunnerRequest = MockPatchedJobInfoRunnerRequest
mock_fac.PatchedRunnerInfoRequest = MockPatchedRunnerInfoRequest

# Store a reference to the mock for easy access in tests
fyn_api_client_mock = mock_fac

# Create mock submodules for specific imports
mock_models = MagicMock()
mock_models.status_enum = MagicMock()
mock_models.status_enum.StatusEnum = MockStatusEnum
mock_models.resource_type_enum = MagicMock()
mock_models.resource_type_enum.ResourceTypeEnum = MockResourceTypeEnum
mock_models.job_info_runner = MagicMock()
mock_models.job_info_runner.JobInfoRunner = MockJobInfoRunner
mock_models.app = MagicMock()
mock_models.app.App = MockApp
mock_models.type_enum = MagicMock()
mock_models.type_enum.TypeEnum = MockTypeEnum
mock_models.patched_job_info_runner_request = MagicMock()
mock_models.patched_job_info_runner_request.PatchedJobInfoRunnerRequest = \
    MockPatchedJobInfoRunnerRequest

mock_fac.models = mock_models

# Install all the mocks in sys.modules before any imports happen
sys.modules['fyn_api_client'] = mock_fac
sys.modules['fyn_api_client.models'] = mock_models
sys.modules['fyn_api_client.models.status_enum'] = mock_models.status_enum
sys.modules['fyn_api_client.models.resource_type_enum'] = mock_models.resource_type_enum
sys.modules['fyn_api_client.models.job_info_runner'] = mock_models.job_info_runner
sys.modules['fyn_api_client.models.app'] = mock_models.app
sys.modules['fyn_api_client.models.type_enum'] = mock_models.type_enum
sys.modules['fyn_api_client.models.patched_job_info_runner_request'] = \
    mock_models.patched_job_info_runner_request


# Make the enums and classes available for import
StatusEnum = MockStatusEnum
ResourceTypeEnum = MockResourceTypeEnum
TypeEnum = MockTypeEnum
StateEnum = MockStateEnum
JobInfoRunner = MockJobInfoRunner
App = MockApp
PatchedJobInfoRunnerRequest = MockPatchedJobInfoRunnerRequest
PatchedRunnerInfoRequest = MockPatchedRunnerInfoRequest
