"""
Tests for DataElement abstract interface class methods that provide
functionality.
"""
import hashlib
import unittest.mock as mock
import os.path as osp
import tempfile
from typing import Dict
import unittest

from smqtk_dataprovider import DataElement
from smqtk_dataprovider.exceptions import NoUriResolutionError, ReadOnlyError


# because this has a stable mimetype conversion
EXPECTED_CONTENT_TYPE = "image/png"
EXPECTED_BYTES = b"hello world"
EXPECTED_MD5 = hashlib.md5(EXPECTED_BYTES).hexdigest()
EXPECTED_SHA1 = hashlib.sha1(EXPECTED_BYTES).hexdigest()
EXPECTED_SHA512 = hashlib.sha512(EXPECTED_BYTES).hexdigest()
# UUID is currently set to be equivalent to SHA1 value by default
EXPECTED_UUID = EXPECTED_SHA1


# Caches the temp directory before we start mocking things out that would
# otherwise be required for the tempfile module to determine the temp
# directory.
tempfile.gettempdir()


# noinspection PyClassHasNoInit,PyAbstractClass
class DummyDataElement (DataElement):

    TEST_WRITABLE = True
    TEST_BYTES = EXPECTED_BYTES
    TEST_CONTENT_TYPE = EXPECTED_CONTENT_TYPE

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def __repr__(self) -> str:
        return super(DummyDataElement, self).__repr__()

    def get_config(self) -> Dict:
        return {}

    def content_type(self) -> str:
        return self.TEST_CONTENT_TYPE

    def is_empty(self) -> bool: ...  # type: ignore[empty-body]

    def get_bytes(self) -> bytes:
        return self.TEST_BYTES

    def set_bytes(self, b: bytes) -> None:
        super(DummyDataElement, self).set_bytes(b)
        self.TEST_BYTES = b

    def writable(self) -> bool:
        return self.TEST_WRITABLE


class TestDataElementAbstract (unittest.TestCase):

    def test_from_uri_default(self) -> None:
        self.assertRaises(
            NoUriResolutionError,
            DummyDataElement.from_uri, 'some uri'
        )

    def test_not_hashable(self) -> None:
        # Hash should be that of the UUID of the element
        de = DummyDataElement()
        self.assertRaises(TypeError, hash, de)

    def test_del(self) -> None:
        de = DummyDataElement()
        m_clean_temp = de.clean_temp = mock.Mock()  # type: ignore
        del de

        self.assertTrue(m_clean_temp.called)

    def test_equality(self) -> None:
        # equal when binary content is the same
        e1 = DummyDataElement()
        e2 = DummyDataElement()

        test_content_1 = b'some similar content'
        e1.TEST_BYTES = e2.TEST_BYTES = test_content_1
        self.assertEqual(e1, e2)

        test_content_2 = b'some other bytes'
        e2.TEST_BYTES = test_content_2
        self.assertNotEqual(e1, e2)

    def test_md5(self) -> None:
        de = DummyDataElement()
        md5 = de.md5()
        self.assertEqual(md5, EXPECTED_MD5)

    def test_sha1(self) -> None:
        de = DummyDataElement()
        sha1 = de.sha1()
        self.assertEqual(sha1, EXPECTED_SHA1)

    def test_sha512(self) -> None:
        de = DummyDataElement()
        sha1 = de.sha512()
        self.assertEqual(sha1, EXPECTED_SHA512)

    @mock.patch('smqtk_dataprovider.interfaces.data_element.safe_create_dir')
    @mock.patch('fcntl.fcntl')  # global
    @mock.patch('os.close')  # global
    @mock.patch('os.open')  # global
    @mock.patch("builtins.open")
    def test_content_type_extension(
        self,
        _mock_open: mock.MagicMock,
        _mock_os_open: mock.MagicMock,
        _mock_os_close: mock.MagicMock,
        _mock_fcntl: mock.MagicMock,
        _mock_scd: mock.MagicMock
    ) -> None:
        de = DummyDataElement()
        de.content_type = mock.Mock(return_value=None)  # type: ignore
        fname = de.write_temp()
        self.assertFalse(fname.endswith('.png'))

        fname = DummyDataElement().write_temp()
        self.assertTrue(fname.endswith('.png'))

    # Cases:
    #   - no existing temps, no specific dir
    #   - no existing temps, given specific dir
    #   - existing temps, no specific dir
    #   - existing temps, given specific dir
    #
    # Mocking open, os.open, os.close and fcntl to actual file interaction
    #   - os.open is used under the hood of tempfile to open a file (which also
    #       creates it on disk).

    @mock.patch('smqtk_dataprovider.interfaces.data_element.safe_create_dir')
    @mock.patch('fcntl.fcntl')  # global
    @mock.patch('os.close')  # global
    @mock.patch('os.open')  # global
    @mock.patch("builtins.open")
    def test_writeTemp_noExisting_noDir(self,
                                        mock_open: mock.MagicMock, _mock_os_open: mock.MagicMock,
                                        _mock_os_close: mock.MagicMock, _mock_fcntl: mock.MagicMock,
                                        mock_scd: mock.MagicMock) -> None:
        # no existing temps, no specific dir
        fp = DummyDataElement().write_temp()

        self.assertFalse(mock_scd.called)
        self.assertTrue(mock_open.called)
        self.assertEqual(osp.dirname(fp), tempfile.gettempdir())

    @mock.patch('smqtk_dataprovider.interfaces.data_element.safe_create_dir')
    @mock.patch('fcntl.fcntl')  # global
    @mock.patch('os.close')  # global
    @mock.patch('os.open')  # global
    @mock.patch("builtins.open")
    def test_writeTemp_noExisting_givenDir(self,
                                           mock_open: mock.MagicMock,
                                           _mock_os_open: mock.MagicMock,
                                           _mock_os_close: mock.MagicMock,
                                           _mock_fcntl: mock.MagicMock,
                                           mock_scd: mock.MagicMock) -> None:
        # no existing temps, given specific dir
        target_dir = '/some/dir/somewhere'

        fp = DummyDataElement().write_temp(target_dir)

        mock_scd.assert_called_once_with(target_dir)
        self.assertTrue(mock_open.called)
        self.assertNotEqual(osp.dirname(fp), tempfile.gettempdir())
        self.assertEqual(osp.dirname(fp), target_dir)

    @mock.patch("smqtk_dataprovider.interfaces.data_element.osp.isfile")
    @mock.patch('smqtk_dataprovider.interfaces.data_element.safe_create_dir')
    @mock.patch('fcntl.fcntl')  # global
    @mock.patch('os.close')  # global
    @mock.patch('os.open')  # global
    @mock.patch("builtins.open")
    def test_writeTemp_hasExisting_noDir(self,
                                         mock_open: mock.MagicMock,
                                         _mock_os_open: mock.MagicMock,
                                         _mock_os_close: mock.MagicMock,
                                         _mock_fcntl: mock.MagicMock,
                                         mock_scd: mock.MagicMock,
                                         mock_isfile: mock.MagicMock) -> None:
        # Pretend we have existing temps. Will to "write" a temp file to no
        # specific dir, which should not write anything new and just return the
        # last path in the list.
        prev_0 = '/tmp/file.txt'
        prev_1 = '/tmp/file_two.png'

        de = DummyDataElement()
        de._temp_filepath_stack.append(prev_0)
        de._temp_filepath_stack.append(prev_1)

        # Make sure os.path.isfile returns true so we think things in temp
        # stack exist.
        def osp_isfile_se(path: str) -> bool:
            if simulate and path in {prev_0, prev_1}:
                return True
            else:
                return False
        simulate = True
        mock_isfile.side_effect = osp_isfile_se

        fp = de.write_temp()

        self.assertFalse(mock_scd.called)
        self.assertFalse(mock_open.called)
        self.assertEqual(fp, prev_1)

        # _temp_filepath_stack files don't exist, so make sure isfile returns
        # false so clean_temp doesn't try to remove files that don't exist.
        simulate = False

    @mock.patch('smqtk_dataprovider.interfaces.data_element.safe_create_dir')
    @mock.patch('fcntl.fcntl')  # global
    @mock.patch('os.close')  # global
    @mock.patch('os.open')  # global
    @mock.patch("builtins.open")
    def test_writeTemp_hasExisting_givenNewDir(
        self,
        mock_open: mock.MagicMock,
        _mock_os_open: mock.MagicMock,
        _mock_os_close: mock.MagicMock,
        _mock_fcntl: mock.MagicMock,
        mock_scd: mock.MagicMock
    ) -> None:
        # existing temps, given specific dir
        prev_0 = '/tmp/file.txt'
        prev_1 = '/tmp/file_two.png'

        target_dir = '/some/specific/dir'

        de = DummyDataElement()
        de._temp_filepath_stack.append(prev_0)
        de._temp_filepath_stack.append(prev_1)

        fp = de.write_temp(temp_dir=target_dir)

        self.assertTrue(mock_scd.called)
        self.assertTrue(mock_open.called)
        self.assertEqual(osp.dirname(fp), target_dir)

    @mock.patch("smqtk_dataprovider.interfaces.data_element.osp.isfile")
    @mock.patch('smqtk_dataprovider.interfaces.data_element.safe_create_dir')
    @mock.patch('fcntl.fcntl')  # global
    @mock.patch('os.close')  # global
    @mock.patch('os.open')  # global
    @mock.patch("builtins.open")
    def test_writeTemp_hasExisting_givenExistingDir(
        self,
        mock_open: mock.MagicMock,
        _mock_os_open: mock.MagicMock,
        _mock_os_close: mock.MagicMock,
        _mock_fcntl: mock.MagicMock,
        mock_scd: mock.MagicMock,
        mock_isfile: mock.MagicMock
    ) -> None:
        # Pretend these files already exist as written temp files.
        # We test that write_temp with a target directory yields a previously
        #   "written" temp file.
        #
        # that given specific dir already in stack
        prev_0 = '/dir1/file.txt'
        prev_1 = '/tmp/things/file_two.png'
        prev_2 = '/some/specific/dir'

        def osp_isfile_se(path: str) -> bool:
            if simulate and path in {prev_0, prev_1, prev_2}:
                return True
            else:
                return False
        simulate = True
        mock_isfile.side_effect = osp_isfile_se

        de = DummyDataElement()
        de._temp_filepath_stack.append(prev_0)
        de._temp_filepath_stack.append(prev_1)
        de._temp_filepath_stack.append(prev_2)

        target_dir = "/tmp/things"

        # Make sure os.path.isfile returns true so we think things in temp
        # stack exist.
        mock_isfile.return_value = True

        fp = de.write_temp(temp_dir=target_dir)

        self.assertFalse(mock_scd.called)
        self.assertFalse(mock_open.called)
        self.assertEqual(fp, prev_1)

        # _temp_filepath_stack files don't exist, so make sure isfile returns
        # false so clean_temp doesn't try to remove files that don't exist.
        simulate = False

    @mock.patch("smqtk_dataprovider.interfaces.data_element.os")
    def test_cleanTemp_noTemp(self, mock_os: mock.MagicMock) -> None:
        # should do all of nothing
        de = DummyDataElement()

        de.clean_temp()

        self.assertFalse(mock_os.path.isfile.called)
        self.assertFalse(mock_os.remove.called)

    @mock.patch("smqtk_dataprovider.interfaces.data_element.os")
    def test_cleanTemp_hasTemp_badPath(self, mock_os: mock.MagicMock) -> None:
        de = DummyDataElement()
        de._temp_filepath_stack.append('tmp/thing')
        mock_os.path.isfile.return_value = False

        de.clean_temp()

        mock_os.path.isfile.assert_called_once_with('tmp/thing')
        self.assertFalse(mock_os.remove.called)

    @mock.patch("smqtk_dataprovider.interfaces.data_element.os")
    def test_cleanTemp_hasTemp_validPath(self, mock_os: mock.MagicMock) -> None:
        expected_path = '/tmp/something'

        de = DummyDataElement()
        de._temp_filepath_stack.append(expected_path)
        mock_os.path.isfile.return_value = True

        de.clean_temp()

        mock_os.path.isfile.assert_called_once_with(expected_path)
        mock_os.remove.assert_called_once_with(expected_path)

    def test_uuid(self) -> None:
        de = DummyDataElement()
        de.TEST_BYTES = EXPECTED_BYTES
        self.assertEqual(de.uuid(), EXPECTED_UUID)

    def test_to_buffered_reader(self) -> None:
        # Check that we get expected file-like returns.
        de = DummyDataElement()
        de.TEST_BYTES = EXPECTED_BYTES
        br = de.to_buffered_reader()
        self.assertEqual(br.readlines(), [b'hello world'])

        de.TEST_BYTES = b'some content\nwith new \nlines'
        br = de.to_buffered_reader()
        self.assertEqual(br.readlines(),
                         [b'some content\n',
                          b'with new \n',
                          b'lines'])

    def test_is_read_only(self) -> None:
        de = DummyDataElement()
        de.TEST_WRITABLE = True
        self.assertFalse(de.is_read_only())
        de.TEST_WRITABLE = False
        self.assertTrue(de.is_read_only())

    def test_set_bytes_not_writable(self) -> None:
        de = DummyDataElement()
        # trigger UUID cache at least once
        self.assertEqual(de.uuid(), EXPECTED_UUID)

        de.TEST_WRITABLE = False
        self.assertRaises(
            ReadOnlyError,
            de.set_bytes, b"test bytes"
        )

        # Caches shouldn't have been invalidated due to error
        self.assertEqual(de.uuid(), EXPECTED_UUID)

    def test_set_bytes_checksum_cache_invalidation(self) -> None:
        de = DummyDataElement()
        # trigger UUID cache at least once
        self.assertEqual(de.uuid(), EXPECTED_UUID)

        new_expected_bytes = b"some new byte content"
        new_expected_uuid = hashlib.sha1(new_expected_bytes).hexdigest()

        de.TEST_WRITABLE = True
        de.set_bytes(new_expected_bytes)

        # Caches should have been invalidated, so UUID return should now
        # reflect new byte content.
        self.assertNotEqual(de.uuid(), EXPECTED_UUID)
        self.assertEqual(de.uuid(), new_expected_uuid)
