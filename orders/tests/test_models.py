"""Test the app models."""
from io import BytesIO

from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.utils import DataError, IntegrityError
from django.test import TestCase, tag
from django.utils import timezone

from orders.models import (
    BankMovement, Comment, Customer, Expense, Invoice, Item, Order, OrderItem,
    PQueue, Timetable, CashFlowIO, StatusShift, ExpenseCategory, )

from orders.settings import PAYMENT_METHODS, WEEK_COLORS, ITEM_TYPE

from decouple import config

from todoist.api import TodoistAPI


class CommentsTests(TestCase):
    """Test the models."""

    def setUp(self):
        """Create the necessary items on database at once."""
        # Create a user
        u = User.objects.create_user(
            username='user', is_staff=True, is_superuser=True, )

        # Create a customer
        c = Customer.objects.create(name='Customer Test', phone=55, cp=44)

        # Create  an order
        o = Order.objects.create(
            user=u, customer=c, ref_name='example', delivery=date(2018, 2, 1),)

        # Create comment
        Comment.objects.create(
            user=u, reference=o, comment='This is a comment')

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

    def setUp(self):
        Customer.objects.create(
            name='Test', address='foo street', city='bar', phone=55,
            email='foo@bar.baz', CIF='baz', cp=44, notes='default', )

    def test_customer_creation_field(self):
        """Test the customer's field types."""
        c = Customer.objects.first()
        self.assertIsInstance(c.creation, datetime)
        self.assertEqual(
            c._meta.get_field('creation').verbose_name, 'Alta')

    def test_customer_name_field(self):
        c = Customer.objects.first()
        self.assertEqual(c.name, 'Test')
        self.assertEqual(
            c._meta.get_field('name').verbose_name, 'Nombre')
        with self.assertRaises(DataError):
            c.name = 65 * 'a'
            c.save()

    def test_customer_address_field(self):
        c = Customer.objects.first()
        self.assertEqual(c.address, 'foo street')
        self.assertEqual(
            c._meta.get_field('address').verbose_name, 'Dirección')

        c.address = ''  # Can be empty but not null
        c.save()

        with self.assertRaises(DataError):
            c.address = 65 * 'a'
            c.save()

    def test_customer_city_field(self):
        c = Customer.objects.first()
        self.assertEqual(c.city, 'bar')
        self.assertEqual(
            c._meta.get_field('city').verbose_name, 'Localidad')

        c.city = ''  # Can be empty but not null
        c.save()

        with self.assertRaises(DataError):
            c.city = 33 * 'a'
            c.save()

    def test_customer_phone_field(self):
        c = Customer.objects.first()
        self.assertEqual(c.phone, 55)
        self.assertEqual(
            c._meta.get_field('phone').verbose_name, 'Telefono')

    def test_customer_email_field(self):
        c = Customer.objects.first()
        self.assertEqual(c.email, 'foo@bar.baz')
        self.assertEqual(
            c._meta.get_field('email').verbose_name, 'Email')

        c.email = ''  # Can be empty but not null
        c.save()

    def test_customer_email_raises_data_error(self):
        c = Customer.objects.first()
        with self.assertRaises(DataError):
            c.email = 65 * 'a'
            c.save()

    def test_customer_email_raises_validation_error(self):
        c = Customer.objects.first()
        with self.assertRaises(ValidationError):
            c.email = 'void'
            c.full_clean()

    def test_customer_CIF_field(self):
        c = Customer.objects.first()
        self.assertEqual(c.CIF, 'baz')
        self.assertEqual(
            c._meta.get_field('CIF').verbose_name, 'CIF')

        c.CIF = ''  # Can be empty but not null
        c.save()

        with self.assertRaises(DataError):
            c.CIF = 21 * 'a'
            c.save()

    def test_customer_cp_field(self):
        c = Customer.objects.first()
        self.assertEqual(c.cp, 44)
        self.assertEqual(
            c._meta.get_field('cp').verbose_name, 'CP')

    def test_customer_cp_field_cannot_be_empty(self):
        c = Customer.objects.first()
        with self.assertRaises(ValueError):
            c.cp = ''
            c.save()

    def test_customer_cp_field_cannot_be_null(self):
        c = Customer.objects.first()
        with self.assertRaises(IntegrityError):
            c.cp = None
            c.save()

        # self.assertEqual(c.notes, 'default')

    def test_customer_notes_field(self):
        c = Customer.objects.first()
        self.assertEqual(c.notes, 'default')
        self.assertEqual(
            c._meta.get_field('notes').verbose_name, 'Observaciones')

        # Can be empty
        c.notes = ''
        self.assertEqual(c.full_clean(), None)
        self.assertEqual(c.save(), None)

        # Can be null
        c.notes = None
        self.assertEqual(c.full_clean(), None)
        self.assertEqual(c.save(), None)

    def test_customer_provider_field(self):
        """Test the field."""
        c = Customer.objects.first()

        self.assertIsInstance(c.provider, bool)
        self.assertFalse(c.provider)
        self.assertEqual(
            c._meta.get_field('provider').verbose_name, 'Proveedor')

    def test_customer_group_field(self):
        """Test the field."""
        c = Customer.objects.first()

        self.assertIsInstance(c.group, bool)
        self.assertFalse(c.group)
        self.assertEqual(
            c._meta.get_field('group').verbose_name, 'Grupo')

    def test_customer_str(self):
        c = Customer.objects.first()
        self.assertEqual(c.__str__(), 'Test')

    def test_avoid_duplicates(self):
        copy = Customer(
            name='Test', address='foo street', city='bar', phone=55,
            email='foo@bar.baz', CIF='baz', cp=44, notes='default',
        )
        with self.assertRaises(ValidationError):
            copy.clean()

    def test_avoid_customer_to_be_provider_and_group_simultaneously(self):
        c = Customer.objects.first()
        c.provider = True
        c.group = True
        c.name = 'Customer provider & group'
        msg = 'Un cliente no puede ser proveedor y grupo al mismo tiempo'
        with self.assertRaisesMessage(ValidationError, msg):
            c.clean()

        c.save()
        c = Customer.objects.first()
        self.assertFalse(c.group)
        self.assertTrue(c.provider)

    def test_email_name(self):
        """Test the correct output for email comunications."""
        c = Customer.objects.create(
            name='teSt With RaNDom eNtries', phone=0, cp=0, )
        self.assertEqual(c.email_name(), 'Test')


class TestOrders(TestCase):
    """Test the Order model."""

    def setUp(self):
        """Create the necessary items on database at once."""
        # Create a user
        User.objects.create_user(username='user', is_staff=True,
                                 is_superuser=True)

        # Create a customer
        c = Customer.objects.create(
            name='Test', address='This computer', city='No city', phone=55,
            email='customer@example.com', CIF='5555G', notes='note', cp=44)

        Item.objects.create(name='test', fabrics=10, price=30, stocked=10)

        Order.objects.create(
            user=User.objects.first(), customer=c, ref_name='example',
            delivery=date(2018, 2, 1), waist=10, chest=20, hip=30, lenght=40,
            others='Custom notes', budget=2000, prepaid=1000, )

    def test_order_creation_field(self):
        """Test the customer's field types."""
        o = Order.objects.first()
        self.assertIsInstance(o.inbox_date, datetime)

    def test_order_user_field(self):
        """Test the customer's field types."""
        o = Order.objects.first()
        u = User.objects.first()
        self.assertEqual(o.user, u)

        u.delete()
        self.assertFalse(Order.objects.first())  # deletes on cascade

    def test_order_customer_field(self):
        """Test the customer's field types."""
        o = Order.objects.first()
        c = Customer.objects.first()
        self.assertEqual(o.customer, c)

        self.assertTrue(c.order)  # related name

        # can be null
        o.customer = None
        o.save()
        o = Order.objects.first()
        self.assertFalse(o.customer)

        # deletes cascade
        o.customer = c
        o.save()
        o = Order.objects.first()
        self.assertTrue(o.customer)
        c.delete()
        self.assertFalse(Order.objects.first())

    def test_order_mebership_field(self):
        """Test the customer's field types."""
        o = Order.objects.first()
        self.assertFalse(o.membership)  # can be null
        g = Customer.objects.create(name='group', phone=0, cp=0, group=True, )
        o.membership = g
        o.save()
        o = Order.objects.first()
        self.assertEqual(o.membership, g)

        self.assertTrue(g.group_order)  # related name

        # can be blank
        o.membership = None
        self.assertEqual(o.full_clean(), None)

        # delete sets null
        g.delete()
        o = Order.objects.first()
        self.assertFalse(o.membership, None)

    def test_order_ref_name_field(self):
        o = Order.objects.first()
        self.assertEqual(o.ref_name, 'example')
        self.assertEqual(
            o._meta.get_field('ref_name').verbose_name, 'Referencia')

        with self.assertRaises(DataError):
            o.ref_name = 33 * 'a'
            o.save()

    def test_order_ref_name_field_cant_be_null(self):
        o = Order.objects.first()
        o.ref_name = None
        with self.assertRaises(IntegrityError):
            o.save()

    def test_order_ref_name_field_cant_be_blank(self):
        o = Order.objects.first()
        o.ref_name = ''
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_order_delivery_field(self):
        o = Order.objects.first()
        self.assertIsInstance(o.delivery, date)
        self.assertEqual(
            o._meta.get_field('delivery').verbose_name, 'Entrega prevista')

        # Can be empty but not null
        o.delivery = None
        self.assertEqual(o.full_clean(), None)
        with self.assertRaises(IntegrityError):
            o.save()

    def test_order_status_field(self):
        o = Order.objects.first()
        self.assertEqual(o.status, '1')  # default
        self.assertEqual(
            o._meta.get_field('status').verbose_name, 'status')

        with self.assertRaises(DataError):
            o.status = '11'  # longer than 1
            o.save()

    def test_order_status_choices(self):
        o = Order.objects.first()

        with self.assertRaises(ValidationError):
            o.status = '10'
            o.full_clean()

    def test_order_status_cant_be_null(self):
        o = Order.objects.first()
        o.status = None
        with self.assertRaises(IntegrityError):
            o.save()

    def test_order_status_cant_be_blank(self):
        o = Order.objects.first()
        o.status = None
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_order_priority_field(self):
        o = Order.objects.first()
        self.assertEqual(o.priority, '2')  # default
        self.assertEqual(
            o._meta.get_field('priority').verbose_name, 'Prioridad')

        with self.assertRaises(DataError):
            o.priority = '11'  # longer than 1
            o.save()

    def test_order_priority_choices(self):
        o = Order.objects.first()

        with self.assertRaises(ValidationError):
            o.priority = '9'
            o.full_clean()

    def test_order_priority_cant_be_null(self):
        o = Order.objects.first()
        o.priority = None
        with self.assertRaises(IntegrityError):
            o.save()

    def test_order_priority_cant_be_blank(self):
        o = Order.objects.first()
        o.priority = None
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_order_confirmed_field(self):
        o = Order.objects.first()
        self.assertIsInstance(o.confirmed, bool)
        self.assertTrue(o.confirmed)  # default
        self.assertEqual(
            o._meta.get_field('confirmed').verbose_name, 'Confirmado')

    def test_order_waist_field(self):
        o = Order.objects.first()
        self.assertEqual(o.waist, 10)
        self.assertIsInstance(o.waist, Decimal)
        self.assertEqual(
            o._meta.get_field('waist').verbose_name, 'Cintura')

        # Default value
        o = Order.objects.create(
            user=User.objects.first(), delivery=date.today(), ref_name='foo',
            customer=Customer.objects.last(), )
        self.assertEqual(o.waist, 0)

    def test_order_waist_max_digits(self):
        o = Order.objects.first()
        with self.assertRaises(ValidationError):
            o.waist = 123456  # longer than 5 digits
            o.full_clean()

    def test_order_waist_max_decimals(self):
        o = Order.objects.first()
        with self.assertRaises(ValidationError):
            o.waist = 12.345  # longer than 2 decimals
            o.full_clean()

    def test_order_waist_cant_be_null(self):
        o = Order.objects.first()
        o.waist = None
        with self.assertRaises(IntegrityError):
            o.save()

    def test_order_waist_cant_be_blank(self):
        o = Order.objects.first()
        o.waist = None
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_order_chest_field(self):
        o = Order.objects.first()
        self.assertEqual(o.chest, 20)
        self.assertIsInstance(o.chest, Decimal)
        self.assertEqual(
            o._meta.get_field('chest').verbose_name, 'Pecho')

        # Default value
        o = Order.objects.create(
            user=User.objects.first(), delivery=date.today(), ref_name='foo',
            customer=Customer.objects.last(), )
        self.assertEqual(o.chest, 0)

    def test_order_chest_max_digits(self):
        o = Order.objects.first()
        with self.assertRaises(ValidationError):
            o.chest = 123456  # longer than 5 digits
            o.full_clean()

    def test_order_chest_max_decimals(self):
        o = Order.objects.first()
        with self.assertRaises(ValidationError):
            o.chest = 12.345  # longer than 2 decimals
            o.full_clean()

    def test_order_chest_cant_be_null(self):
        o = Order.objects.first()
        o.chest = None
        with self.assertRaises(IntegrityError):
            o.save()

    def test_order_chest_cant_be_blank(self):
        o = Order.objects.first()
        o.chest = None
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_order_hip_field(self):
        o = Order.objects.first()
        self.assertEqual(o.hip, 30)
        self.assertIsInstance(o.hip, Decimal)
        self.assertEqual(
            o._meta.get_field('hip').verbose_name, 'Cadera')

        # Default value
        o = Order.objects.create(
            user=User.objects.first(), delivery=date.today(), ref_name='foo',
            customer=Customer.objects.last(), )
        self.assertEqual(o.hip, 0)

    def test_order_hip_max_digits(self):
        o = Order.objects.first()
        with self.assertRaises(ValidationError):
            o.hip = 123456  # longer than 5 digits
            o.full_clean()

    def test_order_hip_max_decimals(self):
        o = Order.objects.first()
        with self.assertRaises(ValidationError):
            o.hip = 12.345  # longer than 2 decimals
            o.full_clean()

    def test_order_hip_cant_be_null(self):
        o = Order.objects.first()
        o.hip = None
        with self.assertRaises(IntegrityError):
            o.save()

    def test_order_hip_cant_be_blank(self):
        o = Order.objects.first()
        o.hip = None
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_order_lenght_field(self):
        o = Order.objects.first()
        self.assertEqual(o.lenght, 40)
        self.assertIsInstance(o.lenght, Decimal)
        self.assertEqual(
            o._meta.get_field('lenght').verbose_name, 'Largo')

        # Default value
        o = Order.objects.create(
            user=User.objects.first(), delivery=date.today(), ref_name='foo',
            customer=Customer.objects.last(), )
        self.assertEqual(o.lenght, 0)

    def test_order_lenght_max_digits(self):
        o = Order.objects.first()
        with self.assertRaises(ValidationError):
            o.lenght = 123456  # longer than 5 digits
            o.full_clean()

    def test_order_lenght_max_decimals(self):
        o = Order.objects.first()
        with self.assertRaises(ValidationError):
            o.lenght = 12.345  # longer than 2 decimals
            o.full_clean()

    def test_order_lenght_cant_be_null(self):
        o = Order.objects.first()
        o.lenght = None
        with self.assertRaises(IntegrityError):
            o.save()

    def test_order_lenght_cant_be_blank(self):
        o = Order.objects.first()
        o.lenght = None
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_order_others_field(self):
        o = Order.objects.first()
        self.assertEqual(o.others, 'Custom notes')
        self.assertEqual(
            o._meta.get_field('others').verbose_name, 'Observaciones')

        # Can be empty
        o.others = ''
        self.assertEqual(o.full_clean(), None)
        self.assertEqual(o.save(), None)
        # o.save()

        # Can be null
        o.others = None
        self.assertEqual(o.full_clean(), None)
        self.assertEqual(o.save(), None)

    def test_budget_and_prepaid_can_be_null(self):
        """Test the emptyness of fields and default value."""
        user = User.objects.first()
        c = Customer.objects.first()
        Order.objects.create(
            user=user, customer=c, ref_name='No Budget nor prepaid',
            delivery=date.today())
        order = Order.objects.get(ref_name='No Budget nor prepaid')
        self.assertEqual(order.prepaid, 0)

    def test_discount(self):
        o = Order.objects.first()
        self.assertEqual(o.discount, 0)  # default value
        self.assertEqual(
            o._meta.get_field('discount').verbose_name, 'Descuento %')
        self.assertIsInstance(o.discount, int)

    def test_discount_cant_be_negative(self):
        o = Order.objects.first()
        msg = (
            'new row for relation "orders_order" violates check constraint' +
            ' "orders_order_discount_check"')
        with self.assertRaisesMessage(IntegrityError, msg):
            o.discount = -10
            o.save()

    def test_discount_field_cant_be_over_32767(self):
        """Although there's also a validation exception for values over 100."""
        o = Order.objects.first()
        msg = 'smallint out of range'
        with self.assertRaisesMessage(DataError, msg):
            o.discount = 33000
            o.save()

    def test_custom_manager_live(self):
        """Test the live custom manager."""
        u = User.objects.first()
        c = Customer.objects.first()
        for i in range(4):
            Order.objects.create(
                user=u, customer=c, ref_name='Test', delivery=date.today())
        self.assertEqual(Order.live.count(), 5)
        invoiced, cancelled = Order.live.all()[:2]
        OrderItem.objects.create(
            reference=invoiced, element=Item.objects.last())
        invoiced.kill()
        cancelled.status = '8'
        cancelled.save()
        self.assertEqual(Order.live.count(), 3)

    def test_custom_manager_outdated(self):
        """Test the outdated custom manager."""
        u = User.objects.first()
        c = Customer.objects.first()
        for i in range(3):
            Order.objects.create(
                user=u, customer=c, ref_name='Test', delivery=date.today())
        self.assertEqual(Order.outdated.count(), 1)
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
        i = Order.objects.create(
            user=u, customer=express, ref_name='Test', delivery=date.today())
        OrderItem.objects.create(reference=i, element=Item.objects.last())
        i.kill()

        # finally an obsolete order, invoice missing
        obsolete = Order.objects.create(
            user=u, customer=express, ref_name='Obsolete',
            delivery=date.today())
        OrderItem.objects.create(
            reference=obsolete, element=Item.objects.last())

        self.assertEqual(Order.objects.count(), 4)  # total orders
        self.assertEqual(Order.obsolete.count(), 1)
        self.assertEqual(Order.obsolete.first().ref_name, 'Obsolete')

    def test_customer_is_not_provider(self):
        o = Order.objects.first()
        c = Customer.objects.first()
        self.assertEqual(o.customer, c)

        c.provider = True
        c.save()

        o.customer = Customer.objects.first()
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_discount_over_100_raises_validation_error(self):
        o = Order.objects.first()
        o.discount = 101
        msg = 'El descuento no puede ser superior al 100%'
        with self.assertRaisesMessage(ValidationError, msg):
            o.clean()

    def test_invoiced_orders_are_status_9(self):
        o = Order.objects.first()
        self.assertEqual(o.status, '1')

        OrderItem.objects.create(reference=o, element=Item.objects.last())
        o.kill()
        self.assertEqual(o.status, '9')

        for s in ('1', '2', '3', '4', '5', '6', '7', '8'):
            o.status = s
            o.save()
            self.assertEqual(o.status, '9')

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

    def test_ensure_membership_is_a_group_customer(self):
        c2 = Customer.objects.create(name='foo', phone=0, cp=0)
        o = Order.objects.first()
        self.assertEqual(o.membership, None)

        o.membership = c2
        o.save()
        o = Order.objects.first()
        self.assertEqual(o.membership, None)  # keeps being None

        c2.group = True
        c2.save()
        c2 = Customer.objects.get(pk=c2.pk)
        o.membership = c2
        o.save()
        o = Order.objects.first()
        self.assertEqual(o.membership, c2)  # Now it's ok

    def test_statuses_4_and_5_are_deprecated(self):
        o = Order.objects.first()
        self.assertEqual(o.status, '1')

        for s in ('3', '4', '5'):
            pass
            o.status = s
            o.save()
            self.assertEqual(o.status, '3')

    def test_saving_an_order_creates_new_statusShift(self):
        o = Order.objects.first()
        self.assertEqual(o.status_shift.count(), 1)  # Created during setUp

    def test_kill_order_pending_0(self):
        order = Order.objects.first()
        for i in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        order.kill()
        self.assertEqual(CashFlowIO.objects.count(), 1)
        self.assertEqual(order.pending, 0)

        order.kill()  # Should do nothing
        self.assertEqual(CashFlowIO.objects.count(), 1)
        self.assertEqual(order.pending, 0)

    def test_kill_order_avoids_orders_to_be_rekilled(self):
        order = Order.objects.first()
        OrderItem.objects.create(reference=order, element=Item.objects.last())
        self.assertEqual(Invoice.objects.count(), 0)
        order.kill()
        self.assertEqual(Invoice.objects.count(), 1)
        order.kill()
        self.assertEqual(Invoice.objects.count(), 1)

    def test_kill_order_kills_pending_payments(self):
        order = Order.objects.first()
        OrderItem.objects.create(reference=order, element=Item.objects.last())
        order.kill()
        cf = CashFlowIO.objects.get(order=order)
        self.assertTrue(cf)
        self.assertEqual(cf.pay_method, 'C')  # default
        self.assertEqual(cf.amount, 30)
        self.assertEqual(order.status, '9')
        cf.delete()
        order.invoice.delete()

        for pm in ('V', 'T'):
            order.kill(pay_method=pm)
            cf = CashFlowIO.objects.get(order=order)
            self.assertEqual(cf.pay_method, pm)
            self.assertEqual(order.status, '9')
            cf.delete()
            order.invoice.delete()

        self.assertEqual(Invoice.objects.count(), 0)  # Last one was killed

    def test_kill_order_updates_delivery_date(self):
        order = Order.objects.first()
        OrderItem.objects.create(reference=order, element=Item.objects.last())
        self.assertEqual(order.delivery, date(2018, 2, 1))
        order.kill()
        self.assertEqual(order.delivery, date.today())

    def test_kill_order_updates_status(self):
        order = Order.objects.first()
        OrderItem.objects.create(reference=order, element=Item.objects.last())
        self.assertEqual(order.status, '1')
        order.kill()
        self.assertEqual(order.status, '9')

    def test_kill_order_creates_invoice(self):
        order = Order.objects.first()
        OrderItem.objects.create(reference=order, element=Item.objects.last())
        order.kill()
        i = Invoice.objects.first()
        self.assertEqual(i.reference, order)
        self.assertEqual(i.pay_method, 'C')
        self.assertEqual(i.amount, order.total)
        self.assertEqual(i.issued_on.date(), date.today())
        self.assertEqual(i.invoice_no, 1)

    def test_kill_updates_stock(self):
        order, item = Order.objects.first(), Item.objects.last()
        self.assertEqual(item.stocked, 10)
        OrderItem.objects.create(reference=order, element=item)
        order.kill()
        item = Item.objects.get(pk=item.pk)
        self.assertEqual(item.stocked, 9)

    @tag('todoist')
    def test_kill_order_archives_todoist(self):
        order = Order.objects.first()
        OrderItem.objects.create(reference=order, element=Item.objects.last())

        order.create_todoist()
        order = Order.objects.get(pk=order.pk)
        self.assertFalse(order.is_archived())
        order = Order.objects.get(pk=order.pk)
        order.kill()
        self.assertTrue(order.is_archived())
        project = order.t_api.projects.get_by_id(order.t_pid)
        project.delete()
        order.t_api.commit()

    def test_order_tz(self):
        order = Order.objects.first()
        self.assertFalse(order.tz)

        tz = Customer.objects.create(name='TrapuzaRrAk', phone=0, cp=0)
        order.customer = tz
        order.save()
        self.assertTrue(order.tz)

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
        """Test the correct sum of all items (applies discount)."""
        u, c = User.objects.first(), Customer.objects.first()
        order = Order.objects.create(user=u, customer=c, ref_name='test',
                                     delivery=date.today(), discount=10, )
        self.assertEqual(order.total, 0)
        for _ in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.assertEqual(order.total, 150 * .90)
        self.assertIsInstance(order.total, float)

    def test_total_amount_is_0(self):
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date.today())
        OrderItem.objects.create(
            reference=order, element=Item.objects.last(), price=0)  # 30€
        OrderItem.objects.create(
            reference=order, element=Item.objects.last(), price=-30)
        self.assertEqual(order.total, 0)

    def test_discount_amount(self):
        u, c = User.objects.first(), Customer.objects.first()
        o = Order.objects.create(user=u, customer=c, ref_name='test',
                                 delivery=date.today(), discount=10, )
        i = Item.objects.last()
        [OrderItem.objects.create(reference=o, element=i) for _ in range(5)]
        self.assertEqual(o.discount_amount, 15)
        self.assertIsInstance(o.discount_amount, float)

    def test_total_pre_discount(self):
        u, c = User.objects.first(), Customer.objects.first()
        o = Order.objects.create(user=u, customer=c, ref_name='test',
                                 delivery=date.today(), discount=10, )
        i = Item.objects.last()
        [OrderItem.objects.create(reference=o, element=i) for _ in range(5)]
        self.assertEqual(o.total_pre_discount, 150)
        self.assertIsInstance(o.total_pre_discount, float)

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

    def test_already_paid(self):
        order = Order.objects.first()
        for i in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.assertEqual(order.already_paid, 0)

        for _ in range(2):
            CashFlowIO.objects.create(order=order, amount=10)
        self.assertIsInstance(order.already_paid, float)
        self.assertEqual(order.already_paid, 20)

    def test_pending_amount(self):
        order = Order.objects.first()
        for i in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.assertEqual(order.pending, 150)

        for _ in range(2):
            CashFlowIO.objects.create(order=order, amount=10)
        self.assertEqual(order.pending, 130)

    def test_closed(self):
        o = Order.objects.first()
        self.assertFalse(o.closed)

        tz = Customer.objects.create(name='Trapuzarrak', phone=0, cp=0)
        o.customer = tz
        o.status = '7'
        o.delivery = date.today() - timedelta(days=1)
        o.save()
        self.assertTrue(o.closed)

        o.customer = Customer.objects.first()
        o.save()
        self.assertFalse(o.closed)

        OrderItem.objects.create(element=Item.objects.last(), reference=o)
        o.kill()
        self.assertTrue(o.closed)

    def test_days_open(self):
        o = Order.objects.first()
        o.inbox_date = o.inbox_date - timedelta(days=5)
        self.assertEqual(o.days_open, 5)

        tz = Customer.objects.create(name='Trapuzarrak', phone=0, cp=0)
        o.customer = tz
        o.status = '7'
        o.delivery = date.today() - timedelta(days=1)
        o.save()
        self.assertEqual(o.days_open, 4)

        o.customer = Customer.objects.first()
        o.save()
        self.assertEqual(o.days_open, 5)

        OrderItem.objects.create(element=Item.objects.last(), reference=o)
        o.kill()
        self.assertEqual(o.days_open, 4)

    def test_color(self):
        o = Order.objects.first()
        self.assertEqual(o.color, WEEK_COLORS['this'])

    def test_has_no_items(self):
        """Test the order has no items."""
        order = Order.objects.create(user=User.objects.all()[0],
                                     customer=Customer.objects.all()[0],
                                     ref_name='Test%',
                                     delivery=date.today(),
                                     budget=100,
                                     prepaid=100)
        self.assertTrue(order.has_no_items)
        item = Item.objects.create(name='Test item', fabrics=2, stocked=30)
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

    def test_the_count_of_times_per_item_in_an_order(self):
        """Test the correct output of count times per order."""
        order = Order.objects.create(user=User.objects.all()[0],
                                     customer=Customer.objects.all()[0],
                                     ref_name='Test%',
                                     delivery=date.today(),
                                     budget=100,
                                     prepaid=100)
        item = Item.objects.create(name='Test item', fabrics=2, stocked=30)
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
        item = Item.objects.create(name='Test item', fabrics=2, stocked=30)
        for i in range(2):
            OrderItem.objects.create(element=item, reference=order, qty=i,
                                     crop=time(5), sewing=time(3),
                                     iron=time(0))
        stocked = OrderItem.objects.all()[0]
        stocked.stock = True
        stocked.save()
        self.assertEqual(order.times[0], 2)
        self.assertEqual(order.times[1], 3)

    def test_order_estimated_time(self):
        # Create previous orders
        older = Order.objects.create(user=User.objects.first(),
                                     customer=Customer.objects.first(),
                                     ref_name='older',
                                     delivery=date.today(),
                                     )
        items = [Item.objects.create(
            name=s, fabrics=5, price=30, stocked=30) for s in ('a', 'b', 'c',)]

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
        OrderItem.objects.create(
            element=items[2], qty=7, reference=curr, stock=True)

        curr = Order.objects.get(pk=curr.pk)

        self.assertEqual(curr.estimated_time, (5+7, 2*(5+7), 3*(5+7)))

    def test_order_production_time(self):
        """Test the property."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date.today(),
            prepaid=10)
        times = [timedelta(minutes=t) for t in (10, 20, 30)]
        OrderItem.objects.create(reference=order, element=Item.objects.last(),
                                 crop=times[0], sewing=times[1], iron=times[2])
        self.assertEqual(order.production_time, timedelta(hours=1))

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

    def test_kanban_shifts(self):
        """Test the correct jump within kanban stages."""
        order = Order.objects.create(
            user=User.objects.first(), customer=Customer.objects.first(),
            ref_name='foo', delivery=date.today(), )

        self.assertEqual(order.status, '1')

        # switch to queued
        order.kanban_forward()
        self.assertEqual(order.status, '2')

        # switch to in progress
        order.kanban_forward()
        self.assertEqual(order.status, '3')

        # switch to waiting
        order.kanban_forward()
        self.assertEqual(order.status, '6')

        # switch to delivered
        order.kanban_forward()
        self.assertEqual(order.status, '7')

        # Raise ValidationError
        msg = 'Can\'t shift the status over 7 (call `kill()`).'
        with self.assertRaisesMessage(ValidationError, msg):
            order.kanban_forward()

        # switch back to in_progress
        order.kanban_backward()
        self.assertEqual(order.status, '3')

        # From status 6 we should also return to 3
        order.status = '6'
        order.save()
        self.assertEqual(order.status, '6')
        order.kanban_backward()
        self.assertEqual(order.status, '3')

        # switch back to queued
        order.kanban_backward()
        self.assertEqual(order.status, '2')

        # switch back to queued
        order.kanban_backward()
        self.assertEqual(order.status, '1')

        # Raise ValidationError
        msg = 'Can\'t shift the status below 1.'
        with self.assertRaisesMessage(ValidationError, msg):
            order.kanban_backward()

        # from status 8 hitting shift up or down shifts to status 1
        for method in (order.kanban_forward, order.kanban_backward):
            order.status = '8'
            order.save()
            method()
            self.assertEqual(order.status, '1')

        # Raise ValidationError for invoiced orders
        OrderItem.objects.create(reference=order, element=Item.objects.last())
        # kill() creates two status shitfs, one for status 7 (thererby calling
        # Order.deliver()) and another for status 9.
        order.kill()
        msg = 'Invoiced orders can\'t change their status.'
        with self.assertRaisesMessage(ValidationError, msg):
            order.kanban_backward()

        self.assertEqual(StatusShift.objects.filter(order=order).count(), 16)


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
                            fabrics=5.2,
                            stocked=30, )
        self.assertTrue(Item.objects.get(name='Test item'))

    def test_name(self):
        i = Item.objects.create(name='foo', fabrics=5, stocked=30, )
        self.assertEqual(i._meta.get_field('name').verbose_name, 'Nombre')

        msg = 'value too long for type character varying(64)'
        with self.assertRaisesMessage(DataError, msg):
            Item.objects.create(name='f' * 65, fabrics=5, stocked=30, )

    def test_item_type(self):
        for it in ITEM_TYPE:
            i = Item.objects.create(
                name='foo', fabrics=5, item_type=it[0], stocked=30)
            self.assertEqual(
                i._meta.get_field('item_type').verbose_name, 'Tipo de prenda')

        # Default value
        i = Item.objects.create(name='foo', fabrics=5, stocked=30)
        self.assertEqual(i.item_type, '0')

    def test_item_type_out_of_choices(self):
        msg = "Value '20' is not a valid choice."
        with self.assertRaisesMessage(ValidationError, msg):
            i = Item(
                name='foo', fabrics=5, item_type='20', item_class='S',
                size=1, price=0, stocked=0, )
            i.full_clean()

    def test_item_type_out_max_length(self):
        msg = "value too long for type character varying(2)"
        with self.assertRaisesMessage(DataError, msg):
            Item.objects.create(
                name='foo', fabrics=5, item_type='200', stocked=30)

    def test_item_class(self):
        for it in ITEM_TYPE:
            i = Item.objects.create(name='foo', fabrics=5, item_type=it[0])
            self.assertEqual(
                i._meta.get_field('item_type').verbose_name, 'Tipo de prenda')

        # Default value
        i = Item.objects.create(name='foo', fabrics=5)
        self.assertEqual(i.item_type, '0')

    def test_item_class_out_of_choices(self):
        msg = "Value 'Void' is not a valid choice."
        with self.assertRaisesMessage(ValidationError, msg):
            i = Item(
                name='foo', fabrics=5, item_type='19', item_class='Void',
                size=1, price=0, stocked=0, )
            i.full_clean()

    def test_item_class_out_max_length(self):
        msg = "value too long for type character varying(1)"
        with self.assertRaisesMessage(DataError, msg):
            Item.objects.create(name='foo', fabrics=5, item_class='SS')

    def test_size(self):
        i = Item.objects.create(name='foo', fabrics=5, )
        self.assertEqual(i._meta.get_field('size').verbose_name, 'Talla')
        self.assertEqual(i.size, '1')

        msg = 'value too long for type character varying(6)'
        with self.assertRaisesMessage(DataError, msg):
            Item.objects.create(name='foo', fabrics=5, size='f' * 7)

    def test_notes(self):
        i = Item(
            name='foo', fabrics=5, item_type='19', item_class='S',
            size=1, price=0, stocked=0, )
        self.assertFalse(i.full_clean())  # can be empty
        i.save()
        self.assertEqual(i.notes, None)
        self.assertEqual(
            i._meta.get_field('notes').verbose_name, 'Observaciones')

    def test_fabrics(self):
        i = Item.objects.create(name='foo', fabrics=5, )
        self.assertEqual(i._meta.get_field('fabrics').verbose_name, 'Tela (M)')
        self.assertIsInstance(Item.objects.get(pk=i.pk).fabrics, Decimal)

    def test_fabrics_max_digits(self):
        i = Item.objects.create(name='foo', fabrics=5, )
        msg = 'Ensure that there are no more than 5 digits in total.'
        with self.assertRaisesMessage(ValidationError, msg):
            i.fabrics = 1234567
            i.full_clean()

    def test_fabrics_max_decimals(self):
        i = Item.objects.create(name='foo', fabrics=5, )
        msg = 'Ensure that there are no more than 2 decimal places.'
        with self.assertRaisesMessage(ValidationError, msg):
            i.fabrics = 12.345
            i.full_clean()

    def test_foreign(self):
        i = Item.objects.create(name='foo', fabrics=5, )
        i = Item.objects.get(pk=i.pk)
        self.assertEqual(i._meta.get_field('foreing').verbose_name, 'Externo')
        self.assertIsInstance(i.foreing, bool)
        self.assertFalse(i.foreing)

    def test_price(self):
        i = Item.objects.create(name='foo', fabrics=5,)
        i = Item.objects.get(pk=i.pk)
        self.assertEqual(i._meta.get_field('fabrics').verbose_name, 'Tela (M)')
        self.assertIsInstance(i.price, Decimal)
        self.assertEqual(i.price, 0)

    def test_price_max_digits(self):
        i = Item.objects.create(name='foo', fabrics=5, )
        msg = 'Ensure that there are no more than 6 digits in total.'
        with self.assertRaisesMessage(ValidationError, msg):
            i.price = 1234567
            i.full_clean()

    def test_price_max_decimals(self):
        i = Item.objects.create(name='foo', fabrics=5, )
        msg = 'Ensure that there are no more than 2 decimal places.'
        with self.assertRaisesMessage(ValidationError, msg):
            i.price = 12.345
            i.full_clean()

    def test_stocked(self):
        i = Item.objects.create(name='foo', fabrics=5, )
        self.assertEqual(i.stocked, 0)  # default value
        self.assertEqual(
            i._meta.get_field('stocked').verbose_name, 'Stock uds')
        self.assertIsInstance(i.stocked, int)

    def test_stocked_field_cant_be_over_32767(self):
        """However, it raises invalid opertion on calculating health."""
        i = Item.objects.create(name='foo', fabrics=5, )
        msg = "[<class 'decimal.InvalidOperation'>]"
        with self.assertRaisesMessage(InvalidOperation, msg):
            i.stocked = 33000
            i.save()

    def test_total_sales(self):
        """Tested in sales default period."""
        pass

    def test_health(self):
        i = Item.objects.create(name='foo', fabrics=5, )
        i = Item.objects.get(pk=i.pk)
        self.assertEqual(i.health, -100)  # Calculated on save
        self.assertEqual(
            i._meta.get_field('health').verbose_name, 'health')
        self.assertIsInstance(i.health, Decimal)

    def test_item_str(self):
        i = Item.objects.create(name='Test item', fabrics=5.2)
        self.assertEqual(i.__str__(), 'No definido Test item S-1 (0€)')

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
        msg = "'Predeterminado' name is reserved"
        with self.assertRaisesMessage(ValidationError, msg):
            i = Item(name='Predeterminado', fabrics=5, item_type='19',
                     item_class='S', size=1, price=0, stocked=0, )
            i.full_clean()

    def test_save_health(self):
        i = Item.objects.create(name='foo', fabrics=5, )

        # No sales and no stock
        self.assertEqual(i.health, -100)

        # No sales and stock
        i.stocked = 5
        i.save()
        self.assertEqual(i.health, -5)

        # Sales and stock
        o = Order.objects.first()
        [OrderItem.objects.create(element=i, reference=o) for _ in range(3)]
        o.kill()  # update stock and health
        i = Item.objects.get(pk=i.pk)  # reload item data

        # 2 over 3 sales in 12 months plus 300 since the order was regular
        self.assertEqual(i.health, (2 / (3/12)) + 300)

        o.ref_name = 'Quick'  # Make one of the orders express
        o.save()
        i.save()
        self.assertEqual(i.health, (2 / (3/12)))

    def test_sales_default_period(self):
        # clone the order
        o1 = Order.objects.first()
        o1.pk = None
        o1.save()
        o2 = Order.objects.first()
        self.assertNotEqual(o1, o2)
        self.assertEqual(Order.objects.count(), 2)

        # Assign some items to them
        i = Item.objects.create(name='foo', fabrics=5, stocked=5)
        for order in Order.objects.all():
            OrderItem.objects.create(element=i, reference=order, price=5)
            order.kill()
        self.assertEqual(i.sales(), 2)
        o2.delivery = date(2018, 12, 31)  # Irrelevant
        o2.save()

        i.save()  # recalculate

        self.assertEqual(i.total_sales, 2)
        self.assertEqual(i.year_sales, 1)

    def test_sales_raises_type_and_value_errors(self):
        i = Item.objects.create(name='foo', fabrics=5, stocked=5)
        msg = 'Period should be timedelta.'
        with self.assertRaisesMessage(TypeError, msg):
            i.sales('void')

        msg = 'Period must be positive.'
        with self.assertRaisesMessage(ValueError, msg):
            i.sales(-timedelta(5))

    def test_sales_custom_period(self):
        # clone the order
        o1 = Order.objects.first()
        o1.pk = None
        o1.save()
        o2 = Order.objects.first()
        self.assertEqual(Order.objects.count(), 2)
        self.assertNotEqual(o1, o2)

        # Assign some items to them
        i = Item.objects.create(name='foo', fabrics=5, stocked=5)
        for order in Order.objects.all():
            OrderItem.objects.create(element=i, reference=order, price=5)
            order.kill()
        self.assertEqual(i.sales(timedelta(days=5)), 2)
        o2.delivery = date.today() - timedelta(days=6)  # Irrelevant
        o2.save()
        self.assertEqual(i.sales(timedelta(days=5)), 1)

    def test_sales_filters_status_9(self):
        # clone the order
        o1 = Order.objects.first()
        o1.pk = None
        o1.save()
        o2 = Order.objects.first()
        self.assertEqual(Order.objects.count(), 2)
        self.assertNotEqual(o1, o2)

        # Assign some items to it
        i = Item.objects.create(name='foo', fabrics=5, stocked=5)
        OrderItem.objects.create(element=i, reference=o2, price=5)
        o2.kill()
        self.assertEqual(i.sales(), 1)

    def test_sales_excludes_tz(self):
        # clone the order
        o1 = Order.objects.first()
        o1.pk = None
        o1.save()
        o2 = Order.objects.first()
        self.assertNotEqual(o1, o2)
        self.assertEqual(Order.objects.count(), 2)

        # Assign some items to them
        i = Item.objects.create(name='foo', fabrics=5, stocked=5)
        for order in Order.objects.all():
            OrderItem.objects.create(element=i, reference=order, price=5)
            order.kill()
        self.assertEqual(i.sales(), 2)
        o2.customer = Customer.objects.create(
            name='Trapuzarrak', cp=0, phone=0)  # Irrelevant
        o2.save()
        self.assertEqual(i.sales(), 1)

    def test_consistent_foreign(self):
        # Create some siblings
        sizes = ('1', '2', '3', '4')
        a, b, c, d = [Item.objects.create(
            name='foo', item_type='2', fabrics=5, size=s) for s in sizes]

        # Create some non-siblings items
        Item.objects.create(name='foo', item_type='3', fabrics=2)
        Item.objects.create(name='bar', item_type='2', fabrics=2)
        Item.objects.create(name='bar', item_type='3', fabrics=2)

        self.assertEqual(Item.objects.filter(foreing=True).count(), 0)

        a.foreing = True
        a.save()
        self.assertEqual(Item.objects.get(foreing=True), a)

        a.consistent_foreign()
        self.assertEqual(Item.objects.filter(foreing=True).count(), 4)
        for i in Item.objects.filter(foreing=True):
            self.assertTrue(i in [a, b, c, d])

    def test_item_html_string(self):
        i = Item.objects.create(
            name='foo', item_type='2', item_class='M', size='xs', fabrics=5)
        html_str = (
            '\n<div class="d-block"><span class="mr-1">Pantalón foo</span>' +
            '</div><div class="d-block"><span class="badge badge-primary' +
            ' mr-1">Medium</span><span class="badge badge-info mr-1">T-xs' +
            '</span></div>\n')
        self.assertEqual(i.html_string, html_str)

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

    def test_pretty_average(self):
        items = [Item.objects.create(
            name=s, fabrics=10, price=30) for s in ('a', 'b', 'c',)]

        for n, item in enumerate(items):
            OrderItem.objects.create(
                element=item, qty=10 * n + 1, reference=Order.objects.first(),
                crop=timedelta(seconds=10),
                sewing=timedelta(seconds=20),
                iron=timedelta(seconds=30), )

        a = Item.objects.first()
        self.assertEqual(a.pretty_avg, ['10s', '20s', '30s'])

    def test_production(self):
        o = Order.objects.first()
        i = Item.objects.create(name='i', fabrics=10, price=30, )
        f = Item.objects.create(name='f', fabrics=10, price=30, foreing=True)
        self.assertEqual(i.production, 0)
        self.assertEqual(f.production, 0)
        oi = OrderItem.objects
        a, b, c = [
            oi.create(reference=o, element=i, qty=10) for _ in range(3)]
        c.element = f
        c.save()
        self.assertEqual(i.production, 20)
        self.assertEqual(f.production, 0)


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
        Item.objects.create(name='Test item', fabrics=5, price=10, stocked=10)

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

    def test_batch(self):
        u = User.objects.first()
        tz = Customer.objects.create(name='trapuzarrak', cp=0, phone=0)
        cs = Customer.objects.first()
        a = Order.objects.first()
        b = Order.objects.create(
            user=u, customer=tz, ref_name='foo', delivery=date.today())
        c = Order.objects.create(
            user=u, customer=cs, ref_name='bar', delivery=date.today())
        i = OrderItem.objects.create(element=Item.objects.first(), reference=a)
        self.assertEqual(i.batch, None)
        i.batch = b
        i.save()
        self.assertIsInstance(i.batch, Order)

        i.batch = a
        msg = 'Lote y pedido no pueden ser iguales'
        with self.assertRaisesMessage(ValidationError, msg):
            i.full_clean()

        i.batch = c
        msg = ('El numero de lote tiene que corresponder con un pedido ' +
               'de trapuzarrak')
        with self.assertRaisesMessage(ValidationError, msg):
            i.full_clean()

        b.delete()
        i = OrderItem.objects.get(pk=i.pk)
        self.assertEqual(i.batch, None)

    def test_orders_with_timed_items_are_at_least_status_3(self):
        o = Order.objects.first()
        self.assertEqual(o.status, '1')
        i = OrderItem.objects.create(
            reference=o, element=Item.objects.last(), crop=timedelta(1))
        self.assertEqual(o.status, '3')
        o.kanban_backward()
        self.assertEqual(o.status, '2')
        i.sewing = timedelta(1)
        i.save()
        self.assertEqual(o.status, '3')
        o.kanban_forward()
        self.assertEqual(o.status, '6')
        i.iron = timedelta(1)
        i.save()
        self.assertEqual(o.status, '6')

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

    def test_orderitem_tz_orders_have_no_stock_items(self):
        """TZ orders can't have stock items."""
        tz = Customer.objects.create(name='TrapuZarrak', phone=0, cp=0)
        order = Order.objects.first()
        order.customer = tz
        order.save()
        item = OrderItem.objects.create(
            element=Item.objects.first(), reference=order, stock=True)

        self.assertFalse(item.stock)

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

    def test_tz_orders_cant_contain_foreign_items(self):
        tz = Customer.objects.create(name='TrapuZarrak', phone=0, cp=0)
        order = Order.objects.first()
        order.customer = tz
        order.save()
        base_item = Item.objects.last()
        base_item.foreing = True
        base_item.save()
        item = OrderItem.objects.create(element=base_item, reference=order)
        with self.assertRaises(ValidationError):
            item.clean()

    def test_adding_more_items_than_stocked_raises_error(self):
        base_item = Item.objects.last()
        self.assertEqual(base_item.stocked, 10)

        # Test first express orders
        order = Order.objects.first()
        order.ref_name = 'Quick'
        order.save()
        item = OrderItem.objects.create(
            element=base_item, reference=order, qty=11)
        msg = 'Estás intentando añadir más prendas de las que tienes.'
        with self.assertRaisesMessage(ValidationError, msg):
            item.clean()

        # Now regular ones when adding stock items
        order.ref_name = 'foo'
        order.save()
        item = OrderItem.objects.create(
            element=base_item, reference=order, qty=11, stock=True, )
        with self.assertRaisesMessage(ValidationError, msg):
            item.clean()

        # However, adding non-stock sholud be ok
        item = OrderItem.objects.create(
            element=base_item, reference=order, qty=11, stock=False, )
        self.assertFalse(item.clean())

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
        cancelled, old, invoiced, tz_owned = Order.live.all()[:4]
        cancelled.status = '8'
        cancelled.save()
        old.delivery = date(2018, 12, 31)
        old.save()
        invoiced.kill()
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

        self.assertEqual(
            test_item.prettified_est, ['50.0h', '100.0h', '150.0h'])

    def test_ticket_print(self):
        item_obj = Item.objects.create(
            name='ticket print', item_type='1', fabrics=10, price=30)
        item = OrderItem.objects.create(
            element=item_obj, reference=Order.objects.first(), qty=5, )
        self.assertEqual(item.ticket_print, '5 x Falda ticket print')

        # Now test a generic object (foreign)
        item_obj.foreing = True
        item_obj.save()
        self.assertEqual(item.ticket_print, '5 x Falda genérica')

        # Check the gender
        item_obj.item_type = '2'
        item_obj.save()
        self.assertEqual(item.ticket_print, '5 x Pantalón genérico')

        # Check the exceptions
        item_obj.item_type = '12'
        item_obj.save()
        self.assertEqual(item.ticket_print, '5 x Traje de niña genérico')


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

    def test_up_does_nothing_for_first_element(self):
        [PQueue.objects.create(item=item) for item in OrderItem.objects.all()]
        first = PQueue.objects.first()
        self.assertEqual(first.score, 1000)
        first.up()
        self.assertEqual(first.score, 1000)

    def test_top_does_nothing_for_first_element(self):
        [PQueue.objects.create(item=item) for item in OrderItem.objects.all()]
        first = PQueue.objects.first()
        self.assertEqual(first.score, 1000)
        first.top()
        self.assertEqual(first.score, 1000)

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

    def test_down_does_nothing_if_last(self):
        """When the element is last, should warn and do nothing."""
        _, _, last = [
            PQueue.objects.create(item=i) for i in OrderItem.objects.all()]
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 1002)
        last.down()
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 1002)

    def test_down(self):
        """Lower the position of an element."""
        for item in OrderItem.objects.all():
            PQueue.objects.create(item=item)
        first, mid, last = PQueue.objects.all()
        first.down()
        self.assertEqual(PQueue.objects.get(pk=mid.pk).score, 999)
        self.assertEqual(PQueue.objects.get(pk=first.pk).score, 1000)
        self.assertEqual(PQueue.objects.get(pk=last.pk).score, 1002)

    def test_bottom_does_nothig_if_last(self):
        """When the element is last, should warn and do nothing."""
        _, _, last = [
            PQueue.objects.create(item=i) for i in OrderItem.objects.all()]
        self.assertEqual(last.score, 1002)
        last.bottom()
        self.assertEqual(last.score, 1002)

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

        # When there are another items queued, uncomplete sends to bottom
        PQueue.objects.create(item=OrderItem.objects.last())
        item.complete()
        item.uncomplete()
        self.assertEqual(item.score, 1002)


class TestInvoice(TestCase):
    """Test the invoice model."""

    def setUp(self):
        """Create the necessary items on database at once."""
        # Create a user
        u = User.objects.create_user(
            username='user', is_staff=True, )

        # Create a customer
        c = Customer.objects.create(
            name='Customer Test', city='NoCity', phone='6', cp='1')

        # Create an order
        order = Order.objects.create(
            user=u, customer=c, ref_name='foo', delivery=date.today())

        # Create obj item
        item = Item.objects.create(
            name='Test item', fabrics=5, price=10, stocked=10)

        # Create orderitems
        OrderItem.objects.create(reference=order, element=item)

    def test_reference_is_a_one_to_one_field(self):
        """That is, each order should appear once on the table."""
        Order.objects.first().kill()
        msg = 'Invoice with this Reference already exists.'
        with self.assertRaisesMessage(ValidationError, msg):
            Invoice(reference=Order.objects.first()).validate_unique()

    def test_reference_delete_cascade(self):
        """If order is deleted so is invoice."""
        o = Order.objects.first()
        o.kill()
        self.assertEqual(Invoice.objects.count(), 1)
        o.delete()
        self.assertFalse(Invoice.objects.all())

    def test_reference_pk_matches_invoice_pk(self):
        """Since reference has primary key true."""
        order = Order.objects.first()
        order.kill()
        self.assertEqual(order.pk, order.invoice.pk)

    def test_issued_on_is_datetime(self):
        """Test the data type and the date."""
        order = Order.objects.first()
        order.kill()
        self.assertIsInstance(order.invoice.issued_on, datetime)
        self.assertEqual(order.invoice.issued_on.date(), date.today())

    def test_only_kill_can_issue_invoices(self):
        self.assertFalse(Invoice.objects.all())
        Invoice.objects.create(reference=Order.objects.first())  # does nothing
        self.assertFalse(Invoice.objects.all())

    def test_invoice_no_default_1(self):
        """When there're no invoices yet, the first one is 1."""
        order = Order.objects.first()
        order.kill()
        self.assertEqual(order.invoice.invoice_no, 1)

    def test_invoice_no_autoincrement(self):
        """When there're invoices should add one to the last one."""
        u, c = User.objects.first(), Customer.objects.first()
        for _ in range(3):
            o = Order.objects.create(
                user=u, customer=c, ref_name='foo', delivery=date.today())
            OrderItem.objects.create(reference=o, element=Item.objects.last())
            o.kill()
        invoices = Invoice.objects.reverse()
        [self.assertEqual(i.invoice_no, n+1) for n, i in enumerate(invoices)]

    def test_invoice_no_several_saves(self):
        """Ensure the number doesn't rise on multiple save calls."""
        order = Order.objects.first()
        order.kill()
        self.assertEqual(order.invoice.invoice_no, 1)
        order.invoice.pay_method = 'V'
        order.invoice.save(kill=True)
        self.assertEqual(order.invoice.invoice_no, 1)

    def test_invoice_amount_sums(self):
        """Test the proper sum of items."""
        o = Order.objects.first()
        i = Item.objects.last()
        for _ in range(3):
            OrderItem.objects.create(reference=o, element=i, price=20, )
        o.kill()
        self.assertIsInstance(o.invoice.amount, float)
        self.assertEqual(o.invoice.amount, 70)

    def test_pay_method_allowed_means(self):
        """Test the proper payment methods."""
        o = Order.objects.first()
        o.kill()
        self.assertEqual(o.invoice.pay_method, 'C')
        for pay_method in ('V', 'T'):
            o.invoice.pay_method = pay_method
            o.invoice.full_clean()
            o.invoice.save(kill=True)
            self.assertEqual(o.invoice.pay_method, pay_method)
            self.assertEqual(o.invoice.invoice_no, 1)

        with self.assertRaises(ValidationError):
            o.invoice.pay_method = 'K'
            o.invoice.full_clean()

    def test_total_amount_0_is_allowed(self):
        """But invoices with 0 amount are allowed, eg, with discount."""
        order = Order.objects.first()
        OrderItem.objects.create(
            reference=order, element=Item.objects.last(), price=-10)
        order.kill()
        self.assertEqual(order.invoice.amount, 0)

    def test_tz_cannot_be_invoiced(self):
        """Ensure that tz can't be invoiced."""
        tz = Customer.objects.create(name='TraPuZarrak', phone=0, cp=0)
        tz_order = Order.objects.first()
        tz_order.customer = tz
        tz_order.save()
        msg = 'TZ can\'t be invoiced'
        with self.assertRaisesMessage(ValidationError, msg):
            i = Invoice(reference=tz_order)
            i.clean()

    def test_invoice_with_no_items_raises_error(self):
        for i in OrderItem.objects.all():
            i.delete()
        o = Order.objects.first()
        self.assertTrue(o.has_no_items)

        msg = 'The invoice has no items'
        with self.assertRaisesMessage(ValidationError, msg):
            i = Invoice(reference=o)
            i.clean()

    def test_printable_ticket_returns_bytesIO(self):
        """Test the output for the method."""
        order = Order.objects.first()
        order.kill()
        self.assertIsInstance(order.invoice.printable_ticket(), BytesIO)

    def test_line_cutter(self):
        """Test the different options for the method."""
        order = Order.objects.first()
        order.kill()

        # First test lines under 25 chars
        linestr = order.invoice.printable_ticket(lc='def foo')
        self.assertEqual(linestr, ('def foo', ))

        # Now over 25 chars
        long_str = 'A very long string with more than 25 characters'
        linestr = order.invoice.printable_ticket(lc=long_str)
        self.assertEqual(
            linestr, ('more than 25 characters', 'A very long string with'))


class TestExpenseCategory(TestCase):

    def test_creation_is_a_date_time_field(self):
        e = ExpenseCategory.objects.first()  # default
        self.assertIsInstance(e.creation, datetime)

    def test_name_max_length(self):
        msg = 'value too long for type character varying(64)'
        with self.assertRaisesMessage(DataError, msg):
            ExpenseCategory.objects.create(name=70 * 'a')

    def test_name_is_unique(self):
        with self.assertRaises(IntegrityError):
            ExpenseCategory.objects.create(name='default')

    def test_description_can_be_blank_and_null(self):
        e = ExpenseCategory.objects.create(name='test')
        self.assertEqual(e.description, None)

        b = ExpenseCategory(name='blank')
        self.assertFalse(b.full_clean())

    def test_str(self):
        e = ExpenseCategory.objects.first()  # default
        self.assertEqual(e.__str__(), 'default')


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

    def test_category(self):
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100, )
        expense.full_clean()
        self.assertIsInstance(expense.category, ExpenseCategory)
        self.assertEqual(expense.category.name, 'default')

        ec = ExpenseCategory.objects.create(name='foo')
        expense.category = ec
        expense.save()

        self.assertEqual(expense.category.name, 'foo')

        ec.delete()
        expense = Expense.objects.get(pk=expense.pk)
        self.assertEqual(expense.category.name, 'default')

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

    def test_closed_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100,
            notes='Notes')
        expense.full_clean()
        self.assertIsInstance(expense.closed, bool)
        self.assertFalse(expense.closed)
        self.assertEqual(
            expense._meta.get_field('closed').verbose_name,
            'Cerrado')

        expense.kill()
        self.assertTrue(expense.closed)

        self.assertEqual(CashFlowIO.objects.count(), 1)
        cf = CashFlowIO.objects.first()
        cf.delete()
        expense.save()  # update status
        self.assertFalse(expense.closed)

    def test_consultancy_field(self):
        """Test the field."""
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='Test',
            issued_on=date.today(), concept='Concept', amount=100,
            notes='Notes')
        self.assertIsInstance(expense.consultancy, bool)
        self.assertTrue(expense.consultancy)

    def test_str(self):
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='foo',
            issued_on=date.today(), concept='bar', amount=100, notes='baz')
        s = '{} {}'.format(expense.pk, 'Customer Test')
        self.assertEqual(expense.__str__(), s)

    def test_kill(self):
        expense = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='foo',
            issued_on=date.today(), concept='bar', amount=100, notes='baz')

        with self.assertRaises(ObjectDoesNotExist):
            CashFlowIO.objects.get(expense=expense)

        self.assertEqual(CashFlowIO.objects.count(), 0)

        for pm, _ in PAYMENT_METHODS:
            expense.pay_method = pm
            expense.save()
            expense.kill()
            cf = CashFlowIO.objects.get(expense=expense)

            self.assertEqual(expense.pending, 0)
            self.assertEqual(cf.amount, 100)
            self.assertEqual(cf.pay_method, pm)

            expense.kill()  # should do nothing
            self.assertEqual(expense.pending, 0)
            self.assertEqual(CashFlowIO.objects.count(), 1)
            self.assertTrue(CashFlowIO.objects.get(expense=expense))

            cf.delete()

    def test_already_paid(self):
        e = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='foo',
            issued_on=date.today(), concept='bar', amount=100, notes='baz')

        self.assertEqual(e.already_paid, 0)

        for _ in range(2):
            CashFlowIO.objects.create(expense=e, amount=10)

        self.assertEqual(e.already_paid, 20)

    def test_pending_amount(self):
        e = Expense.objects.create(
            issuer=Customer.objects.first(), invoice_no='foo',
            issued_on=date.today(), concept='bar', amount=100, notes='baz')

        for _ in range(2):
            CashFlowIO.objects.create(expense=e, amount=10)

        self.assertEqual(e.pending, 80)

    def test_no_address_raises_error(self):
        """Raise ValidationError with partially filled customers."""
        void = Customer.objects.create(
            name='Customer Test', city='This computer',
            phone='666666666', CIF='444E', cp=48003, provider=True, )
        with self.assertRaises(ValidationError):
            Expense.objects.create(
                issuer=void, invoice_no='Test',
                issued_on=date.today(), concept='Concept', amount=100, )

    def test_no_city_raises_error(self):
        """Raise ValidationError with partially filled customers."""
        void = Customer.objects.create(
            name='Customer Test', address='Cache', phone='666666666',
            CIF='444E', cp=48003, provider=True, )
        with self.assertRaises(ValidationError):
            Expense.objects.create(
                issuer=void, invoice_no='Test', issued_on=date.today(),
                concept='Concept', amount=100, )

    def test_no_cif_raises_error(self):
        """Raise ValidationError with partially filled customers."""
        void = Customer.objects.create(
            name='Customer Test', address='Cache', city='This computer',
            phone='666666666', cp=48003, provider=True, )
        with self.assertRaises(ValidationError):
            Expense.objects.create(
                issuer=void, invoice_no='Test', issued_on=date.today(),
                concept='Concept', amount=100, )

    def test_no_provider_raises_error(self):
        """Only providers can be issuers."""
        void = Customer.objects.create(
            name='Customer Test', address='Cache', city='This computer',
            phone='666666666', CIF='444E', cp=48003, )
        with self.assertRaises(ValidationError):
            Expense.objects.create(
                issuer=void, invoice_no='Test', issued_on=date.today(),
                concept='Concept', amount=100, )


class TestCashFlowIO(TestCase):
    """Test the CashFlowIO model."""

    def setUp(self):
        """Create the necessary items on database at once."""
        # Create a user
        u = User.objects.create_user(username='user', is_staff=True, )

        # Create customers
        c = Customer.objects.create(name='foo', phone=99, cp=22)
        p = Customer.objects.create(name='foo', address='bar', city='baz',
                                    CIF='zaz', phone=99, cp=22, provider=True)

        # Create an order
        o = Order.objects.create(user=u, customer=c, ref_name='foo',
                                 delivery=date.today(), )

        # Create items
        i = Item.objects.create(
            name='Test item', fabrics=5, price=10, stocked=20)
        OrderItem.objects.create(reference=o, element=i, qty=10)

        # Create an expense
        Expense.objects.create(
            issuer=p, invoice_no='foo', issued_on=date.today(), concept='bar',
            amount=100, )

    def test_creation_is_a_date_time_field(self):
        cf = CashFlowIO.objects.create(order=Order.objects.first(), amount=50)
        self.assertIsInstance(cf.creation, datetime)

    def test_order_is_foreign_key(self):
        cf = CashFlowIO.objects.create(order=Order.objects.first(), amount=50)
        self.assertIsInstance(cf.order, Order)

    def test_order_can_be_null_and_blank(self):
        cf = CashFlowIO(expense=Expense.objects.first(), amount=50)
        cf.full_clean()  # blank
        cf.save()
        cf = CashFlowIO.objects.get(pk=cf.pk)
        self.assertEqual(cf.order, None)  # Null

    def test_order_deletes_cascade(self):
        o = Order.objects.first()
        CashFlowIO.objects.create(order=o, amount=50)
        self.assertEqual(CashFlowIO.objects.count(), 1)

        o.delete()
        self.assertEqual(CashFlowIO.objects.count(), 0)

    def test_order_related_name_is_cfio_prepaids(self):
        o = Order.objects.first()
        cf = CashFlowIO.objects.create(order=o, amount=50)
        self.assertEqual(o.cfio_prepaids.all()[0], cf)
        self.assertEqual(o.cfio_prepaids.count(), 1)

    def test_expense_is_foreign_key(self):
        cf = CashFlowIO.objects.create(
            expense=Expense.objects.first(), amount=50)
        self.assertIsInstance(cf.expense, Expense)

    def test_expense_can_be_null_and_blank(self):
        cf = CashFlowIO(order=Order.objects.first(), amount=50)
        cf.full_clean()  # blank
        cf.save()
        cf = CashFlowIO.objects.get(pk=cf.pk)
        self.assertEqual(cf.expense, None)  # Null

    def test_expense_deletes_cascade(self):
        e = Expense.objects.first()
        CashFlowIO.objects.create(expense=e, amount=50)
        self.assertEqual(CashFlowIO.objects.count(), 1)

        e.delete()
        self.assertEqual(CashFlowIO.objects.count(), 0)

    def test_amount_is_decimal(self):
        cf = CashFlowIO.objects.create(order=Order.objects.first(), amount=50)
        cf = CashFlowIO.objects.get(pk=cf.pk)
        self.assertIsInstance(cf.amount, Decimal)

    def test_amount_max_digits(self):
        i = OrderItem.objects.first()
        i.qty = 100000
        i.save()
        with self.assertRaises(InvalidOperation):
            CashFlowIO.objects.create(order=i.reference, amount=500000)

    def test_amount_max_decimals(self):
        cf = CashFlowIO.objects.create(
            order=Order.objects.first(), amount=20.355)
        msg = 'Ensure that there are no more than 2 decimal places.'
        with self.assertRaisesMessage(ValidationError, msg):
            cf.full_clean()

    def test_pay_method_length(self):
        msg = 'value too long for type character varying(1)'
        with self.assertRaisesMessage(DataError, msg):
            CashFlowIO.objects.create(
                order=Order.objects.first(), amount=10, pay_method='void')

    def test_pay_method_out_of_choices(self):
        cf = CashFlowIO.objects.create(
            order=Order.objects.first(), amount=10, pay_method='X')
        msg = 'Value \'X\' is not a valid choice.'
        with self.assertRaisesMessage(ValidationError, msg):
            cf.full_clean()

    def test_default_pay_method(self):
        cf = CashFlowIO.objects.create(order=Order.objects.first(), amount=10)
        self.assertEqual(cf.pay_method, 'C')

    def test_custom_managers(self):
        for _ in range(2):
            CashFlowIO.objects.create(order=Order.objects.first(), amount=10)
            CashFlowIO.objects.create(order=Order.objects.first(), amount=10)
            CashFlowIO.objects.create(
                expense=Expense.objects.first(), amount=10)

        all = CashFlowIO.objects
        inbounds, outbounds = CashFlowIO.inbounds, CashFlowIO.outbounds
        self.assertEqual(all.count(), 6)
        self.assertEqual(inbounds.count(), 4)
        self.assertEqual(outbounds.count(), 2)

        for cf in inbounds.all():
            self.assertTrue(cf.order)
            self.assertFalse(cf.expense)

        for cf in outbounds.all():
            self.assertTrue(cf.expense)
            self.assertFalse(cf.order)

    def test_save_closes_expense(self):
        cf = CashFlowIO.objects.create(
            expense=Expense.objects.first(), amount=50)
        self.assertFalse(cf.expense.closed)
        cf = CashFlowIO.objects.create(
            expense=Expense.objects.first(), amount=50)  # kills the debt
        self.assertTrue(cf.expense.closed)

    def test_delete_opens_the_expense_again(self):
        self.assertFalse(Expense.objects.first().closed)
        cf = CashFlowIO.objects.create(
            expense=Expense.objects.first(), amount=100)  # kills the debt
        self.assertTrue(cf.expense.closed)
        cf.delete()
        self.assertFalse(Expense.objects.first().closed)

    def test_order_and_expense_cant_be_null_simultaneously(self):
        msg = 'Pedido y gasto no pueden estar vacios al mismo tiempo.'
        with self.assertRaisesMessage(ValidationError, msg):
            CashFlowIO.objects.create(amount=10)

    def test_order_and_expense_cant_exist_simultaneously(self):
        msg = 'Pedido y gasto no pueden tener valor al mismo tiempo.'
        with self.assertRaisesMessage(ValidationError, msg):
            CashFlowIO.objects.create(
                order=Order.objects.first(), expense=Expense.objects.first(),
                amount=10)

    def test_amount_cant_be_over_pending_in_orders(self):
        msg = 'No se puede pagar más de la cantidad pendiente (100.0).'
        with self.assertRaisesMessage(ValidationError, msg):
            CashFlowIO.objects.create(order=Order.objects.first(), amount=110)

    def test_amount_cant_be_over_pending_in_expenses(self):
        msg = 'No se puede pagar más de la cantidad pendiente (100.00).'
        with self.assertRaisesMessage(ValidationError, msg):
            CashFlowIO.objects.create(
                expense=Expense.objects.first(), amount=110)

    def test_tz_orders_should_raise_rerror(self):
        tz = Customer.objects.create(name='TrapuzaRrAk', phone=0, cp=0)
        o = Order.objects.first()
        o.customer = tz
        o.save()
        msg = 'Los pedidos de trapuzarrak no admiten pagos'
        with self.assertRaisesMessage(ValidationError, msg):
            CashFlowIO.objects.create(order=o, amount=10)

    def test_update_old(self):
        u = User.objects.first()
        c = Customer.objects.get(provider=False)
        p = Customer.objects.get(provider=True)
        i = Item.objects.last()
        for _ in range(3):
            o = Order.objects.create(user=u, customer=c, delivery=date.today())
            OrderItem.objects.create(element=i, reference=o, price=10)
            o.kill()
            Expense.objects.create(
                issuer=p, invoice_no='foo', issued_on=date.today(),
                concept='bar', amount=20)

        # Get rid of setUp order and expense to work more easily
        f1, f2 = Order.objects.first(), Expense.objects.first()
        f1.delete()
        f2.delete()

        # Invoice kills auto the debts so delete them
        for cf in CashFlowIO.objects.all():
            cf.delete()

        self.assertFalse(CashFlowIO.objects.all())

        # Now update
        CashFlowIO.update_old()

        o, e = Order.objects.all(), Expense.objects.all()
        cfs = CashFlowIO.objects.all()
        self.assertEqual(o.count() + e.count(), cfs.count())

        for cf in cfs:
            self.assertEqual(cf.creation.date(), date.today())
            if cf.order:
                self.assertEqual(cf.amount, 10)
            else:
                self.assertEqual(cf.amount, 20)


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


class TestStatusShift(TestCase):
    """Test the status tracker model."""

    def setUp(self):
        """Configure the test.

        Notice that Order creates auto a StatusShift.
        """
        u = User.objects.create_user(username='foo', password='bar')
        c = Customer.objects.create(name='foo', phone=0, cp=0)
        Order.objects.create(
            user=u, customer=c, ref_name='foo', delivery=date.today(), )

    def test_order_field(self):
        ss = StatusShift.objects.first()
        self.assertIsInstance(ss.order, Order)

        o = Order.objects.first()
        self.assertEqual(o.status_shift.first(), ss)  # related name

        ss.order.delete()
        self.assertFalse(StatusShift.objects.count())  # Deletes cascade

    def test_date_in_field(self):
        ss = StatusShift.objects.first()
        self.assertIsInstance(ss.date_in, datetime)
        self.assertEqual(ss.date_in.date(), date.today())

    def test_date_out_field(self):
        ss = StatusShift.objects.first()
        self.assertFalse(ss.date_out)  # default Null
        ss.date_out = timezone.now() + timedelta(days=1)
        ss.save()
        self.assertIsInstance(ss.date_out, datetime)

    def test_status_field(self):
        ss = StatusShift.objects.first()
        self.assertEqual(ss.status, '1')  # default
        for s, _ in Order.STATUS[1:]:
            ss.status = s
            ss.save()
            self.assertEqual(ss.status, s)

    def test_status_length(self):
        ss = StatusShift.objects.first()
        msg = 'value too long for type character varying(1)'
        with self.assertRaisesMessage(DataError, msg):
            ss.status = 'void'
            ss.save()

    def test_status_out_of_choices(self):
        ss = StatusShift.objects.first()
        msg = "Value 'void' is not a valid choice."
        with self.assertRaisesMessage(ValidationError, msg):
            ss.status = 'void'
            ss.full_clean()

    def test_direct_save(self):
        """setUp should have created the first one."""
        self.assertEqual(StatusShift.objects.count(), 1)

    def test_close_previous_before_opening(self):
        o = Order.objects.first()
        o.kanban_forward()
        s1, s2 = StatusShift.objects.all()
        self.assertTrue(s1.date_out)

    def test_skip_on_status_unchanged(self):
        self.assertEqual(StatusShift.objects.count(), 1)

        o = Order.objects.first()
        o.ref_name = 'does not change status'
        o.save()
        self.assertEqual(StatusShift.objects.count(), 1)

        o.kanban_forward()
        s1, s2 = StatusShift.objects.all()
        self.assertEqual(s1.status, '1')
        self.assertEqual(s2.status, '2')

    def test_reaching_status_9_closes_the_entry(self):
        s1 = StatusShift.objects.first()
        self.assertFalse(s1.date_out)
        s1.status = '9'
        s1.save()

    def test_order_must_keep_at_least_one_ss_open(self):
        self.assertEqual(StatusShift.objects.count(), 1)
        msg = 'Can\'t delete the last status shift of an order'
        with self.assertRaisesMessage(ValidationError, msg):
            StatusShift.objects.first().delete()

    def test_cant_delete_other_than_last_entries(self):
        Order.objects.first().kanban_forward()
        Order.objects.first().kanban_forward()
        s1, s2, s3 = StatusShift.objects.all()
        msg = 'Can\'t delete other than last entries'
        for s in (s1, s2):
            with self.assertRaisesMessage(ValidationError, msg):
                s.delete()

    def test_delete_reopens_last_status(self):
        Order.objects.first().kanban_forward()
        Order.objects.first().kanban_forward()
        s1, s2, s3 = StatusShift.objects.all()
        self.assertTrue(s1.date_out)
        self.assertTrue(s2.date_out)
        self.assertFalse(s3.date_out)
        s3.delete()
        self.assertEqual(StatusShift.objects.count(), 2)
        self.assertFalse(StatusShift.objects.last().date_out)

    def test_orders_cant_have_more_than_one_ss_open(self):
        o = Order.objects.first()
        self.assertFalse(StatusShift.objects.first().date_out)
        s2 = StatusShift(order=o, status='2')
        s2.save(force_save=True)  # does not close the previous
        msg = 'Order {} has more than one statusShift open'.format(o.pk)
        with self.assertRaisesMessage(ValidationError, msg):
            s2.full_clean()

    def test_date_out_should_be_after_date_in(self):
        s1 = StatusShift.objects.first()
        s1.date_out = timezone.now() - timedelta(seconds=240)
        i, o = s1.date_in, s1.date_out
        msg = 'date_out ({}) is before date_in ({})'.format(i, o)
        with self.assertRaisesMessage(ValidationError, msg):
            s1.full_clean()

    def test_last_fetchs_the_last_entry_of_a_given_order(self):
        Order.objects.first().kanban_forward()
        Order.objects.first().kanban_forward()
        s1, _, s3 = StatusShift.objects.all()
        self.assertEqual(s1.last, s3)


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
        t = Timetable(user=self.user, hours=timedelta(hours=15.5))
        msg = 'Entry lasts more than 15h'
        with self.assertRaisesMessage(ValidationError, msg):
            t.clean()
        end = timezone.now() + timedelta(hours=15.5)
        t = Timetable(user=self.user, end=end)
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
