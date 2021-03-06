import errno
import os
import unittest
import unittest.mock as mock

from smqtk_dataprovider.utils.file import safe_create_dir


class TestSafeCreateDir (unittest.TestCase):

    @mock.patch('smqtk_dataprovider.utils.file.os.makedirs')
    def test_noExists(self, mock_os_makedirs: mock.MagicMock) -> None:
        dir_path = "/some/directory/somewhere"
        p = safe_create_dir(dir_path)

        self.assertTrue(mock_os_makedirs.called)
        self.assertEqual(p, dir_path)

    @mock.patch('smqtk_dataprovider.utils.file.os.path.exists')
    @mock.patch('smqtk_dataprovider.utils.file.os.makedirs')
    def test_existError_alreadyExists(
        self,
        mock_os_makedirs: mock.MagicMock,
        mock_osp_exists: mock.MagicMock
    ) -> None:
        mock_os_makedirs.side_effect = OSError(errno.EEXIST,
                                               "Existing directory")

        mock_osp_exists.return_value = True

        dir_path = '/existing/dir'
        p = safe_create_dir(dir_path)

        self.assertTrue(mock_os_makedirs.called)
        self.assertTrue(mock_osp_exists.called)
        mock_osp_exists.assert_called_once_with(dir_path)
        self.assertEqual(p, dir_path)

    @mock.patch('smqtk_dataprovider.utils.file.os.path.exists')
    @mock.patch('smqtk_dataprovider.utils.file.os.makedirs')
    def test_existError_noExist(
        self,
        mock_os_makedirs: mock.MagicMock,
        mock_osp_exists: mock.MagicMock
    ) -> None:
        mock_os_makedirs.side_effect = OSError(errno.EEXIST,
                                               "Existing directory")
        mock_osp_exists.return_value = False

        dir_path = '/some/dir'
        self.assertRaises(OSError, safe_create_dir, dir_path)

        mock_os_makedirs.assert_called_once_with(dir_path)
        mock_osp_exists.assert_called_once_with(dir_path)

    @mock.patch('smqtk_dataprovider.utils.file.os.path.exists')
    @mock.patch('smqtk_dataprovider.utils.file.os.makedirs')
    def test_otherOsError(
        self,
        mock_os_makedirs: mock.MagicMock,
        mock_osp_exists: mock.MagicMock
    ) -> None:
        mock_os_makedirs.side_effect = OSError(errno.EACCES,
                                               "Permission Denied")

        dir_path = '/some/dir'
        self.assertRaises(OSError, safe_create_dir, dir_path)

        mock_os_makedirs.assert_called_once_with(dir_path)
        self.assertFalse(mock_osp_exists.called)

    @mock.patch('smqtk_dataprovider.utils.file.os.makedirs')
    def test_otherException(self, mock_os_makedirs: mock.MagicMock) -> None:
        mock_os_makedirs.side_effect = RuntimeError("Some other exception")

        dir_path = 'something'
        self.assertRaises(RuntimeError, safe_create_dir, dir_path)

        mock_os_makedirs.assert_called_once_with(os.path.abspath(dir_path))
