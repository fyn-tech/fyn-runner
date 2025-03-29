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
import threading
import time
from concurrent.futures import Future
from urllib.parse import urljoin

import requests

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
        self.report_interval = configuration.report_interval

        # message handing
        self._running: bool = True
        self._queue: MessageQueue = MessageQueue()
        self._new_send_message: threading.Event = threading.Event()
        self._send_thread: threading.Thread = threading.Thread(target=self._send_handler)
        self._send_thread.daemon = True
        self._response_futures = {}
        self._response_lock = threading.RLock()

        # initialisation procedure
        self._fetch_api()
        self._raise_connection()  # don't catch here, allow propagation at initialisation.
        atexit.register(self._report_status, 'offline')
        self._send_thread.start()

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
        with self._response_lock:
            self._response_futures[message.msg_id] = new_future

        try:
            self.push_message(message)
            return new_future
        except Exception:  # logger would have reported error, just clean future.
            with self._response_lock:
                self._response_futures.pop(message.msg_id)
            raise  # ensures caller knows

    def register_observer(self, name, call_back):
        """todo"""
        pass

    def unregister_observer(self, name):
        """todo"""
        pass

    def notify_observer(self, message):
        """todo"""
        pass

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
                f"{self.api_url}/runner_manager/report_status/",
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
        """todo"""
        self.logger.info("fetching backend API.")

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
        while self._running:
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

        response.raise_for_status()
        result = response.json()
        self.logger.info(f"HTTP request successful for message ({message.msg_id}): "
                         f"{message.method.name} {message.api_path}")

        self._handle_response_future(message, response)

        return result

    def _handle_response_future(self, message, response):

        with self._response_lock:
            future = self._response_futures.pop(message.msg_id, None)
            if future:
                self.logger.debug(f"Updating future for message {message.msg_id}")
                try:
                    future.set_result(response.json())
                except Exception as e:
                    future.set_exception(e)

    def _listen_api(self):
        """todo"""
        pass
