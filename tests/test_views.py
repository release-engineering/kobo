# -*- coding: utf-8 -*-

import django

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured

try:
    from django.test import override_settings
except:
    # Django <= 1.6
    from django.test.utils import override_settings

from mock import Mock, PropertyMock, patch

from kobo.client.constants import TASK_STATES
from kobo.hub.models import Arch, Channel, Task, Worker

from .utils import DjangoRunner

runner = DjangoRunner()
setup_module = runner.start
teardown_module = runner.stop


class TestAuthView(django.test.TransactionTestCase):

    def setUp(self):
        self.client = django.test.Client()

    def test_login(self):
        response = self.client.get('/auth/login/')
        self.assertEqual(response.status_code, 200)

    def test_krb5login(self):
        response = self.client.get('/auth/krb5login/')
        self.assertEqual(response.status_code, 301)
        self.assertIn(response['Location'], ['http://testserver/home/', '/home/'])

    @override_settings(MIDDLEWARE_CLASSES=[], MIDDLEWARE=[])
    def test_krb5login_missing_middleware(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.get('/auth/krb5login/')

    def test_krb5login_redirect_to(self):
        response = self.client.get('/auth/krb5login/', {REDIRECT_FIELD_NAME: '/auth/login/'})
        self.assertEqual(response.status_code, 301)
        self.assertIn(response['Location'], ['http://testserver/auth/login/', '/auth/login/'])

    def test_logout(self):
        response = self.client.get('/auth/logout/')
        self.assertEqual(response.status_code, 200)


class TestTaskView(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        user = User.objects.create(username='testuser')
        arch = Arch.objects.create(name='testarch')
        channel = Channel.objects.create(name='testchannel')
        worker = Worker.objects.create(
            worker_key='mock-worker',
            name='mock-worker',
        )

        worker.arches.add(arch)
        worker.channels.add(channel)
        worker.save()

        self.task1 = Task.objects.create(
            worker=worker,
            arch=arch,
            channel=channel,
            owner=user,
            method='TaskOne',
            state=TASK_STATES['FREE'],
        )

        self.task2 = Task.objects.create(
            worker=worker,
            arch=arch,
            channel=channel,
            owner=user,
            method='TaskTwo',
            state=TASK_STATES['OPEN'],
        )

        self.task3 = Task.objects.create(
            worker=worker,
            arch=arch,
            channel=channel,
            owner=user,
            method='TaskThree',
            state=TASK_STATES['CLOSED'],
        )

        self.task4 = Task.objects.create(
            worker=worker,
            arch=arch,
            channel=channel,
            owner=user,
            method='TaskFour',
            state=TASK_STATES['FAILED'],
        )

        self.client = django.test.Client()

    def test_list(self):
        response = self.client.get('/task/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.task1.method in str(response.content))
        self.assertTrue(self.task2.method in str(response.content))
        self.assertTrue(self.task3.method in str(response.content))
        self.assertTrue(self.task4.method in str(response.content))

    def test_list_running(self):
        response = self.client.get('/task/running/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.task1.method in str(response.content))
        self.assertTrue(self.task2.method in str(response.content))
        self.assertTrue(self.task3.method not in str(response.content))
        self.assertTrue(self.task4.method not in str(response.content))

    def test_list_finished(self):
        response = self.client.get('/task/finished/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.task1.method not in str(response.content))
        self.assertTrue(self.task2.method not in str(response.content))
        self.assertTrue(self.task3.method in str(response.content))
        self.assertTrue(self.task4.method in str(response.content))

    def test_detail(self):
        response = self.client.get('/task/%d/' % self.task1.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('#%d: %s' % (self.task1.id, self.task1.method) in str(response.content))


class TestArchView(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        self.arch1 = Arch.objects.create(name='arch-1', pretty_name='arch-1')
        self.arch2 = Arch.objects.create(name='arch-2', pretty_name='arch-2')

        self.client = django.test.Client()

    def test_list(self):
        response = self.client.get('/info/arch/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.arch1.name in str(response.content))
        self.assertTrue(self.arch2.name in str(response.content))

    def test_detail(self):
        response = self.client.get('/info/arch/%d/' % self.arch1.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('#%d: %s' % (self.arch1.id, self.arch1.name) in str(response.content))


class TestChannelView(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        self.channel1 = Channel.objects.create(name='channel-1')
        self.channel2 = Channel.objects.create(name='channel-2')

        self.client = django.test.Client()

    def test_list(self):
        response = self.client.get('/info/channel/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.channel1.name in str(response.content))
        self.assertTrue(self.channel2.name in str(response.content))

    def test_detail(self):
        response = self.client.get('/info/channel/%d/' % self.channel1.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('#%d: %s' % (self.channel1.id, self.channel1.name) in str(response.content))


class TestUserView(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        self.user1 = User.objects.create(username='user-1')
        self.user2 = User.objects.create(username='user-2')

        self.client = django.test.Client()

    def test_list(self):
        response = self.client.get('/info/user/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user1.username in str(response.content))
        self.assertTrue(self.user2.username in str(response.content))

    def test_detail(self):
        response = self.client.get('/info/user/%d/' % self.user1.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('#%d: %s' % (self.user1.id, self.user1.username) in str(response.content))


class TestWorkerView(django.test.TransactionTestCase):

    def setUp(self):
        self._fixture_teardown()
        self.worker1 = Worker.objects.create(
            worker_key='worker-1',
            name='worker-1',
        )

        self.worker2 = Worker.objects.create(
            worker_key='worker-2',
            name='worker-2',
        )

        self.client = django.test.Client()

    def test_list(self):
        response = self.client.get('/info/worker/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.worker1.name in str(response.content))
        self.assertTrue(self.worker2.name in str(response.content))

    def test_detail(self):
        response = self.client.get('/info/worker/%d/' % self.worker1.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('#%d: %s' % (self.worker1.id, self.worker1.name) in str(response.content))
