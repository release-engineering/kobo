# -*- coding: utf-8 -*-

import django

from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User

from mock import PropertyMock

from kobo.client.constants import TASK_STATES
from kobo.hub.models import Arch, Channel, Task, Worker
from kobo.hub.xmlrpc import client

from .utils import DjangoRunner

runner = DjangoRunner()
setup_module = runner.start
teardown_module = runner.stop


def _make_request(user=None, is_authenticated=True, is_superuser=True, meta=None):
    if user is None:
        return PropertyMock(
            user=PropertyMock(
                is_authenticated=lambda: is_authenticated,
                is_superuser=is_superuser,
                username='testuser',
            ),
            META=meta,
        )

    return PropertyMock(
        user=user,
        META=meta,
    )


class TestXmlRpcClient(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        super(TestXmlRpcClient, self).setUp()

        user = User.objects.create(username='testuser', is_superuser=True)
        arch = Arch.objects.create(name='noarch', pretty_name='noarch')
        channel = Channel.objects.create(name='default')

        self._arch = arch
        self._channel = channel
        self._user = user

    def test_shutdown_worker(self):
        w = Worker.objects.create(
            worker_key='worker',
            name='worker',
            enabled=True,
        )

        task_id = client.shutdown_worker(_make_request(), w.name)
        self.assertTrue(task_id > 0)

        task = Task.objects.get(id=task_id)
        self.assertTrue(task.exclusive)
        self.assertTrue('kill' in task.args)
        self.assertFalse(task.args['kill'])
        self.assertEqual(task.method, 'ShutdownWorker')

    def test_shutdown_worker_kill(self):
        w = Worker.objects.create(
            worker_key='enabled-worker',
            name='enabled-worker',
            enabled=True,
        )

        task_id = client.shutdown_worker(_make_request(), w.name, kill=True)
        self.assertTrue(task_id > 0)

        task = Task.objects.get(id=task_id)
        self.assertTrue(task.exclusive)
        self.assertTrue('kill' in task.args)
        self.assertTrue(task.args['kill'])
        self.assertEqual(task.method, 'ShutdownWorker')

    def test_enable_worker(self):
        w = Worker.objects.create(
            worker_key='disabled-worker',
            name='disabled-worker',
            enabled=False,
        )
        self.assertFalse(w.enabled)

        client.enable_worker(_make_request(), w.name)

        w = Worker.objects.get(id=w.id)
        self.assertTrue(w.enabled)

    def test_disable_worker(self):
        w = Worker.objects.create(
            worker_key='enabled-worker',
            name='enabled-worker',
            enabled=True,
        )
        self.assertTrue(w.enabled)

        client.disable_worker(_make_request(), w.name)

        w = Worker.objects.get(id=w.id)
        self.assertFalse(w.enabled)

    def test_get_worker_info(self):
        w = Worker.objects.create(
            worker_key='test-worker',
            name='test-worker',
        )

        info = client.get_worker_info(_make_request(), w.name)
        self.assertEqual(info['id'], w.id)

    def test_get_worker_info_non_existent(self):
        info = client.get_worker_info(_make_request(), 'non-existent')
        self.assertEqual(info, {})

    def test_get_worker_info_no_auth(self):
        # Should be permissible if anonymous - no exception raised
        client.get_worker_info(_make_request(
            is_authenticated=False,
            is_superuser=False,
        ), 'worker')

    def test_get_worker_info_if_authenticated_but_not_admin(self):
        # Should be permissible if authenticated, but not admin - no exception raised
        client.get_worker_info(_make_request(
            is_authenticated=False,
            is_superuser=False,
        ), 'worker')

    def test_task_info(self):
        task_id = Task.create_task(self._user.username, 'label', 'method')
        task_info = client.task_info(_make_request(), task_id)
        self.assertEqual(task_info['id'], task_id)

    def test_task_info_flat(self):
        task_id = Task.create_task(self._user.username, 'label', 'method')
        task_info = client.task_info(_make_request(), task_id, flat=True)
        self.assertEqual(task_info['id'], task_id)

    def test_task_info_non_existent(self):
        with self.assertRaises(Task.DoesNotExist):
            client.task_info(_make_request(), 999)

    def test_get_tasks_with_no_filters(self):
        Task.create_task(self._user.username, 'task-1', 'method')
        Task.create_task(self._user.username, 'task-2', 'method')
        Task.create_task(self._user.username, 'task-3', 'method')
        Task.create_task(self._user.username, 'task-4', 'method')
        Task.create_task(self._user.username, 'task-5', 'method')

        task_list = client.get_tasks(_make_request(), None, None)

        self.assertEqual(len(task_list), 5)

    def test_get_tasks_filter_by_ids(self):
        t1 = Task.create_task(self._user.username, 'task-1', 'method')
        t2 = Task.create_task(self._user.username, 'task-2', 'method')
        Task.create_task(self._user.username, 'task-3', 'method')
        Task.create_task(self._user.username, 'task-4', 'method')
        Task.create_task(self._user.username, 'task-5', 'method')

        task_list = client.get_tasks(_make_request(), [t1, t2], None)

        self.assertEqual(len(task_list), 2)
        self.assertEqual(set([t['id'] for t in task_list]), set([t1, t2]))

    def test_get_tasks_filter_by_state(self):
        t1 = Task.create_task(self._user.username, 'task-1', 'method', state=TASK_STATES['OPEN'])
        t2 = Task.create_task(self._user.username, 'task-2', 'method', state=TASK_STATES['TIMEOUT'])
        Task.create_task(self._user.username, 'task-3', 'method')
        Task.create_task(self._user.username, 'task-4', 'method')
        Task.create_task(self._user.username, 'task-5', 'method')

        task_list = client.get_tasks(_make_request(), None, [TASK_STATES['OPEN'], TASK_STATES['TIMEOUT']])

        self.assertEqual(len(task_list), 2)
        self.assertEqual(set([t['id'] for t in task_list]), set([t1, t2]))

    def test_cancel_task(self):
        task_id = Task.create_task(self._user.username, 'task', 'method')
        ret = client.cancel_task(_make_request(), task_id)
        self.assertIsNone(ret)

        t = Task.objects.get(id=task_id)
        self.assertEqual(t.state, TASK_STATES['CANCELED'])

    def test_cancel_task_non_existent(self):
        ret = client.cancel_task(_make_request(), 999)
        self.assertEqual(ret, 'Specified task 999 does not exist.')

    def test_resubmit_task(self):
        task_id = Task.create_task(self._user.username, 'task', 'method', state=TASK_STATES['TIMEOUT'])
        new_id = client.resubmit_task(_make_request(self._user), task_id, force=False)
        self.assertTrue(new_id > 0)
        self.assertNotEqual(task_id, new_id)
        task = Task.objects.get(id=new_id)
        self.assertEqual(task.priority, 10)

    def test_resubmit_task_do_not_failed(self):
        task_id = Task.create_task(self._user.username, 'task', 'method', state=TASK_STATES['OPEN'])

        with self.assertRaises(Exception):
            client.resubmit_task(_make_request(), task_id, force=False)

    def test_resubmit_task_force_not_failed(self):
        task_id = Task.create_task(self._user.username, 'task', 'method', state=TASK_STATES['OPEN'])
        new_id = client.resubmit_task(_make_request(self._user), task_id, force=True)
        self.assertTrue(new_id > 0)
        self.assertNotEqual(task_id, new_id)

    def test_resubmit_task_non_existent(self):
        with self.assertRaises(Task.DoesNotExist):
            client.resubmit_task(_make_request(), 999)

    def test_resubmit_task_set_priority(self):
        task_id = Task.create_task(self._user.username, 'task', 'method', state=TASK_STATES['TIMEOUT'])
        new_id = client.resubmit_task(_make_request(self._user), task_id, force=False, priority=19)
        task = Task.objects.get(id=new_id)
        self.assertEqual(task.priority, 19)

    def test_list_workers_enabled(self):
        Worker.objects.create(
            worker_key='enabled-worker',
            name='enabled-worker',
            enabled=True,
        )

        Worker.objects.create(
            worker_key='disabled-worker',
            name='disabled-worker',
            enabled=False,
        )

        worker_list = client.list_workers(_make_request(), True)
        self.assertEqual(len(worker_list), 1)
        self.assertEqual(worker_list[0], 'enabled-worker')

    def test_list_workers_disabled(self):
        Worker.objects.create(
            worker_key='enabled-worker',
            name='enabled-worker',
            enabled=True,
        )

        Worker.objects.create(
            worker_key='disabled-worker',
            name='disabled-worker',
            enabled=False,
        )

        worker_list = client.list_workers(_make_request(), False)
        self.assertEqual(len(worker_list), 1)
        self.assertEqual(worker_list[0], 'disabled-worker')

    def test_create_task(self):
        task_id = client.create_task(_make_request(self._user), {
            'owner_name': self._user.username,
            'label': 'task',
            'method': 'method',
        })

        self.assertTrue(task_id > 0)

        task = Task.objects.get(id=task_id)
        self.assertEqual(task.resubmitted_by.id, self._user.id)
        self.assertIsNone(task.resubmitted_from)

    def test_create_task_based_on_task(self):
        base_task_id = Task.create_task(self._user.username, 'task', 'method')

        clone_task_id = client.create_task(_make_request(self._user), {
            'task_id': base_task_id,
        })

        self.assertTrue(clone_task_id > 0)
        self.assertNotEqual(base_task_id, clone_task_id)

        task = Task.objects.get(id=clone_task_id)
        self.assertEqual(task.resubmitted_by.id, self._user.id)
        self.assertEqual(task.resubmitted_from.id, base_task_id)

    def test_task_url(self):
        url = client.task_url(_make_request(meta={
            'SERVER_PORT': '80',
            'HTTP_HOST': 'example.com',
            'SERVER_NAME': 'srv-name',
        }), 999)

        self.assertEqual(url, 'http://example.com/task/999/')

    def test_task_url_ssl(self):
        url = client.task_url(_make_request(meta={
            'SERVER_PORT': '443',
            'HTTP_HOST': 'example.com',
            'SERVER_NAME': 'srv-name',
        }), 999)

        self.assertEqual(url, 'https://example.com/task/999/')

    def test_task_url_localhost(self):
        url = client.task_url(_make_request(meta={
            'SERVER_PORT': '80',
            'HTTP_HOST': 'localhost',
            'SERVER_NAME': 'srv-name',
        }), 999)

        self.assertEqual(url, 'http://srv-name/task/999/')


class TestXmlRpcClientAuthentication(django.test.TransactionTestCase):

    def test_shutdown_worker_raise_if_no_auth(self):
        with self.assertRaises(PermissionDenied):
            client.shutdown_worker(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), 'worker')

    def test_enable_worker_raise_if_no_auth(self):
        with self.assertRaises(PermissionDenied):
            client.enable_worker(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), 'worker')

    def test_disable_worker_raise_if_no_auth(self):
        with self.assertRaises(PermissionDenied):
            client.disable_worker(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), 'worker')

    def test_cancel_task_raise_if_no_auth(self):
        with self.assertRaises(PermissionDenied):
            client.cancel_task(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), 999)

    def test_resubmit_task_raise_if_no_auth(self):
        with self.assertRaises(PermissionDenied):
            client.resubmit_task(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), 999)

    def test_create_task_raise_if_no_auth(self):
        with self.assertRaises(PermissionDenied):
            client.create_task(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), {})

    def test_shutdown_worker_raise_if_authenticated_but_not_admin(self):
        with self.assertRaises(PermissionDenied):
            client.shutdown_worker(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), 'worker')

    def test_enable_worker_raise_if_authenticated_but_not_admin(self):
        with self.assertRaises(PermissionDenied):
            client.enable_worker(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), 'worker')

    def test_disable_worker_raise_if_authenticated_but_not_admin(self):
        with self.assertRaises(PermissionDenied):
            client.disable_worker(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), 'worker')

    def test_create_task_raise_if_authenticated_but_not_admin(self):
        with self.assertRaises(PermissionDenied):
            client.create_task(_make_request(
                is_authenticated=False,
                is_superuser=False,
            ), {})
