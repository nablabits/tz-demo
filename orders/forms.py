from django import forms
from .models import Customer, Order, Comment


class CustomerForm(forms.ModelForm):
    """Create a form to add new customers"""

    class Meta:
        model = Customer
        fields = ('name', 'address', 'city', 'phone', 'email',
                  'CIF', 'cp', 'notif')


class OrderForm(forms.ModelForm):
    """Create a form to add new orders."""

    class Meta:
        model = Order
        fields = ('customer', 'ref_name', 'delivery', 'status',
                  'waist', 'chest', 'hip', 'lenght', 'others',
                  'budget', 'prepaid')