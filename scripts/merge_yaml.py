#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to combine winsps-kb YAML files."""

import argparse
import glob
import os
import sys
import uuid
import yaml

from winspsrc import resources


class YAMLOutputWriter(object):
  """YAML output writer."""

  def __enter__(self):
    """Make this work with the 'with' statement."""
    return self

  def __exit__(self, exception_type, value, traceback):
    """Make this work with the 'with' statement."""

  def WritePropertyDefinition(self, property_definition):
    """Writes a property definition in YAML to stdout.

    Args:
      property_definition (SerializedPropertyDefinition): property definition.
    """
    print('---')

    if property_definition.aliases:
      aliases = ', '.join(sorted(property_definition.aliases))
      if len(property_definition.aliases) == 1:
        print(f'alias: {aliases:s}')
      else:
        print(f'alias: [{aliases:s}]')

    if property_definition.format_class:
      print(f'format_class: {property_definition.format_class:s}')

    print(f'format_identifier: {property_definition.format_identifier:s}')

    if property_definition.names:
      names = ', '.join(sorted(property_definition.names))
      if len(property_definition.names) == 1:
        print(f'name: {names:s}')
      else:
        print(f'name: [{names:s}]')

    print(f'property_identifier: {property_definition.property_identifier!s}')

    if property_definition.shell_property_keys:
      shell_property_keys = ', '.join(sorted(
          property_definition.shell_property_keys))
      if len(property_definition.shell_property_keys) == 1:
        print(f'shell_property_key: {shell_property_keys:s}')
      else:
        print(f'shell_property_key: [{shell_property_keys:s}]')

    if property_definition.value_types:
      value_types = []
      for value_type in property_definition.value_types:
        if isinstance(value_type, int):
          value_type = f'0x{value_type:04x}'
        value_types.append(value_type)

      value_types= ', '.join(sorted(value_types))
      if len(property_definition.value_types) == 1:
        print(f'value_type: {value_types:s}')
      else:
        print(f'value_type: [{value_types:s}]')


def Main():
  """Entry point of console script to combine winsps-kb YAML files.

  Returns:
    int: exit code that is provided to sys.exit().
  """
  argument_parser = argparse.ArgumentParser(description=(
      'Merges winsps-kb YAML files.'))

  argument_parser.add_argument(
      'source', nargs='?', action='store', metavar='PATH',
      default=None, help='path of a directory with winsps-kb YAML files.')

  options = argument_parser.parse_args()

  if not options.source:
    print('Source directory missing.')
    print('')
    argument_parser.print_help()
    print('')
    return 1

  property_definitions = {}

  for path in glob.glob(os.path.join(options.source, '*.yaml')):
    with open(path, 'r', encoding='utf8') as file_object:
      for yaml_definition in yaml.safe_load_all(file_object):
        alias = yaml_definition.get('alias', None)
        format_class = yaml_definition.get('format_class', None)
        format_identifier = yaml_definition.get('format_identifier', None)
        name = yaml_definition.get('name', None)
        property_identifier = yaml_definition.get('property_identifier', None)
        shell_property_key = yaml_definition.get('shell_property_key', None)
        value_type = yaml_definition.get('value_type', None)

        # Test if the format identifier is a GUID value.
        _ = uuid.UUID(format_identifier)

        lookup_key = f'{{{format_identifier:s}}}/{property_identifier:d}'

        property_definition = property_definitions.get(lookup_key, None)
        if not property_definition:
          property_definition = resources.SerializedPropertyDefinition()
          property_definition.format_identifier = format_identifier
          property_definition.property_identifier = property_identifier

          property_definitions[lookup_key] = property_definition

        if format_class and not property_definition.format_class:
          property_definition.format_class = format_class

        if alias:
          property_definition.aliases.add(alias)

        if name:
          property_definition.names.add(name)

        if shell_property_key:
          if shell_property_key.startswith('PKEY_'):
            property_definition.shell_property_keys.add(shell_property_key)
          else:
            property_definition.aliases.add(shell_property_key)

        if value_type and not property_definition.value_type:
          property_definition.value_type = value_type

  with YAMLOutputWriter() as yaml_writer:
    for property_definition in sorted(
        property_definitions.values(), key=lambda definition: (
            definition.format_identifier, definition.property_identifier)):
      yaml_writer.WritePropertyDefinition(property_definition)

  return 0


if __name__ == '__main__':
  sys.exit(Main())
