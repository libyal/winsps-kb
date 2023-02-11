# -*- coding: utf-8 -*-
"""Binary data format."""

import abc
import os

from dtfabric import errors as dtfabric_errors
from dtfabric.runtime import data_maps as dtfabric_data_maps
from dtfabric.runtime import fabric as dtfabric_fabric

from winspsrc import errors


class BinaryDataFile(object):
  """Binary data file."""

  # The dtFabric fabric, which must be set by a subclass using the
  # ReadDefinitionFile class method.
  _FABRIC = None

  # Preserve the absolute path value of __file__ in case it is changed
  # at run-time.
  _DEFINITION_FILES_PATH = os.path.dirname(__file__)

  def __init__(self):
    """Initializes a binary data file."""
    super(BinaryDataFile, self).__init__()
    self._data_type_maps = {}
    self._file_object = None
    self._file_size = 0

  def _GetDataTypeMap(self, name):
    """Retrieves a data type map defined by the definition file.

    The data type maps are cached for reuse.

    Args:
      name (str): name of the data type as defined by the definition file.

    Returns:
      dtfabric.DataTypeMap: data type map which contains a data type definition,
          such as a structure, that can be mapped onto binary data.

    Raises:
      RuntimeError: if '_FABRIC' is not set.
    """
    if not getattr(self, '_FABRIC', None):
      raise RuntimeError('Missing _FABRIC value')

    data_type_map = self._data_type_maps.get(name, None)
    if not data_type_map:
      data_type_map = self._FABRIC.CreateDataTypeMap(name)
      self._data_type_maps[name] = data_type_map

    return data_type_map

  def _ReadData(self, file_object, file_offset, data_size, description):
    """Reads data.

    Args:
      file_object (file): a file-like object.
      file_offset (int): offset of the data relative to the start of
          the file-like object.
      data_size (int): size of the data.
      description (str): description of the data.

    Returns:
      bytes: byte stream containing the data.

    Raises:
      ParseError: if the data cannot be read.
      ValueError: if the file-like object is missing.
    """
    if not file_object:
      raise ValueError('Missing file-like object.')

    file_object.seek(file_offset, os.SEEK_SET)

    read_error = ''

    try:
      data = file_object.read(data_size)
      read_count = len(data)

      if read_count != data_size:
        read_error = (
            f'missing data (read: {read_count:d}, requested: {data_size:d})')

    except IOError as exception:
      read_error = f'{exception!s}'

    if read_error:
      raise errors.ParseError((
          f'Unable to read {description:s} data at offset: {file_offset:d} '
          f'(0x{file_offset:08x}) with error: {read_error:s}'))

    return data

  def _ReadStructureFromFileObject(
      self, file_object, file_offset, data_type_map, description):
    """Reads a structure from a file-like object.

    If the data type map has a fixed size this method will read the predefined
    number of bytes from the file-like object. If the data type map has a
    variable size, depending on values in the byte stream, this method will
    continue to read from the file-like object until the data type map can be
    successfully mapped onto the byte stream or until an error occurs.

    Args:
      file_object (file): a file-like object to parse.
      file_offset (int): offset of the structure data relative to the start
          of the file-like object.
      data_type_map (dtfabric.DataTypeMap): data type map of the structure.
      description (str): description of the structure.

    Returns:
      tuple[object, int]: structure values object and data size of
          the structure.

    Raises:
      ParseError: if the structure cannot be read.
      ValueError: if the file-like object is missing.
    """
    context = None
    data = b''
    last_data_size = 0

    data_size = data_type_map.GetSizeHint()
    while data_size != last_data_size:
      read_offset = file_offset + last_data_size
      read_size = data_size - last_data_size
      data_segment = self._ReadData(
          file_object, read_offset, read_size, description)

      data = b''.join([data, data_segment])

      try:
        context = dtfabric_data_maps.DataTypeMapContext()
        structure_values_object = data_type_map.MapByteStream(
            data, context=context)

        return structure_values_object, data_size

      except dtfabric_errors.ByteStreamTooSmallError:
        pass

      except dtfabric_errors.MappingError as exception:
        raise errors.ParseError((
            f'Unable to map {description:s} data at offset: {file_offset:d} '
            f'(0x{file_offset:08x}) with error: {exception!s}'))

      last_data_size = data_size
      data_size = data_type_map.GetSizeHint(context=context)

    raise errors.ParseError((
        f'Unable to read {description:s} at offset: {file_offset:d} '
        f'(0x{file_offset:08x})'))

  @classmethod
  def ReadDefinitionFile(cls, filename):
    """Reads a dtFabric definition file.

    Args:
      filename (str): name of the dtFabric definition file.

    Returns:
      dtfabric.DataTypeFabric: data type fabric which contains the data format
          data type maps of the data type definition, such as a structure, that
          can be mapped onto binary data or None if no filename is provided.
    """
    if not filename:
      return None

    path = os.path.join(cls._DEFINITION_FILES_PATH, filename)
    with open(path, 'rb') as file_object:
      definition = file_object.read()

    return dtfabric_fabric.DataTypeFabric(yaml_definition=definition)

  def Close(self):
    """Closes a binary data file.

    Raises:
      IOError: if the file is not opened.
      OSError: if the file is not opened.
    """
    if not self._file_object:
      raise IOError('File not opened')

    self._file_object = None
    self._file_size = 0

  def Open(self, file_object):
    """Opens a binary data file.

    Args:
      file_object (file): file-like object.

    Raises:
      IOError: if the file is already opened.
      OSError: if the file is already opened.
    """
    if self._file_object:
      raise IOError('File already opened')

    self._file_size = file_object.get_size()

    self.ReadFileObject(file_object)

    self._file_object = file_object

  @abc.abstractmethod
  def ReadFileObject(self, file_object):
    """Reads binary data from a file-like object.

    Args:
      file_object (file): file-like object.
    """
