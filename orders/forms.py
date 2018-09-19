"""Form models used in the app."""

from django import forms
from .models import Customer, Order, OrderItem, Comment, Timing
from django.db.models import Count


class CustomerForm(forms.ModelForm):
    """Create a form to add new customers."""

    class Meta:
        """Meta options for a quick design."""

        model = Customer
        fields = ('name', 'address', 'city', 'phone', 'email',
                  'CIF', 'cp')


class OrderForm(forms.ModelForm):
    """Create a form to add or edit orders."""

    class Meta:
        """Meta options for a quick design."""

        model = Order
        fields = ('customer', 'ref_name', 'delivery',
                  'waist', 'chest', 'hip', 'lenght', 'others',
                  'budget', 'prepaid')

    def __init__(self, *args, **kwargs):
        """Sort selection dropdown by getting the orders made by customer."""
        super(OrderForm, self).__init__(*args, **kwargs)
        self.fields['customer'].label = 'Cliente'
        queryset = Customer.objects.annotate(num_orders=Count('order'))
        self.fields['customer'].queryset = queryset


class OrderItemForm(forms.ModelForm):
    """Add items using a form."""

    class Meta:
        """Meta options for a quick design."""

        model = OrderItem
        fields = ('item', 'size', 'qty', 'description')


class CommentForm(forms.ModelForm):
    """Add commnets using a form."""

    class Meta:
        """Meta options for a quick design."""

        model = Comment
        fields = ('comment', )


class TimeForm(forms.ModelForm):
    """Add times to db.

    Time could be added to any order regardless its state.
    """

    class Meta:
        """Meta options for a quick design."""

        model = Timing
        fields = ('reference',
                  'item', 'item_class', 'activity', 'qty', 'time', 'notes')

    def __init__(self, *args, **kwargs):
        """Override the order in the reference dropdown."""
        super(TimeForm, self).__init__(*args, **kwargs)
        self.fields['reference'].label = 'Pedido'
        queryset = Order.objects.order_by('inbox_date')[:25]
        self.fields['reference'].queryset = queryset


class OrderCloseForm(forms.ModelForm):
    """Close orders using a form."""

    class Meta:
        """Meta options for a quick design."""

        model = Order
        fields = ('prepaid',)
