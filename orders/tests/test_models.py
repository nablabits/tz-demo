"""Test the app models."""
from django.test import TestCase
from orders.models import Customer, Order, Comment, Item, OrderItem
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from datetime import date, timedelta, time


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

    def test_order_creation(self):
        """Test the order creation."""
        order = Order.objects.all()[0]
        today = date.today()
        order_str = str(today) + ' Customer Test example'
        self.assertTrue(isinstance(order, Order))
        self.assertEqual(order.__str__(), order_str)
        self.assertTrue(order.overdue)
        self.assertEqual(order.pending, -1000)

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
                       str(today) + ' Customer Test example')
        self.assertTrue(isinstance(comment, Comment))
        self.assertEqual(comment.__str__(), comment_str)

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

    def test_add_items_to_orders(self):
        """Test the proper item attachs to orders."""
        order = Order.objects.all()[0]
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

    def test_the_sum_of_times_per_item_in_an_order(self):
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
        Item.objects.create(name='Test item', fabrics=5)

    def test_orderitem_stock(self):
        """Items are by default new produced for orders."""
        item = OrderItem.objects.create(element=Item.objects.all()[0],
                                        reference=Order.objects.all()[0],
                                        )
        self.assertFalse(item.stock)
        self.assertIsInstance(item.stock, bool)
        self.assertEqual(item._meta.get_field('stock').verbose_name, 'Stock')
#
#
#
#
#
#
