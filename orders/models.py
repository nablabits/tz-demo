"""Orders app let manage and control customers, orders and timing.

Its intended use is for business related to tailor made clothes.
"""

from django.db import models
from django.utils import timezone
from datetime import date


class Customer(models.Model):
    """Hold the data relative to Customers."""

    creation = models.DateTimeField('Alta', default=timezone.now)
    name = models.CharField('Nombre', max_length=64)
    address = models.CharField('Dirección', max_length=64, blank=True)
    city = models.CharField('Localidad', max_length=32)
    phone = models.IntegerField('Telefono')
    email = models.EmailField('Email', max_length=64, blank=True)
    CIF = models.CharField('CIF', max_length=10, blank=True)
    cp = models.IntegerField('CP')

    def __str__(self):
        """Get the name of the entry."""
        return self.name


class Order(models.Model):
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
        ('7', 'Delivered'),
        ('8', 'Cancelled')
    )

    inbox_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    ref_name = models.CharField('Referencia', max_length=32)
    delivery = models.DateField('Entrega prevista', blank=True)
    status = models.CharField(max_length=1, choices=STATUS, default='1')

    # Measures
    waist = models.DecimalField('Cintura', max_digits=5, decimal_places=2)
    chest = models.DecimalField('Pecho', max_digits=5, decimal_places=2)
    hip = models.DecimalField('Cadera', max_digits=5, decimal_places=2)
    lenght = models.DecimalField('Largo', max_digits=5, decimal_places=2)
    others = models.TextField('Observaciones', blank=True, null=True)

    # Pricing
    budget = models.DecimalField('Presupuesto', max_digits=7, decimal_places=2)
    prepaid = models.DecimalField('Pagado', max_digits=7, decimal_places=2)
    workshop = models.DecimalField('Horas de taller',
                                   max_digits=7, decimal_places=2, default=0)

    def __str__(self):
        """Object's representation."""
        return '%s %s %s' % (self.inbox_date.date(),
                             self.customer, self.ref_name)

    @property
    def overdue(self):
        """Set the overdue property."""
        return date.today() > self.delivery

    @property
    def pending(self):
        """Set the pending amount per order."""
        return self.prepaid - self.budget


class OrderItem(models.Model):
    """Each order can have one or several clothes."""

    ITEMS = (
        ('1', 'Falda'),
        ('2', 'Pantalón'),
        ('3', 'Camisa'),
        ('4', 'Pañuelo'),
        ('5', 'Delantal'),
        ('6', 'Corpiño'),
        ('7', 'Chaleco'),
        ('8', 'Gerriko'),
        ('9', 'Bata')
    )
    item = models.CharField('Item', max_length=1, choices=ITEMS, default='1')
    size = models.CharField('Talla', max_length=3, default='1')
    qty = models.IntegerField('Cantidad', default=1)
    description = models.CharField('descripcion', max_length=255, blank=True)
    reference = models.ForeignKey(Order, on_delete=models.CASCADE)


class Comment(models.Model):
    """Store the comments related to the orders."""

    creation = models.DateTimeField('Cuando', default=timezone.now)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    reference = models.ForeignKey(Order, on_delete=models.CASCADE)
    comment = models.TextField('Comentario')
    read = models.BooleanField('Leido', default=False)

    def __str__(self):
        """Object's representation."""
        name = ('El ' + str(self.creation.date()) +
                ', ' + str(self.user) + ' comentó en ' + str(self.reference))
        return name


class Timing(models.Model):
    """Timing let us track production times.

    Time should be given in hours.
    """

    ITEMS = OrderItem.ITEMS
    ITEM_CLASSES = (
        ('1', 'Standard'),
        ('2', 'Medium'),
        ('3', 'Premium')
    )
    ACTIVITIES = (
        ('1', 'Confección'),
        ('2', 'Corte'),
        ('3', 'Planchado')
    )
    item = models.CharField('Item', max_length=1, choices=ITEMS, default='1')
    item_class = models.CharField('Tipo Item',
                                  max_length=1,
                                  choices=ITEM_CLASSES,
                                  default='1')
    activity = models.CharField('Actividad',
                                max_length=1,
                                choices=ACTIVITIES,
                                default='1')
    qty = models.IntegerField('Cantidad', default=1)
    notes = models.TextField('Observaciones', blank=True, null=True)
    time = models.DecimalField('Tiempo (h)', max_digits=5, decimal_places=2)

    def __str__(self):
        """Object's representation."""
        return '{}x{}'.format(self.get_item_display(), self.qty)
