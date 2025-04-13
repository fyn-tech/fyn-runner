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

# pylint: disable=protected-access,pointless-statement,unspecified-encoding, redefined-outer-name

import threading
import time
from unittest.mock import MagicMock

import pytest

from fyn_runner.server.message import Message
from fyn_runner.server.message_queue import MessageQueue


@pytest.fixture
def message_queue():
    """Fixture that creates a fresh MessageQueue for each test."""
    return MessageQueue()


@pytest.fixture
def priority_messages():
    """Fixture that provides mock Message objects with different priorities."""
    low_priority = MagicMock(spec=Message)
    low_priority.priority = 1

    medium_priority = MagicMock(spec=Message)
    medium_priority.priority = 2

    high_priority = MagicMock(spec=Message)
    high_priority.priority = 3

    return {
        'low': low_priority,
        'medium': medium_priority,
        'high': high_priority
    }


def test_initial_queue_is_empty(message_queue):
    """Test that a new queue is empty."""
    assert message_queue.is_empty()


def test_push_message_adds_to_queue(message_queue, priority_messages):
    """Test that pushing a message adds it to the queue."""
    message_queue.push_message(priority_messages['low'])
    assert not message_queue.is_empty()


def test_get_next_message_returns_highest_priority(message_queue, priority_messages):
    """Test that get_next_message returns the highest priority message."""
    # Add messages in random order
    message_queue.push_message(priority_messages['low'])
    message_queue.push_message(priority_messages['high'])
    message_queue.push_message(priority_messages['medium'])

    # Get messages High -> Low
    assert message_queue.get_next_message() == priority_messages['high']
    assert message_queue.get_next_message() == priority_messages['medium']
    assert message_queue.get_next_message() == priority_messages['low']


def test_get_next_message_returns_none_when_empty(message_queue):
    """Test that get_next_message returns None when queue is empty."""
    assert message_queue.get_next_message() is None


def test_is_empty_after_all_messages_popped(message_queue, priority_messages):
    """Test that is_empty returns True after all messages are popped."""
    message_queue.push_message(priority_messages['low'])
    message_queue.get_next_message()
    assert message_queue.is_empty()


def test_thread_safety(message_queue):
    """Test thread safety of the queue with concurrent operations."""
    # Number of messages each thread will add
    message_count = 100

    # Event to synchronize thread start
    start_event = threading.Event()

    # Threads will add this many messages with random priorities
    def producer_task():
        start_event.wait()
        for i in range(message_count):
            msg = MagicMock(spec=Message)
            msg.priority = i % 5  # Use modulo to create some duplicate priorities
            message_queue.push_message(msg)

    # Create and start threads
    threads = []
    thread_count = 5
    for _ in range(thread_count):
        t = threading.Thread(target=producer_task)
        t.start()
        threads.append(t)

    # Populate message queue
    start_event.set()
    for t in threads:
        t.join()

    # Verify the expected number of messages were added
    assert len(message_queue._queue) == message_count * thread_count

    # Check that messages come out in priority order
    prev_priority = message_queue._queue[-1].priority  # first message priority.
    msg_count = 0
    while not message_queue.is_empty():
        msg = message_queue.get_next_message()
        assert msg.priority in (prev_priority, prev_priority - 1)
        prev_priority = msg.priority
        msg_count += 1

    assert msg_count == message_count * thread_count


def test_push_and_pop_in_parallel(message_queue):
    """Test concurrent pushing and popping operations."""
    # Event to synchronize thread start, and some tracking variables
    start_event = threading.Event()
    stop_event = threading.Event()
    consumed_count = [0]
    errors = []

    # Producer function
    def producer():
        try:
            start_event.wait()
            for i in range(100):
                msg = MagicMock(spec=Message)
                msg.priority = i % 5
                message_queue.push_message(msg)
                time.sleep(0.001)  # Small delay to create interleaving
        except Exception as e:
            errors.append(e)

    # Consumer function
    def consumer():
        try:
            start_event.wait()
            while not stop_event.is_set() or not message_queue.is_empty():
                msg = message_queue.get_next_message()
                if msg is not None:
                    consumed_count[0] += 1
                time.sleep(0.002)  # Small delay to create interleaving
        except Exception as e:
            errors.append(e)

    # Create producer and consumer threads, then populate and consume at the same time.
    producer_threads = [threading.Thread(target=producer) for _ in range(3)]
    consumer_threads = [threading.Thread(target=consumer) for _ in range(2)]
    for t in producer_threads + consumer_threads:
        t.start()
    start_event.set()
    for t in producer_threads:
        t.join()
    stop_event.set()
    for t in consumer_threads:
        t.join()

    # Check for errors
    assert len(errors) == 0, f"Thread errors occurred: {errors}"

    # Verify all messages were consumed
    assert consumed_count[0] == 300  # 3 producers x 100 messages
    assert message_queue.is_empty()
