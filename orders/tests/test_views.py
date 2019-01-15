"""The main test suite for views. backend."""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from orders.models import (
    Customer, Order, OrderItem, Comment, Item, PQueue, Invoice, )
from django.core.exceptions import ValidationError, ObjectDoesNotExist
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

    def test_not_logged_in_on_order_express_view(self):
        """Test not logged in users should be redirected to login."""
        login_url = '/accounts/login/?next=/order/express/1'
        resp = self.client.get(reverse('order_express', kwargs={'pk': 1}))
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

    def test_not_logged_in_on_pqueue_manager(self):
        """Test not logged in users should be redirected to login."""
        login_url = '/accounts/login/?next=/pqueue/manager'
        resp = self.client.get(reverse('pqueue_manager'))
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
        Item.objects.create(name='test', fabrics=1, price=10)

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
        order = Order.objects.first()
        resp = self.client.post(
            reverse('orderlist', args=['date']),
            {'void': '5', 'order': order.pk})
        self.assertEqual(resp.status_code, 404)

    def test_orders_view_excludes_quick_orders(self):
        """Express orders should be excluded."""
        self.client.login(username='regular', password='test')
        excluded = Order.objects.first()
        excluded.ref_name = 'Quick'
        excluded.save()
        resp = self.client.get(
            reverse('orderlist', args=['date']))
        for order in resp.context['active']:
            self.assertNotEqual(order.ref_name, 'Quick')

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
        order = Order.objects.first()
        order.status = '8'
        order.save()
        resp = self.client.get(reverse('orderlist', args=['date']))
        self.assertEqual(len(resp.context['pending']), 2)

    def test_pending_are_2019_orders(self):
        """Pending should exclude orders whose delivery was before 2019."""
        self.client.login(username='regular', password='test')
        order = Order.objects.first()
        order.delivery = date(2018, 12, 31)
        order.save()
        resp = self.client.get(reverse('orderlist', args=['date']))
        self.assertEqual(len(resp.context['pending']), 2)

    def test_pending_exclude_invoiced_orders(self):
        """Pending orders are not invoiced yet."""
        self.client.login(username='regular', password='test')
        order = Order.objects.first()
        for i in range(3):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        Invoice.objects.create(reference=order)
        resp = self.client.get(reverse('orderlist', args=['date']))
        self.assertEqual(len(resp.context['pending']), 2)

    def test_pending_orders(self):
        """Test the proper query for pending orders."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('orderlist', args=['date']))
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

    def test_active_timing_sum(self):
        """Test the correct sum of times in orderItems."""
        self.client.login(username='regular', password='test')
        order = Order.objects.all()[0]
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i,
                                     crop=time(5), sewing=time(3),
                                     iron=time(2))
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['active'][0].timing,
                         timedelta(0, 72000))

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

    def test_pending_total_excludes_2018_orders(self):
        """Test the proper sum of budgets."""
        self.client.login(username='regular', password='test')
        order = Order.objects.first()
        order.delivery = date(2018, 12, 31)
        order.save()
        for order in Order.objects.all():
            for i in range(3):
                OrderItem.objects.create(
                    reference=order, element=Item.objects.last())
        resp = self.client.get(reverse('orderlist', args=['date']))
        self.assertEquals(resp.context['pending_total'], 60)

    def test_pending_total_excludes_cancelled_orders(self):
        """Test the proper sum of budgets."""
        self.client.login(username='regular', password='test')
        for order in Order.objects.all():
            for i in range(3):
                OrderItem.objects.create(
                    reference=order, element=Item.objects.last())
        cancelled = Order.objects.first()
        cancelled.status = '8'
        cancelled.save()
        resp = self.client.get(reverse('orderlist', args=['date']))
        self.assertEquals(resp.context['pending_total'], 60)

    def test_pending_total_excludes_express_orders(self):
        """Test the proper sum of budgets."""
        self.client.login(username='regular', password='test')
        for order in Order.objects.all():
            for i in range(3):
                OrderItem.objects.create(
                    reference=order, element=Item.objects.last())
        express_order = Order.objects.first()
        express_order.ref_name = 'Quick'
        express_order.save()
        resp = self.client.get(reverse('orderlist', args=['date']))
        self.assertEquals(resp.context['pending_total'], 60)

    def test_pending_total_excludes_tz_orders(self):
        """Test the proper sum of budgets."""
        self.client.login(username='regular', password='test')
        for order in Order.objects.all():
            for i in range(3):
                OrderItem.objects.create(
                    reference=order, element=Item.objects.last())
        tz = Customer.objects.create(name='Trapuzarrak',
                                     city='Mungia',
                                     phone=0,
                                     cp=0)
        tz_order = Order.objects.first()
        tz_order.customer = tz
        tz_order.save()
        resp = self.client.get(reverse('orderlist', args=['date']))
        self.assertEquals(resp.context['pending_total'], 60)

    def test_pending_total_excludes_invoiced_orders(self):
        """Test the proper sum of budgets."""
        self.client.login(username='regular', password='test')
        for order in Order.objects.all():
            for i in range(3):
                OrderItem.objects.create(
                    reference=order, element=Item.objects.last())
        Invoice.objects.create(reference=Order.objects.first())
        resp = self.client.get(reverse('orderlist', args=['date']))
        self.assertEquals(resp.context['pending_total'], 60)

    def test_pending_total(self):
        """Test the proper sum of budgets."""
        self.client.login(username='regular', password='test')
        for order in Order.objects.all():
            for i in range(3):
                OrderItem.objects.create(
                    reference=order, element=Item.objects.last())
        resp = self.client.get(reverse('orderlist', args=['date']))
        self.assertEquals(resp.context['pending_total'], 90)

    def test_pending_total_type_error_raising(self):
        """Avoid TypeError raising.

        When there's only one order with no budget & no prepaid a TypeError
        is raised.
        """
        self.client.login(username='regular', password='test')
        the_one, delete, and_delete = Order.objects.all()
        delete.delete()
        and_delete.delete()
        self.assertEqual(len(Order.objects.all()), 1)
        the_one.budget = 0.00
        the_one.prepaid = 0.00
        the_one.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEquals(resp.context['pending_total'], 0)

    def test_this_week_active(self):
        """Test the proper display of this week orders."""
        self.client.login(username='regular', password='test')
        this, next, future = Order.objects.all()
        this.delivery = date.today()
        this.save()
        next.delivery = date.today() + timedelta(days=7)
        next.save()
        future.delivery = date.today() + timedelta(days=30)
        future.save()

        this = Order.objects.get(pk=this.pk)
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEquals(len(resp.context['this_week_active']), 1)
        self.assertEquals(resp.context['this_week_active'][0], this)

    def test_this_week_active_excludes_delivered_and_cancelled(self):
        """This week entries should exclude statuses 7&8."""
        self.client.login(username='regular', password='test')
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
        self.assertEqual(resp.context['this_week_active'][0].ref_name,
                         'active')

    def test_i_relax_does_not_raise_error(self):
        """Test picking the icon does not raise index error."""
        self.client.login(username='regular', password='test')
        for i in range(20):  # big enough
            resp = self.client.get(reverse('orderlist',
                                           kwargs={'orderby': 'date'}))
            if resp.context['i_relax'] not in settings.RELAX_ICONS:
                raise ValueError('Not in list')

    def test_active_calendar_excludes_delivered_and_cancelled(self):
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
        self.assertEqual(resp.context['active_calendar'][0].ref_name, 'active')

    def test_active_calendar_includes_tz_orders(self):
        """Active orders do not include tz, but active_calendar does so."""
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
        self.assertEqual(len(resp.context['active_calendar']), 3)

    def test_active_sorting_by_date(self):
        """Test the proper sorting of active orders."""
        self.client.login(username='regular', password='test')
        newer, older, excluded = Order.objects.all()

        older.delivery = older.delivery - timedelta(days=1)
        older.save()

        excluded.status = '8'
        excluded.save()

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        newer = Order.objects.get(pk=newer.pk)
        older = Order.objects.get(pk=older.pk)

        # first active orders
        self.assertEqual(len(resp.context['active']), 2)
        self.assertEqual(resp.context['active'][0], older)
        self.assertEqual(resp.context['active'][1], newer)

        # Now the calendar ones
        self.assertEqual(len(resp.context['active_calendar']), 2)
        self.assertEqual(resp.context['active_calendar'][0], older)
        self.assertEqual(resp.context['active_calendar'][1], newer)

    def test_active_sorting_by_status(self):
        """Should be sorted from 1 to 6."""
        self.client.login(username='regular', password='test')
        user = User.objects.all()[0]
        customer = Customer.objects.all()[0]
        status = 1
        for order in Order.objects.all():
            order.status = str(status)
            order.ref_name = 'Test%s' % status
            order.save()
            status += 1

        self.assertEqual(len(Order.objects.all()), 3)

        for i in range(4, 7):
            Order.objects.create(user=user,
                                 customer=customer,
                                 ref_name='Test%s' % i,
                                 delivery=date.today(),
                                 status=str(i),
                                 budget=100,
                                 prepaid=100)

        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'status'}))

        for i in range(1, 7):
            self.assertEqual(resp.context['active'][i - 1].ref_name,
                             'Test%s' % i)
            self.assertEqual(resp.context['active_calendar'][i - 1].ref_name,
                             'Test%s' % i)

    def test_active_sorting_by_priority(self):
        """Test the proper sorting by priority."""
        self.client.login(username='regular', password='test')
        low, mid, hi = Order.objects.all()
        low.priority = '3'
        low.save()
        mid.priority = '2'
        mid.save()
        hi.priority = '1'
        hi.save()
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'priority'}))
        for var in ('active', 'active_calendar'):
            self.assertEqual(resp.context[var][0].priority, '1')
            self.assertEqual(resp.context[var][1].priority, '2')
            self.assertEqual(resp.context[var][2].priority, '3')

    def test_no_valid_sorting_method_raises_404(self):
        """A valid sorting method is required."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'void'}))
        self.assertEqual(resp.status_code, 404)

    def test_cur_user(self):
        """Test the proper show of current user."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['user'].username, 'regular')

    def test_context_vars(self):
        """Test the remaining context vars (fixed)."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('orderlist',
                                       kwargs={'orderby': 'date'}))
        self.assertEqual(resp.context['version'], settings.VERSION)
        self.assertEqual(resp.context['placeholder'],
                         'Buscar pedido (referencia o nº)')
        self.assertEqual(resp.context['search_on'], 'orders')
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Pedidos')
        self.assertEqual(resp.context['colors'], settings.WEEK_COLORS)


class OrderExpressTests(TestCase):
    """Test the order express view."""

    @classmethod
    def setUpTestData(self):
        """Create all the elements at once."""
        user = User.objects.create_user(username='regular', password='test')
        user.save()

        Customer.objects.create(
            name='Test', city='Bilbao', phone=0, cp=48003)
        Item.objects.create(name='Test', fabrics=5, price=10)

    def test_pk_out_of_range_raises_404(self):
        """Raise a 404 when trying to select a void order."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('order_express', args=[5000]))
        self.assertEqual(resp.status_code, 404)

    def test_regular_orders_should_be_redirected(self):
        """Redirect to order view with regular orders."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='Test', delivery=date.today(),
            budget=0, prepaid=0, )
        resp = self.client.get(reverse('order_express', args=[order.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_items_belong_to_the_order(self):
        """Dsiplay all the items that are owned by an order."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        regular_order = Order.objects.create(
            user=user, customer=c, ref_name='Test', delivery=date.today(),
            budget=0, prepaid=0, )
        excluded_item = OrderItem.objects.create(
            reference=regular_order, element=Item.objects.last()
        )
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')
        included_item = OrderItem.objects.create(
            reference=order_express, element=Item.objects.last())

        resp = self.client.get(
            reverse('order_express', args=[order_express.pk]))
        self.assertEqual(resp.context['items'].count(), 1)
        for i in resp.context['items']:
            self.assertNotEqual(i, excluded_item)
            self.assertEqual(i, included_item)

    def test_get_already_invoiced_orders(self):
        """Test the proper display of invoiced orders."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')

        resp = self.client.get(
            reverse('order_express', args=[order_express.pk]))
        self.assertFalse(resp.context['invoiced'])

        OrderItem.objects.create(
            reference=order_express, element=Item.objects.last(), price=10)
        Invoice.objects.create(reference=order_express)
        resp = self.client.get(
            reverse('order_express', args=[order_express.pk]))
        self.assertTrue(resp.context['invoiced'])

    def test_total_amount(self):
        """Test the proper sum of ticket."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')
        item = Item.objects.last()
        OrderItem.objects.create(
            reference=order_express, element=item, price=10, qty=3)
        OrderItem.objects.create(
            reference=order_express, element=item, price=20, qty=2)
        resp = self.client.get(
            reverse('order_express', args=[order_express.pk]))
        self.assertEqual(resp.context['order'].total, 70)

    def test_context_vars(self):
        """Test the remaining context vars."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')
        resp = self.client.get(
            reverse('order_express', args=[order_express.pk]))
        self.assertEqual(resp.context['user'].username, 'regular')
        self.assertEqual(len(resp.context['item_types']), 19)
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Venta express')
        self.assertEqual(resp.context['placeholder'], 'Busca un nombre')
        self.assertEqual(resp.context['search_on'], 'items')

        # CRUD actions
        self.assertEqual(resp.context['btn_title_add'], 'Nueva prenda')
        self.assertEqual(resp.context['js_action_add'], 'object-item-add')
        self.assertEqual(
            resp.context['js_action_delete'], 'order-express-item-delete')
        self.assertEqual(resp.context['js_data_pk'], '0')


class InvoicesListTest(TestCase):
    """Test the invoices list."""

    @classmethod
    def setUpTestData(self):
        """Create the necessary items on database at once."""
        user = User.objects.create_user(username='regular', password='test')
        user.save()

        Customer.objects.create(
            name='Test', city='Bilbao', phone=0, cp=48003)
        Item.objects.create(name='Test', fabrics=5, price=10)

    def test_invoices_view_only_displays_last_ten_invoices(self):
        """Test that view only displays 10 invoices, the last 10."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        for i in range(22):
            order = Order.objects.create(
                user=user, customer=c, ref_name='Test', delivery=date.today(),
                budget=0, prepaid=0, )
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            Invoice.objects.create(reference=order)
        resp = self.client.get(reverse('invoiceslist'))
        invoices = resp.context['invoices']
        self.assertEqual(invoices.count(), 20)
        self.assertTrue(invoices[0].invoice_no > invoices[1].invoice_no)
        self.assertTrue(invoices[0].issued_on > invoices[1].issued_on)

    def test_invoices_today_displays_today_invoices(self):
        """Test display today's invoices and their total amount."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        for i in range(10):
            order = Order.objects.create(
                user=user, customer=c, ref_name='Test', delivery=date.today(),
                budget=0, prepaid=0, )
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            Invoice.objects.create(reference=order)
        card, transfer = Invoice.objects.all()[:2]
        card.pay_method, transfer.pay_method = 'V', 'T'
        card.save()
        transfer.save()
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['today'].count(), 10)
        self.assertEqual(resp.context['today_cash']['total'], 100)
        self.assertEqual(resp.context['today_cash']['total_cash'], 80)
        self.assertEqual(resp.context['today_cash']['total_card'], 10)
        self.assertEqual(resp.context['today_cash']['total_transfer'], 10)

    def test_invoices_week_displays_week_invoices(self):
        """Test display week's invoices and their total amount."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        for i in range(10):
            order = Order.objects.create(
                user=user, customer=c, ref_name='Test', delivery=date.today(),
                budget=0, prepaid=0, )
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            Invoice.objects.create(reference=order)

        today = timezone.now().date().isocalendar()[2]
        delay = timedelta(days=randint(0, today - 1))
        for invoice in Invoice.objects.all():
            invoice.issued_on = invoice.issued_on - delay
            invoice.save()
        for invoice in Invoice.objects.all()[:5]:
            invoice.issued_on = invoice.issued_on - timedelta(days=10)
            invoice.save()
        card, transfer = Invoice.objects.reverse()[:2]
        card.pay_method, transfer.pay_method = 'V', 'T'
        card.save()
        transfer.save()
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['week'].count(), 5)
        self.assertEqual(resp.context['week_cash']['total'], 50)
        self.assertEqual(resp.context['week_cash']['total_cash'], 30)
        self.assertEqual(resp.context['week_cash']['total_card'], 10)
        self.assertEqual(resp.context['week_cash']['total_transfer'], 10)

    def test_invoices_month_displays_month_invoices(self):
        """Test display month's invoices and their total amount."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        for i in range(10):
            order = Order.objects.create(
                user=user, customer=c, ref_name='Test', delivery=date.today(),
                budget=0, prepaid=0, )
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            Invoice.objects.create(reference=order)
        for invoice in Invoice.objects.all()[:5]:
            invoice.issued_on = invoice.issued_on - timedelta(days=30)
            invoice.save()
        card, transfer = Invoice.objects.reverse()[:2]
        card.pay_method, transfer.pay_method = 'V', 'T'
        card.save()
        transfer.save()
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['month'].count(), 5)
        self.assertEqual(resp.context['month_cash']['total'], 50)
        self.assertEqual(resp.context['month_cash']['total_cash'], 30)
        self.assertEqual(resp.context['month_cash']['total_card'], 10)
        self.assertEqual(resp.context['month_cash']['total_transfer'], 10)

    def test_invoices_view_current_user(self):
        """Test the current user."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='Test', delivery=date.today(),
            budget=0, prepaid=0, )
        OrderItem.objects.create(
            reference=order, element=Item.objects.last())
        Invoice.objects.create(reference=order)
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['user'].username, 'regular')

    def test_invoices_view_title(self):
        """Test the window title."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='Test', delivery=date.today(),
            budget=0, prepaid=0, )
        OrderItem.objects.create(
            reference=order, element=Item.objects.last())
        Invoice.objects.create(reference=order)
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Facturas')

    def test_invoices_template_used(self):
        """Test the window title."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='Test', delivery=date.today(),
            budget=0, prepaid=0, )
        OrderItem.objects.create(
            reference=order, element=Item.objects.last())
        Invoice.objects.create(reference=order)
        resp = self.client.get(reverse('invoiceslist'))
        self.assertTemplateUsed(resp, 'tz/invoices.html')


class PQueueManagerTests(TestCase):
    """Test the pqueue manager view."""

    def setUp(self):
        """Create the necessary items on database at once."""
        # Create a user
        user = User.objects.create_user(username='regular', password='test')

        # Create a customer
        customer = Customer.objects.create(name='Customer Test',
                                           address='This computer',
                                           city='No city',
                                           phone='666666666',
                                           email='customer@example.com',
                                           CIF='5555G',
                                           notes='Default note',
                                           cp='48100')
        # Create an order
        order = Order.objects.create(user=user,
                                     customer=customer,
                                     ref_name='Test order',
                                     delivery=date.today(),
                                     budget=2000,
                                     prepaid=0)
        for i in range(1, 3):
            Item.objects.create(name='Test item%s' % i, fabrics=5)

        # Create orderitems
        for item in Item.objects.all():
            OrderItem.objects.create(reference=order, element=item)

        self.client.login(username='regular', password='test')

    def test_view_exists(self):
        """First test the existence of pqueue view."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/pqueue_manager.html')

    def test_available_items_exclude_delivered_and_cancelled_orders(self):
        """The list only includes active orders."""
        for i in range(2):
            order = Order.objects.create(user=User.objects.first(),
                                         customer=Customer.objects.first(),
                                         ref_name='Void order',
                                         delivery=date.today(),
                                         status=i + 7, budget=0, prepaid=0)
            OrderItem.objects.create(reference=order,
                                     element=Item.objects.first())

        resp = self.client.get(reverse('pqueue_manager'))
        for item in resp.context['available']:
            self.assertEqual(item.reference.ref_name, 'Test order')

    def test_available_items_exclude_stock_items(self):
        """The list only includes production items."""
        self.assertEqual(OrderItem.objects.all().count(), 3)
        stock_item = OrderItem.objects.first()
        stock_item.stock = True
        stock_item.description = 'Stocked item'
        stock_item.save()

        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(len(resp.context['available']), 2)
        for item in resp.context['available']:
            self.assertNotEqual(item.description, 'Stocked item')

    def test_available_items_exclude_items_already_queued(self):
        """The list only includes items that aren't yet in the queue."""
        self.assertEqual(OrderItem.objects.all().count(), 3)
        queued_item = OrderItem.objects.first()
        queued_item.description = 'Queued item'
        queued_item.save()

        PQueue.objects.create(item=queued_item)

        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(len(resp.context['available']), 2)
        for item in resp.context['available']:
            self.assertNotEqual(item.description, 'Queued item')

    def test_available_items_sort_by_delivery(self):
        """Sort by delivery, then by ref_name."""
        delivery = date.today() + timedelta(days=1)
        order = Order.objects.create(user=User.objects.first(),
                                     customer=Customer.objects.first(),
                                     ref_name='Future order',
                                     delivery=delivery,
                                     budget=0, prepaid=0)
        OrderItem.objects.bulk_create([
            OrderItem(reference=order, element=Item.objects.first(), price=0),
            OrderItem(reference=order, element=Item.objects.last(), price=0),
        ])
        orders = Order.objects.all()
        self.assertEqual(orders.count(), 2)
        resp = self.client.get(reverse('pqueue_manager'))
        for item in resp.context['available'][:3]:
            self.assertEqual(item.reference.ref_name, 'Test order')
        for item in resp.context['available'][3:5]:
            self.assertEqual(item.reference.ref_name, 'Future order')

    def test_available_items_sort_by_ref_name(self):
        """On equal delivery, sort by ref_name."""
        order = Order.objects.create(user=User.objects.first(),
                                     customer=Customer.objects.first(),
                                     ref_name='Future order',
                                     delivery=date.today(),
                                     budget=0, prepaid=0)
        OrderItem.objects.bulk_create([
            OrderItem(reference=order, element=Item.objects.first(), price=0),
            OrderItem(reference=order, element=Item.objects.last(), price=0),
        ])
        orders = Order.objects.all()
        self.assertEqual(orders.count(), 2)
        resp = self.client.get(reverse('pqueue_manager'))
        for item in resp.context['available'][:2]:
            self.assertEqual(item.reference.ref_name, 'Future order')
        for item in resp.context['available'][2:5]:
            self.assertEqual(item.reference.ref_name, 'Test order')

    def test_queued_items_exclude_delivered_and_cancelled_orders(self):
        """The queue only shows active order items."""
        for i in range(2):
            order = Order.objects.create(user=User.objects.first(),
                                         customer=Customer.objects.first(),
                                         ref_name='Void order',
                                         delivery=date.today(),
                                         status=i + 7, budget=0, prepaid=0)
            OrderItem.objects.create(reference=order,
                                     element=Item.objects.first())

        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        resp = self.client.get(reverse('pqueue_manager'))
        for item in resp.context['active']:
            self.assertEqual(item.item.reference.ref_name, 'Test order')

    def test_queued_items_active_and_completed(self):
        """Active items are positive scored, while completed are negative."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        completed_item = PQueue.objects.first()
        completed_item.complete()
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(len(resp.context['active']), 2)
        self.assertEqual(len(resp.context['completed']), 1)

    def test_i_relax_does_not_raise_error(self):
        """Test picking the icon does not raise index error."""
        self.client.login(username='regular', password='test')
        for i in range(20):  # big enough
            resp = self.client.get(reverse('pqueue_manager'))
            if resp.context['i_relax'] not in settings.RELAX_ICONS:
                raise ValueError('Not in list')


class PQueueTabletTests(TestCase):
    """Test the pqueue tablet view."""

    def setUp(self):
        """Create the necessary items on database at once."""
        # Create a user
        user = User.objects.create_user(username='regular', password='test')

        # Create a customer
        customer = Customer.objects.create(name='Customer Test',
                                           address='This computer',
                                           city='No city',
                                           phone='666666666',
                                           email='customer@example.com',
                                           CIF='5555G',
                                           notes='Default note',
                                           cp='48100')
        # Create an order
        order = Order.objects.create(user=user,
                                     customer=customer,
                                     ref_name='Test order',
                                     delivery=date.today(),
                                     budget=2000,
                                     prepaid=0)
        for i in range(1, 3):
            Item.objects.create(name='Test item%s' % i, fabrics=5)

        # Create orderitems
        for item in Item.objects.all():
            OrderItem.objects.create(reference=order, element=item)

        self.client.login(username='regular', password='test')

    def test_view_exists(self):
        """First test the existence of pqueue tablet view."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/pqueue_tablet.html')

    def test_queued_items_exclude_delivered_and_cancelled_orders(self):
        """The queue only shows active order items."""
        for i in range(2):
            order = Order.objects.create(user=User.objects.first(),
                                         customer=Customer.objects.first(),
                                         ref_name='Void order',
                                         delivery=date.today(),
                                         status=i + 7, budget=0, prepaid=0)
            OrderItem.objects.create(reference=order,
                                     element=Item.objects.first())

        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        resp = self.client.get(reverse('pqueue_tablet'))
        for item in resp.context['active']:
            self.assertEqual(item.item.reference.ref_name, 'Test order')

    def test_queued_items_active_and_completed(self):
        """Active items are positive scored, while completed are negative."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        completed_item = PQueue.objects.first()
        completed_item.complete()
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertEqual(len(resp.context['active']), 2)
        self.assertEqual(len(resp.context['completed']), 1)

    def test_i_relax_does_not_raise_error(self):
        """Test picking the icon does not raise index error."""
        self.client.login(username='regular', password='test')
        for i in range(20):  # big enough
            resp = self.client.get(reverse('pqueue_tablet'))
            if resp.context['i_relax'] not in settings.RELAX_ICONS:
                raise ValueError('Not in list')


class PQueueActionsTests(TestCase):
    """Test the AJAX server side."""

    def setUp(self):
        """Create the necessary items on database at once."""
        # Create a user
        user = User.objects.create_user(username='regular', password='test')

        # Create a customer
        customer = Customer.objects.create(name='Customer Test',
                                           address='This computer',
                                           city='No city',
                                           phone='666666666',
                                           email='customer@example.com',
                                           CIF='5555G',
                                           notes='Default note',
                                           cp='48100')
        # Create an order
        order = Order.objects.create(user=user,
                                     customer=customer,
                                     ref_name='Test order',
                                     delivery=date.today(),
                                     budget=2000,
                                     prepaid=0)
        item = Item.objects.create(name='Test item object', fabrics=5)

        # Create orderitems
        for i in range(3):
            OrderItem.objects.create(reference=order, element=item)

        self.client.login(username='regular', password='test')

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

    def test_valid_method(self):
        """Only post method is accepted."""
        item = OrderItem.objects.first()
        resp = self.client.get(reverse('queue-actions'),
                               {'pk': item.pk, 'action': 'send'})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.content.decode('utf-8'),
                         'The request should go in a post method')

    def test_no_pk_or_no_action_raise_500(self):
        """Ensure that action and pk are sent with the request."""
        item = OrderItem.objects.first()
        resp_no_pk = self.client.post(reverse('queue-actions'),
                                      {'action': 'send'})
        resp_no_action = self.client.post(reverse('queue-actions'),
                                          {'pk': item.pk})
        self.assertEqual(resp_no_pk.status_code, 500)
        self.assertEqual(resp_no_pk.content.decode('utf-8'),
                         'POST data was poor')
        self.assertEqual(resp_no_action.status_code, 500)
        self.assertEqual(resp_no_action.content.decode('utf-8'),
                         'POST data was poor')

    def test_valid_actions(self):
        """Only certain actions are possible."""
        item = OrderItem.objects.first()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': item.pk, 'action': 'invalid'})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.content.decode('utf-8'),
                         'The action was not recognized')

    def test_pk_out_of_range_raises_404(self):
        """Test the correct pk."""
        actions = ('send', 'back', 'up', 'down', 'top', 'bottom', 'complete',
                   'uncomplete')
        for action in actions:
            resp = self.client.post(reverse('queue-actions'),
                                    {'pk': 2000, 'action': action})
            self.assertEqual(resp.status_code, 404)

    def test_send_action_valid(self):
        """Test the correct process of send action."""
        item = OrderItem.objects.first()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': item.pk, 'action': 'send',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertTrue(data['reload'])
        self.assertFalse(data['html_id'])
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.all().count(), 1)

    def test_send_action_rejected(self):
        """Test the correct process of send action."""
        item = OrderItem.objects.first()
        item.stock = True
        item.save()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': item.pk, 'action': 'send',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertFalse(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['error'], 'Couldn\'t save the object')
        self.assertEqual(PQueue.objects.all().count(), 0)

    def test_back_action_valid(self):
        """Test the correct send back to item list."""
        item = PQueue.objects.create(item=OrderItem.objects.first())
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': item.pk, 'action': 'back',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertTrue(data['reload'])
        self.assertFalse(data['html_id'])
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.all().count(), 0)

    def test_up_action_valid(self):
        """Test the correct process of up action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': last.pk, 'action': 'up',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['html_id'], '#pqueue-list')
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.first(), first)
        self.assertEqual(PQueue.objects.last(), mid)

    def test_up_action_rejected(self):
        """Test the correct process of up action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        stocked_item = OrderItem.objects.last()
        stocked_item.stock = True
        stocked_item.save()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': last.pk, 'action': 'up',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertFalse(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['error'], 'Couldn\'t clean the object')
        self.assertEqual(PQueue.objects.all().count(), 3)

    def test_top_action_valid(self):
        """Test the correct process of top action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': last.pk, 'action': 'top',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['html_id'], '#pqueue-list')
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.first(), last)
        self.assertEqual(PQueue.objects.last(), mid)

    def test_top_action_rejected(self):
        """Test the correct process of top action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        stocked_item = OrderItem.objects.last()
        stocked_item.stock = True
        stocked_item.save()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': last.pk, 'action': 'top',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertFalse(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['error'], 'Couldn\'t clean the object')
        self.assertEqual(PQueue.objects.all().count(), 3)

    def test_down_action_valid(self):
        """Test the correct process of down action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'down',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['html_id'], '#pqueue-list')
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.first(), mid)
        self.assertEqual(PQueue.objects.last(), last)

    def test_down_action_rejected(self):
        """Test the correct process of down action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        stocked_item = OrderItem.objects.first()
        stocked_item.stock = True
        stocked_item.save()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'down',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertFalse(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['error'], 'Couldn\'t clean the object')
        self.assertEqual(PQueue.objects.all().count(), 3)

    def test_bottom_action_valid(self):
        """Test the correct process of bottom action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'bottom',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['html_id'], '#pqueue-list')
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.first(), mid)
        self.assertEqual(PQueue.objects.last(), first)

    def test_bottom_action_rejected(self):
        """Test the correct process of bottom action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        stocked_item = OrderItem.objects.first()
        stocked_item.stock = True
        stocked_item.save()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'bottom',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertFalse(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['error'], 'Couldn\'t clean the object')
        self.assertEqual(PQueue.objects.all().count(), 3)

    def test_complete_action_valid(self):
        """Test the correct process of complete action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'complete',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['html_id'], '#pqueue-list')
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.filter(score__lt=0).count(), 1)

    def test_tablet_complete_action_valid(self):
        """Test the correct process of complete action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'tb-complete',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertEqual(data['template'], 'tz/pqueue_tablet.html')
        self.assertFalse(data['reload'])
        self.assertEqual(data['html_id'], '#pqueue-list-tablet')
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.filter(score__lt=0).count(), 1)

    def test_complete_action_rejected(self):
        """Test the correct process of complete action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        stocked_item = OrderItem.objects.first()
        stocked_item.stock = True
        stocked_item.save()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'complete',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertFalse(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['error'], 'Couldn\'t clean the object')
        self.assertEqual(PQueue.objects.all().count(), 3)
        self.assertFalse(PQueue.objects.filter(score__lt=0).count())

    def test_uncomplete_action_valid(self):
        """Test the correct process of uncomplete action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        first.complete()
        self.assertEqual(PQueue.objects.filter(score__lt=0).count(), 1)
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'uncomplete',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['html_id'], '#pqueue-list')
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.filter(score__lt=0).count(), 0)

    def test_tablet_uncomplete_action_valid(self):
        """Test the correct process of uncomplete action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        first.complete()
        self.assertEqual(PQueue.objects.filter(score__lt=0).count(), 1)
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'tb-uncomplete',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'tz/pqueue_tablet.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertTrue(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['html_id'], '#pqueue-list-tablet')
        self.assertFalse(data['error'])
        self.assertEqual(PQueue.objects.filter(score__lt=0).count(), 0)

    def test_uncomplete_action_rejected(self):
        """Test the correct process of uncomplete action."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        first.complete()
        self.assertEqual(PQueue.objects.filter(score__lt=0).count(), 1)
        stocked_item = OrderItem.objects.first()
        stocked_item.stock = True
        stocked_item.save()
        resp = self.client.post(reverse('queue-actions'),
                                {'pk': first.pk, 'action': 'uncomplete',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertEqual(data['template'], 'includes/pqueue_list.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertFalse(data['is_valid'])
        self.assertFalse(data['reload'])
        self.assertEqual(data['error'], 'Couldn\'t clean the object')
        self.assertEqual(PQueue.objects.all().count(), 3)
        self.assertEqual(PQueue.objects.filter(score__lt=0).count(), 1)


class OrderViewTests(TestCase):
    """Test the order view."""

    def setUp(self):
        """Create the elements at once."""
        user = User.objects.create_user(username='regular', password='test')
        user.save()

        customer = Customer.objects.create(
            name='Test', city='Bilbao', phone=0, cp=48003)
        Order.objects.create(
            customer=customer, user=user, ref_name='Test',
            delivery=date.today(), budget=100, prepaid=0, )

        self.client.login(username='regular', password='test')

    def test_pk_out_of_range_raises_404(self):
        """Raise a 404 when no order is matched."""
        resp = self.client.get(reverse('order_view', args=[5000]))
        self.assertEqual(resp.status_code, 404)

    def test_express_orders_should_be_redirected(self):
        """The are displayed as order_express view."""
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')
        resp = self.client.get(reverse(
            'order_view', args=[order_express.pk]))
        url = reverse('order_express', args=[order_express.pk])
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, url)

    def test_show_comments(self):
        """Display the correct comments."""
        order = Order.objects.first()
        user = User.objects.first()
        for i in range(3):
            Comment.objects.create(reference=order, comment='Test', user=user)

        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEquals(resp.context['comments'].count(), 3)
        self.assertTrue(
            resp.context['comments'][0].creation >
            resp.context['comments'][1].creation)

    def test_show_items(self):
        """Display the correct items."""
        order = Order.objects.first()
        item = Item.objects.create(name='Test', fabrics=5)
        for i in range(3):
            OrderItem.objects.create(reference=order, element=item)
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEquals(resp.context['items'].count(), 3)

    def test_closed_orders(self):
        """Closed status."""
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertFalse(resp.context['closed'])
        order.status = 7
        order.prepaid = order.budget
        order.save()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertTrue(resp.context['closed'])

    def test_context_variables(self):
        """Test the remaining variables."""
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEquals(resp.context['user'].username, order.user.username)
        self.assertEquals(resp.context['title'], 'TrapuZarrak · Ver Pedido')
        self.assertEquals(resp.context['btn_title_add'], 'Añadir prenda')
        self.assertEquals(resp.context['js_action_add'], 'order-item-add')
        self.assertEquals(resp.context['js_action_edit'], 'order-item-edit')
        self.assertEquals(
            resp.context['js_action_delete'], 'order-item-delete')
        self.assertEquals(resp.context['js_data_pk'], order.pk)


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
        for customer in range(10):
            Customer.objects.create(name='Customer%s' % customer,
                                    address='This computer',
                                    city='No city',
                                    phone='666666666',
                                    email='customer%s@example.com' % customer,
                                    CIF='5555G',
                                    cp='48100')

        # Create some orders
        for order in range(20):
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
        for comment in range(10):
            if comment % 2:
                user = regular
            else:
                user = another
            order = Order.objects.get(ref_name='example0')
            Comment.objects.create(user=user,
                                   reference=order,
                                   comment='Comment%s' % comment)

        # Create some items
        for item in range(5):
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

    def test_customer_list(self):
        """Test the main features on customer list."""
        resp = self.client.get(reverse('customerlist'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/list_view.html')

        ctx = resp.context
        self.assertEqual(str(ctx['user']), 'regular')

    def test_customer_view_excludes_express_customer(self):
        """Express customer is annonymous, so ensure not appearing."""
        express = Customer.objects.first()
        express.name = 'express'
        express.save()
        resp = self.client.get(reverse('customerlist'))
        customers = resp.context['customers']
        self.assertEqual(len(customers), 9)
        for customer in customers:
            self.assertNotEqual(customer.name, 'express')

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
        customer = Customer.objects.first()
        no_orders = Order.objects.filter(customer=customer)
        self.assertEqual(len(no_orders), 0)
        item = Item.objects.create(name='Test', fabrics=1, price=10)

        orders = Order.objects.all()
        for order in orders:
            order.customer = customer
            order.prepaid = 0
            order.save()
            OrderItem.objects.create(reference=order, element=item)

        Invoice.objects.create(reference=Order.objects.first())

        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('customer_view', args=[customer.pk]))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/customer_view.html')

        self.assertEqual(len(resp.context['orders_active']), 10)
        self.assertEqual(len(resp.context['orders_delivered']), 10)
        self.assertEqual(len(resp.context['orders_cancelled']), 0)
        self.assertEqual(resp.context['orders_made'], 20)
        self.assertEqual(len(resp.context['pending']), 19)

    def test_items_view_default_item(self):
        """In the begining just one item should be on db."""
        resp = self.client.get(reverse('itemslist'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/list_view.html')

    def test_items_view_context_vars(self):
        """Test the correct context vars."""
        resp = self.client.get(reverse('itemslist'))
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Prendas')
        self.assertEqual(resp.context['h3'], 'Todas las prendas')
        self.assertEqual(resp.context['btn_title_add'], 'Añadir prenda')
        self.assertEqual(resp.context['js_action_add'], 'object-item-add')
        self.assertEqual(resp.context['js_action_edit'], 'object-item-edit')
        self.assertEqual(resp.context['js_action_delete'],
                         'object-item-delete')
        self.assertEqual(resp.context['js_data_pk'], '0')
        self.assertEquals(resp.context['version'], settings.VERSION)

    def test_mark_down_view(self):
        """Test the proper work of view."""
        resp = self.client.get(reverse('changelog'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)

    def test_mark_down_view_only_accept_get(self):
        """Method should be get."""
        resp = self.client.post(reverse('changelog'))
        self.assertEqual(resp.status_code, 404)


class SearchBoxTest(TestCase):
    """Test the standard views."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create users
        regular = User.objects.create_user(username='regular', password='test')
        regular.save()

        # Create some customers
        for customer in range(10):
            Customer.objects.create(name='Customer%s' % customer,
                                    address='This computer',
                                    city='No city',
                                    phone='66666666%s' % customer,
                                    email='customer%s@example.com' % customer,
                                    CIF='5555G',
                                    cp='48100')

        # Create some orders
        for order in range(20):
            customer = Customer.objects.first()
            # delivery = date.today() + timedelta(days=order % 5)
            Order.objects.create(user=regular,
                                 customer=customer,
                                 ref_name='example%s' % order,
                                 delivery=date.today(),
                                 prepaid=0)

    def context_vars(self, context, vars):
        """Compare the given vars with the ones in response."""
        if len(context) == len(vars):
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
        order = Order.objects.first()
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

    def test_search_on_items_no_order_pk(self):
        """Test the correct raise of 404."""
        resp = self.client.post(
            reverse('search'),
            {'search-on': 'items', 'search-obj': 'test item', 'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_search_on_items(self):
        """Test the correct item search."""
        order = Order.objects.first()
        item = Item.objects.create(name='Test', fabrics=0, price=2)
        resp = self.client.post(
            reverse('search'),
            {'search-on': 'items', 'search-obj': 'test',
             'order-pk': order.pk, 'test': True})
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('query_result', 'model', 'order_pk')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertEquals(data['template'], 'includes/search_results.html')
        self.assertEquals(data['query_result'], 1)
        self.assertEquals(data['model'], 'items')
        self.assertEquals(data['query_result_name'], item.name)


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
        if len(context) == len(vars):
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
                   'send-to-order-express',
                   'order-item-add',
                   'order-add-comment',
                   'ticket-to-invoice',
                   'order-edit',
                   'order-edit-date',
                   'customer-edit',
                   'object-item-edit',
                   'order-item-edit',
                   'pqueue-add-time',
                   'object-item-delete',
                   'order-item-delete',
                   'customer-delete',
                   'view-ticket',
                   )
        for action in actions:
            resp = self.client.get(
                reverse('actions'), {'pk': 2000, 'action': action})
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

    def test_order_express(self):
        """Test the correct process of express orders."""
        resp = self.client.get(reverse('actions'),
                               {'pk': None,
                                'action': 'order-express-add',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        vars = ('modal_title', 'pk', 'action', 'submit_btn', 'custom_form')
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
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
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
        item = Item.objects.first()
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

    def test_send_item_to_order_express(self):
        """Test context dictionaries and template."""
        item = Item.objects.first()
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'send-to-order-express',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        vars = ('item', 'modal_title', 'pk', 'order_pk', 'action',
                'submit_btn', 'custom_form')
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
        vars = ('order', 'form', 'items', 'modal_title', 'pk', 'action',
                'submit_btn', 'custom_form')
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

    def test_ticket_to_invoice(self):
        """Test context dictionaries and template."""
        order = Order.objects.first()
        item_obj = Item.objects.create(name='example', fabrics=1, price=20)
        for i in range(3):
            OrderItem.objects.create(reference=order, element=item_obj)
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk,
                                'action': 'ticket-to-invoice',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(data['template'], 'includes/regular_form.html')
        vars = ('form', 'items', 'order', 'total', 'invoiced', 'modal_title',
                'pk', 'action', 'submit_btn', 'custom_form', )
        self.assertTrue(self.context_vars(data['context'], vars))

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
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
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

    def test_pqueue_add_time(self):
        """Test context dictionaries and template."""
        item = OrderItem.objects.get(reference=Order.objects.first())
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'pqueue-add-time',
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

    def test_delete_order_express_item(self):
        """Test context dictionaries and template."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')
        item = OrderItem.objects.create(
            reference=order_express, element=Item.objects.first())
        resp = self.client.get(reverse('actions'),
                               {'pk': item.pk,
                                'action': 'order-express-item-delete',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(data['template'], 'includes/delete_confirmation.html')
        vars = ('modal_title', 'pk', 'action', 'msg', 'submit_btn', )
        self.assertTrue(self.context_vars(data['context'], vars))

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
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/delete_confirmation.html')
        vars = ('modal_title', 'pk', 'action', 'msg', 'submit_btn')
        self.assertTrue(self.context_vars(context, vars))

    def test_view_ticket(self):
        """Test the proper ticket display."""
        order = Order.objects.first()
        OrderItem.objects.create(
            element=Item.objects.first(), reference=order, price=10)
        invoice = Invoice.objects.create(reference=order)
        resp = self.client.get(reverse('actions'),
                               {'pk': invoice.pk,
                                'action': 'view-ticket',
                                'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/invoiced_ticket.html')
        vars = ('items', 'order',)
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

        order = Order.objects.get(ref_name='created')
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            data['redirect'], reverse('order_view', args=[order.pk]))

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

    def test_duplicated_order_returns_to_form_again(self):
        """Reload page when trying to save a duplicated order."""
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
        resp = self.client.post(reverse('actions'),
                                {'customer': order.customer.pk,
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
                                 'pk': 'None',
                                 'action': 'order-new',
                                 'test': True
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertFalse(data['form_is_valid'])

    def test_order_express_add_creates_new_customer(self):
        """When the customer is not yet on db."""
        self.client.post(reverse('actions'), {'cp': 0,
                                              'pk': 'None',
                                              'action': 'order-express-add', })
        customer = Customer.objects.get(name='express')
        self.assertEqual(customer.city, 'server')
        self.assertEqual(customer.phone, 0)
        self.assertEqual(customer.cp, 0)
        self.assertEqual(customer.notes, 'AnnonymousUserAutmaticallyCreated')

    def test_order_express_add_takes_existing_customer(self):
        """When customer is already on db use it."""
        Customer.objects.create(
            name='express', city='server', phone=0,
            cp=0, notes='AnnonymousUserAutmaticallyCreated'
        )
        self.client.post(reverse('actions'), {'cp': 0,
                                              'pk': 'None',
                                              'action': 'order-express-add', })
        self.assertTrue(Customer.objects.get(name='express'))

    def test_order_express_add_creates_new_order(self):
        """Test if creates a new order with the customer."""
        self.client.post(reverse('actions'), {'cp': 0,
                                              'pk': 'None',
                                              'action': 'order-express-add', })
        order = Order.objects.get(ref_name='Quick')
        self.assertEqual(order.user, User.objects.get(username='regular'))
        self.assertEqual(order.customer, Customer.objects.get(name='express'))
        self.assertEqual(order.delivery, date.today())
        self.assertEqual(order.status, '7')
        self.assertEqual(order.budget, 0)
        self.assertEqual(order.prepaid, 0)

    def test_order_express_add_redirects_to_order_express_view(self):
        """This action should redirect to the view to add items."""
        resp = self.client.post(reverse('actions'),
                                {'cp': 1000,
                                 'pk': 'None',
                                 'action': 'order-express-add',
                                 'test': True, })
        order = Order.objects.get(ref_name='Quick')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(data['redirect'],
                         reverse('order_express', args=[order.pk]))
        self.assertFalse(data['template'])

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
                   'ticket-to-invoice',
                   'order-edit',
                   'order-edit-date',
                   'customer-edit',
                   'object-item-edit',
                   'order-item-edit',
                   'pqueue-add-time',
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
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertTrue(read_comment.read)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['redirect'], reverse('main'))

    def test_order_item_add_adds_item(self):
        """Test the proper insertion of items."""
        order = Order.objects.get(ref_name='example')
        item_obj = Item.objects.all()[0]
        self.client.post(reverse('actions'), {'action': 'order-item-add',
                                              'pk': order.pk,
                                              'element': item_obj.pk,
                                              'qty': 2,
                                              'crop': 0,
                                              'sewing': 0,
                                              'iron': 0,
                                              'fit': True,
                                              'stock': True,
                                              'description': 'added item',
                                              'test': True
                                              })
        item = OrderItem.objects.get(description='added item')
        self.assertTrue(item)
        self.assertTrue(item.fit)
        self.assertTrue(item.stock)
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

    def test_ticket_to_invoice_issues_an_invoice(self):
        """Test the correct issue of invoices."""
        order = Order.objects.first()
        item_obj = Item.objects.create(name='example', fabrics=1, price=20)
        for i in range(3):
            OrderItem.objects.create(reference=order, element=item_obj)
        self.client.post(
            reverse('actions'),
            {'pk': order.pk, 'action': 'ticket-to-invoice', 'pay_method': 'V',
             'test': True})
        invoice = Invoice.objects.first()
        self.assertEqual(invoice.reference, order)
        self.assertEqual(invoice.issued_on.date(), date.today())
        self.assertEqual(invoice.invoice_no, 1)
        self.assertEqual(invoice.amount, 60)
        self.assertEqual(invoice.pay_method, 'V')

    def test_ticket_to_invoice_context_response(self):
        """Test the dictionaries and the response."""
        order = Order.objects.first()
        item_obj = Item.objects.create(name='example', fabrics=1, price=20)
        for i in range(3):
            OrderItem.objects.create(reference=order, element=item_obj)
        resp = self.client.post(
            reverse('actions'),
            {'pk': order.pk, 'action': 'ticket-to-invoice', 'pay_method': 'V',
             'test': True})
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(
            data['redirect'], reverse('invoiceslist'))

    def test_ticket_to_invoice_rejected_form(self):
        """Test when from is not valid."""
        order = Order.objects.first()
        item_obj = Item.objects.create(name='example', fabrics=1, price=20)
        for i in range(3):
            OrderItem.objects.create(reference=order, element=item_obj)
        resp = self.client.post(
            reverse('actions'),
            {'pk': order.pk, 'action': 'ticket-to-invoice',
             'pay_method': 'invalid', 'test': True})
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/regular_form.html')
        vars = ('form', 'items', 'order', 'total', 'modal_title', 'pk',
                'action', 'submit_btn', 'custom_form', )
        self.assertTrue(self.context_vars(data['context'], vars))

    def test_send_to_order_raises_error_invalid_item(self):
        """If no item is given raise a 404."""
        order = Order.objects.all()[0]
        no_item = self.client.post(reverse('actions'),
                                   {'action': 'send-to-order',
                                    'pk': 5000,
                                    'order': order.pk,
                                    'isfit': '0',
                                    'isStock': '1',
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
                                     'isStock': '1',
                                     'test': True,
                                     })
        self.assertEqual(no_order.status_code, 404)

    def test_send_to_order_raises_error_invalid_isfit(self):
        """If no valid isfit is given raise a 404."""
        item = Item.objects.all()[0]
        order = Order.objects.all()[0]
        no_order = self.client.post(reverse('actions'),
                                    {'action': 'send-to-order',
                                     'pk': item.pk,
                                     'order': order.pk,
                                     'isfit': 'invalid',
                                     'isStock': '1',
                                     'test': True,
                                     })
        self.assertEqual(no_order.status_code, 404)

    def test_send_to_order_raises_error_invalid_isStock(self):
        """If no valid isStock is given raise a 404."""
        item = Item.objects.all()[0]
        order = Order.objects.all()[0]
        no_order = self.client.post(reverse('actions'),
                                    {'action': 'send-to-order',
                                     'pk': item.pk,
                                     'order': order.pk,
                                     'isfit': '0',
                                     'isStock': 'invalid',
                                     'test': True,
                                     })
        self.assertEqual(no_order.status_code, 404)

    def test_send_to_order_isfit_and_isStock_true(self):
        """Test the correct store of fit and stock."""
        item = Item.objects.all()[0]
        order = Order.objects.all()[0]
        self.client.post(reverse('actions'), {'action': 'send-to-order',
                                              'pk': item.pk,
                                              'order': order.pk,
                                              'isfit': '1',
                                              'isStock': '1',
                                              'test': True,
                                              })
        order_item = OrderItem.objects.filter(element=item)
        order_item = order_item.filter(reference=order)
        self.assertEqual(len(order_item), 1)
        self.assertTrue(order_item[0].fit)
        self.assertTrue(order_item[0].stock)

    def test_send_to_order_isfit_and_isStock_false(self):
        """Test the correct store of fit."""
        item = Item.objects.all()[0]
        order = Order.objects.all()[0]
        self.client.post(reverse('actions'), {'action': 'send-to-order',
                                              'pk': item.pk,
                                              'order': order.pk,
                                              'isfit': '0',
                                              'isStock': '0',
                                              'test': True,
                                              })
        order_item = OrderItem.objects.filter(element=item)
        order_item = order_item.filter(reference=order)
        self.assertEqual(len(order_item), 1)
        self.assertFalse(order_item[0].fit)
        self.assertFalse(order_item[0].stock)

    def test_send_item_to_order_express_raises_404_with_item(self):
        """Raise a 404 execption when trying to pick up an invalid item."""
        resp = self.client.post(reverse('actions'),
                                {'item-pk': 5000,
                                 'action': 'send-to-order-express',
                                 'pk': None,
                                 'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_send_item_to_order_express_raises_404_with_order(self):
        """Raise a 404 execption when trying to pick up an invalid order."""
        resp = self.client.post(reverse('actions'),
                                {'item-pk': Item.objects.first().pk,
                                 'order-pk': 2000,
                                 'action': 'send-to-order-express',
                                 'pk': None,
                                 'test': True})
        self.assertEqual(resp.status_code, 404)

    def test_send_item_to_order_express_no_price_nor_qty(self):
        """Should assign 1 item and default item's price."""
        obj_item = Item.objects.first()
        obj_item.price = 2000
        obj_item.name = 'default price'
        obj_item.save()
        resp = self.client.post(reverse('actions'),
                                {'item-pk': Item.objects.first().pk,
                                 'order-pk': Order.objects.first().pk,
                                 'action': 'send-to-order-express',
                                 'pk': None,
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        orderitem = OrderItem.objects.first()
        self.assertEqual(orderitem.price, 2000)
        self.assertEqual(orderitem.qty, 1)
        self.assertTrue(orderitem.stock)
        self.assertFalse(orderitem.fit)

    def test_send_item_to_order_express_price_0(self):
        """Should assign object item's default."""
        obj_item = Item.objects.first()
        obj_item.price = 2000
        obj_item.name = 'default price'
        obj_item.save()
        resp = self.client.post(reverse('actions'),
                                {'item-pk': Item.objects.first().pk,
                                 'order-pk': Order.objects.first().pk,
                                 'action': 'send-to-order-express',
                                 'custom-price': 0,
                                 'pk': None,
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        orderitem = OrderItem.objects.first()
        self.assertEqual(orderitem.price, 2000)

    def test_send_item_to_order_express_set_default(self):
        """When set-default-price is true set this price on Item object."""
        obj_item = Item.objects.create(name='Test', fabrics=0, price=0)
        self.assertEqual(obj_item.price, 0)
        self.client.post(
            reverse('actions'), {'item-pk': obj_item.pk,
                                 'order-pk': Order.objects.first().pk,
                                 'action': 'send-to-order-express',
                                 'set-default-price': True,
                                 'custom-price': 100,
                                 'pk': None,
                                 'test': True})
        obj_item = Item.objects.get(pk=obj_item.pk)
        self.assertEqual(obj_item.price, 100)

    def test_send_item_to_order_express_context_response(self):
        """Test the correct insertion and response."""
        resp = self.client.post(reverse('actions'),
                                {'item-pk': Item.objects.first().pk,
                                 'order-pk': Order.objects.first().pk,
                                 'custom-price': 1000,
                                 'item-qty': 3,
                                 'action': 'send-to-order-express',
                                 'pk': None,
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['html_id'], '#ticket')
        self.assertEqual(data['template'], 'includes/ticket.html')
        vars = ('items', )
        self.assertTrue(self.context_vars(data['context'], vars))

        orderitem = OrderItem.objects.first()
        self.assertEqual(orderitem.price, 1000)
        self.assertEqual(orderitem.qty, 3)

    def test_obj_item_adds_item(self):
        """Test the proepr creation of item objects."""
        self.client.post(reverse('actions'), {'action': 'object-item-add',
                                              'pk': 'None',
                                              'name': 'Example Item',
                                              'item_type': '2',
                                              'item_class': 'S',
                                              'size': '4',
                                              'fabrics': 4,
                                              'price': 500,
                                              'notes': 'Custom Notes',
                                              })
        item = Item.objects.get(name='Example Item')
        self.assertEqual(item.item_type, '2')
        self.assertEqual(item.item_class, 'S')
        self.assertEqual(item.size, '4')
        self.assertEqual(item.fabrics, 4)
        self.assertEqual(item.price, 500)
        self.assertEqual(item.notes, 'Custom Notes')

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
                                 'price': 500,
                                 'notes': 'Custom Notes',
                                 'test': True,
                                 })
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/item_selector.html')
        self.assertIsInstance(context, list)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['html_id'], '#item-selector')
        vars = ('item_types', 'available_items', 'js_action_edit',
                'js_action_delete', 'js_action_send_to')
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
                                 'notes': 'Custom notes',
                                 'test': True,
                                 })
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertFalse(data['form_is_valid'])
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
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
        item = Item.objects.first()
        resp = self.client.post(reverse('actions'),
                                {'name': 'Changed name',
                                 'item_type': '2',
                                 'item_class': 'M',
                                 'size': 'X',
                                 'fabrics': 5,
                                 'price': 2000,
                                 'notes': 'Changed notes',
                                 'pk': item.pk,
                                 'action': 'object-item-edit',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('item_types', 'available_items', 'js_action_edit',
                'js_action_delete', 'js_action_send_to')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/item_selector.html')
        self.assertEqual(data['html_id'], '#item-selector')
        self.assertTrue(self.context_vars(data['context'], vars))

        # Test if the fields were Modified
        edited = Item.objects.get(name='Changed name')
        self.assertNotEqual(item.name, edited.name)
        self.assertNotEqual(item.item_type, edited.item_type)
        self.assertNotEqual(item.item_class, edited.item_class)
        self.assertNotEqual(item.size, edited.size)
        self.assertNotEqual(item.fabrics, edited.fabrics)
        self.assertNotEqual(item.price, edited.price)

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

    def test_pqueue_add_time_adds_time(self):
        """Test the correct time edition from pqueue."""
        item = OrderItem.objects.first()
        for i in (item.sewing, item.crop, item.iron):
            self.assertEqual(i, timedelta(0))
        resp = self.client.post(reverse('actions'),
                                {'iron': '2', 'crop': '2', 'sewing': '2',
                                 'pk': item.pk,
                                 'action': 'pqueue-add-time',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('active', 'completed', )
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'tz/pqueue_tablet.html')
        self.assertEqual(data['html_id'], '#pqueue-list-tablet')
        self.assertTrue(self.context_vars(data['context'], vars))

        # Test if the fields were modified
        mod_item = OrderItem.objects.get(pk=item.pk)
        for i in (mod_item.sewing, mod_item.crop, mod_item.iron):
            self.assertEqual(i, timedelta(0, 2))

    def test_pqueue_add_time_rejected_form(self):
        """Test invalid forms."""
        item = OrderItem.objects.first()
        for i in (item.sewing, item.crop, item.iron):
            self.assertEqual(i, timedelta(0))
        resp = self.client.post(reverse('actions'),
                                {'iron': '2', 'crop': 'void', 'sewing': '2',
                                 'pk': item.pk,
                                 'action': 'pqueue-add-time',
                                 'test': True
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('form', 'item', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form', )
        self.assertFalse(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/regular_form.html')
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

    def test_update_status_updates_delivery(self):
        """On changing to delivered, ensure that delivery date is updated."""
        order = Order.objects.first()
        order.delivery = date(2018, 1, 1)
        order.save()
        self.assertEqual(order.status, '1')
        self.assertEqual(order.delivery, date(2018, 1, 1))
        self.client.post(
            reverse('actions'),
            {'pk': order.pk, 'action': 'update-status', 'status': '7',
             'test': True})
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '7')
        self.assertEqual(order.delivery, date.today())

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

    def test_delete_order_express_item_deletes_item(self):
        """Test the proper deletion of items."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')
        item = OrderItem.objects.create(
            reference=order_express, element=Item.objects.first())
        self.assertTrue(OrderItem.objects.get(pk=item.pk))
        self.client.post(reverse('actions'),
                         {'pk': item.pk,
                          'action': 'order-express-item-delete',
                          'test': True})
        with self.assertRaises(ObjectDoesNotExist):
            OrderItem.objects.get(pk=item.pk)

    def test_delete_order_express_item_context_response(self):
        """Test the proper deletion of items."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')
        item = OrderItem.objects.create(
            reference=order_express, element=Item.objects.first())
        self.assertTrue(OrderItem.objects.get(pk=item.pk))
        resp = self.client.post(reverse('actions'),
                                {'pk': item.pk,
                                 'action': 'order-express-item-delete',
                                 'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/ticket.html')
        self.assertEqual(data['html_id'], '#ticket')
        vars = ('items', 'total', 'order', 'js_action_delete', 'js_data_pk', )
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
        vars = ('item_types', 'available_items', 'js_action_edit',
                        'js_action_delete', 'js_action_send_to')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/item_selector.html')
        self.assertEqual(data['html_id'], '#item-selector')
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

    def test_delete_customer_returns_to_customer_list(self):
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
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['redirect'], reverse('customerlist'))

    def test_logout_succesfull(self):
        """Test the proper logout from app."""
        resp = self.client.post(reverse('actions'), {'pk': None,
                                                     'action': 'logout',
                                                     'test': True})
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('login'))


class ItemSelectorTests(TestCase):
    """Test the item selector AJAX view."""

    @classmethod
    def setUpTestData(self):
        """Create all the elements at once."""
        user = User.objects.create_user(username='regular', password='test')
        user.save()

        customer = Customer.objects.create(
            name='Test', city='Bilbao', phone=0, cp=48003)
        Order.objects.create(
            user=user, customer=customer, ref_name='Test',
            delivery=date.today())
        for i in range(3):
            Item.objects.create(name='Test', fabrics=5, price=10)

    def test_item_selector_only_accepts_get(self):
        """Test the proper http method."""
        with self.assertRaises(ValueError):
            self.client.post(reverse('item-selector'))

    def test_fix_context_settings(self):
        """Test the proper values."""
        resp = self.client.get(reverse('item-selector'), {'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['item_types'], settings.ITEM_TYPE[1:])
        self.assertEqual(resp.context['js_action_send_to'], 'send-to-order')
        self.assertEqual(resp.context['js_action_edit'], 'object-item-edit')
        self.assertEqual(
            resp.context['js_action_delete'], 'object-item-delete')

    def test_item_selector_gets_order(self):
        """Test the correct pickup of order on order view."""
        order = Order.objects.first()
        resp = self.client.get(
            reverse('item-selector'), {'test': True, 'aditionalpk': order.pk})
        self.assertEqual(resp.context['order'], order)
        self.assertEqual(
            resp.context['js_action_send_to'], 'send-to-order-express')

    def test_item_selector_picks_up_all_the_items(self):
        """Test the correct filter 'all' which includes Predeterminado."""
        resp = self.client.get(reverse('item-selector'), {'test': True})
        self.assertEqual(resp.context['available_items'].count(), 4)

    def test_filter_by_type(self):
        """Test the correct by type filter."""
        for i in range(3):
            Item.objects.create(name='Test%s' % i, fabrics=5, item_type='2')
        resp = self.client.get(
            reverse('item-selector'), {'test': True, 'item-type': '2'})
        self.assertEqual(resp.context['available_items'].count(), 3)
        self.assertEqual(resp.context['data_type'], ('2', 'Pantalón'))
        for i in range(3):
            self.assertEqual(resp.context['item_names'][i].name, 'Test%s' % i)

    def test_filter_by_name(self):
        """Test the correct by name filter."""
        for i in range(3):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type=str(i + 1),
                size=str(i))
        resp = self.client.get(
            reverse('item-selector'),
            {'test': True, 'item-type': '1', 'item-name': 'Test0'})
        self.assertEqual(resp.context['available_items'].count(), 1)
        self.assertEqual(resp.context['item_sizes'][0].size, '0')
        self.assertEqual(resp.context['data_name'], 'Test0')

    def test_filter_by_size(self):
        """Test the correct by size filter."""
        for i in range(3):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type=str(i + 1),
                size=str(i))
        resp = self.client.get(
            reverse('item-selector'), {'test': True,
                                       'item-type': '1',
                                       'item-name': 'Test0',
                                       'item-size': '0'})
        self.assertEqual(resp.context['available_items'].count(), 1)
        self.assertEqual(resp.context['data_size'], '0')

    def test_item_selcetor_limits_to_11(self):
        """Test the limiting results."""
        for i in range(10):
            Item.objects.create(name='Test%s' % i, fabrics=5, item_type='2')
        resp = self.client.get(reverse('item-selector'), {'test': True})
        self.assertEqual(resp.context['available_items'].count(), 11)

    def test_template_used(self):
        """Test the proper template."""
        resp = self.client.get(reverse('item-selector'), {'test': True})
        self.assertTemplateUsed(resp, 'includes/item_selector.html')

    def test_return_json(self):
        """Test the proper json return."""
        resp = self.client.get(reverse('item-selector'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)


#
#
#
#
