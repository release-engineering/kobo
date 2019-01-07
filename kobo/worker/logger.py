# -*- coding: utf-8 -*-

import threading
import time

import six

from six.moves import queue
from six.moves.xmlrpc_client import Fault
from six import BytesIO


__all__ = (
    "LoggingThread",
    "LoggingIO",
)


class LoggingThread(threading.Thread):
    """Send stdout data to hub in a background thread."""

    def __init__(self, hub, task_id, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self._hub = hub
        self._task_id = task_id
        self._queue = queue.Queue()
        self._event = threading.Event()
        self._running = True
        self._send_time = 0
        self._send_data = ""

    def run(self):
        """Send queue content to hub."""
        while self._running or not self._queue.empty() or self._send_data:
            if self._queue.empty():
                self._event.wait(5)

            self._event.clear()
            while True:
                try:
                    self._send_data += self._queue.get_nowait()
                except queue.Empty:
                    break

            if not self._send_data:
                continue

            now = int(time.time())
            if self._running and len(self._send_data) < 1200 and now - self._send_time < 5:
                continue

            if isinstance(self._send_data, six.text_type):
                self._send_data = self._send_data.encode('utf-8')

            try:
                self._hub.upload_task_log(BytesIO(self._send_data), self._task_id, "stdout.log", append=True)
                self._send_time = now
                self._send_data = ""
            except Fault:
                continue

    def write(self, data):
        """Add data to the queue and set the event for sending queue content."""
        self._queue.put(data)
        self._event.set()

    def stop(self):
        """Send remaining data to hub and finish."""
        self._running = False
        self._event.set()
        self.join()


class LoggingIO(object):
    """StringIO wrapper that also writes all data to a logging thread."""

    def __init__(self, io, logging_thread):
        self._io = io
        self._thread = logging_thread

    def __getattr__(self, name):
        return getattr(self._io, name)

    def write(self, data):
        """Write data to the IO stream and to the logging thread."""
        self._io.write(data)
        self._thread.write(data)
