from typing import Set
import unittest.mock as mock

import pytest

from smqtk_dataprovider import DataElement
from smqtk_dataprovider.content_type_validator import ContentTypeValidator


class StubValidator (ContentTypeValidator):

    def valid_content_types(self) -> Set[str]:
        return {'foo', 'bar'}


class TestContentTypeValidator:

    def test_is_valid_element(self) -> None:
        """
        Test that an element matching one of the stub's content types yields a
        `true` result.
        """
        m_de1 = mock.MagicMock(spec=DataElement)
        m_de1.content_type.return_value = "bar"
        m_de2 = mock.MagicMock(spec=DataElement)
        m_de2.content_type.return_value = "foo"

        sv = StubValidator()
        assert sv.is_valid_element(m_de1)
        assert sv.is_valid_element(m_de2)

    def test_is_valid_element_mismatch(self) -> None:
        """
        Test that an element *not* matching one of the stub's content types
        yields a `false` result.
        """
        m_de = mock.MagicMock(spec=DataElement)
        m_de.content_type.return_value = "other"

        sv = StubValidator()
        assert not sv.is_valid_element(m_de)

    def test_raise_valid_element(self) -> None:
        """
        Test that an exception is not raise when a data element matches content
        type with one of the valid ones encoded.
        """
        m_de = mock.MagicMock(spec=DataElement)
        m_de.content_type.return_value = 'foo'

        sv = StubValidator()
        r = sv.raise_valid_element(m_de)
        assert r is m_de

    def test_raise_valid_element_incorrect_ct(self) -> None:
        """
        Test that the default exception and message are raised when the content
        type is not a "valid" one.
        """
        m_de = mock.MagicMock(spec=DataElement)
        m_de.content_type.return_value = 'other'

        sv = StubValidator()
        with pytest.raises(ValueError,
                           match=r"Data element does not match a content type "
                                 r'reported as valid\. Given: "other"\. '
                                 r"Valid types: "
                                 r"\['(foo|bar)', '(foo|bar)'\]\."):
            sv.raise_valid_element(m_de)

    def test_raise_valid_element_custom_error(self) -> None:
        """
        Test raising on content type mismatch with a non-default exception
        type.
        """
        class CustomException (BaseException):
            pass

        m_de = mock.MagicMock(spec=DataElement)
        m_de.content_type.return_value = 'other'

        sv = StubValidator()
        with pytest.raises(CustomException,
                           match=r"Data element does not match a content type "
                                 r'reported as valid\. Given: "other"\. '
                                 r"Valid types: "
                                 r"\['(foo|bar)', '(foo|bar)'\]\."):
            sv.raise_valid_element(m_de, exception_type=CustomException)

    def test_raise_valid_element_custom_message(self) -> None:
        """
        Test raising on content type mismatch with a non-default message
        string.
        """
        msg = "My custom message."

        m_de = mock.MagicMock(spec=DataElement)
        m_de.content_type.return_value = 'other'

        sv = StubValidator()
        with pytest.raises(ValueError, match=msg):
            sv.raise_valid_element(m_de, message=msg)
