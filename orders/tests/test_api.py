from datetime import date

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from orders.models import (BankMovement, Customer, Expense, Invoice, Item,
                           Order, OrderItem, Timetable)


class ReadOnlyTests(APITestCase):

    def setUp(self):
        su = User.objects.create_user(
            username='su', password='test', is_staff=True)
        token = Token.objects.create(user=su)

        c = Customer.objects.create(name='Test Customer', phone=0, cp=0)
        order = Order.objects.create(
            customer=c, user=su, ref_name='Test order', delivery=date.today())
        item = Item.objects.create(name='Test item', fabrics=0, price=10)
        OrderItem.objects.create(
            element=item, reference=order, description='Test order item')

        Invoice.objects.create(reference=order, )

        # Login
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    def test_not_logged_in_users_should_get_a_401(self):
        """Ensure not allowed people can't perform API calls."""
        self.client.credentials()  # Get rid of auth
        endpoints = (
            'api-root', 'order-list', 'customer-list', 'item-list',
            'orderitem-list', 'invoice-list', 'expense-list',
            'bankmovement-list', 'timetable-list',
        )
        for endpoint in endpoints:
            resp = self.client.get(reverse(endpoint))
            self.assertEqual(resp.status_code, 401)

    def test_methods_different_than_get_are_not_allowed(self):
        """Ensure GET method is the only available."""
        resp = self.client.options(reverse('api-root'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp._headers['allow'], ('Allow', 'GET, HEAD, OPTIONS'))

    def test_api_root(self):
        """Test the correct content of the root view."""
        resp = self.client.get(reverse('api-root'))
        self.assertEqual(resp.status_code, 200)
        keys = ('customer', 'order', 'item', 'order_item', 'invoice',
                'expense', 'bank_movement', 'timetable', )
        for key in keys:
            self.assertTrue(key in resp.data.keys())

    def test_customer_api(self):
        """Test the correct content for customer API."""
        resp = self.client.get(reverse('customer-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['name'], 'Test Customer')

        # Finally ensure that all the fields are included
        fields = ('creation', 'name', 'address', 'city', 'phone', 'email',
                  'CIF', 'cp', 'notes', 'provider', )
        for field in fields:
            self.assertTrue(field in resp.data[0].keys())

    def test_order_api(self):
        """Test the correct content for order API."""
        resp = self.client.get(reverse('order-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['ref_name'], 'Test order')

        # Finally ensure that all the fields are included
        fields = (
            'inbox_date', 'user', 'customer', 'ref_name', 'delivery', 'status',
            'priority', 'waist', 'chest', 'hip', 'lenght', 'others', 'prepaid',
            )
        for field in fields:
            self.assertTrue(field in resp.data[0].keys())

    def test_item_api(self):
        """Test the correct content for item API."""
        resp = self.client.get(reverse('item-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['name'], 'Predeterminado')
        self.assertEqual(resp.data[1]['name'], 'Test item')

        # Finally ensure that all the fields are included
        fields = ('name', 'item_type', 'item_class', 'size', 'notes',
                  'fabrics', 'foreing', 'price', )
        for field in fields:
            self.assertTrue(field in resp.data[0].keys())

    def test_order_item_api(self):
        """Test the correct content for order item API."""
        resp = self.client.get(reverse('orderitem-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['description'], 'Test order item')

        # Finally ensure that all the fields are included
        fields = ('element', 'qty', 'description', 'reference', 'crop',
                  'sewing', 'iron', 'fit', 'stock', 'price', )
        for field in fields:
            self.assertTrue(field in resp.data[0].keys())

    def test_invoice_api(self):
        """Test the correct content for invoice API."""
        resp = self.client.get(reverse('invoice-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['amount'], '10.00')

        # Finally ensure that all the fields are included
        fields = (
            'reference', 'issued_on', 'invoice_no', 'amount', 'pay_method', )
        for field in fields:
            self.assertTrue(field in resp.data[0].keys())

    def test_expense_api(self):
        """Test the correct content for expense API."""
        p = Customer.objects.create(
            name='Provider', phone=0, cp=0, provider=True)
        Expense.objects.create(
            issuer=p, invoice_no='NA', issued_on=date.today(),
            concept='Concept', amount=10, )
        resp = self.client.get(reverse('expense-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['amount'], '10.00')

        # Finally ensure that all the fields are included
        fields = ('creation', 'issuer', 'issued_on', 'invoice_no', 'amount',
                  'concept', 'pay_method', 'in_b', 'notes')
        for field in fields:
            self.assertTrue(field in resp.data[0].keys())

    def test_bank_movement_api(self):
        """Test the correct content for bank_movement API."""
        BankMovement.objects.create(
            action_date=date.today(), amount=100, notes='Notes', )
        resp = self.client.get(reverse('bankmovement-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['amount'], '100.00')

        # Finally ensure that all the fields are included
        for field in ('action_date', 'amount', 'notes', ):
            self.assertTrue(field in resp.data[0].keys())

    def test_timetable_api(self):
        """Test the correct content for timetable API."""
        user = User.objects.first()
        Timetable.objects.create(user=user)
        resp = self.client.get(reverse('timetable-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['user'], user.pk)

        # Finally ensure that all the fields are included
        for field in ('user', 'start', 'end', 'hours', ):
            self.assertTrue(field in resp.data[0].keys())




#
#
#
#
#
#
#
