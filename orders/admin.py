"""Show all the models in the admin page."""

from django.contrib import admin
from .models import Customer, Comment, Order, OrderItem, Timing

admin.site.register(Customer)
admin.site.register(Comment)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Timing)
