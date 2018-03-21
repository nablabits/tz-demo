from django.db import models
from django.utils import timezone


class Customer(models.Model):
    """Hold the data relative to Customers."""

    creation = models.DateTimeField('Alta', default=timezone.now)
    name = models.CharField('Nombre', max_length=64)
    address = models.CharField('Dirección', max_length=64, blank=True)
    city = models.CharField('Localidad', max_length=32)
<<<<<<< HEAD
    phone = models.IntegerField('Telefono')
    email = models.EmailField('Eposta', max_length=64, blank=True)
    CIF = models.CharField('CIF', max_length=10, blank=True)
=======
    phone = models.IntegerField('Telefonoa')
    email = models.EmailField('Eposta', max_length=64, blank=True)
    CIF = models.CharField('CIF', max_length=10)
>>>>>>> 33c807aa14257831d7e133ac1069325e1d2dfb2c
    cp = models.IntegerField('CP')
    notif = models.BooleanField(default=False)

    def __str__(self):
        """Get the name of the entry."""
        return self.name


class Orders(models.Model):
    """The main object, store the order info."""

    STATUS = (
        # Shop
        ('1', 'Inboxed'),
        # WorkShop
        ('2', 'Waiting'),
        ('3', 'preparing'),
        ('4', 'performing'),
        ('5', 'WorkShop'),
        # Shop
        ('6', 'Outbox'),
        ('7', 'Delivered')
    )

    inbox_date = models.DateTimeField('Fecha de entrada',
                                      default=timezone.now)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
<<<<<<< HEAD
    ref_name = models.CharField(max_length=32)
    delivery = models.DateField(blank=True, default=timezone.now)
    status = models.CharField(max_length=1, choices=STATUS, default='1')

    # Measures
    waist = models.DecimalField(max_digits=5, decimal_places=2)
    chest = models.DecimalField(max_digits=5, decimal_places=2)
    hip = models.DecimalField(max_digits=5, decimal_places=2)
    lenght = models.DecimalField(max_digits=5, decimal_places=2)
    others = models.TextField(blank=True, null=True)

    # Pricing
    budget = models.DecimalField(max_digits=7, decimal_places=2)
    prepaid = models.DecimalField(max_digits=7, decimal_places=2)
    workshop = models.DecimalField('Horas de taller',
                                   max_digits=7, decimal_places=2, default=0)
=======
    delivery = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS)

    # Measures
    waist = models.DecimalField(max_digits=3, decimal_places=2)
    chest = models.DecimalField(max_digits=3, decimal_places=2)
    hip = models.DecimalField(max_digits=3, decimal_places=2)
    lenght = models.DecimalField(max_digits=3, decimal_places=2)
    others = models.TextField(blank=True)

    # Pricing
    budget = models.DecimalField(max_digits=5, decimal_places=2)
    prepaid = models.DecimalField(max_digits=5, decimal_places=2)
    workshop = models.DecimalField(max_digits=3, decimal_places=2)
>>>>>>> 33c807aa14257831d7e133ac1069325e1d2dfb2c


class Comments(models.Model):
    """Keep the comments by order & user."""

    pass
