import abc
from typing import Optional, Set

from smqtk_dataprovider import DataElement


class ContentTypeValidator (metaclass=abc.ABCMeta):
    """
    Abstract mixin interface for the provision of a method to provide a "valid"
    set of content types relative to the sub-class' function.

    This is not Pluggable/Configurable as it is intended to not be implemented
    by itself, but mixed into some other interface.
    """

    __slots__ = ()

    @abc.abstractmethod
    def valid_content_types(self) -> Set[str]:
        """
        :return: A set valid MIME types that are "valid" within the implementing
            class' context.
        """

    def is_valid_element(self, data_element: DataElement) -> bool:
        """
        Check if the given DataElement instance reports a content type that
        matches one of the MIME types reported by ``valid_content_types``.

        :param data_element:
             Data element instance to check.

        :return: True if the given element has a valid content type as reported
            by ``valid_content_types``, and False if not.
        """
        return data_element.content_type() in self.valid_content_types()

    def raise_valid_element(
        self,
        data_element: DataElement,
        exception_type: type = ValueError,
        message: Optional[str] = None
    ) -> DataElement:
        """
        Check if the given data element matches a reported valid content type,
        raising the given exception class (``ValueError`` by default) if not.

        :param smqtk.representation.DataElement data_element:
             Data element instance to check.
        :param StandardError exception_type:
            Custom exception type to raise if the given element does not report
            as a valid content type. By default we raise a ``ValueError``.
        :param str message:
            Specific message to provide with a raise exception. By default
            we compose a generic message that also reports the given
            element's content type.

        :return: The unmodified input data element.
        :rtype: smqtk.representation.DataElement
        """
        if not self.is_valid_element(data_element):
            if message is None:
                message = "Data element does not match a content type " \
                          "reported as valid. Given: \"{}\". Valid types: {}." \
                          .format(data_element.content_type(),
                                  list(self.valid_content_types()))
            # noinspection PyCallingNonCallable
            # - Leave the handling of whether or not an exception is
            # constructable to the exception class being constructed (user
            # decision repercussion).
            raise exception_type(message)
        return data_element
