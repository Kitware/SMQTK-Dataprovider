import unittest

from smqtk_dataprovider.utils.string import random_characters


class TestRandomCharacters (unittest.TestCase):

    def test_zero_n(self) -> None:
        self.assertEqual(random_characters(0), '')

    def test_no_char_set(self) -> None:
        self.assertRaisesRegex(
            ValueError,
            "Empty char_set given",
            random_characters, 5, ()
        )

    def test_negative_n(self) -> None:
        self.assertRaisesRegex(
            ValueError,
            "n must be a positive integer",
            random_characters, -1234
        )

    def test_floating_point_n(self) -> None:
        # Testing that this should cast down to the integer 4.
        # noinspection PyTypeChecker
        s = random_characters(4.7)
        self.assertEqual(len(s), 4)
