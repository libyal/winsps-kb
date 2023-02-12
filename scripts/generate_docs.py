#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to generate Windows serialized property documentation."""

import argparse
import logging
import os
import sys

from winspsrc import yaml_definitions_file


class IndexRstOutputWriter(object):
  """Index.rst output writer."""

  def __init__(self, path):
    """Initializes an index.rst output writer."""
    super(IndexRstOutputWriter, self).__init__()
    self._file_object = None
    self._path = path

  def __enter__(self):
    """Make this work with the 'with' statement."""
    self._file_object = open(self._path, 'w', encoding='utf-8')

    text = '\n'.join([
        '########################',
        'Serialized Property Sets',
        '########################',
        '',
        '.. toctree::',
        '   :maxdepth: 1',
        '',
        ''])
    self._file_object.write(text)

    return self

  def __exit__(self, exception_type, value, traceback):
    """Make this work with the 'with' statement."""
    self._file_object.close()
    self._file_object = None

  def WritePropertySet(self, format_identifier):
    """Writes a property set to the index.rst file.

    Args:
      format_identifier (str): format identifier.
    """
    self._file_object.write(
        f'   {format_identifier:s} <{format_identifier:s}>\n')


class MarkdownOutputWriter(object):
  """Markdown output writer."""

  def __init__(self, path):
    """Initializes a Markdown output writer."""
    super(MarkdownOutputWriter, self).__init__()
    self._file_object = None
    self._path = path

  def __enter__(self):
    """Make this work with the 'with' statement."""
    self._file_object = open(self._path, 'w', encoding='utf-8')
    return self

  def __exit__(self, exception_type, value, traceback):
    """Make this work with the 'with' statement."""
    self._file_object.close()
    self._file_object = None

  def WritePropertySet(self, property_set):
    """Writes a property set to a Markdown file.

    Args:
      property_set (list[SerializedPropertyDefinition]): property set.
    """
    format_identifier = property_set[0].format_identifier

    format_class = None
    for property_definition in property_set:
      if property_definition.format_class:
        format_class = property_definition.format_class
        break

    if format_class:
      page_header = f'## {format_identifier:s} ({format_class:s})'
    else:
      page_header = f'## {format_identifier:s}'

    table_header_values = [
        'Property identifier', 'Shell property key', 'Shell name', 'Alias']

    lines = [
        page_header,
        '',
        ' | '.join(table_header_values),
        ' | '.join(['---'] * len(table_header_values))]

    for property_definition in sorted(
        property_set, key=lambda definition: definition.property_identifier):
      table_row = ' | '.join([
          f'{property_definition.property_identifier:d}',
          ', '.join(sorted(property_definition.shell_property_keys)),
          ', '.join(sorted(property_definition.names)),
          ', '.join(sorted(property_definition.aliases))])

      lines.append(table_row)

    lines.extend([
        '',
        ''])

    text = '\n'.join(lines)
    self._file_object.write(text)


def Main():
  """The main program function.

  Returns:
    bool: True if successful or False if not.
  """
  argument_parser = argparse.ArgumentParser(description=(
      'Generated Windows serialized property documentation.'))

  argument_parser.parse_args()

  logging.basicConfig(
      level=logging.INFO, format='[%(levelname)s] %(message)s')

  definitions_file = yaml_definitions_file.YAMLPropertyDefinitionsFile()

  property_definitions = {}

  path = os.path.join('data', 'defined_properties.yaml')
  for property_definition in definitions_file.ReadFromFile(path):
    lookup_key = property_definition.lookup_key
    if lookup_key in property_definitions:
      property_definitions[lookup_key].Merge(property_definition)
    else:
      property_definitions[lookup_key] = property_definition

  path = os.path.join('data', 'observed_properties.yaml')
  for property_definition in definitions_file.ReadFromFile(path):
    lookup_key = property_definition.lookup_key
    if lookup_key in property_definitions:
      property_definitions[lookup_key].Merge(property_definition)
    else:
      property_definitions[lookup_key] = property_definition

  path = os.path.join('data', 'third_party_properties.yaml')
  for property_definition in definitions_file.ReadFromFile(path):
    lookup_key = property_definition.lookup_key
    if lookup_key in property_definitions:
      property_definitions[lookup_key].Merge(property_definition)
    else:
      property_definitions[lookup_key] = property_definition

  output_directory = os.path.join('docs', 'sources', 'property-sets')
  os.makedirs(output_directory, exist_ok=True)

  index_rst_file_path = os.path.join(output_directory, 'index.rst')
  with IndexRstOutputWriter(index_rst_file_path) as index_rst_writer:
    last_format_identifier = None
    property_set = []
    for _, property_definition in sorted(property_definitions.items()):
      if last_format_identifier != property_definition.format_identifier:
        if property_set:
          markdown_file_path = os.path.join(
              output_directory, f'{last_format_identifier:s}.md')
          with MarkdownOutputWriter(markdown_file_path) as markdown_writer:
            markdown_writer.WritePropertySet(property_set)

          property_set = []

          index_rst_writer.WritePropertySet(last_format_identifier)

        last_format_identifier = property_definition.format_identifier

      property_set.append(property_definition)

    if property_set:
      if property_set:
        markdown_file_path = os.path.join(
            output_directory, f'{last_format_identifier:s}.md')
        with MarkdownOutputWriter(markdown_file_path) as markdown_writer:
          markdown_writer.WritePropertySet(property_set)

      property_set = []

      index_rst_writer.WritePropertySet(last_format_identifier)

  return True


if __name__ == '__main__':
  if not Main():
    sys.exit(1)
  else:
    sys.exit(0)
