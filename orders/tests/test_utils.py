"""Test utilities."""

from orders.utils import WeekColor
from django.test import TestCase
from datetime import date, timedelta
from orders import settings


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
