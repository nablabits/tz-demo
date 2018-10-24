"""Test utilities."""

from orders.utils import TimeLenght
from django.test import TestCase


class TimeLenghtTest(TestCase):
    """Test the diferent utils for the app."""

    def test_time_length_accepts_floats(self):
        """Floats determine FL direction."""
        way = TimeLenght(5.5)
        self.assertEquals(way.direction(), 'FL')

    def test_time_length_accepts_str(self):
        """Strs determine LF direction."""
        way = TimeLenght('5:30')
        self.assertEquals(way.direction(), 'LF')

    def test_direction_raises_error_with_no_float_nor_string(self):
        """When something diferent is introduced raise an error."""
        way = TimeLenght(range(5))
        with self.assertRaises(ValueError):
            way.direction()

    def test_time_length_str_format(self):
        """The format for str should be H:MM otherwise raise error."""
        way = TimeLenght('abc')
        with self.assertRaises(ValueError):
            way.direction()
        way = TimeLenght('05:30')
        with self.assertRaises(ValueError):
            way.direction()
        way = TimeLenght('5:300')
        with self.assertRaises(ValueError):
            way.direction()

    def test_minutes_should_be_under_60(self):
        """Minutes over 59 should raise an exception."""
        way = TimeLenght('5:60')
        with self.assertRaises(ValueError):
            way.direction()

    def test_time_converts_float_to_duration(self):
        """Test the proper conversion of db entries to show in views."""
        time = TimeLenght(5.5)
        self.assertEqual(time.convert(), '5:30')

    def test_time_converts_duration_to_float(self):
        """Test the proper conversion of form entries into floats."""
        time = TimeLenght('5:30')
        self.assertEqual(time.convert(), 5.5)
