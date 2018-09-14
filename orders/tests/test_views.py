"""The main test suite for views. backend."""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from orders.models import Customer, Order, OrderItem, Comment, Timing
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import JsonResponse
from django.urls import reverse
from datetime import date, timedelta
from random import randint
import json


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

        # Now login to avoid the 404
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')

    def test_main_view(self):
        """Test the main view."""
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
        resp = self.client.get(reverse('orderlist'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/orders.html')

        # Test context vars
        self.assertEqual(str(resp.context['active'][0].ref_name), 'example10')
        self.assertEqual(str(resp.context['user']), 'regular')

    def test_order_list_paginator(self):
        """Test paginator functionality on order list."""
        resp = self.client.get(reverse('orderlist'))

        delivered = resp.context['delivered']
        self.assertFalse(delivered.has_previous())
        self.assertTrue(delivered.has_next())
        self.assertTrue(delivered.has_other_pages())
        self.assertEqual(delivered.number, 1)
        self.assertEqual(len(delivered), 5)
        self.assertEqual(str(delivered[0].ref_name), 'example delivered')

    def test_order_list_paginator_not_an_int_exception(self):
        """When page is not an int, paginator should go to the first one.

        That is because the exception was catch.
        """
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('orderlist'), {'page': 'invalid'})

        delivered = resp.context['delivered']
        self.assertFalse(delivered.has_previous())
        self.assertTrue(delivered.has_next())
        self.assertTrue(delivered.has_other_pages())
        self.assertEqual(delivered.number, 1)

    def test_order_list_paginator_empty_exception(self):
        """When page given is empty, paginator should go to the last one.

        That is because the exception was catch.
        """
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('orderlist'), {'page': 20})

        delivered = resp.context['delivered']
        self.assertEqual(delivered.number, 2)
        self.assertTrue(delivered.has_previous())
        self.assertFalse(delivered.has_next())
        self.assertTrue(delivered.has_other_pages())
        self.assertEqual(len(delivered), 5)

    def test_order_closed_view(self):
        """Test a particular order instance.

        The order tested is a closed order with 10 comments, one of them read,
        5 items and 1 file.
        """
        order = Order.objects.get(ref_name='example closed')
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

    def test_customer_list(self):
        """Test the main features on customer list."""
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
        resp = self.client.get('/customers')

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/customers.html')

        customers = resp.context['customers']
        self.assertFalse(customers.has_previous())
        self.assertTrue(customers.has_next())
        self.assertTrue(customers.has_other_pages())
        self.assertEqual(customers.next_page_number(), 2)
        self.assertEqual(len(customers), 5)

    def test_customer_paginator_not_an_int_exception(self):
        """When page is not an int, paginator should go to the first one.

        That is because the exception was catch.
        """
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('customerlist'), {'page': 'invalid'})

        customers = resp.context['customers']
        self.assertFalse(customers.has_previous())
        self.assertTrue(customers.has_next())
        self.assertTrue(customers.has_other_pages())
        self.assertEqual(customers.number, 1)

    def test_customer_paginator_empty_exception(self):
        """When page given is empty, paginator should go to the last one.

        That is because the exception was catch.
        """
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('customerlist'), {'page': 20})

        customers = resp.context['customers']
        self.assertEqual(customers.number, 2)
        self.assertTrue(customers.has_previous())
        self.assertFalse(customers.has_next())
        self.assertTrue(customers.has_other_pages())
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


class SearchBoxTest(TestCase):
    """Test the standard views."""

    @classmethod
    def setUpTestData(cls):
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
                                    phone='66666666%s' % customer,
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

    def test_search_box_invalid_method(self):
        """Search must be POST method."""
        with self.assertRaises(TypeError):
            self.client.get(reverse('search'))

    def test_search_box_empty_string_returns_404(self):
        """Trying to search empty string should return 404."""
        resp = self.client.post(reverse('search'),
                                {'search-on': 'orders',
                                 'search-obj': ''})
        self.assertEqual(resp.status_code, 404)

    def test_search_box_invalid_search_on(self):
        """Search_on fields should be either orders or customers."""
        with self.assertRaises(ValueError):
            self.client.post(reverse('search'), {'search-on': 'invalid',
                                                 'search-obj': 'string'})

        with self.assertRaises(ValueError):
            self.client.post(reverse('search'), {'search-on': None,
                                                 'search-obj': 'string'})

    def test_search_box_on_orders(self):
        """Test search orders."""
        resp = self.client.post(reverse('search'),
                                {'search-on': 'orders',
                                 'search-obj': 'example11',
                                 'test': True})
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('query_result', 'model')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertEquals(data['template'], 'includes/search_results.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertEquals(data['model'], 'orders')
        self.assertEquals(data['query_result'], 1)
        self.assertEquals(data['query_result_name'], 'example11')

    def test_search_box_on_customers_str(self):
        """Test search customers by name."""
        resp = self.client.post(reverse('search'),
                                {'search-on': 'customers',
                                 'search-obj': 'Customer1',
                                 'test': True})
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('query_result', 'model')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertEquals(data['template'], 'includes/search_results.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertEquals(data['model'], 'customers')
        self.assertEquals(data['query_result'], 1)
        self.assertEquals(data['query_result_name'], 'Customer1')

    def test_search_box_on_customers_int(self):
        """Test search customers by phone."""
        resp = self.client.post(reverse('search'),
                                {'search-on': 'customers',
                                 'search-obj': 666666665,
                                 'test': True})
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('query_result', 'model')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertEquals(data['template'], 'includes/search_results.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertEquals(data['model'], 'customers')
        self.assertEquals(data['query_result'], 1)
        self.assertEquals(data['query_result_name'], 'Customer5')

    def test_search_box_case_insensitive(self):
        """Search should return the same resuslts regardless the case."""
        resp1 = self.client.post(reverse('search'),
                                 {'search-on': 'orders',
                                  'search-obj': 'example11',
                                  'test': True})
        resp2 = self.client.post(reverse('search'),
                                 {'search-on': 'orders',
                                  'search-obj': 'exaMple11',
                                  'test': True})
        data1 = json.loads(str(resp1.content, 'utf-8'))
        data2 = json.loads(str(resp2.content, 'utf-8'))
        self.assertEquals(data1['query_result_name'],
                          data2['query_result_name'])


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
        cls.client = Client()

    def test_no_pk_raises_error(self):
        """Raise an error when no pk is given.

        Edit and delete actions must have a pk reference (customer or order).
        """
        with self.assertRaisesMessage(ValueError, 'Unexpected GET data'):
            self.client.get(reverse('actions'), {'action': 'order-add',
                                                 'test': True})

    def test_no_action_raises_error(self):
        """Raise an error when no action is given."""
        with self.assertRaisesMessage(ValueError, 'Unexpected GET data'):
            self.client.get(reverse('actions'), {'pk': 5, 'test': True})

    def test_invalid_action_raises_error(self):
        """Raise an error when action doesn't match any condition."""
        with self.assertRaisesMessage(NameError, 'Action was not recogniced'):
            self.client.get(reverse('actions'), {'pk': 5,
                                                 'action': 'null',
                                                 'test': True})

    def test_add_order(self):
        """Return code 200 on order-add action."""
        resp = self.client.get(reverse('actions'), {'pk': None,
                                                    'action': 'order-add',
                                                    'test': True})
        self.assertEqual(resp.status_code, 200)

    def test_add_order_context(self):
        """Test context dictionaries and template."""
        resp = self.client.get(reverse('actions'), {'pk': None,
                                                    'action': 'order-add',
                                                    'test': True})
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/add/add_order.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'form')

    def test_add_customer(self):
        """Return code 200 on customer-add action."""
        resp = self.client.get(reverse('actions'), {'pk': None,
                                                    'action': 'customer-add',
                                                    'test': True})
        self.assertEqual(resp.status_code, 200)

    def test_add_customer_context(self):
        """Test context dictionaries and template."""
        resp = self.client.get(reverse('actions'), {'pk': None,
                                                    'action': 'customer-add',
                                                    'test': True})
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
                               {'pk': 290,
                                'action': 'order-from-customer',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_add_order_from_customer(self):
        """Test context dictionaries and template."""
        customer = Customer.objects.get(name='Customer')
        resp = self.client.get(reverse('actions'),
                               {'pk': customer.pk,
                                'action': 'order-from-customer',
                                'test': True})
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
                               {'pk': 290,
                                'action': 'order-add-item',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_add_item(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk,
                                'action': 'order-add-item',
                                'test': True})
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
                               {'pk': 290,
                                'action': 'order-add-comment',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_add_comment(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk,
                                'action': 'order-add-comment',
                                'test': True})
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

    def test_add_time(self):
        """Test add time button click response."""
        resp = self.client.get(reverse('actions'),
                               {'pk': None,
                                'action': 'time-add',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/add/add_time.html')
        self.assertEqual(context[0], 'form')

    def test_edit_order_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200,
                                'action': 'order-edit',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_edit_order(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk,
                                'action': 'order-edit',
                                'test': True})
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
                               {'pk': 200,
                                'action': 'order-edit-date',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_edit_order_date(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk,
                                'action': 'order-edit-date',
                                'test': True})
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
                               {'pk': 200,
                                'action': 'customer-edit',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_edit_customer(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        customer = Customer.objects.get(name='Customer')
        resp = self.client.get(reverse('actions'),
                               {'pk': customer.pk,
                                'action': 'customer-edit',
                                'test': True})
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
                               {'pk': 200,
                                'action': 'order-pay-now',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_collect_order(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk,
                                'action': 'order-pay-now',
                                'test': True})
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
                               {'pk': 200,
                                'action': 'order-close',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_close_order(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk,
                                'action': 'order-close',
                                'test': True})
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
                               {'pk': 200,
                                'action': 'order-edit-item',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_edit_item(self):
        """Test context dictionaries and template.

        The index for the context items seems to be a bit random (why?).
        """
        order = Order.objects.get(ref_name='example')
        item = OrderItem.objects.get(reference=order)
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'order-edit-item',
                                'test': True})
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
                               {'pk': 200,
                                'action': 'order-delete-item',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_delete_item(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        item = OrderItem.objects.get(reference=order)
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'order-delete-item',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/delete/delete_item.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'item')

    def test_delete_customer_returns_404_with_pk_out_of_range(self):
        """Out of range indexes should return a 404 error."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 200,
                                'action': 'customer-delete',
                                'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_delete_customer(self):
        """Test context dictionaries and template."""
        customer = Customer.objects.get(name='Customer')
        resp = self.client.get(reverse('actions'),
                               {'pk': customer.pk,
                                'action': 'customer-delete',
                                'test': True})
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
                               {'pk': None, 'action': 'logout', 'test': True})
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
                                              'action': 'order-new',
                                              'test': True
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
                                 'action': 'order-new',
                                 'test': True
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
                                 'action': 'order-new',
                                 'test': True
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
                                              'action': 'customer-new',
                                              'test': True
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
                                 'action': 'customer-new',
                                 'test': True
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
                                 'action': 'customer-new',
                                 'test': True
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
                   'order-edit',
                   'order-edit-date',
                   'order-edit-item',
                   'order-pay-now',
                   'order-close',
                   'update-status',
                   'customer-edit',
                   'order-delete-item',
                   'customer-delete',
                   )
        for action in actions:
            resp = self.client.post(reverse('actions'),
                                    {'pk': 2000, 'action': action})
            self.assertEqual(resp.status_code, 404)

    def test_time_new_adds_new_time(self):
        """Test the proper creation of times."""
        self.client.post(reverse('actions'), {'item': '1',
                                              'qty': 2,
                                              'item_class': '2',
                                              'activity': '2',
                                              'notes': 'Test note',
                                              'time': 0.5,
                                              'action': 'time-new',
                                              'pk': None,
                                              'test': True})
        Timing.objects.get(notes='Test note')

    def test_time_new_redirects_to_main_page(self):
        """When adding a time, return to main page."""
        resp = self.client.post(reverse('actions'),
                                {'item': '1',
                                 'item_class': '2',
                                 'activity': '2',
                                 'qty': 2,
                                 'notes': 'Test note',
                                 'time': 0.5,
                                 'action': 'time-new',
                                 'pk': None,
                                 'test': True})
        self.assertRedirects(resp, reverse('main'))

    def test_invalid_time_new_return_to_form_again(self):
        """When sending invalid data we shoud recover the form."""
        resp = self.client.post(reverse('actions'),
                                {'item': '1',
                                 'qty': 'this must be int',
                                 'notes': 'Test note',
                                 'time': 0.5,
                                 'action': 'time-new',
                                 'pk': None,
                                 'test': True})
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/add/add_time.html')
        self.assertIsInstance(context, list)
        self.assertEqual(context[0], 'form')

    def test_comment_adds_comment(self):
        """Test the proper insertion of comments."""
        order = Order.objects.get(ref_name='example')
        self.client.post(reverse('actions'), {'action': 'order-comment',
                                              'pk': order.pk,
                                              'comment': 'Entered comment',
                                              'test': True})
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
                                 'comment': 'Entered comment',
                                 'test': True})

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
                                 'pk': order.pk,
                                 'test': True})
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
                                              'comment': 'Entered comment',
                                              'test': True})
        comment = Comment.objects.get(comment='Entered comment')
        resp = self.client.post(reverse('actions'), {'action': 'comment-read',
                                                     'pk': comment.pk,
                                                     'test': True})
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
                          'description': 'added item',
                          'test': True
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
                                 'description': 'added item',
                                 'test': True
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
                                 'description': 'invalid item',
                                 'test': True
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
        # Create an item
        order = Order.objects.get(ref_name='example')
        OrderItem.objects.create(item=1,
                                 size='XL',
                                 qty=1,
                                 description='example item',
                                 reference=order)

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
                                 'action': 'order-edit',
                                 'test': True
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
                                 'action': 'order-edit',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('order', 'form')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/add/add_order.html')
        self.assertTrue(self.context_vars(data['context'], vars))

    def test_edit_date_successful(self):
        """Test the correct quick-edit date."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'delivery': date(2017, 1, 1),
                                 'pk': order.pk,
                                 'action': 'order-edit-date',
                                 'test': True
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
                                 'action': 'order-edit-date',
                                 'test': True
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
                              'action': 'order-edit-date',
                              'test': True
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
                                 'action': 'customer-edit',
                                 'test': True
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
                                 'action': 'customer-edit',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('customer', 'form')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/edit/edit_customer.html')
        self.assertTrue(self.context_vars(data['context'], vars))

    def test_edit_item_edits_item(self):
        """Test the correct item edition."""
        item = OrderItem.objects.get(description='example item')
        resp = self.client.post(reverse('actions'),
                                {'item': '2',
                                 'size': 'L',
                                 'qty': 2,
                                 'description': 'Modified item',
                                 'pk': item.pk,
                                 'action': 'order-edit-item',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('order', 'form', 'items')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/order_details.html')
        self.assertEqual(data['html_id'], '#order-details')
        self.assertTrue(self.context_vars(data['context'], vars))

        # Test if the fields were modified
        mod_item = OrderItem.objects.get(pk=item.pk)
        self.assertEqual(mod_item.item, '2')
        self.assertEqual(mod_item.size, 'L')
        self.assertEqual(mod_item.qty, 2)
        self.assertEqual(mod_item.description, 'Modified item')

    def test_edit_item_invalid_returns_to_form(self):
        """Test rejected forms."""
        item = OrderItem.objects.get(description='example item')
        resp = self.client.post(reverse('actions'),
                                {'qty': 'invalid qty',
                                 'pk': item.pk,
                                 'action': 'order-edit-item',
                                 'test': True
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('form', 'item')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/edit/edit_item.html')
        self.assertTrue(self.context_vars(data['context'], vars))

    def test_collect_order_succesful(self):
        """Test the proper mark-as-paid method."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'pk': order.pk,
                                 'action': 'order-pay-now',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['html_id'], '#order-status')
        self.assertEqual(data['template'], 'includes/order_status.html')
        self.assertEqual(data['context'][0], 'order')

    def test_close_order_succesful(self):
        """Test the proper close of orders."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'prepaid': 2000,
                                 'workshop': 200,
                                 'pk': order.pk,
                                 'action': 'order-close',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        closed_order = Order.objects.get(pk=order.pk)
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertTrue(data['reload'])
        self.assertEqual(closed_order.status, '7')

    def test_close_order_rejected(self):
        """Test when a form is not valid."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'prepaid': 'invalid price',
                                 'workshop': 200,
                                 'pk': order.pk,
                                 'action': 'order-close',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('order', 'form')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/edit/close_order.html')
        self.assertTrue(self.context_vars(data['context'], vars))

    def test_update_status_returns_false_on_raising_error(self):
        """Invalid statuses should raise an exception."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'), {'pk': order.pk,
                                                     'action': 'update-status',
                                                     'status': '9',
                                                     'test': True
                                                     })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertTrue(data['reload'])

    def tests_update_status_successful(self):
        """Test the proper status change."""
        order = Order.objects.get(ref_name='example')
        for i in range(1, 9):
            with self.subTest(i=i):
                resp = self.client.post(reverse('actions'),
                                        {'pk': order.pk,
                                         'action': 'update-status',
                                         'status': str(i),
                                         'test': True
                                         })
                # Test the response object
                data = json.loads(str(resp.content, 'utf-8'))
                template = data['template']
                self.assertIsInstance(resp, JsonResponse)
                self.assertIsInstance(resp.content, bytes)
                self.assertTrue(data['form_is_valid'])
                self.assertEqual(template, 'includes/order_status.html')
                self.assertEqual(data['html_id'], '#order-status')
                self.assertTrue(data['context'][0], 'order')

    def test_delete_item_deletes_the_item(self):
        """Test the proper deletion of items."""
        item = OrderItem.objects.get(description='example item')
        self.client.post(reverse('actions'), {'pk': item.pk,
                                              'action': 'order-delete-item',
                                              'test': True
                                              })
        with self.assertRaises(ObjectDoesNotExist):
            OrderItem.objects.get(pk=item.pk)

    def test_delete_item_context_response(self):
        """Test the response on deletion of items."""
        item = OrderItem.objects.get(description='example item')
        resp = self.client.post(reverse('actions'),
                                {'pk': item.pk,
                                 'action': 'order-delete-item',
                                 'test': True
                                 })

        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('order', 'items')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/order_details.html')
        self.assertEqual(data['html_id'], '#order-details')
        self.assertTrue(self.context_vars(data['context'], vars))

    def test_delete_customer_deletes_customer(self):
        """Test the proper deletion of customers."""
        customer = Customer.objects.get(name='Customer')
        self.client.post(reverse('actions'), {'pk': customer.pk,
                                              'action': 'customer-delete',
                                              'test': True
                                              })
        with self.assertRaises(ObjectDoesNotExist):
            OrderItem.objects.get(pk=customer.pk)

    def test_delete_customer_returns_to_custmer_list(self):
        """Test the proper deletion of customers."""
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')

        customer = Customer.objects.get(name='Customer')
        resp = self.client.post(reverse('actions'),
                                {'pk': customer.pk,
                                 'action': 'customer-delete',
                                 'test': True
                                 })
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('customerlist'))

    def test_logout_succesfull(self):
        """Test the proper logout from app."""
        resp = self.client.post(reverse('actions'), {'pk': None,
                                                     'action': 'logout',
                                                     'test': True})
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('login'))
#
#
#
#
