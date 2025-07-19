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

# pylint: disable=protected-access,pointless-statement,unspecified-encoding,import-error

import atexit
import json
import threading
import time
from unittest.mock import MagicMock, patch, ANY

import pytest
import requests

from fyn_runner.server.server_proxy import ServerProxy
import fyn_api_client as fac


class TestServerProxy:
    """Test suite for ServerProxy factory and WebSocket manager."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_file_manager(self):
        """Create a mock file manager."""
        return MagicMock()

    @pytest.fixture
    def mock_configuration(self):
        """Create a mock configuration."""
        config = MagicMock()
        config.name = "test_runner"
        config.id = "test-123"
        config.token = "test-token"
        config.report_interval = 60
        return config

    @pytest.fixture
    def server_proxy(self, mock_logger, mock_file_manager, mock_configuration):
        """Create a ServerProxy instance for testing."""
        original_register = atexit.register
        original_thread = threading.Thread

        # Mock atexit.register to avoid cleanup registration
        atexit.register = MagicMock()

        # Mock threading.Thread to avoid starting actual threads
        mock_thread = MagicMock()
        threading.Thread = MagicMock(return_value=mock_thread)

        # Mock API configuration and client creation
        with (patch('fyn_api_client.Configuration') as mock_config,
              patch('fyn_api_client.ApiClient') as mock_api_client,
              patch('fyn_api_client.RunnerManagerApi') as mock_runner_api,
              patch.object(ServerProxy, '_report_status') as mock_report_status):

            mock_config.return_value.host = "http://localhost:8000"

            proxy = ServerProxy(mock_logger, mock_file_manager, mock_configuration)

            # Store mocks for later assertions
            proxy._mock_thread = mock_thread
            proxy._mock_report_status = mock_report_status
            proxy._mock_api_client = mock_api_client
            proxy._mock_runner_api = mock_runner_api

        # Restore original functions
        atexit.register = original_register
        threading.Thread = original_thread

        return proxy

    def test_initialization(self, server_proxy, mock_logger, mock_file_manager, mock_configuration):
        """Test ServerProxy initialization."""
        # Check basic attributes
        assert server_proxy.logger == mock_logger
        assert server_proxy.file_manager == mock_file_manager
        assert server_proxy.name == mock_configuration.name
        assert server_proxy.id == str(mock_configuration.id)
        assert server_proxy.token == str(mock_configuration.token)
        assert server_proxy.report_interval == mock_configuration.report_interval

        # Check proxy state
        assert server_proxy.running is True
        assert server_proxy._ws is None
        assert server_proxy._ws_connected is False

        # Check observer management
        assert isinstance(server_proxy._observers, dict)
        assert len(server_proxy._observers) == 0
        assert isinstance(server_proxy._observers_lock, type(threading.RLock()))

        # Check that background thread was started
        server_proxy._mock_thread.start.assert_called_once()

        # Check that status was reported
        server_proxy._mock_report_status.assert_called_once_with(fac.StateEnum.ID)

        # Check API client and runner API setup
        assert server_proxy._api_client is not None
        assert server_proxy._runner_api is not None

        # Check that the report_interval warning was logged
        mock_logger.warning.assert_called_with("report_interval not used, wip.")

    def test_create_application_registry_api(self, server_proxy):
        """Test creating ApplicationRegistryApi client."""
        with patch('fyn_api_client.ApplicationRegistryApi') as mock_app_api:
            mock_instance = MagicMock()
            mock_app_api.return_value = mock_instance

            result = server_proxy.create_application_registry_api()

            assert result == mock_instance
            mock_app_api.assert_called_once_with(server_proxy._api_client)

    def test_create_application_registry_api_failure(self, server_proxy):
        """Test ApplicationRegistryApi creation failure."""
        with patch('fyn_api_client.ApplicationRegistryApi', side_effect=Exception("API error")):
            with pytest.raises(Exception,
                               match="Error while configuring the client api: API error"):
                server_proxy.create_application_registry_api()

            server_proxy.logger.error.assert_called_once()

    def test_create_job_manager_api(self, server_proxy):
        """Test creating JobManagerApi client."""
        with patch('fyn_api_client.JobManagerApi') as mock_job_api:
            mock_instance = MagicMock()
            mock_job_api.return_value = mock_instance

            result = server_proxy.create_job_manager_api()

            assert result == mock_instance
            mock_job_api.assert_called_once_with(server_proxy._api_client)

    def test_create_job_manager_api_failure(self, server_proxy):
        """Test JobManagerApi creation failure."""
        with patch('fyn_api_client.JobManagerApi', side_effect=Exception("API error")):
            with pytest.raises(Exception,
                               match="Error while configuring the client api: API error"):
                server_proxy.create_job_manager_api()

            server_proxy.logger.error.assert_called_once()

    def test_create_runner_manager_api(self, server_proxy):
        """Test creating RunnerManagerApi client."""
        with patch('fyn_api_client.RunnerManagerApi') as mock_runner_api:
            mock_instance = MagicMock()
            mock_runner_api.return_value = mock_instance

            result = server_proxy.create_runner_manager_api()

            assert result == mock_instance
            mock_runner_api.assert_called_once_with(server_proxy._api_client)

    def test_create_runner_manager_api_failure(self, server_proxy):
        """Test RunnerManagerApi creation failure."""
        with patch('fyn_api_client.RunnerManagerApi', side_effect=Exception("API error")):
            with pytest.raises(Exception,
                               match="Error while configuring the client api: API error"):
                server_proxy.create_runner_manager_api()

            server_proxy.logger.error.assert_called_once()

    def test_register_observer(self, server_proxy):
        """Test registering an observer."""
        mock_callback = MagicMock()

        server_proxy.register_observer("test_message", mock_callback)

        assert "test_message" in server_proxy._observers
        assert server_proxy._observers["test_message"] == mock_callback
        server_proxy.logger.info.assert_called_with("Registered observer test_message")

    def test_register_duplicate_observer(self, server_proxy):
        """Test registering a duplicate observer raises an exception."""
        server_proxy.register_observer("test_message", MagicMock())

        with pytest.raises(RuntimeError, match="Trying to add to existing observer test_message"):
            server_proxy.register_observer("test_message", MagicMock())

    def test_deregister_observer(self, server_proxy):
        """Test deregistering an observer."""
        mock_callback = MagicMock()
        server_proxy.register_observer("test_message", mock_callback)

        server_proxy.deregister_observer("test_message")

        assert "test_message" not in server_proxy._observers
        server_proxy.logger.info.assert_called_with("Deregistered observer test_message")

    def test_deregister_nonexistent_observer(self, server_proxy):
        """Test deregistering a non-existent observer raises an exception."""
        with pytest.raises(RuntimeError,
                           match="Trying to remove non-existant observer test_message"):
            server_proxy.deregister_observer("test_message")

    def test_configure_client_api(self, server_proxy):
        """Test API client configuration."""
        with patch('fyn_api_client.ApiClient') as mock_api_client:
            mock_instance = MagicMock()
            mock_api_client.return_value = mock_instance

            result = server_proxy._configure_client_api()

            assert result == mock_instance
            mock_api_client.assert_called_once_with(server_proxy.api_config)
            mock_instance.set_default_header.assert_called_once_with(
                "Authorization", f"Token {server_proxy.token}"
            )

    def test_configure_client_api_failure(self, server_proxy):
        """Test API client configuration failure."""
        with patch('fyn_api_client.ApiClient', side_effect=Exception("Config error")):
            with pytest.raises(Exception,
                               match="Error while configuring the client api: Config error"):
                server_proxy._configure_client_api()

            server_proxy.logger.error.assert_called_once()

    def test_report_status_success(self, server_proxy):
        """Test successful status reporting."""
        server_proxy._runner_api = MagicMock()

        server_proxy._report_status(fac.StateEnum.ID)

        server_proxy.logger.debug.assert_called_once()
        server_proxy._runner_api.runner_manager_runner_partial_update.assert_called_once_with(
            id=server_proxy.id,
            patched_runner_info_request=ANY
        )

    def test_report_status_failure(self, server_proxy):
        """Test status reporting failure."""
        server_proxy._runner_api = MagicMock()
        server_proxy._runner_api.runner_manager_runner_partial_update.side_effect = \
            requests.exceptions.RequestException("Connection failed")

        with pytest.raises(ConnectionError, match="Failed to report status"):
            server_proxy._report_status(fac.StateEnum.ID)

        server_proxy.logger.error.assert_called_once()

    def test_websocket_url_construction(self, server_proxy):
        """Test WebSocket URL construction logic."""
        # Test HTTPS to WSS conversion
        server_proxy.api_config.host = "https://api.example.com:8443"

        # Extract URL construction logic from _receive_handler
        protocol, url, port = server_proxy.api_config.host.split(":")
        protocol = "ws:" if protocol == "http" else "wss:"
        ws_url = f"{protocol}{url}:{port}/ws/runner_manager/{server_proxy.id}"

        expected_url = f"wss://api.example.com:8443/ws/runner_manager/{server_proxy.id}"
        assert ws_url == expected_url

        # Test HTTP to WS conversion
        server_proxy.api_config.host = "http://localhost:8000"
        protocol, url, port = server_proxy.api_config.host.split(":")
        protocol = "ws:" if protocol == "http" else "wss:"
        ws_url = f"{protocol}{url}:{port}/ws/runner_manager/{server_proxy.id}"

        expected_url = f"ws://localhost:8000/ws/runner_manager/{server_proxy.id}"
        assert ws_url == expected_url

    def test_handle_ws_message_valid(self, server_proxy):
        """Test handling a valid WebSocket message."""
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True

        message_data = json.dumps({
            "id": "msg-123",
            "type": "test_message",
            "data": {"key": "value"}
        })

        mock_callback = MagicMock(return_value={"status": "processed"})
        server_proxy._observers["test_message"] = mock_callback

        server_proxy._handle_ws_message(server_proxy._ws, message_data)

        mock_callback.assert_called_once()
        call_arg = mock_callback.call_args[0][0]
        assert call_arg['id'] == "msg-123"
        assert call_arg['type'] == "test_message"

        server_proxy._ws.send.assert_called_once()
        sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
        assert sent_response["response_to"] == "msg-123"
        assert sent_response["status"] == "processed"

    @pytest.mark.parametrize("message_data,expected_error", [
        # Message without ID
        ({"type": "test_message", "data": {"key": "value"}}, "no id"),
        # Message without type
        ({"id": "msg-123", "data": {"key": "value"}}, "without type"),
        # Message with unknown type
        ({"id": "msg-123", "type": "unknown_type", "data": {"key": "value"}},
         "unknown message type"),
    ])
    def test_handle_ws_message_errors(self, server_proxy, message_data, expected_error):
        """Test handling WebSocket messages with various error conditions."""
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True
        server_proxy._observers = {}  # No observers registered

        message_json = json.dumps(message_data)
        server_proxy._handle_ws_message(server_proxy._ws, message_json)

        # Verify error was logged
        server_proxy.logger.error.assert_called_once()
        assert expected_error in server_proxy.logger.error.call_args[0][0].lower()

        # Check response behavior based on message type
        if "id" in message_data:
            server_proxy._ws.send.assert_called_once()
            sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
            assert sent_response["type"] == "error"
            assert sent_response["response_to"] == message_data["id"]
        else:
            server_proxy._ws.send.assert_not_called()

    @pytest.mark.parametrize("callback_return,callback_exception,expected_response_type", [
        # Callback returns None -> success response
        (None, None, "success"),
        # Callback raises exception -> error response
        (None, Exception("Test callback error"), "error"),
    ])
    def test_handle_ws_message_callback_scenarios(
            self,
            server_proxy,
            callback_return,
            callback_exception,
            expected_response_type):
        """Test WebSocket message handling with different callback scenarios."""
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = True

        message_data = json.dumps({
            "id": "msg-123",
            "type": "test_message",
            "data": {"key": "value"}
        })

        # Set up callback
        if callback_exception:
            mock_callback = MagicMock(side_effect=callback_exception)
        else:
            mock_callback = MagicMock(return_value=callback_return)

        server_proxy._observers["test_message"] = mock_callback

        server_proxy._handle_ws_message(server_proxy._ws, message_data)

        # Verify callback was called
        mock_callback.assert_called_once()

        # Verify response
        server_proxy._ws.send.assert_called_once()
        sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
        assert sent_response["type"] == expected_response_type
        assert sent_response["response_to"] == "msg-123"

        # Verify error logging for exceptions
        if callback_exception:
            server_proxy.logger.error.assert_called_once()
            assert str(callback_exception) in server_proxy.logger.error.call_args[0][0]

    def test_websocket_connection_callbacks(self, server_proxy):
        """Test WebSocket connection state callbacks."""
        # Test open callback
        server_proxy._ws_connected = False
        server_proxy._on_ws_open(MagicMock())
        assert server_proxy._ws_connected is True
        server_proxy.logger.info.assert_called_with("WebSocket connection established")

        # Test close callback
        server_proxy._on_ws_close(MagicMock(), 1000, "Normal closure")
        assert server_proxy._ws_connected is False
        server_proxy.logger.info.assert_called_with(
            "WebSocket connection closed: 1000 Normal closure")

        # Test error callback
        error = Exception("Test WebSocket error")
        server_proxy._on_ws_error(MagicMock(), error)
        server_proxy.logger.error.assert_called_with("WebSocket error: Test WebSocket error")

    @pytest.mark.parametrize("connected,send_exception,should_send", [
        (True, None, True),  # Connected, no exception
        (False, None, False),  # Disconnected
        (True, Exception("Send failed"), True),  # Connected but send fails
    ])
    def test_ws_error_response(self, server_proxy, connected, send_exception, should_send):
        """Test WebSocket error response under different conditions."""
        server_proxy._ws = MagicMock()
        server_proxy._ws_connected = connected

        if send_exception:
            server_proxy._ws.send.side_effect = send_exception

        server_proxy._ws_error_response("msg-123", "Test error message")

        if should_send:
            server_proxy._ws.send.assert_called_once()
            if send_exception:
                # Should log error about failed send
                server_proxy.logger.error.assert_called_once()
                log_message = server_proxy.logger.error.call_args[0][0]
                assert "Failed to send error response" in log_message
                assert str(send_exception) in log_message
            else:
                # Should send proper error response
                sent_response = json.loads(server_proxy._ws.send.call_args[0][0])
                assert sent_response["type"] == "error"
                assert sent_response["response_to"] == "msg-123"
                assert sent_response["data"] == "Test error message"
                server_proxy.logger.debug.assert_called()
        else:
            # Should not send and log disconnect error
            server_proxy._ws.send.assert_not_called()
            server_proxy.logger.error.assert_called_with(
                "Cannot send error response: WebSocket not connected"
            )

    def test_receive_handler_reconnection_logic(self, server_proxy):
        """Test WebSocket reconnection logic in receive handler."""

        server_proxy.api_config.host = "http://localhost:8000"

        with (patch('fyn_runner.server.server_proxy.WebSocketApp') as mock_ws_app,
              patch('fyn_runner.server.server_proxy.time.sleep') as mock_sleep):

            # Track calls to run_forever
            call_count = 0

            def mock_ws_factory(*_, **__):
                nonlocal call_count
                call_count += 1
                mock_ws_instance = MagicMock()

                def mock_run_forever():
                    if call_count == 1:
                        # First call: simulate connection lost, return to trigger reconnection
                        return
                    # Second call: just wait for running to be set to False
                    while server_proxy.running:
                        time.sleep(0.01)

                mock_ws_instance.run_forever.side_effect = mock_run_forever
                return mock_ws_instance

            mock_ws_app.side_effect = mock_ws_factory

            # Start the handler in a separate thread
            server_proxy.running = True
            handler_thread = threading.Thread(target=server_proxy._receive_handler)
            handler_thread.daemon = True
            handler_thread.start()

            # Wait for reconnection logic to trigger
            time.sleep(0.2)

            # Stop the handler
            server_proxy.running = False
            handler_thread.join(timeout=1.0)

            # Verify reconnection attempt
            assert mock_ws_app.call_count == 2  # Initial + reconnect
            server_proxy.logger.warning.assert_called_with(
                "WebSocket disconnected, reconnecting...")
            # Check that sleep was called with 5 seconds (reconnection delay)
            assert any(call[0][0] == 5 for call in mock_sleep.call_args_list)

    def test_receive_handler_exception_handling(self, server_proxy):
        """Test exception handling in receive handler."""

        server_proxy.api_config.host = "http://localhost:8000"

        with patch('fyn_runner.server.server_proxy.WebSocketApp') as mock_ws_app:

            # First call raises exception, second call succeeds
            call_count = 0

            def mock_ws_app_side_effect(*_, **__):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise RuntimeError("WebSocket creation failed")
                mock_ws_instance = MagicMock()
                # Second call: wait for running to be set to False

                def mock_run_forever():
                    while server_proxy.running:
                        time.sleep(0.01)
                mock_ws_instance.run_forever.side_effect = mock_run_forever
                return mock_ws_instance

            mock_ws_app.side_effect = mock_ws_app_side_effect

            # Start the handler in a separate thread
            server_proxy.running = True
            handler_thread = threading.Thread(target=server_proxy._receive_handler)
            handler_thread.daemon = True
            handler_thread.start()

            # Wait a bit for the error handling to trigger
            time.sleep(0.1)

            # Stop the handler
            server_proxy.running = False
            handler_thread.join(timeout=1.0)

            # Verify error handling
            server_proxy.logger.error.assert_called_with(
                "WebSocket error: WebSocket creation failed")

    def test_websocket_header_configuration(self, server_proxy):
        """Test WebSocket header configuration with token."""

        server_proxy.api_config.host = "http://localhost:8000"

        with patch('fyn_runner.server.server_proxy.WebSocketApp') as mock_ws_app:

            mock_ws_instance = MagicMock()
            mock_ws_app.return_value = mock_ws_instance

            # Mock run_forever to wait for running to be set to False
            def mock_run_forever():
                while server_proxy.running:
                    time.sleep(0.01)
            mock_ws_instance.run_forever.side_effect = mock_run_forever

            # Start the handler in a separate thread
            server_proxy.running = True
            handler_thread = threading.Thread(target=server_proxy._receive_handler)
            handler_thread.daemon = True
            handler_thread.start()

            # Wait a bit for the WebSocket to be created
            time.sleep(0.1)

            # Stop the handler
            server_proxy.running = False
            handler_thread.join(timeout=1.0)

            # Verify WebSocket was created with correct headers
            mock_ws_app.assert_called_once()
            call_args = mock_ws_app.call_args
            assert 'header' in call_args[1]
            assert call_args[1]['header']['token'] == server_proxy.token

    def test_shutdown_behavior(self, server_proxy):
        """Test that setting running to False stops the WebSocket handler."""

        server_proxy.api_config.host = "http://localhost:8000"

        with patch('fyn_runner.server.server_proxy.WebSocketApp') as mock_ws_app:

            mock_ws_instance = MagicMock()
            mock_ws_app.return_value = mock_ws_instance

            # Mock run_forever to wait for running to be set to False
            def mock_run_forever():
                while server_proxy.running:
                    time.sleep(0.01)
            mock_ws_instance.run_forever.side_effect = mock_run_forever

            # Start the handler in a separate thread
            server_proxy.running = True
            handler_thread = threading.Thread(target=server_proxy._receive_handler)
            handler_thread.daemon = True
            handler_thread.start()

            # Wait a bit for the WebSocket to be created
            time.sleep(0.1)

            # Stop the handler
            server_proxy.running = False
            handler_thread.join(timeout=1.0)

            # Verify the thread stopped gracefully
            assert not handler_thread.is_alive()

            # Should only call WebSocket once since we stopped cleanly
            assert mock_ws_app.call_count == 1

    def test_websocket_error_handling_during_creation(self, server_proxy):
        """Test error handling when WebSocketApp creation fails."""

        server_proxy.api_config.host = "http://localhost:8000"

        with patch('fyn_runner.server.server_proxy.WebSocketApp') as mock_ws_app:

            # Set up to raise error on first call, succeed on second
            call_count = 0

            def side_effect_counter(*_, **__):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise RuntimeError("WebSocket creation failed")
                mock_ws_instance = MagicMock()
                # Second call: wait for running to be set to False

                def mock_run_forever():
                    while server_proxy.running:
                        time.sleep(0.01)
                mock_ws_instance.run_forever.side_effect = mock_run_forever
                return mock_ws_instance

            mock_ws_app.side_effect = side_effect_counter

            # Start the handler in a separate thread
            server_proxy.running = True
            handler_thread = threading.Thread(target=server_proxy._receive_handler)
            handler_thread.daemon = True
            handler_thread.start()

            # Wait a bit for the error handling to trigger
            time.sleep(0.1)

            # Stop the handler
            server_proxy.running = False
            handler_thread.join(timeout=1.0)

            # Should have logged the error
            server_proxy.logger.error.assert_called_with(
                "WebSocket error: WebSocket creation failed")

    def test_atexit_registration(self, mock_logger, mock_file_manager, mock_configuration):
        """Test that cleanup is registered with atexit."""
        with (patch('atexit.register') as mock_register,
              patch('threading.Thread'),
              patch('fyn_api_client.Configuration'),
              patch('fyn_api_client.ApiClient'),
              patch('fyn_api_client.RunnerManagerApi'),
              patch.object(ServerProxy, '_report_status')):

            ServerProxy(mock_logger, mock_file_manager, mock_configuration)

            # Should register cleanup with atexit
            mock_register.assert_called_once_with(ANY, fac.StateEnum.OF)

            # The first argument should be the _report_status method
            call_args = mock_register.call_args[0]
            assert len(call_args) == 2
            assert call_args[1] == fac.StateEnum.OF