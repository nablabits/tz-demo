from django.test import TestCase, Client
from django.contrib.auth.models import User
from orders.models import Customer, Order, Document, OrderItem, Comment
from django.urls import reverse, resolve
from datetime import date, timedelta
from random import randint


class NotLoggedInTest(TestCase):
    """Not logged in users should go to a login page."""

    def setUp(self):
        self.client = Client()

    def test_not_logged_in_on_main_view(self):
        login_url = '/accounts/login/?next=/'
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_not_logged_in_on_orders_list_view(self):
        login_url = '/accounts/login/?next=/orders'
        resp = self.client.get(reverse('orderlist'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_not_logged_in_on_order_view(self):
        login_url = '/accounts/login/?next=/order/view/1'
        resp = self.client.get(reverse('order_view', kwargs={'pk': 1}))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_not_logged_in_on_customers_list_view(self):
        login_url = '/accounts/login/?next=/orders'
        resp = self.client.get(reverse('orderlist'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_not_logged_in_on_customer_view(self):
        login_url = '/accounts/login/?next=/customers'
        resp = self.client.get(reverse('customerlist'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)


class StandardViewsTest(TestCase):
    """Test the standard views."""

    def setUp(self):
        """Create the necessary items on database at once.

        Will be created:
            5 Customers
            20 Orders (random customer) where:
                The first 10 are delivered
                first order has:
                    5 items (exact one each other)
                    10 comments (divided in 2 users) & First comment read
                    Is closed
                11th order is cancelled
        """
        # Create users
        regular = User.objects.create_user(username='regular', password='test')
        another = User.objects.create_user(username='another', password='test')
        regular.save()
        another.save()

        # Create some customers
        customer_count = 5
        for customer in range(customer_count):
            Customer.objects.create(name='Customer%s' % customer,
                                    address='This computer',
                                    city='No city',
                                    phone='666666666',
                                    email='customer%s@example.com' % customer,
                                    CIF='5555G',
                                    cp='48100')

        # Create some orders
        orders_count = 20
        for order in range(orders_count):
            pk = randint(0, 4)
            customer = Customer.objects.get(name='Customer%s' % pk)
            delivery = date.today() + timedelta(days=order % 5)
            Order.objects.create(user=regular,
                                 customer=customer,
                                 ref_name='example%s' % order,
                                 delivery=delivery,
                                 waist=randint(10, 50),
                                 chest=randint(10, 50),
                                 hip=randint(10, 50),
                                 lenght=randint(10, 50),
                                 others='Custom notes',
                                 budget=2000,
                                 prepaid=0)

        # Create comments
        comments_count = 10
        for comment in range(comments_count):
            if comment % 2:
                user = regular
            else:
                user = another
            order = Order.objects.get(ref_name='example0')
            Comment.objects.create(user=user,
                                   reference=order,
                                   comment='Comment%s' % comment)

        # Create some items
        items_count = 5
        for item in range(items_count):
            order = Order.objects.get(ref_name='example0')
            OrderItem.objects.create(item=1, size='XL', qty=5,
                                     description='notes',
                                     reference=order)

        # deliver the first 10 orders
        order_bulk_edit = Order.objects.all().order_by('inbox_date')[:10]
        for order in order_bulk_edit:
            order.ref_name = 'example delivered'
            order.status = 7
            order.save()

        # Have a closed order (delivered & paid)
        order = Order.objects.filter(status=7)[0]
        order.ref_name = 'example closed'
        order.prepaid = order.budget
        order.save()

        # Have a cancelled order
        order = Order.objects.get(ref_name='example10')
        order.ref_name = 'example cancelled'
        order.status = 8
        order.save()

        # Have a read comment
        order = Order.objects.get(ref_name='example closed')
        comment = Comment.objects.filter(reference=order)
        comment = comment.get(comment='Comment0')
        comment.read = True
        comment.comment = 'read comment'
        comment.save()

    def test_main_view(self):
        """Test the main view."""
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('main'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/main.html')

        # Test context variables
        self.assertEqual(str(resp.context['orders'][0].ref_name), 'example15')
        self.assertEqual(resp.context['orders_count'], 9)
        self.assertEqual(resp.context['comments_count'], 4)
        self.assertEqual(str(resp.context['comments'][0].comment), 'Comment8')
        self.assertEqual(str(resp.context['user']), 'regular')

    def test_order_list(self):
        """Test the main features on order list."""
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('orderlist'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/orders.html')

        # Test context vars
        self.assertEqual(str(resp.context['active'][0].ref_name), 'example15')
        self.assertEqual(str(resp.context['user']), 'regular')

    def test_order_list_paginator(self):
        """Test paginator functionality on order list."""
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('orderlist'))

        delivered = resp.context['delivered']
        self.assertTrue(delivered.has_previous)
        self.assertTrue(delivered.has_next)
        self.assertEqual(delivered.number, 1)
        self.assertEqual(len(delivered), 5)
        self.assertEqual(str(delivered[0].ref_name), 'example delivered')

    def test_order_closed_view(self):
        """Test a particular order instance.

        The order tested is a closed order with 10 comments one of them read.
        """
        order = Order.objects.get(ref_name='example closed')
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('order_view', kwargs={'pk': order.pk}))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/order_view.html')

        order = resp.context['order']
        comments = resp.context['comments']
        items = resp.context['items']

        self.assertEqual(order.ref_name, 'example closed')
        self.assertEqual(len(comments), 10)
        self.assertEqual(len(items), 5)
        self.assertTrue(resp.context['closed'])
        self.assertTrue(comments[9].read)
