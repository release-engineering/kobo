kobo
====

A collection of Python utilities.

[![Build Status](https://travis-ci.org/release-engineering/kobo.svg?branch=master)](https://travis-ci.org/release-engineering/kobo)
[![Coverage Status](https://coveralls.io/repos/github/release-engineering/kobo/badge.svg?branch=master)](https://coveralls.io/github/release-engineering/kobo?branch=master)


Development
===========

Use a virtualenv for development.
For example, install kobo and dependencies in editable mode:

    virtualenv ~/kobo-dev
    . ~/kobo-dev/bin/activate
    pip install --editable ~/src/kobo
    pip install -rtest-requirements.txt

To run the test suite:

- Run `py.test` to run tests against installed versions
  of python and dependencies, or...
- Install and run `tox` to run test suite against a matrix of supported
  python and Django versions (more thorough, slower).

Please submit pull requests against https://github.com/release-engineering/kobo.


Changelog
=========

kobo 0.12.0
-----------

### BUG FIXES

- Improved Django 1.11 and 2.x compatibility

kobo 0.11.0
-----------

### FEATURES & IMPROVEMENTS

- The resubmit-tasks command now accepts a `--nowait` argument

### BUG FIXES

- Fixed usage of `shortcuts.run` with text mode in Python 3
  ([#133](https://github.com/release-engineering/kobo/issues/133))
- Fixed decoding crashes in `shortcuts.run` when an incomplete multibyte
  sequence is read
  ([#119](https://github.com/release-engineering/kobo/issues/119))
- Fixed rpmlib attempting to decode binary data in RPM headers
- Fixed various Python 3 compatibility issues

kobo 0.10.0
-----------

### FEATURES & IMPROVEMENTS

- Improved Python 3 compatibility, particularly in xmlrpc and rpmlib modules
- Improved Django 1.11 and 2.x compatibility

### REMOVED

- Testing of Python 2.6 has been dropped; some kobo functionality still works
  with Python 2.6, but may break without warning in later releases
- Support for Django 1.6 has been removed

kobo 0.9.0
----------

### BUG FIXES

- Fixed LoggingThread on Python 3 ([#66](https://github.com/release-engineering/kobo/issues/66))
- Fixed `kobo.django.xmlrpc` migrations for Django 2.x
- Fixed some exceptions discarded without logging ([#32](https://github.com/release-engineering/kobo/issues/32))
- Fixed some reliability issues in `kobo.xmlrpc`

kobo 0.8.0
----------

### FEATURES & IMPROVEMENTS

- Improved Python 3 compatibility
- Improved Django 2.0 compatibility
- Improved tests coverage
- Header produced by kobo.shortcuts.run(show_cmd=True) is now limited to 79 characters length

### BUG FIXES

- Fixed handling of string SERVER_PORT in wsgi requests
- Fixed Worker.timeout_task wrongly setting subtasks to INTERRUPTED ([#72](https://github.com/release-engineering/kobo/issues/72))
- Fixed Worker.set_task_weight always crashing ([#75](https://github.com/release-engineering/kobo/issues/75))

kobo 0.7.0
----------

### FEATURES & IMPROVEMENTS

- Improved Python 3 compatibility
- Improved tests coverage


kobo 0.6.0
----------

### FEATURES & IMPROVEMENTS

- kobo worker name no longer needs to match host FQDN
- improved error reporting when loading configuration
- improved error reporting from kobo.shortcuts.run
- reduced memory usage when handling large log files
- models now respect settings.AUTH_USER_MODEL

### BUG FIXES

- fixed crash on xml-rpc client in python <= 2.7.9
- fixed spurious whitespace from kobo.shortcuts.run (#40)
- fixed missing migration for User model


kobo 0.5.0
----------

### FEATURES & IMPROVEMENTS

- kobo.shortcuts.run now supports all Popen keyword arguments
- resubmit-tasks has a --force argument to resubmit successful tasks
- new watch-log command for watching a log from CLI
- admin UI now covers user model

### BUG FIXES

- kobo.shortcuts.run now resumes on interrupted system calls
- worker load no longer includes assigned but unstarted tasks


kobo 0.4.0
----------

### FEATURES & IMPROVEMENTS

- pkgset.SimpleRpmWrapper has now checksum_type member
- threads.run_in_threads helper function

### Django 1.5 update

Django part of kobo was udpated to be compatible with 1.5 release. Lower
version are no more supported. As a side-effect, only python 2.6+ is
supported by django part.

From same reason there will be no builds of kobo-django package for RHEL 5
and lower as it lacks required python version.

- RemoteUserMiddleware is now used for KrbV authentication
- LimitedRemoreUserMiddleware can be used to authenticate only on entry
pages.
- LongnameUser model is used for auth backend. It allows 255 characters long
user names (as they come from KrbV)
- Class-based generic views ExtraListView and ExtraDetailView. object_list
helper stays for compatibility, but it is deprecated now and will be removed
in future.


kobo 0.3.0
----------


### FEATURES & IMPROVEMENTS

- State machine implementation - StateEnum, db field, form fields
- Brand new HTML template, media, views, urls and menu
- Menu supports django.root
- Task logs, javascript log watcher, threaded worker stdout logger
- XML-RPC help pages display list of contents
- Kerberos support in CookieTransport
- JSONField to store dicts and lists in database
- Add relative_path() and split_path() functions to shortcuts


### kobo.pkgset.FileWrapper

file_name attribute renamed to file_path.
file_name is now a property which returns actual file name.

Action:
Change file_name to file_path in your code.


### Username hack

Username hack is enabled by default now (when kobo.django.auth is used).
It changes username to 255 characters and also overrides validation RE.

Action:
On postgresql run: ALTER TABLE auth_user ALTER username TYPE VARCHAR(255);
Sqlite users have to use db_update-0.2.0-0.3.0 script.


### Worker FQDN checking

Each worker's name must match it's FQDN now.
This prevents cut&paste configuration errors when tasks end in INTERRUPTED state.

Action:
Change worker names to FQDN.
Change related usernames as well.


### Changes in kobo.plugins

Removed 'lower_case' attribute.
Plugins are now subclassed when a container is created.
Each plugin now contains 'container' attribute.

Action:
Remove 'lower_case' attribute from plugins, do whatever is necessary in 'normalize_name() class method instead.


- Improve PluginContainer inheritance. Also add 'container' attribute to each plugin class obtained from a container instance. (Daniel Mach)
- Plugins are now subclassed when a container is created. (Daniel Mach)


### kobo.hub.models.Task refactoring

Field 'traceback' moved to a file (traceback.log).
Field 'result' content dumped to a file (stdout.log), it is supposed to contain actual task result.
Field 'args' changed to JSONField and data is directly available without any conversion.

Action:
Run db_update-0.2.0-0.3.0 script.


### Configuration handling in kobo.client and kobo.worker

Configuration no longer uses os.environ to get config file path.
ClientCommandContainer, HubProxy and TaskManager constructor has a new mandatory 'conf' argument.

Action:
    config_file = os.environ.get("<PROJECT_NAME>_CONFIG_FILE", "/etc/<project_name>.conf")
    conf = kobo.conf.PyConfigParser()
    conf.load_from_file(config_file)
    ... and pass conf to ClientCommandContainer, HubProxy or TaskManager


### Configuration passed to tasks

TaskBase constructor has now a mandatory argument 'conf', which is automatically set in TaskManager.

Action:
Add 'conf' argument to tasks classes with custom constructor.
