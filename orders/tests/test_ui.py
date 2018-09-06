from django.contrib.staticfiles.testing import LiveServerTestCase
from django.test import Client
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.common.by import By
from django.contrib.auth.models import User


class LoginTest(LiveServerTestCase):
    """Test the proper login.

    Since in other views login is set on setUpClass (because is required for
    all of them), test the login here alone.
    """

    @classmethod
    def setUpClass(cls):
        """Set Up the tests in a permanent way."""
        super().setUpClass()
        profile = FirefoxProfile()
        cls.selenium = WebDriver(firefox_profile=profile)
        cls.selenium.implicitly_wait(10)
        regular = User.objects.create_user(username='regular', password='test')
        regular.save()

    @classmethod
    def tearDownClass(cls):
        """Deactivate test settings."""
        cls.selenium.quit()
        super().tearDownClass()

    def test_login(self):
        """Test login into the app."""
        self.selenium.get(self.live_server_url + '/')
        username_input = self.selenium.find_element_by_id("id_username")
        username_input.send_keys('regular')
        password_input = self.selenium.find_element_by_id("id_password")
        password_input.send_keys('test')
        self.selenium.find_element_by_id("submit").click()


class CreationTest(LiveServerTestCase):
    """Test the proper creation of anyone of the models."""

    @classmethod
    def setUpClass(cls):
        """Set Up the tests in a permanent way."""
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        regular = User.objects.create_user(username='regular', password='test')
        regular.save()

    @classmethod
    def tearDownClass(cls):
        """Deactivate test settings."""
        cls.selenium.quit()
        super().tearDownClass()

    def test_create_customer_from_sidebar(self):
        """Try to create a new customer from sidebar."""
        # First of all, login
        self.selenium.get(self.live_server_url + '/')
        username_input = self.selenium.find_element_by_id("id_username")
        username_input.send_keys('regular')
        password_input = self.selenium.find_element_by_id("id_password")
        password_input.send_keys('test')
        self.selenium.find_element_by_id("submit").click()

        # Find the link on sidebar
        driver = self.selenium.find_element
        driver(By.LINK_TEXT, 'Clientes').click()
        # click add customer
        driver(By.CLASS_NAME, 'js-customer-add').click()
#
#
#
#
#
#
#
