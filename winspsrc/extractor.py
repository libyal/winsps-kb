# -*- coding: utf-8 -*-
"""Windows serialized property extractor."""

import logging

import pyfwps
import pylnk
import pysigscan

from dfimagetools import windows_registry

from dfvfs.helpers import volume_scanner as dfvfs_volume_scanner
from dfvfs.resolver import resolver as dfvfs_resolver

from dfwinreg import registry as dfwinreg_registry

from winspsrc import resource_file


class SerializedProperty(object):
  """Windows serialized property.

  Attributes:
    format_identifier (str): format class (or property set) identifier.
    property_identifier (int): identifier of the property within the format
        class (or property set).
  """

  def __init__(self):
    """Initializes a Windows serialized property."""
    super(SerializedProperty, self).__init__()
    self.format_identifier = None
    self.property_identifier = None

  @property
  def lookup_key(self):
    """str: lookup key."""
    return f'{{{self.format_identifier:s}}}/{self.property_identifier:d}'


class SerializedPropertyExtractor(dfvfs_volume_scanner.WindowsVolumeScanner):
  """Windows serialized property extractor.

  Attributes:
    ascii_codepage (str): ASCII string codepage.
    preferred_language_identifier (int): preferred language identifier (LCID).
  """

  _LNK_SIGNATURE = (
      b'\x01\x14\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46')

  def __init__(self, debug=False, mediator=None):
    """Initializes a Windows serialized property extractor.

    Args:
      debug (Optional[bool]): True if debug information should be printed.
      mediator (dfvfs.VolumeScannerMediator): a volume scanner mediator or None.
    """
    super(SerializedPropertyExtractor, self).__init__(mediator=mediator)
    self._debug = debug
    self._format_scanner = None
    self._registry = None
    self._windows_version = None

    self.ascii_codepage = 'cp1252'
    self.preferred_language_identifier = 0x0409

  @property
  def windows_version(self):
    """The Windows version (getter)."""
    if self._windows_version is None:
      self._windows_version = self._GetWindowsVersion()
    return self._windows_version

  @windows_version.setter
  def windows_version(self, value):
    """The Windows version (setter)."""
    self._windows_version = value

  def _CreateFormatScanner(self):
    """Creates a signature scanner for required format check."""
    scanner_object = pysigscan.scanner()
    scanner_object.set_scan_buffer_size(65536)

    scanner_object.add_signature(
        'lnk', 4, self._LNK_SIGNATURE,
        pysigscan.signature_flags.RELATIVE_FROM_START)

    self._format_scanner = scanner_object

  def _GetSystemRoot(self):
    """Determines the value of %SystemRoot%.

    Returns:
      str: value of SystemRoot or None if the value cannot be determined.
    """
    current_version_key = self._registry.GetKeyByPath(
        'HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Windows NT\\CurrentVersion')

    system_root = None
    if current_version_key:
      system_root_value = current_version_key.GetValueByName('SystemRoot')
      if system_root_value:
        system_root = system_root_value.GetDataAsObject()

    if not system_root:
      system_root = self._windows_directory

    return system_root

  def _GetWindowsVersion(self):
    """Determines the Windows version from kernel executable file.

    Returns:
      str: Windows version or None otherwise.
    """
    system_root = self._GetSystemRoot()

    # Window NT variants.
    kernel_executable_path = '\\'.join([
        system_root, 'System32', 'ntoskrnl.exe'])
    message_file = self._OpenMessageResourceFile(kernel_executable_path)

    if not message_file:
      # Window 9x variants.
      kernel_executable_path = '\\'.join([
          system_root, 'System32', '\\kernel32.dll'])
      message_file = self._OpenMessageResourceFile(kernel_executable_path)

    if not message_file:
      return None

    return message_file.file_version

  def _ListFileEntry(self, file_entry, parent_path_segments):
    """Lists a file entry.

    Args:
      file_entry (dfvfs.FileEntry): file entry to list.
      parent_path_segments (str): path segments of the full path of the parent
          file entry.

    Yields:
      tuple[dfvfs.FileEntry, list[str]]: file entry and path segments.
    """
    path_segments = list(parent_path_segments)
    if not file_entry.IsRoot():
      path_segments.append(file_entry.name)

    if file_entry.IsFile():
      yield file_entry, path_segments

    for sub_file_entry in file_entry.sub_file_entries:
      for result in self._ListFileEntry(sub_file_entry, path_segments):
        yield result

  def _ListFileEntries(self):
    """Lists file entries.

    Yields:
      tuple[dfvfs.FileEntry, list[str]]: file entry and path segments.
    """
    file_entry = self._file_system.GetRootFileEntry()

    for result in self._ListFileEntry(file_entry, ['']):
      yield result

  def _OpenMessageResourceFile(self, windows_path):
    """Opens the message resource file specified by the Windows path.

    Args:
      windows_path (str): Windows path containing the message resource
          filename.

    Returns:
      MessageResourceFile: message resource file or None.
    """
    path_spec = self._path_resolver.ResolvePath(windows_path)
    if path_spec is None:
      return None

    return self._OpenMessageResourceFileByPathSpec(path_spec)

  def _OpenMessageResourceFileByPathSpec(self, path_spec):
    """Opens the message resource file specified by the path specification.

    Args:
      path_spec (dfvfs.PathSpec): path specification.

    Returns:
      MessageResourceFile: message resource file or None.
    """
    windows_path = self._path_resolver.GetWindowsPath(path_spec)
    if windows_path is None:
      logging.warning('Unable to retrieve Windows path.')

    try:
      file_object = dfvfs_resolver.Resolver.OpenFileObject(path_spec)
    except IOError as exception:
      logging.warning(
          f'Unable to open: {path_spec.comparable:s} with error: {exception!s}')
      file_object = None

    if file_object is None:
      return None

    message_file = resource_file.MessageResourceFile(
        windows_path, ascii_codepage=self.ascii_codepage,
        preferred_language_identifier=self.preferred_language_identifier)
    message_file.OpenFileObject(file_object)

    return message_file

  def _CollectSerializedProperiesFromLNK(self, file_object):
    """Retrieves the serialized properties from a Windows Shortcut (LNK).

    Args:
      file_object (dfvfs.FileIO): file-like object.

    Yields:
      SerializedProperty: serialized property.
    """
    pylnk_file = pylnk.file()
    pylnk_file.open_file_object(file_object)

    for data_block in iter(pylnk_file.data_blocks):
      if data_block.signature == 0xa0000009:
        pyfwps_store = pyfwps.store()
        pyfwps_store.copy_from_byte_stream(data_block.data)

        for pyfwps_set in iter(pyfwps_store.sets):
          for pyfwps_record in iter(pyfwps_set.records):
            serialized_property = SerializedProperty()
            serialized_property.format_identifier = pyfwps_set.identifier
            serialized_property.property_identifier = pyfwps_record.entry_type

            yield serialized_property

    pylnk_file.close()

  def CollectSerializedProperies(self):
    """Retrieves the serialized properties.

    Yields:
      SerializedProperty: serialized property.
    """
    if not self._format_scanner:
      self._CreateFormatScanner()

    for file_entry, path_segments in self._ListFileEntries():
      file_object = file_entry.GetFileObject()

      scan_results = []
      if file_object:
        scan_state = pysigscan.scan_state()
        self._format_scanner.scan_file_object(scan_state, file_object)
        scan_results = [
            scan_result.identifier
            for scan_result in iter(scan_state.scan_results)]

      generator = None
      if scan_results == ['lnk']:
        generator = self._CollectSerializedProperiesFromLNK(file_object)

      # TODO: add support for jump list formats
      # TODO: add support for shell item formats
      _ = path_segments

      if generator:
        for serialized_property in generator:
          yield serialized_property

  def ScanForWindowsVolume(self, source_path, options=None):
    """Scans for a Windows volume.

    Args:
      source_path (str): source path.
      options (Optional[VolumeScannerOptions]): volume scanner options. If None
          the default volume scanner options are used, which are defined in the
          VolumeScannerOptions class.

    Returns:
      bool: True if a Windows volume was found.

    Raises:
      ScannerError: if the source path does not exists, or if the source path
          is not a file or directory, or if the format of or within
          the source file is not supported.
    """
    result = super(SerializedPropertyExtractor, self).ScanForWindowsVolume(
        source_path, options=options)
    if not result:
      return False

    registry_file_reader = (
        windows_registry.StorageMediaImageWindowsRegistryFileReader(
            self._file_system, self._path_resolver))
    self._registry = dfwinreg_registry.WinRegistry(
        registry_file_reader=registry_file_reader)

    return True