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

import pytest

from fyn_runner.server.message import HttpMethod, Message


class TestMessage:
    """Test suite for Message class."""

    def test_create_message_with_required_fields(self):
        """Test creating a Message with just the required fields."""
        endpoint = "https://api.example.com/endpoint"

        message = Message(
            api_path=endpoint,
            method=HttpMethod.GET
        )

        assert str(message.api_path) == endpoint
        assert message.msg_id is not None
        assert message.method == HttpMethod.GET
        assert message.header == {}
        assert message.params is None
        assert message.priority == 0
        assert message.json_data is None
        assert message.file_path is None

    def test_create_message_with_all_fields(self):
        """Test creating a Message with all fields specified."""
        endpoint = "https://api.example.com/endpoint"
        header = {"Authorization": "Bearer token"}
        params = {"key": "value"}
        json_data = {"data": "value"}
        file_path = Path("/path/to/file")

        message = Message(
            api_path=endpoint,
            method=HttpMethod.POST,
            header=header,
            params=params,
            priority=1,
            json_data=json_data,
            file_path=file_path
        )

        assert str(message.api_path) == endpoint
        assert message.msg_id is not None
        assert message.method == HttpMethod.POST
        assert message.header == header
        assert message.params == params
        assert message.priority == 1
        assert message.json_data == json_data
        assert message.file_path == file_path

    def test_json_message_classmethod(self):
        """Test the json_message classmethod."""
        endpoint = "https://api.example.com/endpoint"
        json_data = {"data": "value"}
        header = {"Authorization": "Bearer token"}
        params = {"key": "value"}

        # Actually call the class method here
        message = Message.json_message(
            api_path=endpoint,
            method=HttpMethod.POST,
            json_data=json_data,
            header=header,
            priority=1,
            params=params
        )

        assert str(message.api_path) == endpoint
        assert message.msg_id is not None
        assert message.method == HttpMethod.POST
        assert "Content-Type" in message.header
        assert message.header["Content-Type"] == "application/json"
        assert message.header["Authorization"] == "Bearer token"
        assert message.params == params
        assert message.priority == 1
        assert message.json_data == json_data
        assert message.file_path is None

    def test_form_message_classmethod(self):
        """Test the file_message classmethod."""
        endpoint = "https://api.example.com/endpoint"
        file_path = Path("/path/to/file")
        header = {"Authorization": "Bearer token"}
        params = {"key": "value"}

        # Actually call the class method here
        message = Message.file_message(
            api_path=endpoint,
            method=HttpMethod.POST,
            file_path=file_path,
            header=header,
            priority=1,
            params=params
        )

        assert str(message.api_path) == endpoint
        assert message.msg_id is not None
        assert message.method == HttpMethod.POST
        assert message.header == header
        assert message.params == params
        assert message.priority == 1
        assert message.json_data is None
        assert message.file_path == file_path

    def test_query_message_classmethod(self):
        """Test the query_message classmethod."""
        endpoint = "https://api.example.com/endpoint"
        params = {"key": "value"}
        extra_headers = {"Authorization": "Bearer token"}

        # Actually call the class method here
        message = Message.query_message(
            api_path=endpoint,
            params=params,
            priority=1,
            extra_headers=extra_headers
        )

        assert str(message.api_path) == endpoint
        assert message.msg_id is not None
        assert message.method == HttpMethod.GET
        assert message.header == extra_headers
        assert message.params == params
        assert message.priority == 1
        assert message.json_data is None
        assert message.file_path is None

    def test_message_id_auto_generation(self):
        """Test that msg_id is automatically generated when not provided."""
        message1 = Message(
            api_path="https://api.example.com/endpoint",
            method=HttpMethod.GET
        )
        message2 = Message(
            api_path="https://api.example.com/endpoint",
            method=HttpMethod.GET
        )

        # Verify msg_id exists
        assert message1.msg_id is not None
        # Verify msg_ids are unique
        assert message1.msg_id != message2.msg_id

    def test_json_message_default_headers(self):
        """Test that json_message sets default Content-Type header."""
        # Actually call the class method here
        message = Message.json_message(
            api_path="https://api.example.com",
            method=HttpMethod.POST,
            json_data={"data": "value"}
        )

        assert message.header == {"Content-Type": "application/json"}

    def test_form_message_default_headers(self):
        """Test that form_message sets default headers."""
        # Actually call the class method here
        message = Message.file_message(
            api_path="https://api.example.com",
            method=HttpMethod.POST,
            file_path=Path("/path/to/file")
        )

        assert message.header == {}

    def test_query_message_default_headers(self):
        """Test that query_message sets default headers."""
        # Actually call the class method here
        message = Message.query_message(
            api_path="https://api.example.com",
            params={"key": "value"}
        )

        assert message.header == {}

    def test_json_message_rejects_content_type_override(self):
        """Test that json_message doesn't allow overriding the Content-Type header."""
        custom_headers = {"Authorization": "Bearer token", "Content-Type": "application/xml"}

        # The method should raise a RuntimeError when trying to change Content-Type
        with pytest.raises(RuntimeError, match="Attempting to specify 'Content-Type'"):
            Message.json_message(
                api_path="https://api.example.com",
                method=HttpMethod.POST,
                json_data={"data": "value"},
                header=custom_headers
            )

    def test_json_message_accepts_same_content_type(self):
        """Test that json_message allows the same Content-Type to be specified."""
        custom_headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}

        # This should work fine since Content-Type is the same
        message = Message.json_message(
            api_path="https://api.example.com",
            method=HttpMethod.POST,
            json_data={"data": "value"},
            header=custom_headers
        )

        assert message.header["Content-Type"] == "application/json"
        assert message.header["Authorization"] == "Bearer token"

    def test_different_http_methods(self):
        """Test Message creation with different HTTP methods."""
        methods = [
            HttpMethod.GET,
            HttpMethod.POST,
            HttpMethod.PUT,
            HttpMethod.PATCH,
            HttpMethod.DELETE]

        for method in methods:
            message = Message(
                api_path="https://api.example.com",
                method=method
            )
            assert message.method == method
