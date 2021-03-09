from typing import Any, Dict, Hashable, Iterable, Iterator, Mapping, Union
import unittest
import unittest.mock as mock

from smqtk_dataprovider import KeyValueStore
from smqtk_dataprovider.exceptions import ReadOnlyError
from smqtk_dataprovider.interfaces.key_value_store import NO_DEFAULT_VALUE


class DummyKVStore (KeyValueStore):

    TEST_READ_ONLY = True
    TEST_COUNT = 0

    # base-class requirements

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict:
        pass

    # KVStore abc methods

    def __repr__(self) -> str:
        return super(DummyKVStore, self).__repr__()

    def count(self) -> int:
        return self.TEST_COUNT

    def keys(self) -> Iterator[Hashable]:
        pass

    def is_read_only(self) -> bool:
        return self.TEST_READ_ONLY

    def add(self, key: Hashable, value: Any) -> "DummyKVStore":
        super(DummyKVStore, self).add(key, value)
        return self

    def add_many(self, d: Mapping[Hashable, Any]) -> "DummyKVStore":
        super(DummyKVStore, self).add_many(d)
        return self

    def has(self, key: Union[int, object, str]) -> bool:
        pass

    def get(self, key: Hashable, default: Any = NO_DEFAULT_VALUE) -> Any:
        pass

    def remove(self, key: Hashable) -> "DummyKVStore":
        super(DummyKVStore, self).remove(key)
        return self

    def remove_many(self, keys: Iterable[Hashable]) -> "DummyKVStore":
        super(DummyKVStore, self).remove_many(keys)
        return self

    def clear(self) -> "DummyKVStore":
        super(DummyKVStore, self).clear()
        return self


class TestKeyValueStoreAbstract (unittest.TestCase):

    def test_len(self) -> None:
        s = DummyKVStore()

        s.TEST_COUNT = 0
        assert len(s) == 0

        s.TEST_COUNT = 23456
        assert len(s) == 23456

    def test_repr(self) -> None:
        # Should return expected template string
        expected_repr = "<DummyKVStore %s>"
        actual_repr = repr(DummyKVStore())
        self.assertEqual(actual_repr, expected_repr)

    # noinspection PyUnresolvedReferences
    def test_value_iterator(self) -> None:
        expected_keys_values = {1, 5, 2345, 'foo'}

        s = DummyKVStore()
        # noinspection PyTypeHints
        s.keys = mock.MagicMock(return_value=expected_keys_values)  # type: ignore
        # noinspection PyTypeHints
        s.get = mock.MagicMock(side_effect=lambda v: v)  # type: ignore

        # Make sure keys now returns expected set.
        # noinspection PyTypeChecker
        # - Return value for `keys()` set above is correctly a set.
        self.assertEqual(set(s.keys()), expected_keys_values)

        # Get initial iterator. ``keys`` should have only been called once so
        # far, and ``get`` method should not have been called yet.
        # called yet.
        v_iter = s.values()
        self.assertIsInstance(v_iter, Iterable)
        self.assertEqual(s.keys.call_count, 1)
        self.assertEqual(s.get.call_count, 0)

        actual_values_list = set(v_iter)
        self.assertEqual(actual_values_list, expected_keys_values)
        # Keys should have been called one more time, and get should have been
        # called an equal number of times as there are keys.
        self.assertEqual(s.keys.call_count, 2)
        self.assertEqual(s.get.call_count, len(expected_keys_values))
        s.get.assert_any_call(1)
        s.get.assert_any_call(5)
        s.get.assert_any_call(2345)
        s.get.assert_any_call('foo')

    # noinspection PyUnresolvedReferences
    def test_contains(self) -> None:
        # Test that python ``has`` keyword and __contains__ method calls the
        # ``has`` method correctly.
        s = DummyKVStore()

        # noinspection PyTypeHints
        s.has = mock.MagicMock(return_value=True)  # type: ignore
        self.assertTrue('some item' in s)
        s.has.assert_called_once_with('some item')

        # noinspection PyTypeHints
        s.has = mock.MagicMock(return_value=False)  # type: ignore
        self.assertFalse('other item' in s)
        s.has.assert_called_once_with('other item')

    def test_get_item(self) -> None:
        s = DummyKVStore()
        # noinspection PyTypeHints
        s.get = mock.Mock(return_value='expected-value')  # type: ignore
        ev = s['some-key']
        s.get.assert_called_once_with('some-key')
        self.assertEqual(ev, 'expected-value')

    def test_get_many(self) -> None:
        s = DummyKVStore()
        mock_return_values = ['expected-value', 'other-expected-value']
        # noinspection PyTypeHints
        s.get = mock.Mock(side_effect=mock_return_values)  # type: ignore
        ev = list(
            s.get_many(('some-key', 'some-other-key'))
        )

        assert ev == mock_return_values

    def test_add_when_read_only(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = True

        self.assertRaises(
            ReadOnlyError,
            s.add, 'k', 'v'
        )

    def test_add_when_not_read_only(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = False
        s.add('k', 'v')
        # Integer
        s.add(0, 'some value')
        # type
        s.add(object, 'some value')
        # some object instance
        s.add(object(), 'some value')

    def test_add_many_read_only(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = True
        self.assertRaises(
            ReadOnlyError,
            s.add_many, {0: 1}
        )

    def test_add_many(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = False
        s.add_many({0: 1})

    def test_remove_read_only(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = True
        self.assertRaises(
            ReadOnlyError,
            s.remove, 0
        )

    def test_remove(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = False
        s.remove(0)

    def test_remove_many_read_only(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = True
        self.assertRaises(
            ReadOnlyError,
            s.remove_many, [0, 1]
        )

    def test_remove_many(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = False
        s.remove_many([0, 1])

    def test_clear_readonly(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = True
        self.assertRaisesRegex(
            ReadOnlyError,
            "Cannot clear a read-only DummyKVStore instance.",
            s.clear
        )

    def test_clear(self) -> None:
        s = DummyKVStore()
        s.TEST_READ_ONLY = False
        s.clear()
