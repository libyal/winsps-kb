#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to combine winsps-kb YAML files."""

import argparse
import glob
import os
import sys
import uuid
import yaml


class PropertyDefinitions(object):
  """Windows Serialized Property definition.

  Attributes:
    format_identifier (str): format class (or property set) identifier.
    names (set[str]): names that identify the property.
    property_identifier (int): identifier of the property within the format
        class (or property set).
    shell_property_keys (set[str]): keys that identify the property.
  """

  def __init__(self):
    """Initializes a Windows Serialized Property definition."""
    super(PropertyDefinitions, self).__init__()
    self.format_identifier = None
    self.names = set()
    self.property_identifier = None
    self.shell_property_keys = set()


def Main():
  """The main program function.

  Returns:
    bool: True if successful or False if not.
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
    return False

  property_definitions = {}

  for path in glob.glob(os.path.join(options.source, '*.yaml')):
    with open(path, 'r', encoding='utf8') as file_object:
      for yaml_definition in yaml.safe_load_all(file_object):
        format_identifier = yaml_definition.get('format_identifier', None)
        name = yaml_definition.get('name', None)
        property_identifier = yaml_definition.get('property_identifier', None)
        shell_property_key = yaml_definition.get('shell_property_key', None)

        # Test if the format identifier is a GUID value.
        _ = uuid.UUID(format_identifier)

        lookup_key = f'{{{format_identifier:s}}}/{property_identifier:d}'

        property_definition = property_definitions.get(lookup_key, None)
        if not property_definition:
          property_definition = PropertyDefinitions()
          property_definition.format_identifier = format_identifier
          property_definition.property_identifier = property_identifier

          property_definitions[lookup_key] = property_definition

        if name:
          property_definition.names.add(name)

        if shell_property_key:
          property_definition.shell_property_keys.add(shell_property_key)

  print('# winsps-kb property definitions')
  for _, property_definition in sorted(property_definitions.items()):
    print('---')
    print(f'format_identifier: {property_definition.format_identifier:s}')

    if property_definition.names:
      names = ', '.join(sorted(property_definition.names))
      if len(property_definition.names) == 1:
        print(f'name: {names:s}')
      else:
        print(f'name: [{names:s}]')

    print(f'property_identifier: {property_definition.property_identifier:d}')

    if property_definition.shell_property_keys:
      shell_property_keys = ', '.join(sorted(
          property_definition.shell_property_keys))
      if len(property_definition.shell_property_keys) == 1:
        print(f'shell_property_key: {shell_property_keys:s}')
      else:
        print(f'shell_property_key: [{shell_property_keys:s}]')

  return True


if __name__ == '__main__':
  if not Main():
    sys.exit(1)
  else:
    sys.exit(0)
