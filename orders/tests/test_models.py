"""Test the app models."""
from django.test import TestCase
from orders.models import Customer, Order, Comment, Timing, Item, OrderItem
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth.models import User
from datetime import date, timedelta


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

    def test_timing_only_accepts_floats(self):
        """Ensure that duration strings are not allowed."""
        with self.assertRaises(ValidationError):
            Timing.objects.create(time='0:35')

    def test_item_object_creation(self):
        """Test the proper creation of item objects."""
        Item.objects.create(name='Test item',
                            item_type='2',
                            item_class='S',
                            size='10',
                            notes='Default notes',
                            fabrics=5.2)
        self.assertTrue(Item.objects.get(name='Test item'))

    def test_default_item_object_should_be_automatically_created(self):
        """The default item object is created by a migration."""
        default = Item.objects.get(name='Predeterminado')
        self.assertTrue(default)

    def test_the_item_object_named_default_is_reserved(self):
        """The item obj named default is reserved & raises ValidationError."""
        with self.assertRaises(ValidationError):
            Item.objects.create(name='Predeterminado',
                                item_type='0',
                                item_class='0',
                                size='0',
                                fabrics=2.2)

    def test_add_items_to_orders(self):
        """Test the proper item attachs to orders."""
        order = Order.objects.all()[0]
        item = Item.objects.create(name='Test item', fabrics=5.2)
        OrderItem.objects.create(description='Test item',
                                 reference=order,
                                 element=item)

        created_item = OrderItem.objects.get(description='Test item')
        self.assertEqual(created_item.item, '1')
        self.assertEqual(created_item.size, '1')
        self.assertEqual(created_item.reference, order)
        self.assertEqual(created_item.element, item)
        self.assertEqual(created_item.qty, 1)
        self.assertEqual(created_item.crop, timedelta(0))
        self.assertEqual(created_item.sewing, timedelta(0))
        self.assertEqual(created_item.iron, timedelta(0))

    def test_add_items_to_orders_default_item(self):
        """If no element is selected, Predetermiando is default."""
        order = Order.objects.all()[0]
        item = Item.objects.get(name='Predeterminado')
        OrderItem.objects.create(description='Test item',
                                 reference=order, )

        created_item = OrderItem.objects.get(description='Test item')
        self.assertEqual(created_item.element, item)

    def test_items_time_quality_property(self):
        """Test the proper value for timing."""
        order = Order.objects.all()[0]
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
