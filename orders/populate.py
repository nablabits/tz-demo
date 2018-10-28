"""Populates the db to have objects to play with."""

from .models import Comment, Customer, Order, OrderItem, Timing
from django.contrib.auth.models import User


class NewPopulation(object):
    """Create a new db representation."""

    def __init__(self):
        """Populate the db."""
        if self.populated():
            raise RuntimeError('The db is not empty, please run' +
                               ' \'dropdb tz_it\'')

            # create some users
            regular = User.objects.create_user(username='regular',
                                               password='test')
            another = User.objects.create_user(username='another',
                                               password='test')
            regular.save()
            another.save()

    def populated(self):
        """Test if the db is already populated."""
        populated = False
        for model in (Comment, Customer, Order, OrderItem, Timing):
            try:
                model.objects.all()[0]
            except IndexError:
                pass
            else:
                populated = True
            return populated
