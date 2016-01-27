import abc
from collections import deque
import hashlib
import mimetypes
import os
import os.path as osp
import tempfile

from smqtk.representation import SmqtkRepresentation
from smqtk.utils import file_utils
from smqtk.utils import plugin


__author__ = "paul.tunison@kitware.com"


MIMETYPES = mimetypes.MimeTypes()


class DataElement (SmqtkRepresentation, plugin.Pluggable):
    """
    Abstract interface for a byte data.

    Basic data elements have a UUID, some byte content, a content type, and
    checksum accessor methods.

    UUIDs must maintain unique-ness when transformed into a string.

    """

    def __init__(self):
        super(DataElement, self).__init__()

        self._md5_cache = None
        self._sha1_cache = None
        self._temp_filepath_stack = []

    def __hash__(self):
        return hash(self.uuid())

    def __del__(self):
        self.clean_temp()

    def __eq__(self, other):
        return isinstance(other, DataElement) and \
               self.get_bytes() == other.get_bytes()

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "%s{uuid: %s, content_type: '%s'}" \
               % (self.__class__.__name__, self.uuid(), self.content_type())

    def _clear_no_exist(self):
        """
        Clear paths in temp list that don't exist on the system until we
        encounter one that does.
        """
        no_exist_paths = deque()
        for fp in self._temp_filepath_stack:
            if not osp.isfile(fp):
                no_exist_paths.append(fp)
        for fp in no_exist_paths:
            self._temp_filepath_stack.remove(fp)

    def md5(self):
        """
        :return: MD5 hex string of the data content.
        :rtype: str
        """
        if not self._md5_cache:
            self._md5_cache = hashlib.md5(self.get_bytes()).hexdigest()
        return self._md5_cache

    def sha1(self):
        """
        :return: SHA1 hex string of the data content.
        :rtype: str
        """
        if not self._sha1_cache:
            self._sha1_cache = hashlib.sha1(self.get_bytes()).hexdigest()
        return self._sha1_cache

    def write_temp(self, temp_dir=None):
        """
        Write this data's bytes to a temporary file on disk, returning the path
        to the written file, whose extension is guessed based on this data's
        content type.

        NOTE:
            The file path returned should not be explicitly removed by the user.
            Instead, the ``clean_temp()`` method should be called on this
            object.

        :param temp_dir: Optional directory to write temporary file in,
            otherwise we use the platform default temporary files directory.
            If this is an empty string, we count it the same as having provided
            None.
        :type temp_dir: None or str

        :return: Path to the temporary file
        :rtype: str

        """
        # Write a new temp file if there aren't any in the stack, or if the none
        # of the entries' base directory is the provided temp_dir (when one is
        # provided).

        def write_temp(d):
            """ Returns path to file written. Always creates new file. """
            if d:
                file_utils.safe_create_dir(d)
            ext = MIMETYPES.guess_extension(self.content_type())
            # Exceptions because mimetypes is apparently REALLY OLD
            if ext in {'.jpe', '.jfif'}:
                ext = '.jpg'
            fd, fp = tempfile.mkstemp(
                suffix=ext,
                dir=d
            )
            os.close(fd)
            with open(fp, 'wb') as f:
                f.write(self.get_bytes())
            return fp

        # Clear out paths, from the back, that don't exist.
        # Stops when it finds something that exists.
        self._clear_no_exist()

        if temp_dir:
            abs_temp_dir = osp.abspath(osp.expanduser(temp_dir))
            # Check if dir is the base of any path in the current stack.
            for tf in self._temp_filepath_stack:
                if osp.dirname(tf) == abs_temp_dir:
                    return tf
            # nothing in stack with given base directory, create new temp file
            self._temp_filepath_stack.append(write_temp(temp_dir))

        elif not self._temp_filepath_stack:
            # write new temp file to platform specific temp directory
            self._temp_filepath_stack.append(write_temp(None))

        # return last written temp file.
        return self._temp_filepath_stack[-1]

    def clean_temp(self):
        """
        Clean any temporary files created by this element. This does nothing if
        no temporary files have been generated for this element yet.
        """
        if len(self._temp_filepath_stack):
            for fp in self._temp_filepath_stack:
                if os.path.isfile(fp):
                    os.remove(fp)
            self._temp_filepath_stack = []

    def uuid(self):
        """
        UUID for this data element. This many take different forms from integers
        to strings to a uuid.UUID instance. This must return a hashable data
        type.

        By default, this ends up being the stringification of the SHA1 hash of
        this data's bytes. Specific implementations may provide other UUIDs,
        however.

        :return: UUID value for this data element. This return value should be
            hashable.
        :rtype: collections.Hashable

        """
        return self.sha1()

    ###
    # Abstract methods
    #

    @abc.abstractmethod
    def content_type(self):
        """
        :return: Standard type/subtype string for this data element, or None if
            the content type is unknown.
        :rtype: str or None
        """

    @abc.abstractmethod
    def get_bytes(self):
        """
        :return: Get the byte stream for this data element.
        :rtype: bytes
        """


def get_data_element_impls(reload_modules=False):
    """
    Discover and return discovered ``DataElement`` classes. Keys in the
    returned map are the names of the discovered classes, and the paired values
    are the actual class type objects.

    We search for implementation classes in:
        - modules next to this file this function is defined in (ones that begin
          with an alphanumeric character),
        - python modules listed in the environment variable ``DATA_ELEMENT_PATH``
            - This variable should contain a sequence of python module
              specifications, separated by the platform specific PATH separator
              character (``;`` for Windows, ``:`` for unix)

    Within a module we first look for a helper variable by the name
    ``DATA_ELEMENT_CLASS``, which can either be a single class object or
    an iterable of class objects, to be specifically exported. If the variable
    is set to None, we skip that module and do not import anything. If the
    variable is not present, we look at attributes defined in that module for
    classes that descend from the given base class type. If none of the above
    are found, or if an exception occurs, the module is skipped.

    :param reload_modules: Explicitly reload discovered modules from source.
    :type reload_modules: bool

    :return: Map of discovered class object of type ``DataElement``
        whose keys are the string names of the classes.
    :rtype: dict[str, type]

    """
    this_dir = os.path.abspath(os.path.dirname(__file__))
    env_var = "DATA_ELEMENT_PATH"
    helper_var = "DATA_ELEMENT_CLASS"
    return plugin.get_plugins(__name__, this_dir, env_var, helper_var,
                              DataElement, reload_modules=reload_modules)
