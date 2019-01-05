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
    budget = models.DecimalField(
        'Presupuesto', max_digits=7, decimal_places=2, blank=True, null=True)
    prepaid = models.DecimalField(
        'Prepago', max_digits=7, decimal_places=2, blank=True, null=True,
        default=0)

    def __str__(self):
        """Object's representation."""
        return '%s %s %s' % (self.inbox_date.date(),
                             self.customer, self.ref_name)

    @property
    def overdue(self):
        """Set the overdue property."""
        return date.today() > self.delivery

    @property
    def total(self):
        """Get the total amount for the invoice."""
        items = OrderItem.objects.filter(reference=self)
        total = items.aggregate(
            total=models.Sum(models.F('qty') * models.F('price'),
                             output_field=models.DecimalField()))
        if total['total'] is None:
            return 0
        else:
            return total['total']

    @property
    def pending(self):
        """Set the pending amount per order."""
        return self.prepaid - self.total

    @property
    def invoiced(self):
        """Determine if the order is already invoiced.

        This setting determines if order appears as pending. Invoiced orders
        don't appear as pending although their pending property is > 0, this
        keeps their prepaid amount. This applies to orders > 2019.
        """
        if self.delivery >= date(2019, 1, 1):
            return Invoice.objects.filter(reference=self)
        else:
            return True

    @property
    def prev_status(self):
        """Determine the previous status."""
        return str(int(self.status) - 1)

    @property
    def next_status(self):
        """Determine the next status."""
        return str(int(self.status) + 1)

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
        items = self.orderitem_set.filter(stock=False)
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
    price = models.DecimalField('Precio unitario',
                                max_digits=6, decimal_places=2, default=0)

    def __str__(self):
        """Object's representation."""
        return '{} {} {}-{} ({}€)'.format(
            self.get_item_type_display(), self.name, self.item_class,
            self.size, self.price)

    def clean(self):
        """Clean up the model to avoid duplicate items."""
        exists = Item.objects.filter(name=self.name)
        if exists:
            for item in exists:
                duplicated = (self.item_class == item.item_class and
                              self.item_class == item.item_class and
                              self.size == item.size and
                              self.fabrics == item.fabrics and
                              self.price == item.price
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
    stock = models.BooleanField('Stock', default=False)

    # Item defined price
    price = models.DecimalField('Precio unitario',
                                max_digits=6, decimal_places=2, blank=True)

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

        # When no price is given, pickup the object item's default
        if not self.price:
            obj_item = Item.objects.get(pk=self.element.pk)
            self.price = obj_item.price

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

    @property
    def subtotal(self):
        """Dsiplay the subtotal amount."""
        return self.qty * self.price


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


class PQueue(models.Model):
    """Create a production queue."""

    item = models.OneToOneField(OrderItem, on_delete=models.CASCADE,
                                primary_key=True)
    score = models.IntegerField(unique=True, blank=True, null=True)

    class Meta:
        """Meta options."""

        ordering = ['score']

    def clean(self):
        """Override clean method."""
        # Avoid stock items to be added to the db."""
        if self.item.stock:
            raise ValidationError('Stocked items can\'t be queued')

    def save(self, *args, **kwargs):
        """Override the save method."""
        # Set score if none
        if self.score is None:
            highest = PQueue.objects.last()
            if not highest:
                self.score = 1000
            else:
                self.score = highest.score + 1

        # Set score if 0
        elif self.score == 0:
            score_1 = PQueue.objects.filter(score=1)
            if score_1.exists():
                for item in PQueue.objects.reverse():
                    item.score = item.score + 1
                    item.save()
                self.score = 1
            else:
                self.score = 1
        super().save(*args, **kwargs)

    def top(self):
        """Raise the current item to the top."""
        prev_elements = PQueue.objects.filter(score__gt=0)
        prev_elements = prev_elements.filter(score__lt=self.score)
        if not prev_elements:
            return ('Warning: you are trying to raise an item that is ' +
                    'already on top')
        else:
            self.score = prev_elements.first().score - 1
            try:
                self.clean()
            except ValidationError:
                return False
            else:
                self.save()
                return True

    def up(self):
        """Raise one position the element in the list."""
        above_elements = PQueue.objects.filter(score__lt=self.score)
        if not above_elements:
            return ('Warning: you are trying to raise an item that is ' +
                    'already on top')
        elif above_elements.count() == 1:
            return self.top()
        else:
            closest, next = above_elements.reverse()[:2]
            if closest.score - next.score > 1:
                self.score = closest.score - 1
                try:
                    self.clean()
                except ValidationError:
                    return False
                else:
                    self.save()
                    return True
            else:
                try:
                    self.clean()
                except ValidationError:
                    return False
                else:
                    closest.score = -1
                    closest.save()
                    self.score = next.score + 1
                    self.save()
                    closest.score = next.score + 2
                    closest.save()
                    return True

    def down(self):
        """Lower one position the element in the list."""
        next_elements = PQueue.objects.filter(score__gt=self.score)
        if not next_elements:
            return ('Warning: you are trying to lower an item that is ' +
                    'already at the bottom')
        else:
            try:
                self.clean()
            except ValidationError:
                return False
            else:
                return next_elements[0].up()

    def bottom(self):
        """Lower to the bottom."""
        next_elements = PQueue.objects.filter(score__gt=self.score)
        if not next_elements:
            return ('Warning: you are trying to lower an item that is ' +
                    'already at the bottom')
        else:
            self.score = next_elements.last().score + 1
            try:
                self.clean()
            except ValidationError:
                return False
            else:
                self.save()
                return True

    def complete(self):
        """Complete an item."""
        first = PQueue.objects.first()
        if first.score > 0:
            self.score = -2
        else:
            self.score = first.score - 1
        try:
            self.clean()
        except ValidationError:
            return False
        else:
            self.save()
            return True

    def uncomplete(self):
        """Send the item again to list."""
        try:
            self.clean()
        except ValidationError:
            return False
        else:
            return self.bottom()


class Invoice(models.Model):
    """Hold the invoices generated by orders."""

    reference = models.OneToOneField(
        Order, on_delete=models.CASCADE, primary_key=True)
    issued_on = models.DateTimeField(default=timezone.now)
    invoice_no = models.IntegerField('Factura no.', unique=True)
    amount = models.DecimalField(
        'Importe con IVA', max_digits=7, decimal_places=2)
    pay_method = models.CharField(
        'Medio de pago', max_length=1, choices=settings.PAYMENT_METHODS,
        default='C')

    def save(self, *args, **kwargs):
        """Override the save method."""
        """Ensure that the invoices are consecutive starting at 1 while keeping
        their original value (if any)."""
        if not self.invoice_no:
            newest = Invoice.objects.first()
            if not newest:
                self.invoice_no = 1
            else:
                self.invoice_no = newest.invoice_no + 1

        # Get the total amount of the ticket
        items = OrderItem.objects.filter(reference=self.reference)
        field = models.F
        total = items.aggregate(
            amount=models.Sum(field('qty') * field('price'),
                              output_field=models.DecimalField()))
        if not total['amount']:
            raise ValidationError('The invoice has no amount')
        else:
            self.amount = total['amount']

        super().save(*args, **kwargs)

    class Meta():
        """Meta options."""

        ordering = ['-invoice_no']


class BankMovement(models.Model):
    """Hold the movements between the bank and the check out."""

    action_date = models.DateField('Fecha del moviento', default=timezone.now)
    amount = models.DecimalField('Cantidad', max_digits=7, decimal_places=2)
    notes = models.TextField('Observaciones', blank=True, null=True)

    class Meta():
        """Meta options."""

        ordering = ['-action_date']
#
#
#
#
