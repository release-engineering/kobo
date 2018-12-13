import os

from django.test.utils import get_runner
from django.conf import settings

# Run test with KOBO_MEMORY_PROFILER=1 to generate memory usage reports from
# tests annotated with @profile.
#
# The point of the memory profiler with tests is to prove that the function
# is memory efficient. When using the profiler, you'll want to verify that
# the peak memory usage shows no significant increase in the annotated test.
if os.environ.get('KOBO_MEMORY_PROFILER', '0') == '1':
    from memory_profiler import profile
else:
    # If memory_profiler is disabled, this is a no-op decorator
    def profile(fn):
        return fn


class DjangoRunner(object):
    """Use this for tests which need an active Django environment
    and database.  Create an instance and start/stop around the
    relevant test(s).

    Ideally, this could be set up as a pytest fixture in conftest.py.
    That doesn't work currently due to https://github.com/pytest-dev/pytest/issues/517 ;
    it clashes with django.testcase.TestCase.setUpClass.
    It can instead be used via setup_module/teardown_module.
    """
    def __init__(self):
        self.runner = None
        self.old_config = None

    def start(self):
        runner_class = get_runner(settings)
        self.runner = runner_class()
        self.runner.setup_test_environment()
        self.old_config = self.runner.setup_databases()

    def stop(self):
        self.runner.teardown_databases(self.old_config)
        self.runner.teardown_test_environment()
        self.runner = None
        self.old_config = None


def data_path(basename):
    """Returns path to a file under 'data' dir."""
    this_dir = os.path.dirname(__file__)
    return os.path.join(this_dir, 'data', basename)


class ArgumentIsInstanceOf(object):

    def __init__(self, classinfo):
        self.classinfo = classinfo

    def __eq__(self, other):
        return isinstance(other, self.classinfo)
