import sys
import os
import json
import gc

from tempfile import TemporaryFile
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

# Run test with KOBO_MEMORY_PROFILER=1 to generate memory usage reports from
# tests annotated with @profile.
#
# The point of the memory profiler with this test is to prove that requesting
# a log doesn't require loading the entire log into memory.  When using the
# profiler, you'll want to verify that the peak memory usage shows no significant
# increase in the tests dealing with big logs.
if os.environ.get('KOBO_MEMORY_PROFILER', '0') == '1':
    from memory_profiler import profile
else:
    # If memory_profiler is disabled, this is a no-op decorator
    def profile(fn):
        return fn


TASK_ID = 123

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
    return out


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

    @profile
    def test_view_big_html_wrapped(self):
        response = self.get_log('big.log')
        self.assertEqual(response.status_code, 200, response)

        content = response.content
        self.assertTrue(content.startswith('<!DOCTYPE html'))
        # TODO: when log trimming is added, verify it here

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
        gz_file = GzipFile(mode='rb', fileobj=tempfile)
        all_data = gz_file.read()
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

    @profile
    def test_view_big_json(self):
        response, content = self.assertGetLog(
            'big.log',
            view_type='log-json',
            test_content_length=False,
        )
        expected_content = self.big_log_content
        doc = json.loads(content)
        self.assertEqual(doc['content'], expected_content)
        self.assertEqual(doc['new_offset'], len(self.big_log_content)),
        self.assertEqual(doc['task_finished'], 0)

    @profile
    def test_view_zipped_big_json(self):
        response, content = self.assertGetLog(
            'zipped_big.log',
            view_type='log-json',
            test_content_length=False,
        )
        expected_content = self.big_log_content
        doc = json.loads(content)
        self.assertEqual(doc['content'], expected_content)
        self.assertEqual(doc['new_offset'], len(self.big_log_content)),
        self.assertEqual(doc['task_finished'], 0)

    @profile
    def test_view_zipped_big_json_offset(self):
        response, content = self.assertGetLog(
            'zipped_big.log',
            view_type='log-json',
            test_content_length=False,
            data={'offset': 20000}
        )
        expected_content = self.big_log_content[20000:]
        doc = json.loads(content)
        self.assertEqual(doc['content'], expected_content)
        self.assertEqual(doc['new_offset'], len(self.big_log_content)),
        self.assertEqual(doc['task_finished'], 0)

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

if __name__ == '__main__':
    TestRunner = get_runner(django.conf.settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests([__name__])
    sys.exit(bool(failures))
