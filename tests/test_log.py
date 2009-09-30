#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest
import run_tests # set sys.path

import logging
from kobo.log import *




class TestLog(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("TestLogger")

    def test_verbose_hack(self):
        self.logger.verbose("foo")
        logging.verbose("foo")
        self.assertEqual(logging.VERBOSE, 15)
        self.assertTrue("VERBOSE" in logging._levelNames)
        self.assertEqual(logging._levelNames[15], "VERBOSE")


if __name__ == '__main__':
    unittest.main()
