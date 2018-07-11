from django.test import TestCase
from orders.models import Customer

class CustomerModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        Customer.objects.create(name='Customer Test',
                                address='This computer',
                                city='No city',
                                phone='666666666',
                                email='cutomer@example.com',
                                CIF='5555G',
                                cp='48100')

    def test_customer_creation(self):
        customer = Customer.objects.get(pk=1)
        self.assertTrue(isinstance(customer, Customer))
