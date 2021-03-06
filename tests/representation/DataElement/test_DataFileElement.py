import os
from tests import TEST_DATA_DIR
import unittest
import unittest.mock as mock

from smqtk_core.configuration import configuration_test_helper
from smqtk_dataprovider import from_uri
from smqtk_dataprovider.exceptions import InvalidUriError, ReadOnlyError
from smqtk_dataprovider.impls.data_element.file import DataFileElement


class TestDataFileElement (unittest.TestCase):

    def test_init_filepath_abs(self) -> None:
        fp = '/foo.txt'
        d = DataFileElement(fp)
        self.assertEqual(d._filepath, fp)

    def test_init_relFilepath_normal(self) -> None:
        # relative paths should be stored as given within the element
        fp = 'foo.txt'
        d = DataFileElement(fp)
        self.assertEqual(d._filepath, fp)

    def test_content_type(self) -> None:
        d = DataFileElement('foo.txt')
        self.assertEqual(d.content_type(), 'text/plain')

    def test_content_type_explicit_type(self) -> None:
        ex_type = 'image/png'
        d = DataFileElement('foo.txt', explicit_mimetype=ex_type)
        self.assertEqual(d.content_type(), ex_type)

    @mock.patch('smqtk_dataprovider.interfaces.data_element.DataElement.write_temp')
    def test_writeTempOverride(self, mock_DataElement_wt: mock.MagicMock) -> None:
        # no manual directory, should return the base filepath
        expected_filepath = '/path/to/file.txt'
        d = DataFileElement(expected_filepath)
        fp = d.write_temp()

        self.assertFalse(mock_DataElement_wt.called)
        self.assertEqual(expected_filepath, fp)

    @mock.patch('smqtk_dataprovider.interfaces.data_element.DataElement.write_temp')
    def test_writeTempOverride_sameDir(self, mock_DataElement_wt: mock.MagicMock) -> None:
        expected_filepath = '/path/to/file.txt'
        target_dir = '/path/to'

        d = DataFileElement(expected_filepath)
        fp = d.write_temp(temp_dir=target_dir)

        self.assertFalse(mock_DataElement_wt.called)
        self.assertEqual(fp, expected_filepath)

    @mock.patch('smqtk_dataprovider.interfaces.data_element.DataElement.write_temp')
    def test_writeTempOverride_diffDir(self, mock_DataElement_wt: mock.MagicMock) -> None:
        """
        Test that adding ``temp_dir`` parameter triggers call to parent class
        """
        source_filepath = '/path/to/file.png'
        target_dir = '/some/other/dir'

        d = DataFileElement(source_filepath)

        # Should call parent class write_temp since target is not the same dir
        # that the source file is in.
        mock_DataElement_wt.return_value = 'expected'
        v = d.write_temp(temp_dir=target_dir)
        self.assertEqual(v, 'expected')
        mock_DataElement_wt.assert_called_with(target_dir)

    def test_cleanTemp(self) -> None:
        # a write temp and clean temp should not affect original file
        source_file = os.path.join(TEST_DATA_DIR, 'test_file.dat')
        self.assertTrue(os.path.isfile(source_file))
        d = DataFileElement(source_file)
        d.write_temp()
        self.assertEqual(len(d._temp_filepath_stack), 0)
        d.clean_temp()
        self.assertTrue(os.path.isfile(source_file))

    def test_configuration(self) -> None:
        fp = os.path.join(TEST_DATA_DIR, "grace_hopper.png")
        inst = DataFileElement(filepath=fp, readonly=True,
                               explicit_mimetype='foo/bar')
        for i in configuration_test_helper(inst):  # type: DataFileElement
            assert i._filepath == fp
            assert i._readonly is True
            assert i._explicit_mimetype == 'foo/bar'

    def test_repr(self) -> None:
        e = DataFileElement('foo')
        self.assertEqual(repr(e),
                         "DataFileElement{filepath: foo, readonly: False, "
                         "explicit_mimetype: None}")

        e = DataFileElement('bar', readonly=True)
        self.assertEqual(repr(e),
                         "DataFileElement{filepath: bar, readonly: True, "
                         "explicit_mimetype: None}")

        e = DataFileElement('baz', readonly=True, explicit_mimetype='some/type')
        self.assertEqual(repr(e),
                         "DataFileElement{filepath: baz, readonly: True, "
                         "explicit_mimetype: some/type}")

    def test_from_uri_invalid_uri_empty(self) -> None:
        # Given empty string
        self.assertRaises(
            InvalidUriError,
            DataFileElement.from_uri,
            ''
        )

    def test_from_uri_invalid_uri_malformed_rel_directory(self) -> None:
        # URI malformed: relative path trailing slash (directory)
        self.assertRaises(
            InvalidUriError,
            DataFileElement.from_uri,
            "some/rel/path/dir/"
        )

    def test_from_uri_invalid_uri_malformed_abs_directory(self) -> None:
        # URI malformed: absolute path trailing slash (directory)
        self.assertRaises(
            InvalidUriError,
            DataFileElement.from_uri,
            "/abs/path/dir/"
        )

    def test_from_uri_invalid_uri_malformed_bad_header(self) -> None:
        # URI malformed: file:// malformed

        # Missing colon
        self.assertRaises(
            InvalidUriError,
            DataFileElement.from_uri,
            "file///some/file/somewhere.txt"
        )

        # file misspelled
        self.assertRaises(
            InvalidUriError,
            DataFileElement.from_uri,
            "fle:///some/file/somewhere.txt"
        )

    def test_from_uri_invalid_uri_malformed_header_rel_path(self) -> None:
        # URL malformed: file:// not given ABS path
        self.assertRaises(
            InvalidUriError,
            DataFileElement.from_uri,
            "file://some/rel/path.txt"
        )

    # noinspection PyUnresolvedReferences
    def test_from_uri(self) -> None:
        # will be absolute path
        test_file_path = os.path.join(TEST_DATA_DIR, "test_file.dat")
        print("Test file path:", test_file_path)

        e = DataFileElement.from_uri(test_file_path)
        self.assertIsInstance(e, DataFileElement)
        self.assertEqual(e._filepath, test_file_path)
        self.assertEqual(e.get_bytes(), b"")

        e = DataFileElement.from_uri('file://' + test_file_path)
        self.assertIsInstance(e, DataFileElement)
        self.assertEqual(e._filepath, test_file_path)
        self.assertEqual(e.get_bytes(), b"")

    # noinspection PyUnresolvedReferences
    def test_from_uri_plugin_level(self) -> None:
        # will be absolute path
        test_file_path = os.path.join(TEST_DATA_DIR, "test_file.dat")
        print("Test file path:", test_file_path)

        e = from_uri(test_file_path)
        assert isinstance(e, DataFileElement)
        self.assertEqual(e._filepath, test_file_path)
        self.assertEqual(e.get_bytes(), b"")

        e = from_uri('file://' + test_file_path)
        assert isinstance(e, DataFileElement)
        self.assertEqual(e._filepath, test_file_path)
        self.assertEqual(e.get_bytes(), b"")

    def test_is_empty_file_not_exists(self) -> None:
        e = DataFileElement('/no/exists')
        self.assertTrue(e.is_empty())

    def test_is_empty_file_zero_data(self) -> None:
        e = DataFileElement(os.path.join(TEST_DATA_DIR, 'test_file.dat'))
        self.assertTrue(e.is_empty())

    def test_is_empty_file_has_data(self) -> None:
        e = DataFileElement(os.path.join(TEST_DATA_DIR, 'grace_hopper.png'))
        self.assertFalse(e.is_empty())

    def test_get_bytes_no_file(self) -> None:
        e = DataFileElement("/not/a/valid/path.txt", readonly=True)
        # We currently expect, in the case where the filepath doesn't exist, to
        # get the same bytes as if the file existed and were empty.
        self.assertEqual(e.get_bytes(), b"")
        # read-only status should have no effect.
        e = DataFileElement("/not/a/valid/path.txt", readonly=True)
        self.assertEqual(e.get_bytes(), b"")

    def test_get_bytes(self) -> None:
        # Test with a known real file.
        test_file_path = os.path.join(TEST_DATA_DIR, 'text_file')
        e = DataFileElement(test_file_path)
        self.assertEqual(e.get_bytes(), b"Some text content.\n")

    def test_writable_readonly_false(self) -> None:
        e = DataFileElement('foo')
        self.assertTrue(e.writable())

        e = DataFileElement('foo', False)
        self.assertTrue(e.writable())

        e = DataFileElement('foo', readonly=False)
        self.assertTrue(e.writable())

    def test_writable_readonly_true(self) -> None:
        e = DataFileElement('foo', True)
        self.assertFalse(e.writable())

        e = DataFileElement('foo', readonly=True)
        self.assertFalse(e.writable())

    @mock.patch('smqtk_dataprovider.impls.data_element.file.safe_file_write')
    def test_set_bytes_writable(self, m_sfw: mock.MagicMock) -> None:
        # Using a relative filepath
        test_path = 'foo'
        test_bytes = b"test string of bytes"

        e = DataFileElement(test_path)
        e.set_bytes(test_bytes)

        # File write function should be called
        m_sfw.assert_called_once_with(test_path, test_bytes)

    def test_set_bytes_readonly(self) -> None:
        e = DataFileElement('foo', readonly=True)
        self.assertRaises(
            ReadOnlyError,
            e.set_bytes,
            b"some bytes"
        )
