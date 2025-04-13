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

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from fyn_runner.server.message import HttpMethod
from fyn_runner.system.collection import (_get_disk_data, _get_system_data,
                                          report_current_system_info)


class TestSystemCollection:
    """Test suite for system information collection functions."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger object."""
        return MagicMock()

    @pytest.fixture
    def mock_file_manager(self):
        """Create a mock file manager with necessary paths."""
        file_manager = MagicMock()
        file_manager.cache_dir = Path("/mock/cache/dir")
        file_manager.simulation_dir = Path("/mock/simulation/dir")
        return file_manager

    @pytest.fixture
    def mock_server_proxy(self):
        """Create a mock server proxy."""
        server_proxy = MagicMock()
        server_proxy.api_url = "https://mockapi.com"
        server_proxy.api_port = 443
        server_proxy.id = "mock-id"
        return server_proxy

    @pytest.fixture
    def mock_system_data(self):
        """Create sample system data for testing."""
        return {
            'system_name': 'Linux',
            'system_release': '5.15.0',
            'system_version': 'Ubuntu 22.04',
            'system_architecture': 'x86_64',
            'cpu_model': 'Intel(R) Core(TM) i7-9700K',
            'cpu_logical_cores': 8,
            'ram_size_total': 16000000000,
            'disk_size_total': 500000000000,
            'disk_size_available': 300000000000
        }

    def test_get_disk_data_success(self, mock_file_manager, mock_logger):
        """Test _get_disk_data function returns correct disk information when successful."""
        mock_usage = MagicMock()
        mock_usage.total = 500000000000  # 500 GB
        mock_usage.free = 300000000000   # 300 GB

        with patch('psutil.disk_usage', return_value=mock_usage):
            result = _get_disk_data(mock_file_manager, mock_logger)

            assert result == {
                'disk_size_total': 500000000000,
                'disk_size_available': 300000000000
            }

    def test_get_disk_data_error(self, mock_file_manager, mock_logger):
        """Test _get_disk_data function handles errors correctly."""
        with patch('psutil.disk_usage', side_effect=Exception("Test error")):
            result = _get_disk_data(mock_file_manager, mock_logger)

            assert result == {
                'disk_size_total': None,
                'disk_size_available': None
            }
            mock_logger.error.assert_called_once()

    def test_get_system_data(self, mock_file_manager, mock_logger, mock_system_data):
        """Test _get_system_data aggregates all system information correctly."""
        with patch('fyn_runner.system.collection._get_os_info',
                   return_value={'system_name': 'Linux', 'system_release': '5.15.0',
                                 'system_version': 'Ubuntu 22.04',
                                 'system_architecture': 'x86_64'}), \
                patch('fyn_runner.system.collection._get_cpu_data',
                      return_value={'cpu_model': 'Intel(R) Core(TM) i7-9700K',
                                    'cpu_logical_cores': 8}), \
                patch('fyn_runner.system.collection._get_ram_data',
                      return_value={'ram_size_total': 16000000000}), \
                patch('fyn_runner.system.collection._get_disk_data',
                      return_value={'disk_size_total': 500000000000,
                                    'disk_size_available': 300000000000}), \
                patch('fyn_runner.system.collection._get_gpu_data', return_value={}):

            result = _get_system_data(mock_file_manager, mock_logger)

            # Verify the result contains all expected data
            for key, value in mock_system_data.items():
                assert result[key] == value

    def test_report_current_system_info(self, mock_logger, mock_file_manager,
                                        mock_server_proxy, mock_system_data):
        """Test report_current_system_info collects and reports system info."""

        mock_file = mock_open()

        with patch('fyn_runner.system.collection._get_system_data',
                   return_value=mock_system_data), \
                patch('builtins.open', mock_file), \
                patch('json.dump') as mock_json_dump:

            report_current_system_info(mock_logger, mock_file_manager, mock_server_proxy)

            # Verify the server was notified
            mock_server_proxy.push_message.assert_called_once()

            # Extract the message that was passed to push_message_with_response
            message = mock_server_proxy.push_message.call_args[0][0]

            # Verify the message has correct parameters
            assert message.method == HttpMethod.PUT
            assert message.json_data == mock_system_data
            assert str(message.api_path).startswith(
                f"{mock_server_proxy.api_url}/runner_manager/update_system/mock-id")
            assert message.api_path.port == mock_server_proxy.api_port

            # Verify logging occurred
            mock_logger.info.assert_called_with("Collecting system information.")

            # Verify the file was written
            expected_file_path = mock_file_manager.cache_dir / 'system_data.json'
            mock_file.assert_called_once_with(expected_file_path, 'w', encoding='utf-8')
            file_handle = mock_file.return_value.__enter__.return_value

            mock_json_dump.assert_called_once_with(
                mock_system_data,  # First arg: the data to write
                file_handle,       # Second arg: the file handle
                ensure_ascii=False,
                indent=4
            )
