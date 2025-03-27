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
from typing import List
from threading import RLock

from fyn_runner.server.message import Message


@dataclass
class MessageQueue:

    queue: List[Message] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def is_empty(self):
        with self._lock:
            return len(self.queue) == 0

    def push_message(self, message):
        with self._lock:
            # FIXME - do I need to validate?
            # FIXME need to sort
            self.queue.append(message)

    def get_next_message(self):
        with self._lock:
            if not self.queue:
                return None
            return self.queue.pop(-1)
