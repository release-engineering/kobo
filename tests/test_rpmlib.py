#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest

# tolerate and skip in absence of rpm since it's not installable to virtualenv
try:
    import rpm
except ImportError:
    HAVE_RPM = False
else:
    HAVE_RPM = True
    from kobo.rpmlib import parse_nvr, parse_nvra, compare_nvr, parse_evr, make_nvr, make_nvra, get_keys_from_header


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


@unittest.skipUnless(HAVE_RPM, "rpm python module is not installed")
class TestGetKeys(unittest.TestCase):
    def test_sigkey(self):
        header = {
            rpm.RPMTAG_DSAHEADER: None,
            rpm.RPMTAG_RSAHEADER: b"\x89\x02\x15\x03\x05\x00]\xb2\x95\\\xef<\x11\x1f\xcf\xc6Y\xb9\x01\x08E.\x0f\xffC\x10\xe5\x0e\xff\xa3\x8a\xce\xfb\xff\xf1\xf6\x98L|\xf5\xcbd\x8dc\xa8IsP\x18\x85\xc0\x06\xc0L\xff\x95\xd7\x86\xdd\xbe\xf1\xe0L%P2^\x14\xfe1\xf6\x85\x88\xe7\x93\xd6{\xaa\xf0\x1d\xa7YJ\x8e\xfc\x08\xa0\x9f\x8e\x10|\xd7(\x94\n\xdd\x06Ta\xca\x94\x0e\x05\x1f\xb2jv|JB^\xffAU\x90\x96d\x88K\xcb<\x06\xca\x93\x7f\xc2B@\xa2\x10DF\x8e\x04\xa5\xf9C\x86\xe3Z.\n\xe4\xde\xa6\x83\xa1\x85\x91I#o\xa4\x8e{\xbc\xdd\xcdF\xa35\xc2~\xed.\xfb\x18\xecS\x95\xb7iz\xfd=\x1d\x9a\xd9h\x7fP@\xcb\xfbW-\x12\xfc\xa2f\xf9\x7fd\xe1\x87\xedu\x9bTZ\\\xbc9\xea\xad\xee\xf8\xdf\xb7f\x88\xdc$\xad\x1c/\xd7\xc1\x1b\xca\xc0\x1b\xd7q\xaa\x13\xa4J\x92\x971X\xac\x16I\xd1\xde\x011+jW\x08\x9dC\x86\x00\x02!g%@h\xe6u\xe1\xd5e\xa7j\x80\xe2\x9bH\xdb\xec\x84\xca \x80\x8c\xbaQ4\xfdVp1\xe1\x98\xe2\xe7\xfb\xdf\x0cE6\xe2\xa7\n^\x14\xe4\xe1\xb2\x06\x1fU\xe7:\xcdH\x15\xa8\x10[\xdd\xf5\xa2B\x1f\xdf\xf9\x9e\x8au\x93l\x97\xb7\x12\xe9\xf9'\x0e\xd4\xe2a\xd6\xa4\xbc4\xa4y\x88\xe8\xabE\xe3\xbf\x15uaFs\x08\xad\xd5,c4K\xa8%ZMHmy\\_\x05\xc6\x0f\xdc0\xcc\x80B\xda\xde\xf0A\x1b\xeb\xe4\x13\x9e\xad\x9d)a\xd4I\xd7\xfd\xc7,\xc5\xf2{\xcc\x0b\t&\xce2\xfb\xe89\x91< \xe1a\xbd\xec\xe6\xe0-K\xc2DX\xc3\xbf\x95\xf3\xf1\x9c\xaa\x91f\xb2}\x9bj+\xb7\x86:\x99\x81\xfd\x96\xbb3\x02\x90\x05\xf6\xa8\x1e#<Na\xdf*\xab\xc9\xd8\x1a\xeaA7bR\xec4/\x83\xf0\x13\x1a\x80%\xe0#\x89\xd0\xa5\x0f\xb8\xb7\x8bNG\x9c~\x9c\xae\xe2\xc5\xeb\x17K\xed\x8d@\x12{\xb0\xe4\xfc\xb1\xe4\xda\xce\xe2\xc7\xe6\xdf@\xd0\x05\xde\x153b\x08\x1b\x80\x11\x80Z\x95A\x85+sQ _\xcd\xee/\xa8\x0fx\xd8\xad\r}\xb4\x19",
            rpm.RPMTAG_SIGGPG: None,
            rpm.RPMTAG_SIGPGP: b'\x89\x02\x15\x03\x05\x00]\xb2\x95\\\xef<\x11\x1f\xcf\xc6Y\xb9\x01\x08+P\x0f\xfd\x1b\x06\x11\xb5\xf2\xcf\x97\xa7+\xd2\x0biU_\xda\xd1\xb4\xf4\xd6A\xf55\xc7se\x92<\xffC\xdc,\xfa\xa6&xbm\xfe\x943f\xedbe \xac\xf9\x1d\x91\xd4\x97\xdd~v\xb5\xf9\x14\xc2\xdc\xdb\xb2\xe0\x08\\g\xaeS&\xed\x1f$U{\xc4\x1f\xe8\xc3\xdfF\xb3\xa0\xdb\xcbo\x94_L\xb0\xf1\x8d<\xa1c\xe3\x16f7E\xd3\xa6O\xde\xa3NG\x10\xbc\x0b*\xaa\xd2\xe2\xe2\xf9\xc2\xb8\xb6\xee\xa5\x88s\xc5\xb7\xcc=\x9e\x17\x97~\x1c\xa4x\x06ri\x80-\x08@ l0\xce\xe2k\xb7\xe3h}\x86\x0c\x88q\x80(\xa6\xc6\xa1\xf1Q\xfd0\xbbg\xf8\xe4\xe1\xe2t\x00O\'\x07D\xdfZ\x10\xd6\x1d\xf0\xee\x1e\xc7\x074\x0e\xb5\xf9\xacO\x89\x90M`\xb1F\xfa\\b\x83\x96\xb0\xcf\xc4\x9b\xdd\xf8$\xc4\x92\x83\x87\x15(6)H\xa0\xdf!\xdc\x04\xdb\x15\x81S%\x0bf\xba\xa6T\x1c\x02_\x08\xfe\xd6]Aa\x81\x8f\xe2Y"\xe0\x08\xb3\xa3\xfak*V\xa3\xdc\xab\xbd\xb3=T\x8fu\x7fN9\xf2s&\xde\x0512\x9b\xe4\xdcY\xeeP\xf1\xd8\xe8\x1dB\xa5v\xb3\xc6\xd8k\x92[\xae\xa2\x8e*\xd9r\x02P2\xf9Vpg\x8b\xd4\xac\xca&\xb2\x13\xc1\x8fu\xee\x96\xce\x02UZ\xc4-O\xae\x04f\x03\xab$u\xb4\x17\xcf[\x00\xc3U\xe4\xe2\xf1$\xcb\xfe\x8a\xa3\x08O\x06\x7fVf%+Dg\x1b\xaa\x06!\xdc\xb5\xb5\xb6\xec\xf3$\xc9\xd0\x1c\x89\x0b\xd4IN\x03\x07\xcd^\x97\\\xce\x93\xce\xeb\xf1\xae\xacB\xe0\x04A\x0b\xbe!\x8d\xa7.W\xa4\xfa\xea[\xebj7\t\xa8\xda\xd0\xff(\x00a\xb0V\x04\x8f\x93 \x1eiQ\x9dG\xb7\x04g\xbc\x86\xc2\x0f\x06\xf4\x83N\xfc\x9e\x88\xb3D\xff\x92\xd9E\xd7\xc6\xea\\Z\x08^\xf3\xd2\xbf\x83\xfe\xef_\xe5|?\xc5x\xc1\xfd\xbd\x8c&,\x17\x1a\x1c\xf1<c\x0b6C\x8b\x7f\xa0|\x9a\xa37\xf9\xf8U\x90\x1db\x85=\xd4\x0e1\xe4\xdf\xba$\xe3\x05=B!4D\xc8\xc9\x15-',
        }
        self.assertEqual(get_keys_from_header(header), "CFC659B9")

    def test_header_only(self):
        header = {
            rpm.RPMTAG_DSAHEADER: None,
            rpm.RPMTAG_RSAHEADER: b"\x89\x02\x15\x03\x05\x00]\xb2\x95\\\xef<\x11\x1f\xcf\xc6Y\xb9\x01\x08E.\x0f\xffC\x10\xe5\x0e\xff\xa3\x8a\xce\xfb\xff\xf1\xf6\x98L|\xf5\xcbd\x8dc\xa8IsP\x18\x85\xc0\x06\xc0L\xff\x95\xd7\x86\xdd\xbe\xf1\xe0L%P2^\x14\xfe1\xf6\x85\x88\xe7\x93\xd6{\xaa\xf0\x1d\xa7YJ\x8e\xfc\x08\xa0\x9f\x8e\x10|\xd7(\x94\n\xdd\x06Ta\xca\x94\x0e\x05\x1f\xb2jv|JB^\xffAU\x90\x96d\x88K\xcb<\x06\xca\x93\x7f\xc2B@\xa2\x10DF\x8e\x04\xa5\xf9C\x86\xe3Z.\n\xe4\xde\xa6\x83\xa1\x85\x91I#o\xa4\x8e{\xbc\xdd\xcdF\xa35\xc2~\xed.\xfb\x18\xecS\x95\xb7iz\xfd=\x1d\x9a\xd9h\x7fP@\xcb\xfbW-\x12\xfc\xa2f\xf9\x7fd\xe1\x87\xedu\x9bTZ\\\xbc9\xea\xad\xee\xf8\xdf\xb7f\x88\xdc$\xad\x1c/\xd7\xc1\x1b\xca\xc0\x1b\xd7q\xaa\x13\xa4J\x92\x971X\xac\x16I\xd1\xde\x011+jW\x08\x9dC\x86\x00\x02!g%@h\xe6u\xe1\xd5e\xa7j\x80\xe2\x9bH\xdb\xec\x84\xca \x80\x8c\xbaQ4\xfdVp1\xe1\x98\xe2\xe7\xfb\xdf\x0cE6\xe2\xa7\n^\x14\xe4\xe1\xb2\x06\x1fU\xe7:\xcdH\x15\xa8\x10[\xdd\xf5\xa2B\x1f\xdf\xf9\x9e\x8au\x93l\x97\xb7\x12\xe9\xf9'\x0e\xd4\xe2a\xd6\xa4\xbc4\xa4y\x88\xe8\xabE\xe3\xbf\x15uaFs\x08\xad\xd5,c4K\xa8%ZMHmy\\_\x05\xc6\x0f\xdc0\xcc\x80B\xda\xde\xf0A\x1b\xeb\xe4\x13\x9e\xad\x9d)a\xd4I\xd7\xfd\xc7,\xc5\xf2{\xcc\x0b\t&\xce2\xfb\xe89\x91< \xe1a\xbd\xec\xe6\xe0-K\xc2DX\xc3\xbf\x95\xf3\xf1\x9c\xaa\x91f\xb2}\x9bj+\xb7\x86:\x99\x81\xfd\x96\xbb3\x02\x90\x05\xf6\xa8\x1e#<Na\xdf*\xab\xc9\xd8\x1a\xeaA7bR\xec4/\x83\xf0\x13\x1a\x80%\xe0#\x89\xd0\xa5\x0f\xb8\xb7\x8bNG\x9c~\x9c\xae\xe2\xc5\xeb\x17K\xed\x8d@\x12{\xb0\xe4\xfc\xb1\xe4\xda\xce\xe2\xc7\xe6\xdf@\xd0\x05\xde\x153b\x08\x1b\x80\x11\x80Z\x95A\x85+sQ _\xcd\xee/\xa8\x0fx\xd8\xad\r}\xb4\x19",
            rpm.RPMTAG_SIGGPG: None,
            rpm.RPMTAG_SIGPGP: None,
        }
        self.assertEqual(get_keys_from_header(header), "CFC659B9")

    def test_unsigned(self):
        header = {
            rpm.RPMTAG_DSAHEADER: None,
            rpm.RPMTAG_RSAHEADER: None,
            rpm.RPMTAG_SIGGPG: None,
            rpm.RPMTAG_SIGPGP: None,
        }
        self.assertIsNone(get_keys_from_header(header))
