"""The main test suite for views. backend."""

import json
from datetime import date, timedelta, datetime
from random import randint

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse, Http404, FileResponse
from django.test import Client, TestCase, tag
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

from orders import settings
from orders.models import (
    BankMovement, Comment, Customer, Expense, Invoice, Item, Order, OrderItem,
    PQueue, Timetable, CashFlowIO)
from orders.forms import (ItemTimesForm, InvoiceForm, OrderItemNotes,
                          CashFlowIOForm, OrderItemForm, OrderForm, ItemForm, )
from orders.views import CommonContexts

from decouple import config


class CommonContextKanbanTests(TestCase):
    """Test the common vars for both AJAX and regular views."""

    def setUp(self):
        """Create the necessary items on database at once."""
        # Create a user
        u = User.objects.create_user(
            username='user', is_staff=True, is_superuser=True,)

        # Create a customer
        c = Customer.objects.create(name='Customer Test', phone=0, cp=48100)

        # Create an item
        i = Item.objects.create(name='test', fabrics=10, price=30, stocked=30)

        # Create some orders with items
        for n in range(5):
            o = Order.objects.create(
                user=u, customer=c, ref_name='test%s' % n,
                delivery=date.today(), )
            OrderItem.objects.create(reference=o, element=i, qty=n)

    def test_icebox_items_have_status_1(self):
        """Test the icebox items."""
        first = Order.objects.first()
        first.status = '2'
        first.save()

        icebox = CommonContexts.kanban()['icebox']
        self.assertEqual(icebox.count(), 4)
        for o in icebox:
            self.assertTrue(o.status == '1')

    def test_icebox_items_filter_confirmed_by_default(self):
        first = Order.objects.first()
        first.confirmed = False
        first.save()

        icebox = CommonContexts.kanban()['icebox']
        self.assertEqual(icebox.count(), 4)
        for o in icebox:
            self.assertTrue(o.confirmed)

    def test_icebox_items_filter_unconfirmed(self):
        first = Order.objects.first()
        first.confirmed = False
        first.save()

        icebox = CommonContexts.kanban(confirmed=False)['icebox']
        self.assertEqual(icebox.count(), 1)
        self.assertFalse(icebox[0].confirmed)

    def test_icebox_items_are_ordered_by_date(self):
        """Test the icebox items."""
        n = 1
        for o in Order.objects.all():
            delay = timedelta(days=n)
            o.delivery = o.delivery + delay
            o.save()
            n += 1

        icebox = CommonContexts.kanban()['icebox']
        idx = 1
        for o in icebox:
            if idx < icebox.count():
                self.assertTrue(o.delivery < icebox[idx].delivery)
                idx += 1

    def test_queued_items_have_status_2(self):
        """Test the queued items."""
        for o in Order.objects.all()[:3]:
            o.status = '2'
            o.save()

        queued = CommonContexts.kanban()['queued']
        self.assertEqual(queued.count(), 3)
        for o in queued:
            self.assertTrue(o.status == '2')

    def test_queued_items_filter_confirmed_by_default(self):
        orders = Order.objects.all()[:3]
        for o in orders:
            o.status = '2'
            o.save()

        orders[0].confirmed = False
        orders[0].save()

        queued = CommonContexts.kanban()['queued']
        self.assertEqual(queued.count(), 2)
        for o in queued:
            self.assertTrue(o.confirmed)

    def test_queued_items_filter_unconfirmed(self):
        orders = Order.objects.all()[:3]
        for o in orders:
            o.status = '2'
            o.save()

        orders[0].confirmed = False
        orders[0].save()

        queued = CommonContexts.kanban(confirmed=False)['queued']
        self.assertEqual(queued.count(), 1)
        self.assertFalse(queued[0].confirmed)

    def test_queued_items_are_ordered_by_date(self):
        """Test the queued items."""
        n = 1
        for o in Order.objects.all():
            delay = timedelta(days=n)
            o.status = '2'
            o.delivery = o.delivery + delay
            o.save()
            n += 1

        queued = CommonContexts.kanban()['queued']
        idx = 1
        for o in queued:
            if idx < queued.count():
                self.assertTrue(o.delivery < queued[idx].delivery)
                idx += 1

    def test_in_progress_items_have_status_3_4_5(self):
        """Test in_progress items."""
        n = 3
        for o in Order.objects.all()[:3]:
            o.status = n
            o.save()
            n += 1

        ip = CommonContexts.kanban()['in_progress']
        self.assertEqual(ip.count(), 3)
        for o in ip:
            self.assertTrue(o.status in ['3', '4', '5', ])

    def test_in_progress_shows_confirmed_by_default(self):
        n = 3
        for o in Order.objects.all()[:3]:
            o.status = n
            o.save()
            n += 1

        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()

        ip = CommonContexts.kanban()['in_progress']
        self.assertEqual(ip.count(), 2)

    def test_in_progress_unconfirmed(self):
        n = 3
        for o in Order.objects.all()[:3]:
            o.status = n
            o.save()
            n += 1

        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()

        ip = CommonContexts.kanban(confirmed=False)['in_progress']
        self.assertEqual(ip.count(), 1)

    def test_in_progress_items_are_ordered_by_date(self):
        """Test the queued items."""
        n = 1
        for o in Order.objects.all():
            delay = timedelta(days=n)
            o.status = '3'
            o.delivery = o.delivery + delay
            o.save()
            n += 1

        ip = CommonContexts.kanban()['in_progress']
        idx = 1
        for o in ip:
            if idx < ip.count():
                self.assertTrue(o.delivery < ip[idx].delivery)
                idx += 1

    def test_waiting_items_have_status_6(self):
        """Test the waiting items."""
        for o in Order.objects.all()[:3]:
            o.status = '6'
            o.save()

        waiting = CommonContexts.kanban()['waiting']
        self.assertEqual(waiting.count(), 3)
        for o in waiting:
            self.assertTrue(o.status == '6')

    def test_waiting_shows_confirmed_by_default(self):
        for o in Order.objects.all()[:3]:
            o.status = '6'
            o.save()

        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()

        ip = CommonContexts.kanban()['waiting']
        self.assertEqual(ip.count(), 2)

    def test_waiting_unconfirmed(self):
        for o in Order.objects.all()[:3]:
            o.status = '6'
            o.save()

        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()

        ip = CommonContexts.kanban(confirmed=False)['waiting']
        self.assertEqual(ip.count(), 1)

    def test_waiting_items_are_ordered_by_date(self):
        """Test the waiting items."""
        n = 1
        for o in Order.objects.all():
            delay = timedelta(days=n)
            o.status = '6'
            o.delivery = o.delivery + delay
            o.save()
            n += 1

        waiting = CommonContexts.kanban()['waiting']
        idx = 1
        for o in waiting:
            if idx < waiting.count():
                self.assertTrue(o.delivery < waiting[idx].delivery)
                idx += 1

    def test_done_items_have_status_7(self):
        """Test the done items."""
        for o in Order.objects.all()[:3]:
            o.status = '7'
            o.save()

        done = CommonContexts.kanban()['done']
        self.assertEqual(done.count(), 3)
        for o in done:
            self.assertTrue(o.status == '7')

    def test_done_items_shows_confirmed_by_default(self):
        """Test the done items."""
        for o in Order.objects.all()[:3]:
            o.status = '7'
            o.save()

        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()

        done = CommonContexts.kanban()['done']
        self.assertEqual(done.count(), 2)

    def test_done_items_excludes_tz(self):
        tz = Customer.objects.create(name='trapuzaRrak', cp=0, phone=0)
        a, b = Order.objects.all()[:2]
        a.customer = tz
        a.status = '7'
        a.save()

        b.status = '7'
        b.save()

        done = CommonContexts.kanban()['done']
        self.assertEqual(done.count(), 1)
        self.assertTrue(done[0].status == '7')

    def test_done_items_unconfirmed(self):
        """Test the done items."""
        for o in Order.objects.all()[:3]:
            o.status = '7'
            o.save()

        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()

        done = CommonContexts.kanban(confirmed=False)['done']
        self.assertEqual(done.count(), 1)

    def test_done_items_are_ordered_by_date(self):
        """Test the done items."""
        n = 1
        for o in Order.objects.all():
            delay = timedelta(days=n)
            o.status = '7'
            o.delivery = o.delivery + delay
            o.save()
            n += 1

        done = CommonContexts.kanban()['done']
        idx = 1
        for o in done:
            if idx < done.count():
                self.assertTrue(o.delivery < done[idx].delivery)
                idx += 1

    def test_amounts_is_a_list(self):
        """Test the type of amounts key."""
        self.assertIsInstance(CommonContexts.kanban()['amounts'], list)

    def test_icebox_amounts(self):
        """Test the aggregates for icebox orders."""
        # 30*0+30*1+30*2+30*3+30*4 = 300
        self.assertEqual(CommonContexts.kanban()['amounts'][0], 300)

    def test_queued_amounts(self):
        """Test the aggregates for queued orders."""
        for o in Order.objects.all()[1:4]:
            o.status = '2'
            o.save()

        # 30*1+30*2+30*3=180
        self.assertEqual(CommonContexts.kanban()['amounts'][1], 180)

    def test_in_progress_amounts(self):
        """Test the aggregates for queued orders."""
        n = 3
        for o in Order.objects.all()[1:4]:
            o.status = str(n)
            o.save()
            n += 1

        # 30*1+30*2+30*3=180
        self.assertEqual(CommonContexts.kanban()['amounts'][2], 180)

    def test_waiting_amounts(self):
        """Test the aggregates for queued orders."""
        for o in Order.objects.all()[1:4]:
            o.status = '6'
            o.save()

        # 30*1+30*2+30*3=180
        self.assertEqual(CommonContexts.kanban()['amounts'][3], 180)

    def test_done_amounts(self):
        """Test the aggregates for queued orders."""
        for o in Order.objects.all()[1:4]:
            o.status = '7'
            o.save()

        # 30*1+30*2+30*3=180
        self.assertEqual(CommonContexts.kanban()['amounts'][4], 180)

    def test_update_date_is_a_form_instance(self):
        """Test the type of update date key."""
        self.assertIsInstance(
            CommonContexts.kanban()['update_date'], forms.ModelForm)

    def test_estimated_times_starts_at_zero(self):
        self.assertEqual(CommonContexts.kanban()['est_times'], ['0s', '0s'])

    def test_estimated_times_is_len_2(self):
        self.assertEqual(len(CommonContexts.kanban()['est_times']), 2)

    def test_estimated_times_in_icebox(self):

        # add some times to already created orderitems (5)
        for n, item in enumerate(OrderItem.objects.all()):
            item.crop = timedelta(seconds=n+1)
            item.sewing = timedelta(minutes=n+1)
            item.iron = timedelta(hours=n+1)
            item.save()

            # adding times moves order to status '3', so go back to status '1'
            item.reference.status = '1'
            item.reference.save()

        # expected result
        sum_sec = 1+90+5400+3+180+10800+4+6+270+360+16200+21600
        est = round(sum_sec / 3600, 1)

        self.assertEqual(
            CommonContexts.kanban()['est_times'][0], '{}h'.format(est))

    def test_estimated_times_in_queued(self):
        # add some times to already created orderitems (5)
        for n, item in enumerate(OrderItem.objects.all()):
            item.crop = timedelta(seconds=n+1)
            item.sewing = timedelta(minutes=n+1)
            item.iron = timedelta(hours=n+1)
            item.save()

        for order in Order.objects.all():
            order.status = '2'
            order.save()

        # expected result
        sum_sec = 1+90+5400+3+180+10800+4+6+270+360+16200+21600
        est = round(sum_sec / 3600, 1)

        self.assertEqual(
            CommonContexts.kanban()['est_times'][1], '{}h'.format(est))


class CommonContextOrderDetails(TestCase):
    """Test the common vars for both AJAX and regular views.

    Since they require a request object, we'll test through order view.
    """

    class Request:
        """Create a dummy request to test the method."""

        def __init__(self, user):
            """Create the needed user."""
            self.user = user

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        user = User.objects.create_user(
            username='test user', is_staff=True, is_superuser=True,)

        # Instantiante the dummy request to use during the test suite
        cls.request = cls.Request(user)

        # Create a customer
        c = Customer.objects.create(name='Customer Test', phone=0, cp=48100)

        # Create an item
        i = Item.objects.create(name='test', fabrics=10, price=30)

        # Create a timetable so view doesn't throw an error
        Timetable.objects.create(user=user)

        # Create some orders with items
        for n in range(5):
            o = Order.objects.create(
                user=user, customer=c, ref_name='test%s' % n,
                delivery=date.today(), )
            OrderItem.objects.create(reference=o, element=i, qty=n)

    def test_request_is_required(self):
        msg = ('order_details() missing 1 required positional argument:' +
               ' \'request\'')
        with self.assertRaisesMessage(TypeError, msg):
            CommonContexts.order_details(pk=1)

    def test_pk_is_required(self):
        msg = ('order_details() missing 1 required positional argument:' +
               ' \'pk\'')
        with self.assertRaisesMessage(TypeError, msg):
            CommonContexts.order_details(request='dummy')

    def test_void_pk_raises_404(self):
        with self.assertRaises(Http404):
            CommonContexts.order_details(request='dummy', pk=4e4)

    def test_comments(self):
        # request = self.re
        order = Order.objects.first()
        Comment.objects.create(
            user=self.request.user, reference=order, comment='test')
        context = CommonContexts.order_details(self.request, order.pk)
        self.assertEqual(context['comments'][0].comment, 'test')

    def test_items(self):
        order = Order.objects.first()
        context = CommonContexts.order_details(self.request, order.pk)
        self.assertEqual(context['items'].count(), 1)

    def test_user(self):
        order = Order.objects.first()
        context = CommonContexts.order_details(self.request, order.pk)
        self.assertEqual(context['user'].username, self.request.user.username)

    def test_session(self):
        order = Order.objects.first()
        context = CommonContexts.order_details(self.request, order.pk)
        self.assertIsInstance(context['session'], Timetable)
        self.assertEqual(context['session'].user, self.request.user)

    def test_estimated_times(self):
        items = [Item.objects.create(
            name=s, fabrics=5, price=30, stocked=10) for s in ('a', 'b', 'c',)]

        for n, item in enumerate(items):
            OrderItem.objects.create(
                element=item, qty=10 * n + 1, reference=Order.objects.first(),
                crop=timedelta(seconds=10),
                sewing=timedelta(seconds=20),
                iron=timedelta(seconds=30), )

        # Create an order
        order = Order.objects.create(
            user=User.objects.first(),
            customer=Customer.objects.first(),
            ref_name='Current',
            delivery=date.today(), )

        OrderItem.objects.create(element=items[0], qty=5, reference=order)

        context = CommonContexts.order_details(self.request, order.pk)
        self.assertEqual(context['order_est'], ['50s', '~2m', '~2m'])
        self.assertEqual(context['order_est_total'], '~5m')

    def test_title(self):
        order = Order.objects.first()
        context = CommonContexts.order_details(self.request, order.pk)
        self.assertEqual(
            context['title'],
            f'Pedido {order.pk}: Customer Test, {order.ref_name}')

    def test_cashflowio_form(self):
        order = Order.objects.first()
        context = CommonContexts.order_details(self.request, order.pk)
        self.assertIsInstance(context['add_prepaids'], CashFlowIOForm)

    def test_static_vars(self):
        order = Order.objects.first()
        context = CommonContexts.order_details(self.request, order.pk)
        self.assertEqual(context['version'], settings.VERSION)


class CommonContextStockTabs(TestCase):
    """Test the common variables for the view and the AJAX response."""

    @classmethod
    def setUpTestData(cls):
        u = User.objects.create_user(username='foo')
        c = Customer.objects.create(name='foo', cp=0, phone=0)
        Order.objects.create(
            user=u, customer=c, ref_name='foo', delivery=date.today())

    def test_tab_elements(self):
        p1, p2, p3, zero, negative = [
            Item.objects.create(
                name='bar', fabrics=2, stocked=s) for s in (5, 15, 5, 0, 5)]

        o = Order.objects.first()
        OrderItem.objects.create(element=p1, reference=o, qty=5)  # 0 stock
        OrderItem.objects.create(element=p2, reference=o, qty=14)  # 1 stock
        OrderItem.objects.create(element=p3, reference=o, qty=1)  # 4 stock

        o.kill()

        cc = CommonContexts.stock_tabs()

        self.assertEqual(cc['tab_elements']['p1'][0], p1)
        self.assertEqual(cc['tab_elements']['p2'][0], p2)
        self.assertEqual(cc['tab_elements']['p3'][0], p3)
        self.assertEqual(cc['tab_elements']['zero'][0], zero)
        self.assertEqual(cc['tab_elements']['negative'][0], negative)

    def test_tab_item_types(self):
        cc = CommonContexts.stock_tabs()
        self.assertEqual(cc['item_types'], settings.ITEM_TYPE[1:])


class CommonContextPqueue(TestCase):
    """Test the common context variables for pqueue."""

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
            Item.objects.create(name='Test item%s' % i, fabrics=5, stocked=30)

        # Create orderitems
        for item in Item.objects.all():
            OrderItem.objects.create(reference=order, element=item)

    def test_available_items_excludes_delivered_cancelled_and_invoiced(self):
        """The list only includes active orders."""
        for s in ('6', '7', '8'):
            order = Order.objects.create(user=User.objects.first(),
                                         customer=Customer.objects.first(),
                                         ref_name='foo{}'.format(s),
                                         delivery=date.today(),
                                         status=s)
            OrderItem.objects.create(reference=order,
                                     element=Item.objects.last())

        invoiced = Order.objects.get(ref_name='foo6')
        invoiced.kill()
        self.assertEqual(invoiced.status, '9')

        context = CommonContexts.pqueue()
        self.assertEqual(OrderItem.objects.count(), 6)
        self.assertEqual(context['available'].count(), 3)
        for item in context['available']:
            self.assertEqual(item.reference.ref_name, 'Test order')

    def test_available_items_exclude_discount_items(self):
        """Discounts are excluded from list."""
        self.assertEqual(OrderItem.objects.all().count(), 3)
        item = Item.objects.first()
        item.name = 'Descuento'
        item.save()

        context = CommonContexts.pqueue()
        self.assertEqual(context['available'].count(), 2)
        for item in context['available']:
            self.assertNotEqual(item.element.name, 'Descuento')

    def test_available_items_exclude_stock_items(self):
        """The list only includes production items."""
        self.assertEqual(OrderItem.objects.all().count(), 3)
        stock_item = OrderItem.objects.first()
        stock_item.stock = True
        stock_item.description = 'Stocked item'
        stock_item.save()

        context = CommonContexts.pqueue()
        self.assertEqual(context['available'].count(), 2)
        for item in context['available']:
            self.assertNotEqual(item.description, 'Stocked item')

    def test_available_items_exclude_items_already_queued(self):
        """The list only includes items that aren't yet in the queue."""
        self.assertEqual(OrderItem.objects.all().count(), 3)
        queued_item = OrderItem.objects.first()
        queued_item.description = 'Queued item'
        queued_item.save()

        PQueue.objects.create(item=queued_item)

        context = CommonContexts.pqueue()
        self.assertEqual(context['available'].count(), 2)
        for item in context['available']:
            self.assertNotEqual(item.description, 'Queued item')

    def test_available_items_exclude_foreign(self):
        """Foreign items can't be shown in PQueue."""
        self.assertEqual(OrderItem.objects.all().count(), 3)
        queued_item = OrderItem.objects.last()
        queued_item.description = 'Foreign item'
        queued_item.element.foreing = True
        queued_item.element.save()

        context = CommonContexts.pqueue()
        self.assertEqual(context['available'].count(), 2)
        for item in context['available']:
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
        context = CommonContexts.pqueue()
        for item in context['available'][:3]:
            self.assertEqual(item.reference.ref_name, 'Test order')
        for item in context['available'][3:5]:
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
        context = CommonContexts.pqueue()
        for item in context['available'][:2]:
            self.assertEqual(item.reference.ref_name, 'Future order')
        for item in context['available'][2:5]:
            self.assertEqual(item.reference.ref_name, 'Test order')

    def test_queued_items_exclude_delivered_cancelled_and_invoiced(self):
        """The queue only shows active order items."""
        for s in ('6', '7', '8'):
            order = Order.objects.create(user=User.objects.first(),
                                         customer=Customer.objects.first(),
                                         ref_name='foo{}'.format(s),
                                         delivery=date.today(),
                                         status=s)
            OrderItem.objects.create(reference=order,
                                     element=Item.objects.last())

        invoiced = Order.objects.get(ref_name='foo6')
        invoiced.kill()
        self.assertEqual(invoiced.status, '9')

        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        context = CommonContexts.pqueue()
        for item in context['active']:
            self.assertEqual(item.item.reference.ref_name, 'Test order')

    def test_queued_items_active_and_completed(self):
        """Active items are positive scored, while completed are negative."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        completed_item = PQueue.objects.first()
        completed_item.complete()
        context = CommonContexts.pqueue()
        self.assertEqual(context['active'].count(), 2)
        self.assertEqual(context['completed'].count(), 1)

    def test_i_relax_does_not_raise_error(self):
        """Test picking the icon does not raise index error."""
        self.client.login(username='regular', password='test')
        for i in range(20):  # big enough
            context = CommonContexts.pqueue()
            if context['i_relax'] not in settings.RELAX_ICONS:
                raise ValueError('Not in list')


class PrintableTicketTests(TestCase):
    """Test the printable ticket view."""

    def setUp(self):
        """Set up the test suite."""
        u = User.objects.create_user(username='regular', password='test')
        self.client = Client()
        self.client.login(username='regular', password='test')
        c = Customer.objects.create(
            name='Test', city='Bilbao', phone=0, cp=48003)
        Item.objects.create(name='Test', fabrics=5, price=10, stocked=30)
        order = Order.objects.create(
            user=u, customer=c, ref_name='Test', delivery=date.today(),
            budget=0, prepaid=0, )
        OrderItem.objects.create(
            reference=order, element=Item.objects.last())
        order.kill()

    def test_printable_ticket_requires_login(self):
        self.client = Client()
        login_url = '/accounts/login/?next=/ticket_print%26invoice_no%253D1'
        resp = self.client.get(
            reverse('ticket_print', kwargs={'invoice_no': 1}))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)

    def test_printable_ticket_requires_valid_invoice_no(self):
        with self.assertRaises(NoReverseMatch):
            self.client.get(reverse('ticket_print'))
        with self.assertRaises(NoReverseMatch):
            self.client.get(reverse('ticket_print',
                                    kwargs={'invoice_no': 1e5}))

    def test_printable_ticket_outputs_a_file(self):
        invoice = Invoice.objects.last()
        resp = self.client.get(
            reverse('ticket_print', kwargs={'invoice_no': invoice.invoice_no}))
        self.assertIsInstance(resp, FileResponse)


class AddHoursTests(TestCase):
    """Test the add hours page."""

    def setUp(self):
        """Set up the test suite."""
        u = User.objects.create_user(username='regular', password='test')
        Timetable.objects.create(user=u)
        self.client = Client()
        self.client.login(username='regular', password='test')

    def test_not_valid_timetable_should_redirect_to_main_view(self):
        """When user has no timetable open can't add hours."""
        # first close the active timetable
        u = User.objects.first()
        active = Timetable.active.get(user=u)
        active.hours = timedelta(hours=5)
        active.save()
        # Other users' open times should not affect
        alt = User.objects.create_user(username='alt', password='test')
        Timetable.objects.create(user=alt)
        resp = self.client.get(reverse('add_hours'))
        self.assertEqual(resp.status_code, 302)

    def test_superusers_and_voyeur_are_logged_out_directly(self):
        """These users skip the process of adding hours."""
        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('add_hours'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('login'))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('add_hours'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('login'))

    def test_initial_vars(self):
        """Test the initial vars values."""
        resp = self.client.get(reverse('add_hours'))
        self.assertEqual(resp.context['cur_user'], User.objects.first())
        self.assertEqual(resp.context['version'], settings.VERSION)
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Añadir horas')

    def test_form_is_TimetableCloseForm(self):
        """Test the correct form loaded."""
        resp = self.client.get(reverse('add_hours'))
        self.assertTrue(resp.context['form'].fields['hours'])
        self.assertTrue(resp.context['form'].fields['user'])

    def test_current_day_loads_on_time_var(self):
        """Test the var on_time."""
        resp = self.client.get(reverse('add_hours'))
        self.assertTrue(resp.context['on_time'])
        t = Timetable.objects.first()
        t.start = t.start - timedelta(days=1)
        t.save()
        resp = self.client.get(reverse('add_hours'))
        with self.assertRaises(KeyError):
            resp.context['on_time']

    def test_form_is_valid_saves_object(self):
        """Test a valid POST method."""
        self.client.post(
            reverse('add_hours'), {'user': User.objects.first().pk,
                                   'hours': timedelta(hours=5), })
        self.assertEqual(Timetable.objects.first().hours, timedelta(hours=5))

    def test_form_is_valid_keeps_open_the_app(self):
        """When keep open is checked redirect to main view."""
        resp = self.client.post(
            reverse('add_hours'), {'user': User.objects.first().pk,
                                   'hours': timedelta(hours=5),
                                   'keep-open': True, })
        self.assertRedirects(resp, reverse('main'))

    def test_form_is_valid_redirects_to_login(self):
        """When keep open is not checked logout and redirect to login."""
        resp = self.client.post(
            reverse('add_hours'), {'user': User.objects.first().pk,
                                   'hours': timedelta(hours=5), })
        self.assertRedirects(resp, reverse('login'))

    def test_form_is_not_valid_returns_to_view_again(self):
        """When keep open is checked redirect to main view."""
        resp = self.client.post(
            reverse('add_hours'), {'user': User.objects.first().pk,
                                   'hours': 'void', })
        self.assertFormError(resp, 'form', 'hours', 'Enter a valid duration.')
        self.assertTemplateUsed(resp, 'registration/add_hours.html')

        resp = self.client.post(
            reverse('add_hours'), {'user': 'void',
                                   'hours': timedelta(hours=5), })
        err = ('Select a valid choice. That choice is not one of the ' +
               'available choices.')
        self.assertFormError(resp, 'form', 'user', err)
        self.assertTemplateUsed(resp, 'registration/add_hours.html')

    def test_get_method_loads_correct_template(self):
        """Test the template used on get method."""
        resp = self.client.get(reverse('add_hours'))
        self.assertTemplateUsed(resp, 'registration/add_hours.html')


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

    def test_not_logged_in_on_timetable_list(self):
        """Test not logged in users should be redirected to login."""
        login_url = '/accounts/login/?next=/timetables/'
        resp = self.client.get(reverse('timetables'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)


class MainViewTests(TestCase):
    """Test the homepage."""

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
            Order.objects.create(
                user=user, customer=customer, ref_name='Test order%s' % i,
                delivery=date.today(), inbox_date=timezone.now())
        Item.objects.create(name='test', fabrics=1, price=10, stocked=50)
        for order in Order.objects.all():
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.client.login(username='regular', password='test')

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.assertFalse(Timetable.objects.all())
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/main.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'regular')

    def test_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_timetable_required_is_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            resp = self.client.get(reverse('main'))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/main.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            resp = self.client.get(reverse('main'))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

    def test_view_exists(self):
        """Test the view exists and template used."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/main.html')

    def test_aggregates_sales_filters_current_year_incomes(self):
        """Only current year invoices are computed."""
        a, b, c = Order.objects.all()
        [o.kill() for o in (a, b)]  # relevant payments

        # Irrelevant payment
        CashFlowIO.objects.create(
            creation=timezone.now() - timedelta(days=367), amount=5, order=c)

        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][0], 20)

    def test_aggregates_year_items_filter_this_year_deliveries(self):
        """This is a common filter for confirmed, unconfirmed and tz."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 30)
        out_range = Order.objects.first()
        out_range.delivery = date(2017, 1, 1)
        out_range.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 20)

    def test_aggregates_year_items_filter_out_invoiced_orders(self):
        """This is a common filter for confirmed, unconfirmed and tz."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 30)
        Order.objects.first().kill()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 20)

    def test_aggregates_year_items_filter_out_quick_customer(self):
        """This is a common filter for confirmed, unconfirmed and tz."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 30)
        express = Order.objects.first()
        express.ref_name = 'QuIcK'
        express.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 20)

    def test_aggregates_year_items_filter_out_cancelled_orders(self):
        """This is a common filter for confirmed, unconfirmed and tz."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 30)
        cancelled = Order.objects.first()
        cancelled.status = 8
        cancelled.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 20)

    def test_aggregates_confirmed_filter_out_unconfirmed_orders(self):
        """Confirmed is confirmed."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 30)
        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 20)

    def test_aggregates_confirmed_filter_out_tz_orders(self):
        """Confirmed should exclude tz orders."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 30)
        tz = Customer.objects.create(name='TraPuZarrak', phone=0, cp=0)
        tz_order = Order.objects.first()
        tz_order.customer = tz
        tz_order.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 20)

    def test_aggregates_unconfirmed_filter_out_confirmed_orders(self):
        """Unconfirmed is unconfirmed."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][2], 0)
        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][2], 10)

    def test_aggregates_unconfirmed_filter_out_tz_orders(self):
        """Confirmed should exclude tz orders."""
        for order in Order.objects.all():
            order.confirmed = False
            order.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][2], 30)
        tz = Customer.objects.create(name='TraPuZarrak', phone=0, cp=0)
        tz_order = Order.objects.first()
        tz_order.customer = tz
        tz_order.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][2], 20)

    def test_aggregates_confirmed_multiplies_price_by_qty(self):
        """Test the correct product."""
        for item in OrderItem.objects.all():
            item.qty = 3
            item.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 90)

    def test_aggregates_unconfirmed_multiplies_price_by_qty(self):
        """Test the correct product."""
        for item in OrderItem.objects.all():
            item.qty = 3
            item.save()
        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][2], 30)

    def test_aggregates_avoid_none_type(self):
        """Empty queries return NoneType and that can't be summed."""
        for item in OrderItem.objects.all():
            item.delete()
        resp = self.client.get(reverse('main'))
        for aggregate in resp.context['aggregates'][:3]:
            self.assertEqual(aggregate, 0)

    def test_aggregates_sales_return_int(self):
        """Check the correct type."""
        [o.kill() for o in Order.objects.all()]
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][0], 30)
        self.assertIsInstance(resp.context['aggregates'][0], int)

    def test_aggregates_confirmed_returns_int(self):
        """Check the correct type."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][1], 30)
        self.assertIsInstance(resp.context['aggregates'][1], int)

    def test_aggregates_unconfirmed_returns_int(self):
        """Check the correct type."""
        unconfirmed = Order.objects.first()
        unconfirmed.confirmed = False
        unconfirmed.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][2], 10)
        self.assertIsInstance(resp.context['aggregates'][2], int)

    def test_bar(self):
        """Test the correct amounts for bar."""
        # Create one more order to have all the elements
        order = Order.objects.create(
            user=User.objects.first(),
            customer=Customer.objects.first(),
            delivery=date.today(), ref_name='Test', )
        OrderItem.objects.create(
            reference=order, element=Item.objects.last())
        sold, confirmed, unconfirmed = Order.objects.all()[:3]

        # Create also an expense
        supplier = Customer.objects.create(
            name='supplier', address='foo', city='bar', CIF='baz', phone=0,
            cp=0, provider=True)
        Expense.objects.create(
            issuer=supplier, invoice_no=0, issued_on=date.today(),
            amount=100)

        # Fetch the goal
        today, cur_year = date.today(), date.today().year
        elapsed = today - date(cur_year - 1, 12, 31)
        goal = elapsed.days * settings.GOAL

        # Set qtys to have a decent number of 'em
        qty = 100
        for item in OrderItem.objects.all():
            item.qty = qty
            item.element.stocked += qty + 5  # and enough stock
            item.element.save()
            item.save()

        # Set sold obj
        sold.kill()

        # Set unconfirmed order
        unconfirmed.confirmed = False
        unconfirmed.save()

        # Finally, test it
        resp = self.client.get(reverse('main'))
        sales, conf, unconf, exp, fut_exp, goal = resp.context['aggregates']

        relevant = (sales, exp, goal)
        mn, mx = min(relevant) * .9,  max(relevant) * 1.1
        bar_len = mx - mn

        bar = resp.context['bar']
        self.assertEqual(bar[0], round((sales - mn) * 100 / bar_len, 2))
        self.assertEqual(
            bar[1], round(((sales + conf - mn) * 100 / bar_len) - bar[0], 2))
        self.assertEqual(
            bar[2],
            round(((sales + conf + unconf - mn)*100/bar_len)-sum(bar[:2]), 2))
        self.assertEqual(bar[3], round((exp - mn) * 100 / bar_len, 2))
        self.assertEqual(
            bar[4], round(((exp + fut_exp - mn) * 100 / bar_len) - bar[3], 2))
        self.assertEqual(bar[5], round((goal - mn) * 100 / bar_len, 2))

    def test_expenses_avoid_NoneType_error(self):
        """Total should return 0 in None queries."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['aggregates'][3], 0)

    def test_tracked_times_is_none(self):
        """Created tt_ratios is None when there are no times."""
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        self.assertEqual(ratios, None)

    def test_tracked_times_excludes_stock_items(self):
        order = Order.objects.first()
        order.status = '7'
        order.save()
        item = OrderItem.objects.get(reference=order)
        item.stock = False
        item.crop = timedelta(hours=5)
        item.save()
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        self.assertEqual(ratios['crop'], 100)

        # Although crop time is 0 return None since is stock
        item.stock = True
        item.save()
        self.assertEqual(item.crop, timedelta(0))  # Stock can't have times
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        self.assertEqual(ratios, None)

    def test_tracked_time_excludes_foreign_items(self):
        order = Order.objects.first()
        order.status = '7'
        order.save()
        item = OrderItem.objects.get(reference=order)
        item.stock = False
        item.crop = timedelta(hours=5)
        item.save()
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        self.assertEqual(ratios['crop'], 100)

        base_item = Item.objects.get(pk=item.element.pk)
        base_item.foreing = True
        base_item.save()
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        self.assertEqual(ratios, None)

    def test_tracked_time_picks_status_7(self):
        a, b = Order.objects.all()[:2]
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        self.assertEqual(a.status, '1')
        self.assertEqual(b.status, '1')
        self.assertEqual(ratios, None)

        a.status = '7'
        a.save()
        b.kill()

        item = OrderItem.objects.get(reference=a)
        item.stock = False
        item.crop = timedelta(hours=5)
        item.save()
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        self.assertEqual(ratios['crop'], 50)  # 50%, b has no times

    def test_tracked_time_picks_current_year_items(self):
        order = Order.objects.first()
        order.status = '7'
        order.save()
        item = OrderItem.objects.get(reference=order)
        item.stock = False
        item.crop = timedelta(hours=5)
        item.save()
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        self.assertEqual(ratios['crop'], 100)

        order.inbox_date = timezone.now() - timedelta(days=365)
        order.save()
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        self.assertEqual(ratios, None)

    def test_tracked_time_excludes_0_times(self):
        for order in Order.objects.all():
            order.status = '7'
            order.save()

        c, s, i = OrderItem.objects.all()
        c.crop = timedelta(5)
        s.sewing = timedelta(5)
        i.iron = timedelta(5)
        c.save(), s.save(), i.save()
        resp = self.client.get(reverse('main'))
        ratios = resp.context['tt_ratio']
        for t in ('crop', 'sewing', 'iron', 'mean'):
            self.assertEqual(ratios[t], 33)

        self.assertEqual(ratios['absolute'], (1, 1, 1, 3))

    def test_active_count_box(self):
        """Test the active box."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['active'], 3)
        self.assertFalse(resp.context['active_msg'])
        order = Order.objects.first()
        order.status = 6
        order.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['active_msg'], 'Aunque hay 1 para entregar')

    def test_pending_orders_count(self):
        """This var appears on view settings."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['pending'], 3)

    def test_pending_amount_prepaid(self):
        """Test the total pending amount changing prepaids."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['pending_msg'], '30€ tenemos aún<br>por cobrar')
        CashFlowIO.objects.create(amount=5, order=Order.objects.first())
        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['pending_msg'], '25€ tenemos aún<br>por cobrar')

    def test_pending_amount_no_items(self):
        """Test the total pending amount."""
        for item in OrderItem.objects.all():
            item.delete()
        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['pending_msg'], 'Genial, tenemos todo cobrado!')

    def test_pending_no_orders(self):
        """Test the message when there are no active orders."""
        [o.kill() for o in Order.live.all()]

        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['pending_msg'], 'Genial, tenemos todo cobrado!')

    def test_outdated(self):
        """Test the proper show of outdated orders."""
        resp = self.client.get(reverse('main'))
        self.assertFalse(resp.context['outdated'])
        for order in Order.objects.all()[:2]:
            order.delivery = date.today() - timedelta(days=1)
            order.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['outdated'], 2)

    def test_balance_box_excludes_card_and_transfer(self):
        """Only cash invoices are summed."""
        pm = ('C', 'V', 'T')
        [o.kill(pay_method=pm[n]) for n, o in enumerate(Order.objects.all())]
        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['balance_msg'],
            """<h3 class="box_link_h">10.00€</h3>
            <h4 class="box_link_h">Pendientes de ingresar
            </h4>""")

    def test_balance_box_includes_negative_bank_movements(self):
        """Only positive amounts are involved."""
        [o.kill() for o in Order.objects.all()]
        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['balance_msg'],
            """<h3 class="box_link_h">30.00€</h3>
            <h4 class="box_link_h">Pendientes de ingresar
            </h4>""")
        BankMovement.objects.create(amount=-10)
        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['balance_msg'],
            """<h3 class="box_link_h">40.00€</h3>
            <h4 class="box_link_h">Pendientes de ingresar
            </h4>""")

    def test_balance_box_sums_bank_movements(self):
        """Test the correct sum of bank movements."""
        for i in range(3):
            BankMovement.objects.create(amount=50)
        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['balance_msg'],
            """<h3 class="box_link_h">150.00€</h3>
            <h4 class="box_link_h">has ingresado de más
            </h4>""")

    def test_balance_box_no_deposits_nor_cash(self):
        """Test when there are neither deposits nor invoices."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(
            resp.context['balance_msg'],
            '<h4 class="box_link_h">Estás en paz con el banco<h4>')

    def test_month_box(self):
        """Test the correct sum of month invoices."""
        a, b, c = Order.objects.all()
        [o.kill() for o in (a, b)]  # relevant payments

        # Irrelevant payment
        cf = CashFlowIO.objects.create(
            creation=timezone.now() - timedelta(days=365), amount=5, order=c)

        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['month'], 20)

        # Also irrelevant
        cf.delete()
        cf = CashFlowIO.objects.create(
            creation=timezone.now() - timedelta(days=35), amount=5, order=c)

    def test_week_box(self):
        """Test the correct sum of week invoices."""
        a, b, c = Order.objects.all()
        [o.kill() for o in (a, b)]  # relevant payments

        # Irrelevant payment
        cf = CashFlowIO.objects.create(
            creation=timezone.now() - timedelta(days=365), amount=5, order=c)

        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['week'], 20)

        # Also irrelevant
        cf.delete()
        cf = CashFlowIO.objects.create(
            creation=timezone.now() - timedelta(days=8), amount=5, order=c)

    def test_top_five_excludes_customer_express(self):
        """Express customer is for express tickets."""
        customer = Customer.objects.create(name='express', phone=5, cp=55)
        order = Order.objects.first()
        order.customer = customer
        order.save()
        [o.kill() for o in Order.objects.all()]
        active_customer = Customer.objects.get(name='Test Customer')
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['top5'][0], active_customer)
        self.assertEqual(resp.context['top5'][0].total, 20)

    def test_top_five_excludes_orders_not_invoiced(self):
        """Orders not invoiced should not count."""
        [o.kill() for o in Order.objects.all()[:2]]
        active_customer = Customer.objects.get(name='Test Customer')
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['top5'][0], active_customer)
        self.assertEqual(resp.context['top5'][0].total, 20)

    def test_top_five_multiplies_qty_by_price(self):
        """Express customer is for express tickets."""
        item = OrderItem.objects.first()
        item.qty = 5
        item.price = 30
        item.save()
        [o.kill() for o in Order.objects.all()]
        active_customer = Customer.objects.get(name='Test Customer')
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['top5'][0], active_customer)
        self.assertEqual(resp.context['top5'][0].total, 170)

    def test_top_five_displays_five_customers(self):
        """Test the number and the order."""
        for i in range(6):
            u = User.objects.first()
            c = Customer.objects.create(name='Test%s' % i, phone=i, cp=i)
            o = Order.objects.create(
                user=u, customer=c, ref_name='foo', delivery=date.today(), )
            OrderItem.objects.create(reference=o, element=Item.objects.last())
            o.kill()

        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['top5'].count(), 5)
        for i in range(4):
            self.assertTrue(resp.context['top5'][i].total >=
                            resp.context['top5'][i+1].total)

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        resp = self.client.get(reverse('main'))
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('main'))
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('main'))
        self.assertFalse(resp.context['session'])

    def test_comments(self):
        """Exclude user comments & read ones."""
        f = User.objects.create(username='foreign', password='void')
        for i in range(5):
            Comment.objects.create(
                user=f, reference=Order.objects.first(), comment='test', )
        read, own = Comment.objects.all()[:2]
        read.read = True
        read.save()
        own.user = User.objects.get(username='regular')
        own.save()
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['comments'].count(), 3)
        for i in range(2):
            self.assertTrue(resp.context['comments'][i].creation >=
                            resp.context['comments'][i+1].creation)

    def test_additional_vars(self):
        """Test the remaining vars."""
        resp = self.client.get(reverse('main'))
        self.assertEqual(resp.context['user'].username, 'regular')
        self.assertEqual(resp.context['version'], settings.VERSION)
        self.assertEqual(resp.context['search_on'], 'orders')
        self.assertEqual(
            resp.context['placeholder'], 'Buscar pedido (referencia)')
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Inicio')


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
            self.client.post(reverse('search'), {'search-on':  '',
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
        self.assertEqual(data['template'], 'includes/search_results.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertEqual(data['model'], 'orders')
        self.assertEqual(data['query_result'], 1)
        self.assertEqual(data['query_result_name'], 'example11')

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
        self.assertEqual(data['template'], 'includes/search_results.html')
        self.assertEqual(data['query_result'], 1)
        self.assertEqual(data['query_result_name'], order.ref_name)

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
        self.assertEqual(data['template'], 'includes/search_results.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertEqual(data['model'], 'customers')
        self.assertEqual(data['query_result'], 1)
        self.assertEqual(data['query_result_name'], 'Customer1')

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
        self.assertEqual(data['template'], 'includes/search_results.html')
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertEqual(data['model'], 'customers')
        self.assertEqual(data['query_result'], 1)
        self.assertEqual(data['query_result_name'], 'Customer5')

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
        self.assertEqual(data1['query_result_name'],
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
        item = Item.objects.create(name='Test', fabrics=0, price=2, stocked=30)
        resp = self.client.post(
            reverse('search'),
            {'search-on': 'items', 'search-obj': 'test',
             'order-pk': order.pk, 'test': True})
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('query_result', 'model', 'order_pk')
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(self.context_vars(data['context'], vars))
        self.assertEqual(data['template'], 'includes/search_results.html')
        self.assertEqual(data['query_result'], 1)
        self.assertEqual(data['model'], 'items')
        self.assertEqual(data['query_result_name'], item.name)


class CustomerListTests(TestCase):
    """Test the customer list view."""

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

        # Create some items
        order = Order.objects.get(ref_name='example0')
        [OrderItem.objects.create(qty=5, reference=order) for _ in range(5)]

        # deliver the first 10 orders
        [o.deliver() for o in Order.objects.all().order_by('inbox_date')[:10]]

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

    def test_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.assertFalse(Timetable.objects.all())
        resp = self.client.get(reverse('customerlist'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/list_view.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'regular')

    def test_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        resp = self.client.get(reverse('customerlist'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_cst_timetable_required_is_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            resp = self.client.get(reverse('customerlist'))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/list_view.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            resp = self.client.get(reverse('customerlist'))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

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

    def test_customer_view_excludes_providers(self):
        """Providers are shown only in admin view."""
        express = Customer.objects.first()
        express.provider = True
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
        self.assertEqual(resp.context['include_template'],
                         'includes/customer_list.html')

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


class ItemsListTests(TestCase):
    """Separated test for items list to test timetable decorator.

    The original tests are under standard views tests but eventually I came up
    with another arrangement such that each view has its tests ordered by
    statement show up.

    In the future those tests will end up here.
    """

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
            Order.objects.create(
                user=user, customer=customer, ref_name='Test order%s' % i,
                delivery=date.today(), inbox_date=timezone.now())
        Item.objects.create(name='test', fabrics=1, price=10, stocked=30)
        for order in Order.objects.all():
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.client.login(username='regular', password='test')

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('itemslist'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('itemslist'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.assertFalse(Timetable.objects.all())
        resp = self.client.get(reverse('itemslist'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/list_view.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'regular')

    def test_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        resp = self.client.get(reverse('itemslist'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_timetable_required_is_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            resp = self.client.get(reverse('itemslist'))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/list_view.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            resp = self.client.get(reverse('itemslist'))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

    def test_items_view_default_item(self):
        """In the begining just one item should be on db."""
        resp = self.client.get(reverse('itemslist'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/list_view.html')

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        resp = self.client.get(reverse('itemslist'))
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('itemslist'))
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('itemslist'))
        self.assertFalse(resp.context['session'])

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
        self.assertEqual(resp.context['version'], settings.VERSION)


class InvoicesListTest(TestCase):
    """Test the invoices list."""

    @classmethod
    def setUpTestData(self):
        """Create the necessary items on database at once."""
        user = User.objects.create_user(username='regular', password='test')
        user.save()

        Customer.objects.create(
            name='Test', city='Bilbao', phone=0, cp=48003)
        Item.objects.create(name='Test', fabrics=5, price=10, stocked=30)

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        self.client.login(username='regular', password='test')
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertTemplateUsed(resp, 'tz/invoices.html')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertTemplateUsed(resp, 'tz/invoices.html')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.client.login(username='regular', password='test')
        self.assertFalse(Timetable.objects.all())
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/invoices.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'regular')

    def test_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        self.client.login(username='regular', password='test')
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_timetable_required_is_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            resp = self.client.get(reverse('invoiceslist'))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/invoices.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            resp = self.client.get(reverse('invoiceslist'))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

    def test_invoices_today_displays_today_invoices(self):
        """Test display today's invoices and their total amount."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        for pm in ('C', 'C', 'V', 'T'):
            order = Order.objects.create(
                user=user, customer=c, ref_name='Test', delivery=date.today(),
                budget=0, prepaid=0, )
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            order.kill(pay_method=pm)

        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['cf_inbounds_today'].count(), 4)
        self.assertEqual(resp.context['cf_inbounds_today_cash']['total'], 40)
        self.assertEqual(
            resp.context['cf_inbounds_today_cash']['total_cash'], 20)
        self.assertEqual(
            resp.context['cf_inbounds_today_cash']['total_card'], 10)
        self.assertEqual(
            resp.context['cf_inbounds_today_cash']['total_transfer'], 10)

    def test_invoices_today_displays_today_prepaids(self):
        """Test display today's prepaids and their total amount."""
        self.client.login(username='regular', password='test')
        u = User.objects.first()
        c = Customer.objects.first()
        for pm in ('C', 'C', 'V', 'T'):
            order = Order.objects.create(
                user=u, customer=c, ref_name='Test', delivery=date.today(), )
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            CashFlowIO.objects.create(order=order, pay_method=pm, amount=5)

        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['cf_inbounds_today'].count(), 4)
        self.assertEqual(resp.context['cf_inbounds_today_cash']['total'], 20)
        self.assertEqual(
            resp.context['cf_inbounds_today_cash']['total_cash'], 10)
        self.assertEqual(
            resp.context['cf_inbounds_today_cash']['total_card'], 5)
        self.assertEqual(
            resp.context['cf_inbounds_today_cash']['total_transfer'], 5)

    def test_invoices_week_displays_week_invoices(self):
        """Test display week's invoices and their total amount."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        for pm in ('C', 'C', 'V', 'T'):
            order = Order.objects.create(
                user=user, customer=c, ref_name='Test', delivery=date.today(),
                budget=0, prepaid=0, )
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            today = timezone.now().date().isocalendar()[2]
            delay = timedelta(days=randint(0, today - 1))
            i = Invoice(
                reference=order, issued_on=timezone.now() - delay,
                pay_method=pm)
            i.save(kill=True)

        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['week'].count(), 4)
        self.assertEqual(resp.context['week_cash']['total'], 40)
        self.assertEqual(resp.context['week_cash']['total_cash'], 20)
        self.assertEqual(resp.context['week_cash']['total_card'], 10)
        self.assertEqual(resp.context['week_cash']['total_transfer'], 10)

    def test_invoices_month_displays_month_invoices(self):
        """Test display month's invoices and their total amount."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        for pm in ('C', 'C', 'V', 'T'):
            order = Order.objects.create(
                user=user, customer=c, ref_name='Test', delivery=date.today(),
                budget=0, prepaid=0, )
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            delay = timedelta(days=randint(0, date.today().day - 1))
            i = Invoice(reference=order, issued_on=timezone.now() - delay,
                        pay_method=pm)
            i.save(kill=True)
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['month'].count(), 4)
        self.assertEqual(resp.context['month_cash']['total'], 40)
        self.assertEqual(resp.context['month_cash']['total_cash'], 20)
        self.assertEqual(resp.context['month_cash']['total_card'], 10)
        self.assertEqual(resp.context['month_cash']['total_transfer'], 10)

    def test_invoices_all_time_cash(self):
        """Test all-time invoices and their total amount."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()
        for pm in ('C', 'C', 'V', 'T'):
            order = Order.objects.create(
                user=user, customer=c, ref_name='Test', delivery=date.today())
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            i = Invoice(
                reference=order, issued_on=timezone.now() - timedelta(days=30),
                pay_method=pm)
            i.save(kill=True)

        resp = self.client.get(reverse('invoiceslist'))
        # 40€ - 10€ (card) - 10€ (transfer)
        self.assertEqual(resp.context['all_time_cash']['total_cash'], 20)

    def test_bank_movements_displays_last_ten(self):
        """Test bank movements list."""
        self.client.login(username='regular', password='test')
        for i in range(15):
            BankMovement.objects.create(
                action_date=date.today(), amount=100, notes=str(i))
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['bank_movements'].count(), 10)

    def test_bank_movements_sums_both_positive_and_negative_values(self):
        """Bank movement should aggregate every value."""
        self.client.login(username='regular', password='test')
        BankMovement.objects.create(
            action_date=date.today(), amount=100, notes='positive')
        BankMovement.objects.create(
            action_date=date.today(), amount=-10, notes='negative')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['all_time_deposit']['total_cash'], 90)

    def test_bank_movements_0_value(self):
        """When there are no movements, all-time deposit should be 0."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['all_time_deposit']['total_cash'], 0)

    def test_total_cash_0_value(self):
        """When there are no cash, all-time cash should be 0."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['all_time_cash']['total_cash'], 0)

    def test_balance(self):
        """Test the correct output of balance."""
        self.client.login(username='regular', password='test')
        user = User.objects.first()
        c = Customer.objects.first()

        # First test no invoices nor bank movements
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['balance'], 0)

        # Now, have an invoice
        order = Order.objects.create(
            user=user, customer=c, ref_name='Test', delivery=date.today(),
            budget=0, prepaid=0, )
        OrderItem.objects.create(
            reference=order, element=Item.objects.last())
        order.kill(pay_method='C')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['balance'], -10)

        # Now, a bank movement
        BankMovement.objects.create(
            action_date=date.today(), amount=100, notes='positive')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['balance'], 90)

        # Now have an expense
        p = Customer.objects.create(
            name='Customer Test', address='Cache', city='This computer',
            phone='666666666', CIF='444E', cp=48003, provider=True, )
        Expense.objects.create(
            issuer=p, invoice_no='Test', issued_on=date.today(),
            concept='Concept', amount=100, pay_method='C')

        # Finally, balance out
        order = Order.objects.create(
            user=user, customer=c, ref_name='Test', delivery=date.today(),
            budget=0, prepaid=0, )
        OrderItem.objects.create(
            reference=order, element=Item.objects.last(), price=190)
        order.kill(pay_method='C')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['balance'], 0)

    def test_pending_expenses(self):
        p = Customer.objects.create(name='foo', address='bar', city='baz',
                                    phone=0, cp=0, CIF='CIF', provider=True)
        for n in range(4):
            e = Expense.objects.create(
                issuer=p, invoice_no='foo', issued_on=date.today(),
                concept='bar', amount=10)
            if n < 2:
                e.kill()
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['pending_expenses'].count(), 2)
        self.assertEqual(resp.context['pending_expenses_cash'], 20)

    def test_invoices_view_current_user(self):
        """Test the current user."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['user'].username, 'regular')

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertFalse(resp.context['session'])

    def test_invoices_view_title(self):
        """Test the window title."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Facturas')

    def test_invoices_template_used(self):
        """Test the window title."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('invoiceslist'))
        self.assertTemplateUsed(resp, 'tz/invoices.html')


class KanbanTests(TestCase):
    """Test the kanban main view."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a user
        u = User.objects.create_user(
            username='user', is_staff=True, password='test')

        # Create a customer
        c = Customer.objects.create(name='Customer Test', phone=0, cp=48100)

        # Create an item
        i = Item.objects.create(name='test', fabrics=10, price=30, stocked=30)

        # Create some orders with items
        for n in range(5):
            o = Order.objects.create(
                user=u, customer=c, ref_name='test%s' % n,
                delivery=date.today(), )
            OrderItem.objects.create(reference=o, element=i, qty=n)

        cls.client = Client()

    def setUp(self):
        """Auto login for tests."""
        self.client.login(username='user', password='test')

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('kanban'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('kanban'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.assertFalse(Timetable.objects.all())
        resp = self.client.get(reverse('kanban'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/kanban.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'user')

    def test_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        resp = self.client.get(reverse('kanban'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_timetable_required_is_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            resp = self.client.get(reverse('kanban'))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/kanban.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            resp = self.client.get(reverse('kanban'))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

    def test_kanban_returns_200(self):
        """Test the proper status return."""
        resp = self.client.get(reverse('kanban'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/kanban.html')

        # Also for unconfirmed
        resp = self.client.get(reverse('kanban'), {'unconfirmed': True})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/kanban.html')

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        resp = self.client.get(reverse('kanban'))
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('kanban'))
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('kanban'))
        self.assertFalse(resp.context['session'])

    def test_kanban_outputs_current_user(self):
        """Test the correct var."""
        resp = self.client.get(reverse('kanban'))
        self.assertEqual(resp.context['cur_user'].username, 'user')

    def test_kanban_outputs_current_vesion(self):
        """Test the correct var."""
        resp = self.client.get(reverse('kanban'))
        self.assertEqual(resp.context['version'], settings.VERSION)

    def test_kanban_outputs_correct_title(self):
        """Test the correct var."""
        resp = self.client.get(reverse('kanban'))
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Vista Kanban')


class StockManagerTests(TestCase):
    """Test the view."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a user
        User.objects.create_user(
            username='user', is_staff=True, password='test')

        # Create some different items
        item = Item.objects.create
        [item(name='test', fabrics=10, item_type=it, stocked=10, )
            for it in ('2', '3')]

        cls.client = Client()

    def setUp(self):
        """Auto login for tests."""
        self.client.login(username='user', password='test')

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('stock_manager'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('stock_manager'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.assertFalse(Timetable.objects.all())
        resp = self.client.get(reverse('stock_manager'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/stock_manager.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'user')

    def test_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        resp = self.client.get(reverse('stock_manager'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_timetable_required_is_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            resp = self.client.get(reverse('stock_manager'))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/stock_manager.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            resp = self.client.get(reverse('stock_manager'))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

    def test_stock_manager_filters_item_types(self):
        resp = self.client.get(
            reverse('stock_manager'), {'filter_type': '2'})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/stock_manager.html')
        i = Item.objects.filter(item_type='2')
        self.assertEqual(resp.context['tab_elements']['negative'][0], i[0])


@tag('todoist')
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

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.assertFalse(Timetable.objects.all())
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/order_view.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'regular')

    def test_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_timetable_required_is_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            order = Order.objects.first()
            resp = self.client.get(reverse('order_view', args=[order.pk]))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/order_view.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            order = Order.objects.first()
            resp = self.client.get(reverse('order_view', args=[order.pk]))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

    def test_pk_out_of_range_raises_404(self):
        """Raise a 404 when no order is matched."""
        resp = self.client.get(reverse('order_view', args=[5000]))
        self.assertEqual(resp.status_code, 404)

    def test_express_orders_should_be_redirected(self):
        """They are displayed as order_express view."""
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')
        resp = self.client.get(reverse(
            'order_view', args=[order_express.pk]))
        url = reverse('order_express', args=[order_express.pk])
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, url)

    def test_no_tab_get_arg_sets_items_as_default(self):
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEqual(resp.context['tab'], 'items')

    def test_tab_void_arg_raises_error(self):
        order = Order.objects.first()
        url = reverse('order_view', args=[order.pk]) + '?tab=void'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'Tab not valid')

    def test_errors_is_default_false(self):
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertFalse(resp.context['errors'])

    def test_post_add_project(self):
        order = Order.objects.first()
        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'add-project', })
        order.t_sync()
        self.assertTrue(order.t_api)
        self.assertTrue(order.t_pid)
        self.assertFalse(resp.context['errors'])
        self.assertEqual(resp.context['tab'], 'tasks')

        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'add-project', })
        errors = [('Couldn\'t create project on todoist, did it ' +
                  'already exist?'), ]
        self.assertEqual(resp.context['errors'], errors)

        project = order.t_api.projects.get_by_id(order.t_pid)
        project.delete()
        order.t_api.commit()

    def test_post_archive_project(self):
        order = Order.objects.first()

        # Try to archive without creation
        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'archive-project', })
        errors = [('Couldn\'t archive project, maybe it was ' +
                   'already archived or just didn\'t exist'), ]
        self.assertEqual(resp.context['errors'], errors)
        order.create_todoist()
        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'archive-project', })
        order.t_sync()
        self.assertTrue(order.is_archived())
        self.assertFalse(resp.context['errors'])
        self.assertEqual(resp.context['tab'], 'tasks')

        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'archive-project', })
        self.assertEqual(resp.context['errors'], errors)

        project = order.t_api.projects.get_by_id(order.t_pid)
        project.delete()
        order.t_api.commit()

    def test_post_unarchive_project(self):
        order = Order.objects.first()

        # Try to unarchive without creation
        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'unarchive-project', })
        errors = [('Couldn\'t unarchive project, maybe it was ' +
                  'already unarchived or just didn\'t exist'), ]
        self.assertEqual(resp.context['errors'], errors)

        # now create it & try to unarchive without archive
        order.create_todoist()
        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'unarchive-project', })
        self.assertEqual(resp.context['errors'], errors)
        order.t_sync()

        # finally archive it and unarchive it
        order.archive()
        order.t_sync()
        self.assertTrue(order.is_archived())
        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'unarchive-project', })
        self.assertFalse(resp.context['errors'])
        self.assertEqual(resp.context['tab'], 'tasks')
        order.t_sync()
        self.assertFalse(order.is_archived())

        project = order.t_api.projects.get_by_id(order.t_pid)
        project.delete()
        order.t_api.commit()

    def test_post_deliver(self):
        order = Order.objects.first()
        order.delivery = date.today() + timedelta(days=5)
        order.save()
        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'deliver-order', })
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '7')
        self.assertEqual(order.delivery, date.today())
        self.assertEqual(resp.context['tab'], 'main')

    def test_post_kill_order(self):
        order = Order.objects.first()
        item = Item.objects.create(name='foo', fabrics=5, stocked=10)
        OrderItem.objects.create(reference=order, element=item)
        msg = 'Order has no invoice.'
        with self.assertRaisesMessage(ObjectDoesNotExist, msg):
            order.invoice
        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'kill-order', 'pay_method': 'V'})
        order = Order.objects.first()
        self.assertEqual(order.invoice.pay_method, 'V')
        self.assertEqual(resp.context['tab'], 'main')

    def test_post_invalid_action_raises_500(self):
        """A valid action is required."""
        order = Order.objects.first()
        resp = self.client.post(reverse('order_view', args=[order.pk]),
                                {'action': 'void', })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'Action was not recognized')

    def test_show_comments(self):
        """Display the correct comments.

        Performed by CommonContexts, but left here anyway.
        """
        order = Order.objects.first()
        user = User.objects.first()
        for i in range(3):
            Comment.objects.create(reference=order, comment='Test', user=user)

        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEqual(resp.context['comments'].count(), 3)
        self.assertTrue(
            resp.context['comments'][0].creation >
            resp.context['comments'][1].creation)

    def test_show_items(self):
        """Display the correct items.

        Performed by CommonContexts, but left here anyway.
        """
        order = Order.objects.first()
        item = Item.objects.create(name='Test', fabrics=5, stocked=30)
        for i in range(3):
            OrderItem.objects.create(reference=order, element=item)
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEqual(resp.context['items'].count(), 3)

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertFalse(resp.context['session'])

    def test_context_variables(self):
        """Test the remaining variables.

        Some of them performed by common contexts, but left here anyway.
        """
        order = Order.objects.first()
        resp = self.client.get(reverse('order_view', args=[order.pk]))
        self.assertEqual(resp.context['user'].username, order.user.username)
        self.assertEqual(
            resp.context['session'], Timetable.active.get(user=order.user))
        self.assertFalse(resp.context['tasks'])
        self.assertFalse(resp.context['archived'])
        self.assertFalse(resp.context['project_id'])
        self.assertEqual(resp.context['version'], settings.VERSION)
        self.assertEqual(resp.context['title'],
                         'Pedido %s: %s, %s' %
                         (order.pk, order.customer.name, order.ref_name))


class OrderExpressTests(TestCase):
    """Test the order express view."""

    @classmethod
    def setUpTestData(self):
        """Create all the elements at once."""
        user = User.objects.create_user(username='regular', password='test')
        user.save()

        Customer.objects.create(
            name='Test', city='Bilbao', phone=0, cp=48003)
        Item.objects.create(name='Test', fabrics=5, price=10, stocked=30)

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order = Order.objects.get(customer__name='express')
        resp = self.client.get(reverse('order_express', args=[order.pk]), )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('order_express', args=[order.pk]), )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_pk_out_of_range_raises_404(self):
        """Raise a 404 when trying to select a void order."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('order_express', args=[5000]))
        self.assertEqual(resp.status_code, 404)

    def test_post_cp_changes_cp(self):
        """Test the correct update of customer."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order = Order.objects.get(customer__name='express')
        resp = self.client.post(reverse('order_express', args=[order.pk]),
                                {'cp': 230})
        self.assertEqual(resp.context['order'].customer.cp, '230')

    def test_post_customer_changes_customer(self):
        """Test the proper change of customer."""
        self.client.login(username='regular', password='test')
        c = Customer.objects.first()
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order = Order.objects.get(customer__name='express')
        resp = self.client.post(reverse('order_express', args=[order.pk]),
                                {'customer': c.pk})
        self.assertEqual(resp.status_code, 302)
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.customer.name, 'Test')

    def test_post_pay_method_ivoices_order(self):
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order = Order.objects.get(customer__name='express')
        with self.assertRaises(ObjectDoesNotExist):
            Invoice.objects.get(reference=order)  # The invoice not yet

        OrderItem.objects.create(
            element=Item.objects.last(), qty=5, reference=order)
        resp = self.client.post(reverse('order_express', args=[order.pk]),
                                {'pay_method': settings.PAYMENT_METHODS[0][0]})

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Invoice.objects.get(reference=order))

    def test_invalid_pk_raises_404(self):
        """Raise a 404 when trying to select a void customer."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order = Order.objects.get(customer__name='express')
        resp = self.client.post(reverse('order_express', args=[order.pk]),
                                {'customer': 3000})
        self.assertEqual(resp.status_code, 404)

    def test_no_cp_or_not_customerpk_should_raise_404(self):
        """Raise a 404 when not passing valid arguments."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order = Order.objects.get(customer__name='express')
        resp = self.client.post(reverse('order_express', args=[order.pk]),
                                {'void': 'null'})
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

    def test_customer_list_excludes_express_and_providers(self):
        """These customers should be excluded."""
        self.client.login(username='regular', password='test')
        Customer.objects.create(
            name='provider', city='server', phone=0, cp=48003, provider=True)
        self.client.post(reverse('actions'),
                         {'cp': 0, 'pk': 'None',
                          'action': 'order-express-add', })
        order_express = Order.objects.get(customer__name='express')
        resp = self.client.get(
            reverse('order_express', args=[order_express.pk]))
        self.assertEqual(resp.context['customers'].count(), 1)
        self.assertEqual(resp.context['customers'][0].name, 'Test')
        self.assertEqual(Customer.objects.count(), 3)

    def test_items_belong_to_the_order(self):
        """Display all the items that are owned by an order."""
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
        msg = 'Order has no invoice.'
        with self.assertRaisesMessage(ObjectDoesNotExist, msg):
            resp.context['order'].invoice

        OrderItem.objects.create(
            reference=order_express, element=Item.objects.last(), price=10)
        order_express.kill()
        resp = self.client.get(
            reverse('order_express', args=[order_express.pk]))
        self.assertTrue(resp.context['order'].invoice)

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

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        self.client.login(username='regular', password='test')
        self.client.post(reverse('actions'), {'cp': 0, 'pk': 'None',
                                              'action': 'order-express-add', })
        order = Order.objects.get(customer__name='express')
        resp = self.client.get(reverse('order_express', args=[order.pk]), )
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('order_express', args=[order.pk]), )
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('order_express', args=[order.pk]), )
        self.assertFalse(resp.context['session'])

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
        self.assertIsInstance(resp.context['invoice_form'], InvoiceForm)
        self.assertEqual(resp.context['title'], 'TrapuZarrak · Venta express')
        self.assertEqual(resp.context['placeholder'], 'Busca un nombre')
        self.assertEqual(resp.context['search_on'], 'items')

        # CRUD actions
        self.assertEqual(resp.context['btn_title_add'], 'Nueva prenda')
        self.assertEqual(resp.context['js_action_add'], 'object-item-add')


class CustomerViewTests(TestCase):
    """Test the customer list view."""

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

        c = Customer.objects.create(name='Customer',
                                    address='This computer',
                                    city='No city',
                                    phone='666666666',
                                    email='customer@example.com',
                                    CIF='5555G',
                                    cp='48100')

        # Create some orders
        for order in range(5):
            delivery = date.today() + timedelta(days=order % 5)
            Order.objects.create(user=regular,
                                 customer=c,
                                 ref_name='example%s' % order,
                                 delivery=delivery,
                                 waist=randint(10, 50),
                                 chest=randint(10, 50),
                                 hip=randint(10, 50),
                                 lenght=randint(10, 50),
                                 others='Custom notes',
                                 budget=2000,
                                 prepaid=0)

        item = Item.objects.create(name='foo', fabrics=1, stocked=30, )

        # Create some items
        for _ in range(5):
            order = Order.objects.get(ref_name='example0')
            OrderItem.objects.create(element=item, qty=5,
                                     description='notes',
                                     reference=order)

        # deliver the first 10 orders
        order_bulk_edit = Order.objects.all().order_by('inbox_date')[:3]
        for order in order_bulk_edit:
            order.ref_name = 'example delivered' + str(order.pk)
            order.status = 7
            order.save()

        # Have a closed order (delivered & paid)
        order = Order.objects.filter(status=7)[0]
        order.ref_name = 'example closed'
        order.prepaid = order.budget
        order.save()

        # Now login to avoid the 404
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        customer = Customer.objects.first()
        resp = self.client.get(reverse('customer_view', args=[customer.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('customer_view', args=[customer.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

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

    def test_cst_view_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.assertFalse(Timetable.objects.all())
        customer = Customer.objects.first()
        resp = self.client.get(reverse('customer_view', args=[customer.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/customer_view.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'regular')

    def test_cst_view_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        customer = Customer.objects.first()
        resp = self.client.get(reverse('customer_view', args=[customer.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_cview_timetable_required_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            customer = Customer.objects.first()
            resp = self.client.get(
                reverse('customer_view', args=[customer.pk]))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/customer_view.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            customer = Customer.objects.first()
            resp = self.client.get(
                reverse('customer_view', args=[customer.pk]))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

    def test_customer_view(self):
        """Test the customer details view."""
        customer = Customer.objects.first()
        no_orders = Order.objects.filter(customer=customer)
        self.assertEqual(no_orders.count(), 5)
        item = Item.objects.create(
            name='Test', fabrics=1, price=10, stocked=30, )

        orders = Order.objects.all()
        for order in orders:
            order.customer = customer
            order.prepaid = 0
            order.save()
            OrderItem.objects.create(reference=order, element=item)

        Order.objects.first().kill()

        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('customer_view', args=[customer.pk]))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/customer_view.html')

        self.assertEqual(len(resp.context['orders_active']), 2)
        self.assertEqual(len(resp.context['orders_delivered']), 3)
        self.assertEqual(len(resp.context['orders_cancelled']), 0)
        self.assertEqual(resp.context['orders_made'], 5)
        self.assertEqual(len(resp.context['pending']), 4)

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        customer = Customer.objects.first()
        resp = self.client.get(reverse('customer_view', args=[customer.pk]))
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('customer_view', args=[customer.pk]))
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('customer_view', args=[customer.pk]))
        self.assertFalse(resp.context['session'])


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
            Item.objects.create(name='Test item%s' % i, fabrics=5, stocked=30)

        # Create orderitems
        for item in Item.objects.all():
            OrderItem.objects.create(reference=order, element=item)

        self.client.login(username='regular', password='test')

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.assertFalse(Timetable.objects.all())
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/pqueue_manager.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'regular')

    def test_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_timetable_required_is_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            resp = self.client.get(reverse('pqueue_manager'))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/pqueue_manager.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            resp = self.client.get(reverse('pqueue_manager'))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

    def test_view_exists(self):
        """First test the existence of pqueue view."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/pqueue_manager.html')

    def test_common_context_is_imported(self):
        """Test the vars comming in the commom context."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('pqueue_manager'))
        vars = ('available', 'active', 'completed', 'i_relax', 'now',
                'version', 'title', )
        for var in vars:
            self.assertTrue(var in resp.context.keys())

    def test_cur_user(self):
        """Test the vars that weren't included in the common context."""
        self.client.login(username='regular', password='test')
        user = User.objects.get(username='regular')
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertEqual(resp.context['cur_user'], user)

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('pqueue_manager'))
        self.assertFalse(resp.context['session'])


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
            Item.objects.create(name='Test item%s' % i, fabrics=5, stocked=30)

        # Create orderitems
        for item in Item.objects.all():
            OrderItem.objects.create(reference=order, element=item)

        self.client.login(username='regular', password='test')

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_timetable_required_creates_timetable(self):
        """When no working session is open a timetable should be created."""
        self.assertFalse(Timetable.objects.all())
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/pqueue_tablet.html')
        self.assertEquals(Timetable.objects.count(), 1)
        self.assertEquals(Timetable.objects.all()[0].user.username, 'regular')

    def test_timetable_required_is_void_15_hours(self):
        """When the timer has been running for +15h user should be prompted."""
        Timetable.objects.create(
            user=User.objects.first(),
            start=(timezone.now() - timedelta(hours=15.5)),
        )
        login_url = '/add-hours'
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, login_url)
        self.assertEquals(Timetable.objects.count(), 1)

    def test_timetable_required_is_void_change_date_and_still_valid(self):
        """When the timer has been running since the day before."""
        self.client.login(username='regular', password='test')
        dlt = (timezone.now() - timedelta(hours=14.5))
        if timezone.now().date() == dlt.date():
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            resp = self.client.get(reverse('pqueue_tablet'))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, 'tz/pqueue_tablet.html')
            self.assertEquals(Timetable.objects.count(), 1)
        else:  # runs fine before 14:30
            Timetable.objects.create(user=User.objects.first(), start=dlt, )
            login_url = '/add-hours'
            resp = self.client.get(reverse('pqueue_tablet'))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, login_url)
            self.assertEquals(Timetable.objects.count(), 1)

    def test_view_exists(self):
        """First test the existence of pqueue tablet view."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'tz/pqueue_tablet.html')

    def test_common_context_is_imported(self):
        """Test the vars comming in the commom context."""
        self.client.login(username='regular', password='test')
        resp = self.client.get(reverse('pqueue_tablet'))
        vars = ('available', 'active', 'completed', 'i_relax', 'now',
                'version', 'title', )
        for var in vars:
            self.assertTrue(var in resp.context.keys())

    def test_cur_user_and_session(self):
        """Test the vars that weren't included in the common context."""
        self.client.login(username='regular', password='test')
        user = User.objects.get(username='regular')
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertEqual(resp.context['cur_user'], user)

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('pqueue_tablet'))
        self.assertFalse(resp.context['session'])


class TimetableListTests(TestCase):
    """Test the generic view for timetables."""

    def setUp(self):
        user = User.objects.create_user(username='regular', password='test')
        user.save()

        Timetable.objects.create(user=user, hours=timedelta(seconds=3600))

        self.client.login(username='regular', password='test')

    def test_timetable_required_skips_superusers_or_voyeur(self):
        """Superusers & voyeur don't track times."""
        voyeur = config('VOYEUR_USER')
        vu = User.objects.create_user(username=voyeur, password='vu_pass')
        su = User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('timetables'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=vu))

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('timetables'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Timetable.objects.filter(user=su))

    def test_template(self):
        resp = self.client.get(reverse('timetables'))
        self.assertTemplateUsed(resp, 'tz/timetable_list.html')
        self.assertEqual(resp.status_code, 200)

    def test_context_main_var(self):
        resp = self.client.get(reverse('timetables'))
        self.assertTrue(resp.context['timetables'])

    def test_view_only_shows_current_user_timetables(self):
        user2 = User.objects.create_user(username='alt', password='test')
        user2.save()
        Timetable.objects.create(user=user2, hours=timedelta(seconds=3000))

        self.assertEqual(Timetable.objects.count(), 2)
        resp = self.client.get(reverse('timetables'))
        self.assertEqual(len(resp.context['timetables']), 1)
        self.assertEqual(
            resp.context['timetables'][0].user.username, 'regular')

    def test_view_only_shows_last_10_entries_descending_ordered(self):
        start = timezone.now() - timedelta(days=15)
        for _ in range(12):
            Timetable.objects.create(
                user=User.objects.first(),
                start=start,
                hours=timedelta(seconds=3600))
            start += timedelta(days=1)
        resp = self.client.get(reverse('timetables'))

        timetables = resp.context['timetables']
        self.assertTrue(len(timetables), 10)

        for n, t in enumerate(timetables[:9]):
            self.assertTrue(t.start > timetables[n + 1].start)

    def test_session_var_is_last_timetable(self):
        start = timezone.now() - timedelta(days=15)
        for _ in range(5):
            Timetable.objects.create(
                user=User.objects.first(),
                start=start,
                hours=timedelta(seconds=3600))
            start += timedelta(days=1)
        resp = self.client.get(reverse('timetables'))
        self.assertEqual(resp.context['session'], Timetable.objects.last())

    def test_sessions(self):
        """Regular users should return timetable whereas su's return None."""
        resp = self.client.get(reverse('timetables'))
        self.assertIsInstance(resp.context['session'], Timetable)

        voyeur = config('VOYEUR_USER')
        User.objects.create_user(username=voyeur, password='vu_pass')
        User.objects.create_user(
            username='su', password='su_pass', is_superuser=True)

        self.client.login(username=voyeur, password='vu_pass')
        resp = self.client.get(reverse('timetables'))
        self.assertFalse(resp.context['session'])

        self.client.login(username='su', password='su_pass')
        resp = self.client.get(reverse('timetables'))
        self.assertFalse(resp.context['session'])


class ActionsGetMethod(TestCase):
    """Test the get method on Actions view."""

    @classmethod
    def setUpTestData(cls):
        """Set up some data for the tests.

        We should create a user, a customer, an order, and an item.
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
        order = Order.objects.create(user=regular,
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
        item = Item.objects.create(name='foo', fabrics=2, stocked=30)
        OrderItem.objects.create(
            element=item, qty=5, description='notes', reference=order)

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
        actions = ('order-add-comment',
                   'customer-edit',
                   'object-item-edit',
                   'pqueue-add-time',
                   'object-item-delete',
                   'order-express-delete',
                   'customer-delete',
                   'view-ticket',
                   )
        for action in actions:
            resp = self.client.get(
                reverse('actions'), {'pk': 2000, 'action': action})
            self.assertEqual(resp.status_code, 404)

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

    def test_order_express(self):
        """Test the correct process of express orders."""
        resp = self.client.get(reverse('actions'),
                               {'pk': 'None',
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
        resp = self.client.get(reverse('actions'), {'pk': 'None',
                                                    'action': 'customer-add',
                                                    'test': True})
        self.assertEqual(resp.status_code, 200)

    def test_add_customer_context(self):
        """Test context dictionaries and template."""
        resp = self.client.get(reverse('actions'), {'pk': 'None',
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
        item = Item.objects.first()
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
                '2nd_sbt_value', '2nd_sbt_btn', 'custom_form')
        self.assertEqual(template, 'includes/regular_form.html')
        self.assertIsInstance(context, list)
        self.assertTrue(self.context_vars(context, vars))

    def test_delete_order_express(self):
        """Testthe correct content for the modal."""
        order = Order.objects.first()
        resp = self.client.get(reverse('actions'),
                               {'pk': order.pk,
                                'action': 'order-express-delete',
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
        item = Item.objects.first()
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
        order.kill()
        resp = self.client.get(reverse('actions'),
                               {'pk': order.invoice.pk,
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


class ActionsPostMethodRaises(TestCase):
    """Test the correct raise of errors in post method."""

    def test_no_pk_raises_error(self):
        """Raise an error when no pk is given."""
        with self.assertRaisesMessage(ValueError, 'POST data was poor'):
            self.client.post(
                reverse('actions'), {'action': 'order-add-comment'})

    def test_no_action_raises_error(self):
        """Raise an error when no action is given."""
        with self.assertRaisesMessage(ValueError, 'POST data was poor'):
            self.client.post(reverse('actions'), {'pk': 5})

    def test_invalid_action_raises_error(self):
        """Raise an error when action doesn't match any condition."""
        with self.assertRaisesMessage(NameError, 'Action was not recogniced'):
            self.client.post(reverse('actions'), {'pk': 5, 'action': 'null'})

    def test_pk_out_of_range_raises_404(self):
        """High pk should raise a 404."""
        actions = ('order-comment',
                   'comment-read',
                   'customer-edit',
                   'object-item-edit',
                   'pqueue-add-time',
                   'object-item-delete',
                   'order-express-delete',
                   'customer-delete',
                   )
        for action in actions:
            resp = self.client.post(
                reverse('actions'), {'pk': 2000, 'action': action})
            self.assertEqual(resp.status_code, 404)


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
                                 'pk': 'None',
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
                                 'pk': 'None',
                                 'action': 'customer-new',
                                 'test': True
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        template = data['template']
        context = data['context']
        vars = ('form', 'modal_title', 'pk', 'action', 'submit_btn',
                'custom_form')
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
                   'customer-edit',
                   'object-item-edit',
                   'pqueue-add-time',
                   'object-item-delete',
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

    def test_obj_item_adds_item(self):
        """Test the proper creation of item objects."""
        self.client.post(reverse('actions'), {'action': 'object-item-add',
                                              'pk': 'None',
                                              'name': 'Example Item',
                                              'item_type': '2',
                                              'item_class': 'S',
                                              'size': '4',
                                              'fabrics': 4,
                                              'price': 500,
                                              'notes': 'Custom Notes',
                                              'stocked': 30,
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
                                 'stocked': 10,
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
                'js_action_delete', )
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
                                 'stocked': 20,
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('item_types', 'available_items', 'js_action_edit',
                'js_action_delete',)
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
        item = Item.objects.first()
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
        self.assertEqual(data['template'], 'includes/pqueue_tablet.html')
        self.assertEqual(data['html_id'], '#pqueue-list-tablet')
        self.assertTrue(self.context_vars(data['context'], vars))

        # Test if the fields were modified
        mod_item = OrderItem.objects.get(pk=item.pk)
        for i in (mod_item.sewing, mod_item.crop, mod_item.iron):
            self.assertEqual(i, timedelta(0, 2))

    def test_pqueue_raises_404_when_pquee_does_not_exist(self):
        """Test the get_object_or_404."""
        item = OrderItem.objects.first()
        for i in (item.sewing, item.crop, item.iron):
            self.assertEqual(i, timedelta(0))
        resp = self.client.post(reverse('actions'),
                                {'iron': '2', 'crop': '2', 'sewing': '2',
                                 'pk': item.pk,
                                 'sbt_action': 'save-and-archive',
                                 'action': 'pqueue-add-time',
                                 'test': True
                                 })
        self.assertEqual(resp.status_code, 404)

    def test_pqueue_adds_time_and_completes(self):
        """Test the correct 2-in-1 action."""
        item = OrderItem.objects.first()
        PQueue.objects.create(item=item)
        for i in (item.sewing, item.crop, item.iron):
            self.assertEqual(i, timedelta(0))
        self.client.post(reverse('actions'),
                         {'iron': '2', 'crop': '2', 'sewing': '2',
                          'pk': item.pk,
                          'sbt_action': 'save-and-archive',
                          'action': 'pqueue-add-time',
                          'test': True
                          })
        mod_item = OrderItem.objects.get(pk=item.pk)
        for i in (mod_item.sewing, mod_item.crop, mod_item.iron):
            self.assertEqual(i, timedelta(0, 2))
        archived = PQueue.objects.get(pk=item.pk)
        self.assertTrue(archived.score < 0)

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

    def test_delete_order_express_deletes_order(self):
        """Test the correct deletion of order express."""
        order = Order.objects.first()
        resp = self.client.post(reverse('actions'),
                                {'pk': order.pk,
                                 'action': 'order-express-delete',
                                 'test': True
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['redirect'], reverse('main'))
        with self.assertRaises(ObjectDoesNotExist):
            OrderItem.objects.get(pk=order.pk)

    def test_delete_obj_item_deletes_the_item(self):
        """Test the correct item deletion."""
        item = Item.objects.create(name='Test', fabrics=5, stocked=30)
        resp = self.client.post(reverse('actions'),
                                {'pk': item.pk,
                                 'action': 'object-item-delete',
                                 'test': True
                                 })
        # Test the response object
        data = json.loads(str(resp.content, 'utf-8'))
        vars = ('item_types', 'available_items', 'js_action_edit',
                'js_action_delete', )
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['template'], 'includes/item_selector.html')
        self.assertEqual(data['html_id'], '#item-selector')
        self.assertTrue(self.context_vars(data['context'], vars))

        # test if the object was actually deleted
        with self.assertRaises(ObjectDoesNotExist):
            Item.objects.get(pk=item.pk)

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


class OrdersCRUDTests(TestCase):
    """Test the AJAX methods."""

    def setUp(self):
        """Create the necessary items on database at once."""
        u = User.objects.create_user(username='regular', password='test')

        # Create a customer
        c = Customer.objects.create(name='Customer Test', phone=0, cp=48100)

        # Create an item
        i = Item.objects.create(name='test', fabrics=10, price=30, stocked=30)

        # Create some orders with items
        for n in range(5):
            o = Order.objects.create(
                user=u, customer=c, ref_name='test%s' % n,
                delivery=date.today(), )
            OrderItem.objects.create(reference=o, element=i, qty=n)
        # Load client
        self.client = Client()

        # Log the user in
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')

    def test_get_data_should_be_a_dict(self):
        resp = self.client.get(reverse('orders-CRUD'), )
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(data, dict)

    def test_get_template_used(self):
        self.client.get(reverse('orders-CRUD'), {'test': True})
        self.assertTemplateUsed('includes/custom_forms/order.html')

    def test_get_edit_order(self):
        o = Order.objects.first()
        resp = self.client.get(reverse('orders-CRUD'),
                               {'test': True, 'order_pk': o.pk})
        self.assertEqual(resp.context['order'], o)
        self.assertIsInstance(resp.context['form'], OrderForm)
        self.assertEqual(resp.context['form'].instance, o)
        self.assertEqual(resp.context['modal_title'], 'Editar pedido')

    def test_get_create_new_order(self):
        resp = self.client.get(reverse('orders-CRUD'), {'test': True, })
        self.assertEqual(resp.context['order'], None)
        self.assertIsInstance(resp.context['form'], OrderForm)
        self.assertEqual(resp.context['modal_title'], 'Crear pedido')

    def test_get_is_json_response(self):
        resp = self.client.get(reverse('orders-CRUD'),)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['html'])

    def test_post_data_should_be_a_dict(self):
        """Data for AJAX request should be a dict."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'delivery': date(2017, 1, 1),
                                 'pk': Order.objects.first().pk,
                                 'action': 'edit-date',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(data, dict)

    def test_post_no_action_raises_500(self):
        """Action is mandatory."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'delivery': date(2017, 1, 1),
                                 'pk': Order.objects.first().pk,
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No action was given.')

    def test_post_main_differentiates_between_edit_and_create(self):
        order = Order.objects.first()
        # Create
        post_data = {
            'inbox_date': datetime.now(), 'user': order.user.pk,
            'customer': order.customer.pk, 'delivery': date.today(),
            'ref_name': 'new', 'status': '1', 'priority': '1',
            'waist': 0, 'chest': 0, 'hip': 0, 'lenght': 0, 'discount': 0,
            'action': 'main', 'test': True, }
        resp = self.client.post(reverse('orders-CRUD'), post_data)

        self.assertTrue(resp.context['form'].is_bound)
        self.assertEqual(resp.context['modal_title'], 'Crear pedido')

        # edit
        post_data['pk'] = order.pk
        resp = self.client.post(reverse('orders-CRUD'), post_data)
        self.assertEqual(resp.context['form'].instance, order)
        self.assertTrue(resp.context['form'].is_bound)
        self.assertEqual(resp.context['modal_title'], 'Editar pedido')

    def test_post_main_edits_order(self):
        order = Order.objects.first()
        post_data = {
            'inbox_date': datetime.now(), 'user': order.user.pk,
            'customer': order.customer.pk, 'delivery': date.today(),
            'ref_name': 'edited', 'status': '1', 'priority': '1',
            'waist': 0, 'chest': 0, 'hip': 0, 'lenght': 0, 'discount': 0,
            'pk': order.pk, 'action': 'main', }
        self.client.post(reverse('orders-CRUD'), post_data)

        self.assertEqual(Order.objects.get(pk=order.pk).ref_name, 'edited')

    def test_post_main_creates_order(self):
        self.assertEqual(Order.objects.count(), 5)
        post_data = {
            'inbox_date': datetime.now(), 'user': User.objects.first().pk,
            'customer': Customer.objects.first().pk, 'delivery': date.today(),
            'ref_name': 'New', 'status': '1', 'priority': '1', 'waist': 0,
            'chest': 0, 'hip': 0, 'lenght': 0, 'discount': 0, 'action': 'main'}
        self.client.post(reverse('orders-CRUD'), post_data)

        self.assertEqual(Order.objects.count(), 6)
        self.assertEqual(Order.objects.last().ref_name, 'New')

    def test_post_main_json_response(self):
        order = Order.objects.first()
        post_data = {
            'inbox_date': datetime.now(), 'user': order.user.pk,
            'customer': order.customer.pk, 'delivery': date.today(),
            'ref_name': 'edited', 'status': '1', 'priority': '1',
            'waist': 0, 'chest': 0, 'hip': 0, 'lenght': 0, 'discount': 0,
            'pk': order.pk, 'action': 'main', }
        resp = self.client.post(reverse('orders-CRUD'), post_data)

        data = json.loads(str(resp.content, 'utf-8'))
        url = (reverse('order_view', args=[order.pk]) + '?tab=main')
        self.assertEqual(data['redirect'], url)
        self.assertTrue(data['form_is_valid'])

    def test_post_main_rejects_form(self):
        """Test first the JSON response and then with the dummy objects."""
        order = Order.objects.first()
        post_data = {
            'inbox_date': datetime.now(), 'user': order.user.pk,
            'customer': order.customer.pk, 'delivery': 'void',
            'ref_name': 'edited', 'status': '1', 'priority': '1',
            'waist': 0, 'chest': 0, 'hip': 0, 'lenght': 0, 'discount': 0,
            'pk': order.pk, 'action': 'main'}
        resp = self.client.post(reverse('orders-CRUD'), post_data)

        data = json.loads(str(resp.content, 'utf-8'))
        self.assertFalse(data['form_is_valid'])

        # Now with the dummy render
        post_data['test'] = True
        resp = self.client.post(reverse('orders-CRUD'), post_data)
        self.assertEqual(resp.context['form'].instance, order)
        self.assertTrue(resp.context['form'].is_bound)
        self.assertEqual(resp.context['modal_title'], 'Editar pedido')
        self.assertTemplateUsed('includes/custom_forms/order.html')

    def test_post_edit_date_raises_404(self):
        msg = 'Order matching query does not exist.'
        with self.assertRaisesMessage(ObjectDoesNotExist, msg):
            self.client.post(reverse('orders-CRUD'),
                             {'direction': 'next',
                              'pk': 5000,
                              'action': 'edit-date',
                              })

    def test_post_edit_date_valid_form_returns_true_form_is_valid(self):
        """Successful processed orders should return form_is_valid."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'delivery': date(2017, 1, 1),
                                 'pk': Order.objects.first().pk,
                                 'action': 'edit-date',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertTrue(data['form_is_valid'])

    def test_post_edit_date_valid_form_context_is_kanban_common(self):
        """Just test the existence."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'delivery': date(2017, 1, 1),
                                 'pk': Order.objects.first().pk,
                                 'action': 'edit-date',
                                 'test': True,
                                 })
        common_vars = ('icebox', 'queued', 'in_progress', 'waiting', 'done',
                       'update_date', 'amounts')
        for var in common_vars:
            self.assertTrue(var in resp.context)

    def test_post_edit_date_valid_form_template(self):
        """Test the correct teplate."""
        self.client.post(
            reverse('orders-CRUD'),
            {'delivery': date(2017, 1, 1),
             'pk': Order.objects.first().pk,
             'action': 'edit-date',
             'test': True,
             })
        self.assertTemplateUsed('includes/kanban_columns.html')

    def test_post_edit_date_html_id(self):
        """Successful processed orders html id."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'delivery': date(2017, 1, 1),
                                 'pk': Order.objects.first().pk,
                                 'action': 'edit-date',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(data['html_id'], '#kanban-columns')

    def test_post_edit_date_form_is_not_valid(self):
        """Unsuccessful processed oders should return false."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'delivery': 'void',
                                 'pk': Order.objects.first().pk,
                                 'action': 'edit-date',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertFalse(data['form_is_valid'])

    def test_post_edit_date_form_is_not_valid_errors(self):
        """Test the errors var."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'delivery': 'void',
                                 'pk': Order.objects.first().pk,
                                 'action': 'edit-date',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(data['error']['delivery'], ['Enter a valid date.', ])

    def test_post_kanban_jump_raises_error_with_invalid_order(self):
        msg = 'Order matching query does not exist.'
        with self.assertRaisesMessage(ObjectDoesNotExist, msg):
            self.client.post(reverse('orders-CRUD'),
                             {'direction': 'next',
                              'pk': 5000,
                              'action': 'kanban-jump',
                              })

    def test_post_kanban_jump_not_origin_returns_500(self):
        """Origin arg is mandatory."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'pk': Order.objects.first().pk,
                                 'action': 'kanban-jump',
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No origin was especified.')

    def test_post_kanban_jump_backwards(self):
        """Test the action."""
        o = Order.objects.first()
        o.status = '3'
        o.save()
        self.client.post(reverse('orders-CRUD'),
                         {'origin': 'satus-shiftBack',
                          'pk': Order.objects.first().pk,
                          'action': 'kanban-jump',
                          })
        o = Order.objects.get(pk=o.pk)
        self.assertEqual(o.status, '2')

    def test_post_kanban_jump_forward(self):
        """Test the action."""
        o = Order.objects.first()
        o.status = '3'
        o.save()
        self.client.post(reverse('orders-CRUD'),
                         {'origin': 'satus-shiftFwd',
                          'pk': Order.objects.first().pk,
                          'action': 'kanban-jump',
                          })
        o = Order.objects.get(pk=o.pk)
        self.assertEqual(o.status, '6')

    def test_post_kanban_jump_unknown_dir(self):
        """Test when no direction is given."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'origin': 'status-void',
                                 'pk': Order.objects.first().pk,
                                 'action': 'kanban-jump',
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'Unknown direction.')

    def test_post_kanban_jump_origin_status(self):
        """Just test the existence."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'origin': 'status-shiftFwd',
                                 'pk': Order.objects.first().pk,
                                 'action': 'kanban-jump',
                                 'test': True,
                                 })
        common_vars = (
            'order', 'items', 'status_tracker', 'order_est', 'order_est_total',
            'update_times', 'add_prepaids', 'kill_order', 'comments',
            'STATUS_ICONS', 'user', 'now', 'session', 'version', 'title', )
        for var in common_vars:
            self.assertTrue(var in resp.context)
        self.assertTemplateUsed('includes/order_status.html')

    def test_post_kanban_jump_origin_status_json_response(self):
        resp = self.client.post(reverse('orders-CRUD'),
                                {'origin': 'status-shiftFwd',
                                 'pk': Order.objects.first().pk,
                                 'action': 'kanban-jump',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(data['html_id'], '#order-status')
        self.assertTrue(data['form_is_valid'])

    def test_post_kanban_jump_origin_kanban_view(self):
        """Just test the existence."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'origin': 'kanban-shiftFwd',
                                 'pk': Order.objects.first().pk,
                                 'action': 'kanban-jump',
                                 'test': True,
                                 })
        common_vars = ('icebox', 'queued', 'in_progress', 'waiting', 'done',
                       'update_date', 'amounts')
        for var in common_vars:
            self.assertTrue(var in resp.context)
        self.assertTemplateUsed('includes/kanban_columns.html')

    def test_post_kanban_jump_origin_kanban_view_json_response(self):
        resp = self.client.post(reverse('orders-CRUD'),
                                {'origin': 'kanban-shiftFwd',
                                 'pk': Order.objects.first().pk,
                                 'action': 'kanban-jump',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(data['html_id'], '#kanban-columns')
        self.assertTrue(data['form_is_valid'])

    def test_post_unknown_action_raises_500(self):
        """Action should exist."""
        resp = self.client.post(reverse('orders-CRUD'),
                                {'delivery': date(2017, 1, 1),
                                 'pk': Order.objects.first().pk,
                                 'action': 'void',
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'The action was not found.')


class ItemsCRUDTests(TestCase):
    """Test the ItemsCRUD view."""

    def setUp(self):
        User.objects.create_user(
            username='user', is_staff=True, password='test')

        # Create some different items
        item = Item.objects.create
        [item(name='test', fabrics=10, item_type=it, stocked=10, )
            for it in ('2', '3')]

        self.client.login(username='user', password='test')

    def test_get_data_is_dict(self):
        item = Item.objects.last()
        payload = {'action': 'edit-stock', 'item_pk': item.pk, }
        resp = self.client.get(reverse('items-CRUD'), payload)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(data, dict)

    def test_get_item_none_returns_404(self):
        payload = {'action': 'edit-stock', 'test': True}
        resp = self.client.get(reverse('items-CRUD'), payload)
        self.assertEqual(resp.status_code, 404)

    def test_get_edit_stock_item_instance(self):
        item = Item.objects.last()
        payload = {'action': 'edit-stock', 'item_pk': item.pk, 'test': True}
        resp = self.client.get(reverse('items-CRUD'), payload)
        self.assertEqual(resp.context['item'], item)
        self.assertIsInstance(resp.context['form'], ItemForm)
        self.assertEqual(resp.context['form'].instance, item)
        self.assertEqual(resp.context['modal_title'], 'Editar stock')
        self.assertTemplateUsed('includes/custom_forms/edit_stock.html')

    def test_get_action_was_not_recognized(self):
        payload = {'action': 'void'}
        resp = self.client.get(reverse('items-CRUD'), payload)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'Action was not recogniced.')

    def test_get_is_json_response(self):
        item = Item.objects.last()
        payload = {'action': 'edit-stock', 'item_pk': item.pk, }
        resp = self.client.get(reverse('items-CRUD'), payload)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['html'])

    def test_post_data_is_dict(self):
        item = Item.objects.last()
        payload = {'action': 'edit-stock', 'item_pk': item.pk, }
        resp = self.client.post(reverse('items-CRUD'), payload)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(data, dict)

    def test_post_item_none_returns_404(self):
        payload = {'action': 'edit-stock', 'test': True}
        resp = self.client.post(reverse('items-CRUD'), payload)
        self.assertEqual(resp.status_code, 404)

    def test_post_edit_form_is_valid_context(self):
        item = Item.objects.last()
        self.assertEqual(item.stocked, 10)
        payload = {
            'action': 'edit-stock', 'item_pk': item.pk, 'name': item.name,
            'item_type': item.item_type, 'item_class': item.item_class,
            'size': item.size, 'fabrics': item.fabrics, 'price': item.price,
            'stocked': 20, 'test': True, }
        resp = self.client.post(reverse('items-CRUD'), payload)
        self.assertTemplateUsed(resp, 'includes/stock_tabs.html')
        self.assertTrue('tab_elements' in resp.context)
        self.assertTrue('item_types' in resp.context)

        item = Item.objects.get(pk=item.pk)
        self.assertEqual(item.stocked, 20)

    def test_post_edit_form_is_valid_json_response(self):
        item = Item.objects.last()
        self.assertEqual(item.stocked, 10)
        payload = {
            'action': 'edit-stock', 'item_pk': item.pk, 'name': item.name,
            'item_type': item.item_type, 'item_class': item.item_class,
            'size': item.size, 'fabrics': item.fabrics, 'price': item.price,
            'stocked': 20, }
        resp = self.client.post(reverse('items-CRUD'), payload)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['html'])
        self.assertTrue(data['form_is_valid'])
        self.assertEqual(data['html_id'], '#stock-tabs')

    def test_post_edit_form_rejected_context(self):
        item = Item.objects.last()
        self.assertEqual(item.stocked, 10)
        payload = {
            'action': 'edit-stock', 'item_pk': item.pk, 'name': item.name,
            'item_type': item.item_type, 'item_class': item.item_class,
            'size': item.size, 'fabrics': 'VOID', 'price': item.price,
            'stocked': 20, 'test': True, }
        resp = self.client.post(reverse('items-CRUD'), payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'includes/custom_forms/edit_stock.html')
        self.assertEqual(resp.context['modal_title'], 'Editar stock')
        self.assertEqual(resp.context['item'], item)
        self.assertIsInstance(resp.context['form'], ItemForm)
        self.assertTrue(resp.context['form'].errors)

    def test_post_edit_form_rejected_json(self):
        item = Item.objects.last()
        self.assertEqual(item.stocked, 10)
        payload = {
            'action': 'edit-stock', 'item_pk': item.pk, 'name': item.name,
            'item_type': item.item_type, 'item_class': item.item_class,
            'size': item.size, 'fabrics': 'VOID', 'price': item.price,
            'stocked': 20, }

        resp = self.client.post(reverse('items-CRUD'), payload)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['html'])
        self.assertFalse(data['form_is_valid'])


class OrderItemsCRUDTests(TestCase):
    """Test the AJAX methods."""

    def setUp(self):
        """Create the necessary items on database at once."""
        u = User.objects.create_user(username='regular', password='test')

        # Create a customer
        c = Customer.objects.create(name='Customer Test', phone=0, cp=48100)

        # Create an item
        i = Item.objects.create(
            name='test', fabrics=10, price=30, notes='Notes', stocked=30)

        Timetable.objects.create(user=u)

        # Create some orders with items
        for n in range(5):
            o = Order.objects.create(
                user=u, customer=c, ref_name='test%s' % n,
                delivery=date.today(), )
            OrderItem.objects.create(reference=o, element=i, qty=n)
        # Load client
        self.client = Client()

        # Log the user in
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')

    def test_get_data_is_dict(self):
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': Order.objects.first().pk,
                                'element': Item.objects.first().pk, })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(data, dict)

    def test_get_no_reference_raises_500(self):
        resp = self.client.get(reverse('orderitems-CRUD'),)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No order was supplied')

    def test_get_picks_order(self):
        o = Order.objects.first()
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': o.pk,
                                'element': Item.objects.first().pk,
                                'test': True, })
        self.assertEquals(resp.context['order'], o)

    def test_get_picks_item(self):
        i = Item.objects.first()
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': Order.objects.first().pk,
                                'element': i.pk,
                                'test': True, })
        self.assertEquals(resp.context['base_item'], i)

    def test_get_picks_order_item(self):
        i = OrderItem.objects.first()
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': Order.objects.first().pk,
                                'element': Item.objects.first().pk,
                                'order_item': i.pk,
                                'test': True, })
        self.assertEquals(resp.context['order_item'], i)

    def test_get_template_used_for_create_and_edit(self):
        # Create
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': Order.objects.first().pk,
                                'element': Item.objects.first().pk,
                                'test': True, })
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed('includes/custom_forms/order_item.html')

        # edit
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': Order.objects.first().pk,
                                'element': Item.objects.first().pk,
                                'order_item': OrderItem.objects.first().pk,
                                'test': True, })
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed('includes/custom_forms/order_item.html')

    def test_get_edit_and_delete_order_item(self):
        i = OrderItem.objects.first()
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': Order.objects.first().pk,
                                'element': Item.objects.first().pk,
                                'order_item': i.pk,
                                'test': True, })
        self.assertIsInstance(resp.context['form'], OrderItemForm)
        self.assertEqual(resp.context['form'].instance, i)
        self.assertEqual(
            resp.context['modal_title'], 'Editar prenda en pedido.')

    def test_get_delete_template_used(self):
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': Order.objects.first().pk,
                                'element': Item.objects.first().pk,
                                'order_item': OrderItem.objects.first().pk,
                                'delete': True,
                                'test': True, })
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed('includes/delete_dialogs/order_item.html')

    def test_get_create_order_item(self):
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': Order.objects.first().pk,
                                'element': Item.objects.first().pk,
                                'test': True, })
        self.assertIsInstance(resp.context['form'], OrderItemForm)
        self.assertEqual(resp.context['modal_title'], 'Añadir prenda.')

    def test_get_is_json_response(self):
        resp = self.client.get(reverse('orderitems-CRUD'),
                               {'reference': Order.objects.first().pk,
                                'element': Item.objects.first().pk, })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)
        self.assertTrue(data['html'])

    def test_post_data_should_be_a_dict(self):
        """Data for AJAX request should be a dict."""
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': OrderItem.objects.first().pk,
                                 'action': 'edit-times',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(data, dict)

    def test_post_no_action_raises_500(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': OrderItem.objects.first().pk, })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No action was given.')

    def test_post_editig_deleting_raises_error(self):
        with self.assertRaises(ObjectDoesNotExist):
            self.client.post(reverse('orderitems-CRUD'),
                             {'reference': Order.objects.first().pk,
                              'element': Item.objects.first().pk,
                              'order_item_pk': 5000,  # big enough
                              'action': 'main',
                              'test': True, })

    def test_post_editig_deleting_modal_title_and_form(self):
        i = OrderItem.objects.first()
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': Order.objects.first().pk,
                                 'element': Item.objects.first().pk,
                                 'order_item_pk': i.pk,
                                 'action': 'main',
                                 'test': True, })
        self.assertEqual(
            resp.context['modal_title'], 'Editar prenda en pedido.')
        self.assertIsInstance(resp.context['form'], OrderItemForm)
        self.assertEqual(resp.context['form'].instance, i)
        self.assertTrue(resp.context['form'].is_bound)

    def test_post_creating_modal_title_and_form(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': Order.objects.first().pk,
                                 'element': Item.objects.first().pk,
                                 'action': 'main',
                                 'test': True, })
        self.assertEqual(resp.context['modal_title'], 'Añadir prenda.')
        self.assertIsInstance(resp.context['form'], OrderItemForm)
        self.assertTrue(resp.context['form'].is_bound)
        self.assertEqual(resp.context['order_item'], None)

    def test_post_action_main_raises_error_for_order_and_item(self):
        msg = 'Order matching query does not exist.'
        with self.assertRaisesMessage(ObjectDoesNotExist, msg):
            self.client.post(reverse('orderitems-CRUD'),
                             {'reference': 5000,  # big enough
                              'element': Item.objects.first().pk,
                              'order_item_pk': OrderItem.objects.first().pk,
                              'action': 'main',
                              'test': True, })

        msg = 'Item matching query does not exist.'
        with self.assertRaisesMessage(ObjectDoesNotExist, msg):
            self.client.post(reverse('orderitems-CRUD'),
                             {'reference': Order.objects.first().pk,
                              'element': 5000,  # big enough
                              'order_item_pk': OrderItem.objects.first().pk,
                              'action': 'main',
                              'test': True, })

    def test_post_action_main_estimated_times(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': Order.objects.first().pk,
                                 'element': Item.objects.first().pk,
                                 'qty': 5,
                                 'crop': timedelta(0),
                                 'sewing': timedelta(0),
                                 'iron': timedelta(0),
                                 'action': 'main',
                                 'test': True, })
        self.assertEqual(resp.context['order_est_total'], '0s')
        self.assertTrue(resp.context['data']['form_is_valid'])

    def test_post_action_main_saves_item(self):
        self.assertEqual(OrderItem.objects.count(), 5)
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': Order.objects.first().pk,
                                 'element': Item.objects.first().pk,
                                 'qty': 5,
                                 'crop': timedelta(0),
                                 'sewing': timedelta(0),
                                 'iron': timedelta(0),
                                 'action': 'main',
                                 'test': True, })
        self.assertEqual(OrderItem.objects.count(), 6)
        self.assertTrue(resp.context['data']['form_is_valid'])
        self.assertTemplateUsed('includes/item_quick_list.html')

    def test_post_action_main_updates_base_item_price(self):
        item = Item.objects.last()
        self.assertEqual(item.price, 30)
        self.assertEqual(item.notes, 'Notes')
        self.client.post(reverse('orderitems-CRUD'),
                         {'reference': Order.objects.first().pk,
                          'element': item.pk,
                          'qty': 5,
                          'crop': timedelta(0),
                          'sewing': timedelta(0),
                          'iron': timedelta(0),
                          'set-default-price': 50,
                          'action': 'main',
                          'test': True, })
        item = Item.objects.last()
        self.assertEqual(item.price, 50)
        self.assertEqual(item.notes, 'Notes Cambio de precio desde pedido')

    def test_post_action_main_cleans_base_item_price(self):
        msg = "'void' value must be a decimal number."
        with self.assertRaisesMessage(ValidationError, msg):
            self.client.post(reverse('orderitems-CRUD'),
                             {'reference': Order.objects.first().pk,
                              'element': Item.objects.last().pk,
                              'qty': 5,
                              'crop': timedelta(0),
                              'sewing': timedelta(0),
                              'iron': timedelta(0),
                              'set-default-price': 'void',
                              'action': 'main',
                              'test': True, })

    def test_post_action_main_renders_ticket_view(self):
        o = Order.objects.first()
        o.ref_name = 'Quick'
        o.save()
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': o.pk,
                                 'element': Item.objects.first().pk,
                                 'qty': 5,
                                 'crop': timedelta(0),
                                 'sewing': timedelta(0),
                                 'iron': timedelta(0),
                                 'action': 'main',
                                 'test': True, })
        self.assertEqual(resp.context['data']['html_id'], '#ticket-wrapper')
        self.assertTemplateUsed('includes/ticket.html')

    def test_post_action_main_renders_quick_list(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': Order.objects.first().pk,
                                 'element': Item.objects.first().pk,
                                 'qty': 5,
                                 'crop': timedelta(0),
                                 'sewing': timedelta(0),
                                 'iron': timedelta(0),
                                 'action': 'main',
                                 'test': True, })
        self.assertEqual(resp.context['data']['html_id'], '#quick-list')
        self.assertTemplateUsed('includes/item_quick_list.html')

    def test_post_action_main_form_not_valid(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': Order.objects.first().pk,
                                 'element': Item.objects.first().pk,
                                 'qty': 5,
                                 # 'crop': timedelta(0),  missing value
                                 'sewing': timedelta(0),
                                 'iron': timedelta(0),
                                 'action': 'main',
                                 'test': True, })
        self.assertFalse(resp.context['data']['form_is_valid'])
        self.assertTemplateUsed('includes/custom_forms/order_item.html')

    def test_post_action_delete_raises_error_orderitem_not_provided(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': Order.objects.first().pk,
                                 'element': Item.objects.first().pk,
                                 'action': 'delete',
                                 'test': True, })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No item pk was provided.')

    def test_post_action_delete_raises_error_order_not_found(self):
        item = OrderItem.objects.last()
        msg = 'Order matching query does not exist.'
        with self.assertRaisesMessage(ObjectDoesNotExist, msg):
            self.client.post(reverse('orderitems-CRUD'),
                             {'reference': 5000,  # Big enough
                              'element': item.element.pk,
                              'order_item_pk': item.pk,
                              'action': 'delete',
                              'test': True, })

    def test_post_action_delete_estimated_times(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': Order.objects.first().pk,
                                 'element': Item.objects.first().pk,
                                 'order_item_pk': OrderItem.objects.first().pk,
                                 'action': 'delete',
                                 'test': True, })
        self.assertEqual(resp.context['order_est_total'], '0s')

    def test_post_action_delete_deletes_item(self):
        item = OrderItem.objects.last()
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': item.reference.pk,
                                 'element': item.element.pk,
                                 'order_item_pk': item.pk,
                                 'action': 'delete',
                                 'test': True, })
        self.assertTrue(resp.context['data']['form_is_valid'])
        msg = 'OrderItem matching query does not exist.'
        with self.assertRaisesMessage(ObjectDoesNotExist, msg):
            OrderItem.objects.get(pk=item.pk)

    def test_post_action_delete_renders_ticket_view(self):
        o = Order.objects.first()
        o.ref_name = 'Quick'
        o.save()
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': o.pk,
                                 'element': Item.objects.first().pk,
                                 'order_item_pk': OrderItem.objects.first().pk,
                                 'qty': 5,
                                 'crop': timedelta(0),
                                 'sewing': timedelta(0),
                                 'iron': timedelta(0),
                                 'action': 'delete',
                                 'test': True, })
        self.assertEqual(resp.context['data']['html_id'], '#ticket-wrapper')
        self.assertTemplateUsed('includes/ticket.html')

    def test_post_action_delete_renders_quick_list(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'reference': Order.objects.first().pk,
                                 'element': Item.objects.first().pk,
                                 'order_item_pk': OrderItem.objects.first().pk,
                                 'qty': 5,
                                 'crop': timedelta(0),
                                 'sewing': timedelta(0),
                                 'iron': timedelta(0),
                                 'action': 'delete',
                                 'test': True, })
        self.assertEqual(resp.context['data']['html_id'], '#quick-list')
        self.assertTemplateUsed('includes/item_quick_list.html')

    def test_post_edit_times_no_pk_raises_500(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'action': 'edit-times', })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No pk was given.')

    def test_post_void_item_retunrs_404(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': int(1e5),  # big enough
                                 'action': 'edit-times',
                                 })
        self.assertEqual(resp.status_code, 404)

    def test_post_form_is_edit_times_form(self):
        item = OrderItem.objects.first()
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': item.pk,
                                 'action': 'edit-times',
                                 'test': True,
                                 })
        self.assertIsInstance(resp.context['form'], ItemTimesForm)
        self.assertEqual(resp.context['form'].instance, item)
        self.assertTrue(resp.context['form'].is_bound)

    def test_post_edit_times_actually_edits_times(self):
        item = OrderItem.objects.first()
        self.assertEqual(item.crop, timedelta(0))
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': item.pk,
                                 'action': 'edit-times',
                                 'crop': timedelta(minutes=5),
                                 'sewing': item.sewing,
                                 'iron': item.iron,
                                 'test': True,
                                 })
        item = OrderItem.objects.first()  # reload item
        self.assertEqual(item.crop, timedelta(minutes=5))

        # Now test the data var returned to AJAX
        self.assertTrue(resp.context['data']['form_is_valid'])
        self.assertEqual(resp.context['data']['html_id'], '#orderitems-list')
        self.assertTemplateUsed(resp, 'includes/orderitems_list.html')

    def test_post_edit_times_failed(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': OrderItem.objects.first().pk,
                                 'action': 'edit-times',
                                 'crop': timedelta(minutes=5),
                                 'sewing': timedelta(minutes=5),
                                 'iron': 'void',
                                 'test': True,
                                 })
        error = dict(iron=['Enter a valid duration.', ])
        self.assertFalse(resp.context['data']['form_is_valid'])
        self.assertEqual(resp.context['data']['error'], error)

    def test_post_edit_notes_no_pk_raises_500(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'action': 'edit-notes', })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No pk was given.')

    def test_post_edit_notes_void_item_retunrs_404(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': int(1e5),  # big enough
                                 'action': 'edit-notes',
                                 })
        self.assertEqual(resp.status_code, 404)

    def test_post_form_is_edit_notes_form(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': OrderItem.objects.first().pk,
                                 'action': 'edit-notes',
                                 'test': True,
                                 })
        self.assertIsInstance(resp.context['form'], OrderItemNotes)

    def test_post_edit_notes_actually_edits_notes(self):
        item = OrderItem.objects.first()
        self.assertEqual(item.description, '')
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': item.pk,
                                 'action': 'edit-notes',
                                 'description': 'foo bar',
                                 'test': True,
                                 })
        item = OrderItem.objects.first()  # reload item
        self.assertEqual(item.description, 'foo bar')

        # Now test the data var returned to AJAX
        self.assertTrue(resp.context['data']['form_is_valid'])
        self.assertEqual(resp.context['data']['html_id'],
                         '#item-details-{}'.format(item.pk))
        self.assertTemplateUsed(resp, 'includes/pqueue_element_details.html')

    def test_post_unknown_action_raises_500(self):
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': OrderItem.objects.first().pk,
                                 'action': 'void',
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'The action was not found.')

    def test_post_view_returns_a_JSON_reponse(self):
        item = OrderItem.objects.first()
        resp = self.client.post(reverse('orderitems-CRUD'),
                                {'pk': item.pk,
                                 'action': 'edit-times',
                                 'crop': timedelta(minutes=5),
                                 'sewing': item.sewing,
                                 'iron': item.iron,
                                 })
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)


class CommentsCRUD(TestCase):
    """Test the AJAX methods."""

    def setUp(self):
        """Create the necessary items on database at once."""
        u = User.objects.create_user(username='regular', password='test')

        # Create a customer
        c = Customer.objects.create(name='Customer Test', phone=0, cp=48100)

        # Create an item
        i = Item.objects.create(name='test', fabrics=10, price=30, stocked=30)

        # Create some orders with items
        for n in range(5):
            o = Order.objects.create(
                user=u, customer=c, ref_name='test%s' % n,
                delivery=date.today(), )
            OrderItem.objects.create(reference=o, element=i, qty=n)
        # Load client
        self.client = Client()

        # Log the user in
        login = self.client.login(username='regular', password='test')
        if not login:
            raise RuntimeError('Couldn\'t login')

    def test_data_should_be_a_dict(self):
        """Data for AJAX request should be a dict."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': 'test',
                                 'pk': Order.objects.first().pk,
                                 'action': 'add-comment',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertIsInstance(data, dict)

    def test_no_pk_raises_500(self):
        """PK is mandatory."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': 'test',
                                 'action': 'add-comment',
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No pk was given.')

    def test_no_action_raises_500(self):
        """Action is mandatory."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': 'test',
                                 'pk': Order.objects.first().pk,
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No action was given.')

    def test_add_comment_raises_404(self):
        """When order is not found  404 should be raised."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': 'test',
                                 'pk': 5000,
                                 'action': 'add-comment',
                                 })
        self.assertEqual(resp.status_code, 404)

    def test_add_comment_saves_new_comment(self):
        """Test the proper save of new comments."""
        order = Order.objects.first()
        self.client.post(reverse('comments-CRUD'), {'comment': 'test',
                                                    'pk': order.pk,
                                                    'action': 'add-comment',
                                                    })
        c = Comment.objects.get(comment='test')
        self.assertEqual(c.user.username, 'regular')
        self.assertEqual(c.reference, order)

    def test_add_comment_valid_form_returns_true_form_is_valid(self):
        """Successful processed orders should return form_is_valid."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': 'test',
                                 'pk': Order.objects.first().pk,
                                 'action': 'add-comment',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertTrue(data['form_is_valid'])

    def test_add_comment_valid_form_context_is_kanban_common(self):
        """Just test the existence."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': 'test',
                                 'pk': Order.objects.first().pk,
                                 'action': 'add-comment',
                                 'test': True,
                                 })
        common_vars = ('icebox', 'queued', 'in_progress', 'waiting', 'done',
                       'update_date', 'amounts')
        for var in common_vars:
            self.assertTrue(var in resp.context)

    def test_add_comment_valid_form_template(self):
        """Test the correct teplate."""
        self.client.post(
            reverse('comments-CRUD'), {'comment': 'test',
                                       'pk': Order.objects.first().pk,
                                       'action': 'add-comment',
                                       'test': True,
                                       })
        self.assertTemplateUsed('includes/kanban_columns.html')

    def test_add_comment_html_id(self):
        """Successful processed orders html id."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': 'test',
                                 'pk': Order.objects.first().pk,
                                 'action': 'add-comment',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(data['html_id'], '#kanban-columns')

    def test_add_comment_not_valid_form_returns_false_form_is_valid(self):
        """Unsuccessful processed orders should return form_is_valid false."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': '',
                                 'pk': Order.objects.first().pk,
                                 'action': 'add-comment',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertFalse(data['form_is_valid'])

    def test_edit_date_form_is_not_valid_errors(self):
        """Test the errors var."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': '',
                                 'pk': Order.objects.first().pk,
                                 'action': 'add-comment',
                                 })
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertEqual(
            data['error']['comment'], ['This field is required.', ])

    def test_unknown_action_raises_500(self):
        """Action should exist."""
        resp = self.client.post(reverse('comments-CRUD'),
                                {'comment': '',
                                 'pk': Order.objects.first().pk,
                                 'action': 'void',
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'The action was not found.')


class CashFlowIOCRUDTests(TestCase):
    """Test the ajax call for CashFlowIO model."""

    def setUp(self):
        """Create the necessary items on database at once."""
        u = User.objects.create_user(username='foo', password='bar')

        # Create a customer
        c = Customer.objects.create(name='Customer foo', phone=0, cp=48100)

        # Create an item
        i = Item.objects.create(name='test', fabrics=10, price=30, stocked=30)

        # Create some orders with items
        o = Order.objects.create(
            user=u, customer=c, ref_name='foo', delivery=date.today(), )
        OrderItem.objects.create(reference=o, element=i, qty=10)

        # Load client
        self.client = Client()

        # Log the user in
        login = self.client.login(username='foo', password='bar')
        if not login:
            raise RuntimeError('Couldn\'t login')

    def test_no_action_raises_500(self):
        """Action is mandatory."""
        o = Order.objects.first()
        resp = self.client.post(reverse('cashflowio-CRUD'),
                                {'order': o.pk,
                                 'amount': 100,
                                 'pay_method': 'C',
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'No action was given.')

    def test_form_saves_oject(self):
        o = Order.objects.first()
        resp = self.client.post(reverse('cashflowio-CRUD'),
                                {'action': 'add-prepaid',
                                 'order': o.pk,
                                 'amount': 100,
                                 'pay_method': 'C',
                                 })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertTrue(data['form_is_valid'])
        self.assertTrue(data['reload'])
        self.assertEqual(o.already_paid, 100)
        self.assertEqual(o.pending, 200)

    def test_form_throws_error(self):
        o = Order.objects.first()
        resp = self.client.post(reverse('cashflowio-CRUD'),
                                {'action': 'add-prepaid',
                                 'order': o.pk,
                                 'amount': 500,
                                 'pay_method': 'C',
                                 })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(str(resp.content, 'utf-8'))
        self.assertFalse(data['form_is_valid'])
        msg = 'No se puede pagar más de la cantidad pendiente (300.0).'
        self.assertEqual(data['errors'], msg)

    def test_action_not_found_raises_500(self):
        """Action is mandatory."""
        o = Order.objects.first()
        resp = self.client.post(reverse('cashflowio-CRUD'),
                                {'action': 'void',
                                 'order': o.pk,
                                 'amount': 500,
                                 'pay_method': 'C',
                                 })
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(
            resp.content.decode("utf-8"), 'The action was not found.')


class ChangelogTests(TestCase):
    """Test the markdown modal."""

    def setUp(self):
        # Create users
        User.objects.create_user(username='regular', password='test')

    def test_mark_down_view(self):
        """Test the proper work of view."""
        resp = self.client.get(reverse('changelog'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.content, bytes)

    def test_mark_down_view_only_accept_get(self):
        """Method should be get."""
        resp = self.client.post(reverse('changelog'))
        self.assertEqual(resp.status_code, 404)


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
        item = Item.objects.create(
            name='Test item object', fabrics=5, stocked=30)

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
        msg = 'Stocked items can\'t be queued'
        with self.assertRaisesMessage(ValidationError, msg):
            self.client.post(reverse('queue-actions'),
                             {'pk': item.pk, 'action': 'send', 'test': True})
        self.assertEqual(PQueue.objects.count(), 0)

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
            Item.objects.create(name='Test', fabrics=5, price=10, stocked=30)

    def test_fix_context_settings(self):
        """Test the proper values."""
        resp = self.client.get(reverse('item-selector'), {'test': True})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['item_types'], settings.ITEM_TYPE[1:])
        self.assertEqual(resp.context['item_classes'], settings.ITEM_CLASSES)
        self.assertEqual(resp.context['js_action_edit'], 'object-item-edit')
        self.assertEqual(
            resp.context['js_action_delete'], 'object-item-delete')

    def test_form_saves_item(self):
        """Test the proper save of new items."""
        self.client.post(reverse('item-selector'), {'name': 'test form',
                                                    'item_type': '1',
                                                    'item_class': 'S',
                                                    'size': '12',
                                                    'fabrics': 10,
                                                    'foreing': True,
                                                    'price': 10,
                                                    'stocked': 30,
                                                    })
        item = Item.objects.get(name='test form')
        self.assertEqual(item.item_type, '1')
        self.assertEqual(item.item_class, 'S')
        self.assertEqual(item.size, '12')
        self.assertEqual(item.fabrics, 10)
        self.assertTrue(item.foreing)
        self.assertEqual(item.price, 10)

    def test_invalid_form(self):
        """Test the proper response of invalid forms."""
        resp = self.client.post(reverse('item-selector'), {'name': 'test form',
                                                           'item_type': '1',
                                                           'item_class': 'S',
                                                           'size': '12',
                                                           'fabrics': 'void',
                                                           'foreing': True,
                                                           'price': 10,
                                                           'stocked': 5,
                                                           })
        self.assertEqual(
            resp.context['errors'], dict(fabrics=['Enter a number.']))

    def test_post_povides_aditional_pk(self):
        """Aditional pk should be passed down to the chain."""
        order = Order.objects.first()
        resp = self.client.post(reverse('item-selector'),
                                {'name': 'test form',
                                 'item_type': '1',
                                 'item_class': 'S',
                                 'size': '12',
                                 'fabrics': 10,
                                 'foreing': True,
                                 'price': 10,
                                 'aditionalpk': order.pk,
                                 })
        self.assertEqual(resp.context['order'], order)

    def test_item_selector_gets_order(self):
        """Test the correct pickup of order on order view."""
        order = Order.objects.first()
        resp = self.client.get(
            reverse('item-selector'), {'test': True, 'aditionalpk': order.pk})
        self.assertEqual(resp.context['order'], order)

    def test_item_selector_get_rid_of_buttons_in_orders(self):
        """Buttons should disappear in send to order."""
        order = Order.objects.first()
        resp = self.client.get(
            reverse('item-selector'), {'test': True, 'aditionalpk': order.pk})
        self.assertFalse(resp.context['js_action_edit'])
        self.assertFalse(resp.context['js_action_delete'])

    def test_item_selector_picks_up_all_the_items_get(self):
        """Test the correct filter 'all' which includes Predeterminado."""
        resp = self.client.get(reverse('item-selector'), {'test': True})
        self.assertEqual(resp.context['available_items'].count(), 4)

    def test_item_selector_picks_up_all_the_items_post(self):
        """Test the correct filter 'all' which includes Predeterminado."""
        resp = self.client.post(reverse('item-selector'),
                                {'name': 'test form',
                                 'item_type': '1',
                                 'item_class': 'S',
                                 'size': '12',
                                 'fabrics': 10,
                                 'foreing': True,
                                 'stocked': 10,
                                 'price': 10,
                                 })
        self.assertEqual(resp.context['available_items'].count(), 5)

    def test_filter_by_type_get(self):
        """Test the correct by type filter."""
        for i in range(3):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type='2', stocked=30, )
        resp = self.client.get(
            reverse('item-selector'), {'test': True, 'item-type': '2'})
        self.assertEqual(resp.context['available_items'].count(), 3)
        self.assertEqual(resp.context['data_type'], ('2', 'Pantalón'))
        for i in range(3):
            self.assertEqual(resp.context['item_names'][i].name, 'Test%s' % i)

    def test_filter_by_type_post(self):
        """Test the correct by type filter."""
        for i in range(3):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type='2', stocked=30)
        resp = self.client.post(reverse('item-selector'),
                                {'name': 'test form',
                                 'item_type': '1',
                                 'item_class': 'S',
                                 'size': '12',
                                 'fabrics': 10,
                                 'foreing': True,
                                 'filter-on-type': '2',
                                 'price': 10,
                                 })
        self.assertEqual(resp.context['available_items'].count(), 3)
        self.assertEqual(resp.context['data_type'], ('2', 'Pantalón'))
        for i in range(3):
            self.assertEqual(resp.context['item_names'][i].name, 'Test%s' % i)

    def test_filter_by_name_get(self):
        """Test the correct by name filter."""
        for i in range(3):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type=str(i + 1),
                size=str(i), stocked=30)
        resp = self.client.get(
            reverse('item-selector'),
            {'test': True, 'item-type': '1', 'item-name': 'Test0'})
        self.assertEqual(resp.context['available_items'].count(), 1)
        self.assertEqual(resp.context['item_sizes'][0].size, '0')
        self.assertEqual(resp.context['data_name'], 'Test0')

    def test_filter_by_name_post(self):
        """Test the correct by name filter."""
        for i in range(3):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type=str(i + 1),
                size=str(i), stocked=30)
        resp = self.client.post(reverse('item-selector'),
                                {'name': 'test form',
                                 'item_type': '1',
                                 'item_class': 'S',
                                 'size': '12',
                                 'fabrics': 10,
                                 'foreing': True,
                                 'filter-on-type': '1',
                                 'filter-on-name': 'Test0',
                                 'price': 10,
                                 })
        self.assertEqual(resp.context['available_items'].count(), 1)
        self.assertEqual(resp.context['item_sizes'][0].size, '0')
        self.assertEqual(resp.context['data_name'], 'Test0')

    def test_filter_by_size_get(self):
        """Test the correct by size filter."""
        for i in range(3):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type=str(i + 1),
                size=str(i), stocked=30)
        resp = self.client.get(
            reverse('item-selector'), {'test': True,
                                       'item-type': '1',
                                       'item-name': 'Test0',
                                       'item-size': '0'})
        self.assertEqual(resp.context['available_items'].count(), 1)
        self.assertEqual(resp.context['data_size'], '0')

    def test_filter_by_size_post(self):
        """Test the correct by size filter."""
        for i in range(3):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type=str(i + 1),
                size=str(i), stocked=30)
        resp = self.client.post(reverse('item-selector'),
                                {'name': 'test form',
                                 'item_type': '1',
                                 'item_class': 'S',
                                 'size': '12',
                                 'fabrics': 10,
                                 'foreing': True,
                                 'filter-on-type': '1',
                                 'filter-on-name': 'Test0',
                                 'filter-on-size': '0',
                                 'price': 10,
                                 })
        self.assertEqual(resp.context['available_items'].count(), 1)
        self.assertEqual(resp.context['data_size'], '0')

    def test_item_selector_limits_to_15(self):
        """Test the limiting results."""
        for i in range(15):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type='2', stocked=30)
        resp = self.client.get(reverse('item-selector'), {'test': True})
        self.assertEqual(resp.context['available_items'].count(), 15)

    def test_item_counts(self):
        """Test the total amount of items."""
        for i in range(10):
            Item.objects.create(
                name='Test%s' % i, fabrics=5, item_type='2', stocked=30)
        resp = self.client.get(reverse('item-selector'), {'test': True})
        self.assertEqual(resp.context['total_items'], 14)

    def test_template_used(self):
        """Test the proper template."""
        resp = self.client.get(reverse('item-selector'), {'test': True})
        self.assertTemplateUsed(resp, 'includes/item_selector.html')

    def test_return_json(self):
        """Test the proper json return."""
        resp = self.client.get(reverse('item-selector'))
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)


class CustomerHintsTests(TestCase):
    """Test the customer hints AJAX call."""

    def setUp(self):
        names = ('foo', 'bar', 'baz', 'sar', )
        for n in names:
            Customer.objects.create(name=n, phone=0, cp=0)

    def test_only_get_method_is_allowed(self):
        resp = self.client.post(reverse('customer-hints'))
        self.assertEqual(resp.status_code, 405)

    def test_no_string_raises_404(self):
        resp = self.client.get(reverse('customer-hints'))
        self.assertEqual(resp.status_code, 404)

    def test_providers_are_excluded_from_the_results(self):
        resp = self.client.get(
            reverse('customer-hints'), {'search': 'ba', 'test': True, })
        self.assertTrue(resp.context[0]['name'] in ('bar', 'baz'))
        self.assertTrue(resp.context[1]['name'] in ('bar', 'baz'))
        with self.assertRaises(KeyError):
            resp.context[2]
        c = Customer.objects.get(name='bar')
        c.provider = True
        c.save()
        resp = self.client.get(
            reverse('customer-hints'), {'search': 'ba', 'test': True, })
        self.assertNotEqual(resp.context[0]['name'], 'bar')
        with self.assertRaises(KeyError):
            resp.context[1]

    def test_searches_first_in_startswith(self):
        resp = self.client.get(
            reverse('customer-hints'), {'search': 'ba', 'test': True, })
        self.assertTrue(resp.context[0]['name'] in ('bar', 'baz'))
        self.assertTrue(resp.context[1]['name'] in ('bar', 'baz'))
        with self.assertRaises(KeyError):
            resp.context[2]

    def test_search_in_the_whole_string(self):
        resp = self.client.get(
            reverse('customer-hints'), {'search': 'ar', 'test': True, })
        self.assertTrue(resp.context[0]['name'] in ('bar', 'sar'))
        self.assertTrue(resp.context[1]['name'] in ('bar', 'sar'))
        with self.assertRaises(KeyError):
            resp.context[2]

    def test_search_cannot_find_anything(self):
        resp = self.client.get(
            reverse('customer-hints'), {'search': 'void', 'test': True, })
        self.assertEqual(resp.context[0]['name'], 'No hay coincidencias...')
        self.assertEqual(resp.context[0]['id'], 'void')
        with self.assertRaises(KeyError):
            resp.context[1]

    def test_return_json(self):
        """Test the proper json return."""
        resp = self.client.get(reverse('customer-hints'), {'search': 'void'})
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)


class GroupHintsTests(TestCase):
    """Test the customer hints AJAX call."""

    def setUp(self):
        names = ('foo', 'bar', 'baz', 'sar', )
        for n in names:
            Customer.objects.create(name=n, phone=0, cp=0, group=True)

    def test_only_get_method_is_allowed(self):
        resp = self.client.post(reverse('group-hints'))
        self.assertEqual(resp.status_code, 405)

    def test_no_string_raises_404(self):
        resp = self.client.get(reverse('group-hints'))
        self.assertEqual(resp.status_code, 404)

    def test_only_groups_are_sought(self):
        resp = self.client.get(
            reverse('group-hints'), {'search': 'ba', 'test': True, })
        self.assertTrue(resp.context[0]['name'] in ('bar', 'baz'))
        self.assertTrue(resp.context[1]['name'] in ('bar', 'baz'))
        with self.assertRaises(KeyError):
            resp.context[2]
        c = Customer.objects.get(name='bar')
        c.group = False
        c.save()
        resp = self.client.get(
            reverse('group-hints'), {'search': 'ba', 'test': True, })
        self.assertNotEqual(resp.context[0]['name'], 'bar')
        with self.assertRaises(KeyError):
            resp.context[1]

    def test_searches_first_in_startswith(self):
        resp = self.client.get(
            reverse('group-hints'), {'search': 'ba', 'test': True, })
        self.assertTrue(resp.context[0]['name'] in ('bar', 'baz'))
        self.assertTrue(resp.context[1]['name'] in ('bar', 'baz'))
        with self.assertRaises(KeyError):
            resp.context[2]

    def test_search_in_the_whole_string(self):
        resp = self.client.get(
            reverse('group-hints'), {'search': 'ar', 'test': True, })
        self.assertTrue(resp.context[0]['name'] in ('bar', 'sar'))
        self.assertTrue(resp.context[1]['name'] in ('bar', 'sar'))
        with self.assertRaises(KeyError):
            resp.context[2]

    def test_search_cannot_find_anything(self):
        resp = self.client.get(
            reverse('group-hints'), {'search': 'void', 'test': True, })
        self.assertEqual(resp.context[0]['name'], 'No hay coincidencias...')
        self.assertEqual(resp.context[0]['id'], 'void')
        with self.assertRaises(KeyError):
            resp.context[1]

    def test_return_json(self):
        """Test the proper json return."""
        resp = self.client.get(reverse('group-hints'), {'search': 'void'})
        self.assertIsInstance(resp, JsonResponse)
        self.assertIsInstance(resp.content, bytes)


#
#
#
#
