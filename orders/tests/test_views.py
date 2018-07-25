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
        customer_count = 10
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
            pk = randint(1, 9)  # The first customer should have no order
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

        # Have a read comment
        order = Order.objects.get(ref_name='example closed')
        comment = Comment.objects.filter(reference=order)
        comment = comment.get(comment='Comment0')
        comment.read = True
        comment.comment = 'read comment'
        comment.save()

        # Have a file uploaded
        order = Order.objects.get(ref_name='example closed')
        Document.objects.create(description='Uploaded File',
                                order=order)

    def test_main_view(self):
        """Test the main view."""
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('main'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/main.html')

        # Test context variables
        self.assertEqual(str(resp.context['orders'][0].ref_name), 'example10')
        self.assertEqual(resp.context['orders_count'], 10)
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
        self.assertEqual(str(resp.context['active'][0].ref_name), 'example10')
        self.assertEqual(str(resp.context['user']), 'regular')

    def test_order_list_paginator(self):
        """Test paginator functionality on order list."""
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('orderlist'))

        delivered = resp.context['delivered']
        self.assertFalse(delivered.has_previous())
        self.assertTrue(delivered.has_next())
        self.assertTrue(delivered.has_other_pages())
        self.assertEqual(delivered.number, 1)
        self.assertEqual(len(delivered), 5)
        self.assertEqual(str(delivered[0].ref_name), 'example delivered')

    def test_order_closed_view(self):
        """Test a particular order instance.

        The order tested is a closed order with 10 comments, one of them read,
        5 items and 1 file.
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
        files = resp.context['files']

        self.assertEqual(order.ref_name, 'example closed')
        self.assertEqual(len(comments), 10)
        self.assertEqual(len(items), 5)
        self.assertEqual(len(files), 1)
        self.assertTrue(resp.context['closed'])
        self.assertTrue(comments[9].read)

    def test_customer_list(self):
        """Test the main features on customer list."""
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('customerlist'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/customers.html')

        ctx = resp.context
        self.assertEqual(str(ctx['user']), 'regular')

        # Customers are ordered by order number
        self.assertGreaterEqual(ctx['customers'][0].num_orders,
                                ctx['customers'][1].num_orders)
        self.assertGreaterEqual(ctx['customers'][1].num_orders,
                                ctx['customers'][2].num_orders)
        self.assertGreaterEqual(ctx['customers'][2].num_orders,
                                ctx['customers'][3].num_orders)
        self.assertGreaterEqual(ctx['customers'][3].num_orders,
                                ctx['customers'][4].num_orders)

    def test_customer_list_paginator(self):
        """Test paginator functionality on customer list."""
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get('/customers')

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/customers.html')

        customers = resp.context['customers']
        self.assertFalse(customers.has_previous())
        self.assertTrue(customers.has_next())
        self.assertTrue(customers.has_other_pages())
        self.assertEqual(customers.next_page_number(), 2)
        self.assertEqual(len(customers), 5)

    def test_customer_view(self):
        """Test the customer details view.

        Let the 10 delivered orders be owned by the tested customer who should
        have no previous orders.
        """
        customer = Customer.objects.all()[0]
        no_orders = Order.objects.filter(customer=customer)
        self.assertEqual(len(no_orders), 0)

        orders = Order.objects.filter(status=7)
        for order in orders:
            order.customer = customer
            order.save()

        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('customer_view',
                                       kwargs={'pk': customer.pk}))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/customer_view.html')

        self.assertEqual(len(resp.context['orders_active']), 0)
        self.assertEqual(len(resp.context['orders_delivered']), 10)
        self.assertEqual(len(resp.context['orders_cancelled']), 0)
        self.assertEqual(resp.context['orders_made'], 10)
        self.assertEqual(len(resp.context['pending']), 9)
#
#
#
#
#
#
#
#
#
#
