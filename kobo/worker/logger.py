import threading
import time
import os
import queue
from io import BytesIO

import kobo.tback


__all__ = (
    "LoggingThread",
    "LoggingIO",
)


class LoggingThread(threading.Thread):
    """Send stdout data to hub in a background thread."""

    def __init__(self, hub, task_id, *args, **kwargs):
        self._logger = kwargs.pop('logger', None)
        threading.Thread.__init__(self, *args, **kwargs)
        self._hub = hub
        self._task_id = task_id
        self._buffer_size = kwargs.pop('buffer_size', 256)
        self._queue = queue.Queue(maxsize=self._buffer_size)
        self._event = threading.Event()
        self._in_logger_call = False
        self._running = True
        self._send_time = 0
        self._send_data = b""
        self._timeout = int(os.environ.get("KOBO_LOGGING_THREAD_TIMEOUT", 600))

    def read_queue(self):
        out = self._queue.get_nowait()

        # We do not know whether we're being sent bytes or text.
        # The hub API always wants bytes.
        # Ensure we safely convert everything to bytes as we go.
        if isinstance(out, str):
            out = out.encode('utf-8', errors='replace')

        return out

    def run(self):
        """Send queue content to hub."""
        while self._running or not self._queue.empty() or self._send_data:
            if self._queue.empty():
                self._event.wait(5)

            self._event.clear()
            for _ in range(self._buffer_size):
                try:
                    self._send_data += self.read_queue()
                except queue.Empty:
                    break

            if not self._send_data:
                continue

            now = int(time.time())
            if self._running and len(self._send_data) < 1200 and now - self._send_time < 5:
                continue

            try:
                self._hub.upload_task_log(BytesIO(self._send_data), self._task_id, "stdout.log", append=True)
                self._send_time = now
                self._send_data = b""
            except Exception:
                # Any exception other than an XML-RPC fault may be fatal. It is
                # possible that we've encountered a retryable error, such as a
                # temporary network disruption between worker and hub. Attempt
                # to retry for a bit.
                if now - self._send_time <= self._timeout:
                    continue

                # If the timemout has been exceeded, we can assume we've
                # encountered a non-temporary, fatal exception.
                #
                # Since upload_task_log is apparently not working, we can't get
                # this into the task logs, but it should at least be possible
                # for this to get into the worker's local log file.
                if self._logger:
                    msg = "\n".join([
                        "Fatal error in LoggingThread",
                        kobo.tback.Traceback().get_traceback(),
                    ])
                    self._logger.log_critical(msg)
                raise

    def write(self, data):
        """Add data to the queue and set the event for sending queue content."""
        # Discard the data if the thread is not running to prevent deadlock
        # when the queue is full.
        if not self.is_alive():
            return

        if threading.get_ident() != self.ident:
            self._queue.put(data)
            self._event.set()

        # If self._hub.upload_task_log() called self._queue.put(), it would
        # cause deadlock because self._queue uses locks that are not reentrant
        # and queue may already be full.
        #
        # Log only data with printable characters.
        elif self._logger and data.strip():
            # Prevent infinite recursion if this thread is also used for the
            # logger output.
            if self._in_logger_call:
                return

            self._in_logger_call = True
            self._logger.log_error("Error in LoggingThread: %r", data)
            self._in_logger_call = False

    def stop(self):
        """Send remaining data to hub and finish."""
        self._running = False
        self._event.set()
        self.join()


class LoggingIO():
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
