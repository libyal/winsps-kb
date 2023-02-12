# -*- coding: utf-8 -*-
"""YAML-based property definitions file."""

import yaml

from winspsrc import resources


class YAMLPropertyDefinitionsFile(object):
  """YAML-based property definitions file.

  A YAML-based property definitions file contains one or more property
  definitions. An property definition consists of:

  format_identifier: 00000000-0000-0000-0000-000000000000
  name: System.Null
  property_identifier: 0
  shell_property_key: PKEY_Null
  value_type: VT_NULL

  Where:
  * alias, defines one or more aliases that identify the property;
  * format_class, name of the format class (or property set);
  * format_identifier, identifier of the format class (or property set);
  * name, defines one or more names that identify the property;
  * property_identifier, defines he property within the format class (or
      property set).
  * shell_property_key, defines one or more shell properties key that identify
      the property;
  * value_type, defines one or more value types used by the property.
  """

  _SUPPORTED_KEYS = frozenset([
      'alias',
      'format_class',
      'format_identifier',
      'name',
      'property_identifier',
      'shell_property_key',
      'value_type'])

  def _ReadPropertyDefinition(self, yaml_property_definition):
    """Reads an event formatter definition from a dictionary.

    Args:
      yaml_property_definition (dict[str, object]): YAML property definition
           values.

    Returns:
      SerializedPropertyDefinition: property definition.

    Raises:
      RuntimeError: if the format of the formatter definition is not set
          or incorrect.
    """
    if not yaml_property_definition:
      raise RuntimeError('Missing property definition values.')

    different_keys = set(yaml_property_definition) - self._SUPPORTED_KEYS
    if different_keys:
      different_keys = ', '.join(different_keys)
      raise RuntimeError('Undefined keys: {0:s}'.format(different_keys))

    format_identifier = yaml_property_definition.get('format_identifier', None)
    if not format_identifier:
      raise RuntimeError(
          'Invalid property definition missing format identifier.')

    property_identifier = yaml_property_definition.get(
        'property_identifier', None)
    if not format_identifier:
      raise RuntimeError(
          'Invalid property definition missing property identifier.')

    property_definition = resources.SerializedPropertyDefinition()
    property_definition.format_class = yaml_property_definition.get(
        'format_class', None)
    property_definition.format_identifier = format_identifier
    property_definition.property_identifier = property_identifier

    alias = yaml_property_definition.get('alias', None)
    if alias and isinstance(alias, list):
      property_definition.aliases = set(alias)
    elif alias:
      property_definition.aliases = set([alias])

    name = yaml_property_definition.get('name', None)
    if name and isinstance(name, list):
      property_definition.names = set(name)
    elif name:
      property_definition.names = set([name])

    shell_property_key = yaml_property_definition.get(
        'shell_property_key', None)
    if shell_property_key and isinstance(shell_property_key, list):
      property_definition.shell_property_keys = set(shell_property_key)
    elif shell_property_key:
      property_definition.shell_property_keys = set([shell_property_key])

    return property_definition

  def _ReadFromFileObject(self, file_object):
    """Reads the event formatters from a file-like object.

    Args:
      file_object (file): formatters file-like object.

    Yields:
      SerializedPropertyDefinition: property definition.
    """
    yaml_generator = yaml.safe_load_all(file_object)

    for yaml_property_definition in yaml_generator:
      yield self._ReadPropertyDefinition(yaml_property_definition)

  def ReadFromFile(self, path):
    """Reads the event formatters from a YAML file.

    Args:
      path (str): path to a formatters file.

    Yields:
      SerializedPropertyDefinition: property definition.
    """
    with open(path, 'r', encoding='utf-8') as file_object:
      for yaml_property_definition in self._ReadFromFileObject(file_object):
        yield yaml_property_definition
