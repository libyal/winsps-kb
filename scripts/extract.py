#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to extract Windows serialized property information."""

import argparse
import logging
import os
import sys
import yaml

from dfvfs.helpers import command_line as dfvfs_command_line
from dfvfs.helpers import volume_scanner as dfvfs_volume_scanner
from dfvfs.lib import errors as dfvfs_errors

import winspsrc

from winspsrc import extractor
from winspsrc import yaml_definitions_file


def Main():
  """Entry point of console script to extract property information.

  Returns:
    int: exit code that is provided to sys.exit().
  """
  argument_parser = argparse.ArgumentParser(description=(
      'Extract Windows serialized property information.'))

  argument_parser.add_argument(
      '-d', '--debug', dest='debug', action='store_true', default=False,
      help='enable debug output.')

  argument_parser.add_argument(
      '-w', '--windows_version', '--windows-version',
      dest='windows_version', action='store', metavar='Windows XP',
      default=None, help='string that identifies the Windows version.')

  argument_parser.add_argument(
      'source', nargs='?', action='store', metavar='PATH', default=None, help=(
          'path of the volume containing C:\\Windows or the filename of '
          'a storage media image containing the C:\\Windows directory.'))

  options = argument_parser.parse_args()

  if not options.source:
    print('Source value is missing.')
    print('')
    argument_parser.print_help()
    print('')
    return 1

  try:
    with open(options.source, 'r', encoding='utf-8') as file_object:
      source_definitions = list(yaml.safe_load_all(file_object))

  except (SyntaxError, UnicodeDecodeError):
    source_definitions = [{
        'source': options.source, 'windows_version': options.windows_version}]

  logging.basicConfig(
      level=logging.INFO, format='[%(levelname)s] %(message)s')

  definitions_file = yaml_definitions_file.YAMLPropertiesDefinitionsFile()

  data_path = os.path.join(os.path.dirname(winspsrc.__file__), 'data')

  path = os.path.join(data_path, 'defined_properties.yaml')
  defined_property_definitions = {}
  for property_definition in definitions_file.ReadFromFile(path):
    lookup_key = property_definition.lookup_key
    if lookup_key not in defined_property_definitions:
      defined_property_definitions[lookup_key] = property_definition

  path = os.path.join(data_path, 'observed_properties.yaml')
  observed_property_definitions = {}
  for property_definition in definitions_file.ReadFromFile(path):
    lookup_key = property_definition.lookup_key
    if lookup_key not in observed_property_definitions:
      observed_property_definitions[lookup_key] = property_definition

  path = os.path.join(data_path, 'third_party_properties.yaml')
  third_party_property_definitions = {}
  for property_definition in definitions_file.ReadFromFile(path):
    lookup_key = property_definition.lookup_key
    if lookup_key not in third_party_property_definitions:
      third_party_property_definitions[lookup_key] = property_definition

  mediator = dfvfs_command_line.CLIVolumeScannerMediator()

  volume_scanner_options = dfvfs_volume_scanner.VolumeScannerOptions()
  volume_scanner_options.partitions = ['all']
  volume_scanner_options.snapshots = ['none']
  volume_scanner_options.volumes = ['none']

  serialized_properties = {}
  defined_serialized_properties = {}
  observed_serialized_properties = {}
  third_party_serialized_properties = {}
  unknown_serialized_properties = {}

  for source_definition in source_definitions:
    source_path = source_definition['source']
    logging.info(f'Processing: {source_path:s}')

    extractor_object = extractor.SerializedPropertyExtractor(
        debug=options.debug, mediator=mediator)

    try:
      result = extractor_object.ScanForWindowsVolume(
          source_path, options=volume_scanner_options)
    except dfvfs_errors.ScannerError:
      result = False

    if not result:
      print((f'Unable to retrieve the volume with the Windows directory '
             f'from: {source_path:s}.'))
      print('')
      return 1

    if extractor_object.windows_version:
      windows_version = extractor_object.windows_version
      logging.info(f'Detected Windows version: {windows_version:s}')

      if source_definition['windows_version']:
        windows_version = source_definition['windows_version']

    else:
      print('Unable to determine Windows version.')

      windows_version = source_definition['windows_version']

    for serialized_property in extractor_object.CollectSerializedProperies():
      lookup_key = serialized_property.lookup_key
      if lookup_key in serialized_properties:
        # TODO: check if property is different from existing
        continue

      serialized_properties[lookup_key] = serialized_property

      property_definition = observed_property_definitions.get(lookup_key, None)
      if property_definition:
        observed_serialized_properties[lookup_key] = serialized_property
        continue

      property_definition = defined_property_definitions.get(lookup_key, None)
      if property_definition:
        defined_serialized_properties[lookup_key] = serialized_property
        continue

      property_definition = third_party_property_definitions.get(
          lookup_key, None)
      if property_definition:
        third_party_serialized_properties[lookup_key] = serialized_property
        continue

      unknown_serialized_properties[lookup_key] = serialized_property

  if observed_serialized_properties:
    print('Observed properties:')
    for lookup_key, serialized_property in sorted(
        observed_serialized_properties.items()):
      property_definition = observed_property_definitions.get(lookup_key, None)

      print(f'\t{lookup_key:s}', end='')
      if property_definition and property_definition.shell_property_keys:
        shell_property_keys = ', '.join(property_definition.shell_property_keys)
        print(f' ({shell_property_keys:s})', end='')

      if serialized_property.value_type:
        print(f' [0x{serialized_property.value_type:04x}]', end='')
        if not property_definition or serialized_property.value_type not in (
            property_definition.value_types):
          print(' (undefined value type)', end='')

      print('')

    print('')

  if defined_serialized_properties:
    print('Defined properties:')
    for lookup_key, serialized_property in sorted(
        defined_serialized_properties.items()):
      property_definition = defined_property_definitions.get(lookup_key, None)

      print(f'\t{lookup_key:s}', end='')
      if property_definition and property_definition.shell_property_keys:
        shell_property_keys = ', '.join(property_definition.shell_property_keys)
        print(f' ({shell_property_keys:s})', end='')

      if serialized_property.value_type:
        print(f' [0x{serialized_property.value_type:04x}]', end='')
        if not property_definition or serialized_property.value_type not in (
            property_definition.value_types):
          print(' (undefined value type)', end='')

      print('')

    print('')

  if third_party_serialized_properties:
    print('Third party properties:')
    for lookup_key, serialized_property in sorted(
        third_party_serialized_properties.items()):
      property_definition = third_party_property_definitions.get(
          lookup_key, None)

      print(f'\t{lookup_key:s}', end='')
      if property_definition and property_definition.shell_property_keys:
        shell_property_keys = ', '.join(property_definition.shell_property_keys)
        print(f' ({shell_property_keys:s})', end='')

      if serialized_property.value_type:
        print(f' [0x{serialized_property.value_type:04x}]', end='')
        if not property_definition or serialized_property.value_type not in (
            property_definition.value_types):
          print(' (undefined value type)', end='')

      print('')

    print('')

  if unknown_serialized_properties:
    print('Unknown properties:')
    for lookup_key, serialized_property in sorted(
        unknown_serialized_properties.items()):
      print((
          f'\t{lookup_key:s} [0x{serialized_property.value_type:04x}]'
          f' ({serialized_property.origin:s})'))

    print('')

  return 0


if __name__ == '__main__':
  sys.exit(Main())
