from django import forms
from .models import Customer, Order, OrderItem, Comment, Document
from django.db.models import Count


class CustomerForm(forms.ModelForm):
    """Create a form to add new customers"""

    class Meta:
        model = Customer
        fields = ('name', 'address', 'city', 'phone', 'email',
                  'CIF', 'cp', 'notif')


class OrderForm(forms.ModelForm):
    """Create a form to add or edit orders."""

    class Meta:
        model = Order
        fields = ('customer', 'ref_name', 'delivery',
                  'waist', 'chest', 'hip', 'lenght', 'others',
                  'budget', 'prepaid')

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        queryset = Customer.objects.annotate(num_orders=Count('order'))[:10]
        self.fields['customer'].queryset = queryset
        self.fields['customer'].label = 'Cliente'

class OrderItemForm(forms.ModelForm):
    """Add items using a form."""

    class Meta:
        model = OrderItem
        fields = ('item', 'size', 'qty')


class DocumentForm(forms.ModelForm):
    """Create a form to upload files."""

    class Meta:
        model = Document
        fields = ('description', 'document', )


class CommentForm(forms.ModelForm):
    """Add commnets using a form."""

    class Meta:
        model = Comment
        fields = ('comment', )


class OrderCloseForm(forms.ModelForm):
    """Close orders using a form."""

    class Meta:
        model = Order
        fields = ('prepaid', 'workshop')
