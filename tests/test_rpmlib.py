#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest2 as unittest

# tolerate and skip in absence of rpm since it's not installable to virtualenv
try:
    import rpm
except ImportError:
    HAVE_RPM = False
else:
    HAVE_RPM = True
    from kobo.rpmlib import parse_nvr, parse_nvra, compare_nvr, parse_evr, make_nvr, make_nvra


@unittest.skipUnless(HAVE_RPM, "rpm python module is not installed")
class TestNVR(unittest.TestCase):
    def test_valid_nvr(self):
        self.assertEqual(parse_nvr("net-snmp-5.3.2.2-5.el5"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch=""))
        self.assertEqual(parse_nvr("1:net-snmp-5.3.2.2-5.el5"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1"))
        self.assertEqual(parse_nvr("net-snmp-1:5.3.2.2-5.el5"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1"))
        self.assertEqual(parse_nvr("net-snmp-5.3.2.2-5.el5:1"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1"))
        self.assertEqual(parse_nvr("/net-snmp-5.3.2.2-5.el5:1"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1"))
        self.assertEqual(parse_nvr("/1:net-snmp-5.3.2.2-5.el5"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1"))
        self.assertEqual(parse_nvr("foo/net-snmp-5.3.2.2-5.el5:1"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1"))
        self.assertEqual(parse_nvr("foo/1:net-snmp-5.3.2.2-5.el5"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1"))
        self.assertEqual(parse_nvr("/foo/bar/net-snmp-5.3.2.2-5.el5:1"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1"))
        self.assertEqual(parse_nvr("/foo/bar/1:net-snmp-5.3.2.2-5.el5"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1"))

        # test for name which contains the version number and a dash
        self.assertEqual(parse_nvr("openmpi-1.10-1.10.2-2.el6"), dict(name="openmpi-1.10", version="1.10.2", release="2.el6", epoch=""))

    def test_invalid_nvr(self):
        self.assertRaises(ValueError, parse_nvr, "net-snmp")
        self.assertRaises(ValueError, parse_nvr, "net-snmp-5.3.2.2-1:5.el5")
        self.assertRaises(ValueError, parse_nvr, "1:net-snmp-5.3.2.2-5.el5:1")
        self.assertRaises(ValueError, parse_nvr, "1:net-snmp-1:5.3.2.2-5.el5")
        self.assertRaises(ValueError, parse_nvr, "net-snmp-1:5.3.2.2-5.el5:1")
        self.assertRaises(ValueError, parse_nvr, "1:net-snmp-1:5.3.2.2-5.el5:1")

    def test_valid_nvra(self):
        self.assertEqual(parse_nvra("net-snmp-5.3.2.2-5.el5.i386"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="", arch="i386", src=False))
        self.assertEqual(parse_nvra("net-snmp-5.3.2.2-5.el5.i386.rpm"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="", arch="i386", src=False))
        self.assertEqual(parse_nvra("net-snmp-5.3.2.2-5.el5.src.rpm"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="", arch="src", src=True))

        self.assertEqual(parse_nvra("/net-snmp-5.3.2.2-5.el5.src.rpm:1"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1", arch="src", src=True))
        self.assertEqual(parse_nvra("/1:net-snmp-5.3.2.2-5.el5.src.rpm"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1", arch="src", src=True))
        self.assertEqual(parse_nvra("foo/net-snmp-5.3.2.2-5.el5.src.rpm:1"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1", arch="src", src=True))
        self.assertEqual(parse_nvra("foo/1:net-snmp-5.3.2.2-5.el5.src.rpm"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1", arch="src", src=True))
        self.assertEqual(parse_nvra("/foo/bar/net-snmp-5.3.2.2-5.el5.src.rpm:1"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1", arch="src", src=True))
        self.assertEqual(parse_nvra("/foo/bar/1:net-snmp-5.3.2.2-5.el5.src.rpm"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1", arch="src", src=True))

    def test_invalid_nvra(self):
        self.assertEqual(parse_nvra("net-snmp-5.3.2.2-5.el5.i386.rpm:1"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1", arch="i386", src=False))
        self.assertEqual(parse_nvra("net-snmp-5.3.2.2-5.el5.i386:1.rpm"), dict(name="net-snmp", version="5.3.2.2", release="5.el5", epoch="1", arch="i386", src=False))
        self.assertRaises(ValueError, parse_nvra, "net-snmp-5.3.2.2-5")

    def test_compare_nvr(self):
        first = {'name': 'a', 'version': '1', 'release': '1', 'epoch': '1'}
        second = {'name': 'a', 'version': '1', 'release': '1', 'epoch': '1'}
        self.assertEqual(compare_nvr(first, second), 0)
        second['version'] = '0'
        self.assertEqual(compare_nvr(first, second), 1)
        second['version'] = 0
        self.assertEqual(compare_nvr(first, second), 1)
        second['version'] = 2
        self.assertEqual(compare_nvr(first, second), -1)
        second['version'] = 1
        second['release'] = 0
        self.assertEqual(compare_nvr(first, second), 1)
        second['release'] = 2
        self.assertEqual(compare_nvr(first, second), -1)
        second['release'] = 1
        second['epoch'] = 0
        self.assertEqual(compare_nvr(first, second), 1)
        second['epoch'] = 2
        self.assertEqual(compare_nvr(first, second), -1)
        first = {'name': 'a', 'version': '1', 'release': '1', 'epoch': None}
        second = {'name': 'a', 'version': '1', 'release': '1', 'epoch': '1'}
        self.assertEqual(compare_nvr(first, second), -1)
        # missing epoch
        first = {'name': 'a', 'version': '1', 'release': '1'}
        self.assertEqual(compare_nvr(first, second), -1)

    def test_valid_evr(self):
        self.assertEqual(parse_evr("5.3.2.2-5.el5"), {"epoch": "", "version": "5.3.2.2", "release": "5.el5"})
        self.assertEqual(parse_evr("1:5.3.2.2-5.el5"), {"epoch": "1", "version": "5.3.2.2", "release": "5.el5"})
        self.assertEqual(parse_evr("5.3.2.2-5.el5:1"), {"epoch": "1", "version": "5.3.2.2", "release": "5.el5"})
        self.assertEqual(parse_evr("5.3.2.2:1", allow_empty_release=True), {"epoch": "1", "version": "5.3.2.2", "release": ""})
        self.assertEqual(parse_evr("1:5.3.2.2", allow_empty_release=True), {"epoch": "1", "version": "5.3.2.2", "release": ""})
        self.assertEqual(parse_evr("1:5", allow_empty_release=True), {"epoch": "1", "version": "5", "release": ""})
        self.assertEqual(parse_evr("1", allow_empty_release=True), {"epoch": "", "version": "1", "release": ""})

    def test_invalid_evr(self):
        self.assertRaises(ValueError, parse_evr, "a:b")
        self.assertRaises(ValueError, parse_evr, "5.3.2.2:1", allow_empty_release=False)
        self.assertRaises(ValueError, parse_evr, "1:5.3.2.2", allow_empty_release=False)
        self.assertRaises(ValueError, parse_evr, "1:5", allow_empty_release=False)
        self.assertRaises(ValueError, parse_evr, "1", allow_empty_release=False)

    def test_make_nvr(self):
        nvr = dict(name="net-snmp", version="5.3.2.2", release="5.el5")
        self.assertEqual(make_nvr(nvr), "net-snmp-5.3.2.2-5.el5")

        nvr = dict(name="net-snmp", version="5.3.2.2", release="5.el5")
        self.assertEqual(make_nvr(nvr), "net-snmp-5.3.2.2-5.el5")
        self.assertEqual(make_nvr(nvr, add_epoch=True), "net-snmp-5.3.2.2-5.el5")
        self.assertEqual(make_nvr(nvr, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5")
        self.assertEqual(make_nvr(nvr, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5")
        # force_epoch overrides add_epoch
        self.assertEqual(make_nvr(nvr, add_epoch=False, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5")

        nvr["epoch"] = None
        self.assertEqual(make_nvr(nvr, add_epoch=True), "net-snmp-5.3.2.2-5.el5")
        self.assertEqual(make_nvr(nvr, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5")

        nvr["epoch"] = ""
        self.assertEqual(make_nvr(nvr, add_epoch=True), "net-snmp-5.3.2.2-5.el5")
        self.assertEqual(make_nvr(nvr, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5")

        nvr["epoch"] = "0"
        self.assertEqual(make_nvr(nvr, add_epoch=True), "net-snmp-5.3.2.2-5.el5")
        self.assertEqual(make_nvr(nvr, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5")

        nvr["epoch"] = 0
        self.assertEqual(make_nvr(nvr, add_epoch=True), "net-snmp-5.3.2.2-5.el5")
        self.assertEqual(make_nvr(nvr, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5")

        nvr["epoch"] = 1
        self.assertEqual(make_nvr(nvr, add_epoch=True), "net-snmp-1:5.3.2.2-5.el5")
        self.assertEqual(make_nvr(nvr, add_epoch=True, force_epoch=True), "net-snmp-1:5.3.2.2-5.el5")

    def test_make_nvra(self):
        nvra = dict(name="net-snmp", version="5.3.2.2", release="5.el5", arch="i386")
        self.assertEqual(make_nvra(nvra), "net-snmp-5.3.2.2-5.el5.i386")
        self.assertEqual(make_nvra(nvra, add_rpm=True), "net-snmp-5.3.2.2-5.el5.i386.rpm")
        self.assertEqual(make_nvra(nvra, add_epoch=True), "net-snmp-5.3.2.2-5.el5.i386")
        self.assertEqual(make_nvra(nvra, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5.i386")
        self.assertEqual(make_nvra(nvra, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5.i386")
        # force_epoch overrides add_epoch
        self.assertEqual(make_nvra(nvra, add_epoch=False, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5.i386")
        self.assertEqual(make_nvra(nvra, add_epoch=True, force_epoch=True, add_rpm=True), "net-snmp-0:5.3.2.2-5.el5.i386.rpm")

        nvra["epoch"] = None
        self.assertEqual(make_nvra(nvra, add_epoch=True), "net-snmp-5.3.2.2-5.el5.i386")
        self.assertEqual(make_nvra(nvra, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5.i386")

        nvra["epoch"] = ""
        self.assertEqual(make_nvra(nvra, add_epoch=True), "net-snmp-5.3.2.2-5.el5.i386")
        self.assertEqual(make_nvra(nvra, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5.i386")

        nvra["epoch"] = "0"
        self.assertEqual(make_nvra(nvra, add_epoch=True), "net-snmp-5.3.2.2-5.el5.i386")
        self.assertEqual(make_nvra(nvra, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5.i386")

        nvra["epoch"] = 0
        self.assertEqual(make_nvra(nvra, add_epoch=True), "net-snmp-5.3.2.2-5.el5.i386")
        self.assertEqual(make_nvra(nvra, add_epoch=True, force_epoch=True), "net-snmp-0:5.3.2.2-5.el5.i386")

        nvra["epoch"] = 1
        self.assertEqual(make_nvra(nvra, add_epoch=True), "net-snmp-1:5.3.2.2-5.el5.i386")
        self.assertEqual(make_nvra(nvra, add_epoch=True, force_epoch=True), "net-snmp-1:5.3.2.2-5.el5.i386")

        nvra = dict(name="openmpi-1.10", version="1.10.2", release="2.el6", arch="i386")
        self.assertEqual(make_nvra(nvra), "openmpi-1.10-1.10.2-2.el6.i386")
