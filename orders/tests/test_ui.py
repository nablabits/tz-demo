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
        driver(By.ID, 'sidebar-new-customer').click()  # Click link on sidebar

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

        """Since we are in customer view, create a new order from there."""
        driver(By.ID, 'order-add').click()

        # Wait for the modal to load
        ref = wait.until(EC.visibility_of_element_located((By.NAME,
                                                           'ref_name')))
        ref.send_keys('Order1')
        driver(By.NAME, 'delivery').send_keys('2020-10-12')
        driver(By.NAME, 'waist').send_keys(10)
        driver(By.NAME, 'chest').send_keys(20)
        driver(By.NAME, 'hip').send_keys(30)
        driver(By.NAME, 'lenght').send_keys(40)
        driver(By.NAME, 'others').send_keys('Notes')
        driver(By.NAME, 'budget').send_keys(2000)
        driver(By.NAME, 'prepaid').send_keys(100)

        # submit
        driver(By.ID, 'submit').click()
        self.assertEquals(self.selenium.title, 'TrapuZarrak · Ver Pedido')

        # TODO: customer should be the last one created. Test It
        # h4/strong[contains(text(), 'Example2')]
        # xpath = "//div[@class='order_header']"
        xpath = "//div[@class='d-flex mt-4 order_header']/h4[1]/strong/following-sibling::text()[1]"
        # wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        self.assertTrue(driver(By.XPATH, xpath))
#
#
#
#
#
#
#
