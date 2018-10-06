#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest
import six

import logging
from kobo.log import *




class TestLog(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("TestLogger")

    def test_verbose_hack(self):
        self.logger.verbose("foo")
        logging.verbose("foo")
        self.assertEqual(logging.VERBOSE, 15)
        if six.PY2:
            # There is no _levelNames attribute in Python 3
            self.assertTrue("VERBOSE" in logging._levelNames)
        self.assertEqual(logging.getLevelName(15), "VERBOSE")
