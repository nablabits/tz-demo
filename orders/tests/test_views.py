from django.test import TestCase, Client
from django.contrib.auth.models import User
from orders.models import Customer, Order, Document, OrderItem, Comment
from django.urls import reverse, resolve
from datetime import date


class ViewTest(TestCase):
    """Test the views."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create users
        User.objects.create_user(username='regular', password='test')
        User.objects.create_user(username='another', password='test')

        # Create a customer
        Customer.objects.create(name='Customer Test',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                cp='48100')

        # Create an outdated and unpaid order
        Order.objects.create(user=User.objects.get(pk=1),
                             customer=Customer.objects.get(pk=1),
                             ref_name='example',
                             delivery=date(2018, 2, 1),
                             waist=10,
                             chest=20,
                             hip=30,
                             lenght=40,
                             others='Custom notes',
                             budget=2000,
                             prepaid=1000,
                             workshop=120)

        # Create a delivered and unpaid order
        Order.objects.create(user=User.objects.get(pk=1),
                             customer=Customer.objects.get(pk=1),
                             status=7,
                             ref_name='example delivered',
                             delivery=date(2018, 7, 1),
                             waist=10,
                             chest=20,
                             hip=30,
                             lenght=40,
                             others='Custom notes',
                             budget=2000,
                             prepaid=1000,
                             workshop=120)

        # Create a cancelled order
        Order.objects.create(user=User.objects.get(pk=1),
                             customer=Customer.objects.get(pk=1),
                             status=8,
                             ref_name='example cancelled',
                             delivery=date(2018, 7, 1),
                             waist=10,
                             chest=20,
                             hip=30,
                             lenght=40,
                             others='Custom notes',
                             budget=2000,
                             prepaid=1000,
                             workshop=120)

        # Create comments
        Comment.objects.create(user=User.objects.get(pk=1),
                               reference=Order.objects.get(pk=1),
                               comment='This is a comment')
        Comment.objects.create(user=User.objects.get(pk=2),
                               reference=Order.objects.get(pk=1),
                               comment='another')

    def test_main_view(self):
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('main'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/main.html')

        # Test context variables
        self.assertEqual(str(resp.context['orders'][0].ref_name), 'example')
        self.assertEqual(str(resp.context['orders_count']), '1')
        self.assertEqual(str(resp.context['comments_count']), '1')
        self.assertEqual(str(resp.context['comments'][0].comment), 'another')
        self.assertEqual(str(resp.context['user']), 'regular')
