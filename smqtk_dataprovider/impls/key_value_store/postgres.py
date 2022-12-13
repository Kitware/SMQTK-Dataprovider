import logging
import multiprocessing
import pickle
from typing import Any, Dict, Hashable, Iterator, Iterable, Mapping, Optional, Set

from smqtk_dataprovider import KeyValueStore
from smqtk_dataprovider.interfaces.key_value_store import NO_DEFAULT_VALUE
from smqtk_dataprovider.utils.postgres import norm_psql_cmd_string, PsqlConnectionHelper

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.extensions
except ImportError as ex:
    logging.getLogger(__name__)\
           .warning("Failed to import psycopg2: %s", str(ex))
    psycopg2 = None  # type: ignore


PSQL_TABLE_CREATE_RLOCK = multiprocessing.RLock()


class PostgresKeyValueStore (KeyValueStore):
    """
    PostgreSQL-backed key-value storage.
    """

    class SqlTemplates:
        """
        Container for static PostgreSQL queries used by the containing class.
        """

        UPSERT_TABLE_TMPL = norm_psql_cmd_string("""
            CREATE TABLE IF NOT EXISTS {table_name:s} (
              {key_col:s} BYTEA NOT NULL,
              {value_col:s} BYTEA NOT NULL,
              PRIMARY KEY ({key_col:s})
            );
        """)

        SELECT_TMPL = norm_psql_cmd_string("""
            SELECT {query:s} FROM {table_name:s};
        """)

        SELECT_LIKE_TMPL = norm_psql_cmd_string("""
            SELECT {query:s}
              FROM {table_name:s}
             WHERE {key_col:s} LIKE %(key_like)s
        """)

        SELECT_MANY_TMPL = norm_psql_cmd_string("""
            SELECT {query:s}
              FROM {table_name:s}
             WHERE {key_col:s} IN %(key_tuple)s
        """)

        UPSERT_TMPL = norm_psql_cmd_string("""
            INSERT INTO {table_name:s} ({key_col:s}, {value_col:s})
                VALUES (%(key)s, %(val)s)
                ON CONFLICT ({key_col:s})
                    DO UPDATE
                        SET {value_col:s} = EXCLUDED.{value_col:s}
        """)

        DELETE_LIKE_TMPL = norm_psql_cmd_string("""
            DELETE FROM {table_name:s}
            WHERE {key_col:s} LIKE %(key_like)s
        """)

        DELETE_ALL = norm_psql_cmd_string("""
            DELETE FROM {table_name:s}
        """)

    @classmethod
    def is_usable(cls) -> bool:
        return psycopg2 is not None

    def __init__(
        self,
        table_name: str = "data_set",
        key_col: str = 'key',
        value_col: str = 'value',
        db_name: str = 'postgres',
        db_host: Optional[str] = None,
        db_port: Optional[int] = None,
        db_user: Optional[str] = None,
        db_pass: Optional[str] = None,
        batch_size: int = 1000,
        pickle_protocol: int = -1,
        read_only: bool = False,
        create_table: bool = True
    ):
        """
        Initialize a PostgreSQL-backed data set instance.

        :param table_name: Name of the table to use.
        :param key_col: Name of the column containing the UUID signatures.
        :param value_col: Name of the table column that will contain
            serialized elements.
        :param db_name: The name of the database to connect to.
        :param db_host: Host address of the Postgres server. If None, we
            assume the server is on the local machine and use the UNIX socket.
            This might be a required field on Windows machines (not tested yet).
        :param db_port: Port the Postgres server is exposed on. If None, we
            assume the default port (5423).
        :param db_user: Postgres user to connect as. If None, postgres
            defaults to using the current accessing user account name on the
            operating system.
        :param db_pass: Password for the user we're connecting as. This may be
            None if no password is to be used.
        :param batch_size: For queries that handle sending or
            receiving many queries at a time, batch queries based on this size.

            The advantage of batching is that it reduces the memory impact for
            queries dealing with a very large number of elements (don't have to
            store the full query for all elements in RAM), but the transaction
            will be some amount slower due to splitting the query into multiple
            transactions.
        :param pickle_protocol: Pickling protocol to use. We will use -1 by
            default (the latest version, probably binary).
        :param read_only: Only allow read actions against this index.
            Modification actions will throw a ReadOnlyError exceptions.
        :param create_table: If this instance should try to create the storing
            table before actions are performed against it when not set to be
            read-only. If the configured user does not have sufficient
            permissions to create the table and it does not currently exist, an
            exception will be raised.
        """
        super(PostgresKeyValueStore, self).__init__()

        self._table_name = table_name
        self._key_col = key_col
        self._value_col = value_col

        self._batch_size = batch_size
        self._pickle_protocol = pickle_protocol
        self._read_only = bool(read_only)
        self._create_table = create_table

        # Checking parameters where necessary
        if self._batch_size is not None:
            self._batch_size = int(self._batch_size)
            assert self._batch_size > 0, \
                "A given batch size must be greater than 0 in size " \
                "(given: %d)." % self._batch_size
        assert -1 <= self._pickle_protocol <= 2, \
            ("Given pickle protocol is not in the known valid range [-1, 2]. "
             "Given: %s." % self._pickle_protocol)

        # helper structure for SQL operations.
        self._psql_helper = PsqlConnectionHelper(
            db_name, db_host, db_port, db_user, db_pass,
            itersize=batch_size,
            table_upsert_lock=PSQL_TABLE_CREATE_RLOCK,
        )

        # Only set table upsert if not read-only.
        if not self._read_only and self._create_table:
            # NOT read-only, so allow table upsert.
            self._psql_helper.set_table_upsert_sql(
                self.SqlTemplates.UPSERT_TABLE_TMPL.format(
                    table_name=self._table_name,
                    key_col=self._key_col,
                    value_col=self._value_col
                )
            )

    @staticmethod
    def _py_to_bin(k: Any) -> "psycopg2.Binary":
        """
        Convert a python hashable value into psycopg2.Binary via pickle.

        :param k: Python object instance to be converted into a
            ``psycopg2.Binary`` instance via ``pickle`` serialization.

        :return: ``psycopg2.Binary`` buffer instance to use for insertion into
            or query against a table.
        """
        return psycopg2.Binary(pickle.dumps(k))

    @staticmethod
    def _bin_to_py(b: memoryview) -> Any:
        """
        Un-"translate" a memory buffer from a PSQL query into a python type.

        :param b: ``psycopg2.Binary`` buffer instance as retrieved from a
            PostgreSQL query.

        :return: Python object instance as loaded via pickle from the given
            buffer.
        """
        return pickle.loads(bytes(b))

    def get_config(self) -> Dict:
        """
        Return a JSON-compliant dictionary that could be passed to this class's
        ``from_config`` method to produce an instance with identical
        configuration.

        In the common case, this involves naming the keys of the dictionary
        based on the initialization argument names as if it were to be passed
        to the constructor via dictionary expansion.

        :return: JSON type compliant configuration dictionary.
        :rtype: dict

        """
        return {
            "table_name": self._table_name,
            "key_col": self._key_col,
            "value_col": self._value_col,

            "db_name": self._psql_helper.db_name,
            "db_host": self._psql_helper.db_host,
            "db_port": self._psql_helper.db_port,
            "db_user": self._psql_helper.db_user,
            "db_pass": self._psql_helper.db_pass,

            "batch_size": self._batch_size,
            "pickle_protocol": self._pickle_protocol,
            "read_only": self._read_only,
            "create_table": self._create_table,
        }

    def __repr__(self) -> str:
        """
        :return: Representative string for this class.
        """
        return (
            f"{super().__repr__()}{{"
            f"table_name: {self._table_name}, "
            f"key_col: {self._key_col}, "
            f"value_col: {self._value_col}, "
            f"db_name: {self._psql_helper.db_name}, "
            f"db_host: {self._psql_helper.db_host}, "
            f"db_port: {self._psql_helper.db_port}, "
            f"db_pass: {'***' if self._psql_helper.db_pass is not None else 'None'}, "
            f"batch_size: {self._batch_size}, "
            f"pickle_protocol: {self._pickle_protocol}, "
            f"read_only: {self._read_only}, "
            f"create_table: {self._create_table}"
            f"}}"
        )

    def count(self) -> int:
        """
        :return: The number of key-value relationships in this store.
        :rtype: int | long
        """
        def cb(cur: psycopg2.extensions.cursor) -> None:
            cur.execute(self.SqlTemplates.SELECT_TMPL.format(
                query='count(%s)' % self._key_col,
                table_name=self._table_name,
            ))
        return list(self._psql_helper.single_execute(
            cb, yield_result_rows=True
        ))[0][0]

    def keys(self) -> Iterator[Hashable]:
        """
        :return: Iterator over keys in this store.
        :rtype: collections.abc.Iterator[collections.abc.Hashable]
        """
        def cb(cur: psycopg2.extensions.cursor) -> None:
            cur.execute(self.SqlTemplates.SELECT_TMPL.format(
                query=self._key_col,
                table_name=self._table_name,
            ))
        # We can use a named cursor because this is a select statement as well
        # as server table size may be large.
        for r in self._psql_helper.single_execute(cb, yield_result_rows=True,
                                                  named=True):
            # Convert from buffer -> string -> python
            yield self._bin_to_py(r[0])

    def values(self) -> Iterator[Any]:
        """
        :return: Iterator over values in this store. Values are not guaranteed
            to be in any particular order.
        """
        def cb(cur: psycopg2.extensions.cursor) -> None:
            cur.execute(self.SqlTemplates.SELECT_TMPL.format(
                query=self._value_col,
                table_name=self._table_name,
            ))
        for r in self._psql_helper.single_execute(cb, yield_result_rows=True,
                                                  named=True):
            # Convert from buffer -> string -> python
            yield self._bin_to_py(r[0])

    def is_read_only(self) -> bool:
        """
        :return: True if this instance is read-only and False if it is not.
        :rtype: bool
        """
        return self._read_only

    def has(self, key: Hashable) -> bool:
        """
        Check if this store has a value for the given key.

        :param key: Key to check for a value for.
        :type key: collections.abc.Hashable

        :return: If this store has a value for the given key.
        :rtype: bool

        """
        # Try to select based on given key value. If any rows are returned,
        # there is clearly a key that matches.
        q = self.SqlTemplates.SELECT_LIKE_TMPL.format(
            query='true',
            table_name=self._table_name,
            key_col=self._key_col,
        )

        def cb(cur: psycopg2.extensions.cursor) -> None:
            cur.execute(q, {'key_like': self._py_to_bin(key)})
        return bool(list(self._psql_helper.single_execute(
            cb, yield_result_rows=True
        )))

    def add(self, key: Hashable, value: Any) -> "PostgresKeyValueStore":
        """
        Add a key-value pair to this store.

        :param key: Key for the value. Must be hashable.
        :param value: Python object to store.

        :raises ReadOnlyError: If this instance is marked as read-only.

        :return: Self.
        """
        super(PostgresKeyValueStore, self).add(key, value)

        q = self.SqlTemplates.UPSERT_TMPL.format(
            table_name=self._table_name,
            key_col=self._key_col,
            value_col=self._value_col,
        )
        v = {
            'key': self._py_to_bin(key),
            'val': self._py_to_bin(value),
        }

        def cb(cur: psycopg2.extensions.cursor) -> None:
            cur.execute(q, v)

        list(self._psql_helper.single_execute(cb))
        return self

    def add_many(self, d: Mapping[Hashable, Any]) -> "PostgresKeyValueStore":
        """
        Add multiple key-value pairs at a time into this store as represented in
        the provided dictionary `d`.

        :param d: Dictionary of key-value pairs to add to this store.

        :return: Self.
        """
        super(PostgresKeyValueStore, self).add_many(d)

        q = self.SqlTemplates.UPSERT_TMPL.format(
            table_name=self._table_name,
            key_col=self._key_col,
            value_col=self._value_col,
        )

        # Iterator over transformed inputs into values for statement.
        def val_iter() -> Iterator:
            for key, val in d.items():
                yield {
                    'key': self._py_to_bin(key),
                    'val': self._py_to_bin(val)
                }

        def cb(cur: psycopg2.extensions.cursor, v_batch: Iterable) -> None:
            psycopg2.extras.execute_batch(cur, q, v_batch,
                                          page_size=self._batch_size)

        list(self._psql_helper.batch_execute(val_iter(), cb, self._batch_size))
        return self

    def remove(self, key: Hashable) -> KeyValueStore:
        """
        Remove a single key-value entry.

        :param key: Key to remove.
        :type key: collections.abc.Hashable

        :raises ReadOnlyError: If this instance is marked as read-only.
        :raises KeyError: The given key is not present in this store and no
            default value given.

        :return: Self.
        :rtype: KeyValueStore

        """
        super(PostgresKeyValueStore, self).remove(key)
        if key not in self:
            raise KeyError(key)

        q = self.SqlTemplates.DELETE_LIKE_TMPL.format(
            table_name=self._table_name,
            key_col=self._key_col,
        )
        v = dict(
            key_like=self._py_to_bin(key)
        )

        def cb(cursor: psycopg2.extensions.cursor) -> None:
            cursor.execute(q, v)

        list(self._psql_helper.single_execute(cb))
        return self

    def _check_contained_keys(self, keys: Set[Hashable]) -> Set[Hashable]:
        """
        Check if the table contains the following keys.

        :param set keys: Keys to check for.

        :return: An set of keys NOT present in the table.
        :rtype: set[collections.abc.Hashable]
        """
        def key_like_iter() -> Iterable:
            for k_ in keys:
                yield self._py_to_bin(k_)

        has_many_q = self.SqlTemplates.SELECT_MANY_TMPL.format(
            query=self._key_col,
            table_name=self._table_name,
            key_col=self._key_col,
        )

        # Keys found in table
        matched_keys: Set[Hashable] = set()

        def cb(cursor: psycopg2.extensions.cursor, batch: Iterable) -> None:
            cursor.execute(has_many_q, {'key_tuple': tuple(batch)})
            matched_keys.update(self._bin_to_py(r[0]) for r in cursor)

        list(self._psql_helper.batch_execute(key_like_iter(), cb,
                                             self._batch_size))

        return keys - matched_keys

    def remove_many(self, keys: Iterable[Hashable]) -> KeyValueStore:
        """
        Remove multiple keys and associated values.

        :param keys: Iterable of keys to remove.  If this is empty this method
            does nothing.
        :type keys: collections.abc.Iterable[collections.abc.Hashable]

        :raises ReadOnlyError: If this instance is marked as read-only.
        :raises KeyError: The given key is not present in this store and no
            default value given.  The store is not modified if any key is
            invalid.

        :return: Self.
        :rtype: KeyValueStore

        """
        super(PostgresKeyValueStore, self).remove_many(keys)
        keys = set(keys)

        # Check that all keys requested for removal are contained in our table
        # before attempting to remove any of them.
        key_diff = self._check_contained_keys(keys)
        # If we're trying to remove a key not in our table, appropriately raise
        # a KeyError.
        if key_diff:
            if len(key_diff) == 1:
                raise KeyError(list(key_diff)[0])
            else:
                raise KeyError(key_diff)

        # Proceed with removal
        def key_like_iter() -> Iterator:
            """ Iterator over query value sets. """
            for k_ in keys:
                yield self._py_to_bin(k_)

        del_q = self.SqlTemplates.DELETE_LIKE_TMPL.format(
            table_name=self._table_name,
            key_col=self._key_col,
        )

        def del_cb(cursor: psycopg2.extensions.cursor, v_batch: Iterable) -> None:
            # Execute the query with a list of value dicts.
            psycopg2.extras.execute_batch(cursor, del_q,
                                          [{'key_like': k} for k in v_batch],
                                          page_size=self._batch_size)

        list(self._psql_helper.batch_execute(key_like_iter(), del_cb,
                                             self._batch_size))
        return self

    def get(self, key: Hashable, default: Any = NO_DEFAULT_VALUE) -> Any:
        """
        Get the value for the given key.

        *NOTE:* **Implementing sub-classes are responsible for raising a
        ``KeyError`` where appropriate.**

        :param key: Key to get the value of.
        :param default: Optional default value if the given key is not present
            in this store. This may be any value except for the
            ``NO_DEFAULT_VALUE`` constant (custom anonymous class instance).

        :raises KeyError: The given key is not present in this store and no
            default value given.

        :return: Deserialized python object stored for the given key.
        """
        q = self.SqlTemplates.SELECT_LIKE_TMPL.format(
            query=self._value_col,
            table_name=self._table_name,
            key_col=self._key_col,
        )
        v = {'key_like': self._py_to_bin(key)}

        def cb(cur: psycopg2.extensions.cursor) -> None:
            cur.execute(q, v)

        rows = list(self._psql_helper.single_execute(
            cb, yield_result_rows=True
        ))
        # If no rows and no default, raise KeyError.
        if len(rows) == 0:
            if default is NO_DEFAULT_VALUE:
                raise KeyError(key)
            else:
                return default
        return self._bin_to_py(rows[0][0])

    def get_many(self, keys: Iterable[Hashable], default: Any = NO_DEFAULT_VALUE) -> Iterable[Any]:
        """
        Get the values for the given keys.

        *NOTE:* **Implementing sub-classes are responsible for raising a
        ``KeyError`` where appropriate.**

        :param keys: The keys for which associated values are requested.
        :param default: Optional default value if a given key is not present
            in this store. This may be any value except for the
            ``NO_DEFAULT_VALUE`` constant (custom anonymous class instance).

        :raises KeyError: A given key is not present in this store and no
            default value given.

        :return: Iterable of deserialized python objects stored for the given
            keys in the order that the corresponding keys were provided.
        """
        sql_command_string = self.SqlTemplates.SELECT_MANY_TMPL.format(
            query=', '.join((self._key_col, self._value_col)),
            table_name=self._table_name,
            key_col=self._key_col
        )
        keys = list(keys)

        sql_keys = tuple(self._py_to_bin(key_) for key_ in keys)
        sql_variables = {'key_tuple': sql_keys}

        def postgres_callback(cursor: psycopg2.extensions.cursor) -> None:
            cursor.execute(sql_command_string, sql_variables)

        retrieved_dict = {
            self._bin_to_py(row_[0]): self._bin_to_py(row_[1])
            for row_ in self._psql_helper.single_execute(
                postgres_callback, yield_result_rows=True
            )
        }

        if default is NO_DEFAULT_VALUE:
            for key_ in keys:
                yield retrieved_dict[key_]
        else:
            for key_ in keys:
                yield retrieved_dict.get(key_, default)

    def clear(self) -> KeyValueStore:
        """
        Clear this key-value store.

        *NOTE:* **Implementing sub-classes should call this super-method. This
        super method should not be considered a critical section for thread
        safety.**

        :raises ReadOnlyError: If this instance is marked as read-only.

        """
        q = self.SqlTemplates.DELETE_ALL.format(table_name=self._table_name)

        def cb(cur: psycopg2.extensions.cursor) -> None:
            cur.execute(q)

        list(self._psql_helper.single_execute(cb))
        return self
