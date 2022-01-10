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
package_data = {}
for package_root_dir in package_root_dirs:
    for root, dirs, files in os.walk(package_root_dir):
        # ignore PEP 3147 cache dirs and those whose names start with '.'
        dirs[:] = [i for i in dirs if not i.startswith('.') and i != '__pycache__']
        parts = root.split("/")
        if "__init__.py" in files:
            package = ".".join(parts)
            packages.add(package)
            relative_path = ""
        elif files:
            relative_path = []
            while ".".join(parts) not in packages:
                relative_path.append(parts.pop())
            if not relative_path:
                continue
            relative_path.reverse()
            relative_path = os.path.join(*relative_path)
            package = ".".join(parts)
        else:
            # not a module, no files -> skip
            continue

        package_files = package_data.setdefault(package, [])
        package_files.extend([os.path.join(relative_path, i) for i in files if not i.endswith(".py")])


packages = sorted(packages)
for package in package_data.keys():
    package_data[package] = sorted(package_data[package])


setup(
    name            = "kobo",
    version         = "0.20.2",
    description     = "A pile of python modules used by Red Hat release engineering to build their tools",
    url             = "https://github.com/release-engineering/kobo/",
    author          = "Red Hat, Inc.",
    author_email    = "dmach@redhat.com",
    license         = "LGPLv2.1",

    packages        = packages,
    package_data    = package_data,
    scripts         = ["kobo/admin/kobo-admin"],
    install_requires=["six"],
    python_requires ='>2.6',
)
