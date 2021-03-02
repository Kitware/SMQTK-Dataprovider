import unittest
import unittest.mock as mock

from smqtk_dataprovider import DataSet, DataElement
from typing import AbstractSet, Hashable, Tuple, Iterator, Dict

class DummyDataSet (DataSet):

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def __init__(self) -> None:
        super(DummyDataSet, self).__init__()

    def __iter__(self) -> Iterator:
        pass

    def count(self) -> int:
        pass

    def uuids(self) -> AbstractSet:
        pass

    def has_uuid(self, uuid: Hashable) -> bool:
        pass

    def add_data(self, *elems: DataElement) -> None:
        pass

    def get_data(self, uuid: Hashable) -> DataElement:
        pass

    def get_config(self) -> Dict:
        return {}


class TestDataSetAbstract (unittest.TestCase):

    def test_len(self) -> None:
        expected_len = 134623456

        ds = DummyDataSet()
        ds.count = mock.MagicMock(return_value=expected_len) #type: ignore

        self.assertEqual(len(ds), expected_len)

    def test_getitem_mock(self) -> None:
        expected_key = 'foo'
        expected_value = 'bar'

        def expected_effect(k: Hashable) -> str:
            if k == expected_key:
                return expected_value
            raise RuntimeError("not expected key")

        ds = DummyDataSet()
        ds.get_data = mock.MagicMock(side_effect=expected_effect) #type: ignore

        self.assertRaisesRegex(
            RuntimeError,
            "^not expected key$",
            ds.__getitem__, 'unexpectedKey'
        )
        self.assertEqual(ds[expected_key], expected_value)

    def test_contains(self) -> None:
        """
        By mocking DummyDataSet's ``has_uuid`` method (an abstract method), we
        check that the ``__contains__`` method on the parent class does the
        right thing when using python's ``in`` syntax.
        """
        # Contains built-in hook expects data element and requests UUID from
        # that.
        expected_uuid = 'some uuid'

        mock_data_element = mock.MagicMock()
        mock_data_element.uuid = mock.MagicMock(return_value=expected_uuid)

        def expected_has_uuid_effect(k: Hashable) -> bool:
            if k == expected_uuid:
                return True
            return False

        ds = DummyDataSet()
        ds.has_uuid = mock.MagicMock(side_effect=expected_has_uuid_effect) #type: ignore

        # noinspection PyTypeChecker
        # - Using a mock object on purpose in conjunction with ``has_uuid``
        #   override.
        self.assertIn(mock_data_element, ds)
        ds.has_uuid.assert_called_once_with(expected_uuid)

        mock_data_element.uuid.return_value = 'not expected uuid'
        # noinspection PyTypeChecker
        # - Using a mock object on purpose in conjunction with ``has_uuid``
        #   override.
        self.assertNotIn(mock_data_element, ds)
