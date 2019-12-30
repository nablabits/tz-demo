"""Test the form models."""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from orders.forms import CustomerForm, OrderForm
from orders.models import Customer, Order


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
        """Test to avoid duplicates."""
        order = Order.objects.create(user=User.objects.all()[0],
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
        duplicated_order = OrderForm({'customer': order.customer.pk,
                                      'ref_name': order.ref_name,
                                      'delivery': order.delivery,
                                      'waist': order.waist,
                                      'chest': order.chest,
                                      'hip': order.hip,
                                      'priority': order.priority,
                                      'lenght': order.lenght,
                                      'others': order.others,
                                      'budget': order.budget,
                                      'prepaid': order.prepaid,
                                      })

        self.assertFalse(duplicated_order.is_valid())
        self.assertEqual(duplicated_order.errors['__all__'][0],
                         'The order already exists in the db')

    def test_customer_label(self):
        """Test the proper customer label."""
        form = OrderForm()
        self.assertEqual(form.fields['customer'].label, 'Cliente')

    def test_customer_excludes_express(self):
        """Express customer should be excluded from choices."""
        form = OrderForm()
        Customer.objects.create(name='express', phone=5, cp=1,)
        self.assertEqual(len(form.fields['customer'].choices), 2)
        for customer in form.fields['customer'].choices:
            self.assertNotEqual(customer[1], 'express')

    def test_customer_excludes_providers(self):
        """Providers should be excluded from dropdown."""
        form = OrderForm()
        Customer.objects.create(name='Provider', phone=5, cp=1, provider=True)
        self.assertEqual(len(form.fields['customer'].choices), 2)
        for customer in form.fields['customer'].choices:
            self.assertNotEqual(customer[1], 'express')


class OrderItemFormTest(TestCase):
    pass


class CommentFormTest(TestCase):
    pass


class EditDateFormTest(TestCase):
    pass
