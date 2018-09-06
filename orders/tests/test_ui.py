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

    def test_create(self):
        """Try to create every element from every place."""
        # First of all, login
        self.selenium.get(self.live_server_url + '/')
        username_input = self.selenium.find_element_by_id("id_username")
        username_input.send_keys('regular')
        password_input = self.selenium.find_element_by_id("id_password")
        password_input.send_keys('test')
        self.selenium.find_element_by_id("submit").click()

        """Create customer from Customer List."""
        # Click the link on the sidebar
        driver = self.selenium.find_element
        driver(By.LINK_TEXT, 'Clientes').click()
        # click add customer
        driver(By.LINK_TEXT, 'Nuevo cliente').click()

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
        # Click the link on the sidebar
        driver(By.LINK_TEXT, 'Nuevo cliente').click()

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
