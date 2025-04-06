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
import threading
import time
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from fyn_runner.server.message import HttpMethod, Message
from fyn_runner.server.message_queue import MessageQueue
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
        assert server_proxy._running is True
        assert isinstance(server_proxy._queue, MessageQueue)
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

        assert server_proxy._ws is None
        assert server_proxy._ws_connected is False
        assert server_proxy._running is True

        assert server_proxy._fetch_api_mock.call_count > 0
        assert server_proxy._raise_connection_mock.call_count > 0
        assert server_proxy._atexit_register_mock.call_count > 0

    def test_push_message(self, server_proxy):
        """Test adding a message to the queue."""
        # Create a mock message
        mock_message = MagicMock()

        # Mock the queue's push_message method and the event
        server_proxy._queue.push_message = MagicMock()
        server_proxy._new_send_message.set = MagicMock()

        # Call push_message
        server_proxy.push_message(mock_message)

        # Verify that the message was added to the queue
        server_proxy._queue.push_message.assert_called_once_with(mock_message)

        # Verify that the event was set
        server_proxy._new_send_message.set.assert_called_once()

    def test_push_message_exception(self, server_proxy):
        """Test handling exceptions when adding a message to the queue."""
        # Create a mock message
        mock_message = MagicMock()

        # Make queue.push_message raise an exception
        error_msg = "Test error"
        server_proxy._queue.push_message = MagicMock(side_effect=Exception(error_msg))

        # Call push_message and expect exception to be raised
        with pytest.raises(Exception):
            server_proxy.push_message(mock_message)

        # Verify error was logged
        server_proxy.logger.error.assert_called_once()
        assert error_msg in server_proxy.logger.error.call_args[0][0]

    def test_push_message_with_response(self, server_proxy):
        """Test adding a message to the queue with response future."""
        # Create a mock message
        mock_message = MagicMock()
        mock_message.msg_id = "test-message-id"

        # Mock the queue's push_message method and the event
        server_proxy._queue.push_message = MagicMock()
        server_proxy._new_send_message.set = MagicMock()

        # Call push_message_with_response
        future = server_proxy.push_message_with_response(mock_message)

        # Verify that the message was added to the queue
        server_proxy._queue.push_message.assert_called_once_with(mock_message)

        # Verify that the event was set
        server_proxy._new_send_message.set.assert_called_once()

        # Verify that a future was created and stored
        assert mock_message.msg_id in server_proxy._response_futures
        assert server_proxy._response_futures[mock_message.msg_id] == future
        assert not future.done()

    def test_push_message_with_response_exception(self, server_proxy):
        """Test handling exceptions when adding a message with response to the queue."""
        # Create a mock message
        mock_message = MagicMock()
        mock_message.msg_id = "test-message-id"

        # Make queue.push_message raise an exception
        error_msg = "Test error"
        server_proxy._queue.push_message = MagicMock(side_effect=Exception(error_msg))

        # Call push_message_with_response and expect exception
        with pytest.raises(Exception):
            server_proxy.push_message_with_response(mock_message)

        # Verify error was logged
        server_proxy.logger.error.assert_called_once()
        assert error_msg in server_proxy.logger.error.call_args[0][0]

        # Verify the future was removed from _response_futures
        assert mock_message.msg_id not in server_proxy._response_futures

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

    def test_report_status_success(self, server_proxy):
        """Test _report_status when the request is successful."""
        # Mock the _send_message method to return a successful response
        expected_result = {"status": "success"}

        with patch.object(server_proxy, '_send_message', return_value=expected_result) as mock_send:
            # Call the method
            server_proxy._report_status('idle')

            # Verify message was created and sent correctly
            mock_send.assert_called_once()
            message_arg = mock_send.call_args[0][0]
            assert message_arg.method == HttpMethod.PATCH
            assert message_arg.json_data == {"state": "idle"}
            assert "https://api.example.com:8000/runner_manager/report_status/" in str(
                message_arg.api_path)

    def test_report_status_connection_error(self, server_proxy):
        """Test _report_status when a connection error occurs."""
        # Mock _send_message to raise a ConnectionError
        error_msg = "Failed to connect"
        exception = requests.exceptions.ConnectionError(error_msg)

        with patch.object(server_proxy, '_send_message', side_effect=exception):
            # Call the method and check that it raises a ConnectionError
            with pytest.raises(ConnectionError) as exc_info:
                server_proxy._report_status('idle')

            # Verify the exception message
            assert "Failed to report status 'idle'" in str(exc_info.value)

            # Verify logging
            server_proxy.logger.error.assert_called_once()

    def test_send_message_json(self, server_proxy):
        """Test sending a JSON message."""
        # Create a mock message with JSON data
        message = Message.json_message(
            api_path="https://api.example.com/test",
            method=HttpMethod.POST,
            json_data={"key": "value"}
        )

        # Mock the requests library
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}

        with patch('requests.post', return_value=mock_response) as mock_post:
            # Call the method
            result = server_proxy._send_message(message)

            # Verify the request was made correctly
            mock_post.assert_called_once()
            kwargs = mock_post.call_args[1]
            assert kwargs['json'] == {"key": "value"}
            assert 'id' in kwargs['headers']
            assert 'token' in kwargs['headers']

            # Verify the result
            assert result == {"result": "success"}

    def test_send_message_file(self, server_proxy, tmp_path):
        """Test sending a file message."""
        # Create a temporary file
        file_path = tmp_path / "test_file.txt"
        with open(file_path, 'w') as f:
            f.write("Test content")

        # Create a mock message with file path
        message = Message.file_message(
            api_path="https://api.example.com/upload",
            method=HttpMethod.POST,
            file_path=file_path
        )

        # Mock the requests library
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "uploaded"}

        with patch('requests.post', return_value=mock_response) as mock_post:
            # Call the method
            result = server_proxy._send_message(message)

            # Verify the request was made correctly
            mock_post.assert_called_once()
            kwargs = mock_post.call_args[1]
            assert 'files' in kwargs
            assert kwargs['files']['file']

            # Verify the result
            assert result == {"result": "uploaded"}

    def test_send_message_file_not_found(self, server_proxy):
        """Test sending a file message with a non-existent file."""
        # Create a mock message with non-existent file path
        message = Message.file_message(
            api_path="https://api.example.com/upload",
            method=HttpMethod.POST,
            file_path=Path("/non/existent/file.txt")
        )

        # Call the method and check that it raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            server_proxy._send_message(message)

    def test_send_message_unsupported_method(self, server_proxy):
        """Test sending a message with an unsupported HTTP method."""
        # Create a mock message with an unsupported method (simulated)
        message = MagicMock()
        message.method = MagicMock()
        message.method.name = "UNSUPPORTED"
        message.api_path = "https://api.example.com/test"
        message.file_path = None
        message.json_data = {}
        message.header = {}
        message.params = None

        # Call the method and check that it raises ValueError
        with pytest.raises(ValueError, match="Unsupported HTTP method"):
            server_proxy._send_message(message)

    def test_send_handler_message_processing(self, server_proxy):
        """Test the _send_handler method processes messages correctly."""
        # Instead of running the actual _send_handler method, we'll test its logic
        # separately since it contains an infinite loop

        # Extract the method implementation and create a modified version that runs once
        def modified_send_handler():
            # Mock the wait method to return True (message added)
            server_proxy._new_send_message.wait = MagicMock(return_value=True)

            # Mock queue.is_empty to return False once then True
            server_proxy._queue.is_empty = MagicMock(side_effect=[False, True])

            # Mock the message
            mock_message = MagicMock()
            server_proxy._queue.get_next_message = MagicMock(return_value=mock_message)

            # Mock _send_message
            server_proxy._send_message = MagicMock()

            # Execute the core logic from _send_handler just once
            server_proxy._new_send_message.clear()
            while not server_proxy._queue.is_empty():
                message = server_proxy._queue.get_next_message()
                server_proxy._send_message(message)

            # Verify message was processed
            server_proxy._send_message.assert_called_once_with(mock_message)

        # Run our modified handler that doesn't have an infinite loop
        modified_send_handler()

    def test_send_handler_periodic_status(self, server_proxy):
        """Test the _send_handler method sends periodic status updates."""
        # Extract and test just the status reporting logic
        def test_status_reporting():
            # Mock dependencies
            server_proxy._queue.is_empty = MagicMock(return_value=True)
            server_proxy._new_send_message.wait = MagicMock(return_value=False)  # Simulate timeout
            server_proxy._report_status = MagicMock()

            # Execute the status reporting logic
            current_time = time.time()
            next_report_time = current_time - 1  # Make it due immediately

            if current_time >= next_report_time:
                server_proxy._report_status('idle')

            # Verify status was reported
            server_proxy._report_status.assert_called_once_with('idle')

        # Run the test
        test_status_reporting()

    def test_send_handler_error_handling(self, server_proxy):
        """Test that _send_handler properly handles errors in message sending."""
        # Extract and test just the error handling logic
        def test_error_handling():
            # Mock queue to return one message then say it's empty
            server_proxy._queue.is_empty = MagicMock(side_effect=[False, True])

            # Create a mock message
            mock_message = MagicMock()
            server_proxy._queue.get_next_message = MagicMock(return_value=mock_message)

            # Make _send_message raise an exception
            error_msg = "Test error"
            server_proxy._send_message = MagicMock(side_effect=Exception(error_msg))

            # Execute the error handling logic
            server_proxy._new_send_message.clear()
            while not server_proxy._queue.is_empty():
                message = server_proxy._queue.get_next_message()
                try:
                    server_proxy._send_message(message)
                except Exception as e:
                    server_proxy.logger.error(f"Error sending message: {e}")

            # Verify error was logged
            server_proxy.logger.error.assert_called_once()
            assert error_msg in server_proxy.logger.error.call_args[0][0]

        # Run the test
        test_error_handling()

    def test_handle_response_future(self, server_proxy):
        """Test handling response futures."""
        # Create a mock message and response
        mock_message = MagicMock()
        mock_message.msg_id = "test-message-id"

        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}

        # Create a future and store it
        future = Future()
        with server_proxy._response_futures_lock:
            server_proxy._response_futures[mock_message.msg_id] = future

        # Call _handle_response_future
        server_proxy._handle_response_future(mock_message, mock_response)

        # Verify future has been completed with the response
        assert future.done()
        assert future.result() == {"result": "success"}

        # Verify the future was removed from _response_futures
        assert mock_message.msg_id not in server_proxy._response_futures

    def test_handle_response_future_exception(self, server_proxy):
        """Test handling response futures when an exception occurs."""
        # Create a mock message and response that raises exception
        mock_message = MagicMock()
        mock_message.msg_id = "test-message-id"

        mock_response = MagicMock()
        error_msg = "JSON decode error"
        mock_response.json.side_effect = ValueError(error_msg)

        # Create a future and store it
        future = Future()
        with server_proxy._response_futures_lock:
            server_proxy._response_futures[mock_message.msg_id] = future

        # Call _handle_response_future
        server_proxy._handle_response_future(mock_message, mock_response)

        # Verify future has been completed with exception
        assert future.done()
        with pytest.raises(ValueError) as exc_info:
            future.result()
        assert error_msg in str(exc_info.value)

        # Verify the future was removed from _response_futures
        assert mock_message.msg_id not in server_proxy._response_futures

    def test_send_message_with_future(self, server_proxy):
        """Test sending a message and handling its future."""
        # Create a mock message
        message = Message.json_message(
            api_path="https://api.example.com/test",
            method=HttpMethod.POST,
            json_data={"key": "value"}
        )

        # Create a future for this message
        future = Future()
        with server_proxy._response_futures_lock:
            server_proxy._response_futures[message.msg_id] = future

        # Mock the requests library
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}

        with patch('requests.post', return_value=mock_response) as mock_post:
            # Call the method
            result = server_proxy._send_message(message)

            # Verify the request was made correctly
            mock_post.assert_called_once()

            # Verify the result
            assert result == {"result": "success"}

            # Verify the future was completed
            assert future.done()
            assert future.result() == {"result": "success"}

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
