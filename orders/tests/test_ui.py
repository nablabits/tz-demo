from django.contrib.staticfiles.testing import LiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver
from django.contrib.auth.models import User


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

    def test_login(self):
        """Test login into the app."""
        self.selenium.get(self.live_server_url + '/')
        username_input = self.selenium.find_element_by_id("id_username")
        username_input.send_keys('regular')
        password_input = self.selenium.find_element_by_id("id_password")
        password_input.send_keys('test')
        self.selenium.find_element_by_id("submit").click()
