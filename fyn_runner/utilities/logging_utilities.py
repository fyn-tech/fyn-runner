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

import datetime
import logging
import os
import time
from pathlib import Path

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


def create_logger(
        log_dir,
        level=logging.INFO,
        develop=False,
        name="fyn_runner",
        retention_days=30) -> logging.Logger:
    """
     Create and configure a logger instance with file and optional console output.

     Creates a new timestamped log file for each session and automatically cleans up
     old log files based on the retention policy. The logger includes source location
     information (filename and line number) in each log entry.

     Args:
         log_dir (Path): Directory where log files will be stored
         level (int): Logging level threshold (e.g., logging.INFO, logging.DEBUG)
         develop (bool): When True, logs will be output to console in addition to file
         name (str): Logger name for hierarchical logging and identification
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

    # Create formatters - colored for console, plain for file
    if HAS_COLORLOG:
        # Colored formatter for console output
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s]%(reset)s%(log_color)s[%(levelname)s]%(reset)s%(purple)s'
            '[%(filename)s::%(lineno)d]:%(reset)s %(white)s%(message)s%(reset)s',
            log_colors={
                'DEBUG': 'blue',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={
                '': {
                    'purple': 'purple',
                    'white': 'white'
                }
            }
        )
        # Plain formatter for file output (no colors)
        file_formatter = logging.Formatter(
            '[%(asctime)s][%(levelname)s][%(filename)s::%(lineno)d]: %(message)s'
        )
    else:
        # Fallback to regular formatter if colorlog not available
        regular_formatter = logging.Formatter(
            '[%(asctime)s][%(levelname)s][%(filename)s::%(lineno)d]: %(message)s'
        )
        file_formatter = regular_formatter
        console_formatter = regular_formatter

    # File handler for all logs
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler for development mode
    if develop:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Log startup information
    logger.info(f"Logger initialized, logging to: {log_path.absolute()}")
    logger.info(f"Logging at {logging.getLevelName(logger.level)} level")
    if develop:
        if HAS_COLORLOG:
            logger.info("Logging in development mode with colors (console only,"
                        " files are plain text)")
        else:
            logger.info("Logging in development mode (install 'colorlog' for colors)")

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
