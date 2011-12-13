# -*- coding: utf-8 -*-


import os

import kobo.rpmlib
from kobo.shortcuts import compute_file_checksums, force_list


__all__ = (
    "FileWrapper",
    "RpmWrapper",
    "FileCache",
)


class FileWrapper(object):
    __slots__ = (
        "_checksums",
        "file_path",
        "stat",
        "__dict__",
    )

    def __init__(self, file_path, **kwargs):
        self._checksums = {}
        self.file_path = os.path.abspath(file_path)
        self.stat = kwargs.get("stat", None)
        if not self.stat:
            self.stat = os.stat(file_path)

    def __str__(self):
        return self.file_path

    @property
    def file_name(self):
        return os.path.basename(self.file_path)

    @property
    def size(self):
        """Return file size from cached stat value."""
        return self.stat.st_size

    @property
    def mtime(self):
        """Return file mtime from cached stat value."""
        return self.stat.st_mtime

    def compute_checksums(self, checksum_types):
        """Compute and cache checksums of given types."""

        result = {}
        missing = []
        checksum_types = force_list(checksum_types)

        for checksum_type in checksum_types:
            if checksum_type in self._checksums:
                result[checksum_type] = self._checksums[checksum_type]
            else:
                missing.append(checksum_type)

        if missing:
            result.update(compute_file_checksums(self.file_path, missing))
            self._checksums.update(result)

        return result


class RpmWrapper(FileWrapper):
    __slots__ = (
        "header",
        "signature",
    )

    def __init__(self, file_path, **kwargs):
        FileWrapper.__init__(self, file_path)
        ts = kwargs.pop("ts", None)
        self.header = kobo.rpmlib.get_rpm_header(file_path, ts=ts)

    def __getattr__(self, name):
        return kobo.rpmlib.get_header_field(self.header, name)

    @property
    def files(self):
        return kobo.rpmlib.get_file_list_from_header(self.header)

    @property
    def signature(self):
        result = kobo.rpmlib.get_keys_from_header(self.header)
        if result is not None:
            result = result.upper()
        return result

    @property
    def digest_algo(self):
        return kobo.rpmlib.get_digest_algo_from_header(self.header)

    @property
    def vr(self):
        return "%s-%s" % (self.version, self.release)

    @property
    def nvr(self):
        return "%s-%s-%s" % (self.name, self.version, self.release)

    @property
    def nvra(self):
        return "%s-%s-%s.%s" % (self.name, self.version, self.release, self.arch)


class FileCache(object):
    __slots__ = (
        "inode_cache",
        "file_cache",
        "file_wrapper_class",
    )

    def __init__(self, file_wrapper_class=None):
        self.inode_cache = {}
        self.file_cache = {}
        self.file_wrapper_class = file_wrapper_class or FileWrapper

    def __getitem__(self, name):
        return self.file_cache[os.path.abspath(name)]

    def __iter__(self):
        return self.file_cache.iterkeys()

    def __len__(self):
        return len(self.file_cache)

    def iteritems(self):
        return self.file_cache.iteritems()

    def add(self, file_path, file_wrapper_class=None, **kwargs):
        file_path = os.path.abspath(file_path)
        if file_path in self.file_cache:
            return self.file_cache[file_path]

        st = os.stat(file_path)
        cache_key = (st.st_dev, st.st_ino)
        if cache_key in self.inode_cache:
            return self.inode_cache[cache_key]

        file_wrapper_class = file_wrapper_class or self.file_wrapper_class
        value = file_wrapper_class(file_path, stat=st, **kwargs)
        self.inode_cache[cache_key] = value
        self.file_cache[file_path] = value
        return value

    def remove(self, file_path):
        if type(file_path) not in (str, unicode):
            file_obj = file_path
            file_path = file_obj.file_path
        else:
            file_obj = self.file_cache[file_path]

        cache_key = (file_obj.stat.st_dev, file_obj.stat.st_ino)
        del self.inode_cache[cache_key]
        del self.file_cache[file_path]
        return file_obj

    def remove_by_filenames(self, file_names):
        file_names = [ os.path.basename(i) for i in force_list(file_names) ]
        for i in self.file_cache.keys():
            if os.path.basename(i) in file_names:
                self.remove(i)
