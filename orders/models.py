"""Orders app let manage and control customers, orders and timing.

Its intended use is for business related to tailor made clothes.
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from .utils import TimeLenght
from . import settings
from datetime import date, timedelta


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
    notes = models.TextField('Observaciones', blank=True, null=True)

    def __str__(self):
        """Get the name of the entry."""
        return self.name


class Order(models.Model):
    """The main object, store the order info."""

    STATUS = (
        # Shop
        ('1', 'Recibido'),
        # WorkShop
        ('2', 'En cola'),
        ('3', 'Preparando'),
        ('4', 'En proceso'),
        ('5', 'Acabado'),
        # Shop
        ('6', 'En espera'),
        ('7', 'Entregado'),
        ('8', 'Cancelado')
    )

    PRIORITY = (
        ('1', 'Alta'),
        ('2', 'Normal'),
        ('3', 'Baja')
    )

    inbox_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    ref_name = models.CharField('Referencia', max_length=32)
    delivery = models.DateField('Entrega prevista', blank=True)
    status = models.CharField(max_length=1, choices=STATUS, default='1')
    priority = models.CharField('Prioridad', max_length=1, choices=PRIORITY,
                                default='2')

    # Measures
    waist = models.DecimalField('Cintura', max_digits=5, decimal_places=2,
                                default=0)
    chest = models.DecimalField('Pecho', max_digits=5, decimal_places=2,
                                default=0)
    hip = models.DecimalField('Cadera', max_digits=5, decimal_places=2,
                              default=0)
    lenght = models.DecimalField('Largo', max_digits=5, decimal_places=2,
                                 default=0)
    others = models.TextField('Observaciones', blank=True, null=True)

    # Pricing
    budget = models.DecimalField('Presupuesto', max_digits=7, decimal_places=2)
    prepaid = models.DecimalField('Pagado', max_digits=7, decimal_places=2)

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

    @property
    def prev_status(self):
        """Determine the previous status."""
        return str(int(self.status)-1)

    @property
    def next_status(self):
        """Determine the previous status."""
        return str(int(self.status)+1)


class Item(models.Model):
    """Hold the different types of items (clothes) and the fabrics needed."""

    name = models.CharField('Nombre', max_length=64)
    item_type = models.CharField('Tipo de prenda',
                                 max_length=2,
                                 choices=settings.ITEM_TYPE,
                                 default=0)
    item_class = models.CharField('Acabado',
                                  max_length=1,
                                  choices=settings.ITEM_CLASSES,
                                  default='1')
    size = models.CharField('Talla', max_length=3, default='1')
    notes = models.TextField('Observaciones', blank=True, null=True)
    fabrics = models.DecimalField('Tela (M)', max_digits=5, decimal_places=2)

    def __str__(self):
        """Object's representation."""
        return '{} {} {}-{}'.format(self.get_item_type_display(), self.name,
                                    self.item_class, self.size)

    def save(self, *args, **kwargs):
        """Override save method.

        Item named Predeterminado is reserved, so raise an exception.
        """
        if self.name == 'Predeterminado':
            try:
                Item.objects.get(name='Predeterminado')
            except ObjectDoesNotExist:
                super().save(*args, **kwargs)
            else:
                raise ValidationError('\'Predeterminado\' name is reserved')
        else:
            super().save(*args, **kwargs)

    class Meta:
        ordering = ('name',)


class OrderItem(models.Model):
    """Each order can have one or several clothes."""

    # Items are now stored in settings, but keep'em until backup.
    ITEMS = (
        ('1', 'Falda'),
        ('2', 'Pantalón'),
        ('3', 'Camisa'),
        ('4', 'Pañuelo'),
        ('5', 'Delantal'),
        ('6', 'Corpiño'),
        ('7', 'Chaleco'),
        ('8', 'Gerriko'),
        ('9', 'Bata'),
        ('10', 'Pololo'),
        ('11', 'Azpikogona'),
        ('12', 'Traje de niña'),
    )
    # Item & size will be deprecated, keep them until backup
    item = models.CharField('Prenda', max_length=2, choices=ITEMS, default='1')
    size = models.CharField('Talla', max_length=3, default='1')

    # Element field should be renamed after backup all the previous fields.
    # on deploying disable default value and add blank=True

    # DEBUG: Uncomment after deploy
    default = Item.objects.get(name='Predeterminado')
    element = models.ForeignKey(Item, default=default.pk,
    #                             on_delete=models.CASCADE)

    # DEBUG: get rid of this line after deploy
    # element = models.ForeignKey(Item, blank=True, on_delete=models.CASCADE)

    qty = models.IntegerField('Cantidad', default=1)
    description = models.CharField('descripcion', max_length=255, blank=True)
    reference = models.ForeignKey(Order, on_delete=models.CASCADE)

    # Timing stuff now goes here
    crop = models.DurationField('Corte', default=timedelta(0))
    sewing = models.DurationField('Confeccion', default=timedelta(0))
    iron = models.DurationField('Planchado', default=timedelta(0))

    @property
    def time_quality(self):
        """Display a message depending on how much time has been tracked."""
        rate = 0
        if self.crop:
            rate += 1
        if self.sewing:
            rate += 1
        if self.iron:
            rate += 1

        return rate

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

    Time should be given in hours. This model is deprecated since timesnow are
    stored per OrderItem.
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
    item = models.CharField('Prenda', max_length=2, choices=ITEMS, default='1')
    item_class = models.CharField('Tipo Prenda',
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
    reference = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True)

    def save(self, *args, **kwargs):
        """Override the save method.

        If no order is given try to pick up the last one.
        """
        order = Order.objects.latest('inbox_date')
        try:
            self.reference
        except ObjectDoesNotExist:
            self.reference = order
        super().save(*args, **kwargs)

    def __str__(self):
        """Object's representation."""
        return '{}x{}'.format(self.get_item_display(), self.qty)

    def output(self):
        """Represent times by its str converted form H:MM."""
        return TimeLenght(float(self.time)).convert()


#
#
#
#
