from io import BytesIO

import numpy as np
import pytest

from smqtk_core.configuration import configuration_test_helper
from smqtk_dataprovider.exceptions import ReadOnlyError
from smqtk_dataprovider.impls.data_element.matrix import MatrixDataElement


class TestMatrixDataElement (object):
    """
    Tests for the ``MatrixDataElement`` implementation
    """

    def test_is_usable(self) -> None:
        """
        Test that implementation is always usable.
        """
        assert MatrixDataElement.is_usable()

    def test_init_no_args(self) -> None:
        """
        Test default constructor results in no internal data.
        """
        e = MatrixDataElement()
        assert e._matrix is None

    def test_init_with_sequence(self) -> None:
        """
        Test that constructor converts given sequence into numpy array.
        """
        s = (1, 2, 3, 4)
        e = MatrixDataElement(s)
        assert isinstance(e._matrix, np.ndarray)
        np.testing.assert_allclose(e._matrix, s)

    def test_init_with_ndarray(self) -> None:
        """
        Test that constructor takes ndarray as is without copying.
        """
        a = np.array([1, 2, 3, 4])
        e = MatrixDataElement(a)

        assert isinstance(e._matrix, np.ndarray)
        np.testing.assert_allclose(e._matrix, (1, 2, 3, 4))

        # Testing reference storing by modifying input array and observing
        # effect in stored array.
        a[:] = (5, 6, 7, 8)
        np.testing.assert_allclose(e._matrix, (5, 6, 7, 8))

    def test_matrix_property_no_data(self) -> None:
        """
        Test that matrix property returns None when internal attribute set to
        None
        """
        e = MatrixDataElement(None)
        assert e.matrix is None

    def test_matrix_property_with_data(self) -> None:
        e = MatrixDataElement((1, 2, 3, 4))
        assert isinstance(e.matrix, np.ndarray)
        np.testing.assert_allclose(e.matrix, (1, 2, 3, 4))

    def test_matrix_property_set_not_RO(self) -> None:
        """
        Test that we can set the numpy matrix via property.
        """
        e = MatrixDataElement((1, 2, 3, 4), readonly=False)
        e.matrix = (5, 6, 7, 8)
        assert isinstance(e._matrix, np.ndarray)
        np.testing.assert_allclose(e._matrix, (5, 6, 7, 8))

    def test_matrix_property_set_RO_exception(self) -> None:
        """
        Test that setting to the matrix property results in a ReadOnlyError when
        the `readonly` attribute is set.
        """
        e = MatrixDataElement((1, 2, 3, 4), readonly=True)
        with pytest.raises(ReadOnlyError):
            e.matrix = (5, 6, 7, 8)
        np.testing.assert_allclose(e._matrix, (1, 2, 3, 4))  # type: ignore

    def test_configuration_no_data(self) -> None:
        """
        Testing getting the configuration from an instance with no matrix data
        and creating a new instance from that configuration.
        """
        inst = MatrixDataElement(readonly=False)
        for i in configuration_test_helper(inst):
            assert i.matrix is None
            assert i.is_read_only() is False

        inst = MatrixDataElement(readonly=True)
        for i in configuration_test_helper(inst):
            assert i.matrix is None
            assert i.is_read_only() is True

    def test_configuration_with_data(self) -> None:
        """
        Testing getting the configuration from an instance with no matrix data
        and creating a new instance from that configuration.
        """
        inst = MatrixDataElement((1, 2, 3, 4), readonly=False)
        for i in configuration_test_helper(inst):
            assert i.matrix is not None
            np.testing.assert_allclose(i.matrix, (1, 2, 3, 4))  # type: ignore
            assert i.is_read_only() is False

        inst = MatrixDataElement((1, 2, 3, 4), readonly=True)
        for i in configuration_test_helper(inst):
            assert i.matrix is not None
            np.testing.assert_allclose(i.matrix, (1, 2, 3, 4))  # type: ignore
            assert i.is_read_only() is True

    def test_is_empty_None(self) -> None:
        """
        Test that is_empty is True when there is no matrix set.
        """
        e = MatrixDataElement(None)
        assert e.is_empty() is True

    def test_is_empty_zero_size(self) -> None:
        """
        Test that is_empty is True when there is a matrix set but its size is 0.
        """
        e = MatrixDataElement(())
        assert isinstance(e._matrix, np.ndarray)
        assert e.is_empty() is True

    def test_is_empty_false(self) -> None:
        """
        Test that is_empty is False when there is valid matrix data set.
        """
        e = MatrixDataElement((1,))
        assert e.is_empty() is False

    def test_get_bytes_None(self) -> None:
        """
        Test that empty bytes are returned when no matrix is set
        """
        e = MatrixDataElement(None)
        assert e.get_bytes() == b''

    def test_get_bytes_with_data(self) -> None:
        """
        Test that valid bytes are returned when a matrix is set.
        """
        assert MatrixDataElement((1, 2, 3, 4)).get_bytes() != b''

    def test_writable_true(self) -> None:
        """
        Test that ``writable`` is True when readonly is False
        """
        assert MatrixDataElement(readonly=False).writable() is True

    def test_writable_false(self) -> None:
        """
        Test that ``writable`` is False when readonly is True.
        """
        assert MatrixDataElement(readonly=True).writable() is False

    def test_set_bytes_None(self) -> None:
        """
        Test that setting blank bytes sets the matrix data to None.
        """
        e = MatrixDataElement((1,))
        assert e._matrix is not None
        e.set_bytes(b'')
        assert e._matrix is None

    def test_set_bytes_valid_bytes(self) -> None:
        """
        Test that setting valid numpy saved bytes results in expected matrix.
        """
        expected_mat = np.array([[[1, 2, 3],
                                  [4, 5, 6]],
                                 [[7, 8, 9],
                                  [0, 1, 2]],
                                 [[3, 4, 5],
                                  [6, 7, 8]]], dtype=np.float16)
        expected_bytes_buf = BytesIO()
        # noinspection PyTypeChecker
        np.save(expected_bytes_buf, expected_mat)
        expected_bytes = expected_bytes_buf.getvalue()

        e = MatrixDataElement()
        assert e._matrix is None

        e.set_bytes(expected_bytes)
        assert e._matrix is not None
        np.testing.assert_allclose(e._matrix, expected_mat)
