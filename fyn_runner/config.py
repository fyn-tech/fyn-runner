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

from pydantic import BaseModel, Field

from fyn_runner.job_management.config import JobManagerConfig
from fyn_runner.server.config import ServerProxyConfig
from fyn_runner.utilities.config import FileManagerConfig, LoggingConfig


class RunnerConfig(BaseModel):
    """Root configuration for the Fyn Runner application."""
    file_manager: FileManagerConfig = Field(default_factory=FileManagerConfig)
    job_manager: JobManagerConfig = Field(default_factory=JobManagerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    server_proxy: ServerProxyConfig = Field(default_factory=ServerProxyConfig)
    
