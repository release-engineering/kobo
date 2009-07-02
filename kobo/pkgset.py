# -*- coding: utf-8 -*-

import os

import kobo.rpmlib


__all__ = (
    "FileWrapper",
    "RpmWrapper",
    "FileCache",
)


class FileWrapper(object):
    __slots__ = (
        "file_name",
    )

    def __init__(self, file_name, **kwargs):
        self.file_name = file_name

    def __str__(self):
        return self.file_name


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


    def __get__(self, name):
        return self.file_cache[os.path.abspath(name)]

    def __iter__(self):
        return self.file_cache.iterkeys()

    def __len__(self):
        return len(self.file_cache)

    def iteritems(self):
        return self.file_cache.iteritems()


    def add(self, file_name, **kwargs):
        file_name = os.path.abspath(file_name)
        st = os.stat(file_name)
        cache_key = (st.st_dev, st.st_ino)

        if cache_key in self.inode_cache:
            return self.inode_cache[cache_key]

        value = self.file_wrapper_class(file_name, **kwargs)
        self.inode_cache[cache_key] = value
        self.file_cache[file_name] = value
        return value
