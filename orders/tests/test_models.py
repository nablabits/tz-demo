"""Test the app models."""
from decimal import Decimal, InvalidOperation
from django.test import TestCase
from orders.models import (
    Customer, Order, Comment, Item, OrderItem, PQueue, Invoice, BankMovement)
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.contrib.auth.models import User
from datetime import date, timedelta, time, datetime


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
        order = Order.objects.first()
        today = date.today()
        order_str = str(today) + ' Customer Test example'
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
                       str(today) + ' Customer Test example')
        self.assertTrue(isinstance(comment, Comment))
        self.assertEqual(comment.__str__(), comment_str)


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

    def test_budget_and_prepaid_can_be_null(self):
        """Test the emptyness of fields and default value."""
        user = User.objects.first()
        c = Customer.objects.first()
        Order.objects.create(
            user=user, customer=c, ref_name='No Budget nor prepaid',
            delivery=date.today())
        order = Order.objects.get(ref_name='No Budget nor prepaid')
        self.assertEqual(order.prepaid, 0)

    def test_overdue(self):
        """Test the overdue attribute."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date(2017, 1, 1))
        self.assertTrue(order.overdue)

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

    def test_pending(self):
        """Test the correct amount."""
        user = User.objects.first()
        c = Customer.objects.first()
        order = Order.objects.create(
            user=user, customer=c, ref_name='test', delivery=date.today(),
            prepaid=50)
        for i in range(5):
            OrderItem.objects.create(
                reference=order, element=Item.objects.last())
        self.assertEqual(order.pending, -100)

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

    def test_orderitem_stock_true_for_express_orders(self):
        """Express orders only contain stocked items."""
        order = Order.objects.first()
        order.ref_name = 'Quick'
        order.save()
        object_item = Item.objects.first()
        item = OrderItem.objects.create(
            element=object_item, reference=Order.objects.first(), )
        self.assertTrue(item.stock)

    def test_add_items_to_orders_default_item(self):
        """If no element is selected, Predetermiando is default."""
        order = Order.objects.first()
        item = Item.objects.get(name='Predeterminado')
        OrderItem.objects.create(description='Test item',
                                 reference=order, )

        created_item = OrderItem.objects.get(description='Test item')
        self.assertEqual(created_item.element, item)

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
        self.assertEquals((queue[0].score, queue[1].score, queue[2].score),
                          (1000, 1001, 1002))

        pqueue.score = 100
        pqueue.save()
        queue = PQueue.objects.all()
        self.assertEquals((queue[0].score, queue[1].score, queue[2].score),
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
        """Test the proper raise when invoice is empty."""
        item = OrderItem.objects.first()
        item.delete()
        order = Order.objects.first()
        item = OrderItem.objects.create(
            reference=order, element=Item.objects.first())
        self.assertEqual(item.price, 0)
        with self.assertRaises(ValidationError):
            Invoice.objects.create(reference=item.reference)


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

#
#
#
#
#
