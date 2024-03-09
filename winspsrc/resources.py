# -*- coding: utf-8 -*-
"""Windows serialized property resources."""


class SerializedPropertyDefinition(object):
  """Windows serialized property definition.

  Attributes:
    aliases (set[str]): aliases that identify the property.
    format_class (str): name of the format class (or property set).
    format_identifier (str): identifier of the format class (or property set).
    names (set[str]): names that identify the property.
    property_identifier (int|str): identifier of the property within the format
        class (or property set).
    shell_property_keys (set[str]): keys that identify the property.
    value_types (set[str]): value types used by the property.
  """

  def __init__(self):
    """Initializes a Windows serialized property definition."""
    super(SerializedPropertyDefinition, self).__init__()
    self.aliases = set()
    self.format_class = None
    self.format_identifier = None
    self.names = set()
    self.property_identifier = None
    self.shell_property_keys = set()
    self.value_types = set()

  @property
  def lookup_key(self):
    """str: lookup key."""
    property_identifier = self.property_identifier
    if isinstance(property_identifier, int):
      property_identifier = f'{property_identifier:d}'

    return f'{{{self.format_identifier:s}}}/{property_identifier:s}'

  def Merge(self, other):
    """Merges the values of another property definition into the current one.

    Args:
      other (SerializedPropertyDefinition): property definition to merge values
          from.
    """
    if not self.format_class and other.format_class:
      self.format_class = other.format_class

    self.aliases.update(other.aliases)
    self.names.update(other.names)
    self.shell_property_keys.update(other.shell_property_keys)
    self.value_types.update(other.value_types)
