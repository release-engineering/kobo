# -*- coding: utf-8 -*-

import unittest

from mock import Mock, PropertyMock

from kobo.exceptions import ShutdownException
from kobo.worker.tasks.task_shutdown_worker import ShutdownWorker

class TestShutdownWorker(unittest.TestCase):

    def test_run(self):
        t = ShutdownWorker(Mock(spec=['worker']), {}, 100, {})

        t.task_manager = PropertyMock(locked=False)
        self.assertFalse(t.task_manager.locked)

        t.run()
        self.assertTrue(t.task_manager.locked)

    def test_run_kill(self):
        t = ShutdownWorker(Mock(spec=['worker']), {}, 100, {'kill': True})

        t.task_manager = PropertyMock(locked=False)
        self.assertFalse(t.task_manager.locked)

        with self.assertRaises(ShutdownException):
            t.run()

        self.assertFalse(t.task_manager.locked)
