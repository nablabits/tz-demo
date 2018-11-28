"""Test utilities."""

from orders.utils import TimeLenght, WeekColor
from django.test import TestCase
from datetime import date, timedelta
from orders import settings


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

    def test_time_rounds_to_5_min(self):
        """Time outputs should increase by 5 min step."""
        time = TimeLenght(1.33)
        self.assertEqual(time.convert(), '1:20')

    def test_time_converts_duration_to_float(self):
        """Test the proper conversion of form entries into floats."""
        time = TimeLenght('5:30')
        self.assertEqual(time.convert(), 5.5)


class WeekColorTest(TestCase):
    """test the color returned by the function."""

    def test_only_date_obj_are_allowed(self):
        """The imput should be a date object, otherwise reaise an error."""
        with self.assertRaises(TypeError):
            WeekColor('invalid type')

    def test_this_week_returns_proper_color(self):
        """The color is stored in settings.py."""
        delivery = date.today()
        color = WeekColor(delivery).get()
        self.assertEqual(color, settings.WEEK_COLORS['this'])

    def test_next_week_returns_proper_color(self):
        """The color is stored in settings.py."""
        delivery = date.today() + timedelta(days=7)
        color = WeekColor(delivery).get()
        self.assertEqual(color, settings.WEEK_COLORS['next'])

    def test_in_two_weeks_returns_proper_color(self):
        """The color is stored in settings.py."""
        delivery = date.today() + timedelta(days=14)
        color = WeekColor(delivery).get()
        self.assertEqual(color, settings.WEEK_COLORS['in_two'])

    def test_more_than_two_weeks_returns_false(self):
        """The color is stored in settings.py."""
        delivery = date.today() + timedelta(days=22)
        color = WeekColor(delivery).get()
        self.assertFalse(color)

    def test_delivery_on_next_year_returns_false(self):
        """On changing year."""
        next_year = date.today().year + 1
        delivery = date(next_year, 1, 1)
        color = WeekColor(delivery).get()
        self.assertFalse(color)

    def test_before_than_this_week_returns_this_week_color(self):
        """The color is stored in settings.py."""
        delivery = date.today() - timedelta(days=7)
        color = WeekColor(delivery).get()
        self.assertEqual(color, settings.WEEK_COLORS['this'])
