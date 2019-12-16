"""Test utilities."""

from datetime import date, timedelta

from django.test import TestCase

from orders import settings
from orders.utils import WeekColor, prettify_times


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
        """Likely to fail close to the end of the year."""
        delivery = date.today() + timedelta(days=7)
        color = WeekColor(delivery).get()
        self.assertEqual(color, settings.WEEK_COLORS['next'])

    def test_in_two_weeks_returns_proper_color(self):
        """Likely to fail close to the end of the year."""
        delivery = date.today() + timedelta(days=14)
        color = WeekColor(delivery).get()
        self.assertEqual(color, settings.WEEK_COLORS['in_two'])

    def test_more_than_two_weeks_returns_false(self):
        """The color is stored in settings.py."""
        delivery = date.today() + timedelta(days=23)
        color = WeekColor(delivery).get()
        self.assertFalse(color)

    def test_delivery_on_next_year_returns_false(self):
        """On changing year."""
        delivery = date.today() + timedelta(days=365)
        color = WeekColor(delivery).get()
        self.assertFalse(color)

    def test_before_than_this_week_returns_this_week_color(self):
        """The color is stored in settings.py."""
        delivery = date.today() - timedelta(days=7)
        color = WeekColor(delivery).get()
        self.assertEqual(color, settings.WEEK_COLORS['this'])


class PrettifyTimesTest(TestCase):

    def test_hours(self):
        s = prettify_times(5400)
        self.assertEqual(s, '1.5h')

    def test_minutes(self):
        s = prettify_times(90)
        self.assertEqual(s, '~2m')

    def test_seconds(self):
        s = prettify_times(50)
        self.assertEqual(s, '50s')
