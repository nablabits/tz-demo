"""Define custom managers fro the models."""

from datetime import date

from django.db import models


# First, Order managers
class LiveOrders(models.Manager):
    """Get the active orders (all)."""

    def get_queryset(self):
        """Return the queryset."""
        live_orders = super().get_queryset().exclude(status__in=[8, 9])
        return live_orders.exclude(customer__name__iexact='express')


class OutdatedOrders(models.Manager):
    """Get the overdue orders."""

    def get_queryset(self):
        """Return the queryset."""
        orders = super().get_queryset().filter(delivery__lt=date.today())
        orders = orders.exclude(customer__name__iexact='express')
        return orders.exclude(status__in=[7, 8, 9])


class ObsoleteOrders(models.Manager):
    """Get the express orders that don't have invoice."""

    def get_queryset(self):
        """Return the queryset."""
        orders = super().get_queryset().filter(
            customer__name__iexact='express')
        return orders.filter(invoice__isnull=True)


class ActiveItems(models.Manager):
    """Get the active items (excluding tz ones)."""

    def get_queryset(self):
        """Return the queryset."""
        items = super().get_queryset().exclude(reference__status=8)
        items = items.filter(reference__delivery__gte=date(2019, 1, 1))
        items = items.exclude(reference__ref_name__iexact='quick')
        items = items.exclude(reference__customer__name__iexact='Trapuzarrak')
        return items.filter(reference__invoice__isnull=True)


class Inbounds(models.Manager):
    """Get the incomes measured by CashFlowIO model."""

    def get_queryset(self):
        """Return the queryset."""
        return super().get_queryset().filter(order__isnull=False)


class Outbounds(models.Manager):
    """Get the expenses measured by CashFlowIO model."""

    def get_queryset(self):
        """Return the queryset."""
        return super().get_queryset().filter(expense__isnull=False)


class ActiveTimetable(models.Manager):
    """Get the current active timetable for a user."""

    def get_queryset(self):
        """Return the queryset."""
        return super().get_queryset().filter(end__isnull=True)
