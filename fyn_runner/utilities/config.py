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

from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Configuration for the logger."""
    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    develop: bool = Field(
        default=False,
        description="Enable development mode, which adds a stream hander for additional console "
                    "logging")
    retention_days: int = Field(default=30, description="Number of days to retain log files")


class FileManagerConfig(BaseModel):
    """Configuration for file management."""
    working_directory: Path = Field(
        default=None,
        description="Root working directory for the runner (simulation directories may be located "
                    "else where). Defaults to appdirs")
