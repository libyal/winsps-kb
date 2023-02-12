# -*- coding: utf-8 -*-
"""Windows serialized property extractor."""

import logging

import pyfwps
import pylnk
import pyolecf
import pysigscan

from dfimagetools import windows_registry

from dfvfs.helpers import volume_scanner as dfvfs_volume_scanner
from dfvfs.resolver import resolver as dfvfs_resolver

from dfwinreg import registry as dfwinreg_registry

from winspsrc import errors
from winspsrc import jump_list
from winspsrc import resource_file


class SerializedProperty(object):
  """Windows serialized property.

  Attributes:
    format_identifier (str): format class (or property set) identifier.
    property_identifier (int): identifier of the property within the format
        class (or property set).
    origin (str): path of the file from which the property originates.
    value_type (int): value type used by the property.
  """

  def __init__(self):
    """Initializes a Windows serialized property."""
    super(SerializedProperty, self).__init__()
    self.format_identifier = None
    self.property_identifier = None
    self.origin = None
    self.value_type = None

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

    # Custom Destinations Jump List (.customDestinations-ms) file.
    scanner_object.add_signature(
        'custom_destination', 4, b'\xab\xfb\xbf\xba',
        pysigscan.signature_flags.RELATIVE_FROM_END)

    # Windows Shortcut (LNK) file.
    scanner_object.add_signature(
        'lnk', 4, self._LNK_SIGNATURE,
        pysigscan.signature_flags.RELATIVE_FROM_START)

    # OLE Compound File (OLECF).
    scanner_object.add_signature(
        'olecf', 0, b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',
        pysigscan.signature_flags.RELATIVE_FROM_START)

    # beta version of OLE Compound File (OLECF).
    scanner_object.add_signature(
        'olecf_beta', 0, b'\x0e\x11\xfc\x0d\xd0\xcf\x11\x0e',
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

  def _CollectSerializedProperiesFromAutomaticDestinationsFile(
      self, file_object, path_segments):
    """Retrieves serialized properties from a .automaticDestinations-ms file.

    Args:
      file_object (dfvfs.FileIO): file-like object.
      path_segments (str): path segments of the full path of the file entry.

    Yields:
      SerializedProperty: serialized property.
    """
    jump_list_file = jump_list.AutomaticDestinationsFile()

    olecf_file = pyolecf.file()
    olecf_item = None

    try:
      olecf_file.open_file_object(file_object)
      try:
        if olecf_file.root_item:  # pylint: disable=using-constant-test
          olecf_item = olecf_file.root_item.get_sub_item_by_name('DestList')  # pylint: disable=no-member
      finally:
        olecf_file.close()

    except IOError as exception:
      path = '\\'.join(path_segments)
      logging.warning(f'Unable to open: {path:s} with error: {exception!s}')

    if olecf_item:
      try:
        jump_list_file.Open(file_object)
        try:
          for jump_list_entry in jump_list_file.GetJumpListEntries():
            yield from self._CollectSerializedProperiesFromLNK(
                jump_list_entry.lnk_file)

        finally:
          jump_list_file.Close()

      except errors.ParseError as exception:
        path = '\\'.join(path_segments)
        logging.warning((f'Unable to parse .automaticDestinations-ms file: '
                         f'{path:s} with error: {exception!s}'))

  def _CollectSerializedProperiesFromCustomDestinationsFile(
      self, file_object, path_segments):
    """Retrieves serialized properties from a .customDestinations-ms file.

    Args:
      file_object (dfvfs.FileIO): file-like object.
      path_segments (str): path segments of the full path of the file entry.

    Yields:
      SerializedProperty: serialized property.
    """
    jump_list_file = jump_list.CustomDestinationsFile()

    try:
      jump_list_file.Open(file_object)

      try:
        for jump_list_entry in jump_list_file.GetJumpListEntries():
          yield from self._CollectSerializedProperiesFromLNK(
              jump_list_entry.lnk_file)

      finally:
        jump_list_file.Close()

    except errors.ParseError as exception:
      path = '\\'.join(path_segments)
      logging.warning((f'Unable to parse .customDestinations-ms file: '
                       f'{path:s} with error: {exception!s}'))

  def _CollectSerializedProperiesFromLNK(self, lnk_file):
    """Retrieves serialized properties from a Windows Shortcut (LNK).

    Args:
      lnk_file (pylnk.file): Windows Shortcut (LNK) file.

    Yields:
      SerializedProperty: serialized property.
    """
    for lnk_data_block in iter(lnk_file.data_blocks):
      if lnk_data_block.signature == 0xa0000009:
        fwps_store = pyfwps.store()
        fwps_store.copy_from_byte_stream(lnk_data_block.data)

        for fwps_set in iter(fwps_store.sets):
          for fwps_record in iter(fwps_set.records):
            serialized_property = SerializedProperty()
            serialized_property.format_identifier = fwps_set.identifier
            serialized_property.property_identifier = fwps_record.entry_type
            serialized_property.value_type = fwps_record.value_type

            yield serialized_property

  def _CollectSerializedProperiesFromLNKFile(self, file_object):
    """Retrieves serialized properties from a Windows Shortcut (LNK) file.

    Args:
      file_object (dfvfs.FileIO): file-like object.

    Yields:
      SerializedProperty: serialized property.
    """
    lnk_file = pylnk.file()
    lnk_file.open_file_object(file_object)

    try:
      yield from self._CollectSerializedProperiesFromLNK(lnk_file)

    finally:
      lnk_file.close()

  def CollectSerializedProperies(self):
    """Retrieves serialized properties.

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

        try:
          self._format_scanner.scan_file_object(scan_state, file_object)
          scan_results = [
              scan_result.identifier
              for scan_result in iter(scan_state.scan_results)]
        except IOError as exception:
          path = '\\'.join(path_segments)
          logging.warning(f'Unable to open: {path:s} with error: {exception!s}')

      generator = None
      if 'custom_destination' in scan_results:
        generator = self._CollectSerializedProperiesFromCustomDestinationsFile(
            file_object, path_segments)

      elif 'lnk' in scan_results:
        generator = self._CollectSerializedProperiesFromLNKFile(file_object)

      elif 'olecf' in scan_results:
        generator = (
            self._CollectSerializedProperiesFromAutomaticDestinationsFile(
                file_object, path_segments))

      # TODO: add support for shell item formats

      if generator:
        for serialized_property in generator:
          serialized_property.origin = '\\'.join(path_segments)
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
