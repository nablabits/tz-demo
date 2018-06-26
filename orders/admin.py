from django.contrib import admin
from .models import Customer, Comment, Order

admin.site.register(Customer)
admin.site.register(Comment)
admin.site.register(Order)
