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
import urllib.parse
from typing import List

import requests

from fyn_runner.server.message_queue import MessageQueue


class ServerProxy:
    """todo"""

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

        # other members
        self._queue: List[MessageQueue] = None

        parsed_url = urllib.parse.urlparse(self.api_url)
        self.domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

        self._fetch_api()
        self._raise_connection()
        atexit.register(self._report_status, 'offline')

    def push_message(self, message):
        """todo"""
        pass

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
            dict: The JSON response from the server containing the result of the status update.

        Raises:
            ConnectionError: If any network-related errors occur during the status update,
                including connection errors, timeouts, or HTTP error responses.
        """

        try:
            endpoint = f"{self.api_url}/runner_manager/report_status/{self.id}"
            self.logger.debug(f"Reporting status '{status}' to {endpoint}")
            response = requests.patch(
                url=endpoint,
                json={
                    "id": str(self.id),
                    "token": str(self.token),
                    "state": str(status)
                },
                headers={
                    "Content-Type": "application/json",
                },
                timeout=request_timeout
            )
            response.raise_for_status()
            result = response.json()
            self.logger.info(f"Status '{status}' reported successfully: {result}")
            return result

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

    def _send_message(self, message):
        """todo"""
        pass

    def _listen_api(self):
        """todo"""
        pass
