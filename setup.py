#!/usr/bin/python
# -*- coding: utf-8 -*-


import os

import distutils.command.sdist
from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES


# override default tarball format with bzip2
distutils.command.sdist.sdist.default_format = {"posix": "bztar"}

# force to install data files to site-packages
for scheme in INSTALL_SCHEMES.values():
    scheme["data"] = scheme["purelib"]

# recursively scan for python modules to be included
package_root_dirs = ["kobo"]
packages = set()
for package_root_dir in package_root_dirs:
    for root, dirs, files in os.walk(package_root_dir):
        if "__init__.py" in files:
            packages.add(root.replace("/", "."))
packages = sorted(packages)


setup(
    name            = "kobo",
    version         = "0.4.0",
    description     = "Python modules for tools development",
    url             = "https://fedorahosted.org/kobo/",
    author          = "Red Hat, Inc.",
    author_email    = "dmach@redhat.com",
    license         = "LGPLv2.1",

    packages        = packages,
    scripts         = ["kobo/admin/kobo-admin"],
)
