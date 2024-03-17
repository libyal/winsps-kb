#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to resolve names of Windows serialized property keys."""

import argparse
import logging
import os
import sys

import pywintypes  # pylint:disable=import-error

from win32com.propsys import propsys  # pylint:disable=import-error

import winspsrc

from winspsrc import yaml_definitions_file


class YAMLOutputWriter(object):
  """YAML output writer."""

  def __init__(self, path):
    """Initializes a YAML output writer."""
    super(YAMLOutputWriter, self).__init__()
    self._file_object = None
    self._path = path

  def __enter__(self):
    """Make this work with the 'with' statement."""
    # Set newline to force Windows to generate newline character only.
    self._file_object = open(
        self._path, 'w', encoding='utf-8', newline='')
    self._file_object.write('# winsps-kb property definitions\n')

    return self

  def __exit__(self, exception_type, value, traceback):
    """Make this work with the 'with' statement."""
    self._file_object.close()
    self._file_object = None

  def WritePropertyDefinition(self, property_definition):
    """Writes a property definition to the YAML file.

    Args:
      property_definition (SerializedPropertyDefinition): property definition.
    """
    self._file_object.write('---\n')

    if property_definition.aliases:
      aliases = ', '.join(sorted(property_definition.aliases))
      if len(property_definition.aliases) == 1:
        self._file_object.write(f'alias: {aliases:s}\n')
      else:
        self._file_object.write(f'alias: [{aliases:s}]\n')

    if property_definition.format_class:
      self._file_object.write(
          f'format_class: {property_definition.format_class:s}\n')

    self._file_object.write(
        f'format_identifier: {property_definition.format_identifier:s}\n')

    if property_definition.names:
      names = ', '.join(sorted(property_definition.names))
      if len(property_definition.names) == 1:
        self._file_object.write(f'name: {names:s}\n')
      else:
        self._file_object.write(f'name: [{names:s}]\n')

    self._file_object.write(
        f'property_identifier: {property_definition.property_identifier!s}\n')

    if property_definition.shell_property_keys:
      shell_property_keys = ', '.join(sorted(
          property_definition.shell_property_keys))
      if len(property_definition.shell_property_keys) == 1:
        self._file_object.write(
            f'shell_property_key: {shell_property_keys:s}\n')
      else:
        self._file_object.write(
            f'shell_property_key: [{shell_property_keys:s}]\n')

    if property_definition.value_types:
      value_types = []
      for value_type in property_definition.value_types:
        if isinstance(value_type, int):
          value_type = f'0x{value_type:04x}'
        value_types.append(value_type)

      value_types= ', '.join(sorted(value_types))
      if len(property_definition.value_types) == 1:
        self._file_object.write(f'value_type: {value_types:s}\n')
      else:
        self._file_object.write(f'value_type: [{value_types:s}]\n')


def Main():
  """Entry point of console script to resolve names.

  Returns:
    int: exit code that is provided to sys.exit().
  """
  argument_parser = argparse.ArgumentParser(description=(
      'Resolve names of Windows serialized property keys.'))

  argument_parser.parse_args()

  logging.basicConfig(
      level=logging.INFO, format='[%(levelname)s] %(message)s')

  definitions_file = yaml_definitions_file.YAMLPropertiesDefinitionsFile()

  property_definitions = {}

  data_path = os.path.join(os.path.dirname(winspsrc.__file__), 'data')

  path = os.path.join(data_path, 'defined_properties.yaml')
  for property_definition in definitions_file.ReadFromFile(path):
    lookup_key = property_definition.lookup_key
    if lookup_key in property_definitions:
      property_definitions[lookup_key].Merge(property_definition)
    else:
      property_definitions[lookup_key] = property_definition

  with YAMLOutputWriter(path) as yaml_writer:
    for property_definition in sorted(
        property_definitions.values(), key=lambda definition: (
            definition.format_identifier, definition.property_identifier)):
      if not property_definition.names and isinstance(
          property_definition.property_identifier, int):
        proprty_key = (
            f'{{{property_definition.format_identifier:s}}}',
            property_definition.property_identifier)

        try:
          name = propsys.PSGetNameFromPropertyKey(proprty_key)
        except pywintypes.com_error:
          logging.warning(
              f'Unable to resolve: {property_definition.lookup_key}')
          name = None

        if name:
          property_definition.names = set([name])

      yaml_writer.WritePropertyDefinition(property_definition)

  return 0


if __name__ == '__main__':
  sys.exit(Main())
