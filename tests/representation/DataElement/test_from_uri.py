"""
Tests for high level ``from_uri`` function, separate from the
``DataElement.from_uri`` class method.
"""
from typing import Dict, Optional, Iterable
import unittest

from smqtk_dataprovider import DataElement, from_uri
from smqtk_dataprovider.exceptions import InvalidUriError


class UnresolvableElement (DataElement):
    """ Does not implement from_uri, declaring no support for URI resolution """

    def __repr__(self) -> str:
        return super(UnresolvableElement, self).__repr__()

    def get_config(self) -> Dict:
        return {}

    def content_type(self) -> None:
        return None

    def is_empty(self) -> bool: ...  # type: ignore[empty-body]

    def get_bytes(self) -> bytes:
        return bytes()

    def set_bytes(self, b: bytes) -> None: ...

    def writable(self) -> bool: ...  # type: ignore[empty-body]


class ResolvableElement (DataElement):

    @classmethod
    def from_uri(cls, uri: str) -> "ResolvableElement":
        """
        :type uri: str
        :rtype: ResolvableElement
        """
        if uri.startswith('resolvable://'):
            return ResolvableElement()
        raise InvalidUriError(uri, "Does not begin with 'resolvable://'.")

    def __repr__(self) -> str:
        return super(ResolvableElement, self).__repr__()

    def get_config(self) -> Dict:
        return {}

    def content_type(self) -> Optional[str]:
        return None

    def is_empty(self) -> bool: ...  # type: ignore[empty-body]

    def get_bytes(self) -> bytes:
        return bytes()

    def set_bytes(self, b: bytes) -> None:
        pass

    def writable(self) -> bool: ...  # type: ignore[empty-body]


class TestDataElementHighLevelFromUri (unittest.TestCase):

    def test_no_classes(self) -> None:
        def impl_generator() -> Dict:
            return {}

        self.assertRaises(
            InvalidUriError,
            from_uri,
            'whatever',
            impl_generator
        )

    def test_no_resolvable_options(self) -> None:
        """
        when no DataElement implementations provide an implementation for
        the ``from_uri`` class method
        """
        def impl_generator() -> Iterable:
            return {UnresolvableElement}

        self.assertRaises(
            InvalidUriError,
            from_uri,
            'something',
            impl_generator
        )

    def test_one_resolvable_option(self) -> None:
        """
        When at least one plugin can resolve a URI
        """
        def impl_generator() -> Iterable:
            return {UnresolvableElement, ResolvableElement}

        # URI that can be resolved by ResolvableElement
        self.assertIsInstance(
            from_uri(
                "resolvable://data",
                impl_generator
            ),
            ResolvableElement
        )

        # bad URI even though something can resolve it
        self.assertRaises(
            InvalidUriError,
            from_uri,
            'not_resolvable', impl_generator
        )
