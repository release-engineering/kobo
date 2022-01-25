# -*- coding: utf-8 -*-

import time

import unittest

from six import BytesIO

from mock import Mock

from kobo.worker.logger import LoggingThread, LoggingIO
from .utils import ArgumentIsInstanceOf


class TestLoggingThread(unittest.TestCase):

    def test_upload_task_log_on_stop(self):
        mock_hub = Mock()
        thread = LoggingThread(mock_hub, 9999)
        thread.daemon = True

        thread.start()
        self.assertTrue(thread.is_alive())
        self.assertTrue(thread._running)

        thread.write('This is a log message!')
        mock_hub.upload_task_log.assert_not_called()

        thread.stop()
        self.assertFalse(thread.is_alive())
        self.assertFalse(thread._running)
        mock_hub.upload_task_log.assert_called_once_with(ArgumentIsInstanceOf(BytesIO), 9999, 'stdout.log', append=True)

    def test_upload_task_log_after_some_time(self):
        mock_hub = Mock()
        thread = LoggingThread(mock_hub, 9999)
        thread.daemon = True

        thread.start()

        self.assertTrue(thread.is_alive())
        self.assertTrue(thread._running)

        for i in range(5):
            thread.write('%d - This is a very long message to be written in the log\n' % (i + 1))
            mock_hub.upload_task_log.assert_not_called()

        # let the thread running for a while
        time.sleep(.1)
        mock_hub.upload_task_log.assert_called_once_with(ArgumentIsInstanceOf(BytesIO), 9999, 'stdout.log', append=True)

        thread.stop()
        self.assertFalse(thread.is_alive())
        self.assertFalse(thread._running)


class TestLoggingIO(unittest.TestCase):

    def test_write(self):
        mock_io = Mock()
        mock_logging_thread = Mock()

        stream = LoggingIO(mock_io, mock_logging_thread)
        stream.write('This is a log message!')

        mock_io.write.assert_called_once_with('This is a log message!')
        mock_logging_thread.write.assert_called_once_with('This is a log message!')

    def test_write_multiple_calls(self):
        mock_io = Mock()
        mock_logging_thread = Mock()

        stream = LoggingIO(mock_io, mock_logging_thread)

        for i in range(10):
            stream.write('This is the %d log message!' % (i + 1))

        mock_io.write.assert_any_call('This is the 1 log message!')
        mock_io.write.assert_any_call('This is the 10 log message!')

        mock_logging_thread.write.assert_any_call('This is the 1 log message!')
        mock_logging_thread.write.assert_any_call('This is the 10 log message!')

        self.assertEqual(mock_io.write.call_count, 10)
        self.assertEqual(mock_logging_thread.write.call_count, 10)

    def test_getattr(self):
        mock_io = Mock()
        mock_logging_thread = Mock()

        stream = LoggingIO(mock_io, mock_logging_thread)
        random_variable = stream.random_variable

        self.assertFalse(random_variable is None)
        self.assertIsInstance(random_variable, Mock)
