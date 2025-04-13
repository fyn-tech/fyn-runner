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

import logging
import os
import tempfile
import time
from pathlib import Path

import pytest

from fyn_runner.utilities.logging_utilities import (_cleanup_old_logs,
                                                    create_logger)


class TestLogger:
    """Test suite for logger utility."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_create_logger_basic(self, temp_log_dir):
        """Test basic logger creation and configuration."""
        logger = create_logger(temp_log_dir)

        assert logger.name == "fyn_runner"
        assert logger.level == logging.INFO

        log_files = list(temp_log_dir.glob("fyn_runner_*.log"))

        assert len(log_files) == 1
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)

    def test_create_logger_develop(self, temp_log_dir):
        """Test logger in dev mode with console output."""
        logger = create_logger(temp_log_dir, develop=True)

        assert len(logger.handlers) == 2
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_create_logger_custom_level(self, temp_log_dir):
        """Test logger with custom logging level."""
        logger = create_logger(temp_log_dir, level=logging.DEBUG)

        assert logger.level == logging.DEBUG
        assert logger.handlers[0].level == logging.DEBUG

    def test_create_logger_custom_name(self, temp_log_dir):
        """Test logger with custom name."""
        custom_name = "custom_logger"
        logger = create_logger(temp_log_dir, name=custom_name)

        assert logger.name == custom_name

    def test_cleanup_old_logs(self, temp_log_dir):
        """Test cleanup of old log files."""
        old_log_path = temp_log_dir / "fyn_runner_2023-01-01_120000.log"
        with open(old_log_path, 'w', encoding='utf-8') as f:
            f.write("Old log content")

        old_mtime = time.time() - (31 * 86400)
        os.utime(old_log_path, (old_mtime, old_mtime))
        new_log_path = temp_log_dir / "fyn_runner_2025-03-22_120000.log"
        with open(new_log_path, 'w', encoding='utf-8') as f:
            f.write("New log content")

        count = _cleanup_old_logs(temp_log_dir, 30)
        assert count == 1
        assert not old_log_path.exists()
        assert new_log_path.exists()
