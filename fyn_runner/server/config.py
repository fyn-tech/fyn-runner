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

from pydantic import UUID4, BaseModel, Field


class ServerProxyConfig(BaseModel):
    """Configuration for the logger."""
    name: str = Field(
        default="unnamed_runner",
        description="The name of the runner.")
    id: UUID4 = Field(
        description="The id the runner should use when interacting with the back-end")
    token: UUID4 = Field(
        description="The authentication token which should be used when interacting with the "
        "back-end")
    report_interval: int = Field(
        default=600,
        description="The interval, in seconds, between reporting status to the backend.")
