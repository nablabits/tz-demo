"""Form models used in the app."""

from django import forms
from .models import Customer, Order, Item, OrderItem, Comment, Timing
from django.db.models import Count


class CustomerForm(forms.ModelForm):
    """Create a form to add new customers."""

    class Meta:
        """Meta options for a quick design."""

        model = Customer
        fields = ('name', 'address', 'city', 'phone', 'email',
                  'CIF', 'cp', 'notes')


class OrderForm(forms.ModelForm):
    """Create a form to add or edit orders."""

    class Meta:
        """Meta options for a quick design."""

        model = Order
        fields = ('customer', 'ref_name', 'delivery', 'priority',
                  'waist', 'chest', 'hip', 'lenght', 'others',
                  'budget', 'prepaid')

    def __init__(self, *args, **kwargs):
        """Sort selection dropdown by getting the orders made by customer."""
        super(OrderForm, self).__init__(*args, **kwargs)
        self.fields['customer'].label = 'Cliente'
        queryset = Customer.objects.annotate(num_orders=Count('order'))
        self.fields['customer'].queryset = queryset


class ItemForm(forms.ModelForm):
    """Add new item objects."""

    class Meta:
        """Meta options for a quick design."""

        model = Item
        fields = ('name', 'item_type', 'item_class', 'size', 'fabrics',
                  'notes', 'foreing', )


class OrderItemForm(forms.ModelForm):
    """Add items to the order using a form."""

    class Meta:
        """Meta options for a quick design."""

        model = OrderItem
        fields = ('element', 'qty', 'crop', 'sewing', 'iron', 'description')

    def __init__(self, *args, **kwargs):
        """Override the order in the reference dropdown."""
        super(OrderItemForm, self).__init__(*args, **kwargs)
        queryset = Item.objects.exclude(name='Predeterminado').order_by('name')
        self.fields['element'].queryset = queryset


class CommentForm(forms.ModelForm):
    """Add comments using a form."""

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
                  'item', 'item_class', 'activity', 'qty', 'notes')

    def __init__(self, *args, **kwargs):
        """Override the order in the reference dropdown."""
        super(TimeForm, self).__init__(*args, **kwargs)
        self.fields['reference'].label = 'Pedido'
        queryset = Order.objects.order_by('inbox_date')
        self.fields['reference'].queryset = queryset


class EditDateForm(forms.ModelForm):
    """Quick edit order date."""

    class Meta:
        """Meta options for a quick design."""

        model = Order
        fields = ('delivery', )


class OrderCloseForm(forms.ModelForm):
    """Close orders using a form."""

    class Meta:
        """Meta options for a quick design."""

        model = Order
        fields = ('prepaid',)
