RUNNING THE TESTS
=================

The test suite requires koji and Django Python packages. Koji is available
only as an RPM package while older Django versions are available from PyPI.
To prepare the local environment execute the commands

    # yum install koji
    $ mkvirtualenv --system-site-packages kobo
    (kobo)$ pip install Django==1.5.12
    (kobo)$ make test

Additionally, the tox command may be used to run tests against a selection
of supported Python and Django versions.
