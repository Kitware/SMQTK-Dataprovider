from io import BytesIO
from typing import Dict, Optional, Tuple, Union

import numpy
import numpy.typing as npt

from smqtk_dataprovider import DataElement
from smqtk_dataprovider.exceptions import ReadOnlyError


class MatrixDataElement (DataElement):  # lgtm[py/missing-equals]
    """
    DataElement whose data is represented in memory by a ``numpy.ndarray``
    instance.

    This implementation additionally provides a ``matrix`` property that exposes
    a natively stored ``numpy.ndarray`` (may be None).  It is expected that this
    implementation is to be used with components that have ``matrix`` short-cuts
    or otherwise where the matrix is the important that data is accessed often.

    Since the ndarray is stored natively, ``get_bytes()`` bytes are generated on
    the fly based on the current state of matrix.  The ``writable()`` method on
    this instance only pertains to both the ``set_bytes()`` method AND
    ``matrix`` property setter.
    """

    @classmethod
    def is_usable(cls) -> bool:
        """
        Check whether this class is available for use.

        Since certain plugin implementations may require additional dependencies
        that may not yet be available on the system, this method should check
        for those dependencies and return a boolean saying if the implementation
        is usable.

        NOTES:
            - This should be a class method
            - When an implementation is deemed not usable, this should emit a
                warning detailing why the implementation is not available for
                use.

        :return: Boolean determination of whether this implementation is usable.
        :rtype: bool

        """
        return True

    def __init__(
        self,
        mat: Optional[npt.ArrayLike] = None,
        readonly: bool = False
    ):
        """
        :param mat: Optional matrix to store at construction time.
        :param readonly:
            If the matrix stored should be considered read-only. This pertains
            to both the ``set_bytes`` method AND setting to the ``matrix``
            property.  This does NOT pertain to modifying an already set matrix,
            which should be controlled by setting flags on the ndarray instance.
        """
        super(MatrixDataElement, self).__init__()
        self._matrix: Optional[npt.NDArray] = None
        if mat is not None:
            self._matrix = numpy.asarray(mat)
        self._readonly = bool(readonly)

    def __repr__(self) -> str:
        shape: Optional[Tuple] = None
        if self._matrix is not None:
            shape = self._matrix.shape
        return (
            super(MatrixDataElement, self).__repr__() +
            "{{shape: {}}}".format(shape)
        )

    @property
    def matrix(self) -> Optional[Union[npt.NDArray, npt.ArrayLike]]:
        """
        :return: Get the matrix stored in this element. This may be None if
            there is no matrix currently stored in this element (is empty).
            Alternatively, the matrix may be an "empty" shape, or have zero
            area.

        TODO: Narrow the return type just `npt.NDArray` once mypy supports
              asymmetric property type annotation.
        """
        return self._matrix

    @matrix.setter
    def matrix(self, m: npt.ArrayLike) -> None:
        """
        :param m: New ndarray instance to set as the contained matrix.

        :raises ReadOnlyError: This data element can only be read from / does
            not support writing.
        """
        if not self.writable():
            raise ReadOnlyError("This %s element is read only." % self)
        self._matrix = numpy.asarray(m)

    def get_config(self) -> Dict:
        """
        Return a JSON-compliant dictionary that could be passed to this class's
        ``from_config`` method to produce an instance with identical
        configuration.

        In the common case, this involves naming the keys of the dictionary
        based on the initialization argument names as if it were to be passed
        to the constructor via dictionary expansion.

        :return: JSON type compliant configuration dictionary.

        """
        mat_json = None
        if self._matrix is not None:
            mat_json = self._matrix.tolist()
        return {
            'mat': mat_json,
            'readonly': self._readonly,
        }

    def content_type(self) -> Optional[str]:
        """
        :return: Standard type/subtype string for this data element, or None if
            the content type is unknown.
        """
        # Blob of bytes (numpy save format)
        return 'application/octet-stream'

    def is_empty(self) -> bool:
        """
        Check if this element contains no bytes.

        The intend of this method is to quickly check if there is any data
        behind this element, ideally without having to read all/any of the
        underlying data.

        :return: If this element contains 0 bytes.

        """
        return self._matrix is None or self._matrix.size == 0

    def get_bytes(self) -> bytes:
        """
        :return: Get the bytes for this data element.
        """
        if self._matrix is not None:
            buf = BytesIO()
            # noinspection PyTypeChecker
            numpy.save(buf, self._matrix)
            return buf.getvalue()
        else:
            return bytes()

    def writable(self) -> bool:
        """
        :return: if this instance supports setting bytes.
        """
        return not self._readonly

    def set_bytes(self, b: bytes) -> None:
        """
        Set bytes to this data element.

        Not all implementations may support setting bytes (check ``writable``
        method return).

        :param b: bytes to set.

        :raises ReadOnlyError: This data element can only be read from / does
            not support writing.

        """
        super(MatrixDataElement, self).set_bytes(b)
        if b:
            buf = BytesIO(b)
            self._matrix = numpy.load(buf)
        else:
            self._matrix = None
