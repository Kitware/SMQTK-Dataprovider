import unittest

import pytest

from smqtk_dataprovider.utils.postgres import psycopg2, PsqlConnectionHelper
from typing import Iterable


@pytest.mark.skipif(psycopg2 is None,
                    reason="Psycopg2 module is not importable, postgres "
                           "utilities are not available.")
class TestPsqlConnectionHelper (unittest.TestCase):

    def setUp(self) -> None:
        self.conn_helper = PsqlConnectionHelper()

    def test_batch_execute_on_empty_iterable(self) -> None:
        # noinspection PyUnusedLocal
        def exec_hook(cur: psycopg2._psycopg.cursor, batch: Iterable) -> None:
            raise Exception('This line shouldn\'t be reached with an empty '
                            'iterable.')

        list(self.conn_helper.batch_execute(iter(()), exec_hook, 1))
