from django.contrib import admin
from .models import Customer, Comment, Order, CommentCheck

admin.site.register(Customer)
admin.site.register(Comment)
admin.site.register(Order)
admin.site.register(CommentCheck)
