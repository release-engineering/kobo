# -*- coding: utf-8 -*-

import base64
import hashlib
import tempfile
import unittest

import django
import pytest
import six

from datetime import datetime, timedelta

from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User

from mock import Mock, PropertyMock, patch

from kobo.client.constants import TASK_STATES, FINISHED_STATES
from kobo.exceptions import ShutdownException
from kobo.hub.models import Arch, Channel, Task, Worker
from kobo.hub.xmlrpc import worker

from .utils import DjangoRunner

runner = DjangoRunner()
setup_module = runner.start
teardown_module = runner.stop


def _make_request(w, is_authenticated=True):
    return PropertyMock(
        worker=w,
        user=Mock(is_authenticated=Mock(return_value=is_authenticated)),
    )


class TestXmlRpcWorker(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        super(TestXmlRpcWorker, self).setUp()

        user = User.objects.create(username='testuser')
        arch = Arch.objects.create(name='testarch')
        channel = Channel.objects.create(name='testchannel')

        w = Worker.objects.create(
            worker_key='testworker',
            name='testworker',
        )

        w.arches.add(arch)
        w.channels.add(channel)
        w.save()

        self._arch = arch
        self._channel = channel
        self._user = user
        self._worker = w

    def test_get_worker_info(self):
        req = _make_request(self._worker)
        wi = worker.get_worker_info(req)

        self.assertFalse(wi is None)
        self.assertEqual(wi['task_count'], 0)
        self.assertEqual(wi['current_load'], 0)
        self.assertEqual(wi['max_load'], 1)
        self.assertTrue(wi['ready'])
        self.assertTrue(wi['enabled'])

    def test_get_worker_id(self):
        req = _make_request(self._worker)
        w_id = worker.get_worker_id(req)

        assert isinstance(w_id, int)

    def test_get_worker_tasks(self):
        for state in TASK_STATES:
            Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=TASK_STATES[state],
            )

        req = _make_request(self._worker)
        tasks = worker.get_worker_tasks(req)

        self.assertEqual(len(tasks), 2)
        self.assertTrue(tasks[0]['id'] < tasks[1]['id'])

        for task in tasks:
            self.assertTrue(task['state'] in [TASK_STATES['ASSIGNED'], TASK_STATES['OPEN']])

    def test_get_worker_tasks_check_wait(self):
        t_parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
            waiting=True,
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['CLOSED'],
            parent=t_parent,
            awaited=True,
        )

        req = _make_request(self._worker)
        tasks = worker.get_worker_tasks(req)

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['id'], t_parent.id)
        self.assertTrue(tasks[0]['alert'])

    def test_get_worker_tasks_returns_empty_list_if_no_tasks(self):
        req = _make_request(self._worker)
        tasks = worker.get_worker_tasks(req)

        self.assertEqual(tasks, [])

    def test_get_task(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        req = _make_request(self._worker)
        task_info = worker.get_task(req, t.id)

        self.assertEqual(task_info['id'], t.id)
        self.assertEqual(task_info['worker'], self._worker.id)
        self.assertEqual(task_info['state'], t.state)

    def test_get_task_cant_get_task_from_other_worker(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(Task.DoesNotExist):
            worker.get_task(req, t.id)

    def test_get_task_no_verify(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        req = _make_request(self._worker)
        task_info = worker.get_task_no_verify(req, t.id)

        self.assertEqual(task_info['id'], t.id)
        self.assertEqual(task_info['worker'], self._worker.id)
        self.assertEqual(task_info['state'], t.state)

    def test_get_task_no_verify_can_get_task_from_other_worker(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        req = _make_request(self._worker)
        task_info = worker.get_task_no_verify(req, t.id)

        self.assertEqual(task_info['id'], t.id)
        self.assertEqual(task_info['worker'], w.id)
        self.assertEqual(task_info['state'], t.state)

    def test_interrupt_tasks_empty_task_list(self):
        req = _make_request(self._worker)
        ok = worker.interrupt_tasks(req, [])
        self.assertTrue(ok)

    def test_interrupt_tasks_single_task(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)
        ok = worker.interrupt_tasks(req, [t.id])
        self.assertTrue(ok)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['INTERRUPTED'])

    def test_interrupt_tasks_multiple_tasks(self):
        t1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        t2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)
        ok = worker.interrupt_tasks(req, [t1.id, t2.id])
        self.assertTrue(ok)

        t1 = Task.objects.get(id=t1.id)
        self.assertEqual(t1.state, TASK_STATES['INTERRUPTED'])

        t2 = Task.objects.get(id=t2.id)
        self.assertEqual(t2.state, TASK_STATES['INTERRUPTED'])

    def test_interrupt_tasks_interrupt_tasks_recursively(self):
        t1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        t2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
            parent=t1,
        )

        req = _make_request(self._worker)
        ok = worker.interrupt_tasks(req, [t1.id])
        self.assertTrue(ok)

        t1 = Task.objects.get(id=t1.id)
        self.assertEqual(t1.state, TASK_STATES['INTERRUPTED'])

        t2 = Task.objects.get(id=t2.id)
        self.assertEqual(t2.state, TASK_STATES['INTERRUPTED'])

    def test_interrupt_tasks_fails_to_interrupt_another_worker_task(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(Task.DoesNotExist):
            worker.interrupt_tasks(req, [t.id])

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

    def test_interrupt_tasks_do_not_interrupt_finished_tasks(self):
        tasks = {}

        for state in FINISHED_STATES:
            tasks[state] = Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=state,
            )

        req = _make_request(self._worker)
        ok = worker.interrupt_tasks(req, [t.id for t in tasks.values()])
        self.assertTrue(ok)


        for state, task in tasks.items():
            t = Task.objects.get(id=task.id)
            self.assertEqual(t.state, state)

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_interrupt_tasks_fails_to_interrupt_if_not_open_or_finished(self):
        tasks = {}

        for state_id in TASK_STATES:
            state = TASK_STATES[state_id]
            if state == TASK_STATES['OPEN'] or state in FINISHED_STATES:
                continue

            tasks[state] = Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=state,
            )

        req = _make_request(self._worker)

        for _, task in tasks.items():
            with self.assertRaises(Exception):
                worker.interrupt_tasks(req, [task.id])

        for state, task in tasks.items():
            t = Task.objects.get(id=task.id)
            self.assertEqual(t.state, state)

    def test_timeout_tasks_empty_task_list(self):
        req = _make_request(self._worker)
        ok = worker.timeout_tasks(req, [])
        self.assertTrue(ok)

    def test_timeout_tasks_single_task(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)
        ok = worker.timeout_tasks(req, [t.id])
        self.assertTrue(ok)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['TIMEOUT'])

    def test_timeout_tasks_multiple_tasks(self):
        t1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        t2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)
        ok = worker.timeout_tasks(req, [t1.id, t2.id])
        self.assertTrue(ok)

        t1 = Task.objects.get(id=t1.id)
        self.assertEqual(t1.state, TASK_STATES['TIMEOUT'])

        t2 = Task.objects.get(id=t2.id)
        self.assertEqual(t2.state, TASK_STATES['TIMEOUT'])

    def test_timeout_tasks_timeout_tasks_recursively(self):
        t1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        t2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
            parent=t1,
        )

        req = _make_request(self._worker)
        ok = worker.timeout_tasks(req, [t1.id])
        self.assertTrue(ok)

        t1 = Task.objects.get(id=t1.id)
        self.assertEqual(t1.state, TASK_STATES['TIMEOUT'])

        t2 = Task.objects.get(id=t2.id)
        self.assertEqual(t2.state, TASK_STATES['TIMEOUT'])

    def test_timeout_tasks_fails_to_interrupt_another_worker_task(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(Task.DoesNotExist):
            worker.timeout_tasks(req, [t.id])

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

    def test_timeout_tasks_do_not_interrupt_finished_tasks(self):
        tasks = {}

        for state in FINISHED_STATES:
            tasks[state] = Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=state,
            )

        req = _make_request(self._worker)
        ok = worker.timeout_tasks(req, [t.id for t in tasks.values()])
        self.assertTrue(ok)


        for state, task in tasks.items():
            t = Task.objects.get(id=task.id)
            self.assertEqual(t.state, state)

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_timeout_tasks_fails_to_interrupt_if_not_open_or_finished(self):
        tasks = {}

        for state_id in TASK_STATES:
            state = TASK_STATES[state_id]
            if state == TASK_STATES['OPEN'] or state in FINISHED_STATES:
                continue

            tasks[state] = Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=state,
            )

        req = _make_request(self._worker)

        for _, task in tasks.items():
            with self.assertRaises(Exception):
                worker.timeout_tasks(req, [task.id])

        for state, task in tasks.items():
            t = Task.objects.get(id=task.id)
            self.assertEqual(t.state, state)

    def test_assign_task(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        req = _make_request(self._worker)
        worker.assign_task(req, t.id)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['ASSIGNED'])

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_assign_task_fails_to_assing_another_worker_task(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(Exception):
            worker.assign_task(req, t.id)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FREE'])

    def test_open_task(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['ASSIGNED'],
        )

        req = _make_request(self._worker)
        worker.open_task(req, t.id)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_open_task_fails_to_open_another_worker_task(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['ASSIGNED'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(Exception):
            worker.open_task(req, t.id)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['ASSIGNED'])

    def test_close_task(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)
        worker.close_task(req, t.id, '')

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CLOSED'])

    def test_close_task_fails_to_close_another_worker_task(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(Task.DoesNotExist):
            worker.close_task(req, t.id, '')

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

    def test_cancel_task(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)
        worker.cancel_task(req, t.id)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['CANCELED'])

    def test_cancel_task_fails_to_cancel_another_worker_task(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(Task.DoesNotExist):
            worker.cancel_task(req, t.id)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

    def test_fail_task(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)
        worker.fail_task(req, t.id, '')

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['FAILED'])

    def test_fail_task_fails_to_fail_another_worker_task(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(Task.DoesNotExist):
            worker.fail_task(req, t.id, '')

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.state, TASK_STATES['OPEN'])

    def test_set_task_weight(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        self.assertEqual(t.weight, 1)

        req = _make_request(self._worker)
        weight = worker.set_task_weight(req, t.id, 100)
        self.assertEqual(weight, 100)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.weight, 100)

    def test_set_task_weight_fails_if_another_worker_task(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        self.assertEqual(t.weight, 1)

        req = _make_request(self._worker)

        with self.assertRaises(Task.DoesNotExist):
            worker.set_task_weight(req, t.id, 100)

        t = Task.objects.get(id=t.id)
        self.assertEqual(t.weight, 1)

    @pytest.mark.xfail(reason='Check issue #68 for more info (https://git.io/fxSZ2).')
    def test_update_worker(self):
        req = _make_request(self._worker)

        self.assertTrue(self._worker.enabled)
        self.assertTrue(self._worker.ready)
        self.assertEqual(self._worker.task_count, 0)

        wi = worker.update_worker(req, False, False, 1)

        self.assertFalse(wi['enabled'])
        self.assertFalse(wi['ready'])
        self.assertEqual(wi['task_count'], 1)

    def test_get_tasks_to_assign(self):
        for _ in range(2):
            Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=TASK_STATES['FREE'],
            )

            Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=TASK_STATES['ASSIGNED'],
                exclusive=True,
            )

            Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=TASK_STATES['FREE'],
                awaited=True,
            )

            Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=TASK_STATES['ASSIGNED'],
            )

            Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=TASK_STATES['CLOSED'],
            )

        req = _make_request(self._worker)
        tasks = worker.get_tasks_to_assign(req)

        self.assertEqual(len(tasks), 8)
        self.assertEqual(len([t for t in tasks if t['state'] == TASK_STATES['FREE'] and not t['exclusive'] and not t['awaited']]), 2)
        self.assertEqual(len([t for t in tasks if t['state'] == TASK_STATES['ASSIGNED'] and t['exclusive']]), 2)
        self.assertEqual(len([t for t in tasks if t['state'] == TASK_STATES['FREE'] and t['awaited']]), 2)
        self.assertEqual(len([t for t in tasks if t['state'] == TASK_STATES['ASSIGNED'] and not t['exclusive']]), 2)

    def test_get_tasks_to_assign_limit_tasks(self):
        for _ in range(10):
            Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=TASK_STATES['FREE'],
            )

            Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=TASK_STATES['ASSIGNED'],
                exclusive=True,
            )

            Task.objects.create(
                worker=self._worker,
                arch=self._arch,
                channel=self._channel,
                owner=self._user,
                state=TASK_STATES['FREE'],
                awaited=True,
            )

        req = _make_request(self._worker)
        tasks = worker.get_tasks_to_assign(req)

        self.assertEqual(len(tasks), 10)
        self.assertEqual(len([t for t in tasks if t['state'] == TASK_STATES['ASSIGNED'] and t['exclusive']]), 10)

    def test_get_awaited_tasks(self):
        t1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        t2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
            awaited=True,
            parent=t1,
        )

        req = _make_request(self._worker)
        tasks = worker.get_awaited_tasks(req, [t1.export()])
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['id'], t2.id)

    def test_get_awaited_tasks_if_empty_task_list(self):
        t_parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
            awaited=True,
            parent=t_parent,
        )

        req = _make_request(self._worker)
        tasks = worker.get_awaited_tasks(req, [])
        self.assertEqual(len(tasks), 0)

    def test_create_subtask(self):
        t_parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        req = _make_request(self._worker)
        task_id = worker.create_subtask(req, 'Label', 'Method', None, t_parent.id)
        self.assertTrue(task_id > 0)

        t_child = Task.objects.get(id=task_id)
        self.assertEqual(t_child.parent.id, t_parent.id)
        self.assertEqual(t_child.label, 'Label')
        self.assertEqual(t_child.method, 'Method')

    def test_create_subtask_if_another_worker_task(self):
        w = Worker.objects.create(
            worker_key='other-worker',
            name='other-worker',
        )

        t = Task.objects.create(
            worker=w,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(Task.DoesNotExist):
            worker.create_subtask(req, '', '', None, t.id)

    def test_wait(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        self.assertFalse(t.waiting)

        req = _make_request(self._worker)
        ok = worker.wait(req, t.id)
        self.assertTrue(ok)

        t = Task.objects.get(id=t.id)
        self.assertTrue(t.waiting)

    def test_wait_subtasks(self):
        t1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        t2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
            parent=t1,
        )

        self.assertFalse(t1.waiting)
        self.assertFalse(t1.awaited)
        self.assertFalse(t2.waiting)
        self.assertFalse(t2.awaited)

        req = _make_request(self._worker)
        ok = worker.wait(req, t1.id)
        self.assertTrue(ok)

        t1 = Task.objects.get(id=t1.id)
        self.assertTrue(t1.waiting)
        self.assertFalse(t1.awaited)

        t2 = Task.objects.get(id=t2.id)
        self.assertFalse(t2.waiting)
        self.assertTrue(t2.awaited)

    def test_wait_subtasks_filter_child(self):
        t1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        t2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
            parent=t1,
        )

        t3 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
            parent=t1,
        )

        self.assertFalse(t1.waiting)
        self.assertFalse(t1.awaited)
        self.assertFalse(t2.waiting)
        self.assertFalse(t2.awaited)
        self.assertFalse(t3.waiting)
        self.assertFalse(t3.awaited)

        req = _make_request(self._worker)
        ok = worker.wait(req, t1.id, [t2.id])
        self.assertTrue(ok)

        t1 = Task.objects.get(id=t1.id)
        self.assertTrue(t1.waiting)
        self.assertFalse(t1.awaited)

        t2 = Task.objects.get(id=t2.id)
        self.assertFalse(t2.waiting)
        self.assertTrue(t2.awaited)

        t3 = Task.objects.get(id=t3.id)
        self.assertFalse(t3.waiting)
        self.assertFalse(t3.awaited)

    def test_check_wait(self):
        t_parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['CLOSED'],
            parent=t_parent,
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['CLOSED'],
            parent=t_parent,
        )

        req = _make_request(self._worker)
        finished, unfinished = worker.check_wait(req, t_parent.id)
        self.assertEqual(len(finished), 2)
        self.assertEqual(len(unfinished), 0)

    def test_check_wait_subtasks_not_finished(self):
        t_parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
            parent=t_parent,
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
            parent=t_parent,
        )

        req = _make_request(self._worker)
        finished, unfinished = worker.check_wait(req, t_parent.id)
        self.assertEqual(len(finished), 0)
        self.assertEqual(len(unfinished), 2)

    def test_check_wait_without_subtasks(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
        )

        req = _make_request(self._worker)
        finished, unfinished = worker.check_wait(req, t.id)
        self.assertEqual(len(finished), 0)
        self.assertEqual(len(unfinished), 0)

    def test_upload_task_log(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)

        with tempfile.NamedTemporaryFile(delete=True) as tf:
            msg = b'this is a text message'
            checksum = hashlib.sha256(msg).hexdigest()
            encode_func = base64.encodebytes if hasattr(base64, "encodebytes") else base64.encodestring
            chunk = encode_func(msg)
            chunk_start = 0
            chunk_size = len(msg)

            ok = worker.upload_task_log(req,
                                        t.id,
                                        tf.name,
                                        0o644,
                                        str(chunk_start),
                                        str(chunk_size),
                                        checksum, chunk)

            self.assertTrue(ok)
            self.assertEqual(tf.read(), msg)

    def test_upload_task_log_catch_decode_error(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)

        with tempfile.NamedTemporaryFile(delete=True) as tf:
            msg = b'this is a text message'
            checksum = 'invalid-checksum'
            encode_func = base64.encodebytes if hasattr(base64, "encodebytes") else base64.encodestring
            chunk = encode_func(msg)
            chunk_start = 0
            chunk_size = len(msg)

            ok = worker.upload_task_log(req,
                                        t.id,
                                        tf.name,
                                        0o644,
                                        str(chunk_start),
                                        str(chunk_size),
                                        checksum, chunk)

            self.assertFalse(ok)
            self.assertEqual(tf.read(), b'')

    def test_upload_task_log_fails_if_invalid_path(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(ValueError):
            worker.upload_task_log(req, t.id, '../foo/bar', 0o644, '', '', '', '')

    def test_upload_task_log_fails_if_task_not_open(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['CLOSED'],
        )

        req = _make_request(self._worker)

        with self.assertRaises(ValueError):
            worker.upload_task_log(req, t.id, '/foo/bar', 0o644, '', '', '', '')


class TestXmlRpcWorkerNotAuthenticated(django.test.TransactionTestCase):

    def test_get_worker_info(self):
        with self.assertRaises(PermissionDenied):
            worker.get_worker_info(_make_request(None, False))

    def test_get_worker_id(self):
        with self.assertRaises(PermissionDenied):
            worker.get_worker_id(_make_request(None, False))

    def test_get_worker_tasks(self):
        with self.assertRaises(PermissionDenied):
            worker.get_worker_tasks(_make_request(None, False))

    def test_get_task(self):
        with self.assertRaises(PermissionDenied):
            worker.get_task(_make_request(None, False), 1)

    def test_get_task_no_verify(self):
        with self.assertRaises(PermissionDenied):
            worker.get_task_no_verify(_make_request(None, False), 1)

    def test_interrupt_tasks(self):
        with self.assertRaises(PermissionDenied):
            worker.interrupt_tasks(_make_request(None, False), [])

    def test_timeout_tasks(self):
        with self.assertRaises(PermissionDenied):
            worker.timeout_tasks(_make_request(None, False), [])

    def test_assign_task(self):
        with self.assertRaises(PermissionDenied):
            worker.assign_task(_make_request(None, False), 1)

    def test_open_task(self):
        with self.assertRaises(PermissionDenied):
            worker.open_task(_make_request(None, False), 1)

    def test_close_task(self):
        with self.assertRaises(PermissionDenied):
            worker.close_task(_make_request(None, False), 1, None)

    def test_cancel_task(self):
        with self.assertRaises(PermissionDenied):
            worker.cancel_task(_make_request(None, False), 1)

    def test_fail_task(self):
        with self.assertRaises(PermissionDenied):
            worker.fail_task(_make_request(None, False), 1, None)

    def test_set_task_weight(self):
        with self.assertRaises(PermissionDenied):
            worker.set_task_weight(_make_request(None, False), 1, 10)

    def test_update_worker(self):
        with self.assertRaises(PermissionDenied):
            worker.update_worker(_make_request(None, False), True, True, 0)

    def test_get_tasks_to_assign(self):
        with self.assertRaises(PermissionDenied):
            worker.get_tasks_to_assign(_make_request(None, False))

    def test_get_awaited_tasks(self):
        with self.assertRaises(PermissionDenied):
            worker.get_awaited_tasks(_make_request(None, False), [])

    def test_create_subtask(self):
        with self.assertRaises(PermissionDenied):
            worker.create_subtask(_make_request(None, False), '', '', None, 1)

    def test_wait(self):
        with self.assertRaises(PermissionDenied):
            worker.wait(_make_request(None, False), 1)

    def test_check_wait(self):
        with self.assertRaises(PermissionDenied):
            worker.check_wait(_make_request(None, False), 1)

    def test_upload_task_log(self):
        with self.assertRaises(PermissionDenied):
            worker.upload_task_log(_make_request(None, False), 1, '/dev/null', 0o666, 0, 0, None, None)
