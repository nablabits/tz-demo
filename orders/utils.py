"""Some utilities to use in the app."""
import re
from . import settings
from datetime import date


class TimeLenght(object):
    """Convert floats into H:MM and viceversa."""

    def __init__(self, time):
        """Start out the object."""
        self.time = time

    def direction(self):
        """Decide the conversion way.

        FL means floatToLength, otherwise LF
        """
        if isinstance(self.time, float):
            way = 'FL'
        elif isinstance(self.time, str):
            check = re.match(r'^\d:\d{2}$', self.time)
            if check:
                way = 'LF'
            else:
                raise ValueError('The time was not recognized:', self.time)
            if int(self.time.split(':')[1]) > 59:
                raise ValueError('Minutes should be under 60')
        else:
            raise ValueError('The time was not recognized:', self.time)
        return way

    def convert(self):
        """Convert the given time into float or duration.

        Durations increase by 5' step.
        """
        direction = self.direction()
        if direction == 'FL':
            hours = int(self.time)
            minutes = int((self.time - hours) * 60)
            minutes = round(minutes / 10) * 10
            conversion = ('%s:%s' % (hours, minutes))
        elif direction == 'LF':
            duration = self.time.split(':')
            hours = float(duration[0])
            minutes = float(duration[1]) / 60
            conversion = round(hours + minutes, 2)
        else:
            raise ValueError('No valid direction was given')

        return conversion


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
