"""Test the user interface using Selenium."""

from django.contrib.staticfiles.testing import LiveServerTestCase
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from django.contrib.auth.models import User
from orders.models import Customer, Order
from datetime import date
from random import randint
import re


class CreationTest(LiveServerTestCase):
    """Test the proper creation of anyone of the models."""

    def setUp(self):
        """Set Up the initial conditions."""
        profile = FirefoxProfile()
        self.selenium = WebDriver(firefox_profile=profile)
        self.selenium.implicitly_wait(10)
        self.find = self.selenium.find_element
        self.wait = WebDriverWait(self.selenium, 10)

        # Create an initial user
        regular = User.objects.create_user(username='regular', password='test')
        regular.save()

        # Create a default customer
        Customer.objects.create(name='Default customer',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                cp='48100')

        # Create an order
        customer = Customer.objects.get(name='Default customer')
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

        # Finally login
        self.selenium.get(self.live_server_url + '/')
        self.find(By.ID, 'id_username').send_keys('regular')
        self.find(By.ID, 'id_password').send_keys('test')
        self.find(By.ID, 'submit').click()

    def tearDown(self):
        """Deactivate test settings."""
        self.selenium.quit()

    def test_create_customer(self):
        """Try to create new customers from sidebar and customer list."""
        # Create customer from Customer List.
        self.find(By.LINK_TEXT, 'Clientes').click()  # Click link on sidebar
        self.find(By.LINK_TEXT, 'Nuevo cliente').click()  # Click add customer

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'name'))
        name = self.wait.until(conditions)

        # Fill up the form & submit
        name.send_keys('Customer from customer list')
        self.find(By.NAME, 'address').send_keys('Address')
        self.find(By.NAME, 'city').send_keys('Mungia')
        self.find(By.NAME, 'phone').send_keys(600600600)
        self.find(By.NAME, 'email').send_keys('jon@jonDoe.es')
        self.find(By.NAME, 'CIF').send_keys('1123444G')
        self.find(By.NAME, 'cp').send_keys(48100)
        self.find(By.ID, 'submit').click()

        # check return to customer view
        customer = Customer.objects.get(name='Customer from customer list')
        url = self.live_server_url + '/customer_view/' + str(customer.pk)
        self.assertEqual(self.selenium.current_url, url)

        # Now, create customer from sidebar.
        self.find(By.ID, 'sidebar-new-customer').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'name'))
        name = self.wait.until(conditions)

        # Fill up the form & submit
        name.send_keys('Customer from sidebar')
        self.find(By.NAME, 'address').send_keys('Address2')
        self.find(By.NAME, 'city').send_keys('Mungia otra vez')
        self.find(By.NAME, 'phone').send_keys(600500400)
        self.find(By.NAME, 'email').send_keys('jon2@jonDoe.es')
        self.find(By.NAME, 'CIF').send_keys('12345677F')
        self.find(By.NAME, 'cp').send_keys(48200)
        self.find(By.ID, 'submit').click()

        # check return to customer view
        customer = Customer.objects.get(name='Customer from sidebar')
        url = self.live_server_url + '/customer_view/' + str(customer.pk)
        self.assertEqual(self.selenium.current_url, url)

    def test_create_orders(self):
        """Try to create new orders from customer view & sidebar."""
        pk = Customer.objects.get(name='Default customer').pk
        url = self.live_server_url + '/customer_view/' + str(pk)
        self.selenium.get(url)

        # Add an order
        self.find(By.ID, 'order-add').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'ref_name'))
        ref = self.wait.until(conditions)

        # Fill up the form & submit
        ref.send_keys('Order from default customer')
        self.find(By.NAME, 'delivery').send_keys('2020-10-12')
        self.find(By.NAME, 'waist').send_keys(10)
        self.find(By.NAME, 'chest').send_keys(20)
        self.find(By.NAME, 'hip').send_keys(30)
        self.find(By.NAME, 'lenght').send_keys(40)
        self.find(By.NAME, 'others').send_keys('Notes')
        self.find(By.NAME, 'budget').send_keys(2000)
        self.find(By.NAME, 'prepaid').send_keys(100)
        self.find(By.ID, 'submit').click()

        # check return to order view
        order = Order.objects.get(ref_name='Order from default customer')
        url = self.live_server_url + '/order/view/' + str(order.pk)
        self.assertEqual(self.selenium.current_url, url)

        # Customer should be the default.
        src = self.selenium.page_source
        self.assertTrue(re.search(r'Default customer', src))
        self.assertTrue(re.search(r'Order from default customer', src))

        # Now, create an order from sidebar.
        self.find(By.ID, 'sidebar-new-order').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'ref_name'))
        ref = self.wait.until(conditions)

        # Fill up the form & submit
        ref.send_keys('Order from sidebar')
        customer = Select(self.find(By.NAME, 'customer'))
        customer.select_by_value(str(pk))
        self.find(By.NAME, 'delivery').send_keys('2020-10-12')
        self.find(By.NAME, 'waist').send_keys(10)
        self.find(By.NAME, 'chest').send_keys(20)
        self.find(By.NAME, 'hip').send_keys(30)
        self.find(By.NAME, 'lenght').send_keys(40)
        self.find(By.NAME, 'others').send_keys('Notes')
        self.find(By.NAME, 'budget').send_keys(2000)
        self.find(By.NAME, 'prepaid').send_keys(100)
        self.find(By.ID, 'submit').click()

        # check return to order view
        order = Order.objects.get(ref_name='Order from sidebar')
        url = self.live_server_url + '/order/view/' + str(order.pk)
        self.assertEqual(self.selenium.current_url, url)

        # Customer should be the default.
        src = self.selenium.page_source
        self.assertTrue(re.search(r'Default customer', src))
        self.assertTrue(re.search(r'Order from sidebar', src))

    def test_create_item_and_comment(self):
        """Create item and comment."""
        pk = Order.objects.get(ref_name='example').pk
        url = self.live_server_url + '/order/view/' + str(pk)
        self.selenium.get(url)

        # add item
        self.find(By.CLASS_NAME, 'js-add-item').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.ID, 'id_item'))
        item = self.wait.until(conditions)

        # Try to select all items on the dropdown
        for value in range(2, 9):
            Select(item).select_by_value(str(value))

        # Fill up the form & submit
        self.find(By.NAME, 'size').send_keys('XL')
        self.find(By.NAME, 'qty').send_keys(5)
        self.find(By.NAME, 'description').send_keys('Descripción')
        self.find(By.ID, 'submit').click()

        self.assertEqual(self.selenium.current_url, url)

        # Add comment
        self.selenium.get(url)  # reload page to avoid modal backdrop
        self.find(By.CLASS_NAME, 'js-order-add-comment').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.ID, 'id_comment'))
        comment = self.wait.until(conditions)

        # Fill up the form
        comment.send_keys('XL')

        self.assertEqual(self.selenium.current_url, url)

    def test_create_time(self):
        """Test create time from sidebar & from order."""
        self.find(By.ID, 'sidebar-new-time').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'item'))
        item = self.wait.until(conditions)

        # Try to select all items on the dropdown
        for value in range(2, 9):
            Select(item).select_by_value(str(value))

        # Try to select all item classes on the dropdown
        item_class = self.find(By.NAME, 'item_class')
        for value in range(2, 4):
            Select(item_class).select_by_value(str(value))

        # Try to select all activities on the dropdown
        activity = self.find(By.NAME, 'activity')
        for value in range(2, 4):
            Select(activity).select_by_value(str(value))

        # Fill up the form & submit
        self.find(By.NAME, 'qty').send_keys(5)
        self.find(By.NAME, 'time').send_keys('5.5')
        self.find(By.NAME, 'notes').send_keys('Descripción')
        self.find(By.ID, 'submit').click()

        self.assertEqual(self.selenium.current_url, self.live_server_url + '/')

        # Now, try to create from order
        pk = Order.objects.get(ref_name='example').pk
        url = self.live_server_url + '/order/view/' + str(pk)
        self.selenium.get(url)

        # Add time
        self.find(By.ID, 'time-add').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'item'))
        item = self.wait.until(conditions)

        # Try to select all items on the dropdown
        for value in range(2, 9):
            Select(item).select_by_value(str(value))

        # Try to select all item classes on the dropdown
        item_class = self.find(By.NAME, 'item_class')
        for value in range(2, 4):
            Select(item_class).select_by_value(str(value))

        # Try to select all activities on the dropdown
        activity = self.find(By.NAME, 'activity')
        for value in range(2, 4):
            Select(activity).select_by_value(str(value))

        # Fill up the form
        self.find(By.NAME, 'qty').send_keys(5)
        self.find(By.NAME, 'time').send_keys('5.5')
        self.find(By.NAME, 'notes').send_keys('Descripción')
        self.find(By.ID, 'submit').click()

        self.assertEqual(self.selenium.current_url, self.live_server_url + '/')


class EditionTest(LiveServerTestCase):
    """Test the correct editions."""

    def setUp(self):
        profile = FirefoxProfile()
        self.selenium = WebDriver(firefox_profile=profile)
        self.selenium.implicitly_wait(10)
        self.find = self.selenium.find_element
        self.wait = WebDriverWait(self.selenium, 10)

        # Create an initial user
        regular = User.objects.create_user(username='regular', password='test')
        regular.save()

        # Create a default customer
        Customer.objects.create(name='Default customer',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='customer@example.com',
                                CIF='5555G',
                                cp='48100')

        # Create an order
        customer = Customer.objects.get(name='Default customer')
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

        # Login
        self.selenium.get(self.live_server_url + '/')
        self.find(By.ID, 'id_username').send_keys('regular')
        self.find(By.ID, 'id_password').send_keys('test')
        self.find(By.ID, 'submit').click()

    def tearDown(self):
        """Deactivate test settings."""
        self.selenium.quit()

    def test_edit_customer(self):
        """Test the correct edition of customers."""
        pk = Customer.objects.get(name='Default customer').pk
        url = self.live_server_url + '/customer_view/' + str(pk)
        self.selenium.get(url)

        # Now, Edit
        self.find(By.ID, 'customer-edit').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'name'))
        name = self.wait.until(conditions)

        # Clear out the form
        name.clear()
        self.find(By.NAME, 'address').clear()
        self.find(By.NAME, 'city').clear()
        self.find(By.NAME, 'phone').clear()
        self.find(By.NAME, 'email').clear()
        self.find(By.NAME, 'CIF').clear()
        self.find(By.NAME, 'cp').clear()

        # and fill up
        name.send_keys('Edited Customer')
        self.find(By.NAME, 'address').send_keys('Edited address')
        self.find(By.NAME, 'city').send_keys('Edited city')
        self.find(By.NAME, 'phone').send_keys(900900900)
        self.find(By.NAME, 'email').send_keys('edited@mail.es')
        self.find(By.NAME, 'CIF').send_keys('edited')
        self.find(By.NAME, 'cp').send_keys(10300)

        # submit
        self.find(By.ID, 'submit').click()
        self.assertEquals(self.selenium.title, 'TrapuZarrak · Ver cliente')

    def test_edit_order(self):
        """Test the proper edition of orders."""
        pk = Order.objects.get(ref_name='example').pk
        url = self.live_server_url + '/order/view/' + str(pk)
        self.selenium.get(url)

        self.find(By.ID, 'order-edit').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'ref_name'))
        ref = self.wait.until(conditions)

        # Clear out the form
        ref.clear()
        self.find(By.NAME, 'delivery').clear()
        self.find(By.NAME, 'waist').clear()
        self.find(By.NAME, 'chest').clear()
        self.find(By.NAME, 'hip').clear()
        self.find(By.NAME, 'lenght').clear()
        self.find(By.NAME, 'others').clear()
        self.find(By.NAME, 'budget').clear()
        self.find(By.NAME, 'prepaid').clear()

        # and fill up
        ref.send_keys('Order from default customer')
        self.find(By.NAME, 'delivery').send_keys('2020-01-01')
        self.find(By.NAME, 'waist').send_keys(20)
        self.find(By.NAME, 'chest').send_keys(30)
        self.find(By.NAME, 'hip').send_keys(40)
        self.find(By.NAME, 'lenght').send_keys(50)
        self.find(By.NAME, 'others').send_keys('Edited notes')
        self.find(By.NAME, 'budget').send_keys(5000)
        self.find(By.NAME, 'prepaid').send_keys(2000)

        # submit
        self.find(By.ID, 'submit').click()
        self.assertEquals(self.selenium.title, 'TrapuZarrak · Ver Pedido')
        url = self.live_server_url + '/order/view/' + str(pk)
        self.assertEqual(self.selenium.current_url, url)

    def test_edit_status(self):
        """Test the proper status edit of orders."""
        pk = Order.objects.get(ref_name='example').pk
        url = self.live_server_url + '/order/view/' + str(pk)
        self.selenium.get(url)

        self.find(By.ID, 'status-waiting').click()
        order = Order.objects.get(pk=pk)
        self.assertEqual(order.status, '2')

        self.find(By.ID, 'status-preparing').click()
        order = Order.objects.get(pk=pk)
        self.assertEqual(order.status, '3')

        self.find(By.ID, 'status-performing').click()
        order = Order.objects.get(pk=pk)
        self.assertEqual(order.status, '4')

        self.find(By.ID, 'status-workshop').click()
        order = Order.objects.get(pk=pk)
        self.assertEqual(order.status, '5')

        self.find(By.ID, 'status-outbox').click()
        order = Order.objects.get(pk=pk)
        self.assertEqual(order.status, '6')

        # deliver order without paying it
        self.find(By.ID, 'status-delivered').click()
        conditions = EC.visibility_of_element_located((By.ID, 'id_prepaid'))
        self.wait.until(conditions)
        self.find(By.ID, 'submit').click()
        order = Order.objects.get(pk=pk)
        self.assertEqual(order.status, '7')

        # Pay it afterwards
        self.find(By.ID, 'status-close').click()
        conditions = EC.visibility_of_element_located((By.ID, 'submit'))
        self.wait.until(conditions).click()
        order = Order.objects.get(pk=pk)
        self.assertEqual(order.budget, order.prepaid)

        # reopen it (still paid)
        order.prepaid = 0
        order.save()  # Undo payment
        self.selenium.get(url)  # reload page # DEBUG: get rid of
        self.find(By.ID, 'status-reopen').click()

        conditions = EC.visibility_of_element_located((By.ID, 'status-close'))
        self.wait.until(conditions).click()
        conditions = EC.visibility_of_element_located((By.ID, 'submit'))
        submit = self.wait.until(conditions)
        submit.click()
        order = Order.objects.get(pk=pk)
        self.assertEqual(order.budget, order.prepaid)
#
#
#
#
#
#
