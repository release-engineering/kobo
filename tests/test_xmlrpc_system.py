# -*- coding: utf-8 -*-

import unittest

from kobo.hub.xmlrpc.system import getAPIVersion


class TestApiVersion(unittest.TestCase):

    def test_api_version(self):
        version = getAPIVersion(None)
        self.assertEqual(version, '0.1.0')
