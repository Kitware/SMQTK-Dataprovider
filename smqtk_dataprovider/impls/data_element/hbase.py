from typing import Any, Dict, Optional

from smqtk_dataprovider import DataElement
from smqtk_dataprovider.exceptions import ReadOnlyError

# attempt to import required modules
try:
    import happybase  # type: ignore
    from tika import detector as tika_detector  # type: ignore
except ImportError:
    happybase = None
    tika_detector = None


class HBaseDataElement(DataElement):  # lgtm [py/missing-equals]
    """
    Wrapper for binary data contained on an HBase server somewhere. Uses Tika
    content type detection to determine content type of served data.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return None not in {happybase, tika_detector}

    def __init__(
        self,
        element_key: str,
        binary_column: str,
        hbase_address: str,
        hbase_table: str,
        timeout: int = 10000,
    ):
        """
        Create a new HBase data element wrapper/reference.

        :param element_key: Key to the table row containing the binary data
        :type element_key: str

        :param binary_column: Name of the column that contains the binary
            data.
        :type binary_column: str

        :param hbase_address: Address of the HBase server. This should at least
            be the hostname of the server. This might also take a ":port"
            suffix?
        :type hbase_address: str

        :param hbase_table: Name of the table the content is contained in.
        :param timeout:
        :return:
        """
        super(HBaseDataElement, self).__init__()

        self.element_key = element_key
        self.binary_column = binary_column
        self.hbase_address = hbase_address
        self.hbase_table = hbase_table
        self.timeout = int(timeout)

        self._binary_ct_cache = None

    def __repr__(self) -> str:
        return super(
            HBaseDataElement, self
        ).__repr__() + "{key: %s, bin_col: %s, hbase_addr: %s, hbase_table: %s, " "timeout: %d}" % (
            self.element_key,
            self.binary_column,
            self.hbase_address,
            self.hbase_table,
            self.timeout,
        )

    def get_config(self) -> Dict[str, Any]:
        return {
            "element_key": self.element_key,
            "binary_column": self.binary_column,
            "hbase_address": self.hbase_address,
            "hbase_table": self.hbase_table,
            "timeout": self.timeout,
        }

    def content_type(self) -> Optional[str]:
        if self._binary_ct_cache is None:
            self._binary_ct_cache = tika_detector.from_buffer(self.get_bytes())
        return self._binary_ct_cache

    def _new_hbase_table_connection(self) -> "happybase.table":
        return happybase.Connection(self.hbase_address, timeout=self.timeout).table(
            self.hbase_table
        )

    def is_empty(self) -> bool:
        """
        Check if this element contains no bytes.

        :return: If this element contains 0 bytes.
        :rtype: bool

        """
        # naive impl for now
        return len(self.get_bytes()) == 0

    def get_bytes(self) -> bytes:
        table = self._new_hbase_table_connection()
        r = table.row(self.element_key, columns=[self.binary_column])
        return r[self.binary_column]

    def writable(self) -> bool:
        """
        :return: if this instance supports setting bytes.
        :rtype: bool
        """
        # No write support (yet) for HBase elements
        return False

    def set_bytes(self, b: bytes) -> None:
        """
        Set bytes to this data element in the form of a string.

        Not all implementations may support setting bytes (writing). See the
        ``writable`` method.

        :param b: bytes to set.
        :type b: bytes

        :raises ReadOnlyError: This data element can only be read from / does
            not support writing.

        """
        raise ReadOnlyError("HBase elements cannot write data.")
