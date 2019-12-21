"""Show all the models in the admin page."""

from django.contrib import admin

from .models import (
    BankMovement, Comment, Customer, Expense, Invoice, Item, Order, OrderItem,
    PQueue, Timetable, CashFlowIO, StatusShift, ExpenseCategory, )

from django.utils.translation import gettext_lazy as _


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Beautify the customer admin view."""

    date_hierarchy = ('creation')
    list_display = ('name', 'CIF', 'address', 'city', 'cp', 'phone', 'email', )
    list_filter = ('city', 'provider')


class CustomerByName(admin.SimpleListFilter):
    """Set the filter by issuer and order by name."""
    title = _('customer name')

    parameter_name = 'customer_by_name'

    def lookups(self, request, model_admin):
        """Returns a list of tuples.

        The first element in each tuple is the coded value for the option that
        will appear in the URL query. The second element is the human-readable
        name for the option that will appear
        in the right sidebar.
        """

        q = Customer.objects.filter(provider=False).order_by('name')

        return [(entry.name, entry.name) for entry in q]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        else:
            return queryset.filter(customer__name=self.value())


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Beautify the order admin view."""

    date_hierarchy = 'inbox_date'
    list_display = ('pk', 'inbox_date', 'customer', 'user', 'ref_name',
                    'status', 'budget', 'prepaid', )
    list_filter = ('status', CustomerByName)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Beautify the object item admin view."""

    list_display = ('pk', 'name', 'item_type', 'item_class', 'size')
    list_filter = ('item_type', 'item_class', 'price')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Beautify the order item admin view."""

    list_display = ('pk', 'element', 'qty', 'reference',
                    'crop', 'sewing', 'iron', 'price')
    list_filter = ('element', )


@admin.register(PQueue)
class PQueueAdmin(admin.ModelAdmin):
    """Beautify the order item admin view."""

    list_display = ('pk', 'item', 'score', )
    list_filter = ('score', )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Beautify the invoice admin view."""

    list_display = ('invoice_no', 'reference', 'issued_on', 'amount',
                    'pay_method', )


class IssuerByName(admin.SimpleListFilter):
    """Set the filter by issuer and order by name."""
    title = _('issuer name')

    parameter_name = 'issuer_by_name'

    def lookups(self, request, model_admin):
        """Returns a list of tuples.

        The first element in each tuple is the coded value for the option that
        will appear in the URL query. The second element is the human-readable
        name for the option that will appear
        in the right sidebar.
        """

        q = Customer.objects.filter(provider=True).order_by('name')

        return [(entry.name, entry.name) for entry in q]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        else:
            return queryset.filter(issuer__name=self.value())


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Beautify the expense admin view."""

    list_display = ('pk', 'issued_on', 'issuer', 'invoice_no', 'concept',
                    'category', 'amount', 'consultancy', 'closed')
    list_filter = ('issued_on', 'category', IssuerByName,)


class CFByType(admin.SimpleListFilter):
    """Set the filter by inbounds/outbounds."""
    title = _('inbound-outbound')

    parameter_name = 'cf_by_type'

    def lookups(self, request, model_admin):
        """Returns a list of tuples.

        The first element in each tuple is the coded value for the option that
        will appear in the URL query. The second element is the human-readable
        name for the option that will appear
        in the right sidebar.
        """

        return (('in', 'Inbounds'), ('out', 'Outbounds'), )

    def queryset(self, request, queryset):
        if self.value() == 'in':
            return queryset.filter(order__isnull=False)
        else:
            return queryset.filter(expense__isnull=False)


@admin.register(CashFlowIO)
class CashFlowIOAdmin(admin.ModelAdmin):
    """Beautify the CashFlow admin view."""

    list_display = (
        'pk', 'creation', 'order', 'expense', 'amount', 'pay_method', )

    list_filter = ('creation', CFByType, )


@admin.register(BankMovement)
class BankMovementAdmin(admin.ModelAdmin):
    """Beautify the order item admin view."""

    list_display = ('action_date', 'amount', 'notes', )


@admin.register(StatusShift)
class StatusTrackerAdmin(admin.ModelAdmin):
    """Beautify the status tracker admin view."""

    list_display = ('order', 'status', 'date_in', 'date_out', 'notes', )
    list_filter = ('date_in', )


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    """Beautify the Timetable admin view."""

    date_hierarchy = 'start'
    list_display = ('user', 'start', 'end', 'hours', )
    list_filter = ('user', )


admin.site.register(Comment)
admin.site.register(ExpenseCategory)
