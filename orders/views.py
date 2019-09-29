"""Define all the views for the app."""

from datetime import date, datetime
from random import randint

import markdown2
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, DecimalField, F, Q, Sum
from django.db.utils import IntegrityError
from django.http import Http404, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView
from rest_framework import viewsets

from . import serializers, settings
from .utils import prettify_times
from .forms import (AddTimesForm, CommentForm, CustomerForm, EditDateForm,
                    InvoiceForm, ItemForm, OrderForm, OrderItemForm,
                    TimetableCloseForm, ItemTimesForm, )
from .models import (BankMovement, Comment, Customer, Expense, Invoice, Item,
                     Order, OrderItem, PQueue, Timetable, )

from decouple import config


class CommonContexts:
    """Define common queries for both AJAX and regular views.

    On performing AJAX calls is ususal to reuse the same queries and vars used
    in regular views, since only a part of the view is changed instead of
    reloading.
    """

    @staticmethod
    def kanban(confirmed=True):
        """Get a dict with all the needed vars for the view."""
        icebox = Order.objects.filter(
            status='1').filter(confirmed=confirmed).order_by('delivery')
        queued = Order.objects.filter(
            status='2').filter(confirmed=confirmed).order_by('delivery')
        in_progress = Order.objects.filter(status__in=['3', '4', '5', ])
        in_progress = in_progress.filter(
            confirmed=confirmed).order_by('delivery')
        waiting = Order.objects.filter(
            status='6').filter(confirmed=confirmed).order_by('delivery')
        done = Order.pending_orders.filter(
            status='7').filter(confirmed=confirmed).order_by('delivery')

        # Get the amounts for each column
        amounts = list()
        col1 = OrderItem.active.filter(reference__status='1')
        col2 = OrderItem.active.filter(reference__status='2')
        col3 = OrderItem.active.filter(
            reference__status__in=['3', '4', '5', ])
        col4 = OrderItem.active.filter(reference__status='6')
        col5 = OrderItem.active.filter(reference__status='7')
        for col in (col1, col2, col3, col4, col5):
            col = col.aggregate(
                total=Sum(F('price') * F('qty'), output_field=DecimalField()))
            if not col['total']:
                col['total'] = 0
            amounts.append(col['total'])

        eti, etq = 0, 0
        for order in icebox:
            eti += sum(order.estimated_time)
        for order in queued:
            etq += sum(order.estimated_time)

        est_times = [prettify_times(d) for d in (eti, etq)]

        vars = {'icebox': icebox,
                'queued': queued,
                'in_progress': in_progress,
                'waiting': waiting,
                'done': done,
                'confirmed': confirmed,
                'update_date': EditDateForm(),
                'amounts': amounts,
                'est_times': est_times,
                }
        return vars

    @staticmethod
    def order_details(request, pk):
        """Get a dict with all the reused vars in the view."""
        order = get_object_or_404(Order, pk=pk)  # pragma: no cover

        comments = Comment.objects.filter(
            reference=order).order_by('-creation')
        items = OrderItem.objects.filter(reference=order)

        cur_user = request.user
        now = datetime.now()
        session = Timetable.active.get(user=request.user)

        # Display estimated times
        order_est = [prettify_times(d) for d in order.estimated_time]
        order_est_total = prettify_times(sum(order.estimated_time))

        title = (order.pk, order.customer.name, order.ref_name)
        vars = {'order': order,
                'items': items,
                'order_est': order_est,
                'order_est_total': order_est_total,
                'update_times': ItemTimesForm(),
                'comments': comments,
                'user': cur_user,
                'now': now,
                'session': session,
                'version': settings.VERSION,
                'title': 'Pedido %s: %s, %s' % title,

                # CRUD Actions
                'btn_title_add': 'Añadir prendas',
                'js_action_add': 'order-item-add',
                'js_action_edit': 'order-item-edit',
                'js_action_delete': 'order-item-delete',
                'js_data_pk': order.pk,
                }
        return vars


def timetable_required(function):
    """Prevent users without valid timetable to load pages."""
    def _inner(request, *args, **kwargs):
        u = request.user
        active = Timetable.objects.filter(user=u).filter(end__isnull=True)
        if not active:
            Timetable.objects.create(user=u)
            return function(request, *args, **kwargs)
        else:
            elp = (timezone.now() - active[0].start).total_seconds()
            void = (elp > 54000 or
                    timezone.now().date() != active[0].start.date())
            if void:
                return redirect('add_hours')
            else:
                return function(request, *args, **kwargs)
    return _inner


# Add hours
@login_required
def add_hours(request):
    """Close an open work session."""
    # prevent reaching this page without valid timetable open
    try:
        active = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:
        return redirect('main')

    view_settings = {'cur_user': request.user,
                     'now': datetime.now(),
                     'version': settings.VERSION,
                     'title': 'TrapuZarrak · Añadir horas',
                     'active': active, }

    if request.method == 'GET':
        view_settings['form'] = TimetableCloseForm()
        if active.start.date() == date.today():
            view_settings['on_time'] = True
    else:
        form = TimetableCloseForm(request.POST, instance=active)
        if form.is_valid():
            form.save()
            if request.POST.get('keep-open', None):
                return redirect('main')
            else:
                logout(request)
                return redirect('login')
        else:
            view_settings['form'] = form
    return render(request, 'registration/add_hours.html', view_settings)


# Root View
@login_required
@timetable_required
def main(request):
    """Create the home page view."""
    # Goal box, goal
    elapsed = date.today() - date(2018, 12, 31)
    goal = elapsed.days * settings.GOAL

    # GoalBox, Avoid naive dates
    offset = date.today() - date(2018, 12, 31)
    start = timezone.now() - offset

    # GoalBox, this year unsold items in queue
    year_items = OrderItem.objects.filter(reference__delivery__gte=start)
    year_items = year_items.filter(reference__invoice__isnull=True)
    year_items = year_items.exclude(reference__ref_name__iexact='quick')
    year_items = year_items.exclude(reference__status=8)

    # GoalBox, solid incomes: already sold or in confirmed orders
    sales = Invoice.objects.filter(issued_on__year=date.today().year)
    sales = sales.aggregate(total=Sum('amount'))
    confirmed = year_items.filter(reference__confirmed=True)
    confirmed = confirmed.exclude(
        reference__customer__name__iexact='trapuzarrak')

    # GoalBox, smoke incomes: unconfirmed, produced tz & future tz
    unconfirmed = year_items.exclude(reference__confirmed=True)
    unconfirmed = unconfirmed.exclude(
        reference__customer__name__iexact='trapuzarrak')
    tz_items = year_items.filter(
        reference__customer__name__iexact='trapuzarrak')
    produced_tz = tz_items.filter(reference__status=7)
    future_tz = tz_items.exclude(reference__status__in=[7, 8])

    # GoalBox, get aggregations for above queries
    queries = (confirmed, unconfirmed, produced_tz, future_tz, )
    aggregates = list()
    for query in queries:
        aggregate = query.aggregate(
            total=Sum(F('price') * F('qty'), output_field=DecimalField()))
        if not aggregate['total']:  # avoid NoneType aggregate
            aggregate = 0
        else:
            aggregate = float(aggregate['total'])
        aggregates.append(aggregate)

    # GoalBox, summary amounts and bar
    if not sales['total']:  # avoid NoneType aggregate
        aggregates.insert(0, 0)
    else:
        aggregates.insert(0, float(sales['total']))  # Amounts list
    bar = [round(amount * 100 / (2 * goal), 2) for amount in aggregates]

    # GoalBox, expenses bar
    expenses = Expense.objects.filter(
        issued_on__year=2019).aggregate(total=Sum('amount'))
    if not expenses['total']:
        expenses['total'] = 0
    exp_perc = round(float(expenses['total']) * 100 / (2 * goal), 2)
    se_diff = expenses['total']

    # Active Box
    active = Order.active.count()
    active_msg = False
    waiting = Order.active.filter(status='6').count()
    if waiting:
        active_msg = 'Aunque hay %s para entregar' % waiting

    # Pending box
    pending = Order.pending_orders.all()
    if pending:
        active_confirmed = OrderItem.active.filter(reference__confirmed=True)
        pending_amount = active_confirmed.aggregate(
            total=Sum(F('price') * F('qty'), output_field=DecimalField()))
        prepaid = pending.aggregate(total=Sum('prepaid'))
        if not pending_amount['total']:
            pending_amount['total'] = 0
        if not prepaid['total']:
            prepaid['total'] = 0
        pending_amount = abs(int(pending_amount['total'] - prepaid['total']))
        if pending_amount == 0:
            pending_msg = 'Hay pedidos activos pero no tienen prendas añadidas'
        else:
            pending_msg = '%s€ tenemos aún<br>por cobrar' % pending_amount
    else:
        pending_msg = 'Genial, tenemos todo cobrado!'

    # Outdated box
    outdated = Order.outdated.count()
    if not outdated:
        outdated = False

    # Balance box (copied from invoiceslist view)
    expenses = Expense.objects.filter(pay_method='C').aggregate(
        total_cash=Sum('amount')
    )
    if not expenses['total_cash']:
        expenses['total_cash'] = 0
    all_time_cash = Invoice.objects.filter(pay_method='C')
    all_time_cash = all_time_cash.aggregate(total_cash=Sum('amount'))
    all_time_deposit = BankMovement.objects.all()
    all_time_deposit = all_time_deposit.aggregate(total_cash=Sum('amount'))
    if not all_time_deposit['total_cash']:
        all_time_deposit['total_cash'] = 0
    if not all_time_cash['total_cash']:
        all_time_cash['total_cash'] = 0
    balance = all_time_deposit['total_cash'] - all_time_cash['total_cash']
    balance = balance + expenses['total_cash']
    if balance < 0:
        balance_msg = (
            """<h3 class="box_link_h">%s€</h3>
            <h4 class="box_link_h">Pendientes de ingresar
            </h4>""" % abs(balance))
    elif balance > 0:
        balance_msg = (
            """<h3 class="box_link_h">%s€</h3>
            <h4 class="box_link_h">has ingresado de más
            </h4>""" % abs(balance))
    else:
        balance_msg = '<h4 class="box_link_h">Estás en paz con el banco<h4>'

    # Month production box
    month = Invoice.objects.filter(
        issued_on__month=timezone.now().date().month)
    month = month.aggregate(total=Sum('amount'))

    # week production box
    week = Invoice.objects.filter(
        issued_on__week=timezone.now().date().isocalendar()[1])
    week = week.aggregate(total=Sum('amount'))

    # top5 customers Box
    top5 = Customer.objects.exclude(name__iexact='express')
    top5 = top5.filter(order__invoice__isnull=False)
    top5 = top5.annotate(
        total=Sum(F('order__orderitem__price') * F('order__orderitem__qty'),
                  output_field=DecimalField()))
    top5 = top5.order_by('-total')[:5]

    cur_user = request.user
    session = Timetable.active.get(user=request.user)

    # Query last comments on active orders
    comments = Comment.objects.exclude(user=cur_user)
    comments = comments.exclude(read=True)
    comments = comments.order_by('-creation')

    now = datetime.now()

    view_settings = {'goal': goal,
                     'bar': bar,
                     'aggregates': aggregates,
                     'exp_perc': exp_perc,
                     'se_diff': se_diff,
                     'active': active,
                     'active_msg': active_msg,
                     'pending': Order.pending_orders.count(),
                     'pending_msg': pending_msg,
                     'outdated': outdated,
                     'month': month['total'],
                     'week': week['total'],
                     'balance_msg': balance_msg,
                     'top5': top5,
                     'comments': comments,
                     'user': cur_user,
                     'session': session,
                     'now': now,
                     'version': settings.VERSION,
                     'search_on': 'orders',
                     'placeholder': 'Buscar pedido (referencia)',
                     'title': 'TrapuZarrak · Inicio',
                     }

    return render(request, 'tz/main.html', view_settings)


def search(request):
    """Perform a search on orders, custmers and items."""
    if request.method == 'POST':
        data = dict()
        context = dict()
        search_on = request.POST.get('search-on')
        search_obj = request.POST.get('search-obj')
        if not search_obj:
            raise Http404
        if search_on == 'orders':
            table = Order.objects.all()
            try:
                int(search_obj)
            except ValueError:
                query_result = table.filter(ref_name__icontains=search_obj)
            else:
                query_result = table.filter(pk=search_obj)
            model = 'orders'
        elif search_on == 'customers':
            table = Customer.objects.exclude(provider=True)
            table = table.exclude(name__iexact='express')
            try:
                int(search_obj)
            except ValueError:
                query_result = table.filter(name__icontains=search_obj)
            else:
                query_result = table.filter(phone__icontains=search_obj)
            model = 'customers'
        elif search_on == 'items':
            order_pk = request.POST.get('order-pk', None)
            if not order_pk:
                raise Http404('An id for order should be included.')
            query_result = Item.objects.filter(name__istartswith=search_obj)
            model = 'items'
            context['order_pk'] = order_pk
        else:
            raise ValueError('Search on undefined')
        template = 'includes/search_results.html'
        context['query_result'] = query_result
        context['model'] = model

        """
        Test stuff. Since it's not very straightforward extract this data
        from render_to_string() method, we'll pass them as keys in JSON but
        just for testing purposes.
        """
        if request.POST.get('test'):
            data['template'] = template
            add_to_context = list()
            for k in context:
                add_to_context.append(k)
            data['context'] = add_to_context
            data['model'] = model
            data['query_result'] = len(query_result)
            if model == 'orders':
                data['query_result_name'] = query_result[0].ref_name
            else:
                data['query_result_name'] = query_result[0].name

        data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)
    else:
        raise TypeError('Invalid request method')


# List views
@login_required
@timetable_required
def orderlist(request, orderby):
    """Display all orders in a view.

    GET requests display the orders sorted by the 'orderby' get parameter.
    POST requests are used to update the status or to set as paid the orders
    (for now). They display the view by date (default).

    In the view, orders are separated on different tabs: active, delivered, tz
    active & delivered, and cancelled. The first two exclude tz orders, if such
    customer exists, while the the next two are exclusive for it (production &
    stock for the shop). Finally, all cancelled orders are displayed regardless
    the customer.
    """
    # POST method to update status & set paid an order.
    if request.method == 'POST':
        order_pk = request.POST.get('order')
        order = get_object_or_404(Order, pk=order_pk)
        if request.POST.get('status'):
            order.status = request.POST.get('status')
        elif request.POST.get('collect'):
            order.prepaid = order.budget
        else:
            raise Http404('Action required')
        order.save()

    orders = Order.objects.exclude(ref_name__iexact='quick')

    try:
        tz = Customer.objects.get(name__iexact='trapuzarrak')
    except ObjectDoesNotExist:
        tz = None

    # Get the orders for each tab when tz customer exists
    if tz:
        # First query the stock, tz related queries
        tz_orders = orders.filter(customer=tz)
        tz_active = tz_orders.exclude(status__in=[7, 8]).order_by('delivery')
        tz_delivered = tz_orders.filter(status=7).order_by('-delivery')[:10]

        # And the attr collection for them
        tz_active = tz_active.annotate(Count('orderitem', distinct=True),
                                       Count('comment', distinct=True),
                                       timing=(Sum('orderitem__sewing') +
                                               Sum('orderitem__iron') +
                                               Sum('orderitem__crop')))
        tz_delivered = tz_delivered.annotate(Count('orderitem', distinct=True),
                                             Count('comment', distinct=True),
                                             timing=(Sum('orderitem__sewing') +
                                                     Sum('orderitem__iron') +
                                                     Sum('orderitem__crop')))

        # Finally, exclude tz customer for further queries and sort
        orders = orders.exclude(customer=tz)

    # If tz customer doesn't exist, these vars should be none
    else:
        tz_active = None
        tz_delivered = None

    delivered = orders.filter(status=7).order_by('-delivery')[:10]
    active = orders.exclude(status__in=[7, 8])
    cancelled = orders.filter(status=8).order_by('-inbox_date')[:10]
    pending = orders.exclude(status=8).filter(delivery__gte=date(2019, 1, 1))
    pending = pending.filter(invoice__isnull=True).order_by('delivery')
    pending = pending.exclude(confirmed=False)

    # Active, delivered & pending orders show some attr at glance
    active = active.annotate(Count('orderitem', distinct=True),
                             Count('comment', distinct=True),
                             timing=(Sum('orderitem__sewing') +
                                     Sum('orderitem__iron') +
                                     Sum('orderitem__crop')))

    delivered = delivered.annotate(Count('orderitem', distinct=True),
                                   Count('comment', distinct=True),
                                   timing=(Sum('orderitem__sewing') +
                                           Sum('orderitem__iron') +
                                           Sum('orderitem__crop')))

    pending = pending.annotate(Count('orderitem', distinct=True),
                               Count('comment', distinct=True),
                               timing=(Sum('orderitem__sewing') +
                                       Sum('orderitem__iron') +
                                       Sum('orderitem__crop')))

    # Total pending amount
    items = OrderItem.objects.filter(reference__delivery__gte=date(2019, 1, 1))
    items = items.exclude(reference__status=8)
    items = items.exclude(reference__ref_name__iexact='quick')
    items = items.exclude(reference__customer__name__iexact='Trapuzarrak')
    items = items.filter(reference__invoice__isnull=True)
    items = items.exclude(reference__confirmed=False)
    items = items.aggregate(
        total=Sum(F('price') * F('qty'), output_field=DecimalField()))
    prepaid = pending.aggregate(total=Sum('prepaid'))
    try:
        pending_total = items['total'] - prepaid['total']
    except TypeError:
        pending_total = 0

    # This week active entries
    this_week = date.today().isocalendar()[1]
    this_week_active = Order.objects.filter(Q(delivery__week=this_week) |
                                            Q(delivery__lte=timezone.now()))
    this_week_active = this_week_active.exclude(status__in=[7, 8])
    i_relax = settings.RELAX_ICONS[randint(0, len(settings.RELAX_ICONS) - 1)]

    # calendar view entries
    active_calendar = Order.objects.exclude(status__in=[7, 8])
    confirmed = active_calendar.filter(confirmed=True).count()
    unconfirmed = active_calendar.filter(confirmed=False).count()

    # Finally, set the sorting method on view
    if orderby == 'date':
        active = active.order_by('delivery')
        active_calendar = active_calendar.order_by('delivery')
    elif orderby == 'status':
        active = active.order_by('status')
        active_calendar = active_calendar.order_by('status')
    elif orderby == 'priority':
        active = active.order_by('priority')
        active_calendar = active_calendar.order_by('priority')
    else:
        raise Http404('Required sorting method')

    cur_user = request.user
    now = datetime.now()
    session = Timetable.active.get(user=request.user)

    view_settings = {'active': active,
                     'confirmed': confirmed,
                     'unconfirmed': unconfirmed,
                     'delivered': delivered,
                     'user': cur_user,
                     'now': now,
                     'session': session,
                     'version': settings.VERSION,
                     'active_stock': tz_active,
                     'active_calendar': active_calendar,
                     'this_week_active': this_week_active,
                     'i_relax': i_relax,
                     'delivered_stock': tz_delivered,
                     'cancelled': cancelled,
                     'pending': pending,
                     'pending_total': pending_total,
                     'prepaid': prepaid['total'],
                     'to_invoice': items['total'],
                     'order_by': orderby,
                     'placeholder': 'Buscar pedido (referencia o nº)',
                     'search_on': 'orders',
                     'title': 'TrapuZarrak · Pedidos',
                     'colors': settings.WEEK_COLORS,
                     }

    return render(request, 'tz/orders.html', view_settings)


@login_required
@timetable_required
def customerlist(request):
    """Display all customers or search'em."""
    customers = Customer.objects.all().exclude(name__iexact='express')
    customers = customers.exclude(provider=True)
    customers = customers.order_by('name')
    customers = customers.annotate(num_orders=Count('order'))
    page = request.GET.get('page', 1)
    paginator = Paginator(customers, 10)
    try:
        customers = paginator.page(page)
    except PageNotAnInteger:
        customers = paginator.page(1)
    except EmptyPage:
        customers = paginator.page(paginator.num_pages)

    cur_user = request.user
    now = datetime.now()
    session = Timetable.active.get(user=request.user)

    view_settings = {'customers': customers,
                     'user': cur_user,
                     'now': now,
                     'session': session,
                     'version': settings.VERSION,
                     'search_on': 'customers',
                     'placeholder': 'Buscar cliente',
                     'title': 'TrapuZarrak · Clientes',
                     'h3': 'Todos los clientes',

                     # CRUD actions
                     'btn_title_add': 'Nuevo cliente',
                     'js_action_add': 'customer-add',
                     'js_data_pk': '0',

                     'include_template': 'includes/customer_list.html',
                     }

    return render(request, 'tz/list_view.html', view_settings)


@login_required
@timetable_required
def itemslist(request):
    """Show the different item objects."""
    cur_user = request.user
    now = datetime.now()
    session = Timetable.active.get(user=request.user)

    view_settings = {'user': cur_user,
                     'now': now,
                     'session': session,
                     'version': settings.VERSION,
                     'title': 'TrapuZarrak · Prendas',
                     'h3': 'Todas las prendas',
                     'table_id': 'item-selector',

                     # CRUD Actions
                     'btn_title_add': 'Añadir prenda',
                     'js_action_add': 'object-item-add',
                     'js_action_edit': 'object-item-edit',
                     'js_action_delete': 'object-item-delete',
                     'js_action_send_to': 'send-to-order',
                     'js_data_pk': '0',
                     }

    return render(request, 'tz/list_view.html', view_settings)


@login_required
@timetable_required
def invoiceslist(request):
    """List all the invoices."""
    today = Invoice.objects.filter(issued_on__date=timezone.now().date())
    week = Invoice.objects.filter(
        issued_on__week=timezone.now().date().isocalendar()[1])
    month = Invoice.objects.filter(
        issued_on__month=timezone.now().date().month)
    all_time_cash = Invoice.objects.filter(pay_method='C')
    all_time_cash = all_time_cash.aggregate(total_cash=Sum('amount'))
    today_cash = today.aggregate(
        total=Sum('amount'),
        total_cash=Sum('amount', filter=Q(pay_method='C')),
        total_card=Sum('amount', filter=Q(pay_method='V')),
        total_transfer=Sum('amount', filter=Q(pay_method='T')),
        )
    week_cash = week.aggregate(
        total=Sum('amount'),
        total_cash=Sum('amount', filter=Q(pay_method='C')),
        total_card=Sum('amount', filter=Q(pay_method='V')),
        total_transfer=Sum('amount', filter=Q(pay_method='T')),
        )
    month_cash = month.aggregate(
        total=Sum('amount'),
        total_cash=Sum('amount', filter=Q(pay_method='C')),
        total_card=Sum('amount', filter=Q(pay_method='V')),
        total_transfer=Sum('amount', filter=Q(pay_method='T')),
        )

    bank_movements = BankMovement.objects.all()[:10]
    expenses = Expense.objects.filter(pay_method='C').aggregate(
        total_cash=Sum('amount')
    )
    if not expenses['total_cash']:
        expenses['total_cash'] = 0
    all_time_deposit = BankMovement.objects.aggregate(total_cash=Sum('amount'))
    if not all_time_deposit['total_cash']:
        all_time_deposit['total_cash'] = 0
    if not all_time_cash['total_cash']:
        all_time_cash['total_cash'] = 0
    balance = all_time_deposit['total_cash'] - all_time_cash['total_cash']
    balance = balance + expenses['total_cash']

    cur_user = request.user
    now = datetime.now()
    session = Timetable.active.get(user=request.user)

    view_settings = {'user': cur_user,
                     'now': now,
                     'session': session,
                     'today': today,
                     'week': week,
                     'month': month,
                     'today_cash': today_cash,
                     'week_cash': week_cash,
                     'month_cash': month_cash,
                     'bank_movements': bank_movements,
                     'all_time_cash': all_time_cash,
                     'all_time_deposit': all_time_deposit,
                     'balance': balance,
                     'version': settings.VERSION,
                     'title': 'TrapuZarrak · Facturas',
                     }

    return render(request, 'tz/invoices.html', view_settings)


@login_required
@timetable_required
def kanban(request):
    """Display a kanban view for orders."""
    if request.GET.get('unconfirmed', None):
        context = CommonContexts.kanban(confirmed=False)
    else:
        context = CommonContexts.kanban()
    context['cur_user'] = request.user
    context['now'] = datetime.now()
    context['session'] = Timetable.active.get(user=request.user)
    context['version'] = settings.VERSION
    context['title'] = 'TrapuZarrak · Vista Kanban'

    return render(request, 'tz/kanban.html', context)


# Object views
@login_required
@timetable_required
def order_view(request, pk):
    """Show all details for an specific order."""
    order = get_object_or_404(Order, pk=pk)

    # Redirect to express order
    if order.customer.name == 'express':
        return redirect(reverse('order_express', args=[order.pk]))

    tab = request.GET.get('tab', None)
    if not tab:
        tab = 'items'  # active tab to show on reload, default
    if tab not in ('main', 'tasks', 'items'):
        return HttpResponseServerError('Tab not valid')

    # Now, process the POST methods
    errors = list()
    if request.method == 'POST':
        action = request.POST.get('action', None)
        if action == 'add-project':
            if not order.create_todoist():
                errors.append('Couldn\'t create project on todoist, did it ' +
                              'already exist?')
            tab = 'tasks'
        elif action == 'archive-project':
            if not order.archive():
                errors.append('Couldn\'t archive project, maybe it was ' +
                              'already archived or just didn\'t exist')
            tab = 'tasks'
        elif action == 'unarchive-project':
            if not order.unarchive():
                errors.append('Couldn\'t unarchive project, maybe it was ' +
                              'already unarchived or just didn\'t exist')
            tab = 'tasks'
        elif action == 'deliver-order':
            order.deliver()
            tab = 'main'
        else:
            return HttpResponseServerError('Action was not recognized')

    order = get_object_or_404(Order, pk=pk)

    # Todoist integration, out from the common elements for performance.
    tasks = order.tasks()
    archived = order.is_archived()

    common_vars = CommonContexts.order_details(request=request, pk=pk)
    curr_vars = {'tab': tab,
                 'errors': errors,
                 'tasks': tasks,
                 'project_id': order.t_pid,
                 'archived': archived, }
    view_settings = {**common_vars, **curr_vars}

    return render(request, 'tz/order_view.html', view_settings)


@login_required
@timetable_required
def order_express_view(request, pk):
    """Create a new quick checkout."""
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        cp = request.POST.get('cp', None)
        customer_pk = request.POST.get('customer', None)
        if cp:
            c = Customer.objects.get_or_create(
                name='express', city='server', phone=0, cp=cp,
                notes='AnnonymousUserAutmaticallyCreated')
            order.customer = c[0]
            order.save()
        elif customer_pk:
            c = get_object_or_404(Customer, pk=customer_pk)
            order.customer = c
            order.ref_name = 'Venta express con arreglo'
            order.save()
        else:
            raise Http404('Something went wrong with the request.')

    # Redirect regular orders
    if order.customer.name != 'express':
        return redirect(reverse('order_view', args=[order.pk]))

    customers = Customer.objects.exclude(name='express')
    customers = customers.exclude(provider=True)
    items = OrderItem.objects.filter(reference=order)
    available_items = Item.objects.all()[:10]
    already_invoiced = Invoice.objects.filter(reference=order)

    cur_user = request.user
    now = datetime.now()
    session = Timetable.active.get(user=request.user)

    view_settings = {'order': order,
                     'customers': customers,
                     'user': cur_user,
                     'now': now,
                     'session': session,
                     'item_types': settings.ITEM_TYPE[1:],
                     'items': items,
                     'available_items': available_items,
                     'invoiced': already_invoiced,
                     'version': settings.VERSION,
                     'title': 'TrapuZarrak · Venta express',
                     'placeholder': 'Busca un nombre',
                     'search_on': 'items',

                     # CRUD Actions
                     'btn_title_add': 'Nueva prenda',
                     'js_action_add': 'object-item-add',
                     'js_action_delete': 'order-express-item-delete',
                     'js_data_pk': '0',
                     }
    return render(request, 'tz/order_express.html', view_settings)


@login_required
@timetable_required
def customer_view(request, pk):
    """Display details for an especific customer."""
    customer = get_object_or_404(Customer, pk=pk)
    orders = Order.objects.filter(customer=customer)
    active = orders.exclude(status__in=[7, 8]).order_by('delivery')
    delivered = orders.filter(status=7).order_by('delivery')
    cancelled = orders.filter(status=8).order_by('delivery')

    # Evaluate pending orders
    pending = orders.filter(delivery__gte=date(2019, 1, 1))
    pending = pending.filter(invoice__isnull=True)

    cur_user = request.user
    now = datetime.now()
    session = Timetable.active.get(user=request.user)

    view_settings = {'customer': customer,
                     'orders_active': active,
                     'orders_delivered': delivered,
                     'orders_cancelled': cancelled,
                     'pending': pending,
                     'orders_made': orders.count(),
                     'user': cur_user,
                     'now': now,
                     'session': session,
                     'version': settings.VERSION,
                     'title': 'TrapuZarrak · Ver cliente',
                     }
    return render(request, 'tz/customer_view.html', view_settings)


@login_required
@timetable_required
def pqueue_manager(request):
    """Display the production queue and edit it."""
    available = OrderItem.objects.exclude(reference__status__in=[7, 8])
    available = available.exclude(element__name__iexact='Descuento')
    available = available.exclude(stock=True).filter(pqueue__isnull=True)
    available = available.exclude(element__foreing=True)
    available = available.order_by('reference__delivery',
                                   'reference__ref_name')
    pqueue = PQueue.objects.select_related('item__reference')
    pqueue = pqueue.exclude(item__reference__status__in=[7, 8])
    pqueue_completed = pqueue.filter(score__lt=0)
    pqueue_active = pqueue.filter(score__gt=0)
    i_relax = settings.RELAX_ICONS[randint(0, len(settings.RELAX_ICONS) - 1)]

    cur_user = request.user
    now = datetime.now()
    session = Timetable.active.get(user=request.user)

    view_settings = {'available': available,
                     'active': pqueue_active,
                     'completed': pqueue_completed,
                     'i_relax': i_relax,
                     'user': cur_user,
                     'now': now,
                     'session': session,
                     'version': settings.VERSION,
                     'title': 'TrapuZarrak · Cola de producción',
                     }
    return render(request, 'tz/pqueue_manager.html', view_settings)


@login_required
@timetable_required
def pqueue_tablet(request):
    """Tablet view of pqueue."""
    pqueue = PQueue.objects.select_related('item__reference')
    pqueue = pqueue.exclude(item__reference__status__in=[7, 8])
    pqueue_completed = pqueue.filter(score__lt=0)
    pqueue_active = pqueue.filter(score__gt=0)
    i_relax = settings.RELAX_ICONS[randint(0, len(settings.RELAX_ICONS) - 1)]

    cur_user = request.user
    now = datetime.now()
    session = Timetable.active.get(user=request.user)

    view_settings = {'active': pqueue_active,
                     'completed': pqueue_completed,
                     'i_relax': i_relax,
                     'user': cur_user,
                     'now': now,
                     'session': session,
                     'version': settings.VERSION,
                     'title': ('TrapuZarrak · Cola de producción' +
                               '(vista tablet)'),
                     }
    return render(request, 'tz/pqueue_tablet.html', view_settings)


# Generic views
class TimetableList(ListView):
    model = Timetable
    template_name = 'tz/timetable_list.html'
    context_object_name = 'timetables'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        """Customize the list of times by showing only user's ones."""
        query = Timetable.objects.filter(user=self.request.user)
        return query.order_by('-start')[:10]

    def get_context_data(self, **kwargs):
        """Add some extra variables to make the view consistent with base."""
        context = super().get_context_data(**kwargs)
        context['session'] = self.get_queryset()[0]
        return context


# Ajax powered views
class Actions(View):
    """Unify all the AJAX actions in a single view.

    With this view we'll be able to edit, upload & delete files, add comments
    or close orders. While let CRUD with customers.
    Get method should load the correct template for the modal, while POST
    method processes the update.
    """

    def get(self, request):
        """Return a JsonResponse with the data to load modal.

        This method returns a template, sometimes with a form, for the modal
        depending the action given. The template is returned as string using
        render_to_string method.

        Every action must have a valid pk, but order-add, customer-add & logout
        otherwise an error is raised(404).
        """
        data = dict()
        pk = self.request.GET.get('pk', None)
        action = self.request.GET.get('action', None)

        if not pk or not action:
            raise ValueError('Unexpected GET data')

        """ Add actions """
        # Add order (GET)
        if action == 'order-add':
            form = OrderForm()
            context = {'form': form,
                       'modal_title': 'Añadir Pedido',
                       'pk': '0',
                       'action': 'order-new',
                       'submit_btn': 'Añadir',
                       'custom_form': 'includes/custom_forms/order.html',
                       }
            template = 'includes/regular_form.html'

        # Add order from customer (GET)
        elif action == 'order-from-customer':
            customer = get_object_or_404(Customer, pk=pk)
            form = OrderForm(initial={'customer': customer})
            context = {'form': form,
                       'modal_title': 'Añadir Pedido',
                       'pk': '0',
                       'action': 'order-new',
                       'submit_btn': 'Añadir',
                       'custom_form': 'includes/custom_forms/order.html',
                       }
            template = 'includes/regular_form.html'

        # Add express order (GET)
        elif action == 'order-express-add':
            custom_form = 'includes/custom_forms/order_express.html'
            context = {'modal_title': 'Nueva venta · Añadir CP',
                       'pk': '0',
                       'action': 'order-express-add',
                       'submit_btn': 'Abrir venta',
                       'custom_form': custom_form,
                       }
            template = 'includes/regular_form.html'

        # Add customer (GET)
        elif action == 'customer-add':
            form = CustomerForm()
            context = {'form': form,
                       'modal_title': 'Añadir Cliente',
                       'pk': '0',
                       'action': 'customer-new',
                       'submit_btn': 'Añadir',
                       'custom_form': 'includes/custom_forms/customer.html'
                       }
            template = 'includes/regular_form.html'

        # Add item object (GET)
        elif action == 'object-item-add':
            form = ItemForm()
            context = {'form': form,
                       'modal_title': 'Añadir prenda',
                       'pk': '0',
                       'action': 'object-item-add',
                       'submit_btn': 'Añadir',
                       'custom_form': 'includes/custom_forms/object_item.html',
                       }
            template = 'includes/regular_form.html'

        # Send item to order (GET)
        elif action == 'send-to-order':
            custom_form = 'includes/custom_forms/send_to_order.html'
            item = get_object_or_404(Item, pk=pk)
            context = {'modal_title': 'Añadir prenda a pedido',
                       'pk': pk,
                       'item': item,
                       'order_pk': self.request.GET.get('aditionalpk', None),
                       'action': 'send-to-order',
                       'submit_btn': 'Añadir a pedido',
                       'custom_form': custom_form,
                       }
            template = 'includes/regular_form.html'

        # Send to order express (GET)
        elif action == 'send-to-order-express':
            custom_form = 'includes/custom_forms/send_to_order.html'
            item = get_object_or_404(Item, pk=pk)
            context = {'modal_title': 'Enviar prenda a ticket',
                       'pk': pk,
                       'item': item,
                       'order_pk': self.request.GET.get('aditionalpk', None),
                       'action': 'send-to-order-express',
                       'submit_btn': 'Añadir a ticket',
                       'custom_form': custom_form,
                       }
            template = 'includes/regular_form.html'

        # Add order item (GET)
        elif action == 'order-item-add':
            order = get_object_or_404(Order, pk=pk)
            form = OrderItemForm()
            items = Item.objects.all()
            context = {'form': form,
                       'order': order,
                       'items': items,
                       'modal_title': 'Añadir prenda',
                       'pk': order.pk,
                       'action': 'order-item-add',
                       'submit_btn': 'Añadir',
                       'custom_form': 'includes/custom_forms/order_item.html',
                       }
            template = 'includes/regular_form.html'

        # Add a comment (GET)
        elif action == 'order-add-comment':
            order = get_object_or_404(Order, pk=pk)
            form = CommentForm()
            context = {'form': form,
                       'modal_title': 'Añadir Comentario',
                       'pk': order.pk,
                       'action': 'order-comment',
                       'submit_btn': 'Añadir',
                       }
            template = 'includes/regular_form.html'

        # Issue invoice (GET)
        elif action == 'ticket-to-invoice':
            order = get_object_or_404(Order, pk=pk)
            already_invoiced = Invoice.objects.filter(reference=order)
            items = OrderItem.objects.filter(reference=order)
            total = items.aggregate(
                total=Sum(F('qty') * F('price'), output_field=DecimalField()))
            form = InvoiceForm()
            context = {'form': form,
                       'items': items,
                       'order': order,
                       'total': total,
                       'invoiced': already_invoiced,
                       'modal_title': 'Facturar',
                       'pk': order.pk,
                       'action': 'ticket-to-invoice',
                       'submit_btn': 'Facturar',
                       'custom_form': 'includes/custom_forms/invoice.html',
                       }
            template = 'includes/regular_form.html'

        # Edit the order (GET)
        elif action == 'order-edit':
            order = get_object_or_404(Order, pk=pk)
            form = OrderForm(instance=order)
            context = {'form': form,
                       'modal_title': 'Editar Pedido',
                       'pk': order.pk,
                       'action': 'order-edit',
                       'submit_btn': 'Guardar',
                       'custom_form': 'includes/custom_forms/order.html',
                       }
            template = 'includes/regular_form.html'

        # Add a prepaid (GET)
        elif action == 'order-edit-add-prepaid':
            order = get_object_or_404(Order, pk=pk)
            email = False
            if order.customer.email:
                email = True
            form = OrderForm(instance=order)
            custom_form = 'includes/custom_forms/order_add_prepaid.html'
            context = {'form': form,
                       'order': order,
                       'modal_title': 'Añadir Prepago',
                       'pk': order.pk,
                       'email': email,
                       'action': 'order-edit-add-prepaid',
                       'submit_btn': 'Añadir',
                       'custom_form': custom_form,
                       }
            template = 'includes/regular_form.html'

        # Edit the date (GET)
        elif action == 'order-edit-date':
            order = get_object_or_404(Order, pk=pk)
            form = EditDateForm(instance=order)
            custom_form = 'includes/custom_forms/edit_date.html'
            context = {'form': form,
                       'modal_title': 'Actualizar fecha de entrega',
                       'pk': order.pk,
                       'action': 'order-edit-date',
                       'submit_btn': 'Guardar',
                       'custom_form': custom_form,
                       }
            template = 'includes/regular_form.html'

        # Edit customer (GET)
        elif action == 'customer-edit':
            customer = get_object_or_404(Customer, pk=pk)
            form = CustomerForm(instance=customer)
            context = {'form': form,
                       'modal_title': 'Editar Cliente',
                       'pk': customer.pk,
                       'action': 'customer-edit',
                       'submit_btn': 'Guardar',
                       'custom_form': 'includes/custom_forms/customer.html'
                       }
            template = 'includes/regular_form.html'

        # Edit Item Object (GET)
        elif action == 'object-item-edit':
            item = get_object_or_404(Item, pk=pk)
            form = ItemForm(instance=item)
            context = {'form': form,
                       'modal_title': 'Editar prenda',
                       'pk': item.pk,
                       'action': 'object-item-edit',
                       'submit_btn': 'Guardar',
                       'custom_form': 'includes/custom_forms/object_item.html'
                       }
            template = 'includes/regular_form.html'

        # Edit order item (GET)
        elif action == 'order-item-edit':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            form = OrderItemForm(instance=item)
            context = {'form': form,
                       'item': item,
                       'modal_title': 'Editar prenda',
                       'pk': item.pk,
                       'action': 'order-item-edit',
                       'submit_btn': 'Guardar',
                       'custom_form': 'includes/custom_forms/order_item.html',
                       }
            template = 'includes/regular_form.html'

        # Edit times on pqueue (GET)
        elif action == 'pqueue-add-time':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            form = OrderItemForm(instance=item)
            context = {'form': form,
                       'item': item,
                       'modal_title': 'Editar tiempos',
                       'pk': item.pk,
                       'action': 'pqueue-add-time',
                       'submit_btn': 'Guardar',
                       '2nd_sbt_value': 'save-and-archive',
                       '2nd_sbt_btn': 'Guardar y completar',
                       'custom_form': 'includes/custom_forms/add_times.html',
                       }
            template = 'includes/regular_form.html'

        # Delete item objects (GET)
        elif action == 'object-item-delete':
            item = get_object_or_404(Item, pk=pk)
            context = {'modal_title': 'Eliminar prenda',
                       'msg': 'Realmente borrar la prenda?',
                       'pk': item.pk,
                       'action': 'object-item-delete',
                       'submit_btn': 'Sí, borrar'}
            template = 'includes/delete_confirmation.html'

        # Delete order item (GET)
        elif action == 'order-item-delete':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            context = {'modal_title': 'Eliminar prenda',
                       'msg': 'Realmente borrar la prenda?',
                       'pk': item.pk,
                       'action': 'order-item-delete',
                       'submit_btn': 'Sí, borrar'}
            template = 'includes/delete_confirmation.html'

        # delete order express (GET)
        elif action == 'order-express-delete':
            order = get_object_or_404(Order, pk=pk)
            context = {'modal_title': 'Eliminar ticket express',
                       'msg': 'Quieres realmente descartar el ticket?',
                       'pk': order.pk,
                       'action': 'order-express-delete',
                       'submit_btn': 'Sí, descartar'}
            template = 'includes/delete_confirmation.html'

        # Delete order express item (GET)
        elif action == 'order-express-item-delete':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            context = {'modal_title': 'Eliminar prenda',
                       'msg': 'Realmente borrar la prenda?',
                       'pk': item.pk,
                       'action': 'order-express-item-delete',
                       'submit_btn': 'Sí, borrar'}
            template = 'includes/delete_confirmation.html'

        # Delete Customer (GET)
        elif action == 'customer-delete':
            customer = get_object_or_404(Customer, pk=pk)
            msg = """
            <div class="d-flex"><div class="alert alert-warning" role="alert">
            <i class="fas fa-exclamation-triangle text-danger"></i>
            <strong>Atención!</strong><br>
            Realmente quieres eliminar el cliente?<br>
            Esto eliminará también todos sus pedidos en la base de datos.
            Esta acción no se puede deshacer.</div></div>
            """
            context = {'modal_title': 'Eliminar cliente',
                       'msg': msg,
                       'pk': customer.pk,
                       'action': 'customer-delete',
                       'submit_btn': 'Sí, quiero eliminarlo'}
            template = 'includes/delete_confirmation.html'

        # View a invoiced ticket (GET)
        elif action == 'view-ticket':
            invoice = get_object_or_404(Invoice, pk=pk)
            items = OrderItem.objects.filter(reference=invoice.reference)
            order = Order.objects.get(pk=pk)
            context = {'items': items, 'order': order, }
            template = 'includes/invoiced_ticket.html'

        else:
            raise NameError('Action was not recogniced', action)

        data['html'] = render_to_string(template, context, request=request)

        """
        Test stuff. Since it's not very straightforward extract this data
        from render_to_string() method, we'll pass them as keys in JSON but
        just for testing purposes.
        """
        if request.GET.get('test'):
            data['template'] = template
            add_to_context = []
            for k in context:
                add_to_context.append(k)
            data['context'] = add_to_context

        return JsonResponse(data)

    def post(self, request):
        """Parse the request provided by AJAX.

        Returns can be: JsonResponse(sometimes with 'reload' order) or redirect
        """
        data = dict()
        pk = self.request.POST.get('pk', None)
        action = self.request.POST.get('action', None)
        template, context = False, False

        if not pk or not action:
            raise ValueError('POST data was poor')

        # Add Order (POST)
        if action == 'order-new':
            form = OrderForm(request.POST)
            if form.is_valid():
                order = form.save(commit=False)
                order.creation = timezone.now()
                order.user = request.user
                order.save()
                data['redirect'] = (reverse('order_view', args=[order.pk]))
                data['form_is_valid'] = True
            else:
                data['form_is_valid'] = False
                context = {'form': form,
                           'modal_title': 'Añadir Pedido',
                           'pk': '0',
                           'action': 'order-new',
                           'submit_btn': 'Añadir',
                           'custom_form': 'includes/custom_forms/order.html',
                           }
                template = 'includes/regular_form.html'

        # Add express order
        elif action == 'order-express-add':
            customer, created = Customer.objects.get_or_create(
                name='express', city='server', phone=0,
                cp=self.request.POST.get('cp'),
                notes='AnnonymousUserAutmaticallyCreated'
            )
            order = Order.objects.create(
                user=request.user, customer=customer, ref_name='Quick',
                delivery=date.today(), status=7, budget=0, prepaid=0,
            )

            data['redirect'] = (reverse('order_express', args=[order.pk]))
            data['form_is_valid'] = True

        # Add Customer (POST)
        elif action == 'customer-new':
            form = CustomerForm(request.POST)
            if form.is_valid():
                customer = form.save(commit=False)
                customer.creation = timezone.now()
                customer.save()
                data['form_is_valid'] = True
                data['reload'] = True
                return JsonResponse(data)
            else:
                data['form_is_valid'] = False
                context = {'form': form,
                           'modal_title': 'Añadir Cliente',
                           'pk': '0',
                           'action': 'customer-new',
                           'submit_btn': 'Añadir',
                           'custom_form': 'includes/custom_forms/customer.html'
                           }
                template = 'includes/regular_form.html'

        # Add comment (POST)
        elif action == 'order-comment':
            order = get_object_or_404(Order, pk=pk)
            form = CommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.creation = timezone.now()
                comment.user = request.user
                comment.reference = order
                comment.save()
                data['form_is_valid'] = True
                data['html_id'] = '#comment-list'
                comments = Comment.objects.filter(reference=order)
                comments = comments.order_by('-creation')
                context = {'comments': comments}
                template = 'includes/comment_list.html'
            else:
                data['form_is_valid'] = False
                context = {'form': form,
                           'modal_title': 'Añadir Comentario',
                           'pk': '0',
                           'action': 'order-comment',
                           'submit_btn': 'Añadir',
                           }
                template = 'includes/regular_form.html'

        # Mark comment as read (POST)
        elif action == 'comment-read':
            comment = get_object_or_404(Comment, pk=pk)
            comment.read = True
            comment.save()
            data['redirect'] = (reverse('main'))
            data['form_is_valid'] = True

        # Add new item Objects (POST)
        elif action == 'object-item-add':
            form = ItemForm(request.POST)
            if form.is_valid():
                add_item = form.save()
                items = Item.objects.all()[:11]
                data['html_id'] = '#item-selector'
                data['form_is_valid'] = True
                context = {'item_types': settings.ITEM_TYPE[1:],
                           'available_items': items,
                           'js_action_edit': 'object-item-edit',
                           'js_action_delete': 'object-item-delete',
                           'js_action_send_to': 'send-to-order',
                           }
                template = 'includes/item_selector.html'
            else:
                data['form_is_valid'] = False
                custom_form = 'includes/custom_forms/object_item.html'
                context = {'form': form,
                           'modal_title': 'Añadir prenda',
                           'pk': '0',
                           'action': 'object-item-add',
                           'submit_btn': 'Añadir',
                           'custom_form': custom_form,
                           }
                template = 'includes/regular_form.html'

        # Send item to order (POST)
        elif action == 'send-to-order':
            item = get_object_or_404(Item,
                                     pk=self.request.POST.get('pk', None))
            order = get_object_or_404(
                Order, pk=self.request.POST.get('order-pk', None))

            # Test isStock (convert to bool)
            is_stock = self.request.POST.get('isStock', None)
            if is_stock:
                is_stock = True
            else:
                is_stock = False

            # Now create OrderItem
            price = self.request.POST.get('custom-price', None)
            qty = self.request.POST.get('item-qty', 1)
            if price is '0':
                price = None
            OrderItem.objects.create(
                element=item, reference=order, qty=qty, price=price,
                stock=is_stock, fit=False)

            # Set default price (if case)
            set_price = self.request.POST.get('set-default-price', None)
            if set_price:
                item.price = price
                item.full_clean()
                item.save()

            # Context for the view
            items = OrderItem.objects.filter(reference=order)
            data['form_is_valid'] = True
            data['html_id'] = '#quick-list'
            context = {'items': items,
                       'order': order,

                       # CRUD Actions
                       'js_action_edit': 'order-item-edit',
                       'js_action_delete': 'order-item-delete',
                       'js_data_pk': order.pk,
                       }
            template = 'includes/item_quick_list.html'

        # Send item to order express (POST)
        elif action == 'send-to-order-express':
            item = get_object_or_404(Item,
                                     pk=self.request.POST.get('item-pk', None))
            order = get_object_or_404(
                Order, pk=self.request.POST.get('order-pk', None)
                )

            # Get the customers for dropdown
            customers = Customer.objects.exclude(name='express')
            customers = customers.exclude(provider=True)

            # Now create OrderItem
            price = self.request.POST.get('custom-price', None)
            qty = self.request.POST.get('item-qty', 1)
            if price is '0':
                price = None
            OrderItem.objects.create(
                element=item, reference=order, qty=qty, price=price,
                stock=True, fit=False)

            # Set default price (if case)
            set_price = self.request.POST.get('set-default-price', None)
            if set_price:
                item.price = price
                item.full_clean()
                item.save()

            # Context for the view
            items = OrderItem.objects.filter(reference=order)
            data['form_is_valid'] = True
            data['html_id'] = '#ticket'
            total = items.aggregate(
                total=Sum(F('qty') * F('price'), output_field=DecimalField()))
            context = {'items': items,
                       'total': total,
                       'order': order,
                       'customers': customers,

                       # CRUD Actions
                       'js_action_delete': 'order-express-item-delete',
                       'js_data_pk': '0',
                       }
            template = 'includes/ticket.html'

        # Attach item to order (POST)
        elif action == 'order-item-add':
            order = get_object_or_404(Order, pk=pk)
            form = OrderItemForm(request.POST)
            if form.is_valid():
                add_item = form.save(commit=False)
                add_item.reference = order
                add_item.save()
                items = OrderItem.objects.filter(reference=order)
                template = 'includes/order_details.html'
                context = {'items': items,
                           'order': order,
                           'btn_title_add': 'Añadir prenda',
                           'js_action_add': 'order-item-add',
                           'js_action_edit': 'order-item-edit',
                           'js_action_delete': 'order-item-delete',
                           'js_data_pk': order.pk,
                           }

                data['form_is_valid'] = True
                data['html_id'] = '#order-details'
            else:
                context = {'order': order, 'form': form}
                template = 'includes/order_details.html'
                data['form_is_valid'] = False

        elif action == 'ticket-to-invoice':
            order = get_object_or_404(Order, pk=pk)
            items = OrderItem.objects.filter(reference=order)
            total = items.aggregate(
                total=Sum(F('qty') * F('price'), output_field=DecimalField()))
            form = InvoiceForm(request.POST)
            if form.is_valid():
                invoice = form.save(commit=False)
                invoice.reference = order
                invoice.save()
                data['redirect'] = (reverse('invoiceslist'))
                data['form_is_valid'] = True
            else:
                data['form_is_valid'] = False
                context = {'form': form,
                           'items': items,
                           'order': order,
                           'total': total,
                           'modal_title': 'Facturar',
                           'pk': order.pk,
                           'action': 'ticket-to-invoice',
                           'submit_btn': 'Facturar',
                           'custom_form': 'includes/custom_forms/invoice.html',
                           }
                template = 'includes/regular_form.html'

        # Edit order (POST)
        elif action == 'order-edit':
            order = get_object_or_404(Order, pk=pk)
            form = OrderForm(request.POST, instance=order)
            if form.is_valid():
                form.save()
                data['form_is_valid'] = True
                data['reload'] = True
                return JsonResponse(data)
            else:
                data['form_is_valid'] = False
                context = {'form': form,
                           'modal_title': 'Editar Pedido',
                           'pk': order.pk,
                           'action': 'order-edit',
                           'submit_btn': 'Guardar',
                           'custom_form': 'includes/custom_forms/order.html',
                           }
                template = 'includes/regular_form.html'

        # Add prepaid (POST)
        elif action == 'order-edit-add-prepaid':
            order = get_object_or_404(Order, pk=pk)
            form = OrderForm(request.POST, instance=order)
            if form.is_valid():
                form.save()

                # Now email settings
                if order.customer.email and self.request.POST.get('send-mail'):
                    subject = 'Tu comprobante de depósito en Trapuzarrak'
                    from_email = settings.CONTACT_EMAIL
                    to = [order.customer.email, ]
                    bcc = [config('EMAIL_BCC'), ]
                    txt = ('Kaixo %s:\n\n' +
                           'Oraitxe bertan %s€-ko aurre ordainketa egin ' +
                           'dozu eskaera baten kontuan.\n' +
                           '00%s da zure eskaeraren erreferentzia zenbakia, ' +
                           'ahalik eta behin prestatu egotea, zugaz ' +
                           'kontaktuan jarriko gara.\n\n' +
                           'Eskerrik asko zure kofidantzagaitik.\n\n' +
                           'Trapuzarraen taldea.\n' +
                           '\n---\n\n' +
                           'Acabas de dejarnos un depósito en efectivo de %s' +
                           '€ a cuenta de un encargo que has realizado.\n' +
                           'La referencia de tu pedido es %s, en cuanto lo ' +
                           'tengamos listo nos pondremos en contacto ' +
                           'contigo.\n\n' +
                           'Gracias por tu confianza.\n\n' +
                           'El equipo de Trapuzarrak.\n\n' +
                           '%s\n%s') % (order.customer.email_name(),
                                        order.prepaid, order.pk,
                                        order.prepaid, order.pk,
                                        settings.CONTACT_EMAIL,
                                        settings.CONTACT_PHONE)
                    msg = EmailMultiAlternatives(
                        subject, txt, from_email, to=to, bcc=bcc)
                    msg.send()

                data['form_is_valid'] = True
                data['reload'] = True
                return JsonResponse(data)
            else:
                data['form_is_valid'] = False
                custom_form = 'includes/custom_forms/order_add_prepaid.html'
                if order.customer.email:
                    email = True
                context = {'form': form,
                           'order': order,
                           'modal_title': 'Añadir prepago',
                           'pk': order.pk,
                           'email': email,
                           'action': 'order-edit-add-prepaid',
                           'submit_btn': 'Guardar',
                           'custom_form': custom_form,
                           }
                template = 'includes/regular_form.html'

        # Edit date (POST)
        elif action == 'order-edit-date':
            order = get_object_or_404(Order, pk=pk)
            form = EditDateForm(request.POST, instance=order)
            if form.is_valid():
                form.save()
                data['form_is_valid'] = True
                data['reload'] = True
                return JsonResponse(data)
            else:
                data['form_is_valid'] = False
                custom_form = 'includes/custom_forms/edit_date.html'
                context = {'form': form,
                           'modal_title': 'Actualizar fecha de entrega',
                           'pk': order.pk,
                           'action': 'order-edit-date',
                           'submit_btn': 'Guardar',
                           'custom_form': custom_form,
                           }
                template = 'includes/regular_form.html'

        # Edit Customer (POST)
        elif action == 'customer-edit':
            customer = get_object_or_404(Customer, pk=pk)
            form = CustomerForm(request.POST, instance=customer)
            if form.is_valid():
                form.save()
                data['form_is_valid'] = True
                data['reload'] = True
                return JsonResponse(data)
            else:
                data['form_is_valid'] = False
                context = {'form': form,
                           'modal_title': 'Editar Cliente',
                           'pk': customer.pk,
                           'action': 'customer-edit',
                           'submit_btn': 'Guardar',
                           'custom_form': 'includes/custom_forms/customer.html'
                           }
                template = 'includes/regular_form.html'

        # Edit item objects (POST)
        elif action == 'object-item-edit':
            item = get_object_or_404(Item, pk=pk)
            form = ItemForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                items = Item.objects.all()[:11]
                data['html_id'] = '#item-selector'
                data['form_is_valid'] = True
                context = {'item_types': settings.ITEM_TYPE[1:],
                           'available_items': items,
                           'js_action_edit': 'object-item-edit',
                           'js_action_delete': 'object-item-delete',
                           'js_action_send_to': 'send-to-order',
                           }
                template = 'includes/item_selector.html'
            else:
                data['form_is_valid'] = False
                custom_form = 'includes/custom_forms/object_item.html'
                context = {'form': form,
                           'modal_title': 'Editar prenda',
                           'pk': item.pk,
                           'action': 'object-item-edit',
                           'submit_btn': 'Guardar',
                           'custom_form': custom_form,
                           }
                template = 'includes/regular_form.html'

        # Edit order item (POST)
        elif action == 'order-item-edit':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            order = item.reference
            form = OrderItemForm(request.POST, instance=item)
            items = OrderItem.objects.filter(reference=order)
            if form.is_valid():
                context = {'items': items,
                           'order': order,
                           'btn_title_add': 'Añadir prenda',
                           'js_action_add': 'order-item-add',
                           'js_action_edit': 'order-item-edit',
                           'js_action_delete': 'order-item-delete',
                           'js_data_pk': order.pk,
                           }
                template = 'includes/item_quick_list.html'
                form.save()
                data['form_is_valid'] = True
                data['html_id'] = '#quick-list'
            else:
                custom_form = 'includes/custom_forms/order_item.html'
                context = {'form': form,
                           'item': item,
                           'modal_title': 'Editar prenda',
                           'pk': item.reference.pk,
                           'action': 'order-item-edit',
                           'submit_btn': 'Guardar',
                           'custom_form': custom_form,
                           }
                template = 'includes/regular_form.html'
                data['form_is_valid'] = False

        # Add times from pqueue (POST)
        elif action == 'pqueue-add-time':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            form = AddTimesForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                data['form_is_valid'] = True
                data['html_id'] = '#pqueue-list-tablet'
                template = 'includes/pqueue_tablet.html'
                sbt_2nd = request.POST.get('sbt_action', None)
                if sbt_2nd == 'save-and-archive':
                    pqueue_item = get_object_or_404(PQueue, pk=item.pk)
                    pqueue_item.complete()
                pqueue = PQueue.objects.select_related('item__reference')
                pqueue = pqueue.exclude(item__reference__status__in=[7, 8])
                pqueue_completed = pqueue.filter(score__lt=0)
                pqueue_active = pqueue.filter(score__gt=0)
                context = {'active': pqueue_active,
                           'completed': pqueue_completed,
                           }
            else:
                custom_form = 'includes/custom_forms/add_times.html'
                context = {'form': form,
                           'item': item,
                           'modal_title': 'Editar tiempos',
                           'pk': item.pk,
                           'action': 'pqueue-add-time',
                           'submit_btn': 'Guardar',
                           'custom_form': custom_form,
                           }
                template = 'includes/regular_form.html'
                data['form_is_valid'] = False

                item = OrderItem.objects.select_related('reference').get(pk=pk)
                form = OrderItemForm(instance=item)

        # Update status (POST)
        elif action == 'update-status':
            status = self.request.POST.get('status', None)
            order = get_object_or_404(Order, pk=pk)
            order.status = status
            try:
                order.full_clean()
            except ValidationError:
                data['form_is_valid'] = False
                data['reload'] = True
                return JsonResponse(data)
            else:
                if status == '7':
                    order.delivery = date.today()
                order.save()
                data['form_is_valid'] = True
                data['html_id'] = '#order-status'
                template = 'includes/order_status.html'
                context = {'order': order}

        # Delete object Item
        elif action == 'object-item-delete':
            item = get_object_or_404(Item, pk=pk)
            try:
                item.delete()
            except IntegrityError:
                data['form_is_valid'] = False
                # TODO: data['error'] = process error msg
                context = {'modal_title': 'Eliminar prenda',
                           'msg': 'Realmente borrar la prenda?',
                           'pk': item.pk,
                           'action': 'object-item-delete',
                           'submit_btn': 'Sí, borrar'}
                template = 'includes/delete_confirmation.html'
            else:
                data['form_is_valid'] = True
                items = Item.objects.all()[:11]
                data['html_id'] = '#item-selector'
                context = {'item_types': settings.ITEM_TYPE[1:],
                           'available_items': items,
                           'js_action_edit': 'object-item-edit',
                           'js_action_delete': 'object-item-delete',
                           'js_action_send_to': 'send-to-order',
                           }
                template = 'includes/item_selector.html'

        # Delete item (POST)
        elif action == 'order-item-delete':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            order = item.reference
            items = OrderItem.objects.filter(reference=order)
            item.delete()
            data['form_is_valid'] = True
            data['html_id'] = '#quick-list'
            context = {'items': items,
                       'order': order,
                       'btn_title_add': 'Añadir prenda',
                       'js_action_add': 'order-item-add',
                       'js_action_edit': 'order-item-edit',
                       'js_action_delete': 'order-item-delete',
                       'js_data_pk': order.pk,
                       }
            template = 'includes/item_quick_list.html'

        # Delete order express (POST)
        elif action == 'order-express-delete':
            order = get_object_or_404(Order, pk=pk)
            order.delete()
            data['redirect'] = (reverse('main'))
            data['form_is_valid'] = True

        # Delete items on order express (POST)
        elif action == 'order-express-item-delete':
            item = get_object_or_404(OrderItem, pk=pk)
            order = item.reference
            items = OrderItem.objects.filter(reference=order)
            item.delete()
            data['form_is_valid'] = True
            data['html_id'] = '#ticket'
            total = items.aggregate(
                total=Sum(F('qty') * F('price'), output_field=DecimalField()))
            context = {'items': items,
                       'total': total,
                       'order': order,

                       # CRUD Actions
                       # 'js_action_edit': 'order-express-item-edit',
                       'js_action_delete': 'order-express-item-delete',
                       'js_data_pk': '0',
                       }
            template = 'includes/ticket.html'

        # Delete customer (POST)
        elif action == 'customer-delete':
            customer = get_object_or_404(Customer, pk=pk)
            customer.delete()
            data['redirect'] = (reverse('customerlist'))
            data['form_is_valid'] = True

        else:
            raise NameError('Action was not recogniced', action)

        """
        Test stuff. Since it's not very straightforward extract this data
        from render_to_string() method, we'll pass them as keys in JSON but
        just for testing purposes.
        """
        if request.POST.get('test'):
            data['template'] = template
            if context:
                add_to_context = []
                for k in context:
                    add_to_context.append(k)
                data['context'] = add_to_context

        # Now render_to_string the html for JSON response
        if template and context:
            data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)


class OrdersCRUD(View):
    """Process all the CRUD actions on order model.

    This is the new version for AJAX calls since Actions class became really
    huge to be clear. Eventually each model will have their CRUD AJAX Actions
    to work with.
    """

    def get(self, request):
        pass

    def post(self, request):
        data = dict()
        pk = self.request.POST.get('pk', None)
        action = self.request.POST.get('action', None)
        test = self.request.POST.get('test', None)
        template, context = False, False

        if not pk:
            return HttpResponseServerError('No pk was given.')

        if not action:
            return HttpResponseServerError('No action was given.')

        # Edit date (POST)
        if action == 'edit-date':
            order = get_object_or_404(Order, pk=pk)
            form = EditDateForm(request.POST, instance=order)
            if form.is_valid():
                form.save()
                data['form_is_valid'] = True
            else:
                data['form_is_valid'] = False
                data['error'] = form.errors

        # Kanban Jump (POST)
        elif action == 'kanban-jump':
            order = get_object_or_404(Order, pk=pk)
            dir = request.POST.get('direction', None)
            if not dir:
                return HttpResponseServerError('No direction was especified.')
            if dir == 'back':
                order.kanban_backward()
            elif dir == 'next':
                order.kanban_forward()
            else:
                return HttpResponseServerError('Unknown direction.')
            data['form_is_valid'] = True

        else:
            return HttpResponseServerError('The action was not found.')

        template = 'includes/kanban_columns.html'
        data['html_id'] = '#kanban-columns'
        context = CommonContexts.kanban()
        data['html'] = render_to_string(template, context, request=request)

        # When testing, display as a regular view in order to test variables
        if test:
            return render(
                request, 'includes/kanban_columns.html', context=context)
        else:
            return JsonResponse(data)


class OrderItemsCRUD(View):
    """Process all the CRUD actions on comment model.

    This is the new version for AJAX calls since Actions class became really
    huge to be clear. Eventually each model will have their CRUD AJAX Actions
    to work with.
    """

    def get(self, request):
        pass

    def post(self, request):
        data = dict()
        pk = self.request.POST.get('pk', None)
        action = self.request.POST.get('action', None)
        test = self.request.POST.get('test', None)
        template, context = False, False

        if not pk:
            return HttpResponseServerError('No pk was given.')

        if not action:
            return HttpResponseServerError('No action was given.')

        if action == 'edit-times':
            item = get_object_or_404(OrderItem, pk=pk)
            form = ItemTimesForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                data['form_is_valid'] = True
                data['html_id'] = '#orderitems-list'
            else:
                data['form_is_valid'] = False
                data['error'] = form.errors

            template = 'includes/orderitems_list.html'
            context = CommonContexts.order_details(
                request=request, pk=item.reference.pk)
        else:
            return HttpResponseServerError('The action was not found.')

        data['html'] = render_to_string(template, context, request=request)

        # When testing, display as a regular view in order to test variables
        if test:
            context['form'] = form
            context['data'] = data
            return render(
                request, template, context=context)
        else:
            return JsonResponse(data)


class CommentsCRUD(View):
    """Process all the CRUD actions on comment model.

    This is the new version for AJAX calls since Actions class became really
    huge to be clear. Eventually each model will have their CRUD AJAX Actions
    to work with.
    """

    def get(self, request):
        pass

    def post(self, request):
        data = dict()
        pk = self.request.POST.get('pk', None)
        action = self.request.POST.get('action', None)
        test = self.request.POST.get('test', None)
        template, context = False, False

        if not pk:
            return HttpResponseServerError('No pk was given.')

        if not action:
            return HttpResponseServerError('No action was given.')

        if action == 'add-comment':
            order = get_object_or_404(Order, pk=pk)
            form = CommentForm(request.POST)
            if form.is_valid():
                c = form.save(commit=False)
                c.user = request.user
                c.reference = order
                c.save()
                data['form_is_valid'] = True
                template = 'includes/kanban_columns.html'
                data['html_id'] = '#kanban-columns'
            else:
                data['form_is_valid'] = False
                data['error'] = form.errors

            template = 'includes/kanban_columns.html'
            context = CommonContexts.kanban()
        else:
            return HttpResponseServerError('The action was not found.')

        if not template:   # pragma: no cover
            return HttpResponseServerError('No template was especified.')

        if not context:   # pragma: no cover
            return HttpResponseServerError('No context variables found.')

        data['html'] = render_to_string(template, context, request=request)

        # When testing, display as a regular view in order to test variables
        if test:
            return render(
                request, 'includes/kanban_columns.html', context=context)
        else:
            return JsonResponse(data)


def changelog(request):
    """Display the changelog."""
    if request.method != 'GET':
        raise Http404('The filter should go in a get request')
    data = dict()
    with open('orders/changelog.md') as md:
        md_file = md.read()
        changelog = markdown2.markdown(md_file)

    data['html'] = changelog
    return JsonResponse(data)


def pqueue_actions(request):
    """Manage the ajax actions for PQueue objects."""
    # Ensure the request method
    if request.method != 'POST':
        return HttpResponseServerError('The request should go in a post ' +
                                       'method')

    pk = request.POST.get('pk', None)
    action = request.POST.get('action', None)

    # Ensure that there is a pk and action
    if not pk or not action:
        return HttpResponseServerError('POST data was poor')

    # Ensure the action is fine
    accepted_actions = ('send', 'back', 'up', 'down', 'top', 'bottom',
                        'complete', 'uncomplete', 'tb-complete',
                        'tb-uncomplete')
    if action not in accepted_actions:
        return HttpResponseServerError('The action was not recognized')

    # Initial data
    data = {'html_id': '#pqueue-list',
            'reload': False,
            'is_valid': False,
            'error': False, }
    template = 'includes/pqueue_list.html'

    pqueue = PQueue.objects.select_related('item__reference')
    pqueue = pqueue.exclude(item__reference__status__in=[7, 8])
    pqueue_completed = pqueue.filter(score__lt=0)
    pqueue_active = pqueue.filter(score__gt=0)
    context = {'active': pqueue_active,
               'completed': pqueue_completed,
               }

    if action == 'send':
        item = get_object_or_404(OrderItem, pk=pk)
        to_queue = PQueue(item=item)
        try:
            to_queue.clean()
        except ValidationError:
            data['error'] = 'Couldn\'t save the object'
        else:
            to_queue.save()
            data['is_valid'] = True
            data['reload'] = True
            data['html_id'] = False

    elif action == 'back':
        item = get_object_or_404(PQueue, pk=pk)
        item.delete()
        data['is_valid'] = True
        data['reload'] = True
        data['html_id'] = False

    elif action == 'up':
        item = get_object_or_404(PQueue, pk=pk)
        if item.up():
            data['is_valid'] = True
        else:
            data['error'] = 'Couldn\'t clean the object'

    elif action == 'down':
        item = get_object_or_404(PQueue, pk=pk)
        if item.down():
            data['is_valid'] = True
        else:
            data['error'] = 'Couldn\'t clean the object'

    elif action == 'top':
        item = get_object_or_404(PQueue, pk=pk)
        if item.top():
            data['is_valid'] = True
        else:
            data['error'] = 'Couldn\'t clean the object'

    elif action == 'bottom':
        item = get_object_or_404(PQueue, pk=pk)
        if item.bottom():
            data['is_valid'] = True
        else:
            data['error'] = 'Couldn\'t clean the object'

    elif action == 'complete' or action == 'tb-complete':
        item = get_object_or_404(PQueue, pk=pk)
        if item.complete():
            data['is_valid'] = True
        else:
            data['error'] = 'Couldn\'t clean the object'

    elif action == 'uncomplete' or action == 'tb-uncomplete':
        item = get_object_or_404(PQueue, pk=pk)
        if item.uncomplete():
            data['is_valid'] = True
        else:
            data['error'] = 'Couldn\'t clean the object'

    # Tablet view id
    if action == 'tb-complete' or action == 'tb-uncomplete':
        data['html_id'] = '#pqueue-list-tablet'
        template = 'tz/pqueue_tablet.html'

    """
    Test stuff. Since it's not very straightforward extract this data
    from render_to_string() method, we'll pass them as keys in JSON but
    just for testing purposes.
    """
    if request.POST.get('test'):
        data['template'] = template
        add_to_context = []
        for k in context:
            add_to_context.append(k)
        data['context'] = add_to_context

    data['html'] = render_to_string(template, context, request=request)
    return JsonResponse(data)


def item_selector(request):
    """Select and add new items."""
    # Set initial search filters as unknown
    by_type, by_size, by_name = None, None, None

    # Fix context settings
    context = {'item_types': settings.ITEM_TYPE[1:],
               'item_classes': settings.ITEM_CLASSES,
               'js_action_edit': 'object-item-edit',
               'js_action_delete': 'object-item-delete'
               }

    # Process form when addding items on the fly
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            context['errors'] = form.errors

    # In orders we should provide the order id to attach items to it
    order_pk = request.GET.get('aditionalpk', None)
    if not order_pk:
        order_pk = request.POST.get('aditionalpk', None)
    if order_pk:
        # get rid of edit and delete in this views
        context['js_action_edit'] = False
        context['js_action_delete'] = False

        # Now divert depending the kind of order
        order = get_object_or_404(Order, pk=order_pk)
        context['order'] = order
        if order.customer.name == 'express':
            context['js_action_send_to'] = 'send-to-order-express'
        else:
            context['js_action_send_to'] = 'send-to-order'

    items = Item.objects.all()

    # Look for filters in GET or POST
    by_type = (request.GET.get('item-type', None) or
               request.POST.get('filter-on-type', None))
    by_name = (request.GET.get('item-name', None) or
               request.POST.get('filter-on-name', None))
    by_size = (request.GET.get('item-size', None) or
               request.POST.get('filter-on-size', None))

    # Finally, apply the proper filter once known above values
    if by_type:
        items = items.filter(item_type=by_type)
        item_names = items.distinct('name')
        context['item_names'] = item_names
        context['data_type'] = settings.ITEM_TYPE[int(by_type)]

    if by_name:
        items = items.filter(name=by_name)
        item_sizes = items.order_by('size').distinct('size')
        context['data_name'] = by_name
        context['item_sizes'] = item_sizes

    if by_size:
        items = items.filter(size=by_size)
        context['data_size'] = by_size

    context['available_items'] = items[:5]
    context['total_items'] = items.count()

    template = 'includes/item_selector.html'
    data = {'html': render_to_string(template, context, request=request),
            'id': '#item-selector'}

    """
    Test stuff. Since it's not very straightforward extract this data
    from render_to_string() method, we'll render it in a regular way.
    """
    if request.GET.get('test', None) or request.POST.get('test', None):
        return render(request, template, context)

    return JsonResponse(data)


# API view
class CustomerAPIList(viewsets.ReadOnlyModelViewSet):
    """API view for customers."""

    queryset = Customer.objects.all()
    serializer_class = serializers.CustomerSerializer


class OrderAPIList(viewsets.ReadOnlyModelViewSet):
    """API view for orders."""

    queryset = Order.objects.all()
    serializer_class = serializers.OrderSerializer


class ItemAPIList(viewsets.ReadOnlyModelViewSet):
    """API view for items."""
    queryset = Item.objects.all()
    serializer_class = serializers.ItemSerializer


class OrderItemAPIList(viewsets.ReadOnlyModelViewSet):
    """API view for order items."""
    queryset = OrderItem.objects.all()
    serializer_class = serializers.OrderItemSerializer


class InvoiceAPIList(viewsets.ReadOnlyModelViewSet):
    """API view for invoices."""
    queryset = Invoice.objects.all()
    serializer_class = serializers.InvoiceSerializer


class ExpenseAPIList(viewsets.ReadOnlyModelViewSet):
    """API view for expenses."""
    queryset = Expense.objects.all()
    serializer_class = serializers.ExpenseSerializer


class BankMovementAPIList(viewsets.ReadOnlyModelViewSet):
    """API view for bank movements."""
    queryset = BankMovement.objects.all()
    serializer_class = serializers.BankMovementSerializer


class TimetableAPIList(viewsets.ReadOnlyModelViewSet):
    """API view for timetabñes."""
    queryset = Timetable.objects.all()
    serializer_class = serializers.TimetableSerializer
#
#
#
#
#
#
#
#
#
#
