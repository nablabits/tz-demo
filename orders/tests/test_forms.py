"""Test the form models."""

from django.test import TestCase
from django.contrib.auth.models import User
from orders.models import Customer, Order, OrderItem, Comment, Item
from orders.forms import (CustomerForm, OrderForm, CommentForm, ItemForm,
                          OrderCloseForm, OrderItemForm, EditDateForm)
from datetime import date


class CustomerFormTest(TestCase):
    """Test the customer form."""

    def test_avoid_duplicates(self):
        """Test to prevent duplicates."""
        Customer.objects.create(name='Test duplicate',
                                city='mungia',
                                address='Foruen enparantza',
                                phone='666555444',
                                email='jondoe@jondoe.com',
                                CIF='0000T',
                                cp='00000',
                                notes='No notes',
                                )
        duplicated_customer = CustomerForm({'name': 'Test duplicate',
                                            'city': 'mungia',
                                            'address': 'Foruen enparantza',
                                            'phone': '666555444',
                                            'email': 'jondoe@jondoe.com',
                                            'CIF': '0000T',
                                            'cp': '00000',
                                            'notes': 'No notes',
                                            })
        self.assertFalse(duplicated_customer.is_valid())
        self.assertEqual(duplicated_customer.errors['name'][0],
                         'The customer already exists in the db')


class OrderFormTest(TestCase):
    """Test the order form."""

    def setUp(self):
        """Set some settings up."""
        User.objects.create_user(username='regular', password='test')
        Customer.objects.create(name='Test duplicate',
                                city='mungia',
                                phone='666555444',
                                cp='00000',
                                )

    def test_avoid_duplicates(self):
        Order.objects.create(user=User.objects.all()[0],
                             customer=Customer.objects.all()[0],
                             ref_name='Duplicate test',
                             delivery=date(2018, 1, 1),
                             priority='2',
                             waist=10,
                             chest=20,
                             hip=30,
                             lenght=40,
                             others='Duplicate order',
                             budget=100,
                             prepaid=100,
                             )
        self.assertTrue(Order.objects.get(ref_name='Duplicate test'))
        duplicated_order = OrderForm({'customer': Customer.objects.all()[0].pk,
                                      'ref_name': 'Duplicate test',
                                      'delivery': date(2018, 1, 1),
                                      'priority': '2',
                                      'waist': 10,
                                      'chest': 20,
                                      'hip': 30,
                                      'lenght': 40,
                                      'others': 'Duplicate order',
                                      'budget': 100,
                                      'prepaid': 100,
                                      })

        not_valid = duplicated_order.is_valid()
        self.assertFalse(not_valid)
        self.assertEqual(duplicated_order.errors['__all__'][0],
                         'The order already exists in the db')


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
        not_valid = duplicated_form.is_valid()
        self.assertFalse(not_valid)
        self.assertEqual(duplicated_form.errors['name'][0],
                         'Items cannot have the same name the same size and ' +
                         'the same class')

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
