"""Show all the models in the admin page."""

from django.contrib import admin
from .models import Customer, Comment, Order, Item, OrderItem, PQueue


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Beautify the customer admin view."""

    date_hierarchy = ('creation')
    list_display = ('name', 'CIF', 'address', 'city', 'cp', 'phone', 'email', )
    list_filter = ('city', )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Beautify the order admin view."""

    date_hierarchy = 'inbox_date'
    list_display = ('pk', 'inbox_date', 'customer', 'user', 'ref_name',
                    'status', 'budget', 'prepaid', 'pending')
    list_filter = ('customer', 'status')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Beautify the object item admin view."""

    list_display = ('pk', 'name', 'item_type', 'item_class', 'size')
    list_filter = ('item_type', 'item_class')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Beautify the order item admin view."""

    list_display = ('pk', 'element', 'qty', 'reference',
                    'crop', 'sewing', 'iron')
    list_filter = ('element', )


admin.site.register(Comment)
admin.site.register(PQueue)
