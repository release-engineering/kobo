import gc
import itertools
import json
import locale
import os

from tempfile import TemporaryFile
from gzip import GzipFile
from io import BytesIO
from shutil import rmtree

import mock
import six

import django.conf
import django.test

from django.http import HttpResponse

from django.contrib.auth.models import User

from kobo.hub.models import Task, Arch, Channel, TASK_STATES

from .utils import DjangoRunner, profile

runner = DjangoRunner()
setup_module = runner.start
teardown_module = runner.stop

TASK_ID = 123


def tiny_log_content():
    """Returns very small log content.  Particularly, small enough that
    gzip-compressing will *increase* the content size."""
    return 'hi!'


def small_log_content():
    """Returns content for a small log, where small means able to fit into
    a single chunk (of whatever chunking scheme might be in use)."""
    return '\n'.join([
        'Line 1 of test log',
        'Line 2 of test log',
    ])


def big_log_content():
    """Returns content for a big log likely to span multiple chunks."""
    out = 'some log content'
    i = 1
    while len(out) < (1024**2) * 20:
        out = ('\njoin %d\n' % i).join([out, out])
        i = i + 1
    return ''.join(['BEGIN LOG\n', out, 'END LOG\n'])


def html_content():
    """Content suitable for an HTML formatted log."""
    return '<html>This is some HTML content</html>'


def response_content(response):
    """Get all the content from an HttpResponse (eagerly loaded if the
    response is streaming)."""
    if response.streaming:
        content = b''.join(response.streaming_content)
    else:
        content = response.content

    if six.PY3:
        try:
            return str(content, encoding=response.charset)
        except UnicodeDecodeError:
            return content
    else:
        return content


def gzip_decompress(data):
    """Like zlib.decompress but handles the gzip header, so it can be used
    on gzipped log files."""
    io = BytesIO(data)
    gzfile = GzipFile(fileobj=io)
    return gzfile.read()


class TestViewLog(django.test.TransactionTestCase):
    def __init__(self, *args, **kwargs):
        super(TestViewLog, self).__init__(*args, **kwargs)
        # This is cached since it is a bit slow to build
        self.big_log_content = big_log_content()

    def cleanDataDirs(self):
        """Delete the log directory for the test task."""
        log_dir = os.path.join(django.conf.settings.TASK_DIR, '0', '0', str(TASK_ID))
        if os.path.exists(log_dir):
            rmtree(log_dir)

    def tearDown(self):
        self.cleanDataDirs()

        super(TestViewLog, self).tearDown()

    def setUp(self):
        self._fixture_teardown()
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
        test_task.logs['zipped_tiny.log'] = tiny_log_content()
        test_task.logs['zipped_small.log'] = small_log_content()
        test_task.logs['zipped_big.log'] = self.big_log_content
        test_task.logs.save()
        test_task.logs.gzip_logs()

        test_task.logs['small.log'] = small_log_content()
        test_task.logs['big.log'] = self.big_log_content
        test_task.logs['log.html'] = html_content()
        test_task.logs.save()

        self.client = django.test.Client()

        # for more accurate memory_profiler tests
        gc.collect()

    def test_view_zipped_small_raw(self):
        """Fetching a small compressed log with raw format should yield
        the gzip-compressed content."""
        response, content = self.assertGetLog(
            'zipped_small.log',
            data={'format': 'raw'},
        )

        uncompressed_content = gzip_decompress(content)
        if six.PY3:
            uncompressed_content = str(uncompressed_content,
                                       encoding=locale.getpreferredencoding())
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

        # No trimming necessary
        self.assertFalse('...trimmed, download required for full log' in content)

    def test_view_tiny_html_wrapped(self):
        """As typical case, but with a log file so small that the gzipped file
        is larger than the uncompressed content."""
        response, content = self.assertGetLog(
            'zipped_tiny.log',
            test_content_length=False,
        )

        self.assertTrue(content.startswith('<!DOCTYPE html'))
        self.assertTrue((tiny_log_content() + "\n</pre>") in content, content)
        self.assertFalse('...trimmed, download required for full log' in content)

    @profile
    def test_view_big_html_wrapped(self):
        response = self.get_log('big.log')
        self.assertEqual(response.status_code, 200, response)

        content = response.content
        if six.PY3:
            content = str(content, encoding=response.charset)
        self.assertTrue(content.startswith('<!DOCTYPE html'))

        # Should not have returned whole content
        self.assertTrue(len(content) < len(self.big_log_content))

        # Should tell the user that the response was trimmed
        self.assertTrue('&lt;...trimmed, download required for full log&gt;\n' in content)

        # Content should contain the end of the log file
        self.assertTrue(self.big_log_content[-5000:] in content)

        # Content should NOT contain the beginning of the log file
        self.assertFalse(self.big_log_content[0:5000] in content)

    @profile
    def test_view_big_html_wrapped_with_offset(self):
        # Just get the last 2000 chars - this should not trigger log trimming
        offset = len(big_log_content()) - 2000
        response = self.get_log('big.log', data={'offset': offset})

        content = response.content
        if six.PY3:
            content = str(content, encoding=response.charset)
        self.assertTrue(content.startswith('<!DOCTYPE html'))
        self.assertTrue(big_log_content()[-2000:] in content)

    @profile
    def test_view_zipped_big_html_context(self):
        """Verify the context passed into HTML template contains correct values."""
        def render(*args, **kwargs):
            return HttpResponse(status=200)

        with mock.patch('kobo.hub.views.render', side_effect=render) as render_mock:
            self.get_log('zipped_big.log')

        mock_call = render_mock.mock_calls[0]

        # make sure we're looking at the right call
        self.assertEqual(mock_call[0], '')

        call_args = mock_call[1]
        (_, template_name, context) = call_args

        self.assertEqual(template_name, 'task/log.html')

        # Check various things passed in context

        # The task is not yet completed
        self.assertEqual(context['task_finished'], 0)

        # It should ask log watcher to poll soon
        self.assertEqual(context['next_poll'], 5000)

        # Since it provided the end of the log content, it should give an offset
        # pointing just past the end
        self.assertEqual(context['offset'], len(self.big_log_content))

    @profile
    def test_view_big_raw(self):
        big_content = self.big_log_content
        offset = 0
        response = self.get_log('big.log', data={'format': 'raw'})
        self.assertEqual(response.status_code, 200, response)

        # Response should be streamed in chunks
        self.assertTrue(response.streaming)
        count = 0
        for chunk in response.streaming_content:
            chunklen = len(chunk)
            if six.PY3:
                chunk = str(chunk, encoding=locale.getpreferredencoding())
            self.assertEqual(chunk, big_content[offset:offset + chunklen])
            offset = offset + chunklen
            count = count + 1

        self.assertTrue(count > 1)

    @profile
    def test_view_zipped_big_raw(self):
        big_content = self.big_log_content

        response = self.get_log('zipped_big.log', data={'format': 'raw'})
        self.assertEqual(response.status_code, 200, response)

        # Response should be streamed in chunks, and once decompressed,
        # should be the expected content
        self.assertTrue(response.streaming)

        tempfile = TemporaryFile()

        for chunk in response.streaming_content:
            tempfile.write(chunk)

        tempfile.seek(0)
        gz_file = GzipFile(mode='r', fileobj=tempfile)
        all_data = gz_file.read()
        if six.PY3:
            all_data = str(all_data, encoding=locale.getpreferredencoding())
        self.assertEqual(all_data, big_content)

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
            'next_poll': 5000,
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
            'next_poll': 5000,
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
            'next_poll': 5000,
        })

    @profile
    def test_view_big_json(self):
        response, content = self.assertGetLog(
            'big.log',
            view_type='log-json',
            test_content_length=False,
        )
        doc = json.loads(content)

        # Should have given us a subset of the content and told us to poll
        # again soon
        self.assertTrue(doc['content'] in self.big_log_content)
        self.assertEqual(doc['new_offset'], len(doc['content'])),
        self.assertEqual(doc['task_finished'], 0)
        self.assertEqual(doc['next_poll'], 0)

    @profile
    def test_view_zipped_big_json(self):
        response, content = self.assertGetLog(
            'zipped_big.log',
            view_type='log-json',
            test_content_length=False,
        )
        doc = json.loads(content)

        self.assertTrue(doc['content'] in self.big_log_content)
        self.assertEqual(doc['new_offset'], len(doc['content'])),
        self.assertEqual(doc['task_finished'], 0)
        self.assertEqual(doc['next_poll'], 0)

    @profile
    def test_view_zipped_big_json_offset(self):
        offset = 20000
        response, content = self.assertGetLog(
            'zipped_big.log',
            view_type='log-json',
            test_content_length=False,
            data={'offset': offset}
        )
        doc = json.loads(content)

        # We're not verifying exactly how much we expect to be given, but we do expect it's
        # a subset of the available content
        content_len = len(doc['content'])
        self.assertTrue(content_len < len(self.big_log_content) - offset)
        self.assertEqual(doc['content'], self.big_log_content[offset:offset + content_len])
        self.assertEqual(doc['new_offset'], offset + content_len),
        self.assertEqual(doc['task_finished'], 0)
        self.assertEqual(doc['next_poll'], 0)

    @profile
    def test_view_big_json_iterate(self):
        """Iterates over log chunks based on next_poll and new_offset in responses,
        simulating the LogWatcher JS behavior. Verifies that the full log can be assembled."""

        # The task has to be finished for this test, otherwise it'll loop forever
        task = Task.objects.get(id=TASK_ID)
        task.state = TASK_STATES["CLOSED"]
        task.save()

        all_content = ''
        offset = 0

        for i in itertools.count():
            self.assertTrue(i < 10000, 'infinite loop reading log?')

            response, content = self.assertGetLog(
                'big.log',
                view_type='log-json',
                test_content_length=False,
                data={'offset': offset},
            )
            doc = json.loads(content)
            all_content = all_content + doc['content']
            offset = doc['new_offset']
            if doc['next_poll'] is None:
                break

        self.assertEqual(all_content, self.big_log_content)

    def assertGetLog(self, log_name, view_type='log', test_content_length=True,
                     expected_content=None, data={}):
        """Verify log can be successfully retrieved and response has certain properties.
        The HttpResponse and its content are returned so that tests may do further
        assertions."""
        response = self.get_log(log_name, view_type=view_type, data=data)
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

    def get_log(self, log_name, view_type='log', data={}):
        url = '/task/{0}/{1}/{2}'.format(TASK_ID, view_type, log_name)
        return self.client.get(url, data)
