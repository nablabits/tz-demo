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
    email = models.EmailField('Emil', max_length=64, blank=True)
    CIF = models.CharField('CIF', max_length=10, blank=True)
    cp = models.IntegerField('CP')
    notif = models.BooleanField(default=False)

    def __str__(self):
        """Get the name of the entry."""
        return self.name

    # @property
    def orders_made(self):
        orders = len(Order.objects.filter(customer=self.pk))
        return orders


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
        ('7', 'Delivered')
    )

    inbox_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    ref_name = models.CharField('Referencia', max_length=32)
    delivery = models.DateField('Entrega prevista',
                                blank=True, default=timezone.now)
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
        """Force object name."""
        return '%s %s %s' % (self.inbox_date.date(),
                             self.customer, self.ref_name)

    @property
    def overdue(self):
        return date.today() > self.delivery

    @property
    def pending(self):
        return self.prepaid - self.budget


class Comment(models.Model):
    """Keep the comments by order & user."""

    creation = models.DateTimeField('Cuando', default=timezone.now)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    reference = models.ForeignKey(Order, on_delete=models.CASCADE)
    comment = models.TextField(default='')

    def __str__(self):
        """Force object name."""
        name = ('El ' + str(self.creation.date()) +
                ', ' + str(self.user) + ' comentó en ' + str(self.reference))
        return name


class CommentCheck(models.Model):
    """Mark the comment as read."""

    creation = models.DateTimeField(default=timezone.now)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    read = models.BooleanField('Leido', default=False)
