# -*- coding: utf-8 -*-

import time
import logging

import unittest

from six import BytesIO, StringIO

from mock import Mock

from kobo.worker.logger import LoggingThread, LoggingIO
from kobo.log import LoggingBase
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

    def test_logs_on_fatal_error(self):
        # Set up a logger whose output we'll be able to inspect.
        logs = StringIO()
        logger = logging.getLogger('TestLoggingThread')
        logger.addHandler(logging.StreamHandler(logs))
        kobo_logger = LoggingBase(logger)

        # Set up hub to raise some exception other than an XML-RPC fault.
        mock_hub = Mock()
        mock_hub.upload_task_log.side_effect = RuntimeError("Simulated error")

        thread = LoggingThread(mock_hub, 9999, logger=kobo_logger)
        thread.daemon = True
        thread.start()

        thread.write('This is a log message!')

        # Since we set up a fatal error, we expect the thread to die soon
        # despite not calling stop().
        thread.join(10.0)
        self.assertFalse(thread.is_alive())

        # Before dying, it should have written something useful to the logs.
        captured = logs.getvalue()
        assert 'Fatal error in LoggingThread' in captured
        assert 'RuntimeError: Simulated error' in captured

    def test_mixed_writes(self):
        uploaded = []

        # Used as a side-effect to keep whatever's uploaded
        def mock_upload(io, *args, **kwargs):
            uploaded.append(io.read())

        mock_hub = Mock()
        mock_hub.upload_task_log.side_effect = mock_upload

        thread = LoggingThread(mock_hub, 9999)
        thread.daemon = True

        thread.start()

        # Mixing text, ascii-safe bytes, ascii-unsafe bytes here
        # as is possible with sys.stdout at least on py2.
        thread.write('Some text!')
        thread.write(b'Some bytes!')
        thread.write(u'Some 文!')
        thread.write(b'Some \xe2 wacky bytes!')

        # It should be able to stop normally
        thread.stop()
        self.assertFalse(thread.is_alive())

        # It should have uploaded exactly the expected bytes.
        assert b''.join(uploaded) == (
            b'Some text!Some bytes!'
            b'Some \xe6\x96\x87!Some \xe2 wacky bytes!'
        )


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
