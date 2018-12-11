"""The main test suite for views. backend."""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from orders.models import Customer, Order, OrderItem, Comment, Item
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import F, Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta, time
from random import randint
from orders import settings
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
        login_url = '/accounts/login/?next=/orders%26orderby%253Ddate/'
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
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
        login_url = '/accounts/login/?next=/customer_view/1'
        resp = self.client.get(reverse('customer_view', kwargs={'pk': 1}))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_not_logged_in_on_customer_view(self):
        """Test not logged in users should be redirected to login."""
        login_url = '/accounts/login/?next=/customers'
        resp = self.client.get(reverse('customerlist'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)


class OrderListTests(TestCase):
    """Test the orderlist view especifically."""

    def setUp(self):
        """Create the necessary items on database at once.

        1 user, 1 customer, 3 orders.
        """
        self.client = Client()
        user = User.objects.create_user(username='regular', password='test')
        customer = Customer.objects.create(name='Test Customer',
                                           address='This computer',
                                           city='No city',
                                           phone='666666666',
                                           email='customer@example.com',
                                           CIF='5555G',
                                           cp='48100')
        for i in range(3):
            Order.objects.create(user=user,
                                 customer=customer,
                                 ref_name='Test order%s' % i,
                                 delivery=date.today(),
                                 waist=randint(10, 50),
                                 chest=randint(10, 50),
                                 hip=randint(10, 50),
                                 lenght=randint(10, 50),
                                 others='Custom notes',
                                 budget=2000,
                                 prepaid=0)

    def test_order_list(self):
        """First test the existence of order list."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/orders.html')

    def test_post_method_raises_404_with_pk_out_of_range(self):
        """When using a pk out of range should raise a 404."""
        self.client.login(username='regular', password='test')
        resp = self.client.post(reverse('orderlist',
                                        kwargs={'orderby': 'date'}),
                                {'status': '5',
                                 'order': 50000})
        self.assertEqual(resp.status_code, 404)

    def test_post_method_updates_status(self):
        """Test the proper status update on post method."""
        self.client.login(username='regular', password='test')
        order = Order.objects.all()[0]
        self.client.post(reverse('orderlist', kwargs={'orderby': 'date'}),
                         {'status': '5', 'order': order.pk})
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '5')

    def test_post_method_collect(self):
        """Test the proper set paid on orders."""
        self.client.login(username='regular', password='test')
        order = Order.objects.all()[0]
        self.client.post(reverse('orderlist', kwargs={'orderby': 'date'}),
                         {'collect': True, 'order': order.pk})
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.budget, order.prepaid)

    def test_post_method_raises_404_without_action(self):
        """When no action is given raise a 404 error."""
        self.client.login(username='regular', password='test')
        order = Order.objects.all()[0]
        resp = self.client.post(reverse('orderlist',
                                        kwargs={'orderby': 'date'}),
                                {'void': '5', 'order': order.pk})
        self.assertEqual(resp.status_code, 404)

    def test_tz_should_exist_case_insensitive(self):
        """Tz customer must be recognized regardless the case.

        They should return 1 active order and an empty queryset delivered.
        """
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        Order.objects.create(user=user,
                             customer=tz,
                             ref_name='tzOrder',
                             delivery=date.today(),
                             budget=100,
                             prepaid=20)
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertTrue(resp.context['active_stock'])
        self.assertEquals(len(resp.context['delivered_stock']), 0)
        for name in ('trapuzarrak', 'TraPuZarrak'):
            tz.name = name
            tz.save()
            resp = self.client.get(reverse('orderlist',
                                           kwargs={'orderby': 'date'}))
            self.assertTrue(resp.context['active_stock'])
            self.assertEquals(len(resp.context['delivered_stock']), 0)

    def test_tz_does_not_exist(self):
        """When tz doesn't exist tz orders should be empty."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))

        self.assertFalse(resp.context['active_stock'])
        self.assertFalse(resp.context['delivered_stock'])

    def test_tz_active_orders(self):
        """Test the number of active tz orders."""
        self.client.login(username='regular', password='test')
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order = Order.objects.all()[0]
        order.customer = tz
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['active_stock']), 1)

    def test_tz_active_orders_sorting(self):
        """Test the sorting of active tz orders."""
        self.client.login(username='regular', password='test')
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        orders = Order.objects.all()
        newer, older = orders[:2]
        newer.customer = tz
        newer.save()

        older.delivery = date.today() - timedelta(days=1)
        older.customer = tz
        older.save()

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        newer = Order.objects.get(pk=newer.pk)
        older = Order.objects.get(pk=older.pk)
        self.assertEqual(len(resp.context['active_stock']), 2)
        self.assertEqual(resp.context['active_stock'][0], older)
        self.assertEqual(resp.context['active_stock'][1], newer)

    def test_tz_delivered_orders(self):
        """Test the number of delivered tz orders."""
        self.client.login(username='regular', password='test')
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order = Order.objects.all()[0]
        order.customer = tz
        order.status = '7'
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['delivered_stock']), 1)

    def test_tz_delivered_orders_sorting(self):
        """Test the sorting of active tz orders."""
        self.client.login(username='regular', password='test')
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        orders = Order.objects.all()
        newer, older = orders[:2]
        newer.customer = tz
        newer.status = '7'
        newer.save()

        older.delivery = date.today() - timedelta(days=1)
        older.customer = tz
        older.status = '7'
        older.save()

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        newer = Order.objects.get(pk=newer.pk)
        older = Order.objects.get(pk=older.pk)
        self.assertEqual(len(resp.context['delivered_stock']), 2)
        self.assertEqual(resp.context['delivered_stock'][0], newer)
        self.assertEqual(resp.context['delivered_stock'][1], older)

    def test_tz_max_number_of_delivered_orders(self):
        """Only 10 orders should be shown."""
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        for i in range(11):
            Order.objects.create(user=user,
                                 customer=tz,
                                 ref_name='Test order%s' % i,
                                 delivery=date.today(),
                                 status='7',
                                 waist=randint(10, 50),
                                 chest=randint(10, 50),
                                 hip=randint(10, 50),
                                 lenght=randint(10, 50),
                                 others='Custom notes',
                                 budget=2000,
                                 prepaid=0)
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['delivered_stock']), 10)

    def test_tz_active_orderitems_count(self):
        """Test the correct count of orderItems."""
        self.client.login(username='regular', password='test')
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order = Order.objects.all()[0]
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i)

        order.customer = tz
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['active_stock'][0].orderitem__count, 2)

    def test_tz_active_comments_count(self):
        """Test the correct count of comments."""
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order = Order.objects.all()[0]
        for i in range(2):
            Comment.objects.create(user=user, reference=order, comment=i)

        order.customer = tz
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['active_stock'][0].comment__count, 2)

    def test_tz_active_timing_sum(self):
        """Test the correct sum of times in orderItems."""
        self.client.login(username='regular', password='test')
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order = Order.objects.all()[0]
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i,
                                     crop=time(5), sewing=time(3),
                                     iron=time(2))
        order.customer = tz
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['active_stock'][0].timing,
                         timedelta(0, 72000))

    def test_tz_delivered_orderitems_count(self):
        """Test the correct count of orderItems."""
        self.client.login(username='regular', password='test')
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order = Order.objects.all()[0]
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i)

        order.customer = tz
        order.status = '7'
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        order_item_count = resp.context['delivered_stock'][0].orderitem__count
        self.assertEqual(order_item_count, 2)

    def test_tz_delivered_comments_count(self):
        """Test the correct count of comments."""
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order = Order.objects.all()[0]
        for i in range(2):
            Comment.objects.create(user=user, reference=order, comment=i)

        order.customer = tz
        order.status = '7'
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['delivered_stock'][0].comment__count, 2)

    def test_tz_delivered_timing_sum(self):
        """Test the correct sum of times in orderItems."""
        self.client.login(username='regular', password='test')
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order = Order.objects.all()[0]
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i,
                                     crop=time(5), sewing=time(3),
                                     iron=time(2))
        order.customer = tz
        order.status = '7'
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['delivered_stock'][0].timing,
                         timedelta(0, 72000))

    def test_delivered_orders_show_only_delivered(self):
        """Test wether the status is 7."""
        self.client.login(username='regular', password='test')
        orders = Order.objects.all()
        for order in orders:
            order.status = '7'
            order.save()

        orders = Order.objects.filter(status='7')
        self.assertEqual(len(orders), 3)

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        for order in resp.context['delivered']:
            self.assertEqual(order.status, '7')

    def test_delivered_orders_sorting_method(self):
        """Sort the list by last delivered first."""
        self.client.login(username='regular', password='test')
        orders = Order.objects.all()
        newer, older = orders[:2]
        newer.status = '7'
        newer.save()

        older.delivery = date.today() - timedelta(days=1)
        older.status = '7'
        older.save()

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        newer = Order.objects.get(pk=newer.pk)
        older = Order.objects.get(pk=older.pk)
        self.assertEqual(len(resp.context['delivered']), 2)
        self.assertEqual(resp.context['delivered'][0], newer)
        self.assertEqual(resp.context['delivered'][1], older)

    def test_delivered_orders_ten_max(self):
        """Delivered orders show only last ten entries."""
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        customer = Customer.objects.all()[0]
        for i in range(11):
            Order.objects.create(user=user,
                                 customer=customer,
                                 ref_name='Test%s' % i,
                                 delivery=date.today(),
                                 status='7',
                                 budget=100,
                                 prepaid=100)
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['delivered']), 10)

    def test_active_exclude_status_7_and_8(self):
        """Active orders should exclude status 7 & 8."""
        self.client.login(username='regular', password='test')
        self.assertEqual(len(Order.objects.all()), 3)
        active, delivered, cancelled = Order.objects.all()
        active.status = '1'
        active.ref_name = 'active'
        active.save()
        delivered.status = '7'
        delivered.save()
        cancelled.status = '8'
        cancelled.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['active'][0].ref_name, 'active')

    def test_cancelled_orders_show_only_cancelled(self):
        """Cancelled orders should exclude all status but 8."""
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        customer = Customer.objects.all()[0]
        for i in range(2, 9):
            Order.objects.create(user=user,
                                 customer=customer,
                                 ref_name='Test%s' % i,
                                 delivery=date.today(),
                                 status=str(i),
                                 budget=100,
                                 prepaid=100)
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['cancelled']), 1)
        self.assertEqual(resp.context['cancelled'][0].ref_name, 'Test8')

    def test_cancelled_orders_sorting_method(self):
        """Sort the list by last inboxed first."""
        self.client.login(username='regular', password='test')
        orders = Order.objects.all()
        newer, older = orders[:2]
        newer.status = '8'
        newer.save()

        older.inbox_date = older.inbox_date - timedelta(days=1)
        older.status = '8'
        older.save()

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        newer = Order.objects.get(pk=newer.pk)
        older = Order.objects.get(pk=older.pk)
        self.assertEqual(len(resp.context['cancelled']), 2)
        self.assertEqual(resp.context['cancelled'][0], newer)
        self.assertEqual(resp.context['cancelled'][1], older)

    def test_cancelled_orders_ten_max(self):
        """Cancelled orders show only last ten entries."""
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        customer = Customer.objects.all()[0]
        for i in range(11):
            Order.objects.create(user=user,
                                 customer=customer,
                                 ref_name='Test%s' % i,
                                 delivery=date.today(),
                                 status='8',
                                 budget=100,
                                 prepaid=100)
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['cancelled']), 10)

    def test_pending_orders_exclude_cancelled(self):
        """Pending orders exclude status 8."""
        self.client.login(username='regular', password='test')
        order = Order.objects.all()[0]
        order.status = '8'
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['pending']), 2)

    def test_pending_orders(self):
        """Test the proper query for pending orders."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['pending']), 3)

    def test_pending_orders_sorting_method(self):
        """Sort the list by first inboxed first."""
        self.client.login(username='regular', password='test')
        newer, older, excluded = Order.objects.all()

        older.inbox_date = older.inbox_date - timedelta(days=1)
        older.save()

        excluded.status = '8'
        excluded.save()

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        newer = Order.objects.get(pk=newer.pk)
        older = Order.objects.get(pk=older.pk)
        self.assertEqual(len(resp.context['pending']), 2)
        self.assertEqual(resp.context['pending'][0], older)
        self.assertEqual(resp.context['pending'][1], newer)

    def test_active_orderitems_count(self):
        """Test the proper count of items."""
        self.client.login(username='regular', password='test')
        order = Order.objects.all()[0]
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i)

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['active'][0].orderitem__count, 2)

    def test_active_comment_count(self):
        """Test the correct count of comments."""
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        order = Order.objects.all()[0]
        for i in range(2):
            Comment.objects.create(user=user, reference=order, comment=i)

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['active'][0].comment__count, 2)

    def test_delivered_orderitems_count(self):
        """Test the proper count of items."""
        self.client.login(username='regular', password='test')
        order = Order.objects.all()[0]
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i)

        order.status = '7'
        order.save()

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['delivered'][0].orderitem__count, 2)

    def test_delivered_comments_count(self):
        """Test the correct count of comments."""
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        order = Order.objects.all()[0]
        for i in range(2):
            Comment.objects.create(user=user, reference=order, comment=i)

        order.status = '7'
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['delivered'][0].comment__count, 2)

    def test_delivered_timing_sum(self):
        """Test the correct sum of times in orderItems."""
        self.client.login(username='regular', password='test')
        order = Order.objects.all()[0]
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i,
                                     crop=time(5), sewing=time(3),
                                     iron=time(2))
        order.status = '7'
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['delivered'][0].timing,
                         timedelta(0, 72000))


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
            OrderItem.objects.create(qty=5,
                                     description='notes',
                                     reference=order)

        # deliver the first 10 orders
        order_bulk_edit = Order.objects.all().order_by('inbox_date')[:10]
        for order in order_bulk_edit:
            order.ref_name = 'example delivered' + str(order.pk)
            order.status = 7
            order.save()

        # Have a closed order (delivered & paid)
        order = Order.objects.filter(status=7)[0]
        order.ref_name = 'example closed'
        order.prepaid = order.budget
        order.save()

        # Have a read comment
        order = Order.objects.get(ref_name='example closed')
        comment = Comment.objects.all()[0]
        comment.read = True
        comment.reference = order
        comment.comment = 'read comment'
        comment.save()

        # Now login to avoid the 404
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

    def test_main_view_pending_orders(self):
        """Test the proper display of pending orders on main view."""
        resp = self.client.get(reverse('main'))
        self.assertEquals(len(resp.context['pending']), 19)
        self.assertEquals(resp.context['pending_total'], 38000)

    def test_main_view_pending_orders_exclude_tz_ones(self):
        """Pending query results should exclude tz orders."""
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order = Order.objects.exclude(status=8)[1]
        order.customer = tz
        order.save()
        resp = self.client.get(reverse('main'))
        for order in resp.context['pending']:
            self.assertNotEqual(order.customer.name, 'Trapuzarrak')

    def test_order_list(self):
        """Test the main features on order list."""
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/orders.html')

        # Test context vars
        self.assertEqual(resp.context['active'][0].ref_name, 'example10')
        self.assertEqual(str(resp.context['user']), 'regular')
        self.assertEqual(str(resp.context['version']), settings.VERSION)
        self.assertEqual(str(resp.context['order_by']), 'date')
        self.assertEqual(resp.context['placeholder'],
                         'Buscar pedido (referencia o nº)')
        self.assertEqual(str(resp.context['search_on']), 'orders')
        self.assertEqual(str(resp.context['title']), 'TrapuZarrak · Pedidos')
        self.assertEqual(resp.context['colors'], settings.WEEK_COLORS)
        self.assertTrue(resp.context['footer'])

    def test_order_list_cancelled_show_last_ten(self):
        """Delivered orders should be a list of last ten elements."""
        Order.objects.all().update(status=8)
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['cancelled']), 10)

    def test_order_list_sorting_methods(self):
        """Test the correct sorting of entries."""
        # Order by date
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))

        self.assertEqual(resp.context['order_by'], 'date')
        for i in range(9):
            first_order = resp.context['active'][i].delivery
            next_order = resp.context['active'][i+1].delivery
            self.assertTrue(first_order <= next_order)

        # order by status
        for order in Order.objects.exclude(status__in=[7, 8]):
            order.status = randint(1, 6)
            order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'status'}))
        self.assertEqual(resp.context['order_by'], 'status')
        for i in range(9):
            first_order = resp.context['active'][i].status
            next_order = resp.context['active'][i+1].status
            self.assertTrue(first_order <= next_order)

        # order by priority
        order = Order.objects.get(ref_name='example13')
        order.priority = '1'
        order.save()
        order = Order.objects.get(ref_name='example12')
        order.priority = '3'
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'priority'}))
        self.assertEqual(resp.context['order_by'], 'priority')
        for i in range(9):
            first_order = resp.context['active'][i].priority
            next_order = resp.context['active'][i+1].priority
            self.assertTrue(first_order <= next_order)

        # inavlid sorting method
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'invalid'}))
        self.assertEqual(resp.status_code, 404)

    def test_order_list_active_week_entries(self):
        """Test whether there are active entries this week."""
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        this_week = date.today().isocalendar()[1]
        this_week_entries = Order.objects.filter(Q(delivery__week=this_week) |
                                                 Q(delivery__lte=timezone.now()
                                                   ))
        this_week_entries = this_week_entries.exclude(status__in=[7, 8])
        self.assertEqual(len(resp.context['this_week_active']),
                         len(this_week_entries))

    def test_calendar_view_active(self):
        """Test the active elements on calendar view."""
        orders = Order.objects.all()
        for order in orders:
            order.delivery = date.today() - timedelta(days=1)
            order.status = '2'
            order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(len(resp.context['active_calendar']),
                         len(orders))

    def test_trapuzarrak_delivered_orders_dont_show_up_in_views(self):
        """Trapuzarrak delievered orders shouldn't be seen on orderlist."""
        tz = Customer.objects.create(name='trapuzarrak',
                                     address='Foruen',
                                     city='Mungia',
                                     phone='662',
                                     cp=48100)
        user = User.objects.get(username='regular')
        Order.objects.create(user=user,
                             customer=tz,
                             status=7,
                             delivery=date.today(),
                             ref_name='tz order',
                             budget=100,
                             prepaid=0)
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        total_orders = len(Order.objects.all())
        self.assertEqual(total_orders, 21)
        for order in resp.context['delivered']:
            self.assertNotEqual(order.ref_name, 'tz order')
        for order in resp.context['active']:
            self.assertNotEqual(order.ref_name, 'tz order')

    def test_tz_cancelled_orders(self):
        """Test the proper return of cancelled orders.

        Trapuzarrak ones should not appear.
        """
        order = Order.objects.get(ref_name='example10')
        order.status = 8
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEquals(len(resp.context['cancelled']), 1)

        # Now change the customer, tz should not appear.
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        order.customer = tz
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEquals(len(resp.context['cancelled']), 0)

    def test_pending_orders(self):
        """Test the correct show of pending invoices."""
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEquals(len(resp.context['pending']), 19)
        self.assertEquals(resp.context['pending_total'], 38000)

    def test_pending_orders_more_ancient_first(self):
        """The order should be from more ancient up."""
        order = Order.objects.exclude(status=8)
        order = order.filter(budget__gt=F('prepaid'))[0]
        order.inbox_date = order.inbox_date - timedelta(weeks=52)
        order.ref_name = 'Should be first'
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEquals(resp.context['pending'][0],
                          Order.objects.get(ref_name='Should be first'))

    def test_pending_orders_should_dismiss_cancelled(self):
        """Pending orders don't include cancelled orders."""
        order = Order.objects.all()[0]
        order.status = 8
        order.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEquals(len(resp.context['pending']), 18)
        self.assertEquals(resp.context['pending_total'], 36000)

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
        self.assertTemplateUsed(resp, 'tz/list_view.html')

        ctx = resp.context
        self.assertEqual(str(ctx['user']), 'regular')

    def test_customer_list_context_vars(self):
        """Test the correct context vars."""
        resp = self.client.get(reverse('customerlist'))
        self.assertEqual(resp.context['search_on'], 'customers')
        self.assertEqual(resp.context['placeholder'], 'Buscar cliente')
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Clientes')
        self.assertEqual(resp.context['h3'], 'Todos los clientes')
        self.assertEqual(resp.context['btn_title_add'], 'Nuevo cliente')
        self.assertEqual(resp.context['js_action_add'], 'customer-add')
        self.assertEqual(resp.context['js_data_pk'], '0')
        self.assertEqual(resp.context['include_template'],
                         'includes/customer_list.html')
        self.assertTrue(resp.context['footer'])

    def test_customer_list_paginator(self):
        """Test paginator functionality on customer list."""
        for i in range(10):
            Customer.objects.create(name='Test customer%s' % i,
                                    city='This computer',
                                    phone=55,
                                    cp=30)
        resp = self.client.get('/customers')

        self.assertEqual(resp.status_code, 200)

        customers = resp.context['customers']
        self.assertFalse(customers.has_previous())
        self.assertTrue(customers.has_next())
        self.assertTrue(customers.has_other_pages())
        self.assertEqual(customers.next_page_number(), 2)
        self.assertEqual(len(customers), 10)

    def test_customer_paginator_not_an_int_exception(self):
        """When page is not an int, paginator should go to the first one.

        That is because the exception was catch.
        """
        for i in range(10):
            Customer.objects.create(name='Test customer%s' % i,
                                    city='This computer',
                                    phone=55,
                                    cp=30)
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
        for i in range(10):
            Customer.objects.create(name='Test customer%s' % i,
                                    city='This computer',
                                    phone=55,
                                    cp=30)
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')
        resp = self.client.get(reverse('customerlist'), {'page': 20})

        customers = resp.context['customers']
        self.assertEqual(customers.number, 2)
        self.assertTrue(customers.has_previous())
        self.assertFalse(customers.has_next())
        self.assertTrue(customers.has_other_pages())
        self.assertEqual(len(customers), 10)

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

    def test_items_view_default_item(self):
        """In the begining just one item should be on db."""
        resp = self.client.get(reverse('itemslist'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/list_view.html')
        self.assertEqual(len(resp.context['items']), 1)

    def test_items_view_context_vars(self):
        """Test the correct context vars."""
        resp = self.client.get(reverse('itemslist'))
        self.assertEqual(resp.context['search_on'], 'items')
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Prendas')
        self.assertEqual(resp.context['h3'], 'Todas las prendas')
        self.assertEqual(resp.context['btn_title_add'], 'Añadir prenda')
        self.assertEqual(resp.context['js_action_add'], 'object-item-add')
        self.assertEqual(resp.context['js_action_edit'], 'object-item-edit')
        self.assertEqual(resp.context['js_action_delete'],
                         'object-item-delete')
        self.assertEqual(resp.context['js_data_pk'], '0')
        self.assertEqual(resp.context['include_template'],
                         'includes/items_list.html')
        self.assertTrue(resp.context['footer'])
        self.assertEquals(resp.context['version'], settings.VERSION)
        self.assertEquals(resp.context['item_types'], settings.ITEM_TYPE[1:])
        self.assertEquals(resp.context['item_classes'], settings.ITEM_CLASSES)

    def test_mark_down_view(self):
        """Test the proper work of view."""
        resp = self.client.get(reverse('changelog'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)

    def test_mark_down_view_only_accept_get(self):
        """Method should be get."""
        resp = self.client.post(reverse('changelog'))
        self.assertEqual(resp.status_code, 404)

    def test_filter_items_view_only_accept_get(self):
        """Method should be get."""
        resp = self.client.post(reverse('filter-items'))
        self.assertEqual(resp.status_code, 404)

    def test_filter_items_view_3_filters(self):
        """Test the proper function of the filters."""
        Item.objects.create(name='Object', item_type='3', item_class='S',
                            fabrics=0)
        resp = self.client.get(reverse('filter-items'),
                               {'search-obj': 'obj',
                                'item-type': '3',
                                'item-class': 'S',
                                'test': True,
                                })
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/items_list.html')
        self.assertIsInstance(context, list)
        vars = ('items', 'item_types', 'item_classes', 'add_to_order',
                'filter_on', 'js_action_send_to', 'js_action_edit',
                'js_action_delete')
        self.assertTrue(self.context_vars(context, vars))
        self.assertEqual(data['filter_on'],
                         'Filtrando obj en Camisas con acabado Standard')
        self.assertEqual(data['len_items'], 1)

    def test_filter_items_view_no_obj(self):
        """Test the proper function of the filters."""
        Item.objects.create(name='Object', item_type='3', item_class='S',
                            fabrics=0)
        resp = self.client.get(reverse('filter-items'),
                               {'item-type': '3',
                                'item-class': 'S',
                                'test': True,
                                })
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/items_list.html')
        self.assertIsInstance(context, list)
        vars = ('items', 'item_types', 'item_classes', 'add_to_order',
                'filter_on', 'js_action_send_to', 'js_action_edit',
                'js_action_delete')
        self.assertTrue(self.context_vars(context, vars))
        self.assertEqual(data['filter_on'],
                         'Filtrando elementos en Camisas con acabado Standard')
        self.assertEqual(data['len_items'], 1)

    def test_filter_no_filter_returns_false_filter_on(self):
        """When no filter is applied, filter_on var should be false."""
        Item.objects.create(name='Object', item_type='3', item_class='S',
                            fabrics=0)
        resp = self.client.get(reverse('filter-items'), {'test': True})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertFalse(data['filter_on'])

    def test_filter_no_obj_returns_empty_queryset(self):
        """When there are no matches on obj, empty list should be returned."""
        resp = self.client.get(reverse('filter-items'),
                               {'search-obj': 'element-null',
                                'test': True})
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(data['len_items'], 0)

    def test_filter_no_matches_show_a_warning(self):
        """When there are no matches, we should show a message."""
        resp1 = self.client.get(reverse('filter-items'),
                                {'search-obj': 'Null element', 'test': True})
        resp2 = self.client.get(reverse('filter-items'),
                                {'item-type': '5', 'test': True})
        resp3 = self.client.get(reverse('filter-items'),
                                {'item-class': 'S', 'test': True})
        for resp in (resp1, resp2, resp3):
            data = json.loads(str(resp.content, 'utf-8'))
            self.assertEqual(data['filter_on'],
                             'El filtro no devolvió ningún resultado')


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
            OrderItem.objects.create(qty=5,
                                     description='notes',
                                     reference=order)

        # deliver the first 10 orders
        order_bulk_edit = Order.objects.all().order_by('inbox_date')[:10]
        for order in order_bulk_edit:
            order.ref_name = 'example delivered' + str(order.pk)
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

    def test_search_on_orders_by_pk(self):
        """Test search orders by pk."""
        order = Order.objects.all()[0]
        resp = self.client.post(reverse('search'),
                                {'search-on': 'orders',
                                 'search-obj': order.pk,
                                 'test': True})
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertEquals(data['template'], 'includes/search_results.html')
        self.assertEquals(data['query_result'], 1)
        self.assertEquals(data['query_result_name'], order.ref_name)

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

        # Create Item & time
        order = Order.objects.get(ref_name='example')
        OrderItem.objects.create(qty=5, description='notes', reference=order)
        cls.client = Client()

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

    def test_pk_out_of_range_raises_404(self):
        """High pk should raise a 404."""
        actions = ('order-from-customer',
                   'order-item-add',
                   'order-add-comment',
                   'order-edit',
                   'order-edit-date',
                   'customer-edit',
                   'order-pay-now',
                   'order-close',
                   'object-item-edit',
                   'order-item-edit',
                   'object-item-delete',
                   'order-item-delete',
                   'customer-delete',
                   )
        for action in actions:
            resp = self.client.get(reverse('actions'), {'pk': 2000,
                                                        'action': action})
            self.assertEqual(resp.status_code, 404)

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
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertTrue(self.context_vars(context, vars))

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
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn')
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

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
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertTrue(self.context_vars(context, vars))

    def test_send_item_to_order(self):
        """Test context dictionaries and template."""
        item = Item.objects.all()[0]
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'send-to-order',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        vars = ('orders', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertTrue(self.context_vars(context, vars))

    def test_add_order_item(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk,
                                'action': 'order-item-add',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/regular_form.html')
        vars = ('order', 'form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertTrue(self.context_vars(context, vars))

    def test_add_obj_item(self):
        """Test context dictionaries and template."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 'None',
                                'action': 'object-item-add',
                                'test': True,
                                })
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/regular_form.html')
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertTrue(self.context_vars(context, vars))

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
        self.assertEqual(template, 'includes/regular_form.html')
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn', )
        self.assertTrue(self.context_vars(context, vars))

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
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

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
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

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
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn')
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

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
        vars = ('modal_title', 'msg', 'pk', 'action', 'submit_btn')
        self.assertEqual(template, 'includes/confirmation.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

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
        vars = ('order', 'form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

    def test_edit_obj_item(self):
        """Test context dictionaries and template."""
        item = Item.objects.all()[0]
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'object-item-edit',
                                'test': True,
                                })
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/regular_form.html')
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertTrue(self.context_vars(context, vars))

    def test_edit_order_item(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        item = OrderItem.objects.get(reference=order)
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'order-item-edit',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        vars = ('item', 'form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

    def test_delete_order_item(self):
        """Test context dictionaries and template."""
        order = Order.objects.get(ref_name='example')
        item = OrderItem.objects.get(reference=order)
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'order-item-delete',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/delete_confirmation.html')
        self.assertIsInstance(context, list)
        vars = ('modal_title', 'pk', 'action', 'msg', 'submit_btn', )
        self.assertTrue(self.context_vars(context, vars))

    def test_delete_obj_item(self):
        """Test context dictionaries and template."""
        item = Item.objects.all()[0]
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'object-item-delete',
                                'test': True,
                                })
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/delete_confirmation.html')
        vars = ('modal_title', 'pk', 'action', 'msg', 'submit_btn')
        self.assertTrue(self.context_vars(context, vars))

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
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/delete_confirmation.html')
        vars = ('modal_title', 'pk', 'action', 'msg', 'submit_btn')
        self.assertTrue(self.context_vars(context, vars))

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
                                              'priority': '2',
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
                                 'priority': '1',
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
        self.assertEqual(template, 'includes/regular_form.html')
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertTrue(self.context_vars(context, vars))

    def test_customer_new_adds_customer(self):
        """Test new customer creation."""
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
        # test context response
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertTrue(data['reload'])
        self.assertTrue(data['form_is_valid'])
        self.assertTrue(Customer.objects.get(name='New Customer'))

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
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

    def test_pk_out_of_range_raises_404(self):
        """Raises a 404 when pk is out of index.

        All the cases but new order, customer or Object item
        """
        actions = ('order-comment',
                   'comment-read',
                   'order-item-add',
                   'order-edit',
                   'order-edit-date',
                   'customer-edit',
                   'object-item-edit',
                   'order-item-edit',
                   'order-pay-now',
                   'order-close',
                   'update-status',
                   'object-item-delete',
                   'order-item-delete',
                   'customer-delete',
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
        vars = ('comments', )
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
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn', )
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertTrue(self.context_vars(context, vars))

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

    def test_order_item_add_adds_item(self):
        """Test the proper insertion of items."""
        order = Order.objects.get(ref_name='example')
        item_obj = Item.objects.all()[0]
        self.client.post(reverse('actions'),
                         {'action': 'order-item-add',
                          'pk': order.pk,
                          'element': item_obj.pk,
                          'qty': 2,
                          'crop': 0,
                          'sewing': 0,
                          'iron': 0,
                          'fit': True,
                          'description': 'added item',
                          'test': True
                          })
        item = OrderItem.objects.get(description='added item')
        self.assertTrue(item)
        self.assertTrue(item.fit)
        self.assertEqual(item.reference, order)

    def test_order_item_add_context_response(self):
        """Test the response given by add item."""
        order = Order.objects.get(ref_name='example')
        item_obj = Item.objects.all()[0]
        resp = self.client.post(reverse('actions'),
                                {'action': 'order-item-add',
                                 'pk': order.pk,
                                 'element': item_obj.pk,
                                 'qty': 2,
                                 'crop': 0,
                                 'sewing': 0,
                                 'iron': 0,
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
        vars = ('order', 'items', 'btn_title_add', 'js_action_add',
                'js_action_edit', 'js_action_delete', 'js_data_pk')
        self.assertTrue(self.context_vars(context, vars))

    def test_order_item_add_invalid_form_returns_to_form_again(self):
        """Test item add invalid form behaviour."""
        order = Order.objects.get(ref_name='example')
        item_obj = Item.objects.all()[0]
        resp = self.client.post(reverse('actions'),
                                {'action': 'order-item-add',
                                 'pk': order.pk,
                                 'element': item_obj.pk,
                                 'qty': 'invalid quantity',
                                 'crop': 0,
                                 'sewing': 0,
                                 'iron': 0,
                                 'description': 'added item',
                                 'test': True
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/order_details.html')
        vars = ('form', 'order')
        self.assertTrue(self.context_vars(context, vars))

    def test_send_to_order_raises_error_invalid_item(self):
        """If no item is given raise a 404."""
        order = Order.objects.all()[0]
        no_item = self.client.post(reverse('actions'),
                                   {'action': 'send-to-order',
                                    'pk': 5000,
                                    'order': order.pk,
                                    'isfit': '0',
                                    'test': True,
                                    })
        self.assertEqual(no_item.status_code, 404)

    def test_send_to_order_raises_error_invalid_order(self):
        """If no order is given raise a 404."""
        item = Item.objects.all()[0]
        no_order = self.client.post(reverse('actions'),
                                    {'action': 'send-to-order',
                                     'pk': item.pk,
                                     'order': 50000,
                                     'isfit': '0',
                                     'test': True,
                                     })
        self.assertEqual(no_order.status_code, 404)

    def test_send_to_order_raises_error_invalid_isfit(self):
        """If no isfit is given raise a 404."""
        item = Item.objects.all()[0]
        order = Order.objects.all()[0]
        no_order = self.client.post(reverse('actions'),
                                    {'action': 'send-to-order',
                                     'pk': item.pk,
                                     'order': order.pk,
                                     'isfit': 'invalid',
                                     'test': True,
                                     })
        self.assertEqual(no_order.status_code, 404)

    def test_send_to_order_isfit_true(self):
        """Test the correct store of fit."""
        item = Item.objects.all()[0]
        order = Order.objects.all()[0]
        self.client.post(reverse('actions'), {'action': 'send-to-order',
                                              'pk': item.pk,
                                              'order': order.pk,
                                              'isfit': '1',
                                              'test': True,
                                              })
        order_item = OrderItem.objects.filter(element=item)
        order_item = order_item.filter(reference=order)
        self.assertEqual(len(order_item), 1)
        self.assertTrue(order_item[0].fit)

    def test_send_to_order_isfit_false(self):
        """Test the correct store of fit."""
        item = Item.objects.all()[0]
        order = Order.objects.all()[0]
        self.client.post(reverse('actions'), {'action': 'send-to-order',
                                              'pk': item.pk,
                                              'order': order.pk,
                                              'isfit': '0',
                                              'test': True,
                                              })
        order_item = OrderItem.objects.filter(element=item)
        order_item = order_item.filter(reference=order)
        self.assertEqual(len(order_item), 1)
        self.assertFalse(order_item[0].fit)

    def test_obj_item_adds_item(self):
        """Test the proepr creation of item objects."""
        self.client.post(reverse('actions'), {'action': 'object-item-add',
                                              'pk': 'None',
                                              'name': 'Example Item',
                                              'item_type': '2',
                                              'item_class': 'S',
                                              'size': '4',
                                              'fabrics': 4,
                                              'notes': 'Custom Notes',
                                              })
        self.assertTrue(Item.objects.get(name='Example Item'))

    def test_obj_item_add_context_response(self):
        """Test the context returned by obj item creation."""
        resp = self.client.post(reverse('actions'),
                                {'action': 'object-item-add',
                                 'pk': 'None',
                                 'name': 'Example Item',
                                 'item_type': '2',
                                 'item_class': 'S',
                                 'size': '4',
                                 'fabrics': 4,
                                 'notes': 'Custom Notes',
                                 'test': True,
                                 })
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/items_list.html')
        self.assertIsInstance(context, list)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['html_id'], '#item_objects_list')
        vars = ('items', 'js_action_edit', 'js_action_delete', )
        self.assertTrue(self.context_vars(context, vars))

    def test_obj_item_add_invalid_form_returns_to_form_again(self):
        """Should define."""
        resp = self.client.post(reverse('actions'),
                                {'action': 'object-item-add',
                                 'pk': 'None',
                                 'name': 'Example Item',
                                 'item_type': '2',
                                 'item_class': 'S',
                                 'size': '4',
                                 'fabrics': 'invalid quantity',
                                 'notes': 'Custom Notes',
                                 'test': True,
                                 })
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertFalse(data['form_is_valid'])
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',)
        self.assertTrue(self.context_vars(context, vars))


class ActionsPostMethodEdit(TestCase):
    """Test the post method on Actions view to edit elements."""

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
        OrderItem.objects.create(qty=1,
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
                                 'priority': '3',
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
        template = data['template']
        context = data['context']
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/regular_form.html')
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertTrue(self.context_vars(context, vars))

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

    def test_edit_date_returns_to_form_again(self):
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
        template = data['template']
        context = data['context']
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

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
        template = data['template']
        context = data['context']
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

    def test_obj_item_edit(self):
        """Test the correct item edition."""
        item = Item.objects.all()[0]
        resp = self.client.post(reverse('actions'),
                                {'name': 'Changed name',
                                 'item_type': '2',
                                 'item_class': 'M',
                                 'size': 'X',
                                 'fabrics': 5,
                                 'notes': 'Changed notes',
                                 'pk': item.pk,
                                 'action': 'object-item-edit',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('items', 'js_action_edit', 'js_action_delete',
                'js_action_send_to')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/items_list.html')
        self.assertEqual(data['html_id'], '#item_objects_list')
        self.assertTrue(self.context_vars(data['context'], vars))

        # Test if the fields were Modified
        edited = Item.objects.get(name='Changed name')
        self.assertNotEqual(item.name, edited.name)
        self.assertNotEqual(item.item_type, edited.item_type)
        self.assertNotEqual(item.item_class, edited.item_class)
        self.assertNotEqual(item.size, edited.size)
        self.assertNotEqual(item.fabrics, edited.fabrics)

    def test_obj_item_edit_invalid_form_returns_to_form_again(self):
        """Test the proper rejection of forms."""
        item = Item.objects.all()[0]
        resp = self.client.post(reverse('actions'),
                                {'name': 'Changed name',
                                 'item_type': '2',
                                 'item_class': 'M',
                                 'size': 'X',
                                 'fabrics': 'invalid field',
                                 'notes': 'Changed notes',
                                 'pk': item.pk,
                                 'action': 'object-item-edit',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn', )
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/regular_form.html')
        self.assertTrue(self.context_vars(data['context'], vars))

    def test_edit_item_edits_item(self):
        """Test the correct item edition."""
        item = OrderItem.objects.select_related('element')
        item = item.get(description='example item')
        resp = self.client.post(reverse('actions'),
                                {'element': item.element.pk,
                                 'qty': '2',
                                 'crop': '2',
                                 'sewing': '2',
                                 'iron': '2',
                                 'description': 'Modified item',
                                 'pk': item.pk,
                                 'action': 'order-item-edit',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('order', 'items', 'btn_title_add', 'js_action_add',
                'js_action_edit', 'js_action_delete', 'js_data_pk')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/order_details.html')
        self.assertEqual(data['html_id'], '#order-details')
        self.assertTrue(self.context_vars(data['context'], vars))

        # Test if the fields were modified
        mod_item = OrderItem.objects.get(pk=item.pk)
        self.assertEqual(mod_item.qty, 2)
        self.assertEqual(mod_item.description, 'Modified item')

    def test_edit_item_invalid_returns_to_form(self):
        """Test rejected forms."""
        item = OrderItem.objects.get(description='example item')
        resp = self.client.post(reverse('actions'),
                                {'qty': 'invalid qty',
                                 'pk': item.pk,
                                 'action': 'order-item-edit',
                                 'test': True
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('form', 'item', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/regular_form.html')
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
        self.assertTrue(data['reload'])

    def test_close_order_succesful(self):
        """Test the proper close of orders."""
        order = Order.objects.get(ref_name='example')
        resp = self.client.post(reverse('actions'),
                                {'prepaid': 2000,
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
        template = data['template']
        context = data['context']
        vars = ('order', 'form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

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
        for i in range(2, 9):
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

    def test_delete_order_item_deletes_the_item(self):
        """Test the proper deletion of items."""
        item = OrderItem.objects.get(description='example item')
        self.client.post(reverse('actions'), {'pk': item.pk,
                                              'action': 'order-item-delete',
                                              'test': True
                                              })
        with self.assertRaises(ObjectDoesNotExist):
            OrderItem.objects.get(pk=item.pk)

    def test_delete_order_item_context_response(self):
        """Test the response on deletion of items."""
        item = OrderItem.objects.get(description='example item')
        resp = self.client.post(reverse('actions'),
                                {'pk': item.pk,
                                 'action': 'order-item-delete',
                                 'test': True
                                 })

        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('order', 'items', 'btn_title_add', 'js_action_add',
                'js_action_edit', 'js_action_delete', 'js_data_pk')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/order_details.html')
        self.assertEqual(data['html_id'], '#order-details')
        self.assertTrue(self.context_vars(data['context'], vars))

    def test_delete_obj_item_deletes_the_item(self):
        """Test the correct item deletion."""
        item = Item.objects.all()[0]
        resp = self.client.post(reverse('actions'),
                                {'pk': item.pk,
                                 'action': 'object-item-delete',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('items', 'js_action_edit', 'js_action_delete',
                'js_action_send_to')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/items_list.html')
        self.assertEqual(data['html_id'], '#item_objects_list')
        self.assertTrue(self.context_vars(data['context'], vars))

        # test if the object was actually deleted
        with self.assertRaises(ObjectDoesNotExist):
            Item.objects.get(name=item.name)

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
