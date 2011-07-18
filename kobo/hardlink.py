# -*- coding: utf-8 -*-


import os
import shutil
import logging
import tempfile


__all__ = (
    "Hardlink",
    "UndoHardlink",
)


class Hardlink(object):
    """
    Hardink files within one filesystem or copy files
    to another filesystem while preserving hardlinks.
    """

    __slots__ = (
        "_inode_cache",
        "_precache",
        "logger",
        "test",
    )


    def __init__(self, test=False, logger=None):
        self._inode_cache = {}
        self._precache = {}
        self.test = test
        self.logger = logger


    def __call__(self, src, dst):
        return self.link(src, dst)


    def log(self, loglevel, msg):
        if self.logger:
            self.logger.log(loglevel, msg)


    def precache(self, path, recursive=False):
        def get_stats(item):
            return [ item[i] for i in ("st_dev", "st_ino", "st_mtime", "st_size") ]

        path = os.path.abspath(path)
        if os.path.isfile(path):
            msg = "Precaching %s" % path
            self.log(logging.DEBUG, msg)
            st = os.stat(path)
            item = {
                "st_dev": st.st_dev,
                "st_ino": st.st_ino,
                "st_mtime": st.st_mtime,
                "st_size": st.st_size,
                "path": path,
            }

            fn = os.path.basename(path)
            precache_key = (fn, item["st_mtime"], item["st_size"])
            if precache_key in self._precache:
                if get_stats(item) != get_stats(self._precache[precache_key]):
                    self.log(logging.DEBUG, "Caching failed, files are different: %s, %s" % (path, self._precache[precache_key]["path"]))

            self._precache[precache_key] = item
            return

        for fn in os.listdir(path):
            fn_path = os.path.join(path, fn)

            if os.path.isfile(fn_path):
                self.precache(fn_path)
                continue

            if recursive:
                self.precache(fn_path, recursive=True)


    def link(self, src, dst):
        """ Create hardlinks or copy files."""

        if os.path.isfile(src):
            self._link_file(src, dst)
        else:
            self._link_dir(src, dst)


    def _link_dir(self, src, dst):
        # src and dst has to be directories
        for i in (src, dst):
            if not os.path.isdir(i):
                raise IOError("Not a file: %s" % i)

        if not os.path.isdir(dst):
            if self.test:
                msg = "TEST: would create directory: %s" % dst
                self.log(logging.INFO, msg)
            else:
                msg = "Creating directory: %s" % dst
                self.log(logging.INFO, msg)
                os.makedirs(dst)

            for fn in os.listdir(src):
                new_src = os.path.join(src, fn)
                new_dst = os.path.join(dst, fn)
                self.link(new_src, new_dst)


    def _link_file(self, src, dst):
        if self.test:
            msg = "TEST: would link %s -> %s" % (src, dst)
            self.log(logging.INFO, msg)
            return

        if not os.path.isfile(src):
            raise IOError("Not a file: %s" % src)

        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        src_stat = os.stat(src)
        src_key = (src_stat.st_dev, src_stat.st_ino)

        if os.path.isfile(dst):
            dst_stat = os.stat(dst)
            dst_key = (dst_stat.st_dev, dst_stat.st_ino)
            if src_key == dst_key:
                # same device and inode -> same content -> skip silently
                msg = "Files have the same inode: %s -> %s" % (src, dst)
                self.log(logging.DEBUG, msg)
                return

            if (dst_stat.st_mtime, dst_stat.st_size) == (src_stat.st_mtime, src_stat.st_size):
                # file exists, but size and time is the same
                msg = "File already exists: %s" % dst
                self.log(logging.WARNING, msg)
                return

            # file exists and size or time is different
            msg = "File already exists, time or size differs: %s" % dst
            self.log(logging.ERROR, msg)
            return


        dst_dir = os.path.dirname(dst)
        dst_dir_stat = os.stat(dst_dir)

        if (src_stat.st_dev == dst_dir_stat.st_dev):
            # same device
            msg = "Linking file: %s -> %s" % (src, dst)
            self.log(logging.INFO, msg)
            os.link(src, dst)
            return

        if src_key in self._inode_cache:
            # (st_dev, st_ino) found in the cache
            msg = "Cache hit. Linking file: %s -> %s" % (src, dst)
            self.log(logging.INFO, msg)
            os.link(self._inode_cache[src_key], dst)
            return

        src_fn = os.path.basename(src)
        if src_fn in self._precache:
            if (src_stat.st_mtime, src_stat.st_size) == (self._precache[src_fn]["st_mtime"], self._precache[src_fn]["st_size"]):
                msg = "Preache hit. Linking file: %s -> %s" % (self._precache[src_fn]["path"], dst)
                self.log(logging.INFO, msg)
                os.link(self._precache[src_fn]["path"], dst)
                self._inode_cache[src_key] = dst
                return

        # copy file otherwise and populate _inode_cache
        msg = "Copying file: %s -> %s" % (src, dst)
        self.log(logging.INFO, msg)
        shutil.copy2(src, dst)
        os.utime(dst, (src_stat.st_atime, src_stat.st_mtime))
        self._inode_cache[src_key] = dst


class UndoHardlink(object):
    __slots__ = (
       "logger",
       "test",
    )

    def __init__(self, test=False, logger=None):
        self.test = test
        self.logger = logger


    def __call__(self, file_path):
        self.undo_hardlink(file_path)


    def log(self, loglevel, msg):
        if self.logger:
            self.logger.log(loglevel, msg)


    def undo_hardlink(self, file_path):
        if os.path.isdir(file_path):
            for fn in os.listdir(file_path):
                self.undo_hardlink(os.path.join(file_path, fn))
            return

        if not os.path.isfile(file_path):
            # skip special files (devices, etc.)
            return

        if self.test:
            self.log(logging.INFO, "TEST: Would remove hardlink: %s" % file_path)
            return

        self.log(logging.DEBUG, "Removing hardlink: %s" % file_path)

        try:
            st = os.stat(file_path)
        except IOError, ex:
            self.log(logging.ERROR, "Stat failed: %s" % ex)

        if st.st_nlink < 2:
            return

        dn = os.path.dirname(file_path)
        fn = os.path.basename(file_path)

        tmp_dir = tempfile.mkdtemp(dir=dn)
        tmp_file = os.path.join(tmp_dir, fn)

        try:
            shutil.copy(file_path, tmp_file)
        except IOError, ex:
            self.log(logging.ERROR, "Copy failed: %s" % ex)
            raise

        try:
            shutil.move(tmp_file, file_path)
        except IOError, ex:
            self.log(logging.ERROR, "Move failed: %s" % ex)
            raise

        os.chown(file_path, st.st_uid, st.st_gid)
        os.chmod(file_path, st.st_mode)
        os.utime(file_path, (st.st_atime, st.st_mtime))

        try:
            os.rmdir(tmp_dir)
        except IOError, ex:
            self.log(logging.ERROR, "Move failed: %s" % ex)
            raise
