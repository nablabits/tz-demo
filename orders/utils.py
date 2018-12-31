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
        # first, all the dates in the past have 'this' color
        past = (self.date < date.today())
        future = (self.date >= date.today())

        # Get the delivery and current week
        delivery = self.date.isocalendar()[1]
        this_week = date.today().isocalendar()[1]

        # Finally evaluate both numbers and return the proper color
        if delivery <= this_week or past:
            return settings.WEEK_COLORS['this']
        elif delivery == this_week + 1 and future:
            return settings.WEEK_COLORS['next']
        elif delivery == this_week + 2 and future:
            return settings.WEEK_COLORS['in_two']
        else:
            return False
