# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .models import Worker


def get_worker(request):
    try:
        if "/" not in request.user.username:
            return None

        hostname = request.user.username.split("/")[1]
        worker = Worker.objects.get(name=hostname)
        return worker
    except:
        return None


class LazyWorker(object):
    def __get__(self, request, obj_type=None):
        if not hasattr(request, "_cached_worker"):
            request._cached_worker = get_worker(request)
        return request._cached_worker


class WorkerMiddleware():
    """Sets a request.worker.

    - Worker instance if username exists in database
    - None otherwise
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.process_request(request)
        response = self.get_response(request)
        return response

    def process_request(self, request):
        assert hasattr(request, "user"), "Worker middleware requires authentication middleware to be installed. Also make sure the database is set and writable."
        request.__class__.worker = LazyWorker()
        return None
