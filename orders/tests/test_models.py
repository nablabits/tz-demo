"""Test the app models."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.utils import DataError, IntegrityError
from django.test import TestCase, tag
from django.utils import timezone

from orders.models import (BankMovement, Comment, Customer, Expense, Invoice,
                           Item, Order, OrderItem, PQueue, Timetable, )

from decouple import config

from todoist.api import TodoistAPI


class ModelTest(TestCase):
    """Test the models."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a user
        User.objects.create_user(username='user', is_staff=True,
                                 is_superuser=True)

        # Create a customer
        Customer.objects.create(name='Customer Test',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                notes='Default note',
                                cp='48100')

        # Create  an order
        customer = Customer.objects.get(name='Customer Test')
        Order.objects.create(user=User.objects.all()[0],
                             customer=customer,
                             ref_name='example',
                             delivery=date(2018, 2, 1),
                             waist=10,
                             chest=20,
                             hip=30,
                             lenght=40,
                             others='Custom notes',
                             budget=2000,
                             prepaid=1000)

        # Create comment
        Comment.objects.create(user=User.objects.all()[0],
                               reference=Order.objects.all()[0],
                               comment='This is a comment')

    def test_customer_creation(self):
        """Test the customer creation."""
        customer = Customer.objects.get(name='Customer Test')
        self.assertTrue(isinstance(customer, Customer))
        self.assertEqual(customer.__str__(), 'Customer Test')

    def test_customer_provider_field(self):
        """Test the field."""
        customer = Customer.objects.create(
            name='Customer Test', address='Cache', city='This computer',
            phone='666666666', CIF='444E', cp=48003, )

        self.assertIsInstance(customer.provider, bool)
        self.assertFalse(customer.provider)
        self.assertEqual(
            customer._meta.get_field('provider').verbose_name, 'Proveedor')

    def test_order_creation(self):
        """Test the order creation."""
        order = Order.objects.first()
        order_str = str(order.pk) + ' Customer Test example'
        self.assertTrue(isinstance(order, Order))
        self.assertEqual(order.__str__(), order_str)
        self.assertTrue(order.overdue)

    def test_order_progress_status_1(self):
        """Test the proper display of progress."""
        order = Order.objects.all()[0]
        order.status = '1'
        order.ref_name = 'status changed'
        order.save()
        order = Order.objects.get(ref_name='status changed')
        self.assertEqual(order.progress, 0)

    def test_order_progress_status_2(self):
        """Test the proper display of progress."""
        order = Order.objects.all()[0]
        order.status = '2'
        order.ref_name = 'status changed'
        order.save()
        order = Order.objects.get(ref_name='status changed')
        self.assertEqual(order.progress, 0)

    def test_order_progress_status_3(self):
        """Test the proper display of progress."""
        order = Order.objects.all()[0]
        order.status = '3'
        order.ref_name = 'status changed'
        order.save()
        order = Order.objects.get(ref_name='status changed')
        self.assertEqual(order.progress, 25)

    def test_order_progress_status_4(self):
        """Test the proper display of progress."""
        order = Order.objects.all()[0]
        order.status = '4'
        order.ref_name = 'status changed'
        order.save()
        order = Order.objects.get(ref_name='status changed')
        self.assertEqual(order.progress, 50)

    def test_order_progress_status_5(self):
        """Test the proper display of progress."""
        order = Order.objects.all()[0]
        order.status = '5'
        order.ref_name = 'status changed'
        order.save()
        order = Order.objects.get(ref_name='status changed')
        self.assertEqual(order.progress, 75)

    def test_order_progress_status_6(self):
        """Test the proper display of progress."""
        order = Order.objects.all()[0]
        order.status = '6'
        order.ref_name = 'status changed'
        order.save()
        order = Order.objects.get(ref_name='status changed')
        self.assertEqual(order.progress, 100)

    def test_comment_creation(self):
        """Test the comment creation."""
        comment = Comment.objects.all()[0]
        today = date.today()
        comment_str = ('El ' + str(today) + ', user comentó en ' +
                       str(comment.reference.pk) + ' Customer Test example')
        self.assertTrue(isinstance(comment, Comment))
        self.assertEqual(comment.__str__(), comment_str)


class TestCustomer(TestCase):
    """Test the attributes & the methods of customer model."""

    def test_email_name(self):
        """Test the correct output for email comunications."""
        c = Customer.objects.create(
            name='teSt With RaNDom eNtries', phone=0, cp=0, )
        self.assertEqual(c.email_name(), 'Test')


class TestOrders(TestCase):
    """Test the Order model."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a user
        User.objects.create_user(username='user', is_staff=True,
                                 is_superuser=True)

        # Create a customer
        Customer.objects.create(name='Customer Test',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                notes='Default note',
                                cp='48100')

        Item.objects.create(name='test', fabrics=10, price=30)

    def test_confirmed_default_true(self):
        """Confirmed field should be bool and true by default."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='Test', delivery=date.today())
        self.assertIsInstance(order.confirmed, bool)
        self.assertTrue(order.confirmed)

    def test_trapuzarrak_orders_are_always_confirmed(self):
        """Trapuzarrak are not allowed to be unconfirmed."""
        user = User.objects.first()
        tz = Customer.objects.create(name='TraPuZarrak', phone=0, cp=0)
        order = Order.objects.create(
            user=user, delivery=date.today(), customer=tz, ref_name='Tz Order',
            confirmed=False, )

        # New created TZ orders should be confirmed
        self.assertTrue(order.confirmed)

        # Changing to tz customer should change also the confirmation status
        order.customer = Customer.objects.first()
        order.confirmed = False
        order.save()
        self.assertFalse(Order.objects.get(pk=order.pk).confirmed)
        order.customer = tz
        order.save()
        self.assertTrue(Order.objects.get(pk=order.pk).confirmed)

    def test_budget_and_prepaid_can_be_null(self):
        """Test the emptyness of fields and default value."""
        user = User.objects.first()
        c = Customer.objects.first()
        Order.objects.create(
            user=user, customer=c, ref_name='No Budget nor prepaid',
            delivery=date.today())
        order = Order.objects.get(ref_name='No Budget nor prepaid')
        self.assertEqual(order.prepaid, 0)

    def test_custom_manager_active(self):
        """Test the active custom manager."""
        u = User.objects.first()
        c = Customer.objects.first()
        for i in range(4):
            Order.objects.create(
                user=u, customer=c, ref_name='Test', delivery=date.today())
        self.assertEqual(Order.active.count(), 4)
        delivered, cancelled = Order.active.all()[:2]
        delivered.status = '7'
        delivered.save()
        cancelled.status = '8'
        cancelled.save()
        self.assertEqual(Order.active.count(), 2)

    def test_custom_manager_pending(self):
        """Test the pending custom manager."""
        u = User.objects.first()
        c = Customer.objects.first()
        for i in range(5):
            Order.objects.create(
                user=u, customer=c, ref_name='Test', delivery=date.today())
        self.assertEqual(Order.pending_orders.count(), 5)
        cancelled, old, invoiced = Order.pending_orders.all()[:3]
        cancelled.status = '8'
        cancelled.save()
        old.delivery = date(2018, 12, 31)
        old.save()
        OrderItem.objects.create(
            reference=invoiced, element=Item.objects.last())
        Invoice.objects.create(reference=invoiced)
        self.assertEqual(Order.pending_orders.count(), 2)

    def test_custom_manager_outdated(self):
        """Test the outdated custom manager."""
        u = User.objects.first()
        c = Customer.objects.first()
        for i in range(3):
            Order.objects.create(
                user=u, customer=c, ref_name='Test', delivery=date.today())
        self.assertEqual(Order.outdated.count(), 0)
        past = Order.objects.first()
        past.delivery = date.today() - timedelta(days=5)
        past.save()
        self.assertEqual(Order.outdated.count(), 1)

    def test_custom_manager_obsolete(self):
        """Test the obsolete order custom manager."""
        u = User.objects.first()
        c = Customer.objects.first()
        express = Customer.objects.create(name='express', phone=0, cp=0)

        # First a common order
        Order.objects.create(
            user=u, customer=c, ref_name='Test', delivery=date.today())

        # Now an invoiced express order
        invoiced = Order.objects.create(
            user=u, customer=express, ref_name='Test', delivery=date.today())
        OrderItem.objects.create(
            reference=invoiced, element=Item.objects.last())
        Invoice.objects.create(reference=invoiced)

        # finally an obsolete order, invoice missing
        obsolete = Order.objects.create(
            user=u, customer=express, ref_name='Obsolete',
            delivery=date.today())
        OrderItem.objects.create(
            reference=obsolete, element=Item.objects.last())

        self.assertEqual(Order.objects.count(), 3)  # total orders
        self.assertEqual(Order.obsolete.count(), 1)
        self.assertEqual(Order.obsolete.first().ref_name, 'Obsolete')

    def test_overdue(self):
        """Test the overdue attribute."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date(2017, 1, 1))
        self.assertTrue(order.overdue)

    def test_overdue_has_no_effect_on_delivered_orders(self):
        """Delivered orders can't be overdued."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date(2017, 1, 1))
        order.status = '7'
        order.save()
        order = Order.objects.get(pk=order.pk)
        self.assertFalse(order.overdue)

    def test_total_amount(self):
        """Test the correct sum of all items."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date.today())
        for i in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.assertEqual(order.total, 150)

    def test_total_amount_before_taxes(self):
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date.today())
        for i in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.assertEqual(order.total_bt, round(150 / 1.21, 2))

    def test_vat(self):
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date.today())
        for i in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.assertEqual(order.vat, round(150 * .21 / 1.21, 2))

    def test_pending_amount(self):
        """Test the correct pending amount."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date.today(),
            prepaid=10)
        for i in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.assertEqual(order.pending, -140)

    def test_invoiced(self):
        """Test the invoiced property."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date.today(),
            prepaid=50)
        self.assertFalse(order.invoiced)
        for i in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        Invoice.objects.create(reference=order)
        self.assertTrue(order.invoiced)

    def test_invoiced_returns_true_with_older_orders(self):
        """Orders previous to 2019 should appear as invoiced."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test',
            delivery=date(2018, 12, 31), prepaid=50, )
        self.assertTrue(order.invoiced)

    def test_the_count_of_times_per_item_in_an_order(self):
        """Test the correct output of count times per order."""
        order = Order.objects.create(user=User.objects.all()[0],
                                     customer=Customer.objects.all()[0],
                                     ref_name='Test%',
                                     delivery=date.today(),
                                     budget=100,
                                     prepaid=100)
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i,
                                     crop=time(5), sewing=time(3),
                                     iron=time(0))
        self.assertEqual(order.times[0], 4)
        self.assertEqual(order.times[1], 6)

    def test_count_of_times_should_esclude_stock_items(self):
        """Stock has no timing, since it should aready have."""
        order = Order.objects.create(user=User.objects.all()[0],
                                     customer=Customer.objects.all()[0],
                                     ref_name='Test%',
                                     delivery=date.today(),
                                     budget=100,
                                     prepaid=100)
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i,
                                     crop=time(5), sewing=time(3),
                                     iron=time(0))
        stocked = OrderItem.objects.all()[0]
        stocked.stock = True
        stocked.save()
        self.assertEqual(order.times[0], 2)
        self.assertEqual(order.times[1], 3)

    def test_has_no_items(self):
        """Test the order has no items."""
        order = Order.objects.create(user=User.objects.all()[0],
                                     customer=Customer.objects.all()[0],
                                     ref_name='Test%',
                                     delivery=date.today(),
                                     budget=100,
                                     prepaid=100)
        self.assertTrue(order.has_no_items)
        item = Item.objects.create(name='Test item', fabrics=2)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i,
                                     crop=time(5), sewing=time(3),
                                     iron=time(0))
        order = Order.objects.get(pk=order.pk)
        self.assertFalse(order.has_no_items)

    def test_has_comments(self):
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today(),
                                 )
        self.assertFalse(o.has_comments)
        Comment.objects.create(
            user=User.objects.all()[0], reference=o, comment='Test')
        o = Order.objects.get(pk=o.pk)
        self.assertTrue(o.has_comments)

    def test_order_estimated_time(self):
        # Create previous orders
        older = Order.objects.create(user=User.objects.first(),
                                     customer=Customer.objects.first(),
                                     ref_name='older',
                                     delivery=date.today(),
                                     )
        items = [Item.objects.create(
            name=s, fabrics=10, price=30) for s in ('a', 'b', 'c',)]

        for item in items:
            OrderItem.objects.create(
                element=item, qty=10, reference=older,
                crop=timedelta(seconds=10),
                sewing=timedelta(seconds=20),
                iron=timedelta(seconds=30), )

        curr = Order.objects.create(
            user=User.objects.first(),
            customer=Customer.objects.first(),
            ref_name='current',
            delivery=date.today()
        )

        OrderItem.objects.create(element=items[0], qty=5, reference=curr)
        OrderItem.objects.create(element=items[1], qty=7, reference=curr)

        curr = Order.objects.get(pk=curr.pk)

        self.assertEqual(curr.estimated_time, (5+7, 2*(5+7), 3*(5+7)))

    def test_deliver(self):
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today() - timedelta(days=2),
                                 )
        o.deliver()
        order = Order.objects.get(pk=o.pk)
        self.assertEqual(order.status, '7')
        self.assertEqual(order.delivery, date.today())

    def test_kanban_jumps(self):
        """Test the correct jump within kanban stages."""
        order = Order.objects.create(user=User.objects.all()[0],
                                     customer=Customer.objects.all()[0],
                                     ref_name='Test%',
                                     delivery=date.today(),
                                     budget=100,
                                     prepaid=100)
        self.assertEqual(order.status, '1')

        # switch to queued
        order.kanban_forward()
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '2')

        # switch to in progress
        order.kanban_forward()
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '3')

        # switch to waiting
        order.kanban_forward()
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '6')

        # switch to delivered
        order.kanban_forward()
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '7')

        # switch back to in_progress
        order.status = '6'
        order.save()
        order.kanban_backward()
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '3')

        # switch back to queued
        order.kanban_backward()
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '2')

        # switch back to queued
        order.kanban_backward()
        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, '1')

    def test_kanban_jump_forward_raises_error(self):
        """Status 7 & 8 should raise an exeption."""
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today(),
                                 )
        for s in ('7', '8'):
            o.status = s
            o.save()
            with self.assertRaises(ValueError):
                o.kanban_forward()

    def test_kanban_jump_backward_raises_error(self):
        """Status 1, 7 & 8 should raise an exeption."""
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today(),
                                 )
        for s in ('1', '7', '8'):
            o.status = s
            o.save()
            with self.assertRaises(ValueError):
                o.kanban_backward()


@tag('todoist')
class TestTodoist(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a user
        User.objects.create_user(username='user', is_staff=True,
                                 is_superuser=True)

        # Create a customer
        Customer.objects.create(name='Todoist test customer',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                notes='Default note',
                                cp='48100')

    def test_sync(self):
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today() - timedelta(days=2),
                                 )
        # First ensure that attributes don't exist prior to sync
        with self.assertRaises(AttributeError):
            o.t_api
        with self.assertRaises(AttributeError):
            o.t_pid

        # Now sync to create them
        o.t_sync()
        self.assertTrue(o.t_api)
        self.assertIsInstance(o.t_api, TodoistAPI)
        self.assertFalse(o.t_pid)

        # Now create a project to check pid true
        name = '%s.%s' % (o.pk, o.customer.name)
        o.t_api.projects.add(name=name, parent_id=config('APP_ID'))
        a = o.t_api.commit()
        o.t_sync()
        self.assertEqual(o.t_pid, a['temp_id_mapping'].popitem()[1])

        # Finally, delete the project from todoist
        project = o.t_api.projects.get_by_id(o.t_pid)
        project.delete()
        o.t_api.commit()

    def test_create_todoist(self):
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today() - timedelta(days=2),
                                 )
        # First ensure that attributes don't exist prior to sync
        with self.assertRaises(AttributeError):
            o.t_api
        with self.assertRaises(AttributeError):
            o.t_pid

        # Create the project since it doesn't exist yet
        self.assertTrue(o.create_todoist())

        # Sync to reject project creation
        o.t_sync()
        self.assertFalse(o.create_todoist())

        # Finally, delete the project from todoist
        project = o.t_api.projects.get_by_id(o.t_pid)
        project.delete()
        o.t_api.commit()

    def test_tasks(self):
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today() - timedelta(days=2),
                                 )
        # First ensure that attributes don't exist prior to sync
        with self.assertRaises(AttributeError):
            o.t_api
        with self.assertRaises(AttributeError):
            o.t_pid

        # Since the sync is performed by the decorator, there are no tasks yet
        self.assertFalse(o.tasks())

        # Create the project on todoist and sync
        o.create_todoist()
        o = Order.objects.get(pk=o.pk)
        o.t_sync()

        # create one task
        o.t_api.items.add('Task1', project_id=o.t_pid)
        o.t_api.commit()
        o.t_sync()
        self.assertTrue(o.tasks())

        # Finally, delete the project from todoist
        project = o.t_api.projects.get_by_id(o.t_pid)
        project.delete()
        o.t_api.commit()

    def test_is_archived(self):
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today() - timedelta(days=2),
                                 )

        # First ensure that attributes don't exist prior to sync
        with self.assertRaises(AttributeError):
            o.t_api
        with self.assertRaises(AttributeError):
            o.t_pid

        # Since there's no project created, is_archived is False
        self.assertFalse(o.is_archived())

        # Create the project on todoist and sync
        o.create_todoist()
        o = Order.objects.get(pk=o.pk)
        o.t_sync()

        # Archive it and test
        project = o.t_api.projects.get_by_id(o.t_pid)
        project.archive()
        o.t_api.commit()
        self.assertTrue(o.is_archived())

        # Finally, destroy the project in todoist
        project.delete()
        o.t_api.commit()

    def test_archive(self):
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today() - timedelta(days=2),
                                 )

        # First ensure that attributes don't exist prior to sync
        with self.assertRaises(AttributeError):
            o.t_api
        with self.assertRaises(AttributeError):
            o.t_pid

        # Since there's no project created, archived returns false
        self.assertFalse(o.archive())

        # Create the project on todoist and sync
        o.create_todoist()
        o = Order.objects.get(pk=o.pk)

        # Archive it and test
        self.assertTrue(o.archive())
        self.assertFalse(o.archive())

        # Finally, destroy the project in todoist
        project = o.t_api.projects.get_by_id(o.t_pid)
        project.delete()
        o.t_api.commit()

    def test_unarchive(self):
        o = Order.objects.create(user=User.objects.all()[0],
                                 customer=Customer.objects.all()[0],
                                 ref_name='Test%',
                                 delivery=date.today() - timedelta(days=2),
                                 )

        # First ensure that attributes don't exist prior to sync
        with self.assertRaises(AttributeError):
            o.t_api
        with self.assertRaises(AttributeError):
            o.t_pid

        # Since there's no project created, archived returns false
        self.assertFalse(o.unarchive())

        # Create the project on todoist and sync
        o.create_todoist()
        o = Order.objects.get(pk=o.pk)

        # Archive it and test
        self.assertTrue(o.archive())
        self.assertTrue(o.unarchive())

        # Test that is correctly placed
        project = o.t_api.projects.get_by_id(o.t_pid)
        self.assertEqual(project['parent_id'], int(config('APP_ID')))

        # Finally, destroy the project in todoist
        project.delete()
        o.t_api.commit()


class TestObjectItems(TestCase):
    """Test the Item model."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a user
        User.objects.create_user(username='user', is_staff=True,
                                 is_superuser=True)

        # Create a customer
        Customer.objects.create(name='Customer Test',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                notes='Default note',
                                cp='48100')

        # Create  an order
        Order.objects.create(user=User.objects.first(),
                             customer=Customer.objects.first(),
                             ref_name='example',
                             delivery=date.today(),
                             budget=2000,
                             prepaid=1000)

    def test_item_object_creation(self):
        """Test the proper creation of item objects."""
        Item.objects.create(name='Test item',
                            item_type='2',
                            item_class='S',
                            size='10',
                            notes='Default notes',
                            fabrics=5.2)
        self.assertTrue(Item.objects.get(name='Test item'))

    def test_item_duplicate_raises_error(self):
        """Clean method should raise ValidationError."""
        original = Item.objects.create(name='duplicate', fabrics=0, size='2')
        duplicated = Item(name='duplicate', fabrics=0, size='2')
        self.assertEqual(original.name, duplicated.name)
        self.assertEqual(original.item_type, duplicated.item_type)
        self.assertEqual(original.item_class, duplicated.item_class)
        self.assertEqual(original.size, duplicated.size)
        with self.assertRaises(ValidationError):
            duplicated.clean()

    def test_object_item_allows_6_chars_on_size(self):
        """Items's size should allow up to 6 chars."""
        Item.objects.create(name='Test 6 char item',
                            item_type='2',
                            item_class='S',
                            size='6chars',
                            notes='Default notes',
                            fabrics=5.2)
        self.assertTrue(Item.objects.get(name='Test 6 char item'))

    def test_item_object_foreing_is_default_false(self):
        """Item's default origin should be false (ie homemade)."""
        Item.objects.create(name='Test 6 char item',
                            item_type='2',
                            item_class='S',
                            size='6chars',
                            notes='Default notes',
                            fabrics=5.2)

        item = Item.objects.get(name='Test 6 char item')
        self.assertFalse(item.foreing)

    def test_item_object_price_attr(self):
        """Item's default attributes."""
        item = Item.objects.create(name='default price', fabrics=1)
        self.assertEqual(item.price, 0)
        self.assertEqual(item._meta.get_field('price').verbose_name,
                         'Precio unitario')

    def test_item_price_values(self):
        """Test the values for the field."""
        Item.objects.create(name='default price', fabrics=1, price=1234.45)

        with self.assertRaises(ValidationError):
            Item.objects.create(name='default price', fabrics=1,
                                price='invalid')

    def test_default_item_object_should_be_automatically_created(self):
        """The default item object is created by a migration."""
        self.assertTrue(Item.objects.get(name='Predeterminado'))

    def test_the_item_object_named_default_is_reserved(self):
        """The item obj named default is reserved & raises ValidationError."""
        with self.assertRaises(ValidationError):
            Item.objects.create(name='Predeterminado',
                                item_type='0',
                                item_class='0',
                                size='0',
                                fabrics=2.2)

    def test_item_average_times(self):
        items = [Item.objects.create(
            name=s, fabrics=10, price=30) for s in ('a', 'b', 'c',)]

        for n, item in enumerate(items):
            OrderItem.objects.create(
                element=item, qty=10 * n + 1, reference=Order.objects.first(),
                crop=timedelta(seconds=10),
                sewing=timedelta(seconds=20),
                iron=timedelta(seconds=30), )

        not_timed_order = Order.objects.create(
            user=User.objects.first(),
            customer=Customer.objects.first(),
            ref_name='No time order',
            delivery=date.today(), )

        OrderItem.objects.create(element=items[0], reference=not_timed_order)

        # reload the item list
        items = [Item.objects.get(pk=item.pk) for item in items]

        self.assertEqual(items[0].avg_crop, timedelta(seconds=10))
        self.assertEqual(items[1].avg_crop, timedelta(seconds=10) / 11)
        self.assertEqual(items[2].avg_crop, timedelta(seconds=10) / 21)

        self.assertEqual(items[0].avg_sewing, timedelta(seconds=20))
        self.assertEqual(items[1].avg_sewing, timedelta(seconds=20) / 11)
        self.assertEqual(items[2].avg_sewing, timedelta(seconds=20) / 21)

        self.assertEqual(items[0].avg_iron, timedelta(seconds=30))
        self.assertEqual(items[1].avg_iron, timedelta(seconds=30) / 11)
        self.assertEqual(items[2].avg_iron, timedelta(seconds=30) / 21)


class TestOrderItems(TestCase):
    """Test the orderItem model."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a user
        user = User.objects.create_user(username='user', is_staff=True,
                                        is_superuser=True)

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
        Order.objects.create(user=user,
                             customer=customer,
                             ref_name='Test order',
                             delivery=date.today(),
                             budget=2000,
                             prepaid=0)
        # Create item
        Item.objects.create(name='Test item', fabrics=5, price=10)

    def test_delete_obj_item_is_protected(self):
        """Deleting the reference should be forbidden."""
        item = Item.objects.first()
        OrderItem.objects.create(
            element=item, reference=Order.objects.first())
        with self.assertRaises(IntegrityError):
            item.delete()

    def test_orderitem_stock(self):
        """Items are by default new produced for orders."""
        item = OrderItem.objects.create(element=Item.objects.first(),
                                        reference=Order.objects.first(),
                                        )
        self.assertFalse(item.stock)
        self.assertIsInstance(item.stock, bool)
        self.assertEqual(item._meta.get_field('stock').verbose_name, 'Stock')

    def test_add_items_to_orders(self):
        """Test the proper item attachs to orders."""
        order = Order.objects.first()
        item = Item.objects.create(name='Test item', fabrics=5.2)
        OrderItem.objects.create(description='Test item',
                                 reference=order,
                                 element=item)

        created_item = OrderItem.objects.get(description='Test item')
        self.assertEqual(created_item.reference, order)
        self.assertEqual(created_item.element, item)
        self.assertEqual(created_item.qty, 1)
        self.assertEqual(created_item.crop, timedelta(0))
        self.assertEqual(created_item.sewing, timedelta(0))
        self.assertEqual(created_item.iron, timedelta(0))
        self.assertFalse(created_item.fit)

    def test_orderitem_price_attr(self):
        """Order item's default attributes."""
        item = OrderItem.objects.create(
            element=Item.objects.first(), reference=Order.objects.first(),
            price=0)
        self.assertEqual(item.price, 0)
        self.assertEqual(item._meta.get_field('price').verbose_name,
                         'Precio unitario')

    def test_orderitem_default_price(self):
        """When no price is given, pickup the object item's default."""
        object_item = Item.objects.first()
        object_item.price = 200
        object_item.name = 'Item default price'
        object_item.save()
        item = OrderItem.objects.create(
            element=object_item, reference=Order.objects.first(), )
        self.assertEqual(item.price, 200)

    def test_orderitem_stock_items_have_no_times(self):
        item = OrderItem.objects.create(
            element=Item.objects.first(),
            reference=Order.objects.first(),
            crop=timedelta(5), sewing=timedelta(10), iron=timedelta(10),
            stock=True
        )

        self.assertEqual(item.crop, timedelta(0))
        self.assertEqual(item.sewing, timedelta(0))
        self.assertEqual(item.iron, timedelta(0))

    def test_orderitem_stock_true_for_express_orders(self):
        """Express orders only contain stocked items."""
        order = Order.objects.first()
        order.ref_name = 'Quick'
        order.save()
        object_item = Item.objects.first()
        item = OrderItem.objects.create(
            element=object_item, reference=Order.objects.first(), )
        self.assertTrue(item.stock)

    def test_orderitem_stock_false_for_foreign_items(self):
        """Ensure that foreign items are not stock."""
        order = Order.objects.first()
        order.ref_name = 'Quick'
        order.save()
        object_item = Item.objects.last()
        object_item.foreing = True
        object_item.save()
        item = OrderItem.objects.create(
            element=object_item, reference=Order.objects.first(), stock=True)
        self.assertFalse(item.stock)

    def test_stock_items_cant_be_fit(self):
        """Ensure that fit items cant be stock."""
        order = Order.objects.first()
        item = Item.objects.last()
        o_item = OrderItem.objects.create(
            element=item, reference=order, fit=True, stock=True)
        self.assertFalse(o_item.fit)
        self.assertTrue(o_item.stock)
        o_item.fit = True
        o_item.save()
        self.assertFalse(OrderItem.objects.get(pk=o_item.pk).fit)

    def test_add_items_to_orders_default_item(self):
        """If no element is selected, Predetermiando is default."""
        order = Order.objects.first()
        item = Item.objects.get(name='Predeterminado')
        OrderItem.objects.create(description='Test item',
                                 reference=order, )

        created_item = OrderItem.objects.get(description='Test item')
        self.assertEqual(created_item.element, item)

    def test_custom_manager_active(self):
        """Test the proper custom manager."""
        u = User.objects.first()
        c = Customer.objects.first()

        # Create some orders
        for i in range(6):
            Order.objects.create(
                user=u, customer=c, ref_name='Test', delivery=date.today())

        # Add an item to these orders
        for i in Order.objects.all():
            OrderItem.objects.create(reference=i, element=Item.objects.last())

        self.assertEqual(OrderItem.active.count(), 7)

        # Now modify
        cancelled, old, invoiced, tz_owned = Order.pending_orders.all()[:4]
        cancelled.status = '8'
        cancelled.save()
        old.delivery = date(2018, 12, 31)
        old.save()
        Invoice.objects.create(reference=invoiced)
        tz = Customer.objects.create(name='Trapuzarrak', phone=0, cp=12)
        tz_owned.customer = tz
        tz_owned.save()

        self.assertEqual(OrderItem.active.count(), 3)

    def test_items_time_quality_property(self):
        """Test the proper value for timing."""
        order = Order.objects.first()
        order_item = OrderItem.objects.create(description='Test item',
                                              reference=order,
                                              crop=timedelta(2),
                                              sewing=timedelta(2),
                                              iron=timedelta(2),)
        self.assertEqual(order_item.time_quality, 3)
        order_item.sewing = timedelta(0)
        self.assertEqual(order_item.time_quality, 2)
        order_item.iron = timedelta(0)
        self.assertEqual(order_item.time_quality, 1)
        order_item.crop = timedelta(0)
        self.assertEqual(order_item.time_quality, 0)

    def test_items_subtotal(self):
        """Test the proepr value of subtotal."""
        item = OrderItem.objects.create(
            element=Item.objects.first(), reference=Order.objects.first(),
            qty=5, price=10
        )
        self.assertEqual(item.subtotal, 50)

    def test_price_bt(self):
        item = OrderItem.objects.create(
            element=Item.objects.first(), reference=Order.objects.first(),
            qty=5, price=10
        )
        self.assertEqual(item.price_bt, round(10 / 1.21, 2))

    def test_subtotal_bt(self):
        item = OrderItem.objects.create(
            element=Item.objects.first(), reference=Order.objects.first(),
            qty=5, price=10
        )
        self.assertEqual(item.subtotal_bt, round(50 / 1.21, 2))

    def test_estimated_time(self):
        items = [Item.objects.create(
            name=s, fabrics=10, price=30) for s in ('a', 'b', 'c',)]

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

        test_item = OrderItem.objects.create(
            element=items[0], qty=5, reference=order)

        self.assertEqual(test_item.estimated_time, (50, 100, 150))

    def test_prettfied_est(self):
        items = [Item.objects.create(
            name=s, fabrics=10, price=30) for s in ('a', 'b', 'c',)]

        for n, item in enumerate(items):
            OrderItem.objects.create(
                element=item, qty=10 * n + 1, reference=Order.objects.first(),
                crop=timedelta(hours=10),
                sewing=timedelta(hours=20),
                iron=timedelta(hours=30), )

        # Create an order
        order = Order.objects.create(
            user=User.objects.first(),
            customer=Customer.objects.first(),
            ref_name='Current',
            delivery=date.today(), )

        test_item = OrderItem.objects.create(
            element=items[0], qty=5, reference=order)

        self.assertEqual(test_item.prettified_est, ['2.0h', '4.0h', '6.0h'])


class TestPQueue(TestCase):
    """Test the production queue model."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a user
        user = User.objects.create_user(username='user', is_staff=True,
                                        is_superuser=True)

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

    def test_item_is_a_one_to_one_field(self):
        """That is, each item should appear once on the table."""
        item1 = OrderItem.objects.first()
        PQueue.objects.create(item=item1, score=1000)
        with self.assertRaises(IntegrityError):
            PQueue.objects.create(item=item1, score=200)

    def test_item_delete_cascade(self):
        """If orderitem is deleted pqueue is so."""
        item1 = OrderItem.objects.first()
        PQueue.objects.create(item=item1, score=1000)
        self.assertTrue(PQueue.objects.all())
        item1.delete()
        self.assertFalse(PQueue.objects.all())

    def test_pqueue_pk_matches_orderitem_pk(self):
        """Since item has primary key true."""
        item1 = OrderItem.objects.first()
        pqueue_item = PQueue.objects.create(item=item1, score=1000)
        self.assertEqual(item1.pk, pqueue_item.pk)

    def test_score_is_unique(self):
        """Two elements cannot share the same score."""
        item1, item2 = OrderItem.objects.all()[:2]
        PQueue.objects.create(item=item1)  # Score: 1000
        pqueue = PQueue.objects.create(item=item2)  # To the bottom (1001)
        with self.assertRaises(IntegrityError):
            pqueue.score = 1000
            pqueue.save()

    def test_default_ordering(self):
        """Objects are sorted by score."""
        item1, item2, item3 = OrderItem.objects.all()
        PQueue.objects.create(item=item1)  # Score: 1000
        PQueue.objects.create(item=item2)  # To the bottom (1001)
        pqueue = PQueue.objects.create(item=item3)  # To the bottom (1002)
        queue = PQueue.objects.all()
        self.assertEqual((queue[0].score, queue[1].score, queue[2].score),
                         (1000, 1001, 1002))

        pqueue.score = 100
        pqueue.save()
        queue = PQueue.objects.all()
        self.assertEqual((queue[0].score, queue[1].score, queue[2].score),
                         (100, 1000, 1001))

    def test_stock_items_cannot_be_added(self):
        """Stock items are already produced so can't be queued."""
        item = OrderItem.objects.first()
        item.stock = True
        item.save()
        queued = PQueue(item=item)
        with self.assertRaises(ValidationError):
            queued.clean()

    def test_default_score_on_empty_table(self):
        """When saving on an empty table the initial score should be 1000."""
        pqueue = PQueue.objects.create(item=OrderItem.objects.first())
        self.assertEqual(pqueue.score, 1000)

    def test_default_score_on_table_with_negatives(self):
        """On saving in a table with negatives initial score is 1000."""
        pqueue = PQueue.objects.create(item=OrderItem.objects.first())
        self.assertEqual(pqueue.score, 1000)
        pqueue.complete()
        self.assertEqual(pqueue.score, -2)
        pqueue = PQueue.objects.create(item=OrderItem.objects.last())
        self.assertEqual(pqueue.score, 1000)

    def test_send_to_bottom_with_no_score(self):
        """On saving an object without score (new creation), send to bottom."""
        item1, item2 = OrderItem.objects.all()[:2]
        pqueue1 = PQueue.objects.create(item=item1)  # Score: 1000
        pqueue2 = PQueue.objects.create(item=item2)  # To the bottom (1001)
        self.assertTrue(pqueue1.score < pqueue2.score)
        self.assertEqual((pqueue1.score, pqueue2.score), (1000, 1001))

        pqueue2.score = None
        pqueue2.save()
        self.assertEqual(pqueue2.score, 1002)

    def test_score_0_is_reserved(self):
        """For swapping function."""
        PQueue.objects.create(item=OrderItem.objects.first(), score=0)
        self.assertEqual(PQueue.objects.count(), 1)
        queued_item = PQueue.objects.first()
        self.assertEqual(queued_item.score, 1)

    def test_queue_slides_when_one_is_already_taken(self):
        """Queue should slide to avoid integrity error."""
        order = Order.objects.first()
        item = Item.objects.first()

        # first create a decent list
        for i in range(10):
            OrderItem.objects.create(reference=order, element=item)
        score = 1
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item, score=score)
            score += 1

        self.assertEqual(PQueue.objects.count(), 13)
        self.assertEqual(PQueue.objects.first().score, 1)

        # now, create a new pqueue entry
        item = OrderItem.objects.create(reference=order,
                                        element=Item.objects.first())
        PQueue.objects.create(item=item, score=0)
        queue = PQueue.objects.all()
        self.assertEqual(queue.count(), 14)
        score = 1

        # finally, test sliding
        for item in queue:
            self.assertEqual(item.score, score)
            score += 1

    def test_top_sends_with_lowest_score(self):
        """The score for the new element should be one below the lowest."""
        order = Order.objects.first()
        item = Item.objects.first()

        # first create a decent list
        for i in range(10):
            OrderItem.objects.create(reference=order, element=item)
        score = 10
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item, score=score)
            score += 1
        last_item = PQueue.objects.last()
        self.assertEqual(last_item.score, 22)
        last_item.top()
        former_last = PQueue.objects.get(pk=last_item.pk)  # now first
        self.assertEqual(former_last.score, 9)

    def test_top_from_score_equal_to_two(self):
        """Since 1 is reserved the list should slide."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        first.score = 1
        first.save()
        last.top()
        former_first = PQueue.objects.get(pk=first.pk)  # now second
        former_last = PQueue.objects.get(pk=last.pk)  # now first
        former_mid = PQueue.objects.get(pk=mid.pk)  # now last, slide by 1
        self.assertEqual(former_last.score, 1)
        self.assertEqual(former_first.score, 2)
        self.assertEqual(former_mid.score, 1002)

    def test_up_raises_if_place(self):
        """Test up method when there is a place between two next numbers."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()

        mid.score = 1020  # move far apart
        mid.save()
        self.assertEqual(PQueue.objects.get(pk=mid.pk).score, 1020)

        mid.up()  # now raise
        self.assertEqual(PQueue.objects.get(pk=mid.pk).score, 1001)

        # try with a bigger hole
        first.score = 20
        last.score = 2000
        first.save()
        last.save()
        queue = PQueue.objects.all()
        self.assertEqual((queue[0].score, queue[1].score, queue[2].score),
                         (20, 1001, 2000))
        last.up()
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 1000)

    def test_up_if_second(self):
        """When the element is second, should call top()."""
        for item in OrderItem.objects.all()[:2]:
            PQueue.objects.create(item=item)
        first, last = PQueue.objects.all()
        last.up()
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 999)

    def test_up_if_first(self):
        """When the element is first, should warn and do nothing."""
        for item in OrderItem.objects.all()[:2]:
            PQueue.objects.create(item=item)
        first = PQueue.objects.first()
        warning = first.up()
        self.assertEqual(PQueue.objects.get(pk=first.pk).score, 1000)
        self.assertEqual(warning,
                         ('Warning: you are trying to raise an item that is ' +
                          'already on top'))

    def test_up_no_place(self):
        """When there's no place to fit in, scores should be swapped."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        self.assertEqual((first.score, mid.score, last.score),
                         (1000, 1001, 1002))
        last.up()
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 1001)
        self.assertEqual(PQueue.objects.get(pk=mid.pk).score, 1002)

    def test_down_if_last(self):
        """When the element is last, should warn and do nothing."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        last = PQueue.objects.last()
        warning = last.down()
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 1002)
        self.assertEqual(warning,
                         ('Warning: you are trying to lower an item that is ' +
                          'already at the bottom'))

    def test_down(self):
        """Lower the position of an element."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        first.down()
        self.assertEqual(PQueue.objects.get(pk=mid.pk).score, 999)
        self.assertEqual(PQueue.objects.get(pk=first.pk).score, 1000)
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 1002)

    def test_bottom_if_last(self):
        """When the element is last, should warn and do nothing."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        last = PQueue.objects.last()
        warning = last.bottom()
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 1002)
        self.assertEqual(warning,
                         ('Warning: you are trying to lower an item that is ' +
                          'already at the bottom'))

    def test_bottom(self):
        """Lower the position of an element to the bottom."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        first.bottom()
        self.assertEqual(PQueue.objects.get(pk=mid.pk).score, 1001)
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 1002)
        self.assertEqual(PQueue.objects.get(pk=first.pk).score, 1003)

    def test_complete(self):
        """Test complete method."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        for item in PQueue.objects.all()[:2]:
            item.complete()
        first, mid, last = PQueue.objects.all()
        self.assertEqual((first.score, mid.score, last.score),
                         (-3, -2, 1002))

    def test_uncomplete(self):
        """Test ucomplete method."""
        item = PQueue.objects.create(item=OrderItem.objects.first())
        item.complete()
        self.assertEqual(item.score, -2)
        item.uncomplete()
        self.assertEqual(item.score, 1000)


@tag('todoist')
class TestInvoice(TestCase):
    """Test the invoice model."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a user
        user = User.objects.create_user(
            username='user', is_staff=True, )

        # Create a customer
        customer = Customer.objects.create(
            name='Customer Test', city='NoCity', phone='6', cp='1')

        # Create an order
        order = Order.objects.create(
            user=user, customer=customer, ref_name='Test order',
            budget=2000, prepaid=0, delivery=date.today())

        # Create obj item
        item = Item.objects.create(name='Test item', fabrics=5, price=10)

        # Create orderitems
        OrderItem.objects.create(reference=order, element=item)

    def test_reference_is_a_one_to_one_field(self):
        """That is, each order should appear once on the table."""
        Invoice.objects.create(reference=Order.objects.first())
        with self.assertRaises(IntegrityError):
            Invoice.objects.create(reference=Order.objects.first())

    def test_reference_delete_cascade(self):
        """If order is deleted so is invoice."""
        order = Order.objects.first()
        Invoice.objects.create(reference=order)
        self.assertTrue(Invoice.objects.all())
        order.delete()
        self.assertFalse(Invoice.objects.all())

    def test_reference_pk_matches_invoice_pk(self):
        """Since reference has primary key true."""
        order = Order.objects.first()
        invoice = Invoice.objects.create(reference=order)
        self.assertEqual(order.pk, invoice.pk)

    def test_issued_on_is_datetime(self):
        """Test the data type and the date."""
        invoice = Invoice.objects.create(reference=Order.objects.first())
        self.assertIsInstance(invoice.issued_on, datetime)
        self.assertEqual(invoice.issued_on.date(), date.today())

    def test_tz_cannot_be_invoiced(self):
        """Ensure that tz can't be invoiced."""
        tz = Customer.objects.create(name='TraPuZarrak', phone=0, cp=0)
        tz_order = Order.objects.first()
        tz_order.customer = tz
        tz_order.save()
        with self.assertRaises(ValueError):
            Invoice.objects.create(reference=tz_order)

    def test_invoice_no_default_1(self):
        """When there're no invoices yet, the first one is 1."""
        invoice = Invoice.objects.create(reference=Order.objects.first())
        self.assertEqual(invoice.invoice_no, 1)

    def test_invoice_no_autoincrement(self):
        """When there're invoices should add one to the last one."""
        user = User.objects.first()
        customer = Customer.objects.first()
        for i in range(3):
            order = Order.objects.create(
                user=user, customer=customer, ref_name='Test%s' % i,
                budget=10, prepaid=0, delivery=date.today())
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
            Invoice.objects.create(reference=order)
        i = 1
        for invoice in Invoice.objects.reverse():
            self.assertEqual(invoice.invoice_no, i)
            i += 1

    def test_invoice_no_several_saves(self):
        """Ensure the number doesn't rise on multiple save calls."""
        invoice = Invoice.objects.create(reference=Order.objects.first())
        self.assertEqual(invoice.invoice_no, 1)
        invoice.pay_method = 'V'
        invoice.save()
        self.assertEqual(invoice.invoice_no, 1)

    def test_invoice_amount_sums(self):
        """Test the proper sum of items."""
        order = Order.objects.first()
        for i in range(3):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last(), price=20, )
        invoice = Invoice.objects.create(reference=order)
        self.assertIsInstance(invoice.amount, Decimal)
        self.assertEqual(invoice.amount, 70)

    def test_pay_method_allowed_means(self):
        """Test the proper payment methods."""
        invoice = Invoice.objects.create(reference=Order.objects.first())
        self.assertEqual(invoice.pay_method, 'C')
        for pay_method in ('V', 'T'):
            invoice.pay_method = pay_method
            invoice.full_clean()
            invoice.save()
            self.assertEqual(invoice.pay_method, pay_method)
            self.assertEqual(invoice.invoice_no, 1)

        with self.assertRaises(ValidationError):
            invoice.pay_method = 'K'
            invoice.full_clean()

    def test_total_amount_0_raises_error(self):
        """Test the proper raise when invoice has no items."""
        item = OrderItem.objects.first()
        item.delete()
        order = Order.objects.first()
        with self.assertRaises(ValidationError):
            Invoice.objects.create(reference=order)

    def test_total_amount_0_is_allowed(self):
        """But invoices with 0 amount are allowed, eg, with discount."""
        order = Order.objects.first()
        OrderItem.objects.create(
            reference=order, element=Item.objects.first(), price=100)
        OrderItem.objects.create(
            reference=order, element=Item.objects.first(), price=-110)
        invoice = Invoice.objects.create(reference=order)
        self.assertEqual(invoice.amount, 0)

    def test_invoicing_archives_todoist(self):
        order = Order.objects.first()
        OrderItem.objects.create(
            reference=order, element=Item.objects.first(), price=100)
        order.create_todoist()
        Invoice.objects.create(reference=order)
        order = Order.objects.get(pk=order.pk)
        self.assertTrue(order.is_archived())
        project = order.t_api.projects.get_by_id(order.t_pid)
        project.delete()
        order.t_api.commit()


class TestExpense(TestCase):
    """Test the expense model."""

    @classmethod
    def setUpTestData(cls):
        """Create the necessary items on database at once."""
        # Create a customer
        Customer.objects.create(
            name='Customer Test', address='Cache', city='This computer',
            phone='666666666', CIF='444E', cp=48003, provider=True, )

    def test_creation_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        expense.full_clean()
        self.assertIsInstance(expense.creation, datetime)
        self.assertTrue(expense.creation.date, date.today())
        self.assertEqual(
            expense._meta.get_field('creation').verbose_name, 'Alta')

    def test_issuer_is_foreign_key(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        expense.full_clean()
        self.assertIsInstance(expense.issuer, Customer)

    def test_delete_providers_should_raise_error(self):
        """Providers with isssued invoices should be prevented from delete."""
        issuer = Customer.objects.first()
        expense = Expense.objects.create(
            issuer=issuer, invoice_no='Test', issued_on=date.today(),
            concept='Concept', amount=100, )
        expense.full_clean()
        with self.assertRaises(IntegrityError):
            issuer.delete()

    def test_invoice_no_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        expense.full_clean()
        self.assertIsInstance(expense.invoice_no, str)
        self.assertTrue(expense.invoice_no, 'Test')
        self.assertEqual(
            expense._meta.get_field('invoice_no').verbose_name,
            'Número de factura')
        with self.assertRaises(DataError):
            expense = Expense.objects.create(
                issuer=Customer.objects.first(), invoice_no='T' * 65,
                issued_on=date.today(), concept='Concept', amount=100, )

    def test_issued_on_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        expense.full_clean()
        self.assertIsInstance(expense.issued_on, date)
        self.assertTrue(expense.issued_on, date.today())
        self.assertEqual(
            expense._meta.get_field('issued_on').verbose_name,
            'Emisión')

    def test_concept_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        expense.full_clean()
        self.assertIsInstance(expense.concept, str)
        self.assertTrue(expense.concept, 'Concept')
        self.assertEqual(
            expense._meta.get_field('concept').verbose_name,
            'Concepto')
        with self.assertRaises(DataError):
            expense = Expense.objects.create(
                issuer=Customer.objects.first(), invoice_no='Test',
                issued_on=date.today(), concept='C' * 65, amount=100, )

    def test_amount_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        expense.full_clean()
        self.assertIsInstance(expense.amount, Decimal)
        self.assertTrue(expense.amount, 100)
        self.assertEqual(
            expense._meta.get_field('amount').verbose_name,
            'Importe con IVA')

        # More decimals validation
        void = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100.35566, )
        with self.assertRaises(ValidationError):
            void.full_clean()

        # More digits validation
        with self.assertRaises(InvalidOperation):
            Expense.objects.create(
                issuer=Customer.objects.first(), invoice_no='Test',
                issued_on=date.today(), concept='Concept', amount=10**8, )

    def test_pay_method_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        expense.full_clean()
        self.assertIsInstance(expense.pay_method, str)
        self.assertTrue(expense.pay_method, 'T')
        self.assertEqual(
            expense._meta.get_field('pay_method').verbose_name,
            'Medio de pago')

    def test_in_b_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        expense.full_clean()
        self.assertIsInstance(expense.in_b, bool)
        self.assertFalse(expense.in_b)
        self.assertEqual(
            expense._meta.get_field('in_b').verbose_name,
            'En B')

    def test_notes_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100,
            notes='Notes')
        expense.full_clean()
        self.assertIsInstance(expense.notes, str)
        self.assertTrue(expense.notes, 'Notes')
        self.assertEqual(
            expense._meta.get_field('notes').verbose_name,
            'Observaciones')

    def test_no_address_raises_error(self):
        """Raise ValidationError with partially filled customers."""
        void = Customer.objects.create(
            name='Customer Test', city='This computer',
            phone='666666666', CIF='444E', cp=48003, provider=True, )
        void_expense = Expense.objects.create(
            issuer=void, invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        with self.assertRaises(ValidationError):
            void_expense.full_clean()

    def test_no_city_raises_error(self):
        """Raise ValidationError with partially filled customers."""
        void = Customer.objects.create(
            name='Customer Test', address='Cache', phone='666666666',
            CIF='444E', cp=48003, provider=True, )
        void_expense = Expense.objects.create(
            issuer=void, invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        with self.assertRaises(ValidationError):
            void_expense.full_clean()

    def test_no_cif_raises_error(self):
        """Raise ValidationError with partially filled customers."""
        void = Customer.objects.create(
            name='Customer Test', address='Cache', city='This computer',
            phone='666666666', cp=48003, provider=True, )
        void_expense = Expense.objects.create(
            issuer=void, invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        with self.assertRaises(ValidationError):
            void_expense.full_clean()

    def test_no_provider_raises_error(self):
        """Only providers can be issuers."""
        void = Customer.objects.create(
            name='Customer Test', address='Cache', city='This computer',
            phone='666666666', CIF='444E', cp=48003, )
        void_expense = Expense.objects.create(
            issuer=void, invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        with self.assertRaises(ValidationError):
            void_expense.full_clean()


class TestBankMovement(TestCase):
    """Test the bank movements model."""

    def test_action_date_is_date_instance(self):
        """Test the field type."""
        movement = BankMovement.objects.create(amount=100, notes='Test')
        self.assertIsInstance(movement.action_date, date)

    def test_action_date_default_is_today(self):
        """Test the field defaults."""
        movement = BankMovement.objects.create(amount=100, notes='Test')
        self.assertEqual(movement.action_date.date(), date.today())

    def test_amount_is_decimal(self):
        """Test the field type."""
        BankMovement.objects.create(amount=100.5, notes='Test')
        movement = BankMovement.objects.first()
        self.assertIsInstance(movement.amount, Decimal)

    def test_amount_max_digits(self):
        """Test the max length for the field."""
        with self.assertRaises(InvalidOperation):
            BankMovement.objects.create(amount=12345678, )

    def test_amount_max_decimal_places(self):
        """Test the max decimals for the field."""
        BankMovement.objects.create(amount=12345.678, )
        movement = BankMovement.objects.first()
        self.assertEqual(movement.amount, Decimal('12345.68'))

    def test_sorting_default(self):
        """Test the default ordering for the model."""
        issued_on = date.today()
        for i in range(5):
            BankMovement.objects.create(action_date=issued_on, amount=100)
            delay = timedelta(days=i+2)
            issued_on = issued_on + delay
        bms = BankMovement.objects.all()
        for i in range(4):
            self.assertTrue(bms[i].action_date > bms[i+1].action_date)


class TestTimetable(TestCase):
    """Test the timetable method."""

    def setUp(self):
        """Create the necessary objects."""
        self.user = User.objects.create_user(
            username='regular', password='test')

    def test_user_is_a_fk_field(self):
        """A user can have several times."""
        d = timedelta(hours=3)
        start = timezone.now()
        for i in range(3):
            end = start + d
            Timetable.objects.create(start=start, user=self.user, end=end)
            start = end + d
        self.assertEqual(Timetable.objects.filter(user=self.user).count(), 3)

    def test_start_and_end_are_datetime_fields(self):
        """Test the correct type."""
        end = timezone.now() + timedelta(hours=3)
        t = Timetable.objects.create(user=self.user, end=end)
        self.assertIsInstance(t.start, datetime)
        self.assertIsInstance(t.end, datetime)

    def test_end_can_be_null(self):
        """Test wether end can be null."""
        t = Timetable.objects.create(user=self.user)
        self.assertEqual(t.end, None)

    def test_hours_is_duration_field(self):
        """Test the correct type."""
        end = timezone.now() + timedelta(hours=3, minutes=22)
        t = Timetable.objects.create(user=self.user, end=end)
        self.assertIsInstance(t.hours, timedelta)

    def test_hours_can_be_null(self):
        """Test wether end can be null."""
        t = Timetable.objects.create(user=self.user)
        self.assertEqual(t.hours, None)

    def test_active_return_active_timetables(self):
        """Test the proper custom manager."""
        u2 = User.objects.create_user(username='u2', password='test')
        Timetable.objects.create(
            user=self.user, end=timezone.now() + timedelta(hours=3))
        Timetable.objects.create(user=self.user)
        Timetable.objects.create(user=u2)
        self.assertEqual(Timetable.active.count(), 2)

    def test_auto_fill_hours(self):
        """When end is provided, autofill hours."""
        end = timezone.now() + timedelta(hours=3, minutes=22)
        t = Timetable.objects.create(user=self.user, end=end)
        self.assertEqual(t.hours, timedelta(hours=3.5))

    def test_auto_fill_end(self):
        """When end is provided, autofill hours."""
        end = timezone.now() + timedelta(hours=3, minutes=30)
        t = Timetable.objects.create(
            user=self.user, hours=timedelta(hours=3.5))
        self.assertEqual(t.end.hour, end.hour)
        self.assertEqual(t.end.minute, end.minute)

    def test_clean_avoid_open_timetables(self):
        """When there are already timetables open."""
        Timetable.objects.create(user=self.user)
        t = Timetable(user=self.user)
        msg = 'Cannot open a timetable when other timetables are open'
        with self.assertRaisesMessage(ValidationError, msg):
            t.clean()

    def test_clean_avoid_open_timetables_exclude_other_users(self):
        """When there are already timetables open."""
        Timetable.objects.create(user=self.user)
        u = User.objects.create_user(username='alt', password='test')
        t = Timetable(user=u)
        self.assertEqual(t.clean(), None)

    def test_clean_avoid_open_timetables_exclude_current_entry(self):
        """When there are already timetables open."""
        t = Timetable.objects.create(user=self.user)
        t.start = t.start - timedelta(hours=2)
        self.assertEqual(t.clean(), None)

    def test_clean_overlapping(self):
        """An entry can't start when there are open entries."""
        end = timezone.now() + timedelta(hours=3, minutes=22)
        Timetable.objects.create(user=self.user, end=end)
        overlapped = end - timedelta(hours=1)
        t = Timetable(user=self.user, start=overlapped)
        msg = 'Entry is overlapping an existing entry'
        with self.assertRaisesMessage(ValidationError, msg):
            t.clean()

    def test_clean_overlapping_excludes_other_users(self):
        """An entry can't start when there are open entries."""
        u = User.objects.create_user(username='alt', password='test')
        end = timezone.now() + timedelta(hours=3, minutes=22)
        Timetable.objects.create(user=self.user, end=end)
        overlapped = end - timedelta(hours=3)
        t = Timetable(user=u, start=overlapped)
        self.assertEqual(t.clean(), None)

    def test_clean_overlapping_excludes_current_entry(self):
        """An entry can't start when there are open entries."""
        end = timezone.now() + timedelta(hours=3, minutes=22)
        t = Timetable.objects.create(user=self.user, end=end)
        overlapped = end - timedelta(hours=3)
        t.start = overlapped
        t.end = None  # to avoid validation simultaneous validation
        self.assertEqual(t.clean(), None)

    def test_clean_prevents_starting_in_the_future(self):
        """There's a threshold of 1h."""
        u = User.objects.create_user(username='alt', password='test')
        t = Timetable(user=u, start=timezone.now() + timedelta(hours=2))
        msg = 'Entry is starting in the future'
        with self.assertRaisesMessage(ValidationError, msg):
            t.clean()

    def test_clean_avoid_end_and_hours_simultaneously(self):
        """End and hours cannot be added at the same time."""
        delta = timedelta(hours=5)
        end = timezone.now() + timedelta(hours=3)
        t = Timetable(user=self.user, end=end, hours=delta)
        msg = ('Can\'t be added end date and hours simultaneously')
        with self.assertRaisesMessage(ValidationError, msg):
            t.clean()

    def test_clean_15_hours_limit(self):
        """The max length for entries is 15h."""
        end = timezone.now() + timedelta(hours=15.5)
        t = Timetable(user=self.user, end=end)
        msg = 'Entry lasts more than 15h'
        with self.assertRaisesMessage(ValidationError, msg):
            t.clean()

    def test_clean_more_than_15h_in_a_day_is_forbidden(self):
        """Several entries cannot add up more than 15h."""
        Timetable.objects.create(
            user=self.user, start=timezone.now() - timedelta(hours=2),
            hours=timedelta(hours=1))
        Timetable.objects.create(
            user=self.user, start=timezone.now() - timedelta(minutes=59),
            hours=timedelta(minutes=35))
        t = Timetable(user=self.user, hours=timedelta(hours=14))
        msg = 'You are trying to track more than 15h today.'
        with self.assertRaisesMessage(ValidationError, msg):
            t.clean()

    def test_clean_prevent_15_min_sessions(self):
        """The least length for the session is 15 min."""
        u = User.objects.create_user(username='alt', password='test')
        t = Timetable(user=u, hours=timedelta(minutes=14))
        msg = 'Sessions less than 15\' are forbidden.'
        with self.assertRaisesMessage(ValidationError, msg):
            t.clean()

    def test_clean_start_after_end(self):
        """We can't start after we end."""
        end = timezone.now() - timedelta(hours=3)
        t = Timetable(user=self.user, end=end)
        msg = 'Entry cannot start after the end'
        with self.assertRaisesMessage(ValidationError, msg):
            t.clean()

    def test_fisrt_segment_on_auto_hours(self):
        """Test the 15' margin for lower segment."""
        end = timezone.now() + timedelta(hours=3, minutes=14)
        t = Timetable.objects.create(user=self.user, end=end)
        self.assertEqual(t.hours, timedelta(hours=3))

    def test_second_segment_on_auto_hours(self):
        """Test the 30' margin for the mid segment."""
        end = timezone.now() + timedelta(hours=3, minutes=15)
        t = Timetable.objects.create(user=self.user, end=end)
        self.assertEqual(t.hours, timedelta(hours=3.5))
        t.end = end + timedelta(minutes=29)
        t.save()
        t = Timetable.objects.get(pk=t.pk)
        self.assertEqual(t.hours, timedelta(hours=3.5))

    def test_last_segment_on_auto_hours(self):
        """Test the 15' margin for upper segment."""
        end = timezone.now() + timedelta(hours=3, minutes=45)
        t = Timetable.objects.create(user=self.user, end=end)
        self.assertEqual(t.hours, timedelta(hours=4))

    def test_get_end(self):
        """Test the correct output."""
        end = timezone.now() + timedelta(hours=3, minutes=30)
        t = Timetable.objects.create(
            user=self.user, hours=timedelta(hours=3.5))
        self.assertEqual(t.end.hour, end.hour)
        self.assertEqual(t.end.minute, end.minute)


#
#
#
#
#
