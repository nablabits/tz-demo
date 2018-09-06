from django.contrib.staticfiles.testing import LiveServerTestCase
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from django.contrib.auth.models import User


class CreationTest(LiveServerTestCase):
    """Test the proper creation of anyone of the models."""

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

    def test_create_customer(self):
        """Try to create new customers."""
        self.selenium.get(self.live_server_url + '/')
        driver = self.selenium.find_element

        # First of all, login
        driver(By.ID, 'id_username').send_keys('regular')
        driver(By.ID, 'id_password').send_keys('test')
        driver(By.ID, 'submit').click()

        """Create customer from Customer List."""
        driver(By.LINK_TEXT, 'Clientes').click()  # Click link on sidebar
        driver(By.LINK_TEXT, 'Nuevo cliente').click()  # Click add customer

        # Wait for the modal to load
        wait = WebDriverWait(self.selenium, 10)
        name = wait.until(EC.visibility_of_element_located((By.NAME, 'name')))

        # Fill up the form
        name.send_keys('Example')
        driver(By.NAME, 'address').send_keys('Address')
        driver(By.NAME, 'city').send_keys('Mungia')
        driver(By.NAME, 'phone').send_keys(600600600)
        driver(By.NAME, 'email').send_keys('jon@jonDoe.es')
        driver(By.NAME, 'CIF').send_keys('1123444G')
        driver(By.NAME, 'cp').send_keys(48100)

        # submit
        driver(By.ID, 'submit').click()
        self.assertEquals(self.selenium.title, 'TrapuZarrak · Ver cliente')

        """Create customer from sidebar."""
        driver(By.LINK_TEXT, 'Nuevo cliente').click()  # Click link on sidebar

        # Wait for the modal to load
        wait = WebDriverWait(self.selenium, 10)
        name = wait.until(EC.visibility_of_element_located((By.NAME, 'name')))

        # Fill up the form
        name.send_keys('Example2')
        driver(By.NAME, 'address').send_keys('Address2')
        driver(By.NAME, 'city').send_keys('Mungia otra vez')
        driver(By.NAME, 'phone').send_keys(600500400)
        driver(By.NAME, 'email').send_keys('jon2@jonDoe.es')
        driver(By.NAME, 'CIF').send_keys('12345677F')
        driver(By.NAME, 'cp').send_keys(48200)

        # submit
        driver(By.ID, 'submit').click()
        self.assertEquals(self.selenium.title, 'TrapuZarrak · Ver cliente')
#
#
#
#
#
#
#
