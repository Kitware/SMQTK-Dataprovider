import unittest.mock as mock
import os
import requests
from tests import TEST_DATA_DIR
import unittest

from smqtk_core.configuration import configuration_test_helper
from smqtk_dataprovider.exceptions import InvalidUriError, ReadOnlyError
from smqtk_dataprovider.impls.data_element.url import DataUrlElement


# Check to see if we have an internet connection.
internet_available = True
try:
    r = requests.get('https://data.kitware.com')
    _ = r.content
except requests.ConnectionError:
    internet_available = False


class TestDataUrlElement (unittest.TestCase):
    """

    :NOTE: Some of these tests require a connection to the internet in order to
        pass.

    """

    # Public domain Lenna image from Wikipedia, same as local test image file
    EXAMPLE_URL = \
        'https://data.kitware.com/api/v1/file/6025ba632fa25629b964a1bd/download'
    EXAMPLE_PTH = os.path.join(TEST_DATA_DIR, 'grace_hopper.png')

    def test_is_usable(self) -> None:
        # Should always be available, because local/intranet networks are a
        # thing.
        self.assertTrue(DataUrlElement.is_usable())

    @mock.patch('smqtk_dataprovider.impls.data_element.url.requests.get')
    def test_configuration(self, m_req_get: mock.MagicMock) -> None:
        # Mocking requests usage to no actually head into the network.
        inst = DataUrlElement(self.EXAMPLE_URL)
        for i in configuration_test_helper(inst):  # type: DataUrlElement
            assert i._url == self.EXAMPLE_URL

    @unittest.skipUnless(internet_available, "Internet not accessible")
    def test_new_from_internet(self) -> None:
        e = DataUrlElement(self.EXAMPLE_URL)
        self.assertEqual(e.get_bytes(), open(self.EXAMPLE_PTH, 'rb').read())

    def test_new_invalid_url(self) -> None:
        self.assertRaises(
            requests.ConnectionError,
            DataUrlElement,
            'https://not.a.real.host/'
        )

    @unittest.skipUnless(internet_available, "Internet not accessible")
    def test_content_type(self) -> None:
        e = DataUrlElement(self.EXAMPLE_URL)
        self.assertEqual(e.content_type(), 'image/png')

    @unittest.skipUnless(internet_available, "Internet not accessible")
    def test_from_configuration(self) -> None:
        default_config = DataUrlElement.get_default_config()
        self.assertEqual(default_config, {'url_address': None})

        default_config['url_address'] = self.EXAMPLE_URL
        #: :type: DataUrlElement
        inst1 = DataUrlElement.from_config(default_config)
        self.assertEqual(default_config, inst1.get_config())
        self.assertEqual(inst1._url, self.EXAMPLE_URL)
        self.assertEqual(inst1.get_bytes(), open(self.EXAMPLE_PTH, 'rb').read())

        inst2 = DataUrlElement.from_config(inst1.get_config())
        self.assertEqual(inst1, inst2)

    @unittest.skipUnless(internet_available, "Internet not accessible")
    def test_from_uri(self) -> None:
        e = DataUrlElement.from_uri(self.EXAMPLE_URL)
        self.assertEqual(e.get_bytes(), open(self.EXAMPLE_PTH, 'rb').read())
        self.assertEqual(e.content_type(), 'image/png')

    def test_from_uri_no_scheme(self) -> None:
        self.assertRaises(
            InvalidUriError,
            DataUrlElement.from_uri,
            'www.kitware.com'
        )

    def test_from_uri_invalid_scheme(self) -> None:
        self.assertRaises(
            InvalidUriError,
            DataUrlElement.from_uri,
            'ftp://www.kitware.com'
        )

    @mock.patch('smqtk_dataprovider.impls.data_element.url.requests.get')
    def test_is_empty_zero_bytes(self, _m_requests_get: mock.MagicMock) -> None:
        e = DataUrlElement('some-address')
        # simulate no content bytes returned
        # noinspection PyTypeHints
        e.get_bytes = mock.MagicMock(return_value='')  # type: ignore
        self.assertTrue(e.is_empty())

    @mock.patch('smqtk_dataprovider.impls.data_element.url.requests.get')
    def test_is_empty_nonzero_bytes(self, _m_requests_get: mock.MagicMock) -> None:
        e = DataUrlElement('some-address')
        # simulate some content bytes returned
        # noinspection PyTypeHints
        e.get_bytes = mock.MagicMock(return_value='some bytes returned')  # type: ignore
        self.assertFalse(e.is_empty())

    @unittest.skipUnless(internet_available, "Internet not accessible")
    def test_get_bytes_from_url(self) -> None:
        e = DataUrlElement(self.EXAMPLE_URL)
        self.assertEqual(e.get_bytes(), open(self.EXAMPLE_PTH, 'rb').read())
        self.assertEqual(e.content_type(), 'image/png')

    @mock.patch('smqtk_dataprovider.impls.data_element.url.requests.get')
    def test_get_bytes_404_return_code(self, m_requests_get: mock.MagicMock) -> None:
        e = DataUrlElement('some-address')

        sim_rc = 500
        simulated_r = requests.Response()
        simulated_r.status_code = sim_rc
        m_requests_get.return_value = simulated_r

        self.assertRaisesRegex(
            requests.HTTPError,
            '%d' % sim_rc,
            e.get_bytes
        )

    @unittest.skipUnless(internet_available, "Internet not accessible")
    def test_writable_universal_false(self) -> None:
        # Cannot write to a URL hosted file, should always return false
        e = DataUrlElement(self.EXAMPLE_URL)
        self.assertFalse(e.writable())

    @unittest.skipUnless(internet_available, "Internet not accessible")
    def test_set_bytes_universal_readonly(self) -> None:
        # should never be able to write to a url element
        e = DataUrlElement(self.EXAMPLE_URL)
        self.assertRaises(
            ReadOnlyError,
            e.set_bytes, 'foo'
        )
