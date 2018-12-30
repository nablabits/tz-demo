"""Form models used in the app."""

from django import forms
from .models import Customer, Order, Item, OrderItem, Comment, Invoice
from django.db.models import Count
from django.core.exceptions import ValidationError


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

    def clean(self):
        """Test duplicated for new orders."""
        data = self.cleaned_data
        exists = Order.objects.filter(ref_name=data['ref_name'])
        duplicated = False
        if exists:
            for order in exists:
                duplicated = (data['customer'] == order.customer and
                              data['delivery'] == order.delivery and
                              data['priority'] == order.priority and
                              data['waist'] == order.waist and
                              data['chest'] == order.chest and
                              data['hip'] == order.hip and
                              data['lenght'] == order.lenght and
                              data['others'] == order.others and
                              data['budget'] == order.budget and
                              data['prepaid'] == order.prepaid
                              )
                if duplicated:
                    raise ValidationError('The order already exists in the db')
        return data


class ItemForm(forms.ModelForm):
    """Add new item objects."""

    class Meta:
        """Meta options for a quick design."""

        model = Item
        fields = ('name', 'item_type', 'item_class', 'size', 'fabrics',
                  'notes', 'foreing', 'price', )


class OrderItemForm(forms.ModelForm):
    """Add items to the order using a form."""

    class Meta:
        """Meta options for a quick design."""

        model = OrderItem
        fields = ('element', 'qty', 'crop', 'sewing', 'iron', 'description',
                  'fit', 'stock')

    def __init__(self, *args, **kwargs):
        """Override the order in the reference dropdown."""
        super(OrderItemForm, self).__init__(*args, **kwargs)
        queryset = Item.objects.order_by('item_type')
        self.fields['element'].queryset = queryset


class AddTimesForm(forms.ModelForm):
    """Edit the item times on Pqueue."""

    class Meta:
        """Meta options for a quick design."""

        model = OrderItem
        fields = ('crop', 'sewing', 'iron')


class CommentForm(forms.ModelForm):
    """Add comments using a form."""

    class Meta:
        """Meta options for a quick design."""

        model = Comment
        fields = ('comment', )


class InvoiceForm(forms.ModelForm):
    """Issue invoices using a form."""

    class Meta:
        """Meta options for a quick design."""

        model = Invoice
        fields = ('pay_method', )


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
