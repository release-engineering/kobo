#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import unittest
import pytest

from django.core.exceptions import ValidationError
from django.test import TestCase
from django import VERSION
from .models import DummyDefaultModel, DummyModel, DummyNotHumanModel


class TestBasicJSONField(TestCase):

    def test_default(self):
        """
        Test if default works as it should
        """
        d = DummyDefaultModel()
        d.save()

        self.assertEqual(d.field, {})

    def test_default2(self):
        """
        This should raise 'AssertionError: {} != []'
        """
        d = DummyDefaultModel()
        d.save()

        self.assertNotEqual(d.field, [])

    def test_nothumanreadable(self):
        """
        Test human_readable parameter doesn't change anything on dict level
        """
        d = DummyNotHumanModel()
        d.save()

        self.assertEqual(d.field, {})

    def test_nothumanreadable2(self):
        """
        Test human_readable parameter doesn't change anything with data
        """

        data = {'a': 1}
        d = DummyNotHumanModel()
        d.field = data
        d.save()

        self.assertEqual(data, d.field)


    def test_assignment(self):
        """
        Basic assignment
        """
        d = DummyDefaultModel()
        d.field = []

        self.assertEqual(d.field, [])

    def test_assignment_with_save(self):
        """
        Basic assignment with save
        """
        d = DummyDefaultModel()
        d.field = []
        d.save()

        self.assertEqual(d.field, [])

    def test_complex_assignment_with_save(self):
        d = DummyDefaultModel()
        data = {'asd': [1, 2, 3], 'qwe': {'a': 'b'}}
        d.field = data
        d.save()

        self.assertEqual(d.field, data)

@unittest.skipUnless(VERSION[0:3] < (1, 9, 0),
                     "Automatic fixture loading is not possible since syncdb was removed.")
class TestFixturesJSONField(unittest.TestCase):
    """
    DO NOT ADD ANYTHING INTO DATABASE IN THIS TESTCASE

    these tests are meant to test loading fixtures and dumping models
    initial_data.json fixture should be loaded automatically and tested if it's okay
    """
    # will be loaded from <APP>/fixtures/
    #fixtures = ['fixture.json']

    def test_fixture(self):
        """
        Basic assignment
        """
        d = DummyModel.objects.get(pk=1)
        try:
            # python 2.7+
            self.assertIsInstance(d.field, dict)
        except AttributeError:
            # python <2.7
            self.assertTrue(isinstance(d.field, dict))
        self.assertTrue('key' in d.field)
        self.assertEqual(d.field['key'], 'value')

    def test_dump(self):
        """
        Basic assignment
        """
        from django.core import serializers

        JSSerializer = serializers.get_serializer('json')
        js_serializer = JSSerializer()
        js = js_serializer.serialize(DummyModel.objects.all())
        js_des = json.loads(js)
        des_obj = js_des[0]
        self.assertEqual(des_obj['pk'], 1)
        self.assertEqual(json.loads(des_obj['fields']['field']), {'key': 'value', })

