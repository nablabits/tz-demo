"""Define custom managers fro the models."""

from datetime import date

from django.db import models


# First, Order managers
class ActiveOrders(models.Manager):
    """Get the active orders (all)."""

    def get_queryset(self):
        """Return the queryset."""
        return super().get_queryset().exclude(status__in=[7, 8])


class PendingOrders(models.Manager):
    """Get the pending orders."""

    def get_queryset(self):
        """Return the queryset."""
        orders = super().get_queryset().exclude(status=8)
        orders = orders.filter(delivery__gte=date(2019, 1, 1))
        orders = orders.exclude(ref_name__iexact='quick')
        orders = orders.exclude(customer__name__iexact='Trapuzarrak')
        return orders.filter(invoice__isnull=True)


class OutdatedOrders(models.Manager):
    """Get the overdue orders."""

    def get_queryset(self):
        """Return the queryset."""
        orders = super().get_queryset().filter(delivery__lt=date.today())
        return orders.exclude(status__in=[7, 8])


class ObsoleteOrders(models.Manager):
    """Get the express orders that don't have invoice."""

    def get_queryset(self):
        """Return the queryset."""
        orders = super().get_queryset().filter(
            customer__name__iexact='express')
        return orders.filter(invoice__isnull=True)


# Now, OrderItems managers
class ActiveItems(models.Manager):
    """Get the active items (excluding tz ones)."""

    def get_queryset(self):
        """Return the queryset."""
        items = super().get_queryset().exclude(reference__status=8)
        items = items.filter(reference__delivery__gte=date(2019, 1, 1))
        items = items.exclude(reference__ref_name__iexact='quick')
        items = items.exclude(reference__customer__name__iexact='Trapuzarrak')
        return items.filter(reference__invoice__isnull=True)
