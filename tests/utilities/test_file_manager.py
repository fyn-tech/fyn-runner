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

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from fyn_runner.utilities.file_manager import FileManager


class TestFileManager:
    """Test suite for FileManager utility."""

    def test_default_directory_initialisation(self):
        """Mock appdirs and ensure correct directory creation"""

        temp_path = Path(tempfile.mkdtemp())
        with patch('appdirs.user_data_dir') as mock_data_dir, \
                patch('appdirs.user_cache_dir') as mock_cache_dir, \
                patch('appdirs.user_config_dir') as mock_config_dir, \
                patch('appdirs.user_log_dir') as mock_log_dir:

            mock_data_dir.return_value = str(temp_path)
            mock_cache_dir.return_value = str(temp_path / 'cache')
            mock_config_dir.return_value = str(temp_path / 'config')
            mock_log_dir.return_value = str(temp_path / 'logs')

            FileManager(temp_path)
            assert Path(temp_path).exists()
            assert Path(temp_path / 'cache').exists()
            assert Path(temp_path / 'config').exists()
            assert Path(temp_path / 'logs').exists()
            assert Path(temp_path / 'simulations').exists()

        shutil.rmtree(temp_path)

    def test_default_directory_with_app_name(self):
        """Mock appdirs, and change program name, and ensure correct directory creation"""

        name = 'test_runner'
        temp_path = Path(tempfile.mkdtemp())
        with patch('appdirs.user_data_dir') as mock_data_dir, \
                patch('appdirs.user_cache_dir') as mock_cache_dir, \
                patch('appdirs.user_config_dir') as mock_config_dir, \
                patch('appdirs.user_log_dir') as mock_log_dir:

            mock_data_dir.return_value = str(temp_path / name)
            mock_cache_dir.return_value = str(temp_path / name / 'cache')
            mock_config_dir.return_value = str(temp_path / name / 'config')
            mock_log_dir.return_value = str(temp_path / name / 'logs')

            FileManager(None, name)
            assert Path(temp_path).exists()
            assert Path(temp_path / name).exists()
            print(temp_path / name)
            assert Path(temp_path / name / 'cache').exists()
            assert Path(temp_path / name / 'config').exists()
            assert Path(temp_path / name / 'logs').exists()
            assert Path(temp_path / name / 'simulations').exists()

        shutil.rmtree(temp_path)

    def test_custom_directory_initialisation(self):
        """Test dependency injection path and ensure directory creation"""

        temp_path = Path(tempfile.mkdtemp())
        FileManager(temp_path)
        assert Path(temp_path / 'cache').exists()
        assert Path(temp_path / 'config').exists()
        assert Path(temp_path / 'logs').exists()
        assert Path(temp_path / 'simulations').exists()
        shutil.rmtree(temp_path)

    def test_custom_string_directory_initialisation(self):
        """Test string dependency injection path and ensure directory creation"""

        temp_path = str(tempfile.mkdtemp())  # explicitly make string
        FileManager(temp_path)
        assert Path(temp_path + '/cache').exists()
        assert Path(temp_path + '/config').exists()
        assert Path(temp_path + '/logs').exists()
        assert Path(temp_path + '/simulations').exists()
        shutil.rmtree(temp_path)

    def test_simulation_dir_setter(self):
        """Test addition of a simulation directory """
        temp_path = Path(tempfile.mkdtemp())
        manager = FileManager(temp_path)

        new_sim_dir = temp_path / "new_simulations"
        manager.simulation_dir = new_sim_dir

        assert new_sim_dir.exists()

        shutil.rmtree(temp_path)
