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

    def tearDown(self):
        """Deactivate test settings."""
        self.selenium.quit()

    def test_create_customer(self):
        """Try to create new customers from sidebar and customer list."""
        self.selenium.get(self.live_server_url + '/')

        # First of all, login
        self.find(By.ID, 'id_username').send_keys('regular')
        self.find(By.ID, 'id_password').send_keys('test')
        self.find(By.ID, 'submit').click()

        # Create customer from Customer List.
        self.find(By.LINK_TEXT, 'Clientes').click()  # Click link on sidebar
        self.find(By.LINK_TEXT, 'Nuevo cliente').click()  # Click add customer

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'name'))
        name = self.wait.until(conditions)

        # Fill up the form
        name.send_keys('Customer from customer list')
        self.find(By.NAME, 'address').send_keys('Address')
        self.find(By.NAME, 'city').send_keys('Mungia')
        self.find(By.NAME, 'phone').send_keys(600600600)
        self.find(By.NAME, 'email').send_keys('jon@jonDoe.es')
        self.find(By.NAME, 'CIF').send_keys('1123444G')
        self.find(By.NAME, 'cp').send_keys(48100)

        # submit
        self.find(By.ID, 'submit').click()
        self.assertEquals(self.selenium.title, 'TrapuZarrak · Ver cliente')

        # Now, create customer from sidebar.
        self.find(By.ID, 'sidebar-new-customer').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'name'))
        name = self.wait.until(conditions)

        # Fill up the order_form_common
        name.send_keys('Customer from sidebar')
        self.find(By.NAME, 'address').send_keys('Address2')
        self.find(By.NAME, 'city').send_keys('Mungia otra vez')
        self.find(By.NAME, 'phone').send_keys(600500400)
        self.find(By.NAME, 'email').send_keys('jon2@jonDoe.es')
        self.find(By.NAME, 'CIF').send_keys('12345677F')
        self.find(By.NAME, 'cp').send_keys(48200)

        # submit
        self.find(By.ID, 'submit').click()
        self.assertEquals(self.selenium.title, 'TrapuZarrak · Ver cliente')

    def test_create_orders(self):
        """Try to create new orders from customer view & sidebar."""
        pk = Customer.objects.get(name='Default customer').pk
        url = self.live_server_url + '/customer_view/' + str(pk)
        self.selenium.get(url)

        # First of all, login
        self.find(By.ID, 'id_username').send_keys('regular')
        self.find(By.ID, 'id_password').send_keys('test')
        self.find(By.ID, 'submit').click()

        # Add an order
        self.find(By.ID, 'order-add').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'ref_name'))
        ref = self.wait.until(conditions)

        # Fill up the form
        ref.send_keys('Order from default customer')
        self.find(By.NAME, 'delivery').send_keys('2020-10-12')
        self.find(By.NAME, 'waist').send_keys(10)
        self.find(By.NAME, 'chest').send_keys(20)
        self.find(By.NAME, 'hip').send_keys(30)
        self.find(By.NAME, 'lenght').send_keys(40)
        self.find(By.NAME, 'others').send_keys('Notes')
        self.find(By.NAME, 'budget').send_keys(2000)
        self.find(By.NAME, 'prepaid').send_keys(100)

        # submit
        self.find(By.ID, 'submit').click()
        self.assertEquals(self.selenium.title, 'TrapuZarrak · Ver Pedido')

        # Customer should be the default.
        src = self.selenium.page_source
        self.assertTrue(re.search(r'Default customer', src))
        self.assertTrue(re.search(r'Order from default customer', src))

        # Now, create an order from sidebar.
        self.find(By.ID, 'sidebar-new-order').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.NAME, 'ref_name'))
        ref = self.wait.until(conditions)

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

        # submit
        self.find(By.ID, 'submit').click()
        self.assertEquals(self.selenium.title, 'TrapuZarrak · Ver Pedido')

        # Customer should be the default.
        src = self.selenium.page_source
        self.assertTrue(re.search(r'Default customer', src))
        self.assertTrue(re.search(r'Order from sidebar', src))

    def test_create_item(self):
        """Create item."""
        pk = Order.objects.get(ref_name='example').pk
        url = self.live_server_url + '/order/view/' + str(pk)
        self.selenium.get(url)

        # First of all, login
        self.find(By.ID, 'id_username').send_keys('regular')
        self.find(By.ID, 'id_password').send_keys('test')
        self.find(By.ID, 'submit').click()

        self.find(By.CLASS_NAME, 'js-add-item').click()

        # Wait for the modal to load
        conditions = EC.visibility_of_element_located((By.ID, 'id_item'))
        item = self.wait.until(conditions)
        Select(item).select_by_value('2')
        self.find(By.NAME, 'size').send_keys('XL')
        self.find(By.NAME, 'qty').send_keys(5)
        self.find(By.NAME, 'description').send_keys('Descripción')
        self.find(By.ID, 'submit').click()

#
#
#
#
#
#
