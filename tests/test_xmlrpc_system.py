# -*- coding: utf-8 -*-

import unittest2 as unittest

from kobo.hub.xmlrpc.system import getAPIVersion


class TestApiVersion(unittest.TestCase):

    def test_api_version(self):
        version = getAPIVersion(None)
        self.assertEquals(version, '0.1.0')
