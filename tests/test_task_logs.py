#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import pytest

from shutil import rmtree

import django.conf
import django.test
from django.test.utils import get_runner
from django.shortcuts import get_object_or_404

from kobo.hub.models import Task, Arch, Channel
from django.contrib.auth.models import User

from .utils import DjangoRunner

runner = DjangoRunner()
setup_module = runner.start
teardown_module = runner.stop

TASK_ID = 123

class TestTaskLogs(django.test.TransactionTestCase):
    def cleanDataDirs(self):
        """Delete the log directory for the test task."""
        log_dir = os.path.join(django.conf.settings.TASK_DIR, '0', '0', str(TASK_ID))
        if os.path.exists(log_dir):
            rmtree(log_dir)

    def tearDown(self):
        self.cleanDataDirs()

        super(TestTaskLogs, self).tearDown()

    def setUp(self):
        self._fixture_teardown()
        super(TestTaskLogs, self).setUp()

        self.cleanDataDirs()

        # These objects are required to exist but their attributes are irrelevant
        user = User.objects.create()
        arch = Arch.objects.create(name='testarch')
        channel = Channel.objects.create(name='testchannel')

        test_task = Task.objects.create(
            pk=TASK_ID, arch=arch, channel=channel, owner=user)

        self.log_content = log_content = b'Line 1 \xe2\x98\xba\nLine 2 \xe2\x98\xba\nLine 3'

        test_task.logs['test_compressed.log'] = log_content
        test_task.logs.save()
        test_task.logs.gzip_logs()

        test_task.logs['test.log'] = log_content
        test_task.logs.save()

    def task_logs(self):
        return get_object_or_404(Task, id=TASK_ID).logs

    def test_read_log_typical(self):
        task_logs = self.task_logs()
        log_content = task_logs['test.log']
        self.assertEqual(log_content, self.log_content)

        # It should be in the cache
        self.assertEqual(log_content, task_logs.cache['test.log'])

    def test_read_log_compressed(self):
        task_logs = self.task_logs()

        log_content = task_logs['test_compressed.log']
        self.assertEqual(log_content, self.log_content)

        # It should be in the cache
        self.assertEqual(log_content, task_logs.cache['test_compressed.log'])

    def test_get_chunk_missing(self):
        do_call = lambda: self.task_logs().get_chunk('notexist.log')
        self.assertRaises(Exception, do_call)

    def test_get_chunk_all(self):
        self.assertEqual(self.task_logs().get_chunk('test.log'), self.log_content)

    def test_get_chunk_offset(self):
        chunk = self.task_logs().get_chunk('test.log', offset=len(b'Line 1 \xe2\x98\xba\n'))
        self.assertEqual(chunk, b'Line 2 \xe2\x98\xba\nLine 3')

    def test_get_chunk_offset_len(self):
        self.do_chunk_offset_len_test('test.log')
        self.do_chunk_offset_len_test('test_compressed.log')

    def do_chunk_offset_len_test(self, log_name):
        chunk = self.task_logs().get_chunk(log_name, offset=1, length=2)
        self.assertEqual(chunk, b'in')

    def test_chunk_offset_len_from_cache(self):
        task_logs = self.task_logs()

        # First, read the entire log.
        self.assertEqual(self.log_content, task_logs['test.log'])

        # Now, if I request a chunk, it comes directly from the cache
        # rather than reading from disk again, proven by deleting
        # the log dir before requesting chunk
        self.cleanDataDirs()

        chunk = task_logs.get_chunk('test.log', offset=1, length=2)
        self.assertEqual(chunk, b'in')

    def test_get_chunk_offset_within_char(self):
        self.do_chunk_offset_within_char_test('test.log')
        self.do_chunk_offset_within_char_test('test_compressed.log')

    def do_chunk_offset_within_char_test(self, log_name):
        task_logs = self.task_logs()
        offset = self.log_content.index(b'\n') + 1
        expected_chunk = b'Line 2 \xe2\x98\xba'
        byteslen = len(expected_chunk)

        # ☺ character requires three bytes to encode; see what happens if we try to read
        # within that char

        full_chunk = task_logs.get_chunk(log_name, offset=offset, length=byteslen)
        chunk_min1 = task_logs.get_chunk(log_name, offset=offset, length=byteslen-1)
        chunk_min2 = task_logs.get_chunk(log_name, offset=offset, length=byteslen-2)
        chunk_min3 = task_logs.get_chunk(log_name, offset=offset, length=byteslen-3)

        # reading entirety of character should be fine
        self.assertEqual(full_chunk, expected_chunk)

        # reading prior to character should be fine
        self.assertEqual(chunk_min3, b'Line 2 ')

        # these two requests to read within the character should have truncated and
        # given the same result as reading prior to the character
        self.assertEqual(chunk_min1, chunk_min3)
        self.assertEqual(chunk_min2, chunk_min3)
