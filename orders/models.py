"""Orders app let manage and control customers, orders and timing.

Its intended use is for business related to tailor made clothes.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import (ObjectDoesNotExist, ValidationError, )
from .utils import WeekColor
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

    def clean(self):
        """Avoid duplicate customers."""
        exists = Customer.objects.filter(name=self.name)
        if exists:
            for customer in exists:
                duplicated = (customer.address == self.address and
                              customer.city == self.city and
                              customer.phone == self.phone and
                              customer.email == self.email and
                              customer.CIF == self.CIF and
                              customer.cp == self.cp and
                              customer.notes == self.notes)
                if duplicated:
                    raise ValidationError({'name': _('The customer already ' +
                                                     'exists in the db')})


class Order(models.Model):
    """The main object, store the order info."""

    STATUS = (
        # Shop
        ('1', 'Recibido'),
        # WorkShop
        ('2', 'En cola'),
        ('3', 'Corte'),
        ('4', 'Confección'),
        ('5', 'Remate'),
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

    def clean(self):
        """Avoid duplicate orders."""
        exists = Order.objects.filter(ref_name=self.ref_name)
        if exists:
            for order in exists:
                diff = self.inbox_date - order.inbox_date
                duplicated = (diff.seconds < 120 and
                              self.customer == order.customer and
                              self.delivery == order.delivery and
                              self.status == order.status and
                              self.priority == order.priority and
                              self.waist == order.waist and
                              self.chest == order.chest and
                              self.hip == order.hip and
                              self.lenght == order.lenght and
                              self.others == order.others and
                              self.budget == order.budget and
                              self.prepaid == order.prepaid
                              )
                if duplicated:
                    raise ValidationError(_('The order already ' +
                                            'exists in the db'))

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
        """Determine the next status."""
        return str(int(self.status)+1)

    @property
    def color(self):
        """Add a color depending the delivery date."""
        return WeekColor(self.delivery).get()

    @property
    def progress(self):
        """Return the status in percentage."""
        if self.status in ('6', '7', '8'):
            return 100
        elif self.status == '1':
            return 0
        else:
            return round((int(self.status)-2) * 100 / 4, 0)

    @property
    def times(self):
        """Return the total time tracked and the total trackeable time."""
        tracked = 0
        items = self.orderitem_set.all()
        for item in items:
            tracked = tracked + item.time_quality
        return (tracked, len(items) * 3)


class Item(models.Model):
    """Hold the different types of items (clothes) and the fabrics needed."""

    name = models.CharField('Nombre', max_length=64)
    item_type = models.CharField('Tipo de prenda',
                                 max_length=2,
                                 choices=settings.ITEM_TYPE,
                                 default='0')
    item_class = models.CharField('Acabado',
                                  max_length=1,
                                  choices=settings.ITEM_CLASSES,
                                  default='1')
    size = models.CharField('Talla', max_length=6, default='1')
    notes = models.TextField('Observaciones', blank=True, null=True)
    fabrics = models.DecimalField('Tela (M)', max_digits=5, decimal_places=2)
    foreing = models.BooleanField('Externo', default=False)

    def __str__(self):
        """Object's representation."""
        return '{} {} {}-{}'.format(self.get_item_type_display(), self.name,
                                    self.item_class, self.size)

    def clean(self):
        """Clean up the model to avoid duplicate items."""
        exists = Item.objects.filter(name=self.name)
        if exists:
            for item in exists:
                duplicated = (self.item_class == item.item_class and
                              self.item_class == item.item_class and
                              self.size == item.size and
                              self.fabrics == item.fabrics
                              )
                if duplicated:
                    raise ValidationError({'name': _('Items cannot have the ' +
                                                     'same name the same ' +
                                                     'size and the same class'
                                                     )})
                    break

    def save(self, *args, **kwargs):
        """Override save method.

        Item named Predeterminado is reserved, so raise an exception. Avoid,
        also, duplicate items
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

    # Element field should be renamed after backup all the previous fields.
    element = models.ForeignKey(Item, blank=True, on_delete=models.CASCADE)

    qty = models.IntegerField('Cantidad', default=1)
    description = models.CharField('descripcion', max_length=255, blank=True)
    reference = models.ForeignKey(Order, on_delete=models.CASCADE)

    # Timing stuff now goes here
    crop = models.DurationField('Corte', default=timedelta(0))
    sewing = models.DurationField('Confeccion', default=timedelta(0))
    iron = models.DurationField('Planchado', default=timedelta(0))

    # store if the item is an element that must be fitted
    fit = models.BooleanField('Arreglo', default=False)

    def save(self, *args, **kwargs):
        """Override the save method."""
        try:
            default = Item.objects.get(name='Predeterminado')
        except ObjectDoesNotExist:
            default = Item.objects.create(name='Predeterminado',
                                          item_type='0',
                                          item_class='0',
                                          size=0,
                                          fabrics=0)

        try:
            self.element
        except ObjectDoesNotExist:
            self.element = default

        super().save(*args, **kwargs)

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
#
#
#
#
