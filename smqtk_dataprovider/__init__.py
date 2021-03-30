import pkg_resources

from .interfaces.data_element import DataElement, from_uri  # noqa: F401
from .interfaces.data_set import DataSet  # noqa: F401
from .interfaces.key_value_store import KeyValueStore  # noqa: F401

from .content_type_validator import ContentTypeValidator  # noqa: F401


# It is known that this will fail if this package is not "installed" in the
# current environment. Additional support is pending defined use-case-driven
# requirements.
__version__ = pkg_resources.get_distribution(__name__).version
