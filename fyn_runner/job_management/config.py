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

import math
import psutil
from pydantic import BaseModel, Field


class JobManagerConfig(BaseModel):
    """Configuration for the logger."""
    max_cpu: int = Field(
        default=psutil.cpu_count(logical=False),
        le=psutil.cpu_count(logical=False),
        ge=0,
        description="The maximum number of physical CPU cores which nay be used. (0 = max)")
    max_concurrent_jobs: int = Field(
        default=1,
        gt=0,
        allow_inf_nan=True,
        description="The maximum number of concurrent jobs the runner can launh.")
    max_main_loop_count: int = Field(
        default=math.inf,
        gt=0,
        allow_inf_nan=True,
        description="Typically for development, the number ticks the main wait thread must do "
                    "before terminating.")
