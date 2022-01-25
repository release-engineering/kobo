# -*- coding: utf-8 -*-

import unittest

from mock import Mock, PropertyMock, patch, call

from kobo.client.constants import TASK_STATES
from kobo.worker.task import TaskBase, FailTaskException


class ForegroundTaskBase(TaskBase):
    foreground = True


class TestTaskBase(unittest.TestCase):

    def test_taskbase(self):
        task_info = {'id': 100}
        hub = Mock(worker=Mock(get_task=Mock(return_value=task_info)))
        conf = {'key': 'value'}
        task_id = 100
        args = ('value', 100)

        t = TaskBase(hub, conf, task_id, args)
        self.assertTrue(t.enabled)
        self.assertEqual(t.hub, hub)
        self.assertEqual(t.conf, conf)
        self.assertEqual(t.task_id, task_id)
        self.assertEqual(t.task_info, task_info)

        hub.worker.get_task.assert_called_once_with(task_id)

    def test_task_manager_background_task(self):
        task_info = {'id': 100}
        hub = Mock(worker=Mock(get_task=Mock(return_value=task_info)))
        conf = {'key': 'value'}
        task_id = 100
        args = ('value', 100)

        t = TaskBase(hub, conf, task_id, args)

        tm = t.task_manager
        self.assertIsNone(tm)

        with self.assertRaises(ValueError):
            t.task_manager = Mock()

        tm = t.task_manager
        self.assertIsNone(tm)

    def test_task_manager_foreground_task(self):
        task_info = {'id': 100}
        hub = Mock(worker=Mock(get_task=Mock(return_value=task_info)))
        conf = {'key': 'value'}
        task_id = 100
        args = ('value', 100)

        # task_manager functions check `__class__`
        # and it's impossible to safely mock it.
        t = ForegroundTaskBase(hub, conf, task_id, args)

        tm = t.task_manager
        self.assertIsNone(tm)

        t.task_manager = Mock()

        tm = t.task_manager
        self.assertIsNotNone(tm)

    def test_args(self):
        task_info = {'id': 100}
        hub = Mock(worker=Mock(get_task=Mock(return_value=task_info)))
        conf = {'key': 'value'}
        task_id = 100
        args = []

        t = TaskBase(hub, conf, task_id, args)
        self.assertEqual(len(t._args), 0)

        # access directly
        t._args.append(100)
        self.assertEqual(len(t._args), 1)

        # copy to prevent modification
        t.args.append(200)
        self.assertEqual(len(t._args), 1)

    def test_subtask_list(self):
        task_info = {'id': 100}
        hub = Mock(worker=Mock(get_task=Mock(return_value=task_info)))
        conf = {'key': 'value'}
        task_id = 100
        args = []

        t = TaskBase(hub, conf, task_id, args)
        self.assertEqual(len(t._subtask_list), 0)

        # access directly
        t._subtask_list.append({'id': 1})
        self.assertEqual(len(t._subtask_list), 1)

        # copy to prevent modification
        t.subtask_list.append({'id': 2})
        self.assertEqual(len(t._subtask_list), 1)

    def test_run(self):
        task_info = {'id': 100}
        hub = Mock(worker=Mock(get_task=Mock(return_value=task_info)))
        conf = {'key': 'value'}
        task_id = 100
        args = []

        t = TaskBase(hub, conf, task_id, args)

        with self.assertRaises(NotImplementedError):
            t.run()

    def test_fail(self):
        task_info = {'id': 100}
        hub = Mock(worker=Mock(get_task=Mock(return_value=task_info)))
        conf = {'key': 'value'}
        task_id = 100
        args = []

        t = TaskBase(hub, conf, task_id, args)

        with self.assertRaises(FailTaskException):
            t.fail()

    def test_spawn_subtask(self):
        task_info = {'id': 100}
        conf = {'key': 'value'}
        task_id = 100
        subtask_id = 999
        args = []
        hub = Mock(worker=Mock(
            get_task=Mock(return_value=task_info),
            create_subtask=Mock(return_value=subtask_id),
        ))

        t = TaskBase(hub, conf, task_id, args)
        t.foreground = False

        ret_id = t.spawn_subtask('method', [], 'label')
        self.assertEqual(ret_id, subtask_id)

        hub.worker.create_subtask.assert_called_once_with('label', 'method', [], task_id)

    def test_spawn_subtask_foreground_task(self):
        task_info = {'id': 100}
        hub = Mock(worker=Mock(get_task=Mock(return_value=task_info)))
        conf = {'key': 'value'}
        task_id = 100
        args = []

        t = TaskBase(hub, conf, task_id, args)
        t.foreground = True

        with self.assertRaises(RuntimeError):
            t.spawn_subtask('method', [])

        hub.worker.create_subtask.assert_not_called()

    def test_wait_no_subtasks(self):
        task_info = {'id': 100}
        conf = {'key': 'value'}
        task_id = 100
        args = []
        hub = Mock(worker=Mock(
            get_task=Mock(return_value=task_info),
            check_wait=Mock(return_value=([], [])),
        ))

        t = TaskBase(hub, conf, task_id, args)
        t.foreground = False

        finished = t.wait()
        self.assertEqual(len(finished), 0)

        hub.worker.check_wait.assert_called_once_with(task_id)
        hub.worker.get_task.assert_called_once_with(task_id)
        hub.worker.wait.assert_called_once_with(task_id, None)

    def test_wait_with_subtask_list_closed(self):
        def get_task(task_id):
            return {'id': task_id, 'state': TASK_STATES['CLOSED']}

        conf = {'key': 'value'}
        task_id = 100
        subtask_id = 999
        args = []
        hub = Mock(worker=Mock(
            get_task=Mock(side_effect=get_task),
            check_wait=Mock(return_value=([subtask_id], [])),
            create_subtask=Mock(return_value=subtask_id),
        ))

        t = TaskBase(hub, conf, task_id, args)
        t.foreground = False

        t.spawn_subtask('method', [])

        finished = t.wait(subtask_id)
        self.assertEqual(len(finished), 1)

        hub.worker.check_wait.assert_called_once_with(task_id)
        hub.worker.get_task.assert_has_calls([call(task_id), call(subtask_id)], any_order=False)
        hub.worker.wait.assert_called_once_with(task_id, [subtask_id])

    def test_wait_with_subtask_closed(self):
        def get_task(task_id):
            return {'id': task_id, 'state': TASK_STATES['CLOSED']}

        conf = {'key': 'value'}
        task_id = 100
        subtask_id = 999
        args = []
        hub = Mock(worker=Mock(
            get_task=Mock(side_effect=get_task),
            check_wait=Mock(return_value=([subtask_id], [])),
            create_subtask=Mock(return_value=subtask_id),
        ))

        t = TaskBase(hub, conf, task_id, args)
        t.foreground = False

        t.spawn_subtask('method', [])

        finished = t.wait()
        self.assertEqual(len(finished), 1)

        hub.worker.check_wait.assert_called_once_with(task_id)
        hub.worker.get_task.assert_has_calls([call(task_id), call(subtask_id)], any_order=False)
        hub.worker.wait.assert_called_once_with(task_id, None)

    def test_wait_with_subtask_timeout(self):
        def get_task(task_id):
            return {'id': task_id, 'state': TASK_STATES['TIMEOUT']}

        conf = {'key': 'value'}
        task_id = 100
        subtask_id = 999
        args = []
        hub = Mock(worker=Mock(
            get_task=Mock(side_effect=get_task),
            check_wait=Mock(return_value=([subtask_id], [])),
            create_subtask=Mock(return_value=subtask_id),
        ))

        t = TaskBase(hub, conf, task_id, args)
        t.foreground = False

        t.spawn_subtask('method', [])

        with self.assertRaises(FailTaskException):
            t.wait()

        hub.worker.check_wait.assert_called_once_with(task_id)
        hub.worker.get_task.assert_has_calls([call(task_id), call(subtask_id)], any_order=False)
        hub.worker.wait.assert_called_once_with(task_id, None)

    def test_wait_foreground_task(self):
        task_info = {'id': 100}
        hub = Mock(worker=Mock(get_task=Mock(return_value=task_info)))
        conf = {'key': 'value'}
        task_id = 100
        args = []

        t = TaskBase(hub, conf, task_id, args)
        t.foreground = True

        with self.assertRaises(RuntimeError):
            t.wait()

        hub.worker.wait.assert_not_called()
