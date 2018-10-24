""" Some utilities to use in the app."""
import re


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
        """Convert the given time into float or duration."""
        direction = self.direction()
        if direction == 'FL':
            hours = int(self.time)
            minutes = int((self.time - hours) * 60)
            conversion = ('%s:%s' % (hours, minutes))
        elif direction == 'LF':
            duration = self.time.split(':')
            hours = float(duration[0])
            minutes = float(duration[1]) / 60
            conversion = round(hours + minutes, 2)

        return conversion
