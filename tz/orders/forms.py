from django import forms
from .models import Customer, Order, Comment


class CustomerForm(forms.ModelForm):
    """Create a form with all the fields included in models.Weekly."""

    class Meta:
        model = Customer
        fields = ('name', 'address', 'city', 'phone', 'email',
                  'CIF', 'cp', 'notif')
