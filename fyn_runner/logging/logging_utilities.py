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
import datetime
import os
import time
from pathlib import Path


def create_logger(
        log_dir,
        name="fyn_runner",
        level=logging.INFO,
        dev_mode=False,
        retention_days=30):
    """
     Create and configure a logger instance with file and optional console output.

     Creates a new timestamped log file for each session and automatically cleans up
     old log files based on the retention policy. The logger includes source location
     information (filename and line number) in each log entry.

     Args:
         log_dir (Path): Directory where log files will be stored
         name (str): Logger name for hierarchical logging and identification
         level (int): Logging level threshold (e.g., logging.INFO, logging.DEBUG)
         dev_mode (bool): When True, logs will be output to console in addition to file
         retention_days (int): Number of days to keep log files before deletion

     Returns:
         logging.Logger: Configured logger instance ready for use
    """

    # Create timestamp for this session's log file
    timestamp = datetime.datetime.now().strftime(r"%Y-%m-%d_%H%M%S")
    log_filename = f"fyn_runner_{timestamp}.log"
    log_path = Path(log_dir) / log_filename

    # Get a logger with the specified name
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Set format
    formatter = logging.Formatter(
        '[%(asctime)s][%(levelname)s][%(filename)s::%(lineno)d]: %(message)s'
    )

    # File handler for all logs
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler for development mode
    if dev_mode:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Log startup information
    logger.info(f"Logger initialized. Logging to: {log_path}")
    logger.info(f"Logging at {logging.getLevelName(logger.level)} level")
    if dev_mode:
        logger.info("Logging in development mode")

    # Clean up old logs
    try:
        count = _cleanup_old_logs(log_dir, retention_days)
        logger.info(f"Cleaned up {count} log files older than {retention_days} days")
    except Exception as error:
        logger.error(error)

    return logger


def _cleanup_old_logs(log_dir, retention_days):
    """
    Clean up log files older than retention_days.

    Args:
        log_dir (Path): Directory containing log files
        retention_days (int): Maximum age of log files in days
    """

    # Scan log directory
    count = 0
    for log_file in log_dir.glob("fyn_runner_*.log"):
        file_age = time.time() - os.path.getmtime(log_file)
        if file_age > (retention_days * 86400):  # in seconds
            log_file.unlink()  # Delete file
            count += 1
    return count
