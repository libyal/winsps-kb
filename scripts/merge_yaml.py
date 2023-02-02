#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to parse merge winsps-kb YAML files."""

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
    name (str): name that identifiers the property.
    property_identifier (int): identifier of the property within the format
        class (or property set).
    shell_property_key (str): key that identifies the property.
  """

  def __init__(self):
    """Initializes a Windows Serialized Property definition."""
    super(PropertyDefinitions, self).__init__()
    self.format_identifier = None
    self.name = None
    self.property_identifier = None
    self.shell_property_key = None


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
          property_definition.name = name
          property_definition.property_identifier = property_identifier
          property_definition.shell_property_key = shell_property_key

          property_definitions[lookup_key] = property_definition

          continue

        if name:
          if not property_definition.name:
            property_definition.name = name
          elif property_definition.name != name:
            print((f'{lookup_key:s} has multiple names: '
                   f'{property_definition.name:s}, {name:s}'))

        if shell_property_key:
          if not property_definition.shell_property_key:
            property_definition.shell_property_key = shell_property_key
          elif property_definition.shell_property_key != shell_property_key:
            print((f'{lookup_key:s} has multiple shell property keys: '
                   f'{property_definition.shell_property_key:s}, '
                   f'{shell_property_key:s}'))


  return True


if __name__ == '__main__':
  if not Main():
    sys.exit(1)
  else:
    sys.exit(0)
