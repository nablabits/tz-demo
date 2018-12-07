"""Some utilities to use in the app."""
from . import settings
from datetime import date


class WeekColor(object):
    """Generate a color depending the delivery's week."""

    def __init__(self, delivery):
        """Start the object."""
        if not isinstance(delivery, date):
            raise TypeError('The imput should be a datetype')
        self.date = delivery

    def get(self):
        """Return the proper color."""

        # first get the delivery and current week
        delivery = self.date.isocalendar()[1]
        this_week = date.today().isocalendar()[1]

        # If delivery is on next year avoid the isocalendar reset
        if self.date.year > date.today().year:
            delivery = delivery + 52
        elif self.date.year < date.today().year:
            delivery = delivery - 53

        # Finally evaluate both numbers and return the proper color
        if delivery <= this_week:
            return settings.WEEK_COLORS['this']
        elif delivery == this_week + 1:
            return settings.WEEK_COLORS['next']
        elif delivery == this_week + 2:
            return settings.WEEK_COLORS['in_two']
        else:
            return False
