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

from typing import List

from fyn_runner.server.message_queue import MessageQueue


class ServerProxy:

    def __init__(self):
        self.queue: List[MessageQueue] = None
        pass

    def push_message(self, message):
        pass

    def register_observer(self, name, call_back):
        pass

    def unregister_observer(self, name):
        pass

    def notify_observer(self, message):
        pass

    def _raise_connection():
        pass

    def _fetch_api():
        pass

    def _send_message(message):
        pass

    def _listen_api():
        pass
