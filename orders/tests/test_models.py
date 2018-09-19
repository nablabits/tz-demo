"""Test the app models."""
from django.test import TestCase
from orders.models import Customer, Order, Comment, Timing
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from datetime import date


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
                             prepaid=1000)

        # Create comment
        Comment.objects.create(user=User.objects.get(pk=1),
                               reference=Order.objects.get(pk=1),
                               comment='This is a comment')

    def test_customer_creation(self):
        """Test the customer creation."""
        customer = Customer.objects.get(pk=1)
        self.assertTrue(isinstance(customer, Customer))
        self.assertEqual(customer.__str__(), 'Customer Test')

    def test_order_creation(self):
        """Test the order creation."""
        order = Order.objects.get(pk=1)
        today = date.today()
        order_str = str(today) + ' Customer Test example'
        self.assertTrue(isinstance(order, Order))
        self.assertEqual(order.__str__(), order_str)
        self.assertTrue(order.overdue)
        self.assertEqual(order.pending, -1000)

    def test_comment_creation(self):
        """Test the comment creation."""
        comment = Comment.objects.get(pk=1)
        today = date.today()
        comment_str = ('El ' + str(today) + ', user comentó en ' +
                       str(today) + ' Customer Test example')
        self.assertTrue(isinstance(comment, Comment))
        self.assertEqual(comment.__str__(), comment_str)

    def test_regular_timing(self):
        """Test the time creation."""
        # Create a single-use order
        customer = Customer.objects.get(name='Customer Test')
        Order.objects.create(user=User.objects.get(username='user'),
                             customer=customer,
                             ref_name='timeEx',
                             delivery=date(2018, 2, 1),
                             waist=10,
                             chest=20,
                             hip=30,
                             lenght=40,
                             budget=2000,
                             prepaid=1000)

        order = Order.objects.get(ref_name='timeEx')
        Timing.objects.create(item=1,
                              item_class=2,
                              activity=2,
                              qty=5,
                              time=0.5,
                              reference=order,
                              notes='time test')
        time = Timing.objects.get(notes='time test')
        self.assertIsInstance(time, Timing)
        self.assertEqual(time.__str__(),
                         '{}x{}'.format(time.get_item_display(), time.qty))
        self.assertEqual(time.reference, order)

    def test_timimg_without_order_should_pick_up_the_last_one(self):
        """Test when no order is provided."""
        Timing.objects.create(item=1,
                              item_class=2,
                              activity=2,
                              qty=5,
                              time=0.5,
                              notes='time test')
        time = Timing.objects.get(notes='time test')
        order = Order.objects.latest('inbox_date')
        self.assertEqual(time.reference, order)


class TimingSpecial(TestCase):
    """Try creating times without order entries in the db."""

    def test_create_time_without_order_raises_error(self):
        """Creating times when there are no orders, should raise error."""
        with self.assertRaises(ObjectDoesNotExist):
            Timing.objects.create(item=1,
                                  item_class=2,
                                  activity=2,
                                  qty=5,
                                  time=0.5,
                                  notes='time test')
