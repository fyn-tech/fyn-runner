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

import appdirs
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
from typing import Literal

from fyn_runner.constants import DEFAULT_WORK_DIRECTORY

class LoggingConfig(BaseModel):
    """Configuration for the logger."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
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
        default=Path(DEFAULT_WORK_DIRECTORY),
        description="Path to the runner's working directory (simulation directories may be located "
                    "else where). Defaults to appdirs")
    simulation_directory: Path = Field(
        default="simulations",
        description="Path (absolute) to simulation directory (containing case folders) for the runner. Defaults to working_directory/simulations")
    
    @model_validator(mode='after')
    def resolve_paths(self) -> 'FileManagerConfig':
        """Resolve simulation_directory relative to working_directory if needed."""
        if not self.simulation_directory.is_absolute():
            self.simulation_directory = self.working_directory / self.simulation_directory
        return self