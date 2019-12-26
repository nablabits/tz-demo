"""Orders app let manage and control customers, orders and timing.

Its intended use is for business related to tailor made clothes.
"""

import io
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string

from . import managers, settings
from .utils import WeekColor, prettify_times
from decouple import config

from todoist.api import TodoistAPI
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


def default_category():
    """Get or create the default category for expenses."""
    obj, _ = ExpenseCategory.objects.get_or_create(
        name='default', description='The default category')
    return obj.pk


class Customer(models.Model):
    """Hold the data relative to Customers."""

    creation = models.DateTimeField('Alta', default=timezone.now)
    name = models.CharField('Nombre', max_length=64)
    address = models.CharField('Dirección', max_length=64, blank=True)
    city = models.CharField('Localidad', max_length=32, blank=True)
    phone = models.IntegerField('Telefono')
    email = models.EmailField('Email', max_length=64, blank=True)
    CIF = models.CharField('CIF', max_length=20, blank=True)
    cp = models.IntegerField('CP')
    notes = models.TextField('Observaciones', blank=True, null=True)
    provider = models.BooleanField('Proveedor', default=False)
    group = models.BooleanField('Grupo', default=False)

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

        # Avoid being provider & group @ the same time
        if self.provider and self.group:
            raise ValidationError(
                {'provider': _('Un cliente no puede ser proveedor y grupo al' +
                               ' mismo tiempo')})

    def save(self, *args, **kwargs):
        """Override save method."""
        # if clean() was not called, providers are default, this avoids being
        # group and provider simultaneously
        if self.provider:
            self.group = False

        super().save(*args, **kwargs)

    def email_name(self):
        """Get first name in lower case and properly capitalized."""
        return self.name.lower().split()[0].capitalize()

    class Meta:
        ordering = ('name',)


class Order(models.Model):
    """The main object, store the order info."""

    STATUS = (
        # Shop
        ('1', 'Icebox'),
        # WorkShop
        ('2', 'En cola'),
        ('3', 'En proceso'),
        ('4', 'Confección'),  # deprecated since 2020
        ('5', 'Remate'),  # deprecated since 2020
        # Shop
        ('6', 'En espera'),
        ('7', 'Entregado'),
        ('8', 'Cancelado'),
        ('9', 'Facturado')
    )

    PRIORITY = (
        ('1', 'Alta'),
        ('2', 'Normal'),
        ('3', 'Baja')
    )
    inbox_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, null=True,
        related_name='order')
    membership = models.ForeignKey(
        Customer, limit_choices_to={'group': True}, blank=True,
        null=True, on_delete=models.SET_NULL, related_name='group_order')
    ref_name = models.CharField('Referencia', max_length=32)
    delivery = models.DateField('Entrega prevista', blank=True)
    status = models.CharField(max_length=1, choices=STATUS, default='1')
    priority = models.CharField(
        'Prioridad', max_length=1, choices=PRIORITY, default='2')
    confirmed = models.BooleanField('Confirmado', default=True)

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
    # budget was deprecated by 2019 on invoices behalf
    # prepaid was deprecated by 2020 on cashflow model behalf
    budget = models.DecimalField(
        'Presupuesto', max_digits=7, decimal_places=2, blank=True, null=True)
    prepaid = models.DecimalField(
        'Prepago', max_digits=7, decimal_places=2, blank=True, null=True,
        default=0)

    # Custom managers
    objects = models.Manager()
    live = managers.LiveOrders()
    outdated = managers.OutdatedOrders()
    obsolete = managers.ObsoleteOrders()

    def __str__(self):
        """Object's representation."""
        return '%s %s %s' % (self.pk,
                             self.customer, self.ref_name)

    def clean(self):
        """Set validation constraints."""
        # Ensure that customer is not provider
        if self.customer and self.customer.provider:
            msg = 'El cliente no puede ser proveedor'
            raise ValidationError({'customer': _(msg)})

    def save(self, *args, **kwargs):
        """Override save method."""
        # ensure invoiced orders are in status 9
        try:
            self.invoice
        except ObjectDoesNotExist:
            pass
        else:
            self.status = '9'

        # ensure trapuzarrak is always Confirmed
        if self.customer and self.customer.name.lower() == 'trapuzarrak':
            self.confirmed = True

        # ensure membership field is a group customer
        if self.membership and not self.membership.group:
            self.membership = None

        # Since 2020 statuses 4 & 5 are deprecated so redirect them to status 3
        if self.status in ('4', '5'):
            self.status = '3'

        super().save(*args, **kwargs)

        """After saving, add a new StatusShift (will be created only if status
        has changed)"""
        StatusShift.objects.create(order=self, status=self.status)

    def kill(self, pay_method='C'):
        """Kill the order.

        Kill is the only entry point for invoicing orders. It sets the last
        state an order should have.
        """
        # Avoid killed orders to be rekilled
        try:
            self.invoice
        except ObjectDoesNotExist:
            pass
        else:
            exit

        # If there are pending payments, kill'em
        if self.pending:
            CashFlowIO.objects.create(
                order=self, amount=self.pending, pay_method=pay_method)

        """
        Only shifting up to status 7 with kanban_forward updates the
        delivery date, so update it if we're delayed (like for express orders).
        """
        if self.status != '7':
            self.deliver()  # Creates status shift

        # Set status to 9 (invoiced)
        self.status = '9'
        self.save()  # Also creates status shift and closes it

        # And issue the invoice
        i = Invoice(reference=self, pay_method=pay_method, amount=self.total)
        i.save(kill=True)

        # Finally archive the project in todoist
        self.archive()

        return

    @property
    def tz(self):
        """Determine whether the customer is Trapuzarrak."""
        return self.customer.name.lower() == 'trapuzarrak'

    @property
    def overdue(self):
        """Set the overdue property."""
        if self.status != '7':
            overdue = date.today() > self.delivery
        else:
            overdue = False
        return overdue

    @property
    def total(self):
        """Get the total amount for the invoice."""
        items = self.items.aggregate(
            total=models.Sum(models.F('qty') * models.F('price'),
                             output_field=models.DecimalField()))
        return [items['total'] if items['total'] else 0][0]

    @property
    def total_bt(self):
        """Get the total amount before taxes."""
        return round(float(self.total) / 1.21, 2)

    @property
    def vat(self):
        """Calculate the taxes amount."""
        return round(float(self.total_bt) * .21, 2)

    @property
    def already_paid(self):
        """Collect the total amount paid by the order."""
        cf = CashFlowIO.inbounds.filter(order=self)
        prepaid = cf.aggregate(total=models.Sum('amount'))
        if not prepaid['total']:
            return 0
        else:
            return prepaid['total']

    @property
    def pending(self):
        """Get the pending amount of the order."""
        return self.total - self.already_paid

    @property
    def days_open(self):
        """Calculate the days the order has been open."""
        return (date.today() - self.status_shift.first().date_in.date()).days

    @property
    def color(self):
        """Add a color depending the delivery date."""
        return WeekColor(self.delivery).get()

    @property
    def has_no_items(self):
        """Determine if the order has no items."""
        items = OrderItem.objects.filter(reference=self)
        if not items:
            return True
        else:
            return False

    @property
    def has_comments(self):
        """Determine if the order has comments."""
        return Comment.objects.filter(reference=self)

    @property
    def times(self):
        """Determine how many of the trackeable times have been tracked."""
        tracked = 0
        items = self.items.filter(stock=False)
        for item in items:
            tracked = tracked + item.time_quality
        return (tracked, len(items) * 3)

    @property
    def estimated_time(self):
        """Estimate the time in seconds to produce the order."""
        items = self.items.exclude(stock=True)
        tc, ts, ti = 0, 0, 0  # set initial times to 0
        for item in items:
            c, s, i = item.estimated_time
            tc += c
            ts += s
            ti += i
        return (tc, ts, ti)

    @property
    def production_time(self):
        """Calculate the total production time spent."""
        items = OrderItem.objects.filter(reference=self)
        time = items.aggregate(
            tc=models.Sum('crop'),
            ts=models.Sum('sewing'),
            ti=models.Sum('iron'), )
        return time['tc'] + time['ts'] + time['ti']

    def deliver(self):
        """Deliver the order and update the date."""
        self.status = '7'
        self.delivery = date.today()
        return self.save()

    def kanban_forward(self):
        """Shift to the next kanban stage.

        Although statuses 4 & 5 were deprecated since 2020, keep them a while.
        """
        if self.status == '1':
            self.status = '2'
        elif self.status == '2':
            self.status = '3'
        elif self.status in ('3', '4', '5'):
            self.status = '6'
        elif self.status == '6':
            self.status = '7'
            self.delivery = date.today()
        elif self.status == '8':
            self.status = '1'
        else:
            msg = 'Can\'t shift the status over 7 (call `kill()`).'
            raise ValidationError({'status': _(msg)})
        self.save()

    def kanban_backward(self):
        """Jump back to previous kanban stage.

        Although statuses 4 & 5 were deprecated since 2020, keep them a while.
        """
        if self.status == '2':
            self.status = '1'
        elif self.status in ('3', '4', '5'):
            self.status = '2'
        elif self.status in ('6', '7'):  # Order returned to fix something
            self.status = '3'
        elif self.status == '8':  # resume order
            self.status = '1'
        elif self.status == '9':
            msg = 'Invoiced orders can\'t change their status.'
            raise ValidationError({'status': _(msg)})
        else:
            msg = 'Can\'t shift the status below 1.'
            raise ValidationError({'status': _(msg)})

        self.save()

    def t_sync(self):
        """Syncronize with todoist server."""
        try:
            self.t_api
        except AttributeError:
            self.t_api = TodoistAPI(config('TODOIST_API_TOKEN'))
        self.t_api.sync()
        name = '%s.%s' % (self.pk, self.customer.name)
        self.t_pid = False
        for p in self.t_api.projects.all():
            if p['name'] == name:
                self.t_pid = p['id']

    def sync_required(function):
        """Require sycronization decorator.

        Usually the order data is loaded at once on the details page, this
        decorator lets perform a sync from todoist just once (on load).
        """
        def _inner(self, *args, **kwargs):
            try:
                self.t_api
            except AttributeError:
                self.t_sync()
            return function(self, *args, **kwargs)
        return _inner

    @sync_required
    def create_todoist(self):
        """Create a todoist project for the order."""
        if self.t_pid:
            return False
        else:
            name = '%s.%s' % (self.pk, self.customer.name)
            self.t_api.projects.add(name=name, parent_id=config('APP_ID'))
            self.t_api.commit()
            return True

    @sync_required
    def tasks(self):
        """Connect to todoist to get the tasks for the order."""
        if self.t_pid:
            tasks = list()
            for task in self.t_api.items.all():
                if task['project_id'] == self.t_pid:
                    tasks.append(task)
            return tasks
        else:
            return False

    @sync_required
    def is_archived(self):
        """Determine if the project is already archived."""
        if self.t_pid:
            p = self.t_api.projects.get_by_id(self.t_pid)
            return p['is_archived']
        else:
            return False

    @sync_required
    def archive(self):
        """Archive the project on todoist."""
        if self.is_archived() or not self.t_pid:
            return False
        else:
            project = self.t_api.projects.get_by_id(self.t_pid)
            project.archive()
            return self.t_api.commit()

    @sync_required
    def unarchive(self):
        """Unarchive the project on todoist."""
        if self.is_archived():
            project = self.t_api.projects.get_by_id(self.t_pid)
            project.unarchive()
            project.move(parent_id=config('APP_ID'))
            return self.t_api.commit()
        else:
            return False


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
                                  default='S')
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
                duplicated = (self.item_type == item.item_type and
                              self.item_class == item.item_class and
                              self.size == item.size and
                              self.fabrics == item.fabrics and
                              self.price == item.price and
                              self.foreing == item.foreing and
                              self.notes == item.notes
                              )
                if duplicated:
                    msg = 'This item it\'s already in the db'
                    raise ValidationError({'name': _(msg)})

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

    @property
    def html_string(self):
        """Render the item string for views."""
        context = {'type': self.get_item_type_display(),
                   'name': self.name,
                   'class': self.get_item_class_display(),
                   'size': self.size, }
        return render_to_string('includes/item_string.html', context)

    @property
    def avg_crop(self):
        """Average the time to crop the item."""
        crop = OrderItem.objects.filter(element=self)
        crop = crop.exclude(crop=timedelta(0))
        crop = crop.aggregate(
            total=models.Sum('crop'),
            qtys=models.Sum('qty'), )

        return crop['total'] / crop['qtys'] if crop['qtys'] else timedelta(0)

    @property
    def avg_sewing(self):
        """Average the time to sew the item."""
        t0 = timedelta(0)
        sewing = OrderItem.objects.filter(element=self)
        sewing = sewing.exclude(sewing=t0)
        sewing = sewing.aggregate(
            total=models.Sum('sewing'),
            qtys=models.Sum('qty'), )

        return sewing['total'] / sewing['qtys'] if sewing['qtys'] else t0

    @property
    def avg_iron(self):
        """Average the time to iron the item."""
        iron = OrderItem.objects.filter(element=self)
        iron = iron.exclude(iron=timedelta(0))
        iron = iron.aggregate(
            total=models.Sum('iron'),
            qtys=models.Sum('qty'), )

        return iron['total'] / iron['qtys'] if iron['qtys'] else timedelta(0)

    @property
    def pretty_avg(self):
        """Prettify the average times for views."""
        avgs = (self.avg_crop, self.avg_sewing, self.avg_iron)
        return [prettify_times(a.total_seconds()) for a in avgs]

    @property
    def production(self):
        """Sum the total production for this item."""
        item = self.order_item.aggregate(total=models.Sum('qty'))
        return [0 if (not item['total'] or self.foreing) else item['total']][0]

    class Meta:
        ordering = ('name',)


class OrderItem(models.Model):
    """Each order can have one or several clothes."""

    element = models.ForeignKey(
        Item, blank=True, on_delete=models.PROTECT, related_name='order_item')

    qty = models.IntegerField('Cantidad', default=1)
    description = models.TextField('Descripción', blank=True)
    reference = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items')

    batch = models.ForeignKey(
        Order, on_delete=models.SET_NULL, related_name='batch', blank=True,
        limit_choices_to=models.Q(customer__name__iexact='trapuzarrak'),
        null=True, )

    # Timing stuff now goes here
    crop = models.DurationField('Corte', default=timedelta(0))
    sewing = models.DurationField('Confeccion', default=timedelta(0))
    iron = models.DurationField('Planchado', default=timedelta(0))

    """Store if the item is an element that must be fitted (deprecated, since
    we have the 'Varios Arreglo' Item to match that.)"""
    fit = models.BooleanField('Arreglo', default=False)
    stock = models.BooleanField('Stock', default=False)

    # Item defined price
    price = models.DecimalField('Precio unitario',
                                max_digits=6, decimal_places=2, blank=True)

    # Custom managers
    objects = models.Manager()
    active = managers.ActiveItems()

    def save(self, *args, **kwargs):
        """Override the save method."""
        # Avoid items to be stock and fit simultaneously.
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

        # Ensure that items with times are at least in status 3
        times = (self.crop or self.sewing or self.iron)
        void_statuses = self.reference.status in ('1', '2')
        if times and void_statuses:
            self.reference.status = '3'
            self.reference.save()

        # When no price is given, pickup the object item's default
        if not self.price:
            obj_item = Item.objects.get(pk=self.element.pk)
            self.price = obj_item.price

        # Ensure that order express items are stocked
        if self.reference.ref_name == 'Quick':
            self.stock = True

        # Ensure that stock items have no times and can't be fit
        if self.stock:
            self.crop = timedelta(0)
            self.sewing = timedelta(0)
            self.iron = timedelta(0)
            self.fit = False

        # Ensure tz orders don't contain stock items
        if self.reference.customer.name.lower() == 'trapuzarrak':
            self.stock = False

        # Ensure that providing a batch number makes the item stock
        if self.batch:
            self.stock = True

        # Finally, ensure that foreign items are not Stock
        if self.element.foreing:
            self.stock = False

        super().save(*args, **kwargs)

    def clean(self):
        """Define custom validators."""
        # Tz orders can't contain foreign items
        void = (
            self.reference.customer.name.lower() == 'trapuzarrak' and
            self.element.foreing is True
        )
        if void:
            raise ValidationError(_('Los pedidos de Trapuzarrak no pueden ' +
                                    'contener prendas externas'))

        # check that reference & batch are different
        if self.reference == self.batch:
            msg = 'Lote y pedido no pueden ser iguales'
            raise ValidationError({'reference': _(msg)})

        # Check that only tz invoices are batch
        if self.batch and self.batch.customer.name.lower() != 'trapuzarrak':
            msg = ('El numero de lote tiene que corresponder con un pedido ' +
                   'de trapuzarrak')
            raise ValidationError({'batch': _(msg)})

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
        """Display the subtotal amount."""
        return self.qty * self.price

    @property
    def price_bt(self):
        """Display the price before taxes."""
        return round(float(self.price) / 1.21, 2)

    @property
    def subtotal_bt(self):
        """Display the subtotal amount without the taxes."""
        return round(float(self.qty * self.price) / 1.21, 2)

    @property
    def estimated_time(self):
        """Return the estimated time in seconds to produce the item."""
        item = Item.objects.get(pk=self.element.pk)
        times = (
            (item.avg_crop * self.qty).seconds,
            (item.avg_sewing * self.qty).seconds,
            (item.avg_iron * self.qty).seconds, )
        return times

    @property
    def prettified_est(self):
        """Return the displayable estimated times."""
        return [prettify_times(d) for d in self.estimated_time]

    @property
    def ticket_print(self):
        """Output the ticket print lines."""
        item = self.element
        type_name = item.get_item_type_display()
        item_name = item.name
        excluded = ('Traje de niña', )
        if item.foreing:
            if type_name[-1] in ('a', ) and type_name not in excluded:
                item_name = 'genérica'
            else:
                item_name = 'genérico'
        ticket_str = '{} x {} {}'.format(self.qty, type_name, item_name)

        return ticket_str


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
            if not highest or highest.score < 0:
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
            return
        else:
            self.score = prev_elements.first().score - 1
            self.clean()
            self.save()
            return True

    def up(self):
        """Raise one position the element in the list."""
        above_elements = PQueue.objects.filter(score__lt=self.score)
        if not above_elements:
            return
        elif above_elements.count() == 1:
            return self.top()
        else:
            closest, next = above_elements.reverse()[:2]
            if closest.score - next.score > 1:
                self.score = closest.score - 1
                self.clean()
                self.save()
                return True
            else:
                closest.score = -1
                self.clean()
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
            return
        else:
            return next_elements[0].up()

    def bottom(self):
        """Lower to the bottom."""
        next_elements = PQueue.objects.filter(score__gt=self.score)
        if not next_elements:
            return
        else:
            self.score = next_elements.last().score + 1
            self.clean()
            self.save()
            return True

    def complete(self):
        """Complete an item."""
        first = PQueue.objects.first()
        if first.score > 0:
            self.score = -2
        else:
            self.score = first.score - 1
        self.clean()
        self.save()
        return True

    def uncomplete(self):
        """Send the item again to list."""
        if PQueue.objects.count() == 1:
            self.score = 1000
            self.clean()
            self.save()
            return True
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

    def save(self, kill=False, *args, **kwargs):
        """Override the save method."""
        # Ensure only Order.kill() can create/edit invoices
        if not kill:
            return

        self.clean()  # first, run custom validators

        """Ensure that the invoices are consecutive starting at 1 while keeping
        their original value (if any)."""
        if not self.invoice_no:
            newest = Invoice.objects.first()
            if not newest:
                self.invoice_no = 1
            else:
                self.invoice_no = newest.invoice_no + 1

        self.amount = self.reference.total  # Get the total

        super().save(*args, **kwargs)

    def clean(self):
        """Custom validators."""
        # Ensure tz has no invoices
        if self.reference.customer.name.lower() == 'trapuzarrak':
            raise ValidationError({'reference': 'TZ can\'t be invoiced'})

        # Ensure invoices have items (although the amount can be 0€)
        if self.reference.has_no_items:
            raise ValidationError({'reference': 'The invoice has no items'})

    def printable_ticket(self, lc=False):
        """Create a PDF with the sale summary to send or to print."""
        def linecutter(ticket_print):
            """Cut the line string when it's too long."""
            f, s, n = ticket_print, None, 25
            if len(f) > n:
                f = f[:n]
                while f[-1] != ' ':
                    n -= 1
                    f, s = f[:n], ticket_print[n:]
                return s, f[:-1]
            else:
                return (f, )

        # Exit with the line cut for testing
        if lc:
            return linecutter(lc)

        order = self.reference
        items = OrderItem.objects.filter(reference=order)

        buffer = io.BytesIO()

        # Create the PDF object, using the buffer as its "file."
        w, h = 180 * mm, (160 + 30 * len(items)) * mm
        p = canvas.Canvas(buffer, pagesize=(w, h))
        p.setFont("Helvetica", 24)

        # Notice that the PDF is written bottom up, so start by the end
        line = 20 * mm  # bottom margin

        # Start out with the summary
        summary = (
            'Guztira: {}€'.format(order.total),
            'BEZ/IVA (21%) €: {}€'.format(order.vat), )
        for textline in summary:
            p.drawRightString(170 * mm, line, textline)
            line += 15 * mm

        # Separator line & netx block margin
        p.line(100*mm, line, 180*mm, line)
        line += 30 * mm

        # Sale breakdown
        for item in items:
            p.drawRightString(130 * mm, line, '{}€'.format(item.price), )
            p.drawRightString(170 * mm, line, '{}€'.format(item.subtotal), )
            for tl in linecutter(item.ticket_print):
                p.drawString(10, line, tl)
                line += 10 * mm
            line += 10 * mm

        # Separator
        p.line(0, line, 180*mm, line)

        # Finally, the header
        textobject = p.beginText()
        textobject.setTextOrigin(10, line + 60 * mm)
        textobject.textLines(
            """Trapuzarrak · Euskal Jantziak
            Iratxe Maruri Garrastazu
            78870226Y
            Foru enparantza 2, lonja.
            48100 Mungia.
            """)
        textobject.moveCursor(0, 20)
        textobject.textOut(
            'Factura simplificada nº: {}'.format(self.invoice_no))
        p.drawText(textobject)

        # Close the PDF object cleanly, and we're done.
        p.showPage()
        p.save()

        buffer.seek(0)
        return buffer

    class Meta():
        """Meta options."""

        ordering = ['-invoice_no']


class ExpenseCategory(models.Model):
    """Set categories for each expense so we can classify them."""
    creation = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Hold the general expenses of the business."""

    creation = models.DateTimeField('Alta', default=timezone.now)
    issuer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        limit_choices_to={'provider': True}, )
    invoice_no = models.CharField('Número de factura', max_length=64)
    issued_on = models.DateField('Emisión')
    concept = models.CharField('Concepto', max_length=64)
    amount = models.DecimalField(
        'Importe con IVA', max_digits=7, decimal_places=2)
    pay_method = models.CharField(
        'Medio de pago', max_length=1, choices=settings.PAYMENT_METHODS,
        default='T')
    category = models.ForeignKey(ExpenseCategory, default=default_category,
                                 on_delete=models.SET_DEFAULT)
    in_b = models.BooleanField('En B', default=False)
    notes = models.TextField('Observaciones', blank=True, null=True)
    closed = models.BooleanField('Cerrado', default=False)
    consultancy = models.BooleanField(default=True)

    def __str__(self):
        return '{} {}'.format(self.pk, self.issuer.name)

    def clean(self):
        """Ensure the invoices are valid."""
        # Ensure issuers have all the fields filled in
        issuer = Customer.objects.get(pk=self.issuer.pk)
        void = (not issuer.address or not issuer.city or
                not issuer.CIF or not issuer.provider)
        if void:
            raise ValidationError(
                {'issuer': _('The customer does not match' +
                             ' some of the required fields')})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def kill(self):
        """Close the debt."""
        if self.pending:
            CashFlowIO.objects.create(
                expense=self, amount=self.pending, pay_method=self.pay_method)
        self.closed = True
        self.save()

    def _self_close(self):
        """Check the consistency of the close attribute.

        Closed attribute rely on their cashflows' amounts and although delete
        method should reopen the expense, it might be useful from time to time
        to check manually if everything is ok. This method does so.
        """
        if self.pending:
            self.closed = False  # Swap truth
        else:
            self.closed = True  # Swap truth

        return self.save()

    @property
    def already_paid(self):
        """Collect the total amount paid by the order."""
        cf = CashFlowIO.outbounds.filter(expense=self)
        prepaid = cf.aggregate(total=models.Sum('amount'))
        if not prepaid['total']:
            return 0
        else:
            return prepaid['total']

    @property
    def pending(self):
        """Get the pending amount for the expense."""
        return self.amount - self.already_paid


class CashFlowIO(models.Model):
    """Manage the inbound/outbound movements.

    This model tracks the payments done to orders in advance and the splitted
    expense invoices to have a better feel of how the business is running.

    It completely substitutes 2019's prepaid box.
    """
    creation = models.DateTimeField(default=timezone.now)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True,
                              null=True, related_name='cfio_prepaids')
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, blank=True,
                                null=True, limit_choices_to={'closed': False})
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    pay_method = models.CharField(
        max_length=1, choices=settings.PAYMENT_METHODS, default='C')

    # Custom managers
    objects = models.Manager()
    inbounds = managers.Inbounds()
    outbounds = managers.Outbounds()

    def save(self, *args, **kwargs):
        """Override save options."""
        self.clean()  # Run custom validators
        super().save(*args, **kwargs)
        e = self.expense
        if e and e.pending == 0:
            e.closed = True
            e.save()

    def delete(self, *args, **kwargs):
        """Override delete options."""
        # Ensure expenses are reopened after deleting one of their cashflows
        if self.expense:
            self.expense.closed = False
            self.expense.save()
        super().delete(*args, **kwargs)

    def clean(self):
        """Custom validation parameters."""
        # Prevent both order and expense being null simultaneously
        if not self.order and not self.expense:
            msg = 'Pedido y gasto no pueden estar vacios al mismo tiempo.'
            raise ValidationError({'order': _(msg)})

        # Prevent both order and expense being True simultaneously
        if self.order and self.expense:
            msg = 'Pedido y gasto no pueden tener valor al mismo tiempo.'
            raise ValidationError({'order': _(msg)})

        """
        Prevent amount to be over expense/order amount.
        You might want to call kill() in the respective models to close
        payments.
        """
        if self.order:
            pending = self.order.pending
        else:
            pending = self.expense.pending

        if self.amount > pending:
            msg = ('No se puede pagar más de la cantidad ' +
                   'pendiente ({}).'.format(pending))
            raise ValidationError({'amount': _(msg)})

        # Prevent trapuzarrak having cashflow items
        if self.order and self.order.customer.name.lower() == 'trapuzarrak':
            msg = 'Los pedidos de trapuzarrak no admiten pagos'
            raise ValidationError({'order': _(msg)})

    @staticmethod
    def update_old():
        """Update the old cash management.

        Previously, prepaids and total payments where stored in orders/invoices
        so we have to make sure that all the invoices processed have their
        corresponding cash flow movement. Also we need to do so with expense
        objects.
        """
        print('Updating invoices')
        invoices = Invoice.objects.reverse()
        for i in invoices:
            CashFlowIO.objects.create(creation=i.issued_on, order=i.reference,
                                      amount=i.amount, pay_method=i.pay_method)

        print('Updating expenses')
        expenses = Expense.objects.reverse()
        for e in expenses:
            creation = timezone.now() - (timezone.now().date() - e.issued_on)
            CashFlowIO.objects.create(creation=creation, expense=e,
                                      amount=e.amount, pay_method=e.pay_method)
            e.closed = True
            e.save()

        print('Completed. You might want to update prepaids of active orders.')

    class Meta():
        """Meta options."""

        ordering = ['-creation']


class BankMovement(models.Model):
    """Hold the movements between the bank and the check out."""

    action_date = models.DateField('Fecha del moviento', default=timezone.now)
    amount = models.DecimalField('Cantidad', max_digits=7, decimal_places=2)
    notes = models.TextField('Observaciones', blank=True, null=True)

    class Meta():
        """Meta options."""

        ordering = ['-action_date']


class StatusShift(models.Model):
    """The status tracker."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='status_shift')
    date_in = models.DateTimeField(default=timezone.now)
    date_out = models.DateTimeField(blank=True, null=True, )
    status = models.CharField(max_length=1, choices=Order.STATUS, default='1')
    notes = models.TextField(blank=True, null=True)

    def save(self, force_save=False, *args, **kwargs):
        """Override the save method.

        We need to avoid close_last method to interact with the status change
        constraint, so a force_save arg is provided.
        """
        # Direct save the first one
        if not self.last or force_save:
            return super().save(*args, **kwargs)

        # Before  opening a new statusShift close the last one (forces save).
        self.close_last()

        # Prevent a new instance when status doesn't change.
        if self.last.status == self.status:
            return None

        # When status 9 (invoiced) is reached, close also the entry
        if self.status == '9':
            self.date_out = timezone.now()

        # print('status changed', self.status)
        return super().save(*args, **kwargs)

    def delete(self, clear_all=False, *args, **kwargs):
        """Override the delete method.

        clear_all argument was created for the update_20 module prevent the
        Validation error on deleting last item of an order.
        """
        if clear_all:
            return super().delete(*args, **kwargs)

        # Orders must have at least one (the first) ss
        ss = self.order.status_shift
        if ss.count() == 1:
            msg = 'Can\'t delete the last status shift of an order'
            raise ValidationError({'order': _(msg)})

        if self.date_out:
            msg = 'Can\'t delete other than last entries'
            raise ValidationError({'date_out': _(msg)})

        super().delete(*args, **kwargs)

        # After a ss is deleted, the last one should be reopened
        last = self.last
        last.date_out = None
        last.save(force_save=True)

    def clean(self):
        """Validate the model."""
        # Ensure an order has one and only one ss open
        ss = self.order.status_shift
        ss = ss.filter(date_out__isnull=True).count()
        if ss > 1:
            pk = self.order.pk
            msg = 'Order {} has more than one statusShift open'.format(pk)
            raise ValidationError({'order': _(msg)})

        if self.date_out and self.date_in > self.date_out:
            i, o = self.date_in, self.date_out
            msg = 'date_out ({}) is before date_in ({})'.format(i, o)
            raise ValidationError({'date_in': _(msg)})

    def close_last(self):
        """Close the last status."""
        last = self.last
        last.date_out = timezone.now()
        last.full_clean()
        last.save(force_save=True)

    @property
    def last(self):
        """Fetch the last ss from current order."""
        return self.order.status_shift.last()


class Timetable(models.Model):
    """Store the workers timetable.

    End and hours attr can be null when workers are at workplace.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start = models.DateTimeField('entrada', default=timezone.now)
    end = models.DateTimeField('salida', blank=True, null=True)
    hours = models.DurationField('horas', blank=True, null=True)

    # Custom managers
    objects = models.Manager()
    active = managers.ActiveTimetable()

    def save(self, *args, **kwargs):
        """Override the save method.

        When end or hours are provided auto-fill the remaining field.
        """
        if self.end and not self.hours:
            self.hours = self.get_hours()
        elif self.hours and not self.end:
            self.end = self.get_end()
        else:
            pass

        super().save(*args, **kwargs)

    def clean(self):
        """Clean up the model.

        Avoid overlapping, +15h lengths & check simultaneous end and hours.
        """
        # avoid saving a new timetable object when there are timetables open
        t = Timetable.objects.filter(
            end__isnull=True).filter(user=self.user)
        if self.pk:
            t = t.exclude(pk=self.pk)
        if t:
            raise ValidationError(
                {'start': _('Cannot open a timetable when other ' +
                            'timetables are open')})

        # Avoid overlapping
        test_date = self.start.date()
        e = Timetable.objects.filter(start__date=test_date)
        e = e.filter(user=self.user)
        if self.pk:
            e = e.exclude(pk=self.pk)
        for entry in e:
            if entry.end > self.start:
                raise ValidationError(
                    {'start': _('Entry is overlapping an existing entry'), }
                    )

        # Prevent start in the future
        if self.start > timezone.now() + timedelta(hours=1):
            raise ValidationError(
                {'start': _('Entry is starting in the future'), }
                )

        # Avoid end & hours being added simultaneously
        if self.end and self.hours:
            raise ValidationError(
                {'end': _('Can\'t be added end date and hours simultaneously')}
            )

        # Prevent less than 15 min and more than 15h registers
        if self.hours:
            u_lim = timedelta(hours=15)  # upper limit
            if self.hours > u_lim:
                raise ValidationError(
                    {'hours': _('Entry lasts more than 15h'), }
                )

            e = e.aggregate(tracked=models.Sum(
                'hours', output_field=models.DurationField()))
            if e['tracked'] and self.hours + e['tracked'] > u_lim:
                raise ValidationError(
                    {'hours':
                     _('You are trying to track more than 15h today.'), }
                )

            if self.hours < timedelta(minutes=15):
                raise ValidationError(
                    {'hours': _('Sessions less than 15\' are forbidden.')})

        if self.end:
            # Avoid +15h lengths
            if (self.end - self.start).total_seconds() > 54000:
                raise ValidationError(
                    {'end': _('Entry lasts more than 15h'), }
                )

            # Avoid end before start
            if self.start > self.end:
                raise ValidationError(
                    {'start': _('Entry cannot start after the end'), }
                )

    def get_hours(self):
        """Calculate the hours having start and end timestamps."""
        elapsed = round((self.end - self.start).total_seconds() / 3600, 2)
        segment = elapsed - int(elapsed)
        if segment < 0.25:
            hours = timedelta(hours=int(elapsed))
        elif segment >= 0.75:
            hours = timedelta(hours=int(elapsed) + 1)
        else:
            hours = timedelta(hours=int(elapsed) + 0.5)
        return hours

    def get_end(self):
        """Calculate end timestamp having start and hours."""
        return self.start + self.hours

    class Meta:
        ordering = ('start',)
#
#
#
#
