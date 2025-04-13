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
from concurrent.futures import Future
from urllib.parse import urljoin

import requests
from websocket import WebSocketApp

from fyn_runner.server.message import HttpMethod, Message
from fyn_runner.server.message_queue import MessageQueue


class ServerProxy:
    """todo

    TODO: Package locks and data into a generalised class.
    """

    def __init__(self, logger, file_manager, configuration):
        """todo"""

        # injected objects
        self.logger = logger
        self.file_manager = file_manager

        # configs
        self.name = configuration.name
        self.id = configuration.id
        self.token = configuration.token
        self.api_url = str(configuration.api_url).rstrip('/')
        self.api_port = configuration.api_port
        self.report_interval = configuration.report_interval

        # Proxy Status
        self.running: bool = True

        # HTTP message handing and related
        self._queue: MessageQueue = MessageQueue()
        self._new_send_message: threading.Event = threading.Event()
        self._send_thread: threading.Thread = threading.Thread(target=self._send_handler)
        self._send_thread.daemon = True
        self._response_futures = {}
        self._response_futures_lock = threading.RLock()

        # Websocket message handling and related
        self._observers = {}
        self._observers_lock = threading.RLock()
        self._ws: WebSocketApp = None  # only the _ws_thread should access
        self._ws_connected: bool = False
        self._ws_thread: threading.Thread = threading.Thread(target=self._receive_handler)
        self._ws_thread.daemon = True

        # initialisation procedure
        self._fetch_api()
        self._raise_connection()  # don't catch here, allow propagation at initialisation.
        atexit.register(self._report_status, 'offline')
        self._send_thread.start()
        self._ws_thread.start()

    def push_message(self, message):
        """
        Add a message to the outgoing queue (non-blocking), and notifies the sending thread.

        Args:
            message (Message): The message to be sent

        Returns:
            None

        Raises:
            Exception: If the message couldn't be added to the queue.
        """
        try:
            self.logger.debug(f"Pushing message {message.msg_id}")
            self._queue.push_message(message)
            self._new_send_message.set()
        except Exception as e:
            self.logger.error(f"Failed to push message ({message.msg_id}): {e}")
            raise  # ensures caller knows

    def push_message_with_response(self, message):
        """
        Add a message to the outgoing queue and return a Future for the response.

        Args:
            message (Message): The message to be sent

        Returns:
            Future: A Future that will contain the server response

        Raises:
            Exception: If the message couldn't be added to the queue or the event couldn't be set.
        """

        new_future = Future()
        with self._response_futures_lock:
            self._response_futures[message.msg_id] = new_future

        try:
            self.push_message(message)
            return new_future
        except Exception:  # logger would have reported error, just clean future.
            with self._response_futures_lock:
                self._response_futures.pop(message.msg_id)
            raise  # ensures caller knows

    def register_observer(self, message_type, call_back):
        """
        Register a callback function to be invoked when messages of the specified type are received.

        Each message type can have only one observer at a time. Attempting to register a second
        observer for the same message type will raise a RuntimeError.

        Args:
            message_type (str): The type of message to observe
            call_back (callable): Function to be called when a message of this type is received.
                                Should accept a message parameter and return an optional response.

        Raises:
            RuntimeError: If an observer is already registered for this message type
        """
        with self._observers_lock:
            if message_type not in self._observers:
                self._observers[message_type] = call_back
                self.logger.info(f"Registered observer {message_type}")
            else:
                raise RuntimeError(f"Trying to add to existing observer {message_type}")

    def deregister_observer(self, message_type):
        """
        Remove a previously registered observer for the specified message type.

        Args:
            message_type (str): The type of message for which to remove the observer

        Raises:
            RuntimeError: If no observer is registered for this message type
        """
        with self._observers_lock:
            if message_type in self._observers:
                del self._observers[message_type]
                self.logger.info(f"Deregistered observer {message_type}")
            else:
                raise RuntimeError(f"Trying to remove non-existant observer {message_type}")

    def _report_status(self, status, request_timeout=10):
        """
        Report the runner's current status to the server.

        Args:
            status (str): The status to report to the server. Common values include:
            - 'idle': Runner is online but not processing any jobs
            - 'busy': Runner is currently processing a job
            - 'offline': Runner is shutting down
            request_timeout (int, optional): Timeout value in seconds for the HTTP request.
            Defaults to 10 seconds.

        Returns:
            None

        Raises:
            ConnectionError: If any network-related errors occur during the status update,
                including connection errors, timeouts, or HTTP error responses.
        """

        try:
            self._send_message(Message.json_message(
                f"{self.api_url}:{self.api_port}/runner_manager/report_status/",
                HttpMethod.PATCH,
                {"state": str(status)},
            ), request_timeout=request_timeout)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to report status '{status}': {str(e)}")
            raise ConnectionError(f"Failed to report status '{status}': {str(e)}") from e

    def _raise_connection(self):
        """
        This method is called during the initialization of the ServerProxy. A successful call
        indicates that the runner has been registered with the server and is ready to receive jobs.

        Returns:
            None

        Raises:
            ConnectionError: If the connection to the server cannot be established, this method will
                propagate any ConnectionError raised by _report_status.

        """

        self.logger.info(f"Contacting {self.api_url}...")
        self._report_status('idle')

    def _fetch_api(self):
        """TODO"""
        self.logger.info("fetching backend API... STILL TO DO")

    def _send_handler(self):
        """
        Background kernel for thread that processes outgoing messages and handles periodic status
        reporting.

        This method runs in a separate thread and:
            1. Waits for new messages to be added to the queue or timeout to occur
            2. Processes all available messages when notified
            3. Sends periodic status reports to the server based on report_interval

        The thread continues running until self._running is set to False.
        """

        next_report_time = time.time() + self.report_interval
        while self.running:
            wait_time = max(0.0, next_report_time - time.time())
            message_added = self._new_send_message.wait(timeout=wait_time)

            # Check and send all messages
            if message_added:
                self._new_send_message.clear()
                while not self._queue.is_empty():
                    message = self._queue.get_next_message()
                    try:
                        self._send_message(message)
                    except Exception as e:
                        self.logger.error(f"Error sending message ({message.msg_id}): {e}")

            # Check if we need to report status
            current_time = time.time()
            if current_time >= next_report_time:
                try:
                    self._report_status('idle')
                except Exception:
                    pass  # error reported in _report_status, no further action required

                next_report_time = current_time + self.report_interval

    def _send_message(self, message, request_timeout=10):
        """
        Send the parsed message to the backend.

        Constructs and sends the full HTTP request based on the provided Message object. Handles
        various message types (JSON, file) and HTTP methods.

        Args:
            message (Message): The message to send
            request_timeout (int, optional): Timeout in seconds for the request. Defaults to 10.

        Returns:
            dict: JSON response from the server

        Raises:
            FileNotFoundError: If a file message references a non-existent file
            ValueError: If the HTTP method is not supported
            requests.exceptions.RequestException: For any network-related errors
        """

        kwargs = {
            "url": urljoin(str(message.api_path), str(self.id)),
            "headers": {"id": str(self.id), "token": str(self.token)},
            "params": message.params,
            "timeout": request_timeout
        }

        if message.header:
            kwargs["headers"].update(message.header)

        if message.file_path:
            if not message.file_path.exists():
                raise FileNotFoundError(f"File not found: {message.file_path}")
            with open(message.file_path, 'rb') as f:
                kwargs["files"] = {'file': f}
        elif message.json_data:
            kwargs["json"] = message.json_data

        response: requests.Response = None
        self.logger.debug(f"Sending message {message.msg_id},  {kwargs}")
        match message.method:
            case HttpMethod.GET:
                response = requests.get(**kwargs)
            case HttpMethod.POST:
                response = requests.post(**kwargs)
            case HttpMethod.PUT:
                response = requests.put(**kwargs)
            case HttpMethod.PATCH:
                response = requests.patch(**kwargs)
            case HttpMethod.DELETE:
                response = requests.delete(**kwargs)
            case _:
                raise ValueError(f"Unsupported HTTP method: {message.method.name}")

        try:
            response.raise_for_status()
            result = response.json()
            self._handle_response_future(message, response)
            self.logger.info(f"HTTP request successful for message ({message.msg_id}): "
                             f"{message.method.name} {message.api_path}")
        except requests.exceptions.HTTPError:
            result = response.json()
            self.logger.error(f"HTTP request error for message ({message.msg_id}): "
                              f"status_code: {response.status_code}, "
                              f"server message: {result['message']}")

        self._handle_response_future(message, response)

        return result

    def _handle_response_future(self, message, response):
        """
        Handles the response from the backend to the future result.

        Args:
            message(Message): The message store the result
            response(Response): The repose from the backend server.

        Raises:
            Exception: For any issue in trying to decode or set the server response.
        """

        with self._response_futures_lock:
            future = self._response_futures.pop(message.msg_id, None)
            if future:
                self.logger.debug(f"Updating future for message {message.msg_id}")
                try:
                    future.set_result(response.json())
                except Exception as e:
                    self.logger.error("Error setting future result for message "
                                      f"{message.msg_id}: {e}")
                    future.set_exception(e)

    def _receive_handler(self):
        """
        Background thread handler that manages WebSocket connection to the backend server.

        This method runs in a separate daemon thread and is responsible for:
        1. Establishing and maintaining the WebSocket connection
        2. Reconnecting if the connection is lost
        3. Handles any WebSocket errors

        The thread continues retrying the connection until self._running is set to False.
        """

        ws_url = self.api_url.replace('http://', 'ws://').replace('https://', 'wss://') \
            + f":{self.api_port}/ws/runner_manager/{self.id}"
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
        """
        Process incoming WebSocket messages from the server.

        This callback is invoked when a message is received over the WebSocket connection.
        It parses the message, identifies its type, and routes it to the appropriate observer.

        Args:
            _ws(WebSocketApp): The WebSocket instance that received the message
            message_data(str): The raw message string received from the server
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
        """
        Callback invoked when the WebSocket connection is established.

        Args:
            _ws(WebSocketApp): The WebSocket instance that was opened
        """
        self.logger.info("WebSocket connection established")
        self._ws_connected = True

    def _on_ws_close(self, _ws, close_status_code, close_msg):
        """
        Callback invoked when the WebSocket connection is closed.

        Args:
            _ws(WebSocketApp): The WebSocket instance that was closed
            close_status_code(int): The status code indicating why the connection was closed
            close_msg(str): The message associated with the close status
        """
        self.logger.info(f"WebSocket connection closed: {close_status_code} {close_msg}")
        self._ws_connected = False

    def _on_ws_error(self, _ws, error):
        """
        Callback invoked when a WebSocket error occurs.

        Args:
            _ws(WebSocketApp): The WebSocket instance that encountered an error
            error(Exception): The error that occurred
        """
        self.logger.error(f"WebSocket error: {error}")

    def _ws_error_response(self, message_id, data):
        """
        Send an error response back to the server via the WebSocket connection.

        This method constructs and sends a standardized error response message.

        Args:
            message_id(str): The ID of the message being responded to
            data(str): The error message or details to include in the response

        Returns:
            None

        Raises:
            Exception: If sending the error response fails
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
