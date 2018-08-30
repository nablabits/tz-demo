"""The main test suite for views. backend."""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from orders.models import Customer, Order, Document, OrderItem, Comment
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.urls import reverse
from datetime import date, timedelta
from random import randint
import json
import io
import os


class NotLoggedInTest(TestCase):
    """Not logged in users should go to a login page.

    On successful login, they're redirected to the view requested.
    """

    def setUp(self):
        """Set up the tests."""
        self.client = Client()

    def test_not_logged_in_on_main_view(self):
        """Test not logged in users should be redirected to login."""
        login_url = '/accounts/login/?next=/'
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_not_logged_in_on_orders_list_view(self):
        """Test not logged in users should be redirected to login."""
        login_url = '/accounts/login/?next=/orders'
        resp = self.client.get(reverse('orderlist'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_not_logged_in_on_order_view(self):
        """Test not logged in users should be redirected to login."""
        login_url = '/accounts/login/?next=/order/view/1'
        resp = self.client.get(reverse('order_view', kwargs={'pk': 1}))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_not_logged_in_on_customers_list_view(self):
        """Test not logged in users should be redirected to login."""
        login_url = '/accounts/login/?next=/orders'
        resp = self.client.get(reverse('orderlist'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_not_logged_in_on_customer_view(self):
        """Test not logged in users should be redirected to login."""
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


class ActionsGetMethod(TestCase):
    """Test the get method on Actions view."""

    @classmethod
    def setUpTestData(cls):
        """Set up some data for the tests.

        We should create a user, a customer, an order, an item and a file to
        play with.
        """
        regular = User.objects.create_user(username='regular', password='test')
        regular.save()

        # Create customer
        Customer.objects.create(name='Customer',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                cp='48100')

        # Create an order
        customer = Customer.objects.get(name='Customer')
        Order.objects.create(user=regular,
                             customer=customer,
                             ref_name='example',
                             delivery=date.today(),
                             waist=randint(10, 50),
                             chest=randint(10, 50),
                             hip=randint(10, 50),
                             lenght=randint(10, 50),
                             others='Custom notes',
                             budget=2000,
                             prepaid=0)

        # Create Item & Document
        order = Order.objects.get(ref_name='example')
        OrderItem.objects.create(item=1, size='XL', qty=5,
                                 description='notes',
                                 reference=order)
        Document.objects.create(description='Uploaded File',
                                order=order)
        cls.client = Client()

    def test_no_pk_raises_error(self):
        """Raise an error when no pk is given.

        Edit and delete actions must have a pk reference (customer or order).
        """
        with self.assertRaisesMessage(ValueError, 'Unexpected GET data'):
            self.client.get(reverse('actions'), {'action': 'order-add'})

    def test_no_action_raises_error(self):
        """Raise an error when no action is given."""
        with self.assertRaisesMessage(ValueError, 'Unexpected GET data'):
            self.client.get(reverse('actions'), {'pk': 5})

    def test_invalid_action_raises_error(self):
        """Raise an error when action doesn't match any condition."""
        with self.assertRaisesMessage(NameError, 'Action was not recogniced'):
            self.client.get(reverse('actions'), {'pk': 5, 'action': 'null'})

    def test_add_order(self):
        """Return code 200 on order-add action."""
        resp = self.client.get(reverse('actions'),
                               {'pk': None, 'action': 'order-add'})
        self.assertEqual(resp.status_code, 200)

    def test_add_order_context(self):
        """Test context dictionaries and template."""
        resp = self.client.get(reverse('actions'),
                               {'pk': None, 'action': 'order-add'})
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/add/add_order.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'form')

    def test_add_customer(self):
        """Return code 200 on customer-add action."""
        resp = self.client.get(reverse('actions'),
                               {'pk': None, 'action': 'customer-add'})
        self.assertEqual(resp.status_code, 200)

    def test_add_customer_context(self):
        """Test context dictionaries and template."""
        resp = self.client.get(reverse('actions'),
                               {'pk': None, 'action': 'customer-add'})
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/add/add_customer.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'form')

    def test_add_order_from_customer_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error.

        Hi numbers are given to avoid db previous entries (though they should
        be deleted).
        """
        resp = self.client.get(reverse('actions'),
                               {'pk': 290, 'action': 'order-from-customer'})
        self.assertEqual(resp.status_code, 404)

    def test_add_order_from_customer(self):
        """Test context dictionaries and template."""
        customer = Customer.objects.get(name='Customer')
        resp = self.client.get(reverse('actions'),
                               {'pk': customer.pk,
                               'action': 'order-from-customer'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/add/add_order.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'form')

    def test_add_item_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 290, 'action': 'order-add-item'})
        self.assertEqual(resp.status_code, 404)

    def test_add_item(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk, 'action': 'order-add-item'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/add/add_item.html')
        self.assertIsInstance(context, list)
        if context[0] == 'order':
            self.assertEqual(context[1], 'form')
        elif context[0] == 'form':
            self.assertEqual(context[1], 'order')
        else:
            self.assertEqual(context[0], 'Not recognized')

    def test_add_comments_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 290, 'action': 'order-add-comment'})
        self.assertEqual(resp.status_code, 404)

    def test_add_comment(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk, 'action': 'order-add-comment'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/add/add_comment.html')
        self.assertIsInstance(context, list)
        if context[0] == 'order':
            self.assertEqual(context[1], 'form')
        elif context[0] == 'form':
            self.assertEqual(context[1], 'order')
        else:
            self.assertEqual(context[0], 'Not recognized')

    def test_add_file_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'order-add-file'})
        self.assertEqual(resp.status_code, 404)

    def test_add_file(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk, 'action': 'order-add-file'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/add/add_file.html')
        self.assertIsInstance(context, list)
        if context[0] == 'order':
            self.assertEqual(context[1], 'form')
        elif context[0] == 'form':
            self.assertEqual(context[1], 'order')
        else:
            self.assertEqual(context[0], 'Not recognized')

    def test_edit_order_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'order-edit'})
        self.assertEqual(resp.status_code, 404)

    def test_edit_order(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk, 'action': 'order-edit'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/edit/edit_order.html')
        self.assertIsInstance(context, list)
        if context[0] == 'order':
            self.assertEqual(context[1], 'form')
        elif context[0] == 'form':
            self.assertEqual(context[1], 'order')
        else:
            self.assertEqual(context[0], 'Not recognized')

    def test_edit_order_date_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'order-edit-date'})
        self.assertEqual(resp.status_code, 404)

    def test_edit_order_date(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk, 'action': 'order-edit-date'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/edit/edit_date.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'order')

    def test_edit_customer_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'customer-edit'})
        self.assertEqual(resp.status_code, 404)

    def test_edit_customer(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        customer = Customer.objects.get(name='Customer')
        resp = self.client.get(reverse('actions'),
                               {'pk': customer.pk, 'action': 'customer-edit'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/edit/edit_customer.html')
        self.assertIsInstance(context, list)
        if context[0] == 'customer':
            self.assertEqual(context[1], 'form')
        elif context[0] == 'form':
            self.assertEqual(context[1], 'customer')
        else:
            self.assertEqual(context[0], 'Not recognized')

    def test_collect_order_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'order-pay-now'})
        self.assertEqual(resp.status_code, 404)

    def test_collect_order(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk, 'action': 'order-pay-now'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/edit/pay_order.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'order')

    def test_close_order_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'order-close'})
        self.assertEqual(resp.status_code, 404)

    def test_close_order(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk, 'action': 'order-close'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/edit/close_order.html')
        self.assertIsInstance(context, list)
        if context[0] == 'order':
            self.assertEqual(context[1], 'form')
        elif context[0] == 'form':
            self.assertEqual(context[1], 'order')
        else:
            self.assertEqual(context[0], 'Not recognized')

    def test_edit_item_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'order-edit-item'})
        self.assertEqual(resp.status_code, 404)

    def test_edit_item(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        item = OrderItem.objects.get(reference=order)
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk, 'action': 'order-edit-item'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/edit/edit_item.html')
        self.assertIsInstance(context, list)
        if context[0] == 'form':
            self.assertEqual(context[1], 'item')
        elif context[0] == 'item':
            self.assertEqual(context[1], 'form')
        else:
            self.assertEqual(context[0], 'Not recognized')

    def test_delete_item_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'order-delete-item'})
        self.assertEqual(resp.status_code, 404)

    def test_delete_item(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        item = OrderItem.objects.get(reference=order)
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk, 'action': 'order-delete-item'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/delete/delete_item.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'item')

    def test_delete_file_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'order-delete-file'})
        self.assertEqual(resp.status_code, 404)

    def test_delete_file(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        file = Document.objects.get(order=order)
        resp = self.client.get(reverse('actions'),
                               {'pk': file.pk, 'action': 'order-delete-file'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/delete/delete_file.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'file')

    def test_delete_customer_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200, 'action': 'customer-delete'})
        self.assertEqual(resp.status_code, 404)

    def test_delete_customer(self):
        """Test context dictionaries and template."""
        customer = Customer.objects.get(name='Customer')
        resp = self.client.get(reverse('actions'),
                               {'pk': customer.pk,
                               'action': 'customer-delete'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/delete/delete_customer.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'customer')

    def test_logout(self):
        """Test context dictionaries and template."""
        resp = self.client.get(reverse('actions'),
                               {'pk': None, 'action': 'logout'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'registration/logout.html')
        self.assertIsInstance(context, list)
        self.assertEqual(len(context), 0)


class ActionsPostMethodRaises(TestCase):
    """Test the correct raise of errors in post method."""

    def test_no_pk_raises_error(self):
        """Raise an error when no pk is given."""
        with self.assertRaisesMessage(ValueError, 'POST data was poor'):
            self.client.post(reverse('actions'), {'action': 'order-add'})

    def test_no_action_raises_error(self):
        """Raise an error when no action is given."""
        with self.assertRaisesMessage(ValueError, 'POST data was poor'):
            self.client.post(reverse('actions'), {'pk': 5})

    def test_invalid_action_raises_error(self):
        """Raise an error when action doesn't match any condition."""
        with self.assertRaisesMessage(NameError, 'Action was not recogniced'):
            self.client.post(reverse('actions'), {'pk': 5, 'action': 'null'})


class ActionsPostMethodCreate(TestCase):
    """Test the post method on Actions view to add new elements."""

    def setUp(self):
        """Set up some data for the tests.

        We should create a user, a customer and an order to play with.
        """
        regular = User.objects.create_user(username='regular', password='test')
        regular.save()

        # Create customer
        Customer.objects.create(name='Customer',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                cp='48100')

        # Create order
        customer = Customer.objects.get(name='Customer')
        Order.objects.create(user=regular,
                             customer=customer,
                             ref_name='example',
                             delivery=date.today(),
                             waist=randint(10, 50),
                             chest=randint(10, 50),
                             hip=randint(10, 50),
                             lenght=randint(10, 50),
                             others='Custom notes',
                             budget=2000,
                             prepaid=0)

        # Load client
        self.client = Client()

        # Log the user in
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')

    def context_vars(self, context, vars):
        """Compare the given vars with the ones in response."""
        context_is_valid = 0
        for item in context:
            for var in vars:
                if item == var:
                    context_is_valid += 1
        if context_is_valid == len(vars):
            return True
        else:
            return False

    def test_order_new_adds_an_order(self):
        """Test new order creation."""
        customer = Customer.objects.get(name='Customer')
        self.client.post(reverse('actions'), {'customer': customer.pk,
                                              'ref_name': 'created',
                                              'delivery': date.today(),
                                              'waist': '1',
                                              'chest': '2',
                                              'hip': '3.4',
                                              'lenght': 5,
                                              'others': 'None',
                                              'budget': '1000',
                                              'prepaid': '100',
                                              'pk': 'None',
                                              'action': 'order-new'
                                              })
        self.assertTrue(Order.objects.get(ref_name='created'))

    def test_order_new_redirects_to_order_page(self):
        """Test redirection to recently created order."""
        customer = Customer.objects.get(name='Customer')
        resp = self.client.post(reverse('actions'),
                                {'customer': customer.pk,
                                 'ref_name': 'created',
                                 'delivery': date.today(),
                                 'waist': '1',
                                 'chest': '2',
                                 'hip': '3.4',
                                 'lenght': 5,
                                 'others': 'None',
                                 'budget': '1000',
                                 'prepaid': '100',
                                 'pk': 'None',
                                 'action': 'order-new'
                                 })

        order_created = Order.objects.get(ref_name='created')
        url = '/order/view/%s' % order_created.pk
        self.assertRedirects(resp, url)

    def test_invalid_order_new_returns_to_form_again(self):
        """When form is not valid JsonResponse should be sent again."""
        customer = Customer.objects.get(name='Customer')

        # hip field is missing
        resp = self.client.post(reverse('actions'),
                                {'customer': customer.pk,
                                 'ref_name': 'created',
                                 'delivery': date.today(),
                                 'waist': '1',
                                 'chest': '2',
                                 'invalid-hip-field': '2.2',
                                 'lenght': 5,
                                 'others': 'None',
                                 'budget': '1000',
                                 'prepaid': '100',
                                 'pk': 'None',
                                 'action': 'order-new'
                                 })

        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/add/add_order.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'form')

    def test_customer_new_adds_customer(self):
        """Test new customer creation."""
        self.client.post(reverse('actions'), {'name': 'New Customer',
                                              'address': 'example address',
                                              'city': 'Mungia',
                                              'phone': '123456789',
                                              'email': 'johndoe@example.com',
                                              'CIF': '123456789F',
                                              'cp': '12345',
                                              'pk': None,
                                              'action': 'customer-new'
                                              })
        self.assertTrue(Customer.objects.get(name='New Customer'))

    def test_customer_new_redirects_to_customer_page(self):
        """Test redirection to recently created customer."""
        resp = self.client.post(reverse('actions'),
                                {'name': 'New Customer',
                                 'address': 'example address',
                                 'city': 'Mungia',
                                 'phone': '123456789',
                                 'email': 'johndoe@example.com',
                                 'CIF': '123456789F',
                                 'cp': '12345',
                                 'pk': None,
                                 'action': 'customer-new'
                                 })
        customer_created = Customer.objects.get(name='New Customer')
        url = '/customer_view/%s' % customer_created.pk
        self.assertRedirects(resp, url)

    def test_invalid_customer_new_returns_to_form_again(self):
        """When form is not valid JsonResponse should be sent again."""
        resp = self.client.post(reverse('actions'),
                                {'name': 'New Customer',
                                 'address': 'example address',
                                 'city': 'Mungia',
                                 'invalid-phone-field-name': '123456789',
                                 'email': 'johndoe@example.com',
                                 'CIF': '123456789F',
                                 'cp': '12345',
                                 'pk': None,
                                 'action': 'customer-new'
                                 })
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/add/add_customer.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'form')

    def test_pk_out_of_range_raises_404(self):
        """Raises a 404 when pk is out of index."""
        actions = ('order-comment',
                   'comment-read',
                   'order-add-item',
                   'order-add-file',
                   'order-edit',
                   'order-edit-date',
                   'order-edit-item',
                   'order-pay-now',
                   'order-close',
                   'update-status',
                   'customer-edit',
                   'order-delete-item',
                   'order-delete-file',
                   'customer-delete'
                   )
        for action in actions:
            resp = self.client.post(reverse('actions'),
                                    {'pk': 2000, 'action': action})
            self.assertEqual(resp.status_code, 404)

    def test_comment_adds_comment(self):
        """Test the proper insertion of comments."""
        order = Order.objects.get(ref_name='example')
        self.client.post(reverse('actions'), {'action': 'order-comment',
                                              'pk': order.pk,
                                              'comment': 'Entered comment'})
        comment = Comment.objects.get(comment='Entered comment')
        user = User.objects.get(username='regular')
        self.assertTrue(comment)
        self.assertEqual(comment.reference, order)
        self.assertEqual(comment.user, user)

    def test_comment_add_context_response(self):
        """Test the content of the response."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'action': 'order-comment',
                                 'pk': order.pk,
                                 'comment': 'Entered comment'})

        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/comment_list.html')
        self.assertIsInstance(context, list)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['html_id'], '#comment-list')
        vars = ('comments', 'form')
        context_is_valid = self.context_vars(context, vars)
        self.assertTrue(context_is_valid)

    def test_comment_add_invalid_form_returns_to_form_again(self):
        """Not valid forms should return to the form again."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'action': 'order-comment',
                                 'pk': order.pk})
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/add/add_comment.html')
        self.assertIsInstance(context, list)
        if context[0] == 'order':
            self.assertEqual(context[1], 'form')
        if context[0] == 'form':
            self.assertEqual(context[1], 'order')

    def test_mark_comment_as_read_returns_to_main(self):
        """Mark comments as read should redirect to main view."""
        order = Order.objects.get(ref_name='example')
        self.client.post(reverse('actions'), {'action': 'order-comment',
                                              'pk': order.pk,
                                              'comment': 'Entered comment'})
        comment = Comment.objects.get(comment='Entered comment')
        resp = self.client.post(reverse('actions'), {'action': 'comment-read',
                                                     'pk': comment.pk})
        read_comment = Comment.objects.get(comment='Entered comment')
        url = '/'
        self.assertTrue(read_comment.read)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, url)

    def test_item_add_adds_item(self):
        """Test the proper insertion of items."""
        order = Order.objects.get(ref_name='example')
        self.client.post(reverse('actions'),
                         {'action': 'order-add-item',
                          'pk': order.pk,
                          'item': '1',
                          'size': 'xs',
                          'qty': 2,
                          'description': 'added item'
                          })
        item = OrderItem.objects.get(description='added item')
        self.assertTrue(item)
        self.assertEqual(item.reference, order)

    def test_item_add_context_response(self):
        """Test the response given by add item."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'action': 'order-add-item',
                                 'pk': order.pk,
                                 'item': '1',
                                 'size': 'xs',
                                 'qty': 2,
                                 'description': 'added item'
                                 })
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/order_details.html')
        self.assertIsInstance(context, list)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['html_id'], '#order-details')
        vars = ('form', 'order', 'items')
        context_is_valid = self.context_vars(context, vars)
        self.assertTrue(context_is_valid)

    def test_item_add_invalid_form_returns_to_form_again(self):
        """Test item add invalid form behaviour."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'action': 'order-add-item',
                                 'pk': order.pk,
                                 'item': '1',
                                 'size': 'xs',
                                 'qty': 2.5,
                                 'description': 'invalid item'
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/add/add_item.html')
        self.assertIsInstance(context, list)
        vars = ('form', 'order')
        context_is_valid = self.context_vars(context, vars)
        self.assertTrue(context_is_valid)

    def test_add_file_adds_a_file(self):
        """Test the proper file creation."""
        order = Order.objects.get(ref_name='example')
        test_file = io.StringIO('Example text')
        self.client.post(reverse('actions'),
                         {'action': 'order-add-file',
                          'pk': order.pk,
                          'description': 'New file',
                          'document': test_file})
        # Get rid of the temp file
        document = Document.objects.get(description='New file')
        os.remove('media/' + str(document.document))

        self.assertTrue(document)
        self.assertEqual(document.order, order)

    def test_add_files_redirects_to_order_view(self):
        """Test the response given by add file."""
        order = Order.objects.get(ref_name='example')
        test_file = io.StringIO('Example text')
        resp = self.client.post(reverse('actions'),
                                {'action': 'order-add-file',
                                 'pk': order.pk,
                                 'description': 'New file',
                                 'document': test_file})
        # Get rid of the temp file
        document = Document.objects.get(description='New file')
        os.remove('media/' + str(document.document))
        # Now try the redirect
        url = '/order/view/%s' % order.pk
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, url)

    def test_add_files_invalid_form_returns_to_form_again(self):
        """Test file add invalid form behaviour."""
        order = Order.objects.get(ref_name='example')

        # Missing file, so should be not valid
        resp = self.client.post(reverse('actions'),
                                {'action': 'order-add-file',
                                 'pk': order.pk,
                                 'description': 'New file'})

        # Now try the behaviour
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/add/add_file.html')
        self.assertIsInstance(context, list)
        vars = ('form', 'order')
        context_is_valid = self.context_vars(context, vars)
        self.assertTrue(context_is_valid)


class ActionsPostMethodEdit(TestCase):
    """Test the post method on Actions view to add new elements."""

    def setUp(self):
        """Set up some data for the tests.

        We should create a user, a customer, an order, a comment, an item and a
        file to play with.
        """
        regular = User.objects.create_user(username='regular', password='test')
        regular.save()

        # Create customer
        Customer.objects.create(name='Customer',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                cp='48100')

        # Create order
        customer = Customer.objects.get(name='Customer')
        Order.objects.create(user=regular,
                             customer=customer,
                             ref_name='example',
                             delivery=date.today(),
                             waist=randint(10, 50),
                             chest=randint(10, 50),
                             hip=randint(10, 50),
                             lenght=randint(10, 50),
                             others='Custom notes',
                             budget=2000,
                             prepaid=0)

        # Load client
        self.client = Client()

    def context_vars(self, context, vars):
        """Compare the given vars with the ones in response."""
        context_is_valid = 0
        for item in context:
            for var in vars:
                if item == var:
                    context_is_valid += 1
        if context_is_valid == len(vars):
            return True
        else:
            return False

    def test_edit_order_edits_the_order(self):
        """Test the correct edition for fields."""
        order = Order.objects.get(ref_name='example')
        customer = Customer.objects.get(name='Customer')
        resp = self.client.post(reverse('actions'),
                                {'ref_name': 'modified',
                                 'customer': customer.pk,
                                 'delivery': date(2017, 1, 1),
                                 'waist': '1',
                                 'chest': '2',
                                 'hip': '3',
                                 'lenght': 5,
                                 'others': 'None',
                                 'budget': '1000',
                                 'prepaid': '100',
                                 'pk': order.pk,
                                 'action': 'order-edit'
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertTrue(data['reload'])

        # Test if the fields were modified
        mod_order = Order.objects.get(pk=order.pk)
        self.assertEqual(mod_order.ref_name, 'modified')
        self.assertEqual(str(mod_order.delivery), '2017-01-01')
        self.assertEqual(mod_order.waist, 1)
        self.assertEqual(mod_order.chest, 2)
        self.assertEqual(mod_order.hip, 3)
        self.assertEqual(mod_order.lenght, 5)
        self.assertEqual(mod_order.others, 'None')
        self.assertEqual(mod_order.budget, 1000)
        self.assertEqual(mod_order.prepaid, 100)

    def test_edit_order_not_valid_returns_to_form(self):
        """Test rejected edit order forms."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'ref_name': 'modified',
                                 'customer': 'wrong customer',
                                 'delivery': date(2017, 1, 1),
                                 'waist': '1',
                                 'chest': '2',
                                 'hip': '3',
                                 'lenght': 5,
                                 'others': 'None',
                                 'budget': '1000',
                                 'prepaid': '100',
                                 'pk': order.pk,
                                 'action': 'order-edit'
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['context'][0], 'form')
        self.assertEqual(data['template'], 'includes/add/add_order.html')

    def test_edit_date_successful(self):
        """Test the correct quick-edit date."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'delivery': date(2017, 1, 1),
                                 'pk': order.pk,
                                 'action': 'order-edit-date'
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertTrue(data['reload'])

    def test_edit_date_returns_false_with_invalid_dates_objs(self):
        """No datetime objects should return false to form_is_valid."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'delivery': 'invalid data',
                                 'pk': order.pk,
                                 'action': 'order-edit-date'
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])

    def text_edit_date_raises_error(self):
        """Invalid dates should raise an exception."""
        order = Order.objects.get(ref_name='example')
        with self.assertRaises(ValidationError):
            self.client.post(reverse('actions'),
                             {'delivery': 'invalid data',
                              'pk': order.pk,
                              'action': 'order-edit-date'
                              })

    def test_edit_customer_edits_customer(self):
        """Test the correct edition for fields."""
        customer = Customer.objects.get(name='Customer')
        resp = self.client.post(reverse('actions'),
                                {'name': 'modified Customer',
                                 'address': 'Another computer',
                                 'city': 'Mod city',
                                 'phone': 5555,
                                 'email': 'modified@example.com',
                                 'CIF': '4444E',
                                 'cp': 48200,
                                 'pk': customer.pk,
                                 'action': 'customer-edit'
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertTrue(data['reload'])

        # Test if the fields were modified
        mod_customer = Customer.objects.get(pk=customer.pk)
        self.assertEqual(mod_customer.name, 'modified Customer')
        self.assertEqual(mod_customer.address, 'Another computer')
        self.assertEqual(mod_customer.city, 'Mod city')
        self.assertEqual(mod_customer.phone, 5555)
        self.assertEqual(mod_customer.email, 'modified@example.com')
        self.assertEqual(mod_customer.CIF, '4444E')
        self.assertEqual(mod_customer.cp, 48200)

    def test_edit_customer_invalid_returns_to_form(self):
        """Test when forms are rejected."""
        customer = Customer.objects.get(name='Customer')
        resp = self.client.post(reverse('actions'),
                                {'phone': 'invalid phone',
                                 'pk': customer.pk,
                                 'action': 'customer-edit'
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/edit/edit_customer.html')
        vars = ('customer', 'form')
        self.assertTrue(self.context_vars(data['context'], vars))

#
#
#
#
