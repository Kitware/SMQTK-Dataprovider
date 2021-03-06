import logging
import pickle
import threading
from typing import Any, Dict, Hashable, Iterator, Optional, Set, Type, TypeVar

from smqtk_core.configuration import (
    from_config_dict,
    make_default_config,
    to_config_dict
)
from smqtk_core.dict import merge_dict
from smqtk_dataprovider import DataElement, DataSet
from smqtk_dataprovider.exceptions import ReadOnlyError
from smqtk_dataprovider.utils import SimpleTimer


LOG = logging.getLogger(__name__)
T = TypeVar("T", bound="DataMemorySet")


class DataMemorySet (DataSet):
    """
    In-memory DataSet implementation.

    This implementation maintains an in-memory mapping of stored DataElement
    original UUID to the DataElement instance.

    An optional writable DataElement may be provided to which the current set's
    map state is cached. This cache is updated every time new data elements are
    added to this set..

    """

    @classmethod
    def is_usable(cls) -> bool:
        """
        Check whether this data set implementations is available for use.

        This is always true for this implementation as there are no required 3rd
        party dependencies

        :return: Boolean determination of whether this implementation is usable.
        :rtype: bool

        """
        return True

    @classmethod
    def get_default_config(cls) -> Dict:
        """
        Generate and return a default configuration dictionary for this class.
        This will be primarily used for generating what the configuration
        dictionary would look like for this class without instantiating it.

        By default, we observe what this class's constructor takes as arguments,
        turning those argument names into configuration dictionary keys. If any
        of those arguments have defaults, we will add those values into the
        configuration dictionary appropriately. The dictionary returned should
        only contain JSON compliant value types.

        It is not be guaranteed that the configuration dictionary returned
        from this method is valid for construction of an instance of this class.

        :return: Default configuration dictionary for the class.
        :rtype: dict

        """
        c = super(DataMemorySet, cls).get_default_config()
        c['cache_element'] = make_default_config(DataElement.get_impls())
        return c

    @classmethod
    def from_config(
        cls: Type[T],
        config_dict: Dict,
        merge_default: bool = True
    ) -> T:
        if merge_default:
            config_dict = merge_dict(cls.get_default_config(), config_dict)

        cache_element = None
        if config_dict['cache_element'] and config_dict['cache_element']['type']:
            cache_element = from_config_dict(config_dict['cache_element'],
                                             DataElement.get_impls())
        config_dict['cache_element'] = cache_element

        return super(DataMemorySet, cls).from_config(config_dict, False)

    def __init__(
        self,
        cache_element: Optional[DataElement] = None,
        pickle_protocol: int = -1
    ):
        """
        Initialize a new in-memory data set instance.

        :param cache_element: Optional data element to store/load a cache of
            this data set's contents into. Cache loading, if the element has
            bytes, will occur in this constructor. Cache writing will only occur
            after adding one or more elements.

            This can be optionally turned on after creating/using this data set
            for a while by setting a valid element to the ``cache_element``
            attribute and calling the ``.cache()`` method. When
            ``cache_element`` is not set, the ``cache()`` method does nothing.
        :type cache_element: None | smqtk.representation.DataElement

        :param pickle_protocol: Pickling protocol to use. We will use -1 by
            default (latest version, probably binary).
        :type pickle_protocol: int

        """
        super(DataMemorySet, self).__init__()

        # Mapping of UUIDs to DataElement instances
        #: :type: dict[collections.abc.Hashable, DataElement]
        self._element_map = {}
        self._element_map_lock = threading.RLock()

        # Optional path to a file that will act as a cache of our internal
        # table
        self.cache_element = cache_element
        if cache_element and not cache_element.is_empty():
            #: :type: dict[collections.abc.Hashable, DataElement]
            self._element_map = pickle.loads(cache_element.get_bytes())

        self.pickle_protocol = pickle_protocol

    def __iter__(self) -> Iterator[DataElement]:
        """
        :return: Generator over the DataElements contained in this set in no
            particular order.
        """
        # making copy of UUIDs so we don't block when between yields, as well
        # as so we aren't walking a possibly modified map
        uuids = self.uuids()
        with self._element_map_lock:
            for k in uuids:
                yield self._element_map[k]

    def cache(self) -> None:
        """
        Cache the current table if a cache has been configured.
        """
        if self.cache_element:
            if self.cache_element.is_read_only():
                raise ReadOnlyError("Cache element (%s) is read-only."
                                    % self.cache_element)

            with self._element_map_lock:
                with SimpleTimer("Caching memory data-set table",
                                 LOG.debug):
                    self.cache_element.set_bytes(
                        pickle.dumps(self._element_map, self.pickle_protocol)
                    )

    def get_config(self) -> Dict[str, Any]:
        """
        This implementation has no configuration properties.

        :return: JSON type compliant configuration dictionary.
        :rtype: dict

        """
        c = merge_dict(self.get_default_config(), {
            "pickle_protocol": self.pickle_protocol,
        })
        if self.cache_element:
            c['cache_element'] = merge_dict(
                c['cache_element'],
                to_config_dict(self.cache_element)
            )
        return c

    def count(self) -> int:
        """
        :return: The number of data elements in this set.
        :rtype: int
        """
        with self._element_map_lock:
            return len(self._element_map)

    def uuids(self) -> Set[Hashable]:
        """
        :return: A new set of uuids represented in this data set.
        :rtype: set
        """
        with self._element_map_lock:
            return set(self._element_map)

    def has_uuid(self, uuid: Hashable) -> bool:
        """
        Test if the given uuid refers to an element in this data set.

        :param uuid: Unique ID to test for inclusion. This should match the
            type that the set implementation expects or cares about.

        :return: True if the given uuid matches an element in this set, or
            False if it does not.
        :rtype: bool

        """
        with self._element_map_lock:
            return uuid in self._element_map

    def add_data(self, *elems: DataElement) -> None:
        """
        Add the given data element(s) instance to this data set.

        :param elems: Data element(s) to add
        :type elems: smqtk.representation.DataElement

        """
        with self._element_map_lock:
            added_elements = False
            for e in elems:
                assert isinstance(e, DataElement), \
                    "Expected DataElement instance, got '%s' instance instead" \
                    % type(e)
                self._element_map[e.uuid()] = e
                added_elements = True
            if added_elements:
                self.cache()

    def get_data(self, uuid: Hashable) -> DataElement:
        """
        Get the data element the given uuid references, or raise an
        exception if the uuid does not reference any element in this set.

        :raises KeyError: If the given uuid does not refer to an element in
            this data set.

        :param uuid: The uuid of the element to retrieve.

        :return: The data element instance for the given uuid.
        :rtype: smqtk.representation.DataElement

        """
        with self._element_map_lock:
            return self._element_map[uuid]


DATA_SET_CLASS = DataMemorySet
