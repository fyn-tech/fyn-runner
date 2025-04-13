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

from dataclasses import dataclass, field
from threading import RLock
from typing import List

from fyn_runner.server.message import Message


@dataclass
class MessageQueue:
    """
    A thread-safe priority queue for Message objects.

    Manages message storage and retrieval based on priority. Designed to ensure thread safety
    through locking and processes higher priority messages first. The queue is sorted in ascending
    order, and message retrieved from the back. While the queue is FIFO, this is for no particular
    reason - a result of queue construction.
    """

    _queue: List[Message] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def is_empty(self):
        """Check if the queue contains any messages."""
        with self._lock:
            return len(self._queue) == 0

    def push_message(self, message):
        """
        Add a message to the queue and sort by priority.

        Args:
            message (Message): The message to be added.
        """

        with self._lock:
            self._queue.append(message)
            self._queue.sort(key=lambda x: x.priority)

    def get_next_message(self):
        """
        Retrieve and remove the highest priority message.

        Returns:
            Message: The highest priority message, or None if queue is empty.
        """

        with self._lock:
            if not self._queue:
                return None
            return self._queue.pop(-1)
