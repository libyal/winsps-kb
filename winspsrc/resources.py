# -*- coding: utf-8 -*-
"""Windows serialized property resources."""


class SerializedPropertyDefinition(object):
  """Windows serialized property definition.

  Attributes:
    aliases (set[str]): aliases that identify the property.
    format_class (str): name of the format class (or property set).
    format_identifier (str): identifier of the format class (or property set).
    names (set[str]): names that identify the property.
    property_identifier (int): identifier of the property within the format
        class (or property set).
    shell_property_keys (set[str]): keys that identify the property.
    value_type (str): value type used by the property.
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
    self.value_type = None

  @property
  def lookup_key(self):
    """str: lookup key."""
    return f'{{{self.format_identifier:s}}}/{self.property_identifier:d}'

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

    if not self.value_type and other.value_type:
      self.value_type = other.value_type
