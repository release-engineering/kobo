# -*- coding: utf-8 -*-


import os

import kobo.rpmlib
from kobo.shortcuts import compute_file_checksums, force_list
import six


__all__ = (
    "FileWrapper",
    "RpmWrapper",
    "SimpleRpmWrapper",
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

    def __getstate__(self):
        result = {}
        all_slots = set()
        for cls in type(self).__mro__:
            all_slots.update(getattr(cls, "__slots__", []))

        try:
            # dict is a special case
            all_slots.remove("__dict__")
            result.update(self.__dict__)
        except KeyError:
            pass

        # get data from all slots
        for slot in all_slots:
            result[slot] = getattr(self, slot)

        return result

    def __setstate__(self, value_dict):
        for key, value in six.iteritems(value_dict):
            setattr(self, key, value)

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

    @property
    def nevra(self):
        epoch = self.epoch
        if epoch is None:
            epoch = 0
        return "%s-%s:%s-%s.%s" % (self.name, epoch, self.version, self.release, self.arch)

    @property
    def changelogs(self):
        return kobo.rpmlib.get_changelogs_from_header(self.header)

    @property
    def is_source(self):
        return bool(self.sourcepackage)

    @property
    def is_system_release(self):
        return "system-release" in self.providename


class SimpleRpmWrapper(FileWrapper):
    """
    SimpleRpmWrapper extracts only certain RPM fields instead of
    keeping the whole RPM header in memory.
    """
    __slots__ = (
        "name",
        "version",
        "release",
        "epoch",
        "arch",
        "signature",
        "excludearch",
        "exclusivearch",
        "sourcerpm",
        "is_source",
        "is_system_release",
    )

    def __init__(self, file_path, **kwargs):
        FileWrapper.__init__(self, file_path)

        ts = kwargs.pop("ts", None)
        header = kobo.rpmlib.get_rpm_header(file_path, ts=ts)

        self.name = kobo.rpmlib.get_header_field(header, "name")
        self.version = kobo.rpmlib.get_header_field(header, "version")
        self.release = kobo.rpmlib.get_header_field(header, "release")
        self.epoch = kobo.rpmlib.get_header_field(header, "epoch")
        self.arch = kobo.rpmlib.get_header_field(header, "arch")
        self.signature = kobo.rpmlib.get_keys_from_header(header)
        if self.signature is not None:
            self.signature = self.signature.upper()
        self.excludearch = kobo.rpmlib.get_header_field(header, "excludearch")
        self.exclusivearch = kobo.rpmlib.get_header_field(header, "exclusivearch")
        self.sourcerpm = kobo.rpmlib.get_header_field(header, "sourcerpm")
        self.is_source = bool(kobo.rpmlib.get_header_field(header, "sourcepackage"))
        self.is_system_release = b"system-release" in kobo.rpmlib.get_header_field(header, "providename")
        self.checksum_type = kobo.rpmlib.get_digest_algo_from_header(header).lower()

    def __str__(self):
        return "%s-%s-%s.%s.rpm" % (self.name, self.version, self.release, self.arch)

    def __repr__(self):
        return str(self)

    @property
    def vr(self):
        return "%s-%s" % (self.version, self.release)

    @property
    def nvr(self):
        return "%s-%s-%s" % (self.name, self.version, self.release)

    @property
    def nvra(self):
        return "%s-%s-%s.%s" % (self.name, self.version, self.release, self.arch)

    @property
    def nevra(self):
        epoch = self.epoch
        if epoch is None:
            epoch = 0
        return "%s-%s:%s-%s.%s" % (self.name, epoch, self.version, self.release, self.arch)


class FileCache(object):
    def __init__(self, file_wrapper_class=None):
        self.inode_cache = {}
        self.file_cache = {}
        self.file_wrapper_class = file_wrapper_class or FileWrapper

    def __getitem__(self, name):
        return self.file_cache[os.path.abspath(name)]

    def __setitem__(self, name, value):
        self.file_cache[os.path.abspath(name)] = value

    def __iter__(self):
        return iter(self.file_cache)

    def __len__(self):
        return len(self.file_cache)

    def iteritems(self):
        return six.iteritems(self.file_cache)

    def items(self):
        return list(self.file_cache.items())

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
        if type(file_path) not in (str, six.text_type):
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
        for i in dict(self.file_cache):
            if os.path.basename(i) in file_names:
                self.remove(i)
