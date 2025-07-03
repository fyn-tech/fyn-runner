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

# pylint: disable=protected-access,pointless-statement,unspecified-encoding

import atexit
import json
import threading
import time
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import MagicMock, patch
from queue import PriorityQueue

import pytest
import requests

from fyn_runner.server.message import HttpMethod, Message
from fyn_runner.server.server_proxy import ServerProxy


class TestServerProxy:
    """Test suite for ServerProxy utility."""

    @pytest.fixture
    def server_proxy(self):
        """Create a ServerProxy instance for testing."""
        # Create mocks for the dependencies
        logger_mock = MagicMock()
        file_manager_mock = MagicMock()

        # Create a configuration mock with required attributes
        config_mock = MagicMock()
        config_mock.name = "test_runner"
        config_mock.id = "test-123"
        config_mock.token = "test-token"
        config_mock.api_url = "https://api.example.com"
        config_mock.api_port = 8000
        config_mock.report_interval = 60

        # Save original register function and threading class
        original_register = atexit.register
        original_thread = threading.Thread

        # Create thread mocks that track when daemon is set
        thread_instances = []

        def create_thread_mock(**_kwargs):
            mock_thread = MagicMock()
            thread_instances.append(mock_thread)
            return mock_thread

        thread_mock = MagicMock(side_effect=create_thread_mock)
        register_mock = MagicMock()
        fetch_api_mock = MagicMock()
        raise_connection_mock = MagicMock()

        # Temporarily replace atexit.register and threading.Thread
        atexit.register = register_mock
        threading.Thread = thread_mock

        # Create the ServerProxy with patched methods
        with patch.object(ServerProxy, '_fetch_api', fetch_api_mock), \
                patch.object(ServerProxy, '_raise_connection', raise_connection_mock):
            proxy = ServerProxy(logger_mock, file_manager_mock, config_mock)

        # Store mocks for later assertions
        proxy._thread_mock = thread_mock
        proxy._thread_instances = thread_instances  # Store the thread instances
        proxy._fetch_api_mock = fetch_api_mock
        proxy._raise_connection_mock = raise_connection_mock
        proxy._atexit_register_mock = register_mock

        # Restore original functions
        atexit.register = original_register
        threading.Thread = original_thread

        return proxy

    def test_initialization(self, server_proxy):
        """Test the initialization of ServerProxy."""
        # Check that essential attributes are initialized
        assert server_proxy.running is True
        assert isinstance(server_proxy._queue, PriorityQueue)
        assert isinstance(server_proxy._new_send_message, threading.Event)

        # Check that thread is created (mocked) - using our stored mock
        thread_mock = server_proxy._thread_mock
        assert thread_mock.call_count >= 2

        # Check thread targets set
        thread_calls = thread_mock.call_args_list
        thread_targets = [call[1]["target"] for call in thread_calls if "target" in call[1]]
        assert server_proxy._send_handler in thread_targets
        assert server_proxy._receive_handler in thread_targets

        # Check that the daemon property was set on at least one thread instance
        daemon_values = [getattr(instance, 'daemon', None)
                         for instance in server_proxy._thread_instances]
        assert True in daemon_values, "No thread had daemon=True set"

        assert server_proxy.running is True
        assert server_proxy._ws is None
        assert server_proxy._ws_connected is False

        assert server_proxy._fetch_api_mock.call_count > 0
        assert server_proxy._raise_connection_mock.call_count > 0
        assert server_proxy._atexit_register_mock.call_count > 0

    def test_register_observer(self, server_proxy):
        """Test registering an observer."""
        # Create a mock callback
        mock_callback = MagicMock()

        # Register the observer
        server_proxy.register_observer("test_message", mock_callback)

        # Verify it was registered
        assert "test_message" in server_proxy._observers
        assert server_proxy._observers["test_message"] == mock_callback

        # Verify logging occurred
        server_proxy.logger.info.assert_called_with("Registered observer test_message")

    def test_register_duplicate_observer(self, server_proxy):
        """Test that registering a duplicate observer raises an exception."""
        # Register an initial observer
        server_proxy.register_observer("test_message", MagicMock())

        # Attempt to register a duplicate
        with pytest.raises(RuntimeError, match="Trying to add to existing observer test_message"):
            server_proxy.register_observer("test_message", MagicMock())

    def test_deregister_observer(self, server_proxy):
        """Test deregistering an observer."""
        # First register an observer
        mock_callback = MagicMock()
        server_proxy.register_observer("test_message", mock_callback)

        # Then deregister it
        server_proxy.deregister_observer("test_message")

        # Verify it was removed
        assert "test_message" not in server_proxy._observers

        # Verify logging occurred
        server_proxy.logger.info.assert_called_with("Deregistered observer test_message")

    def test_deregister_nonexistent_observer(self, server_proxy):
        """Test that deregistering a non-existent observer raises an exception."""
        with pytest.raises(RuntimeError,
                           match="Trying to remove non-existant observer test_message"):
            server_proxy.deregister_observer("test_message")

    def test_raise_connection_success(self, server_proxy):
        """Test _raise_connection when the connection is successful."""
        # Mock _report_status to succeed
        with patch.object(server_proxy, '_report_status') as mock_report_status:
            # Call the method
            server_proxy._raise_connection()

            # Verify _report_status was called with 'idle'
            mock_report_status.assert_called_once_with('idle')

            # Verify logging
            server_proxy.logger.info.assert_called_once()

    def test_raise_connection_error(self, server_proxy):
        """Test _raise_connection when a connection error occurs."""
        # Mock _report_status to raise a ConnectionError
        error_msg = "Failed to connect"
        with patch.object(server_proxy, '_report_status', side_effect=ConnectionError(error_msg)):
            # Call the method and check that it raises a ConnectionError
            with pytest.raises(ConnectionError) as exc_info:
                server_proxy._raise_connection()

            # Verify the exception message
            assert error_msg in str(exc_info.value)

            # Verify logging
            server_proxy.logger.info.assert_called_once()

    def test_handle_ws_message_valid(self, server_proxy):
        """Test handling a valid WebSocket message."""
        # Set up the WebSocket connection state
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True

        # Create a mock message
        message_data = json.dumps({
            "id": "msg-123",
            "type": "test_message",
            "data": {"key": "value"}
        })

        # Create a mock observer callback that returns a response
        mock_callback = MagicMock(return_value={"status": "processed"})

        # Add the observer to the observers dictionary
        server_proxy._observers = {}  # Reset observers
        with server_proxy._observers_lock:
            server_proxy._observers["test_message"] = mock_callback

        # Call the method
        server_proxy._handle_ws_message(server_proxy._ws, message_data)

        # Verify callback was called with the message
        mock_callback.assert_called_once()
        call_arg = mock_callback.call_args[0][0]
        assert call_arg['id'] == "msg-123"
        assert call_arg['type'] == "test_message"

        # Verify response was sent
        server_proxy._ws.send.assert_called_once()
        sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
        assert sent_response["response_to"] == "msg-123"
        assert sent_response["status"] == "processed"

    def test_handle_ws_message_no_id(self, server_proxy):
        """Test handling a WebSocket message without an ID."""
        # Set up the WebSocket connection state
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True

        # Create a message without an ID
        message_data = json.dumps({
            "type": "test_message",
            "data": {"key": "value"}
        })

        # Call the method
        server_proxy._handle_ws_message(server_proxy._ws, message_data)

        # Verify error was logged
        server_proxy.logger.error.assert_called_once()
        assert "no id" in server_proxy.logger.error.call_args[0][0].lower()

        # Verify no response was sent
        server_proxy._ws.send.assert_not_called()

    def test_handle_ws_message_no_type(self, server_proxy):
        """Test handling a WebSocket message without a type."""
        # Set up the WebSocket connection state
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True

        # Create a message without a type
        message_data = json.dumps({
            "id": "msg-123",
            "data": {"key": "value"}
        })

        # Call the method
        server_proxy._handle_ws_message(server_proxy._ws, message_data)

        # Verify error was logged
        server_proxy.logger.error.assert_called_once()
        assert "without type" in server_proxy.logger.error.call_args[0][0].lower()

        # Verify error response was sent
        server_proxy._ws.send.assert_called_once()
        sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
        assert sent_response["type"] == "error"
        assert sent_response["response_to"] == "msg-123"
        assert "type" in sent_response["data"].lower()

    def test_handle_ws_message_unknown_type(self, server_proxy):
        """Test handling a WebSocket message with an unknown type."""
        # Set up the WebSocket connection state
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True

        # Create a message with an unknown type
        message_data = json.dumps({
            "id": "msg-123",
            "type": "unknown_type",
            "data": {"key": "value"}
        })

        # Ensure no observers are registered
        server_proxy._observers = {}
        server_proxy._handle_ws_message(server_proxy._ws, message_data)

        # Verify error was logged
        server_proxy.logger.error.assert_called_once()
        assert "unknown message type" in server_proxy.logger.error.call_args[0][0].lower()

        # Verify error response was sent
        server_proxy._ws.send.assert_called_once()
        sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
        assert sent_response["type"] == "error"
        assert sent_response["response_to"] == "msg-123"
        assert "unknown" in sent_response["data"].lower()

    def test_handle_ws_message_callback_exception(self, server_proxy):
        """Test handling a WebSocket message when the callback raises an exception."""
        # Set up the WebSocket connection state
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True

        # Create a mock message
        message_data = json.dumps({
            "id": "msg-123",
            "type": "test_message",
            "data": {"key": "value"}
        })

        # Create a mock observer callback that raises an exception
        error_msg = "Test callback error"
        mock_callback = MagicMock(side_effect=Exception(error_msg))

        # Add the observer to the observers dictionary
        server_proxy._observers = {}  # Reset observers
        with server_proxy._observers_lock:
            server_proxy._observers["test_message"] = mock_callback

        # Call the method
        server_proxy._handle_ws_message(server_proxy._ws, message_data)

        # Verify callback was called
        mock_callback.assert_called_once()

        # Verify error was logged
        server_proxy.logger.error.assert_called_once()
        assert error_msg in server_proxy.logger.error.call_args[0][0]

        # Verify error response was sent
        server_proxy._ws.send.assert_called_once()
        sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
        assert sent_response["type"] == "error"
        assert sent_response["response_to"] == "msg-123"
        assert error_msg in sent_response["data"]

    def test_handle_ws_message_callback_no_response(self, server_proxy):
        """Test handling a WebSocket message when the callback returns None."""
        # Set up the WebSocket connection state
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True

        # Create a mock message
        message_data = json.dumps({
            "id": "msg-123",
            "type": "test_message",
            "data": {"key": "value"}
        })

        # Create a mock observer callback that returns None
        mock_callback = MagicMock(return_value=None)

        # Add the observer to the observers dictionary
        server_proxy._observers = {}  # Reset observers
        with server_proxy._observers_lock:
            server_proxy._observers["test_message"] = mock_callback

        # Call the method
        server_proxy._handle_ws_message(server_proxy._ws, message_data)

        # Verify callback was called
        mock_callback.assert_called_once()

        # Verify a default success response was sent
        server_proxy._ws.send.assert_called_once()
        sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
        assert sent_response["type"] == "success"
        assert sent_response["response_to"] == "msg-123"

    def test_on_ws_open(self, server_proxy):
        """Test the WebSocket open callback."""
        # Reset the connection state
        server_proxy._ws_connected = False

        # Call the method
        server_proxy._on_ws_open(MagicMock())

        # Verify connection status was updated
        assert server_proxy._ws_connected is True

        # Verify event was logged
        server_proxy.logger.info.assert_called_with("WebSocket connection established")

    def test_on_ws_close(self, server_proxy):
        """Test the WebSocket close callback."""
        # Set initial state to connected
        server_proxy._ws_connected = True

        # Call the method
        server_proxy._on_ws_close(MagicMock(), 1000, "Normal closure")

        # Verify connection status was updated
        assert server_proxy._ws_connected is False

        # Verify event was logged with status code and message
        server_proxy.logger.info.assert_called_with(
            "WebSocket connection closed: 1000 Normal closure"
        )

    def test_on_ws_error(self, server_proxy):
        """Test the WebSocket error callback."""
        # Create a mock error
        error = Exception("Test WebSocket error")

        # Reset the logger mock
        server_proxy.logger.reset_mock()

        # Call the method
        server_proxy._on_ws_error(MagicMock(), error)

        # Verify error was logged
        server_proxy.logger.error.assert_called_with("WebSocket error: Test WebSocket error")

    def test_ws_error_response_connected(self, server_proxy):
        """Test sending a WebSocket error response when connected."""
        # Set up the WebSocket connection state
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True

        # Call the method
        server_proxy._ws_error_response("msg-123", "Test error message")

        # Verify the error response was sent
        server_proxy._ws.send.assert_called_once()
        sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
        assert sent_response["type"] == "error"
        assert sent_response["response_to"] == "msg-123"
        assert sent_response["data"] == "Test error message"

        # Verify debug message was logged
        server_proxy.logger.debug.assert_called()
        assert "Sent error response" in server_proxy.logger.debug.call_args[0][0]

    def test_ws_error_response_disconnected(self, server_proxy):
        """Test sending a WebSocket error response when disconnected."""
        # Set up the WebSocket instance but disconnected state
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = False

        # Call the method
        server_proxy._ws_error_response("msg-123", "Test error message")

        # Verify no message was sent
        server_proxy._ws.send.assert_not_called()

        # Verify error was logged
        server_proxy.logger.error.assert_called_with(
            "Cannot send error response: WebSocket not connected"
        )

    def test_ws_error_response_send_exception(self, server_proxy):
        """Test handling an exception when sending a WebSocket error response."""
        # Set up the WebSocket connection state with an error on send
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True
        error_msg = "Send failed"
        server_proxy._ws.send.side_effect = Exception(error_msg)

        # Call the method
        server_proxy._ws_error_response("msg-123", "Test error message")

        # Verify send was called
        server_proxy._ws.send.assert_called_once()

        # Verify error was logged
        server_proxy.logger.error.assert_called_once()
        log_message = server_proxy.logger.error.call_args[0][0]
        assert "Failed to send error response" in log_message
        assert error_msg in log_message
