"""Some utilities to use in the app."""
from datetime import date

from . import settings


class WeekColor(object):
    """Generate a color depending the delivery's week."""

    # NOTE: this should be an Order @property

    def __init__(self, delivery):
        """Start the object."""
        if not isinstance(delivery, date):
            raise TypeError('The input should be a datetype')
        self.date = delivery

    def get(self):
        """Return the proper color."""
        # first, all the dates in the past have 'this' color
        distance = self.date - date.today()

        # Get the delivery and current week
        delivery = self.date.isocalendar()[1]
        this_week = date.today().isocalendar()[1]

        # Finally evaluate both numbers and return the proper color
        if distance.days < 0:
            return settings.WEEK_COLORS['this']
        elif delivery == this_week and distance.days < 7:
            return settings.WEEK_COLORS['this']
        elif delivery == this_week + 1 and distance.days < 15:
            return settings.WEEK_COLORS['next']
        elif delivery == this_week + 2 and distance.days < 22:
            return settings.WEEK_COLORS['in_two']
        else:
            return False


def prettify_times(duration):
    """Convert the lengths in seconds into displayable strings."""
    if duration > 60 * 60:  # we have hours (likely)
        duration = duration / 3600
        t_string = '{}h'.format(round(duration, 1))
    elif duration > 60:  # we have minutes
        duration = duration / 60
        t_string = '~{}m'.format(int(round(duration, 0)))
    else:
        t_string = '{}s'.format(int(duration))
    return t_string
