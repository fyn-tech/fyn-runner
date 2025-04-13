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

import uuid
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Optional

from pydantic import UUID4, BaseModel, Field, HttpUrl


class HttpMethod(Enum):
    """HTTP method for the Message Class"""
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()


class Message(BaseModel):
    """
    Represents a message to be sent to or received from the API.

    A Message encapsulates all information needed to make an HTTP request to the API, including the
    api_path, method, headers, and content payload. This class is also responsible for message
    validation.
    """

    api_path: HttpUrl = Field(..., json_schema_extra={"allowed_schemes": ["http", "https"]})
    method: HttpMethod = Field(...)
    header: Dict[str, str] = Field(default_factory=dict)
    params: Optional[Dict[str, str]] = Field(None)
    priority: int = Field(default=0)

    json_data: Optional[Dict] = Field(None)
    file_path: Optional[Path] = Field(None)
    msg_id: UUID4 = Field(default_factory=uuid.uuid4)

    @classmethod
    def json_message(cls, api_path, method, json_data, header=None, priority=0, params=None):
        """
        Create a new Message instance with a JSON payload.

        Args:
            api_path (str): The API URL path
            method (HttpMethod): The HTTP method to use for this request
            json_data (dict): The JSON data to be sent in the request body
            header (dict, optional): Additional HTTP headers to include in the request
            priority (int, optional): Message priority for queue processing (higher = more priority)
            params (dict, optional): URL query parameters to append to the api_path

        Returns:
            Message: A new Message instance configured for JSON data transmission
        """

        message_headers = {"Content-Type": "application/json"}
        if header:
            if ("Content-Type" in header.keys() and header["Content-Type"] != "application/json"):
                raise RuntimeError("Attempting to specify 'Content-Type', other than "
                                   f"application/json: {header['Content-Type']}")
            message_headers.update(header)

        return cls(
            api_path=api_path,
            method=method,
            json_data=json_data,
            header=message_headers,  # Changed from headers to header
            params=params,
            priority=priority
        )

    @classmethod
    def file_message(cls, api_path, method, file_path, header=None, priority=0, params=None):
        """
        Create a new Message instance with a file payload.

        Args:
            api_path (str): The API URL path
            method (HttpMethod): The HTTP method to use for this request
            file_path (Path): The path to the file to send, must exist when message sent
            header (dict, optional): Additional HTTP headers to include in the request
            priority (int, optional): Message priority for queue processing (higher = more priority)
            params (dict, optional): URL query parameters to append to the api_path

        Returns:
            Message: A new Message instance configured for JSON data transmission
        """

        message_headers = {}
        if header:
            message_headers.update(header)

        return cls(
            api_path=api_path,
            method=method,
            file_path=file_path,
            header=message_headers,  # Changed from headers to header
            params=params,
            priority=priority
        )

    @classmethod
    def query_message(cls, api_path: str, params: Dict, priority: int = 0,
                      extra_headers: Optional[Dict] = None) -> 'Message':
        """
        TODO: will correct method when we do the receive side.
        Create a GET message with query parameters.

        Args:
            api_path (str): The API URL path
            params (Dict): Query parameters to append to the URL
            priority (int, optional): Message priority for queue processing
            extra_headers (Dict, optional): Additional HTTP headers to include

        Returns:
            Message: A new Message instance configured for a GET request
        """

        headers = {}
        if extra_headers:
            headers.update(extra_headers)

        return cls(
            api_path=api_path,
            method=HttpMethod.GET,
            params=params,
            header=headers,
            priority=priority
        )
