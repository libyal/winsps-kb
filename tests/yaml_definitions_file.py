#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the YAML-based properties definitions file."""

import unittest

from winspsrc import yaml_definitions_file

from tests import test_lib


class YAMLPropertiesDefinitionsFileTest(test_lib.BaseTestCase):
  """Tests for the YAML-based properties definitions file."""

  # pylint: disable=protected-access

  _TEST_YAML = {
      'format_class': 'FMTID_IntSite',
      'format_identifier': '000214a1-0000-0000-c000-000000000046',
      'name': 'System.Status',
      'property_identifier': 9,
      'shell_property_key': 'PKEY_Status',
      'value_type': 'VT_LPWSTR'}

  def testReadPropertyDefinition(self):
    """Tests the _ReadPropertyDefinition function."""
    test_definitions_file = (
        yaml_definitions_file.YAMLPropertiesDefinitionsFile())

    definitions = test_definitions_file._ReadPropertyDefinition(self._TEST_YAML)

    self.assertIsNotNone(definitions)
    self.assertEqual(definitions.format_class, 'FMTID_IntSite')
    self.assertEqual(
        definitions.format_identifier, '000214a1-0000-0000-c000-000000000046')
    self.assertEqual(definitions.names, set(['System.Status']))
    self.assertEqual(definitions.property_identifier, 9)
    self.assertEqual(definitions.shell_property_keys, set(['PKEY_Status']))
    self.assertEqual(definitions.value_types, set(['VT_LPWSTR']))

    with self.assertRaises(RuntimeError):
      test_definitions_file._ReadPropertyDefinition({})

    with self.assertRaises(RuntimeError):
      test_definitions_file._ReadPropertyDefinition({
          'format_class': 'FMTID_IntSite',
          'name': 'System.Status',
          'property_identifier': 9,
          'shell_property_key': 'PKEY_Status',
          'value_type': 'VT_LPWSTR'})

    with self.assertRaises(RuntimeError):
      test_definitions_file._ReadPropertyDefinition({
          'format_class': 'FMTID_IntSite',
          'format_identifier': '000214a1-0000-0000-c000-000000000046',
          'name': 'System.Status',
          'shell_property_key': 'PKEY_Status',
          'value_type': 'VT_LPWSTR'})

    with self.assertRaises(RuntimeError):
      test_definitions_file._ReadPropertyDefinition({
          'bogus': 'test'})

  def testReadFromFileObject(self):
    """Tests the _ReadFromFileObject function."""
    test_file_path = self._GetTestFilePath(['properties.yaml'])
    self._SkipIfPathNotExists(test_file_path)

    test_definitions_file = (
        yaml_definitions_file.YAMLPropertiesDefinitionsFile())

    with open(test_file_path, 'r', encoding='utf-8') as file_object:
      definitions = list(test_definitions_file._ReadFromFileObject(file_object))

    self.assertEqual(len(definitions), 3)

  def testReadFromFile(self):
    """Tests the ReadFromFile function."""
    test_file_path = self._GetTestFilePath(['properties.yaml'])
    self._SkipIfPathNotExists(test_file_path)

    test_definitions_file = (
        yaml_definitions_file.YAMLPropertiesDefinitionsFile())

    definitions = list(test_definitions_file.ReadFromFile(test_file_path))

    self.assertEqual(len(definitions), 3)

    self.assertEqual(
        definitions[0].format_identifier,
        '00000000-0000-0000-0000-000000000000')
    self.assertEqual(
        definitions[2].format_identifier,
        'f29f85e0-4ff9-1068-ab91-08002b27b3d9')


if __name__ == '__main__':
  unittest.main()
