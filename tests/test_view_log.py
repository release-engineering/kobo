import sys
import os
import json

from gzip import GzipFile
from StringIO import StringIO
from shutil import rmtree

import django
import django.conf
import django.test
from django.test.utils import get_runner

# Only for Django >= 1.7
if 'setup' in dir(django):
    # This has to happen before below imports because they have a hard requirement
    # on settings being loaded before import.
    django.setup()

from kobo.hub.models import Task, Arch, Channel
from kobo.hub import views
from django.contrib.auth.models import User

TASK_ID = 123

def small_log_content():
    """Returns content for a small log, where small means able to fit into
    a single chunk (of whatever chunking scheme might be in use)."""
    return '\n'.join([
        'Line 1 of test log',
        'Line 2 of test log',
    ])


def html_content():
    """Content suitable for an HTML formatted log."""
    return '<html>This is some HTML content</html>'


def response_content(response):
    """Get all the content from an HttpResponse (eagerly loaded if the
    response is streaming)."""
    if response.streaming:
        return b''.join(response.streaming_content)
    else:
        return response.content


def gzip_decompress(data):
    """Like zlib.decompress but handles the gzip header, so it can be used
    on gzipped log files."""
    io = StringIO(data)
    gzfile = GzipFile(fileobj=io)
    return gzfile.read()


class TestViewLog(django.test.TestCase):
    def cleanDataDirs(self):
        """Delete the log directory for the test task."""
        log_dir = os.path.join(django.conf.settings.TASK_DIR, '0', '0', str(TASK_ID))
        if os.path.exists(log_dir):
            rmtree(log_dir)

    def tearDown(self):
        self.cleanDataDirs()

        super(TestViewLog, self).tearDown()

    def setUp(self):
        super(TestViewLog, self).setUp()

        self.cleanDataDirs()

        # These objects are required to exist but their attributes are irrelevant
        user = User.objects.create()
        arch = Arch.objects.create(name='testarch')
        channel = Channel.objects.create(name='testchannel')

        test_task = Task.objects.create(
            pk=TASK_ID, arch=arch, channel=channel, owner=user)

        # associate some compressed and decompressed logs with the task.
        # (the save and gzip_logs methods here are writing files to disk)
        test_task.logs['zipped_small.log'] = small_log_content()
        test_task.logs.save()
        test_task.logs.gzip_logs()

        test_task.logs['small.log'] = small_log_content()
        test_task.logs['log.html'] = html_content()
        test_task.logs.save()

        self.client = django.test.Client()

    def test_view_zipped_small_raw(self):
        """Fetching a small compressed log with raw format should yield
        the gzip-compressed content."""
        response, content = self.assertGetLog(
            'zipped_small.log',
            data={'format': 'raw'},
        )

        uncompressed_content = gzip_decompress(content)
        self.assertEqual(uncompressed_content, small_log_content())

    def test_view_small_raw_offset(self):
        """Fetching a small log with an offset should return only the
        content from that offset to the end of the log."""
        full_content = small_log_content()

        offset = 10

        self.assertGetLog(
            'small.log',
            data={'format': 'raw', 'offset': offset},
            expected_content=full_content[offset:]
        )

    def test_view_html_passthrough(self):
        """Fetching an HTML log yields exactly the HTML content,
        not wrapped in any template (even if format: raw is not requested)."""
        self.assertGetLog(
            'log.html',
            expected_content=html_content()
        )

    def test_view_html_wrapped(self):
        """In the typical case of fetching a small plaintext log with no
        specified format, the log's text is wrapped in an HTML view."""
        response, content = self.assertGetLog(
            'small.log',
            # Django-rendered template responses are not including
            # Content-Length
            test_content_length=False,
        )

        # The response is expected to be wrapped in some view.
        # We are only doing a very basic verification of the view here
        self.assertTrue(content.startswith('<!DOCTYPE html'))
        self.assertTrue((small_log_content() + "\n</pre>") in content, content)

    def test_view_zipped_small_json(self):
        """Fetching compressed small log via JSON gives expected document."""
        response, content = self.assertGetLog(
            'zipped_small.log',
            view_type='log-json',
            test_content_length=False,
        )
        expected_content = small_log_content()
        doc = json.loads(content)
        self.assertEqual(doc, {
            'content': expected_content,
            'new_offset': len(expected_content),
            'task_finished': 0,
        })

    def test_view_small_json(self):
        """As test_view_zipped_small_json, but log is uncompressed.
        Otherwise identical, i.e. compression is expected to be handled
        transparently."""
        response, content = self.assertGetLog(
            'small.log',
            view_type='log-json',
            test_content_length=False,
        )
        expected_content = small_log_content()
        doc = json.loads(content)
        self.assertEqual(doc, {
            'content': expected_content,
            'new_offset': len(expected_content),
            'task_finished': 0,
        })

    def test_view_small_json_offset(self):
        """Fetching log with offset via JSON returns only the content
        starting from that offset."""
        full_content = small_log_content()
        offset = 10
        expected_content = full_content[offset:]

        response, content = self.assertGetLog(
            'small.log',
            view_type='log-json',
            test_content_length=False,
            data={'offset': offset}
        )

        doc = json.loads(content)
        self.assertEqual(doc, {
            'content': expected_content,
            'new_offset': offset + len(expected_content),
            'task_finished': 0,
        })


    def assertGetLog(self, log_name, view_type='log', test_content_length=True,
                     expected_content=None, data={}):
        """Verify log can be successfully retrieved and response has certain properties.
        The HttpResponse and its content are returned so that tests may do further
        assertions."""
        url = '/task/{0}/{1}/{2}'.format(TASK_ID, view_type, log_name)
        response = self.client.get(url, data)
        content = response_content(response)

        # Should always succeed
        self.assertEqual(response.status_code, 200)

        if expected_content:
            # Should be exactly this content
            # (if not provided, caller is expected to do custom verification)
            self.assertEqual(content, expected_content)

        # Content-Length is optional, but if present, must be correct
        if test_content_length or ('Content-Length' in response):
            self.assertEqual(response['Content-Length'], str(len(content)))

        return response, content


if __name__ == '__main__':
    TestRunner = get_runner(django.conf.settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests([__name__])
    sys.exit(bool(failures))
