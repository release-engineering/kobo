# -*- coding: utf-8 -*-

import tempfile
import signal

import pytest
import six
import unittest

from mock import Mock, patch, call

from kobo.exceptions import ShutdownException
from kobo.worker import main


class DummyTaskManager(object):

    def __init__(self, conf, logger):
        def get_next_task_mock():
            self.run_count += 1

            if self.run_count >= self.max_runs:
                raise ShutdownException()

            if self.fail:
                raise Exception('This task always fails.')

        self.run_count = 0
        self.max_runs = conf.get('max_runs', 1)
        self.fail = conf.get('fail', False)
        self._logger = logger
        self.hub = Mock(spec=['_login'], _login=Mock(return_value=None))
        self.sleep = Mock(return_value=None)
        self.shutdown = Mock(return_value=None)
        self.get_next_task = Mock(side_effect=get_next_task_mock)
        self.update_tasks = Mock(return_value=None)
        self.update_worker_info = Mock(return_value=None)
        self.log_debug = Mock(return_value=None)
        self.log_error = Mock(return_value=None)
        self.log_info = Mock(return_value=None)


class TestMainLoop(unittest.TestCase):

    def setUp(self):
        self.task_manager = None

    def tearDown(self):
        self.task_manager = None

    def create_task_manager(self):
        def wrap(conf, logger):
            self.task_manager = DummyTaskManager(conf=conf, logger=logger)
            return self.task_manager
        return wrap

    def test_daemon_shutdown(self):
        with self.assertRaises(ShutdownException):
            main.daemon_shutdown()

    def test_main_loop_task_manager_exception(self):
        with patch('kobo.worker.main.TaskManager', Mock(side_effect=ValueError)) as mock_tm:
            with patch.object(main.signal, 'signal') as signal_mock:
                with patch.object(main.sys, 'exit') as exit_mock:
                    with self.assertRaises(ValueError):
                        main.main_loop({}, foreground=False)

                        mock_tm.assert_called_once()
                        signal_mock.assert_called_once_with(signal.SIGTERM, main.daemon_shutdown)
                        exit_mock.assert_not_called()

    def test_main_loop_task_exception(self):
        max_runs = 10

        with patch('kobo.worker.main.TaskManager', self.create_task_manager()):
            with patch.object(main.signal, 'signal') as signal_mock:
                with patch.object(main.sys, 'exit') as exit_mock:
                    main.main_loop({
                        'max_runs': max_runs,
                        'fail': True,
                    }, foreground=False)

                    signal_mock.assert_has_calls([
                        call(signal.SIGTERM, main.daemon_shutdown),
                        call(signal.SIGINT, signal.SIG_IGN),
                        call(signal.SIGTERM, signal.SIG_IGN),
                    ], any_order=False)

                    exit_mock.assert_not_called()

            self.assertEqual(self.task_manager.hub._login.call_count, max_runs)
            self.assertEqual(self.task_manager.update_worker_info.call_count, max_runs)
            self.assertEqual(self.task_manager.update_tasks.call_count, max_runs)
            self.assertEqual(self.task_manager.get_next_task.call_count, max_runs)
            self.assertEqual(self.task_manager.sleep.call_count, max_runs - 1)
            self.assertEqual(self.task_manager.log_error.call_count, max_runs - 1)
            self.assertEqual(self.task_manager.shutdown.call_count, 1)

    def test_main_loop(self):
        max_runs = 10

        with patch('kobo.worker.main.TaskManager', self.create_task_manager()):
            with patch.object(main.signal, 'signal') as signal_mock:
                with patch.object(main.sys, 'exit') as exit_mock:
                    main.main_loop({
                        'max_runs': max_runs,
                    }, foreground=False)

                    signal_mock.assert_has_calls([
                        call(signal.SIGTERM, main.daemon_shutdown),
                        call(signal.SIGINT, signal.SIG_IGN),
                        call(signal.SIGTERM, signal.SIG_IGN),
                    ], any_order=False)

                    exit_mock.assert_not_called()

            self.assertEqual(self.task_manager.hub._login.call_count, max_runs)
            self.assertEqual(self.task_manager.update_worker_info.call_count, max_runs)
            self.assertEqual(self.task_manager.update_tasks.call_count, max_runs)
            self.assertEqual(self.task_manager.get_next_task.call_count, max_runs)
            self.assertEqual(self.task_manager.sleep.call_count, max_runs - 1)
            self.assertEqual(self.task_manager.shutdown.call_count, 1)

    def test_main_loop_in_foreground(self):
        max_runs = 10

        with patch('kobo.worker.main.TaskManager', self.create_task_manager()):
            with patch.object(main.signal, 'signal') as signal_mock:
                with patch.object(main.sys, 'exit') as exit_mock:
                    main.main_loop({
                        'max_runs': max_runs,
                    }, foreground=False)

                    signal_mock.assert_has_calls([
                        call(signal.SIGTERM, main.daemon_shutdown),
                        call(signal.SIGINT, signal.SIG_IGN),
                        call(signal.SIGTERM, signal.SIG_IGN),
                    ], any_order=False)

                    exit_mock.assert_not_called()

            self.assertEqual(self.task_manager.hub._login.call_count, max_runs)
            self.assertEqual(self.task_manager.update_worker_info.call_count, max_runs)
            self.assertEqual(self.task_manager.update_tasks.call_count, max_runs)
            self.assertEqual(self.task_manager.get_next_task.call_count, max_runs)
            self.assertEqual(self.task_manager.sleep.call_count, max_runs - 1)
            self.assertEqual(self.task_manager.shutdown.call_count, 1)

    def test_main_loop_with_file_logger(self):
        max_runs = 1

        with patch('kobo.worker.main.TaskManager', self.create_task_manager()):
            with patch.object(main.kobo, 'log') as log_mock:
                with patch.object(main.signal, 'signal') as signal_mock:
                    with patch.object(main.sys, 'exit') as exit_mock:
                        main.main_loop({
                            'max_runs': max_runs,
                            'LOG_FILE': '/tmp/log.txt',
                        }, foreground=False)

                        log_mock.add_rotating_file_logger.assert_called_once_with(
                            self.task_manager._logger,
                            '/tmp/log.txt',
                            log_level=10,
                        )

                        log_mock.add_stderr_logger.assert_not_called()

                        signal_mock.assert_has_calls([
                            call(signal.SIGTERM, main.daemon_shutdown),
                            call(signal.SIGINT, signal.SIG_IGN),
                            call(signal.SIGTERM, signal.SIG_IGN),
                        ], any_order=False)

                        exit_mock.assert_not_called()

            self.assertEqual(self.task_manager.hub._login.call_count, max_runs)
            self.assertEqual(self.task_manager.update_worker_info.call_count, max_runs)
            self.assertEqual(self.task_manager.update_tasks.call_count, max_runs)
            self.assertEqual(self.task_manager.get_next_task.call_count, max_runs)
            self.assertEqual(self.task_manager.sleep.call_count, max_runs - 1)
            self.assertEqual(self.task_manager.shutdown.call_count, 1)

    def test_main_loop_foreground_with_file_logger(self):
        max_runs = 1

        with patch('kobo.worker.main.TaskManager', self.create_task_manager()):
            with patch.object(main.kobo, 'log') as log_mock:
                with patch.object(main.signal, 'signal') as signal_mock:
                    with patch.object(main.sys, 'exit') as exit_mock:
                        main.main_loop({
                            'max_runs': max_runs,
                            'LOG_FILE': '/tmp/log.txt',
                        }, foreground=True)

                        log_mock.add_rotating_file_logger.assert_called_once_with(
                            self.task_manager._logger,
                            '/tmp/log.txt',
                            log_level=10,
                        )

                        log_mock.add_stderr_logger.assert_called_once_with(self.task_manager._logger)

                        signal_mock.assert_has_calls([
                            call(signal.SIGTERM, main.daemon_shutdown),
                            call(signal.SIGINT, signal.SIG_IGN),
                            call(signal.SIGTERM, signal.SIG_IGN),
                        ], any_order=False)

                        exit_mock.assert_not_called()

            self.assertEqual(self.task_manager.hub._login.call_count, max_runs)
            self.assertEqual(self.task_manager.update_worker_info.call_count, max_runs)
            self.assertEqual(self.task_manager.update_tasks.call_count, max_runs)
            self.assertEqual(self.task_manager.get_next_task.call_count, max_runs)
            self.assertEqual(self.task_manager.sleep.call_count, max_runs - 1)
            self.assertEqual(self.task_manager.shutdown.call_count, 1)


class TestMain(unittest.TestCase):

    def test_main_with_no_commands(self):
        conf = {'PID_FILE': '/tmp/pid'}

        with patch.object(main.kobo.process, 'daemonize') as daemonize_mock:
            with patch.object(main.os, 'kill') as kill_mock:
                with patch.object(main.sys, 'exit') as exit_mock:
                    main.main(conf, argv=[])

                    exit_mock.assert_not_called()
                    kill_mock.assert_not_called()
                    daemonize_mock.assert_called_once_with(
                        main.main_loop,
                        conf=conf,
                        daemon_pid_file='/tmp/pid',
                        foreground=False,
                    )

    def test_main_foreground_command(self):
        conf = {'PID_FILE': '/tmp/pid'}

        with patch('kobo.worker.main.main_loop') as main_loop_mock:
            with patch.object(main.kobo.process, 'daemonize') as daemonize_mock:
                with patch.object(main.os, 'kill') as kill_mock:
                    with patch.object(main.sys, 'exit') as exit_mock:
                        main.main(conf, argv=['--foreground'])

                        exit_mock.assert_not_called()
                        kill_mock.assert_not_called()
                        daemonize_mock.assert_not_called()
                        main_loop_mock.assert_called_once_with(conf, foreground=True)

    def test_main_pid_file_command(self):
        with patch.object(main.kobo.process, 'daemonize') as daemonize_mock:
            with patch.object(main.os, 'kill') as kill_mock:
                with patch.object(main.sys, 'exit') as exit_mock:
                    main.main({}, argv=['--pid-file', '/tmp/pid'])

                    exit_mock.assert_not_called()
                    kill_mock.assert_not_called()
                    daemonize_mock.assert_called_once_with(
                        main.main_loop,
                        conf={},
                        daemon_pid_file='/tmp/pid',
                        foreground=False,
                    )

    def test_main_kill_command(self):
        with tempfile.NamedTemporaryFile('r+') as temp_file:
            temp_file.write('999')
            temp_file.flush()

            with patch.object(main.kobo.process, 'daemonize') as daemonize_mock:
                with patch.object(main.os, 'kill') as kill_mock:
                    with patch.object(main.sys, 'exit') as exit_mock:
                        main.main({}, argv=['--pid-file', temp_file.name, '--kill'])

                        exit_mock.assert_called_once_with(0)
                        kill_mock.assert_called_once_with(999, 15)
                        # since exit is mocked and don't exits the program daemonize will be called.
                        daemonize_mock.assert_called_once()
