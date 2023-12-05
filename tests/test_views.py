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
        self.credentials = {
            'username': 'user1',
            'password': 'test'}
        self.user = User.objects.create_user(**self.credentials)
        self.client = django.test.Client()

    def test_login(self):
        response = self.client.get('/auth/login/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get("_auth_user_id"))
        response = self.client.post('/auth/login/', self.credentials)
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(self.client.session.get("_auth_user_id"))

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
        response = self.client.post('/auth/logout/')
        self.assertIn(response.status_code, [200, 302])
        self.client.post('/auth/login/', self.credentials)
        self.client.logout()
        self.assertFalse(self.client.session.get("_auth_user_id"))


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

    def test_list_failed(self):
        response = self.client.get('/task/failed/')
        self.assertEqual(response.status_code, 200)
        # make sure only failed tasks are listed
        self.assertTrue(self.task1.get_state_display() not in str(response.content))
        self.assertTrue(self.task2.get_state_display() not in str(response.content))
        self.assertTrue(self.task3.get_state_display() not in str(response.content))
        self.assertTrue(self.task4.get_state_display() in str(response.content))

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

    def _create_user(self, username, password="test", is_staff=False):
        user = User.objects.create(username=username)
        user.set_password(password)
        user.is_staff = is_staff
        user.save()

        return user

    def setUp(self):
        self._fixture_teardown()
        self.user1 = self._create_user("user1")
        self.user2 = self._create_user("user2")
        self.staff_user = self._create_user("user3", is_staff=True)

        self.client = django.test.Client()

    # nothing will be impacted if `USERS_ACL_PERMISSION` is not available
    # in settings or is an empty string
    @override_settings(USERS_ACL_PERMISSION="")
    def test_list(self):
        response = self.client.get('/info/user/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user1.username in str(response.content))
        self.assertTrue(self.user2.username in str(response.content))

    @override_settings(USERS_ACL_PERMISSION="")
    def test_detail(self):
        response = self.client.get('/info/user/%d/' % self.user1.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('#%d: %s' % (self.user1.id, self.user1.username) in str(response.content))

    @override_settings(USERS_ACL_PERMISSION="authenticated")
    def test_authenticated_access_user_list(self):
        response = self.client.get('/info/user/')
        self.assertEqual(response.status_code, 403)
        # user should have access once logged in
        self.client.login(username=self.user1.username, password="test")
        response = self.client.get('/info/user/')
        self.assertEqual(response.status_code, 200)

    @override_settings(USERS_ACL_PERMISSION="authenticated")
    def test_authenticated_access_user_detail(self):
        response = self.client.get('/info/user/%d/' % self.user1.id)
        self.assertEqual(response.status_code, 403)
        self.client.login(username=self.user1.username, password="test")
        response = self.client.get('/info/user/%d/' % self.user1.id)
        self.assertEqual(response.status_code, 200)

    @override_settings(USERS_ACL_PERMISSION="staff")
    def test_staff_access_user_list(self):
        response = self.client.get('/info/user/')
        self.assertEqual(response.status_code, 403)
        # no access for authenticated user
        self.client.login(username=self.user1.username, password="test")
        response = self.client.get('/info/user/')
        self.assertEqual(response.status_code, 403)
        self.client.login(username=self.staff_user.username, password="test")
        response = self.client.get('/info/user/')
        self.assertEqual(response.status_code, 200)

    @override_settings(USERS_ACL_PERMISSION="staff")
    def test_staff_access_user_detail(self):
        user_detail_url = '/info/user/%d/' % self.user2.id
        response = self.client.get(user_detail_url)
        self.assertEqual(response.status_code, 403)
        self.client.login(username=self.user1.username, password="test")
        response = self.client.get(user_detail_url)
        self.assertEqual(response.status_code, 403)
        self.client.login(username=self.staff_user.username, password="test")
        response = self.client.get(user_detail_url)
        self.assertEqual(response.status_code, 200)


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
