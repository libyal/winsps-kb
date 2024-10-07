# -*- coding: utf-8 -*-
"""Windows serialized property extractor."""

import logging

# TODO: add CREG support

import pyfwps
import pyfwsi
import pylnk
import pyolecf
import pyregf
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
    property_identifier (str): identifier of the property within the format
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
    return f'{{{self.format_identifier:s}}}/{self.property_identifier:s}'


class SerializedPropertyExtractor(dfvfs_volume_scanner.WindowsVolumeScanner):
  """Windows serialized property extractor.

  Attributes:
    ascii_codepage (str): ASCII string codepage.
    preferred_language_identifier (int): preferred language identifier (LCID).
  """

  _LNK_GUID = (
      b'\x01\x14\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46')

  _SHELL_ITEM_MRU_KEY_PATHS = [
      '\\Local Settings\\Software\\Microsoft\\Windows\\Shell\\BagMRU',
      '\\Local Settings\\Software\\Microsoft\\Windows\\ShellNoRoam\\BagMRU',
      '\\Software\\Microsoft\\Windows\\Shell\\BagMRU',
      '\\Software\\Microsoft\\Windows\\ShellNoRoam\\BagMRU',
      ('\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\'
       'Shell\\BagMRU'),
      ('\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\'
       'ShellNoRoam\\BagMRU'),
      ('\\Software\\Classes\\Wow6432Node\\Local Settings\\Software\\'
       'Microsoft\\Windows\\Shell\\BagMRU'),
      ('\\Software\\Classes\\Wow6432Node\\Local Settings\\Software\\'
       'Microsoft\\Windows\\ShellNoRoam\\BagMRU')]

  _SHELL_ITEM_MRU_KEY_PATHS = [
      key_path.upper() for key_path in _SHELL_ITEM_MRU_KEY_PATHS]

  _SHELL_ITEM_LIST_MRU_KEY_PATHS = [
      ('\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\'
       'DesktopStreamMRU'),
      ('\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ComDlg32\\'
       'OpenSavePidlMRU'),
      '\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StreamMRU']

  _SHELL_ITEM_LIST_MRU_KEY_PATHS = [
      key_path.upper() for key_path in _SHELL_ITEM_LIST_MRU_KEY_PATHS]

  _STRING_AND_SHELL_ITEM_MRU_KEY_PATHS = [
      '\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RecentDocs']

  _STRING_AND_SHELL_ITEM_MRU_KEY_PATHS = [
      key_path.upper() for key_path in _STRING_AND_SHELL_ITEM_MRU_KEY_PATHS]

  _STRING_AND_SHELL_ITEM_LIST_MRU_KEY_PATHS = [
      ('\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ComDlg32\\'
       'LastVisitedPidlMRU')]

  _STRING_AND_SHELL_ITEM_LIST_MRU_KEY_PATHS = [
      key_path.upper()
      for key_path in _STRING_AND_SHELL_ITEM_LIST_MRU_KEY_PATHS]

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
        'lnk', 4, self._LNK_GUID, pysigscan.signature_flags.RELATIVE_FROM_START)

    # OLE Compound File (OLECF).
    scanner_object.add_signature(
        'olecf', 0, b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',
        pysigscan.signature_flags.RELATIVE_FROM_START)

    # beta version of OLE Compound File (OLECF).
    scanner_object.add_signature(
        'olecf_beta', 0, b'\x0e\x11\xfc\x0d\xd0\xcf\x11\x0e',
        pysigscan.signature_flags.RELATIVE_FROM_START)

    # Windows NT Registry File (REGF).
    scanner_object.add_signature(
        'regf', 0, b'regf', pysigscan.signature_flags.RELATIVE_FROM_START)

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

    # Windows NT variants.
    kernel_executable_path = '\\'.join([
        system_root, 'System32', 'ntoskrnl.exe'])
    windows_resource_file = self._OpenWindowsResourceFile(
        kernel_executable_path)

    if not windows_resource_file:
      # Windows 9x variants.
      kernel_executable_path = '\\'.join([
          system_root, 'System32', '\\kernel32.dll'])
      windows_resource_file = self._OpenWindowsResourceFile(
          kernel_executable_path)

    if not windows_resource_file:
      return None

    return windows_resource_file.file_version

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
      yield from self._ListFileEntry(sub_file_entry, path_segments)

  def _ListFileEntries(self):
    """Lists file entries.

    Yields:
      tuple[dfvfs.FileEntry, list[str]]: file entry and path segments.
    """
    file_entry = self._file_system.GetRootFileEntry()

    yield from self._ListFileEntry(file_entry, [''])

  def _OpenWindowsResourceFile(self, windows_path):
    """Opens the Windows resource file specified by the Windows path.

    Args:
      windows_path (str): Windows path of the Windows resource file.

    Returns:
      WindowsResourceFile: Windows resource file or None.
    """
    path_spec = self._path_resolver.ResolvePath(windows_path)
    if path_spec is None:
      return None

    return self._OpenWindowsResourceFileByPathSpec(path_spec)

  def _OpenWindowsResourceFileByPathSpec(self, path_spec):
    """Opens the Windows resource file specified by the path specification.

    Args:
      path_spec (dfvfs.PathSpec): path specification.

    Returns:
      WindowsResourceFile: Windows resource file or None.
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

    windows_resource_file = resource_file.WindowsResourceFile(
        windows_path, ascii_codepage=self.ascii_codepage,
        preferred_language_identifier=self.preferred_language_identifier)
    windows_resource_file.OpenFileObject(file_object)

    return windows_resource_file

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
    if lnk_file.link_target_identifier_data:
      fwsi_item_list = pyfwsi.item_list()
      fwsi_item_list.copy_from_byte_stream(
          lnk_file.link_target_identifier_data)

      yield from self._CollectSerializedProperiesFromShellItemList(
          fwsi_item_list)

    for lnk_data_block in iter(lnk_file.data_blocks):
      if lnk_data_block.signature == 0xa0000009 and lnk_data_block.data:
        fwps_store = pyfwps.store()
        fwps_store.copy_from_byte_stream(lnk_data_block.data)

        yield from self._CollectSerializedProperiesFromPropertyStore(fwps_store)

  def _CollectSerializedProperiesFromLNKFile(self, file_object, path_segments):
    """Retrieves serialized properties from a Windows Shortcut (LNK) file.

    Args:
      file_object (dfvfs.FileIO): file-like object.
      path_segments (str): path segments of the full path of the file entry.

    Yields:
      SerializedProperty: serialized property.
    """
    lnk_file = pylnk.file()

    try:
      lnk_file.open_file_object(file_object)
    except IOError as exception:
      path = '\\'.join(path_segments)
      logging.warning(f'Unable to open: {path:s} with error: {exception!s}')

    try:
      yield from self._CollectSerializedProperiesFromLNK(lnk_file)

    except IOError as exception:
      path = '\\'.join(path_segments)
      logging.warning((
          f'Unable to collect serialized properties from: {path:s} with '
          f'error: {exception!s}'))

    finally:
      lnk_file.close()

  def _CollectSerializedProperiesFromPropertyStore(self, fwps_store):
    """Retrieves serialized properties from a property store.

    Args:
      fwps_store (pyfwps.store): property store.

    Yields:
      SerializedProperty: serialized property.
    """
    for fwps_set in iter(fwps_store.sets):
      for fwps_record in iter(fwps_set.records):

        if fwps_record.entry_name:
          property_identifier = fwps_record.entry_name
        else:
          property_identifier = f'{fwps_record.entry_type:d}'

        serialized_property = SerializedProperty()
        serialized_property.format_identifier = fwps_set.identifier
        serialized_property.property_identifier = property_identifier
        serialized_property.value_type = fwps_record.value_type

        yield serialized_property

  def _CollectSerializedProperiesFromREGFFile(self, file_object, path_segments):
    """Retrieves serialized properties from a Windows NT Registry File (REGF).

    Args:
      file_object (dfvfs.FileIO): file-like object.
      path_segments (str): path segments of the full path of the file entry.

    Yields:
      SerializedProperty: serialized property.
    """
    regf_file = pyregf.file()

    try:
      regf_file.open_file_object(file_object)
    except IOError as exception:
      path = '\\'.join(path_segments)
      logging.warning(f'Unable to open: {path:s} with error: {exception!s}')

    try:
      regf_root_key = regf_file.get_root_key()
      if regf_root_key:
        # Ignore the name of the root key.
        yield from self._CollectSerializedProperiesFromREGFKey(
            [''], regf_root_key)

    except IOError as exception:
      path = '\\'.join(path_segments)
      logging.warning((
          f'Unable to collect serialized properties from: {path:s} with '
          f'error: {exception!s}'))

    finally:
      regf_file.close()

  def _CollectSerializedProperiesFromREGFKey(self, key_path_segments, regf_key):
    """Retrieves serialized properties from a Windows NT Registry key.

    Args:
      key_path_segments (list[str]): key path segments.
      regf_key (pyregf.key): Windows NT Registry key.

    Yields:
      SerializedProperty: serialized property.
    """
    value_names = [regf_value.name for regf_value in regf_key.values]

    if 'MRUList' in value_names or 'MRUListEx' in value_names:
      yield from self._CollectSerializedProperiesFromREGFKeyWithMRU(
          key_path_segments, regf_key)

    for regf_sub_key in regf_key.sub_keys:
      key_path_segments.append(regf_sub_key.name)

      try:
        yield from self._CollectSerializedProperiesFromREGFKey(
            key_path_segments, regf_sub_key)
      finally:
        key_path_segments.pop(-1)

  def _CollectSerializedProperiesFromREGFKeyWithMRU(
      self, key_path_segments, regf_key):
    """Retrieves serialized properties from a Registry key with a MRU.

    Args:
      key_path_segments (list[str]): key path segments.
      regf_key (pyregf.key): Windows NT Registry key.

    Yields:
      SerializedProperty: serialized property.
    """
    key_path = '\\'.join(key_path_segments).upper()

    if self._InKeyPaths(key_path, self._SHELL_ITEM_MRU_KEY_PATHS):
      known_key_type = 'shell-item'
    elif self._InKeyPaths(key_path, self._SHELL_ITEM_LIST_MRU_KEY_PATHS):
      known_key_type = 'shell-item-list'
    elif self._InKeyPaths(key_path, self._STRING_AND_SHELL_ITEM_MRU_KEY_PATHS):
      known_key_type = 'string-and-shell-item'
    elif self._InKeyPaths(
        key_path, self._STRING_AND_SHELL_ITEM_LIST_MRU_KEY_PATHS):
      known_key_type = 'string-and-shell-item-list'
    else:
      known_key_type = None

    if known_key_type:
      for regf_value in regf_key.values:
        if not regf_value.data or regf_value.name in (
            'MRUList', 'MRUListEx', 'NodeSlot', 'NodeSlots', 'ViewStream'):
          continue

        data_offset = 0
        data_size = len(regf_value.data)
        if known_key_type.startswith('string-and-shell-item'):
          for data_offset in range(0, data_size, 2):
            if regf_value.data[data_offset:data_offset + 2] == b'\0\0':
              data_offset += 2
              break

        if data_offset >= data_size:
          continue

        data = regf_value.data[data_offset:]

        if known_key_type.endswith('shell-item'):
          fwsi_item = pyfwsi.item()
          fwsi_item.copy_from_byte_stream(data)

          yield from self._CollectSerializedProperiesFromShellItem(fwsi_item)

        elif known_key_type.endswith('shell-item-list'):
          fwsi_item_list = pyfwsi.item_list()
          fwsi_item_list.copy_from_byte_stream(data)

          yield from self._CollectSerializedProperiesFromShellItemList(
              fwsi_item_list)

  def _CollectSerializedProperiesFromShellItem(self, fwsi_item):
    """Retrieves serialized properties from a shell item.

    Args:
      fwsi_item (pyfwsi.item): shell item.

    Yields:
      SerializedProperty: serialized property.
    """
    if isinstance(fwsi_item, pyfwsi.users_property_view):
      if fwsi_item.property_store_data:
        fwps_store = pyfwps.store()
        fwps_store.copy_from_byte_stream(fwsi_item.property_store_data)

        yield from self._CollectSerializedProperiesFromPropertyStore(fwps_store)

  def _CollectSerializedProperiesFromShellItemList(self, fwsi_item_list):
    """Retrieves serialized properties from a shell item list.

    Args:
      fwsi_item_list (pyfwsi.item_list): shell item list.

    Yields:
      SerializedProperty: serialized property.
    """
    for fwsi_item in fwsi_item_list.items:
      yield from self._CollectSerializedProperiesFromShellItem(fwsi_item)

  def _InKeyPaths(self, key_path_upper, key_paths):
    """Checks if a specific key path is defined in a list of key paths.

    Args:
      key_path_upper (list[str]): key path in upper case.
      key_paths (list[str]): list of Windows Registry key paths in upper case.

    Returns:
      bool: True if the key path is defined in the list of key paths.
    """
    for matching_key_path in key_paths:
      if key_path_upper.startswith(matching_key_path):
        return True

    return False

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
        generator = self._CollectSerializedProperiesFromLNKFile(
            file_object, path_segments)

      elif 'olecf' in scan_results:
        generator = (
            self._CollectSerializedProperiesFromAutomaticDestinationsFile(
                file_object, path_segments))

      elif 'regf' in scan_results:
        generator = self._CollectSerializedProperiesFromREGFFile(
            file_object, path_segments)

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
