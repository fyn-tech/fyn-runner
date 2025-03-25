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

# pylint: disable=protected-access,pointless-statement,unspecified-encoding

import atexit
from unittest.mock import MagicMock, patch

import pytest
import requests

from fyn_runner.server.server_proxy import ServerProxy


class TestServerProxy:
    """Test suite for ServerProxy utility."""

    @pytest.fixture
    def server_proxy(self):
        """Create a ServerProxy instance for testing."""
        # Create mocks for the dependencies
        logger_mock = MagicMock()
        file_manager_mock = MagicMock()

        # Create a configuration mock with required attributes
        config_mock = MagicMock()
        config_mock.name = "test_runner"
        config_mock.id = "test-123"
        config_mock.token = "test-token"
        config_mock.api_url = "https://api.example.com"
        config_mock.report_interval = 60

        # Save original register function
        original_register = atexit.register

        # Temporarily replace atexit.register to prevent the _report_status
        # callback from being registered
        atexit.register = MagicMock()

        # Create the proxy with mocked _fetch_api and _raise_connection
        with patch.object(ServerProxy, '_fetch_api'), patch.object(ServerProxy,
                                                                   '_raise_connection'):
            proxy = ServerProxy(logger_mock, file_manager_mock, config_mock)

        # Restore original atexit.register
        atexit.register = original_register

        return proxy

    def test_report_status_success(self, server_proxy):
        """Test _report_status when the request is successful."""
        # Mock the requests.patch to return a successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}

        with patch('requests.patch', return_value=mock_response):
            # Call the method
            result = server_proxy._report_status('idle')

            # Verify the result
            assert result == {"status": "success"}

            # Verify logging
            server_proxy.logger.debug.assert_called_once()
            server_proxy.logger.info.assert_called_once()

    def test_report_status_connection_error(self, server_proxy):
        """Test _report_status when a connection error occurs."""
        # Mock requests.patch to raise a ConnectionError
        with patch('requests.patch',
                   side_effect=requests.exceptions.ConnectionError("Failed to connect")):
            # Call the method and check that it raises a ConnectionError
            with pytest.raises(ConnectionError) as exc_info:
                server_proxy._report_status('idle')

            # Verify the exception message
            assert "Failed to report status 'idle'" in str(exc_info.value)

            # Verify logging
            server_proxy.logger.debug.assert_called_once()
            server_proxy.logger.error.assert_called_once()

    def test_report_status_http_error(self, server_proxy):
        """Test _report_status when an HTTP error response is received."""
        # Mock response that raises an HTTPError when raise_for_status is called
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error")

        with patch('requests.patch', return_value=mock_response):
            # Call the method and check that it raises a ConnectionError
            with pytest.raises(ConnectionError) as exc_info:
                server_proxy._report_status('idle')

            # Verify the exception message
            assert "Failed to report status 'idle'" in str(exc_info.value)

            # Verify logging
            server_proxy.logger.debug.assert_called_once()
            server_proxy.logger.error.assert_called_once()

    def test_report_status_timeout(self, server_proxy):
        """Test _report_status when a timeout occurs."""
        # Mock requests.patch to raise a Timeout exception
        with patch('requests.patch', side_effect=requests.exceptions.Timeout("Request timed out")):
            # Call the method and check that it raises a ConnectionError
            with pytest.raises(ConnectionError) as exc_info:
                server_proxy._report_status('idle')

            # Verify the exception message
            assert "Failed to report status 'idle'" in str(exc_info.value)

            # Verify logging
            server_proxy.logger.debug.assert_called_once()
            server_proxy.logger.error.assert_called_once()

    def test_report_status_custom_timeout(self, server_proxy):
        """Test _report_status with a custom timeout value."""
        # Mock the requests.patch to return a successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}

        with patch('requests.patch', return_value=mock_response) as mock_patch:
            # Call the method with a custom timeout
            custom_timeout = 30
            server_proxy._report_status('idle', request_timeout=custom_timeout)

            # Verify the request was made with the custom timeout
            mock_patch.assert_called_once()
            kwargs = mock_patch.call_args[1]
            assert kwargs['timeout'] == custom_timeout

    def test_report_status_different_states(self, server_proxy):
        """Test _report_status with different status values."""
        # Mock the requests.patch to return a successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}

        with patch('requests.patch', return_value=mock_response) as mock_patch:
            # Test with different status values
            for status in ['idle', 'busy', 'offline']:
                server_proxy._report_status(status)

                # Check that the correct status was sent in the latest call
                last_call_args = mock_patch.call_args
                assert last_call_args[1]['json']['state'] == status

    def test_raise_connection_success(self, server_proxy):
        """Test _raise_connection when the connection is successful."""
        # Mock _report_status to succeed
        with patch.object(server_proxy, '_report_status') as mock_report_status:
            # Call the method
            server_proxy._raise_connection()

            # Verify _report_status was called with 'idle'
            mock_report_status.assert_called_once_with('idle')

            # Verify logging
            server_proxy.logger.info.assert_called_once()

    def test_raise_connection_error(self, server_proxy):
        """Test _raise_connection when a connection error occurs."""
        # Mock _report_status to raise a ConnectionError
        error_msg = "Failed to connect"
        with patch.object(server_proxy, '_report_status', side_effect=ConnectionError(error_msg)):
            # Call the method and check that it raises a ConnectionError
            with pytest.raises(ConnectionError) as exc_info:
                server_proxy._raise_connection()

            # Verify the exception message
            assert error_msg in str(exc_info.value)

            # Verify logging
            server_proxy.logger.info.assert_called_once()
