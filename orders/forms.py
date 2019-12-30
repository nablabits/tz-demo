"""Form models used in the app."""

from django import forms
from django.core.exceptions import ValidationError

from .models import (Comment, Customer, Invoice, Item, Order, OrderItem,
                     Timetable, CashFlowIO, Expense)


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
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        """Override default settings."""
        super(OrderForm, self).__init__(*args, **kwargs)
        self.fields['customer'].label = 'Cliente'
        queryset = Customer.objects.exclude(name__iexact='express')
        queryset = queryset.exclude(provider=True)
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
        fields = '__all__'

class OrderItemForm(forms.ModelForm):
    """Create new or update order items."""

    class Meta:
        """Define the model and the fields for the form."""

        model = OrderItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        """Override some of the fields defatults."""
        super(OrderItemForm, self).__init__(*args, **kwargs)

        # Set the order for the order dropdown
        queryset = Item.objects.order_by('item_type')
        self.fields['element'].queryset = queryset

        # Filter the results for batch field
        queryset = Order.objects.filter(customer__name__iexact='trapuzarrak')
        self.fields['batch'].queryset = queryset.order_by('pk')


class ItemTimesForm(forms.ModelForm):
    """Edit item times."""

    class Meta:
        """Meta options for a quick design."""

        model = OrderItem
        fields = ('crop', 'sewing', 'iron', )


class OrderItemNotes(forms.ModelForm):
    """Add/edit some notes to already created OrderItems."""

    class Meta:
        """Meta options for a quick design."""

        model = OrderItem
        fields = ('description',)


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


class CashFlowIOForm(forms.ModelForm):
    """Create and update cashflow instances."""

    class Meta:
        """Meta options for a quick design."""

        model = CashFlowIO
        exclude = ['creation', ]

    def __init__(self, *args, **kwargs):
        """Override default settings."""
        super(CashFlowIOForm, self).__init__(*args, **kwargs)
        queryset = Expense.objects.filter(closed=False)
        self.fields['expense'].queryset = queryset
        self.fields['expense'].label = 'Factura'


class EditDateForm(forms.ModelForm):
    """Quick edit order date."""

    class Meta:
        """Meta options for a quick design."""

        model = Order
        fields = ('delivery', )


class TimetableCloseForm(forms.ModelForm):
    """Close an open timetable."""

    class Meta:
        """Meta for quick design."""
        model = Timetable
        fields = ('hours', 'user')
