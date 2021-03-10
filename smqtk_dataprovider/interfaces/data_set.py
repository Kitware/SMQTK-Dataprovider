import abc
from collections.abc import Set as ISet
from typing import Any, Hashable, Iterator, Set

from smqtk_core import Configurable, Pluggable
from smqtk_dataprovider import DataElement


class DataSet (ISet, Configurable, Pluggable):
    """
    Abstract interface for data sets, that contain an arbitrary number of
    ``DataElement`` instances of arbitrary implementation type, keyed on
    ``DataElement`` UUID values.

    This should only be used with DataElements whose byte content is expected
    not to change. If they do, then UUID keys may no longer represent the
    elements associated with them.

    """

    def __len__(self) -> int:
        """
        :return: Number of elements in this DataSet.
        :rtype: int
        """
        return self.count()

    def __getitem__(self, uuid: Hashable) -> DataElement:
        return self.get_data(uuid)

    def __contains__(self, d: Any) -> bool:
        """
        Different than has_uuid() because this takes another DataElement
        instance, not a UUID.

        :param d: DataElement to test for containment
        :type d: smqtk.representation.DataElement

        :return: True of this DataSet contains the given data element. Since,
        :rtype: bool

        """
        return self.has_uuid(d.uuid())

    @abc.abstractmethod
    def __iter__(self) -> Iterator[DataElement]:
        """
        :return: Generator over the DataElements contained in this set in no
            particular order.
        """

    @abc.abstractmethod
    def count(self) -> int:
        """
        :return: The number of data elements in this set.
        :rtype: int
        """

    @abc.abstractmethod
    def uuids(self) -> Set[Hashable]:
        """
        :return: A new set of uuids represented in this data set.
        :rtype: set
        """

    @abc.abstractmethod
    def has_uuid(self, uuid: Hashable) -> bool:
        """
        Test if the given uuid refers to an element in this data set.

        :param uuid: Unique ID to test for inclusion. This should match the
            type that the set implementation expects or cares about.
        :type uuid: collections.abc.Hashable

        :return: True if the given uuid matches an element in this set, or
            False if it does not.
        :rtype: bool

        """

    @abc.abstractmethod
    def add_data(self, *elems: DataElement) -> None:
        """
        Add the given data element(s) instance to this data set.

        *NOTE: Implementing methods should check that input elements are in
        fact DataElement instances.*

        :param elems: Data element(s) to add
        :type elems: smqtk.representation.DataElement

        """

    @abc.abstractmethod
    def get_data(self, uuid: Hashable) -> DataElement:
        """
        Get the data element the given uuid references, or raise an
        exception if the uuid does not reference any element in this set.

        :raises KeyError: If the given uuid does not refer to an element in
            this data set.

        :param uuid: The uuid of the element to retrieve.
        :type uuid: collections.abc.Hashable

        :return: The data element instance for the given uuid.
        :rtype: smqtk.representation.DataElement

        """
