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

import atexit
import json
import threading
import time
import requests
from websocket import WebSocketApp

import fyn_api_client as fac


class ServerProxy:
    """Factory for REST API clients and WebSocket communication manager.

    This class serves a dual purpose: it acts as a factory for creating OpenAPI-generated REST
    client instances for communicating with the Django backend, and manages a persistent WebSocket
    connection for real-time message handling using an observer pattern.

    The proxy automatically reports runner status changes to the backend and handles WebSocket
    reconnection. It maintains thread-safe observer registration for different message types
    received via WebSocket.

    TODO: This class should ideally be refactored into separate rest_factory and web_socket_proxy
          components in the future.

    Attributes:
        running (bool): Flag indicating if the proxy should continue operating.
        name (str): Runner name from configuration.
        id (str): Runner ID for backend identification.
        token (str): Authentication token for API requests.
    """

    def __init__(self, logger, file_manager, configuration):
        """Initialize the ServerProxy with backend communication capabilities.

        Sets up REST API client configuration, initializes WebSocket connection, and starts the
        background WebSocket handler thread. Automatically reports initial status and registers
        cleanup handler.

        Args:
            logger: Logger instance for debugging and error reporting.
            file_manager: File manager instance (injected dependency).
            configuration: Configuration object containing runner details.
                Must have attributes: name, id, token, report_interval.

        Raises:
            Exception: If API client configuration fails.
            ConnectionError: If initial status reporting fails.
        """

        # injected objects
        self.logger = logger
        self.file_manager = file_manager

        # configs
        self.name = configuration.name
        self.id = str(configuration.id)
        self.token = str(configuration.token)
        self.report_interval = configuration.report_interval
        self.api_config = fac.Configuration()
        logger.warning("report_interval not used, wip.")

        # Proxy Status
        self.running: bool = True

        # HTTP message handing and related
        self._api_client = self._configure_client_api()
        self._runner_api = self.create_runner_manager_api()

        # Websocket message handling and related
        self._observers = {}
        self._observers_lock = threading.RLock()
        self._ws: WebSocketApp = None  # only the _ws_thread should access
        self._ws_connected: bool = False
        self._ws_thread: threading.Thread = threading.Thread(target=self._receive_handler)
        self._ws_thread.daemon = True

        # initialisation procedure
        self._report_status(fac.StateEnum.ID)
        atexit.register(self._report_status, fac.StateEnum.OF)
        self._ws_thread.start()

    # ----------------------------------------------------------------------------------------------
    #  Server Proxy Interface
    # ----------------------------------------------------------------------------------------------

    def create_application_registry_api(self):
        """Create and return an ApplicationRegistryApi client instance.

        Returns:
            fyn_api_client.ApplicationRegistryApi: Configured API client for application registry
            operations.

        Raises:
            RuntimeError: If API client creation fails.
        """
        try:
            job_api = fac.ApplicationRegistryApi(self._api_client)
        except Exception as e:
            self.logger.error(f"Error while configuring the client api: {str(e)}")
            raise RuntimeError(f"Error while configuring the client api: {str(e)}") from e
        return job_api

    def create_job_manager_api(self):
        """Create and return a JobManagerApi client instance.

        Returns:
            fyn_api_client.JobManagerApi: Configured API client for job management operations.

        Raises:
            RuntimeError: If API client creation fails.
        """
        try:
            job_api = fac.JobManagerApi(self._api_client)
        except Exception as e:
            self.logger.error(f"Error while configuring the client api: {str(e)}")
            raise RuntimeError(f"Error while configuring the client api: {str(e)}") from e
        return job_api

    def create_runner_manager_api(self):
        """Create and return a RunnerManagerApi client instance.

        Returns:
            fyn_api_client.RunnerManagerApi: Configured API client for runner management operations.

        Raises:
            RuntimeError: If API client creation fails.
        """
        try:
            runner_api = fac.RunnerManagerApi(self._api_client)
        except Exception as e:
            self.logger.error(f"Error while configuring the client api: {str(e)}")
            raise RuntimeError(f"Error while configuring the client api: {str(e)}") from e
        return runner_api

    def register_observer(self, message_type, call_back):
        """Register a callback function for WebSocket messages of a specific type.

        Each message type can have only one observer at a time. The callback will be invoked
        whenever a WebSocket message of the specified type is received.

        Args:
            message_type (str): The type of message to observe.
            call_back (callable): Function to call when message is received. Should accept a message
                dict parameter and return an optional response dict.

        Raises:
            RuntimeError: If an observer is already registered for this message type.
        """
        with self._observers_lock:
            if message_type not in self._observers:
                self._observers[message_type] = call_back
                self.logger.info(f"Registered observer {message_type}")
            else:
                raise RuntimeError(f"Trying to add to existing observer {message_type}")

    def deregister_observer(self, message_type):
        """Remove a previously registered observer for the specified message type.

        Args:
            message_type (str): The type of message for which to remove the observer.

        Raises:
            RuntimeError: If no observer is registered for this message type.
        """
        with self._observers_lock:
            if message_type in self._observers:
                del self._observers[message_type]
                self.logger.info(f"Deregistered observer {message_type}")
            else:
                raise RuntimeError(f"Trying to remove non-existant observer {message_type}")

    # ----------------------------------------------------------------------------------------------
    #  Internal Backend HTTP Reporting Methods
    # ----------------------------------------------------------------------------------------------

    def _configure_client_api(self):
        """Configure and return the base API client with authentication.

        Returns:
            fyn_api_client.ApiClient: Configured API client with authorization header.

        Raises:
            Exception: If API client configuration fails.
        """
        try:
            api_client = fac.ApiClient(self.api_config)
            api_client.set_default_header("Authorization", f"Token {str(self.token)}")
        except Exception as e:
            self.logger.error(f"Error while configuring the client api: {str(e)}")
            raise RuntimeError(f"Error while configuring the client api: {str(e)}") from e
        return api_client

    def _report_status(self, status):
        """Report the runner's current status to the backend server.

        Args:
            status (fyn_api_client.StateEnum): The status to report to the server.
            request_timeout (int, optional): HTTP request timeout in seconds. Defaults to 10.

        Raises:
            ConnectionError: If the HTTP request to report status fails.
        """

        self.logger.debug(f"Reporting status {status.value}")
        try:
            self._runner_api.runner_manager_runner_partial_update(
                id=self.id,
                patched_runner_info_request=fac.PatchedRunnerInfoRequest(state=status),
            )
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to report status '{status}': {str(e)}")
            raise ConnectionError(f"Failed to report status '{status}': {str(e)}") from e

    # ----------------------------------------------------------------------------------------------
    #  Internal Web Socket Methods
    # ----------------------------------------------------------------------------------------------

    def _receive_handler(self):
        """Background thread handler for WebSocket connection management.

        Runs in a separate daemon thread and handles:
        - Establishing WebSocket connection to the backend
        - Automatic reconnection on connection loss
        - WebSocket error handling and recovery

        Continues attempting connection until self.running is set to False.
        """

        [protocol, url, port] = self.api_config.host.split(":")
        protocol = "ws:" if protocol == "http" else "wss:"
        ws_url = f"{protocol}{url}:{port}/ws/runner_manager/{self.id}"
        self.logger.debug(f"Starting WebSocket on {ws_url}")

        while self.running:
            try:
                self._ws = WebSocketApp(
                    ws_url,
                    header={'token': f'{self.token}'},
                    on_message=self._handle_ws_message,
                    on_open=self._on_ws_open,
                    on_close=self._on_ws_close,
                    on_error=self._on_ws_error
                )

                self._ws.run_forever()

                if self.running:
                    self.logger.warning("WebSocket disconnected, reconnecting...")
                    time.sleep(5)
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                time.sleep(5)

    def _handle_ws_message(self, _ws, message_data):
        """Process incoming WebSocket messages and route to appropriate observers.

        Parses JSON message data, validates required fields, and invokes the registered observer
        callback for the message type. Sends response back to server.

        Args:
            _ws (WebSocketApp): The WebSocket instance that received the message.
            message_data (str): Raw JSON message string from the server.
        """

        message = json.loads(message_data)
        message_id = message.get('id')
        message_type = message.get('type')

        if not message_id:
            self.logger.error(f"Received message with no id: {message}")
            return

        if not message_type:
            self.logger.error(f"Received message {message_id} without type.")
            self._ws_error_response(message_id,
                                    "Websocket messages must contain a 'type' field.")
            return

        self.logger.debug(f"Received WebSocket message ({message_id}) {message_type}")

        callback = None
        with self._observers_lock:
            callback = self._observers.get(message_type)

        if callback:
            try:
                response = callback(message)

                if not response:
                    response = {'type': 'success'}

                if 'id' not in response and message_id:
                    response['response_to'] = message_id

                self._ws.send(json.dumps(response))
                self.logger.info(f"Websocket success response for message {message_id}")

            except Exception as e:
                error_msg = f"Error while processing message{message_id} {message_type}: {e}"
                self.logger.error(error_msg)
                self._ws_error_response(message_id, error_msg)

        else:
            error_msg = f"Unknown message type {message_type} for message {message_id}"
            self.logger.error(error_msg)
            self._ws_error_response(message_id, error_msg)

    def _on_ws_open(self, _ws):
        """WebSocket connection established callback.

        Args:
            _ws (WebSocketApp): The WebSocket instance that was opened.
        """
        self.logger.info("WebSocket connection established")
        self._ws_connected = True

    def _on_ws_close(self, _ws, close_status_code, close_msg):
        """WebSocket connection closed callback.

        Args:
            _ws (WebSocketApp): The WebSocket instance that was closed.
            close_status_code (int): Status code indicating why connection was closed.
            close_msg (str): Message associated with the close status.
        """
        self.logger.info(f"WebSocket connection closed: {close_status_code} {close_msg}")
        self._ws_connected = False

    def _on_ws_error(self, _ws, error):
        """WebSocket error callback.

        Args:
            _ws (WebSocketApp): The WebSocket instance that encountered an error.
            error (Exception): The error that occurred.
        """
        self.logger.error(f"WebSocket error: {error}")

    def _ws_error_response(self, message_id, data):
        """Send standardized error response via WebSocket.

        Constructs and sends an error response message back to the server
        for the specified message ID.

        Args:
            message_id (str): ID of the message being responded to.
            data (str): Error message or details to include in the response.
        """

        if self._ws and self._ws_connected:  # Check connection state
            error_response = {
                "type": "error",
                "response_to": message_id,
                "data": data
            }
            try:
                self._ws.send(json.dumps(error_response))
                self.logger.debug(f"Sent error response: {error_response}")
            except Exception as e:
                self.logger.error(f"Failed to send error response: {e}")
        else:
            self.logger.error("Cannot send error response: WebSocket not connected")
