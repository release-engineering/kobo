# -*- coding: utf-8 -*-

import django

# Only for Django >= 1.7
if 'setup' in dir(django):
    # This has to happen before below imports because they have a hard requirement
    # on settings being loaded before import.
    django.setup()

from django.contrib.auth.models import User
from mock import Mock, PropertyMock

from kobo.client.constants import TASK_STATES
from kobo.hub.models import Arch, Channel, Task, Worker
from kobo.hub.forms import TaskSearchForm

from .utils import DjangoRunner

runner = DjangoRunner()
setup_module = runner.start
teardown_module = runner.stop


class TestTaskSearchForm(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        user = User.objects.create(username='testuser')
        user2 = User.objects.create(username='anothertestuser')
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
        self._user2 = user2
        self._worker = w

    def test_get_query_search_filter_authenticated(self):
        task = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 1',
            state=TASK_STATES['FREE'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 2',
            state=TASK_STATES['OPEN'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user2,
            method='TaskMethod',
            label='Task 3',
            state=TASK_STATES['FREE'],
        )

        post = {'my': True, 'search': 'TaskMethod'}
        form = TaskSearchForm(post, state=[TASK_STATES['FREE']])

        valid = form.is_valid()
        self.assertTrue(valid)

        req = PropertyMock(spec=['user'], user=self._user)
        tasks = form.get_query(req)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, task.id)

    def test_get_query_search_filter_not_authenticated(self):
        task1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 1',
            state=TASK_STATES['FREE'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 2',
            state=TASK_STATES['OPEN'],
        )

        task3 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user2,
            method='TaskMethod',
            label='Task 3',
            state=TASK_STATES['FREE'],
        )

        post = {'my': True, 'search': 'TaskMethod'}
        form = TaskSearchForm(post, state=[TASK_STATES['FREE']])

        valid = form.is_valid()
        self.assertTrue(valid)

        req = PropertyMock(spec=['user'], user=Mock(is_authenticated=Mock(return_value=False)))
        tasks = form.get_query(req)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, task3.id)
        self.assertEqual(tasks[1].id, task1.id)

    def test_get_query_search_filter_authenticated_not_mine(self):
        task1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 1',
            state=TASK_STATES['FREE'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 2',
            state=TASK_STATES['OPEN'],
        )

        task3 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user2,
            method='TaskMethod',
            label='Task 3',
            state=TASK_STATES['FREE'],
        )

        post = {'my': False, 'search': 'TaskMethod'}
        form = TaskSearchForm(post, state=[TASK_STATES['FREE']])

        valid = form.is_valid()
        self.assertTrue(valid)

        req = PropertyMock(spec=['user'], user=self._user)
        tasks = form.get_query(req)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, task3.id)
        self.assertEqual(tasks[1].id, task1.id)

    def test_get_query_search_filter_authenticated_without_state_filter(self):
        task1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 1',
            state=TASK_STATES['FREE'],
        )

        task2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 2',
            state=TASK_STATES['OPEN'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user2,
            method='TaskMethod',
            label='Task 3',
            state=TASK_STATES['FREE'],
        )

        post = {'my': True, 'search': 'TaskMethod'}
        form = TaskSearchForm(post, state=None)

        valid = form.is_valid()
        self.assertTrue(valid)

        req = PropertyMock(spec=['user'], user=self._user)
        tasks = form.get_query(req)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, task2.id)
        self.assertEqual(tasks[1].id, task1.id)

    def test_get_query_search_no_filter_authenticated(self):
        task1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 1',
            state=TASK_STATES['FREE'],
        )

        task2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 2',
            state=TASK_STATES['OPEN'],
        )

        Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user2,
            method='TaskMethod',
            label='Task 3',
            state=TASK_STATES['FREE'],
        )

        post = {'my': True, 'search': ''}
        form = TaskSearchForm(post, state=None)

        valid = form.is_valid()
        self.assertTrue(valid)

        req = PropertyMock(spec=['user'], user=self._user)
        tasks = form.get_query(req)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, task2.id)
        self.assertEqual(tasks[1].id, task1.id)

    def test_get_query_search_no_filter_not_authenticated(self):
        task1 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 1',
            state=TASK_STATES['FREE'],
        )

        task2 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user,
            method='TaskMethod',
            label='Task 2',
            state=TASK_STATES['OPEN'],
        )

        task3 = Task.objects.create(
            worker=self._worker,
            arch=self._arch,
            channel=self._channel,
            owner=self._user2,
            method='TaskMethod',
            label='Task 3',
            state=TASK_STATES['FREE'],
        )

        post = {'my': True, 'search': ''}
        form = TaskSearchForm(post, state=None)

        valid = form.is_valid()
        self.assertTrue(valid)

        req = PropertyMock(spec=['user'], user=Mock(is_authenticated=Mock(return_value=False)))
        tasks = form.get_query(req)
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0].id, task3.id)
        self.assertEqual(tasks[1].id, task2.id)
        self.assertEqual(tasks[2].id, task1.id)
