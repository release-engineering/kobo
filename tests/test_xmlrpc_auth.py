# -*- coding: utf-8 -*-

import django

from django.core.exceptions import PermissionDenied
from mock import Mock, patch

from kobo.hub.models import Worker
from kobo.hub.xmlrpc import auth
from kobo.django.django_version import django_version_ge

from .utils import DjangoRunner

runner = DjangoRunner()
setup_module = runner.start
teardown_module = runner.stop


class TestLoginWorker(django.test.TransactionTestCase):

    def test_login_worker_key_valid_worker_and_user(self):
        def login(request, user):
            request.session.session_key = '1234567890'
            return user

        Worker.objects.create(worker_key='key', name='name')

        req = Mock(spec=['session'], session=Mock())
        user = Mock()
        krb_mock = Mock(spec=['authenticate'], authenticate=Mock(return_value=user))

        with patch('kobo.hub.xmlrpc.auth.Krb5RemoteUserBackend', return_value=krb_mock):
            with patch.object(auth.django.contrib.auth, 'login', side_effect=login) as login_mock:
                session_key = auth.login_worker_key(req, 'key')

                login_mock.assert_called_once_with(req, user)
        if django_version_ge('1.11.0'):
            krb_mock.authenticate.assert_called_once_with(None, 'worker/name')
        else:
            krb_mock.authenticate.assert_called_once_with('worker/name')
        self.assertEqual(session_key, '1234567890')

    def test_login_worker_key_valid_worker_invalid_user(self):
        Worker.objects.create(worker_key='key', name='name')
        req = Mock(spec=['session'], session=Mock())
        krb_mock = Mock(spec=['authenticate'], authenticate=Mock(return_value=None))

        with patch('kobo.hub.xmlrpc.auth.Krb5RemoteUserBackend', return_value=krb_mock):
            with self.assertRaises(PermissionDenied):
                auth.login_worker_key(req, 'key')

        if django_version_ge('1.11.0'):
            krb_mock.authenticate.assert_called_once_with(None, 'worker/name')
        else:
            krb_mock.authenticate.assert_called_once_with('worker/name')

    def test_login_worker_key_invalid_worker(self):
        req = Mock()

        with self.assertRaises(PermissionDenied):
            auth.login_worker_key(req, 'key')
