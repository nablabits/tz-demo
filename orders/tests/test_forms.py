"""Test the form models."""

from django.test import TestCase
from django.contrib.auth.models import User
from orders.models import Customer, Order, OrderItem, Comment, Item
from orders.forms import (CustomerForm, OrderForm, CommentForm, ItemForm,
                          OrderCloseForm, OrderItemForm, EditDateForm)


class CustomerFormTest(TestCase):
    pass


class OrderFormTest(TestCase):
    pass


class ItemFormTest(TestCase):
    """Test the ItemForm."""

    def setUp(self):
        """Set up the tests."""
        self.form = ItemForm({'name': 'Test Item',
                              'item_type': '1',
                              'item_class': 'S',
                              'size': 10,
                              'fabrics': 10,
                              'notes': 'Notes',
                              'foreing': True})
        self.assertTrue(self.form.is_valid())
        self.form.save()

    def test_avoid_duplicates(self):
        """When trying to save a duplicated form, is_valid() is False."""
        duplicated_form = ItemForm({'name': 'Test Item',
                                    'item_type': '1',
                                    'item_class': 'S',
                                    'size': 10,
                                    'fabrics': 10,
                                    'notes': 'Another Notes',
                                    'foreing': True})
        self.assertFalse(duplicated_form.is_valid())

    def test_items_with_different_fabrics_should_be_accepted(self):
        """Avoid cleaning for edited items."""
        same_fabrics = ItemForm({'name': 'Test Item',
                                 'item_type': '1',
                                 'item_class': 'S',
                                 'size': 10,
                                 'fabrics': 12,
                                 'notes': 'Another Notes',
                                 'foreing': True})
        self.assertTrue(same_fabrics.is_valid())


class OrderItemFormTest(TestCase):
    pass


class CommentFormTest(TestCase):
    pass


class EditDateFormTest(TestCase):
    pass


class OrderCloseForm(TestCase):
    pass
