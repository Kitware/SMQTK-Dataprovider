import base64
import re
from typing import Any, Dict, Optional, Type, TypeVar

from smqtk_core.dict import merge_dict
from smqtk_dataprovider import DataElement
from smqtk_dataprovider.exceptions import InvalidUriError, ReadOnlyError


BYTES_CONFIG_ENCODING = 'latin-1'
T = TypeVar("T", bound="DataMemoryElement")


class DataMemoryElement (DataElement):  # lgtm [py/missing-equals]
    """
    In-memory representation of data stored in a byte list
    """

    # Base64 RE including URL-safe character replacements
    B64_PATTERN = '[a-zA-Z0-9+/_-]*={0,2}'
    URI_B64_RE = re.compile('^base64://(?P<base64>{})$'.format(B64_PATTERN))
    URI_DATA_B64_RE = re.compile(r"^data:(?P<ct>[\w/]+);base64,(?P<base64>{})$"
                                 .format(B64_PATTERN))

    @classmethod
    def is_usable(cls) -> bool:
        # No dependencies
        return True

    @classmethod
    def from_config(
        cls: Type[T],
        config_dict: Dict,
        merge_default: bool = True
    ) -> T:
        """
        Instantiate a new instance of this class given the configuration
        JSON-compliant dictionary encapsulating initialization arguments.

        Overrides base because this implementation's "bytes" argument wants to
        be given a ``bytes`` type object. When not None, in python 2 this is a
        normal string (not unicode), while in python 3 bytes is a distinct
        type.
        """
        if merge_default:
            config_dict = merge_dict(cls.get_default_config(),
                                     config_dict)
        try:
            # In python 3, encode input ``str`` into ``bytes``.
            # In python 2, even though ``str`` and ``bytes`` are the same
            # underlying type, we could be given ``unicode``, which needs to be
            # encoded down to ``bytes`` (``str``).
            config_dict["bytes"] = \
                config_dict['bytes'].encode(BYTES_CONFIG_ENCODING)
        except AttributeError:
            # If this is a None value, which has no attributes at all, leave it
            # alone. If in python 2 and given a unicode string, as is the norm
            # return from ``json.load`` and ``json.loads``,
            pass
        return super(DataMemoryElement, cls).from_config(config_dict,
                                                         merge_default=False)

    @classmethod
    def from_uri(cls, uri: str) -> DataElement:
        """
        Construct a new instance based on the given URI.

        Memory elements resolve byte-string formats. Currently, this method
        accepts a base64 using the standard and URL-safe alphabet as the python
        ``base64.urlsafe_b64decode`` module function would expect.

        This method accepts URIs in two formats:
            - ``base64://<data>``
            - ``data:<mimetype>;base64,<data>``
            - Empty string (no data)

        Filling in ``<data>`` with the actual byte string, and ``<mimetype>``
        with the actual MIMETYPE of the bytes.

        :param uri: URI string to resolve into an element instance

        :raises smqtk.exceptions.InvalidUriError: The given URI was not a
            base64 format

        :return: New element instance of our type.
        """
        if uri is None:
            raise InvalidUriError(uri, 'None value given')

        if len(uri) == 0:
            return DataMemoryElement(b'', None)

        data_b64_m = cls.URI_B64_RE.match(uri)
        if data_b64_m is not None:
            m_d = data_b64_m.groupdict()
            return DataMemoryElement.from_base64(m_d['base64'], None)

        data_b64_m = cls.URI_DATA_B64_RE.match(uri)
        if data_b64_m is not None:
            m_d = data_b64_m.groupdict()
            return DataMemoryElement.from_base64(
                m_d['base64'], m_d['ct']
            )

        raise InvalidUriError(uri, "Did not detect byte format URI")

    @classmethod
    def from_base64(
        cls,
        b64_str: str,
        content_type: Optional[str] = None
    ) -> "DataMemoryElement":
        """
        Create new MemoryElement instance based on a given base64 string and
        content type.

        This method accepts a base64 using the standard and URL-safe alphabet
        as the python ``base64.urlsafe_b64decode`` module function would
        expect.

        :param b64_str: Base64 data string.
        :param content_type: Content type string, or None if unknown.

        :return: New MemoryElement instance containing the byte data in the
            given base64 string.
        """
        if b64_str is None:
            raise ValueError("Base 64 string should not be None")
        # The decode function does not like taking unicode strings
        # (python 2.x). Additionally, the encoding alphabet should not
        # container any unicode symbols, so this aught to be safe.
        b64_str = str(b64_str)
        return DataMemoryElement(base64.urlsafe_b64decode(b64_str),
                                 content_type)

    # noinspection PyShadowingBuiltins
    def __init__(
        self, bytes: Optional[bytes] = None,
        content_type: Optional[str] = None,
        readonly: bool = False
    ):
        """
        Create a new DataMemoryElement from a byte string and optional content
        type.

        :param bytes: Bytes to contain. It may be None to represent no bytes.
        :param content_type: Content type of the bytes given.
        :param readonly: If this element should allow writing or not.
        """
        super(DataMemoryElement, self).__init__()
        self._bytes = bytes
        self._content_type = content_type
        self._readonly = bool(readonly)

    def __repr__(self) -> str:
        return super(DataMemoryElement, self).__repr__() + \
               "{len(bytes): %d, content_type: %s, readonly: %s}" \
               % (len(self.get_bytes()), self._content_type, self._readonly)

    def get_config(self) -> Dict[str, Any]:
        b = self._bytes
        b_str: Optional[str] = None
        if b is not None:
            b_str = b.decode(BYTES_CONFIG_ENCODING)
        return {
            "bytes": b_str,
            'content_type': self._content_type,
            "readonly": self._readonly,
        }

    def content_type(self) -> Optional[str]:
        """
        :return: Standard type/subtype string for this data element, or None if
            the content type is unknown.
        """
        return self._content_type

    def is_empty(self) -> bool:
        """
        Check if this element contains no bytes.

        :return: If this element contains 0 bytes.
        """
        return not bool(self._bytes)

    def get_bytes(self) -> bytes:
        """
        :return: Get the byte stream for this data element.
        """
        return self._bytes or b''

    def writable(self) -> bool:
        """
        :return: if this instance supports setting bytes.
        """
        return not self._readonly

    def set_bytes(self, b: bytes) -> None:
        """
        Set bytes to this data element in the form of a string.

        Previous content type value is maintained.

        :param b: bytes to set.

        :raises ReadOnlyError: This data element can only be read from / does
            not support writing.
        """
        if not self._readonly:
            self._bytes = b
        else:
            raise ReadOnlyError("This memory element cannot be written to.")
