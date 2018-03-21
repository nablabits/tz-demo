from django.contrib import admin
from .models import Customer, Comments, Orders

admin.site.register(Customer)
admin.site.register(Comments)
admin.site.register(Orders)
