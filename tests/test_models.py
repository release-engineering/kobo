# -*- coding: utf-8 -*-

import gzip
import os
import tempfile

import django
import pytest
import six

from datetime import datetime, timedelta
from mock import patch, Mock, PropertyMock

# Only for Django >= 1.7
if 'setup' in dir(django):
    # This has to happen before below imports because they have a hard requirement
    # on settings being loaded before import.
    django.setup()

from django.contrib.auth.models import User

try:
    from django.test import override_settings
except:
    # Django <= 1.6
    from django.test.utils import override_settings

from kobo.client.constants import TASK_STATES
from kobo.hub import models
from kobo.hub.models import (
    Arch,
    Channel,
    Task,
    Worker,
    TaskLogs,
)

from .utils import DjangoRunner

runner = DjangoRunner()
setup_module = runner.start
teardown_module = runner.stop


class TestArch(django.test.TransactionTestCase):

    def test_export(self):
        arch = Arch.objects.create(name='i386', pretty_name='32 bit')
        data = arch.export()
        self.assertTrue(data['id'] > 0)
        self.assertEquals(data['name'], 'i386')
        self.assertEquals(data['pretty_name'], '32 bit')

    def test_worker_count(self):
        arch = Arch.objects.create(name='i386', pretty_name='32 bit')
        self.assertEquals(arch.worker_count, 0)

        worker = Worker.objects.create(
            worker_key='mock-worker',
            name='mock-worker',
        )

        worker.arches.add(arch)
        worker.save()

        self.assertEquals(arch.worker_count, 1)


class TestChannel(django.test.TransactionTestCase):

    def test_export(self):
        channel = Channel.objects.create(name='test')
        data = channel.export()
        self.assertTrue(data['id'] > 0)
        self.assertEquals(data['name'], 'test')

    def test_worker_count(self):
        channel = Channel.objects.create(name='test')
        self.assertEquals(channel.worker_count, 0)

        worker = Worker.objects.create(
            worker_key='mock-worker',
            name='mock-worker',
        )

        worker.channels.add(channel)
        worker.save()

        self.assertEquals(channel.worker_count, 1)


@override_settings(VERSION='1.0.0')
class TestWorker(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        self._arch = Arch.objects.create(name='i386', pretty_name='32 bit')
        self._channel = Channel.objects.create(name='test')
        self._user = User.objects.create(username='testuser')

    def test_save_creates_worker_key_if_empty(self):
        worker = Worker.objects.create(name='Worker')
        self.assertIsNotNone(worker.worker_key)
        self.assertEquals(len(worker.worker_key), 64)

    def test_save_update_fields(self):
        worker = Worker.objects.create(worker_key='worker', name='Worker')
        worker.save()

        self.assertEquals(worker.task_count, 0)
        self.assertEquals(worker.current_load, 0)
        self.assertEquals(worker.ready, True)

        Task.objects.create(
            worker=worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
            weight=100,
        )

        worker.save()
        worker = Worker.objects.get(id=worker.id)
        self.assertEquals(worker.task_count, 1)
        self.assertEquals(worker.current_load, 100)
        self.assertEquals(worker.ready, False)

    def test_export(self):
        worker = Worker.objects.create(worker_key='worker', name='Worker')
        data = worker.export()

        self.assertTrue(data['id'] > 0)
        self.assertEquals(data['name'], 'Worker')
        self.assertEquals(data['arches'], [])
        self.assertEquals(data['channels'], [])
        self.assertEquals(data['enabled'], True)
        self.assertEquals(data['max_load'], 1)
        self.assertEquals(data['ready'], True)
        self.assertEquals(data['task_count'], 0)
        self.assertEquals(data['current_load'], 0)
        self.assertEquals(data['version'], '1.0.0')

    def test_export_with_arch_and_channel(self):
        worker = Worker.objects.create(worker_key='worker', name='Worker')
        worker.arches.add(self._arch)
        worker.channels.add(self._channel)
        worker.save()

        data = worker.export()

        self.assertTrue(data['id'] > 0)
        self.assertEquals(data['name'], 'Worker')
        self.assertEquals(data['arches'][0]['name'], 'i386')
        self.assertEquals(data['channels'][0]['name'], 'test')
        self.assertEquals(data['enabled'], True)
        self.assertEquals(data['max_load'], 1)
        self.assertEquals(data['ready'], True)
        self.assertEquals(data['task_count'], 0)
        self.assertEquals(data['current_load'], 0)
        self.assertEquals(data['version'], '1.0.0')

    def test_running_tasks(self):
        worker = Worker.objects.create(worker_key='worker', name='Worker')

        Task.objects.create(
            worker=worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        Task.objects.create(
            worker=worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        Task.objects.create(
            worker=None,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        tasks = worker.running_tasks()
        self.assertEquals(len(tasks), 1)

    def test_assigned_tasks(self):
        worker = Worker.objects.create(worker_key='worker', name='Worker')

        Task.objects.create(
            worker=worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['ASSIGNED'],
        )

        Task.objects.create(
            worker=worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        Task.objects.create(
            worker=None,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['ASSIGNED'],
        )

        tasks = worker.assigned_tasks()
        self.assertEquals(len(tasks), 1)

    @pytest.mark.xfail(reason='Check issue #68 for more info (https://git.io/fxSZ2).')
    def test_update_worker(self):
        worker = Worker.objects.create(worker_key='worker', name='Worker')
        data = worker.update_worker(False, False, 0)

        self.assertFalse(data['enabled'])
        self.assertFalse(data['ready'])
        self.assertEquals(data['task_count'], 0)


class TestWorkerManager(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        self._arch = Arch.objects.create(name='i386', pretty_name='32 bit')
        self._channel = Channel.objects.create(name='test')
        self._user = User.objects.create(username='testuser')

    def test_enabled(self):
        Worker.objects.create(worker_key='worker-disabled', name='Worker disabled', enabled=False)
        worker = Worker.objects.create(worker_key='worker-enabled', name='Worker enabled', enabled=True)

        workers = Worker.objects.enabled()
        self.assertEquals(len(workers), 1)
        self.assertEquals(workers[0].id, worker.id)

    def test_ready(self):
        worker1 = Worker.objects.create(worker_key='worker-1', name='Worker 1', enabled=True)

        Task.objects.create(
            worker=worker1,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
            weight=100
        )

        worker1.save()

        worker2 = Worker.objects.create(worker_key='worker-2', name='Worker 2', enabled=True)

        workers = Worker.objects.ready()
        self.assertEquals(len(workers), 1)
        self.assertEquals(workers[0].id, worker2.id)


class TestTaskManager(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        self._arch = Arch.objects.create(name='test-arch', pretty_name='Test Arch')
        self._channel = Channel.objects.create(name='test-channel')
        self._user = User.objects.create(username='test-user')
        self._worker = Worker.objects.create(worker_key='test-worker', name='Test Worker')
        self._worker2 = Worker.objects.create(worker_key='test-worker-2', name='Test Worker 2')

    def _create_task(self, **kwargs):
        params = {
            'worker': self._worker,
            'arch': self._arch,
            'channel': self._channel,
            'owner': self._user,
            'method': 'DummyTask',
            'state': TASK_STATES['FREE'],
        }

        params.update(kwargs)

        return Task.objects.create(**params)

    @pytest.mark.xfail(reason='Check issue #88 for more info (https://git.io/fpzNc).')
    def test_custom_query_set_filter_achieved(self):
        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['CLOSED'],
            archive=True,
        )

        tasks = Task.objects.all()

        self.assertEquals(len(tasks), 2)

    def test_get_and_verify(self):
        task1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        task2 = Task.objects.get_and_verify(task1.id, self._worker)

        self.assertEquals(task2.id, task1.id)

    def test_get_and_verify_fails_if_different_worker(self):
        task1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        with self.assertRaises(Task.DoesNotExist):
            Task.objects.get_and_verify(task1.id, self._worker2)

    def test_running(self):
        self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['ASSIGNED'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['OPEN'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['OPEN'], exclusive=True)

        tasks = Task.objects.running()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)

    def test_free(self):
        self._create_task(worker=self._worker, state=TASK_STATES['ASSIGNED'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['FREE'], exclusive=True)

        tasks = Task.objects.free()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)

    def test_assigned(self):
        self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['ASSIGNED'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['ASSIGNED'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['ASSIGNED'], exclusive=True)

        tasks = Task.objects.assigned()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)

    def test_opened(self):
        self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['OPEN'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['OPEN'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['OPEN'], exclusive=True)

        tasks = Task.objects.opened()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)

    def test_closed(self):
        self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['CLOSED'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['CLOSED'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['CLOSED'], exclusive=True)

        tasks = Task.objects.closed()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)

    def test_canceled(self):
        self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['CANCELED'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['CANCELED'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['CANCELED'], exclusive=True)

        tasks = Task.objects.canceled()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)

    def test_failed(self):
        self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['FAILED'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['FAILED'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['FAILED'], exclusive=True)

        tasks = Task.objects.failed()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)

    def test_interrupted(self):
        self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['INTERRUPTED'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['INTERRUPTED'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['INTERRUPTED'], exclusive=True)

        tasks = Task.objects.interrupted()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)

    def test_timeout(self):
        self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['TIMEOUT'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['TIMEOUT'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['TIMEOUT'], exclusive=True)

        tasks = Task.objects.timeout()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)

    def test_created(self):
        self._create_task(worker=self._worker, state=TASK_STATES['FREE'])
        t2 = self._create_task(worker=self._worker, state=TASK_STATES['CREATED'])
        t3 = self._create_task(worker=self._worker, state=TASK_STATES['CREATED'])
        t4 = self._create_task(worker=self._worker2, state=TASK_STATES['CREATED'], exclusive=True)

        tasks = Task.objects.created()

        self.assertEquals(len(tasks), 3)
        self.assertEquals(tasks[0].id, t4.id)
        self.assertEquals(tasks[1].id, t2.id)
        self.assertEquals(tasks[2].id, t3.id)


class TestTaskLog(django.test.TransactionTestCase):

    def test_get_chunk_from_cached_file(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        log_msg = 'This is a log message.'
        log_file = 'cached.log'

        task_log = TaskLogs(task)
        task_log[log_file] = log_msg

        s = task_log.get_chunk(log_file, 0, 1024)

        self.assertEquals(s, log_msg)

    def test_get_chunk_gz_file(self):
        _, filepath = tempfile.mkstemp(prefix='kobo-test-', suffix='.log.gz', text=True)
        filename = os.path.basename(filepath)[:-3]
        content = b'This is a log message.'

        f = gzip.open(filepath, mode='wb')
        f.write(content)
        f.close()

        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        s = task_log.get_chunk(filename, 0, 1024)
        os.remove(filepath)

        self.assertEquals(s, content)

    def test_get_chunk_small_file(self):
        _, filepath = tempfile.mkstemp(prefix='kobo-test-', suffix='.log', text=True)
        filename = os.path.basename(filepath)
        content = b'This is a log message.'

        with open(filepath, 'wb') as f:
            f.write(content)

        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        s = task_log.get_chunk(filename, 0, 1024)
        os.remove(filepath)

        self.assertEquals(s, content)

    def test_get_chunk_long_file(self):
        _, filepath = tempfile.mkstemp(prefix='kobo-test-', suffix='.log', text=True)
        filename = os.path.basename(filepath)
        lines = []

        for i in range(100):
            lines.append(('This is the line %d in the log message.\n' % (i + 1)).encode())

        with open(filepath, 'wb') as f:
            f.writelines(lines)

        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        s = task_log.get_chunk(filename, 0, len(lines[0]) + len(lines[1]))
        os.remove(filepath)

        self.assertEquals(s, lines[0] + lines[1])

    def test_get_chunk_invalid_file(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        with self.assertRaises(Exception):
            task_log.get_chunk('invalid.log', 0, 1024)

    def test_tail_gz_file(self):
        _, filepath = tempfile.mkstemp(prefix='kobo-test-', suffix='.log.gz', text=True)
        filename = os.path.basename(filepath)[:-3]
        content = b'This is a log message.'

        f = gzip.open(filepath, mode='wb')
        f.write(content)
        f.close()

        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        s, n = task_log.tail(filename, 1024, 1024)
        os.remove(filepath)

        self.assertEquals(s, content)
        self.assertEquals(n, len(content))

    def test_tail_small_file(self):
        _, filepath = tempfile.mkstemp(prefix='kobo-test-', suffix='.log', text=True)
        filename = os.path.basename(filepath)
        content = b'This is a log message.'

        with open(filepath, 'wb') as f:
            f.write(content)

        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        s, n = task_log.tail(filename, 1024, 1024)
        os.remove(filepath)

        self.assertEquals(s, content)
        self.assertEquals(n, len(content))

    def test_tail_long_file(self):
        _, filepath = tempfile.mkstemp(prefix='kobo-test-', suffix='.log', text=True)
        filename = os.path.basename(filepath)
        lines = []

        for i in range(1000):
            lines.append(('This is the line %d in the log message.\n' % (i + 1)).encode())

        with open(filepath, 'wb') as f:
            f.writelines(lines)

        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        s, n = task_log.tail(filename, 50, 1024)
        os.remove(filepath)

        self.assertEquals(s, lines[-1])
        self.assertEquals(n, sum([len(line) for line in lines]))

    def test_tail_invalid_file(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        with self.assertRaises(Exception):
            task_log.tail('invalid.log', 1024, 1024)

    def test_list_walks_task_dir(self):
        task = PropertyMock(
            id=100,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        with patch.object(models.os, 'walk') as mock_walk:
            mock_walk.return_value = [
                ('/tmp', (), ('file1.log.gz', 'file2.log.gz',),),
            ]

            files = task_log.list

            mock_walk.assert_called_once_with(tempfile.tempdir + '/')
            self.assertEquals(len(files), 2)
            self.assertEquals(files[0], 'file1.log')
            self.assertEquals(files[1], 'file2.log')

    def test_list_include_cached_files(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        with tempfile.NamedTemporaryFile(suffix='.log', dir=tempfile.tempdir, delete=True) as tf:
            filename = os.path.basename(tf.name)
            task_log[filename] = 'This is a log message.'
            files = task_log.list
            self.assertEquals(len(files), 1)
            self.assertEquals(files[0], filename)

    def test_gzip_logs(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        with tempfile.NamedTemporaryFile(suffix='.log', dir=tempfile.tempdir, delete=True) as tf:
            filename = os.path.basename(tf.name)
            task_log[filename] = 'This is a log message.'

            with patch('kobo.hub.models.run') as mock_run:
                task_log.gzip_logs()

                mock_run.assert_called_once_with(
                    'gzip %s' % os.path.join(tempfile.tempdir, filename),
                    can_fail=True,
                    stdout=False
                )

    def test_gzip_logs_gzips_only_log(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)

        with tempfile.NamedTemporaryFile(suffix='.txt', dir=tempfile.tempdir, delete=True) as tf:
            filename = os.path.basename(tf.name)
            task_log[filename] = 'This is a log message.'

            with patch('kobo.hub.models.run') as mock_run:
                task_log.gzip_logs()
                mock_run.assert_not_called()

    def test_save(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        log_file = 'cached.log'
        log_file_path = os.path.join(tempfile.tempdir, log_file)
        log_msg = 'This is a log message.'

        task_log = TaskLogs(task)
        task_log[log_file] = log_msg
        self.assertTrue(task_log.changed[log_file])

        with patch('kobo.hub.models.save_to_file') as mock_save:
            task_log.save()
            self.assertFalse(task_log.changed[log_file])
            mock_save.assert_called_once_with(log_file_path, log_msg, mode=0o644)

    def test_save_ignore_cached_not_changed(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        log_file = 'cached.log'
        log_file_not_changed = 'cached-not-changed.log'
        log_file_path = os.path.join(tempfile.tempdir, log_file)
        log_msg = 'This is a log message.'

        task_log = TaskLogs(task)
        task_log[log_file] = log_msg
        task_log[log_file_not_changed] = log_msg
        task_log.changed[log_file_not_changed] = False

        self.assertTrue(task_log.changed[log_file])

        with patch('kobo.hub.models.save_to_file') as mock_save:
            task_log.save()
            self.assertFalse(task_log.changed[log_file])
            mock_save.assert_called_once_with(log_file_path, log_msg, mode=0o644)

    def test_save_traceback(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        log_file = 'traceback.log'
        log_file_path = os.path.join(tempfile.tempdir, log_file)
        log_msg = 'This is a log message.'

        task_log = TaskLogs(task)
        task_log[log_file] = log_msg
        self.assertTrue(task_log.changed[log_file])

        with patch('kobo.hub.models.save_to_file') as mock_save:
            task_log.save()
            self.assertFalse(task_log.changed[log_file])
            mock_save.assert_called_once_with(log_file_path, log_msg, mode=0o600)

    def test_get_item_non_existing(self):
        task = PropertyMock(
            id=100,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        filename = 'some-random-file.log'

        task_log = TaskLogs(task)
        content = task_log[filename]

        self.assertEquals(content, '')
        self.assertEquals(task_log.cache[filename], '')
        self.assertEquals(task_log.changed[filename], False)

    def test_get_item_non_existing_for_unsaved_task(self):
        task = PropertyMock(
            id=None,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        filename = 'some-random-file.log'

        task_log = TaskLogs(task)
        content = task_log[filename]

        self.assertEquals(content, '')
        self.assertFalse(filename in task_log.cache)
        self.assertFalse(filename in task_log.changed)

    def test_get_item_file(self):
        _, filepath = tempfile.mkstemp(prefix='kobo-test-', suffix='.log', text=True)
        filename = os.path.basename(filepath)
        content = b'This is a log message.'

        with open(filepath, mode='wb') as f:
            f.write(content)

        task = PropertyMock(
            id=100,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)
        file_content = task_log[filename]
        os.remove(filepath)

        self.assertEquals(file_content, content)
        self.assertEquals(task_log.cache[filename], content)
        self.assertEquals(task_log.changed[filename], False)

    def test_get_item_gz_file(self):
        _, filepath = tempfile.mkstemp(prefix='kobo-test-', suffix='.log.gz', text=True)
        filename = os.path.basename(filepath)[:-3]
        content = b'This is a log message.'

        f = gzip.open(filepath, mode='wb')
        f.write(content)
        f.close()

        task = PropertyMock(
            id=100,
            task_dir=Mock(return_value=tempfile.tempdir),
            spec=['id', 'task_dir'],
        )

        task_log = TaskLogs(task)
        file_content = task_log[filename]
        os.remove(filepath)

        self.assertEquals(file_content, content)
        self.assertEquals(task_log.cache[filename], content)
        self.assertEquals(task_log.changed[filename], False)


@override_settings(TASK_DIR='/task-dir')
class TestTask(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        self._arch = Arch.objects.create(name='noarch', pretty_name='noarch')
        self._channel = Channel.objects.create(name='default')
        self._user = User.objects.create(username='testuser', is_superuser=True)
        self._worker = Worker.objects.create(worker_key='worker', name='Worker')

    def test_get_task_dir(self):
        path = Task.get_task_dir(100, create=False)
        self.assertEquals(path, '/task-dir/0/0/100')

    def test_get_task_dir_creates_if_not_exists(self):
        with patch.object(models.os.path, 'isdir', return_value=False):
            with patch.object(models.os, 'makedirs') as mkdir_mock:
                path = Task.get_task_dir(100, create=True)
                mkdir_mock.assert_called_once_with('/task-dir/0/0/100', mode=0o755)
                self.assertEquals(path, '/task-dir/0/0/100')

    def test_get_task_dir_do_not_creates_if_exists(self):
        with patch.object(models.os.path, 'isdir', return_value=True):
            with patch.object(models.os, 'makedirs') as mkdir_mock:
                path = Task.get_task_dir(100, create=True)
                mkdir_mock.assert_not_called()
                self.assertEquals(path, '/task-dir/0/0/100')

    def test_task_dir(self):
        task = Task(id=100)
        path = task.task_dir(create=False)
        self.assertEquals(path, '/task-dir/0/0/100')

    def test_export_flat(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
            weight=100,
        )

        data = t.export(flat=True)

        self.assertEquals(data['id'], t.id)
        self.assertEquals(data['owner'], t.owner.username)
        self.assertEquals(data['worker'], t.worker.id)
        self.assertEquals(data['arch'], t.arch.id)
        self.assertEquals(data['channel'], t.channel.id)
        self.assertEquals(data['state'], t.state)

    def test_export_not_flat(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
            weight=100,
        )

        data = t.export(flat=False)

        self.assertEquals(data['id'], t.id)
        self.assertEquals(data['owner'], t.owner.username)
        self.assertEquals(data['worker']['id'], t.worker.id)
        self.assertEquals(data['arch']['id'], t.arch.id)
        self.assertEquals(data['channel']['id'], t.channel.id)
        self.assertEquals(data['state'], t.state)
        self.assertEquals(data['subtask_id_list'], [])

    def test_subtasks(self):
        t_parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        t_child = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
            parent=t_parent,
        )

        subtasks = t_parent.subtasks()
        self.assertEquals(len(subtasks), 1)
        self.assertEquals(subtasks[0].id, t_child.id)

        subtasks = t_child.subtasks()
        self.assertEquals(len(subtasks), 0)

    def test_time_task_not_started(self):
        t = Task(dt_started=None, dt_finished=None)
        self.assertIsNone(t.time)

    def test_time_task_running(self):
        t = Task(dt_started=datetime(2000, 1, 1, 0, 0), dt_finished=None)

        with patch('kobo.hub.models.datetime.datetime', now=Mock(return_value=datetime(2000, 1, 1, 12, 0))):
            self.assertEquals(t.time, timedelta(hours=12))

    def test_time_task_finished(self):
        t = Task(dt_started=datetime(2000, 1, 1, 0, 0), dt_finished=datetime(2000, 1, 1, 12, 0))
        self.assertEquals(t.time, timedelta(hours=12))

    def test_get_time_display_task_not_started(self):
        t = Task(dt_started=None, dt_finished=None)
        self.assertEquals(t.get_time_display(), '')

    def test_get_time_display_task_running(self):
        t = Task(dt_started=datetime(2000, 1, 1, 0, 0), dt_finished=None)

        with patch('kobo.hub.models.datetime.datetime', now=Mock(return_value=datetime(2000, 1, 1, 12, 0))):
            self.assertEquals(t.get_time_display(), '12:00:00')

    def test_get_time_display_task_finished(self):
        t = Task(dt_started=datetime(2000, 1, 1, 0, 0), dt_finished=datetime(2000, 1, 1, 12, 0))
        self.assertEquals(t.get_time_display(), '12:00:00')

    def test_get_time_display_task_finished_after_24_hours(self):
        t = Task(dt_started=datetime(2000, 1, 1, 0, 0), dt_finished=datetime(2000, 1, 2, 0, 0))
        self.assertEquals(t.get_time_display(), '1 days, 00:00:00')

    def test_get_time_display_task_finished_after_31_days(self):
        t = Task(dt_started=datetime(2000, 1, 1, 0, 0), dt_finished=datetime(2000, 2, 1, 12, 0))
        self.assertEquals(t.get_time_display(), '31 days, 12:00:00')

    def test_set_weight(self):
        t = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
            weight=0,
        )

        self.assertEquals(t.weight, 0)
        t.set_weight(100)
        self.assertEquals(t.weight, 100)

    def test_create_task(self):
        parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        task_id = Task.create_task(
            self._user.username, 'label', 'MethodName',
            args={'key': 'value'},
            parent_id=parent.id,
            worker_name=self._worker.name,
        )

        self.assertTrue(task_id > 0)

        task = Task.objects.get(id=task_id)
        self.assertEquals(task.owner.id, self._user.id)
        self.assertEquals(task.worker.id, self._worker.id)
        self.assertEquals(task.parent.id, parent.id)
        self.assertEquals(task.state, TASK_STATES['ASSIGNED'])
        self.assertEquals(task.label, 'label')
        self.assertEquals(task.method, 'MethodName')
        self.assertEquals(task.args['key'], 'value')

    def test_create_shutdown_task(self):
        task_id = Task.create_shutdown_task(self._user.username, self._worker.name, True)
        self.assertTrue(task_id > 0)

        task = Task.objects.get(id=task_id)
        self.assertEquals(task.owner.id, self._user.id)
        self.assertEquals(task.worker.id, self._worker.id)
        self.assertEquals(task.exclusive, True)
        self.assertEquals(task.weight, 0)
        self.assertEquals(task.method, 'ShutdownWorker')
        self.assertEquals(task.args['kill'], True)

    def test_free_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['ASSIGNED'],
        )

        task.free_task()

        task = Task.objects.get(id=task.id)
        self.assertEquals(task.state, TASK_STATES['FREE'])

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_free_task_with_invalid_initial_state(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        with self.assertRaises(Exception):
            task.free_task()

    def test_assign_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        task.assign_task()

        task = Task.objects.get(id=task.id)
        self.assertEquals(task.state, TASK_STATES['ASSIGNED'])

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_assign_task_with_invalid_initial_state(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['ASSIGNED'],
        )

        with self.assertRaises(Exception):
            task.assign_task()

    def test_open_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        task.open_task()

        task = Task.objects.get(id=task.id)
        self.assertEquals(task.state, TASK_STATES['OPEN'])

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_open_task_with_invalid_initial_state(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        with self.assertRaises(Exception):
            task.open_task()

    def test_close_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        task.close_task()

        task = Task.objects.get(id=task.id)
        self.assertEquals(task.state, TASK_STATES['CLOSED'])

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_close_task_with_invalid_initial_state(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        with self.assertRaises(Exception):
            task.close_task()

    def test_cancel_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        task.cancel_task()

        task = Task.objects.get(id=task.id)
        self.assertEquals(task.state, TASK_STATES['CANCELED'])

    def test_interrupt_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        task.interrupt_task()

        task = Task.objects.get(id=task.id)
        self.assertEquals(task.state, TASK_STATES['INTERRUPTED'])

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_interrupt_task_with_invalid_initial_state(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        with self.assertRaises(Exception):
            task.interrupt_task()

    def test_timeout_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        task.timeout_task()

        task = Task.objects.get(id=task.id)
        self.assertEquals(task.state, TASK_STATES['TIMEOUT'])

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_timeout_task_with_invalid_initial_state(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        with self.assertRaises(Exception):
            task.timeout_task()

    def test_fail_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['OPEN'],
        )

        task.fail_task()

        task = Task.objects.get(id=task.id)
        self.assertEquals(task.state, TASK_STATES['FAILED'])

    @pytest.mark.xfail(six.PY3, reason='Check issue #73 for more info (https://git.io/fxdfm).')
    def test_fail_task_with_invalid_initial_state(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FREE'],
        )

        with self.assertRaises(Exception):
            task.fail_task()

    @pytest.mark.xfail(reason='Check issue #89 for more info (https://git.io/fp6gq).')
    def test_cancel_subtasks(self):
        parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['ASSIGNED'],
        )

        child1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['ASSIGNED'],
            parent=parent,
        )

        child2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
            parent=parent,
        )

        canceled = parent.cancel_subtasks()
        self.assertTrue(canceled)

        child1 = Task.objects.get(id=child1.id)
        child2 = Task.objects.get(id=child2.id)

        self.assertEquals(child1.state, TASK_STATES['CANCELED'])
        self.assertEquals(child2.state, TASK_STATES['CANCELED'])

    def test_resubmit_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FAILED'],
        )

        task_id = task.resubmit_task(self._user)
        self.assertTrue(task_id > 0)

        new_task = Task.objects.get(id=task_id)
        self.assertEquals(new_task.owner.id, task.owner.id)
        self.assertEquals(new_task.method, task.method)
        self.assertEquals(new_task.resubmitted_from.id, task.id)

    def test_resubmit_task_that_is_not_failed(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['CLOSED'],
        )

        with self.assertRaises(Exception):
            task.resubmit_task(self._user)

    def test_resubmit_task_force_task_that_is_not_failed(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['CLOSED'],
        )

        task_id = task.resubmit_task(self._user, True)
        self.assertTrue(task_id > 0)

        new_task = Task.objects.get(id=task_id)
        self.assertEquals(new_task.owner.id, task.owner.id)
        self.assertEquals(new_task.method, task.method)
        self.assertEquals(new_task.resubmitted_from.id, task.id)

    def test_resubmit_task_that_is_exclusive(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FAILED'],
            exclusive=True,
        )

        with self.assertRaises(Exception):
            task.resubmit_task(self._user)

    def test_clone_task(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FAILED'],
        )

        task_id = task.clone_task(self._user)
        self.assertTrue(task_id > 0)

        new_task = Task.objects.get(id=task_id)
        self.assertEquals(new_task.owner.id, task.owner.id)
        self.assertEquals(new_task.method, task.method)
        self.assertEquals(new_task.resubmitted_from.id, task.id)

    def test_clone_task_if_not_superuser(self):
        user = User.objects.create(username='user-non-admin')

        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=user,
            method='DummyTask',
            state=TASK_STATES['FAILED'],
        )

        with self.assertRaises(Exception):
            task.clone_task(user)

    def test_clone_task_that_is_not_top_level(self):
        parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['ASSIGNED'],
        )

        child = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['FAILED'],
            parent=parent
        )

        with self.assertRaises(Exception):
            child.clone_task(self._user)

    def test_wait(self):
        parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['ASSIGNED'],
        )

        child1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['ASSIGNED'],
            parent=parent,
        )

        child2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['ASSIGNED'],
            parent=parent,
        )

        parent.wait([child1.id])

        parent = Task.objects.get(id=parent.id)
        child1 = Task.objects.get(id=child1.id)
        child2 = Task.objects.get(id=child2.id)

        self.assertEquals(parent.waiting, True)
        self.assertEquals(parent.awaited, False)

        self.assertEquals(child1.waiting, False)
        self.assertEquals(child1.awaited, True)

        self.assertEquals(child2.waiting, False)
        self.assertEquals(child2.awaited, False)

    def test_check_wait_subtasks_finished(self):
        parent = Task.objects.create(
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
            parent=parent,
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['CLOSED'],
            parent=parent,
        )

        finished, unfinished = parent.check_wait()
        self.assertEqual(len(finished), 2)
        self.assertEqual(len(unfinished), 0)

    def test_check_wait_subtasks_with_filter(self):
        parent = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['OPEN'],
        )

        child = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['CLOSED'],
            parent=parent,
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['CLOSED'],
            parent=parent,
        )

        finished, unfinished = parent.check_wait([child.id])
        self.assertEqual(len(finished), 1)
        self.assertEqual(len(unfinished), 0)

    def test_check_wait_subtasks_not_finished(self):
        parent = Task.objects.create(
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
            parent=parent,
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            state=TASK_STATES['FREE'],
            parent=parent,
        )

        finished, unfinished = parent.check_wait()
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

        finished, unfinished = t.check_wait()
        self.assertEqual(len(finished), 0)
        self.assertEqual(len(unfinished), 0)

    def test_task_delete(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='DummyTask',
            state=TASK_STATES['ASSIGNED'],
        )

        task_dir = task.task_dir()

        with patch('kobo.hub.models.shutil') as shutil_mock:
            task.delete()

            shutil_mock.rmtree.assert_called_once_with(task_dir)
