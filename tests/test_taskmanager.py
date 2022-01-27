# -*- coding: utf-8 -*-

import errno
import os
import signal
import logging

import django
import pytest
import six

from datetime import datetime, timedelta

from django.contrib.auth.models import User

from mock import Mock, PropertyMock, patch

from kobo.client.constants import TASK_STATES
from kobo.exceptions import ShutdownException
from kobo.hub.models import Arch, Channel, Task, Worker
from kobo.worker import TaskBase
from kobo.worker.task import FailTaskException
from kobo.worker.taskmanager import TaskManager, TaskContainer
from six.moves.xmlrpc_client import ProtocolError

from .rpc import HubProxyMock, RpcServiceMock
from .utils import DjangoRunner

runner = DjangoRunner()
setup_module = runner.start
teardown_module = runner.stop


class DummyTask(TaskBase):

    def run(self):
        self.result = True

    @classmethod
    def cleanup(cls, hub, conf, task_info):
        pass

    @classmethod
    def notification(cls, hub, conf, task_info):
        pass


class DummyForegroundTask(DummyTask):
    enabled = True
    arches = ['testarch']
    channels = ['testchannel']
    exclusive = False
    foreground = True
    priority = 10
    weight = 1.0


class DummyForkTask(DummyTask):
    enabled = True
    arches = ['testarch']
    channels = ['testchannel']
    exclusive = False
    foreground = False
    priority = 10
    weight = 1.0


class DummyHeavyTask(DummyTask):
    enabled = True
    arches = ['testarch']
    channels = ['testchannel']
    exclusive = False
    foreground = False
    priority = 10
    weight = 100.0


class DummyFailTask(DummyTask):
    enabled = True
    arches = ['testarch']
    channels = ['testchannel']
    exclusive = False
    foreground = True
    priority = 10
    weight = 1.0

    def run(self):
        raise FailTaskException()


class DummyExceptionTask(DummyTask):
    enabled = True
    arches = ['testarch']
    channels = ['testchannel']
    exclusive = False
    foreground = True
    priority = 10
    weight = 1.0

    def run(self):
        raise Exception()


class TestTaskManager(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        super(TestTaskManager, self).setUp()

        TaskContainer.register_plugin(DummyForegroundTask)
        TaskContainer.register_plugin(DummyForkTask)
        TaskContainer.register_plugin(DummyHeavyTask)
        TaskContainer.register_plugin(DummyFailTask)
        TaskContainer.register_plugin(DummyExceptionTask)

        user = User.objects.create(username='testuser')
        arch = Arch.objects.create(name='testarch')
        channel = Channel.objects.create(name='testchannel')

        w = Worker.objects.create(
            worker_key='mock-worker',
            name='mock-worker',
        )

        w.arches.add(arch)
        w.channels.add(channel)
        w.save()

        self._arch = arch
        self._channel = channel
        self._user = user
        self._worker = RpcServiceMock(w)

    @pytest.mark.xfail(reason='Check issue #68 for more info (https://git.io/fxSZ2).')
    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_update_worker_info(self):
        tm = TaskManager(conf={'worker': self._worker})
        self.assertTrue(tm.worker_info['enabled'])
        self.assertTrue(tm.worker_info['ready'])

        tm.worker_info['enabled'] = False
        tm.worker_info['ready'] = False
        tm.update_worker_info()
        self.assertFalse(tm.worker_info['enabled'])
        self.assertFalse(tm.worker_info['ready'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_update_worker_info_catch_protocol_error(self):
        tm = TaskManager(conf={'worker': self._worker})

        tm.hub.worker.update_worker = Mock(side_effect=ProtocolError(None, None, None, None))
        tm.update_worker_info()

        with self.assertRaises(ValueError):
            tm.hub.worker.update_worker = Mock(side_effect=ValueError)
            tm.update_worker_info()

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_wakeup_task_if_alert_is_set(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        tm = TaskManager(conf={'worker': self._worker})

        task_info = t.export(False)
        task_info['alert'] = True

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()
            tm.wakeup_task(task_info)
            os_mock.kill.assert_called_once_with(9999, signal.SIGUSR2)

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_wakeup_task_if_alert_is_not_set(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()
            tm.wakeup_task(task_info)
            os_mock.kill.assert_not_called()

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_wakeup_task_catch_os_error(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        tm = TaskManager(conf={'worker': self._worker})

        task_info = t.export(False)
        task_info['alert'] = True

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)

        with patch('kobo.worker.taskmanager.os', kill=Mock(side_effect=OSError)) as os_mock:
            tm.wakeup_task(task_info)
            os_mock.kill.assert_called_once_with(9999, signal.SIGUSR2)

        with self.assertRaises(ValueError):
            with patch('kobo.worker.taskmanager.os', kill=Mock(side_effect=ValueError)) as os_mock:
                tm.wakeup_task(task_info)
                os_mock.kill.assert_called_once_with(9999, signal.SIGUSR2)

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_update_tasks_timeout_task_if_running_for_to_long(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            timeout=0,
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

        self.assertTrue(t.id in tm.pid_dict)
        tm.update_tasks()
        self.assertFalse(t.id in tm.pid_dict)

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['TIMEOUT'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_update_tasks_finish_task_if_canceled(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

        self._worker.cancel_task(t.id)

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CANCELED'])

        self.assertTrue(t.id in tm.pid_dict)
        tm.update_tasks()
        self.assertFalse(t.id in tm.pid_dict)

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CANCELED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_update_tasks_interrupt_taks_if_not_on_pid_list(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['OPEN'],
        )

        self.assertEqual(t.state, TASK_STATES['OPEN'])

        tm = TaskManager(conf={'worker': self._worker})

        self.assertFalse(t.id in tm.pid_dict)
        tm.update_tasks()
        self.assertFalse(t.id in tm.pid_dict)

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['INTERRUPTED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_update_tasks_cleanup_finished_tasks(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

        tm.run_task(task_info)

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CLOSED'])

        with patch('kobo.worker.taskmanager.os', waitpid=Mock(return_value=(123, 0))) as os_mock:
            self.assertTrue(t.id in tm.pid_dict)
            tm.update_tasks()
            self.assertFalse(t.id in tm.pid_dict)
            os_mock.waitpid.assert_called_once()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CLOSED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_update_tasks_without_tasks(self):
        tm = TaskManager(conf={'worker': self._worker})
        tm.update_tasks()
        self.assertEqual(len(tm.pid_dict.keys()), 0)
        self.assertEqual(len(tm.task_dict.keys()), 0)

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_get_next_task_runs_free_task(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        tm.get_next_task()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CLOSED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_get_next_task_dont_run_tasks_if_disabled(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        tm.worker_info['enabled'] = False

        tm.get_next_task()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FREE'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_get_next_task_dont_run_tasks_if_not_ready(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        tm.worker_info['ready'] = False

        tm.get_next_task()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FREE'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_get_next_task_raise_shutdown_exception_if_locked_and_no_tasks_running(self):
        tm = TaskManager(conf={'worker': self._worker})
        tm.lock()

        # ensure no tasks are running
        self.assertEqual(len(self._worker.worker.running_tasks()), 0)

        with self.assertRaises(ShutdownException):
            tm.get_next_task()

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_get_next_task_runs_assigened_awaited_task_if_locked(self):
        t1 = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['OPEN'],
        )

        t2 = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['ASSIGNED'],
            awaited=True,
            parent=t1,
        )

        t3 = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            waiting=True,
            parent=t2,
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t1.state, TASK_STATES['OPEN'])
        self.assertEqual(t2.state, TASK_STATES['ASSIGNED'])
        self.assertEqual(t3.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        tm.lock()
        tm.get_next_task()

        # reload task info
        t1 = Task.objects.get(id=t1.id)
        self.assertEqual(t1.state, TASK_STATES['OPEN'])

        t2 = Task.objects.get(id=t2.id)
        self.assertEqual(t2.state, TASK_STATES['CLOSED'])

        t3 = Task.objects.get(id=t3.id)
        self.assertEqual(t3.state, TASK_STATES['FREE'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_take_task_open_task_if_free(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_take_task_open_task_if_assigned(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['ASSIGNED'],
        )

        self.assertEqual(t.state, TASK_STATES['ASSIGNED'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_take_task_runs_task_if_foreground(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            os_mock.devnull = os.devnull

            tm.take_task(task_info)
            os_mock.fork.assert_not_called()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CLOSED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_take_task_catch_errors_if_cant_open_task(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        tm.hub.worker.open_task = Mock(side_effect=ValueError)

        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_not_called()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FREE'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_take_task_if_worker_not_ready(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        tm.worker_info['ready'] = False

        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_not_called()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FREE'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_take_task_if_wrong_arch(self):
        arch = Arch.objects.create(name='arch_x86', pretty_name='Arch x86')

        t = Task.objects.create(
            worker=self._worker.worker,
            arch=arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_not_called()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FREE'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_take_task_if_wrong_channel(self):
        channel = Channel.objects.create(name='channel_x86')

        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_not_called()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FREE'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_take_task_set_load_and_ready(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyHeavyTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        self.assertEqual(tm.worker_info['current_load'], 100)
        self.assertFalse(tm.worker_info['ready'])

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_fork_task(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.fork_task(task_info)
            os_mock.fork.assert_called_once()

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_fork_task_runs_task_if_cant_fork(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['OPEN'],
        )

        self.assertEqual(t.state, TASK_STATES['OPEN'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=0)) as os_mock:
            os_mock.devnull = os.devnull

            with patch('kobo.worker.taskmanager.signal') as signal_mock:
                tm.fork_task(task_info)
                os_mock.fork.assert_called_once()
                os_mock.setpgrp.assert_called_once()
                os_mock._exit.assert_called_once()
                signal_mock.signal.assert_called()

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CLOSED'])

    def test_fork_task_logs_exceptions(self):
        """Exceptions from the child within fork_task are logged."""

        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['OPEN'],
        )

        logger = Mock()

        with patch('kobo.worker.taskmanager.HubProxy') as hub_mock:
            # Arrange for close_task call to fail (at end of task)
            hub_mock.return_value.worker.close_task.side_effect = RuntimeError("simulated error")

            tm = TaskManager(conf={'worker': self._worker}, logger=logger)
            task_info = t.export(False)

            with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=0)) as os_mock:
                os_mock.devnull = os.devnull
                tm.fork_task(task_info)

        # It should have logged something about the failure to close the task.
        logger.log.assert_called_with(logging.CRITICAL, 'Error running forked task', exc_info=1)

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_run_task_runs_foreground_task(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForegroundTask',
            state=TASK_STATES['OPEN'],
        )

        self.assertEqual(t.state, TASK_STATES['OPEN'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)
 
        tm.run_task(task_info)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CLOSED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_run_task_runs_fork_task(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['OPEN'],
        )

        self.assertEqual(t.state, TASK_STATES['OPEN'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        tm.run_task(task_info)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CLOSED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_run_task_mark_task_as_failed(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyFailTask',
            state=TASK_STATES['OPEN'],
        )

        self.assertEqual(t.state, TASK_STATES['OPEN'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        tm.run_task(task_info)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FAILED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_run_task_mark_task_as_failed_if_generic_exception(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyExceptionTask',
            state=TASK_STATES['OPEN'],
        )

        self.assertEqual(t.state, TASK_STATES['OPEN'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        tm.run_task(task_info)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FAILED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_finish_task(self):
        tm = TaskManager(conf={'worker': self._worker})

        mock = Mock()
        # inject mock plugin
        tm.task_container.plugins['Mock'] = mock

        tm.finish_task({
            'method': 'Mock'
        })

        mock.cleanup.assert_called_once()
        mock.notification.assert_called_once()

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_is_finished_task(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        with patch('kobo.worker.taskmanager.os', waitpid=Mock(return_value=(123, 0))) as os_mock:
            self.assertTrue(tm.is_finished_task(t.id))
            os_mock.waitpid.assert_called_once()

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_is_finished_task_invalid_child_pid(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        with patch('kobo.worker.taskmanager.os', waitpid=Mock(return_value=(0, 0))) as os_mock:
            self.assertFalse(tm.is_finished_task(t.id))
            os_mock.waitpid.assert_called_once()

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_is_finished_task_catch_os_error(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        err = OSError()
        err.errno = errno.ECHILD

        with patch('kobo.worker.taskmanager.os', waitpid=Mock(side_effect=err)) as os_mock:
            self.assertFalse(tm.is_finished_task(t.id))
            os_mock.waitpid.assert_called_once()

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_shutdown_with_running_tasks(self):
        t = Task.objects.create(
            worker=self._worker.worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyForkTask',
            state=TASK_STATES['FREE'],
        )

        self.assertEqual(t.state, TASK_STATES['FREE'])

        tm = TaskManager(conf={'worker': self._worker})
        task_info = t.export(False)

        with patch('kobo.worker.taskmanager.os', fork=Mock(return_value=9999)) as os_mock:
            tm.take_task(task_info)
            os_mock.fork.assert_called_once()

        tm.update_tasks()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

        tm.shutdown()

        # reload task info
        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['INTERRUPTED'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_shutdown_without_running_tasks(self):
        tm = TaskManager(conf={'worker': self._worker})
        tm.update_tasks()
        tm.shutdown()

        self.assertTrue(tm.worker_info['enabled'])
        self.assertTrue(tm.worker_info['ready'])

    @patch('kobo.worker.taskmanager.HubProxy', HubProxyMock)
    def test_lock(self):
        tm = TaskManager(conf={'worker': self._worker})
        self.assertFalse(tm.locked)
        tm.lock()
        self.assertTrue(tm.locked)
