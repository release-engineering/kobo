# -*- coding: utf-8 -*-

import unittest

from mock import Mock, PropertyMock, patch

from kobo.hub import middleware


class DummyRequest(object):
    pass


class DummyWorker(object):

    def __init__(self, name=None):
        self.name = name


class TestGetWorker(unittest.TestCase):

    def test_get_worker(self):
        with patch('kobo.hub.middleware.Worker') as worker_mock:
            worker_mock.objects.get.return_value = DummyWorker()
            req = PropertyMock(user=PropertyMock(username='foo/bar'))
            worker = middleware.get_worker(req)
            self.assertIsInstance(worker, DummyWorker)
            worker_mock.objects.get.assert_called_once_with(name='bar')

    def test_get_worker_missing_hostname(self):
        req = PropertyMock(user=PropertyMock(username='username'))
        worker = middleware.get_worker(req)
        self.assertIsNone(worker)

    def test_get_worker_catch_exceptions(self):
        req = PropertyMock(user=Mock(side_effect=ValueError))
        worker = middleware.get_worker(req)
        self.assertIsNone(worker)


class TestLazyWorker(unittest.TestCase):

    def test_lazy_worker_set_cache_variable_if_not_set(self):
        with patch('kobo.hub.middleware.get_worker', return_value=DummyWorker()) as get_worker_mock:
            req = PropertyMock(
                spec=['user'],
                user=PropertyMock(username='foo/bar'),
            )

            cached_worker = middleware.LazyWorker().__get__(req)
            self.assertIsInstance(cached_worker, DummyWorker)

            get_worker_mock.assert_called_once_with(req)

    def test_lazy_worker_do_not_set_cache_variable_if_already_set(self):
        with patch('kobo.hub.middleware.get_worker', return_value=DummyWorker('new-worker')) as get_worker_mock:
            req = PropertyMock(
                spec=['user', '_cached_worker'],
                user=PropertyMock(username='foo/bar'),
                _cached_worker=DummyWorker('cached-worker'),
            )

            cached_worker = middleware.LazyWorker().__get__(req)
            self.assertIsInstance(cached_worker, DummyWorker)
            self.assertEqual(cached_worker.name, 'cached-worker')

            get_worker_mock.assert_not_called()


class TestWorkerMiddleware(unittest.TestCase):

    def test_process_request(self):
        with patch('kobo.hub.middleware.get_worker', return_value=DummyWorker()) as get_worker_mock:
            req = DummyRequest()
            req.user = PropertyMock(username='foo/bar')

            middleware.WorkerMiddleware().process_request(req)
            self.assertIsInstance(req.worker, DummyWorker)
            get_worker_mock.assert_called_once_with(req)

    def test_process_request_missing_user(self):
        req = DummyRequest()

        with self.assertRaises(AssertionError):
            middleware.WorkerMiddleware().process_request(req)
