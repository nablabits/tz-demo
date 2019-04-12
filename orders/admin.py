"""Show all the models in the admin page."""

from django.contrib import admin

from .models import (BankMovement, Comment, Customer, Expense, Invoice, Item,
                     Order, OrderItem, PQueue)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Beautify the customer admin view."""

    date_hierarchy = ('creation')
    list_display = ('name', 'CIF', 'address', 'city', 'cp', 'phone', 'email', )
    list_filter = ('city', 'provider' )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Beautify the order admin view."""

    date_hierarchy = 'inbox_date'
    list_display = ('pk', 'inbox_date', 'customer', 'user', 'ref_name',
                    'status', 'budget', 'prepaid', )
    list_filter = ('customer', 'status')


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


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Beautify the expense admin view."""

    list_display = (
        'pk', 'issued_on', 'issuer', 'invoice_no', 'concept', 'amount', )
    list_filter = ('issuer', )


@admin.register(BankMovement)
class BankMovementAdmin(admin.ModelAdmin):
    """Beautify the order item admin view."""

    list_display = ('action_date', 'amount', 'notes', )


admin.site.register(Comment)
