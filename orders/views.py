"""Define all the views for the app."""

from datetime import date, datetime, timedelta
from random import randint

import markdown2
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, DecimalField, FloatField, F, Q, Sum
from django.http import (
    Http404, HttpResponseServerError, JsonResponse, FileResponse, )
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_GET
from django.views.generic import ListView
from rest_framework import viewsets

from . import serializers, settings
from .utils import prettify_times
from .forms import (
    CommentForm, CustomerForm, EditDateForm, InvoiceForm, ItemForm, OrderForm,
    OrderItemForm, TimetableCloseForm, ItemTimesForm, OrderItemNotes,
    CashFlowIOForm, )
from .models import (BankMovement, Comment, Customer, Expense, Invoice, Item,
                     Order, OrderItem, PQueue, Timetable, CashFlowIO, )

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
        done = Order.live.filter(status='7').filter(confirmed=confirmed)
        done = done.exclude(customer__name__iexact='trapuzarrak')
        done = done.order_by('delivery')

        # Get the amounts for each column
        cols = (icebox, queued, in_progress, waiting, done, )
        cols = [c.exclude(customer__name__iexact='Trapuzarrak') for c in cols]
        amounts = [sum([order.total for order in col]) for col in cols]
        already_paid = [
            sum([order.already_paid for order in col]) for col in cols]

        # Get times for icebox & queued orders. Recall that
        # order.estimated_time returns 3 times
        cols = (icebox, queued, )
        est_times = [
            sum([sum(order.estimated_time) for order in col]) for col in cols]

        est_times = [prettify_times(d) for d in est_times]

        vars = {'icebox': icebox,
                'queued': queued,
                'in_progress': in_progress,
                'waiting': waiting,
                'done': done,
                'confirmed': confirmed,
                'update_date': EditDateForm(),
                'amounts': amounts,
                'already_paid': already_paid,
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
        try:
            session = Timetable.active.get(user=request.user)
        except ObjectDoesNotExist:  # pragma: no cover
            session = None

        # Display max status dates without overrun the next stages
        ss = order.status_shift.all()
        sts = ('1', '2', '3', '6', '7', '9', )
        sis = settings.STATUS_ICONS
        status_tracker = [
            (sis[n], ss.filter(status=s).last()) for n, s in enumerate(sts)
        ]

        # Display estimated times
        order_est = [prettify_times(d) for d in order.estimated_time]
        order_est_total = prettify_times(sum(order.estimated_time))

        title = (order.pk, order.customer.name, order.ref_name)
        vars = {'order': order,
                'items': items,
                'status_tracker': status_tracker,
                'order_est': order_est,
                'order_est_total': order_est_total,
                'update_times': ItemTimesForm(),
                'add_prepaids': CashFlowIOForm(),
                'kill_order': InvoiceForm(),  # we'll use the pay_method field
                'comments': comments,
                'STATUS_ICONS': sis,
                'user': cur_user,
                'now': now,
                'session': session,
                'version': settings.VERSION,
                'title': 'Pedido %s: %s, %s' % title, }
        return vars

    @staticmethod
    def stock_tabs(items=None):
        """Get the common variables for stock manager."""
        if not items:
            items = Item.objects.all().order_by('health')  # Default value

        items = items.exclude(name='Predeterminado')
        tab_elements = {
            'p1': items.filter(health=0),
            'p2': items.filter(health__gt=0).filter(health__lt=1),
            'p3': items.filter(health__gte=1),
            'zero': items.filter(health=-100),
            'negative': items.filter(health__lt=0).filter(health__gt=-100),
        }

        return {
            'tab_elements': tab_elements, 'item_types': settings.ITEM_TYPE[1:]
        }

    @staticmethod
    def pqueue():
        """Get common context var for pqueue."""
        available = OrderItem.objects.exclude(reference__status__in=[7, 8, 9])
        available = available.filter(reference__confirmed=True)
        available = available.exclude(element__name__iexact='Descuento')
        available = available.exclude(stock=True).filter(pqueue__isnull=True)
        available = available.exclude(element__foreing=True)
        available = available.order_by('reference__delivery',
                                       'reference__ref_name')
        pqueue = PQueue.objects.select_related('item__reference')
        pqueue = pqueue.exclude(item__reference__status__in=[7, 8, 9])
        pqueue_completed = pqueue.filter(score__lt=0)
        pqueue_active = pqueue.filter(score__gt=0)
        i_relax = settings.RELAX_ICONS[
            randint(0, len(settings.RELAX_ICONS) - 1)]

        view_settings = {'available': available,
                         'active': pqueue_active,
                         'completed': pqueue_completed,
                         'i_relax': i_relax,
                         'now': timezone.now(),
                         'version': settings.VERSION,
                         'title': 'TrapuZarrak · Cola de producción',
                         }

        return view_settings


def timetable_required(function):
    """Prevent users without valid timetable to load pages.

    Superusers and voyeur are allowed to navigate freely.
    """
    def _inner(request, *args, **kwargs):
        u = request.user
        if u.is_superuser or u.username == config('VOYEUR_USER'):
            return function(request, *args, **kwargs)
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


@login_required
def printable_ticket(request, invoice_no):
    """Download an invoiced order."""
    invoice = Invoice.objects.get(invoice_no=invoice_no)
    pdf = invoice.printable_ticket()
    filename = 'ticket-{}.pdf'.format(invoice.invoice_no)
    return FileResponse(pdf, as_attachment=True, filename=filename, )


# Add hours
@login_required
def add_hours(request):
    """Close an open work session."""
    u = request.user
    # Superuser and voyeur should skip this process
    if u.is_superuser or u.username == config('VOYEUR_USER'):
        logout(request)
        return redirect('login')

    # prevent reaching this page without valid timetable open
    try:
        active = Timetable.active.get(user=u)
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
    today, cur_year = date.today(), date.today().year
    elapsed = today - date(cur_year - 1, 12, 31)
    goal = elapsed.days * settings.GOAL

    """
    Incomes bar.

    Incomes bar shows three elements (at most): current year incomes (sales +
    prepaids); active orders' pending amount and unconfirmed orders's amounts.

    0th, 1st & 2nd aggregates.
    """
    active_items = OrderItem.active.all()

    # GoalBox, solid incomes: invoiced and prepaids
    sales = CashFlowIO.inbounds.filter(creation__year=cur_year)
    sales = sales.aggregate(total=Sum('amount'))
    confirmed = active_items.filter(reference__confirmed=True)

    # GoalBox, pending in unconfirmed orders
    unconfirmed = active_items.exclude(reference__confirmed=True)

    # GoalBox, summary amounts
    aggregates = [int(sales['total']) if sales['total'] else 0]

    # GoalBox, get aggregations for confirmed & unconfirmed
    for queryset in (confirmed, unconfirmed):
        if queryset:
            to_list = queryset.aggregate(
                total=Sum(F('price') * F('qty'), output_field=FloatField()))
            to_list = [int(to_list['total']) if to_list['total'] else 0][0]
        else:
            to_list = 0
        aggregates.append(to_list)

    """
    Expenses bar.

    Expenses bar shows two elements (at most): current year already paid
    payments, previous and current year pending payments, provided that
    there won't be pending payments older than that (1 year)

    Aggregates 3rd & 4th.
    """
    cfo, e = CashFlowIO.outbounds.all(), Expense.objects.filter(closed=False)
    already_paid = cfo.filter(creation__year=cur_year)
    already_paid = already_paid.aggregate(total=Sum('amount'))['total']
    pending_expenses = e.aggregate(total=Sum('amount'))['total']
    partially_paid = cfo.filter(expense__closed=False)
    partially_paid = partially_paid.aggregate(total=Sum('amount'))['total']
    agg = (already_paid, pending_expenses, partially_paid, )
    already_paid, pending_expenses, partially_paid = [
        int(a) if a else 0 for a in agg]
    aggregates.append(already_paid)  # 3rd aggregate, expenses paid

    # 4th aggregate, pending expenses
    aggregates.append(pending_expenses - partially_paid)

    # Finally, insert the goal estimation to compute (5th aggregate)
    aggregates.append(goal)

    # Estimate the length of the bar from the relevant amounts: inbounds,
    # outbounds and goal
    relevant = (aggregates[0], aggregates[3], aggregates[5])
    mn, mx = min(relevant) * .9,  max(relevant) * 1.1
    bar_len = mx - mn

    # Estimate the percentages for each aggregate
    bar = [round((amount - mn) * 100 / bar_len, 2) for amount in aggregates]

    # Adjust confirmed and unconfirmed since they are not included in relevant
    bar[1] = round(((sum(aggregates[:2]) - mn)*100 / bar_len)-bar[0], 2)
    bar[2] = round(((sum(aggregates[:3]) - mn)*100 / bar_len)-sum(bar[:2]), 2)
    bar[4] = round(((sum(aggregates[3:5]) - mn)*100 / bar_len)-bar[3], 2)

    # GoalBox, tracked time ratios this year
    nat = timedelta(0)
    tt = OrderItem.objects.filter(stock=False).filter(element__foreing=False)
    tt = tt.filter(reference__status__in=['7', '9'])
    tt = tt.filter(reference__inbox_date__year=cur_year)
    if tt:
        ttc, tts, tti = (
            tt.exclude(crop=nat), tt.exclude(sewing=nat), tt.exclude(iron=nat))
        ttc, tts, tti, tt = [query.count() for query in (ttc, tts, tti, tt)]
        tt_ratio = {
            'crop': round(100 * ttc / tt),
            'sewing': round(100 * tts / tt),
            'iron': round(100 * tti / tt),
            'absolute': (ttc, tts, tti, tt),
            'mean': round(100 * (ttc+tts+tti)/(3*tt))
        }
    else:
        tt_ratio = None

    # Active Box
    active = Order.live.exclude(status='7').count()
    active_msg = False
    waiting = Order.live.filter(status='6').count()
    if waiting:
        active_msg = 'Aunque hay %s para entregar' % waiting

    # Pending box
    pending = [o.pending for o in Order.live.all() if o.pending]
    pending_amount = int(sum(pending))
    pending_msg = '{}€ tenemos aún<br>por cobrar'.format(pending_amount)
    if pending_amount == 0:
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
    month = CashFlowIO.inbounds.filter(creation__year=cur_year)
    month = month.filter(creation__month=timezone.now().date().month)
    month = month.aggregate(total=Sum('amount'))

    # week production box
    week = CashFlowIO.inbounds.filter(creation__year=cur_year)
    week = week.filter(creation__week=timezone.now().date().isocalendar()[1])
    week = week.aggregate(total=Sum('amount'))

    # top5 customers Box
    top5 = Customer.objects.exclude(name__iexact='express')
    top5 = top5.filter(order__invoice__isnull=False)
    top5 = top5.annotate(
        total=Sum(F('order__items__price') * F('order__items__qty'),
                  output_field=DecimalField()))
    top5 = top5.order_by('-total')[:5]

    cur_user = request.user
    try:
        session = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:
        session = None

    # Query last comments on active orders
    comments = Comment.objects.exclude(user=cur_user)
    comments = comments.exclude(read=True)
    comments = comments.order_by('-creation')

    now = datetime.now()

    view_settings = {'bar': bar,
                     'aggregates': aggregates,
                     'tt_ratio': tt_ratio,
                     'active': active,
                     'active_msg': active_msg,
                     'pending': len(pending),
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
    try:
        session = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:  # pragma: no cover
        session = None

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

                     'include_template': 'includes/customer_list.html',
                     }

    return render(request, 'tz/list_view.html', view_settings)


@login_required
@timetable_required
def itemslist(request):
    """Show the different item objects."""
    cur_user = request.user
    now = datetime.now()
    try:
        session = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:
        session = None

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
                     }

    return render(request, 'tz/list_view.html', view_settings)


@login_required
@timetable_required
def invoiceslist(request):
    """List all the invoices."""
    # Invoiced today, current week and current month
    cf_inbounds_today = CashFlowIO.inbounds.filter(
        creation__date=timezone.now().date())
    week = Invoice.objects.filter(
        issued_on__week=timezone.now().date().isocalendar()[1])
    month = Invoice.objects.filter(
        issued_on__month=timezone.now().date().month)
    all_time_cash = Invoice.objects.filter(pay_method='C')
    all_time_cash = all_time_cash.aggregate(total_cash=Sum('amount'))
    cf_inbounds_today_cash = cf_inbounds_today.aggregate(
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

    # bank-shop status
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

    # Pending expenses
    pending_expenses = Expense.objects.filter(closed=False)
    pending_expenses_cash = 0
    for e in pending_expenses:
        pending_expenses_cash += e.pending

    cur_user = request.user
    now = datetime.now()
    try:
        session = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:
        session = None

    view_settings = {'user': cur_user,
                     'now': now,
                     'session': session,
                     'week': week,
                     'month': month,
                     'week_cash': week_cash,
                     'month_cash': month_cash,
                     'bank_movements': bank_movements,
                     'cf_inbounds_today': cf_inbounds_today,
                     'cf_inbounds_today_cash': cf_inbounds_today_cash,
                     'pending_expenses': pending_expenses,
                     'pending_expenses_cash': pending_expenses_cash,
                     'add_prepaids': CashFlowIOForm(),
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

    try:
        session = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:
        session = None

    context['cur_user'] = request.user
    context['now'] = datetime.now()
    context['session'] = session
    context['version'] = settings.VERSION
    context['title'] = 'TrapuZarrak · Vista Kanban'

    return render(request, 'tz/kanban.html', context)


@login_required
@timetable_required
def stock_manager(request):
    """View and edit items' stock."""
    items = Item.objects.all().order_by('health')
    filter_type = request.GET.get('filter_type', None)
    if filter_type:
        items = items.filter(item_type=filter_type)

    context = CommonContexts.stock_tabs(items)

    return render(request, 'tz/stock_manager.html', context)


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

        elif action == 'kill-order':
            pm = request.POST.get('pay_method', None)
            order.kill(pay_method=pm)
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
        pay_method = request.POST.get('pay_method', None)
        if cp:  # Add a zip code to the express order
            c = Customer.objects.get_or_create(
                name='express', city='server', phone=0, cp=cp,
                notes='AnnonymousUserAutmaticallyCreated')
            order.customer = c[0]
            order.save()
        elif customer_pk:  # convert to regular order
            c = get_object_or_404(Customer, pk=customer_pk)
            order.customer = c
            order.ref_name = 'Venta express con arreglo'
            order.save()
        elif pay_method:  # Invoice the order
            order.kill(pay_method=pay_method)
            # define the email sending options
            if request.POST.get('email', None):
                pass  # pragma: no cover

        else:
            raise Http404('Something went wrong with the request.')

    # Redirect regular orders
    if order.customer.name != 'express':
        return redirect(reverse('order_view', args=[order.pk]))

    customers = Customer.objects.exclude(name='express')
    customers = customers.exclude(provider=True)
    items = OrderItem.objects.filter(reference=order)
    available_items = Item.objects.all()[:10]

    cur_user = request.user
    now = datetime.now()
    try:
        session = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:
        session = None

    view_settings = {'order': order,
                     'customers': customers,
                     'user': cur_user,
                     'now': now,
                     'session': session,
                     'item_types': settings.ITEM_TYPE[1:],
                     'items': items,
                     'invoice_form': InvoiceForm(),
                     'available_items': available_items,
                     'version': settings.VERSION,
                     'title': 'TrapuZarrak · Venta express',
                     'placeholder': 'Busca un nombre',
                     'search_on': 'items',

                     # CRUD Actions
                     'btn_title_add': 'Nueva prenda',
                     'js_action_add': 'object-item-add',
                     }
    return render(request, 'tz/order_express.html', view_settings)


@login_required
@timetable_required
def customer_view(request, pk):
    """Display details for an especific customer."""
    customer = get_object_or_404(Customer, pk=pk)
    orders = Order.objects.filter(customer=customer)
    active = orders.exclude(status__in=[7, 8, 9]).order_by('delivery')
    delivered = orders.filter(status__in=[7, 9]).order_by('delivery')
    cancelled = orders.filter(status=8).order_by('delivery')

    # Evaluate pending orders
    pending = orders.filter(delivery__gte=date(2019, 1, 1))
    pending = pending.filter(invoice__isnull=True)

    cur_user = request.user
    now = datetime.now()
    try:
        session = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:
        session = None

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
    try:
        session = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:
        session = None
    context = CommonContexts.pqueue()
    context['cur_user'] = request.user
    context['session'] = session
    return render(request, 'tz/pqueue_manager.html', context)


@login_required
@timetable_required
def pqueue_tablet(request):
    """Tablet view of pqueue."""
    try:
        session = Timetable.active.get(user=request.user)
    except ObjectDoesNotExist:
        session = None
    context = CommonContexts.pqueue()
    context['cur_user'] = request.user
    context['session'] = session
    return render(request, 'tz/pqueue_tablet.html', context)


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
        u = self.request.user
        if u.is_superuser or u.username == config('VOYEUR_USER'):
            query = Timetable.objects.all()
        else:
            query = Timetable.objects.filter(user=self.request.user)
        return query.order_by('-start')[:10]

    def get_context_data(self, **kwargs):
        """Add some extra variables to make the view consistent with base."""
        u = self.request.user
        context = super().get_context_data(**kwargs)
        if u.is_superuser or u.username == config('VOYEUR_USER'):
            context['session'] = None
        else:
            context['session'] = self.get_queryset()[0]
        context['user'] = u
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

        if not action:
            raise ValueError('Unexpected GET data')

        """ Add actions """
        # Add express order (GET)
        if action == 'order-express-add':
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

        # delete order express (GET)
        elif action == 'order-express-delete':
            order = get_object_or_404(Order, pk=pk)
            context = {'modal_title': 'Eliminar ticket express',
                       'msg': 'Quieres realmente descartar el ticket?',
                       'pk': order.pk,
                       'action': 'order-express-delete',
                       'submit_btn': 'Sí, descartar'}
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

        # Add express order
        if action == 'order-express-add':
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
                form.save()
                items = Item.objects.all()[:11]
                data['html_id'] = '#item-selector'
                data['form_is_valid'] = True
                context = {'item_types': settings.ITEM_TYPE[1:],
                           'available_items': items,
                           'js_action_edit': 'object-item-edit',
                           'js_action_delete': 'object-item-delete',
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

        # Add times from pqueue (POST)
        elif action == 'pqueue-add-time':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            form = ItemTimesForm(request.POST, instance=item)
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

        # Delete object Item
        elif action == 'object-item-delete':
            item = get_object_or_404(Item, pk=pk)
            item.delete()
            data['form_is_valid'] = True
            items = Item.objects.all()[:11]
            data['html_id'] = '#item-selector'
            context = {'item_types': settings.ITEM_TYPE[1:],
                       'available_items': items,
                       'js_action_edit': 'object-item-edit',
                       'js_action_delete': 'object-item-delete',
                       }
            template = 'includes/item_selector.html'

        # Delete order express (POST)
        elif action == 'order-express-delete':
            order = get_object_or_404(Order, pk=pk)
            order.delete()
            data['redirect'] = (reverse('main'))
            data['form_is_valid'] = True

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
    """Process all the CRUD actions called by AJAX on order model.

    This is the new version for AJAX calls since Actions class became really
    huge to be clear. Eventually each model will have their CRUD AJAX Actions
    to work with.
    """

    def get(self, request):
        """Open a dialog to create or edit orders."""
        data = dict()

        # Creating and editing use the same template
        template = 'includes/custom_forms/order.html'

        # Determine whether we're editing or creating
        order_pk = request.GET.get('order_pk', None)
        if order_pk:  # we're editing
            order = Order.objects.get(pk=order_pk)
            form = OrderForm(instance=order)
            modal_title = 'Editar pedido'
        else:
            form = OrderForm()
            modal_title = 'Crear pedido'
            order = None

        context = {'form': form, 'modal_title': modal_title, 'order': order, }

        # When testing, display as a regular view in order to test variables
        if self.request.GET.get('test', None):
            return render(request, template, context=context)

        data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)

    def post(self, request):
        data = dict()
        pk = self.request.POST.get('pk', None)
        order = Order.objects.get(pk=pk) if pk else None
        template, context, modal_title = None, None, None

        action = self.request.POST.get('action', None)
        if not action:
            return HttpResponseServerError('No action was given.')

        # Create/Edit the whole order (POST)
        if action == 'main':
            if order:  # we're editing
                form = OrderForm(request.POST, instance=order)
                modal_title = 'Editar pedido'
            else:  # we're creating
                form = OrderForm(request.POST)
                modal_title = 'Crear pedido'

            if form.is_valid():
                order = form.save()
                url = (reverse('order_view', args=[order.pk]) + '?tab=main')
                data['redirect'] = url
                data['form_is_valid'] = True
                template, context = None, None  # redirect does not need'em
            else:
                data['form_is_valid'] = False
                context = {'form': form, 'modal_title': modal_title, }
                template = 'includes/custom_forms/order.html'

        # Edit date (POST)
        elif action == 'edit-date':
            # Edits the date inside kanban elements
            form = EditDateForm(request.POST, instance=order)
            if form.is_valid():
                form.save()
                data['form_is_valid'] = True
                data['html_id'] = '#kanban-columns'
                context = CommonContexts.kanban()
            else:
                data['form_is_valid'] = False
                data['error'] = form.errors

        # Kanban Jump (POST)
        elif action == 'kanban-jump':
            """Shifts kanban status in both kanban view and order view when
            cliking on the arrows."""
            raw_input = request.POST.get('origin', None)
            if not raw_input:
                return HttpResponseServerError('No origin was especified.')
            else:
                origin, dir = raw_input.split('-')
            if dir == 'shiftBack':
                order.kanban_backward()
            elif dir == 'shiftFwd':
                order.kanban_forward()
            else:
                return HttpResponseServerError('Unknown direction.')

            if origin == 'status':
                template = 'includes/order_status.html'
                data['html_id'] = '#order-status'
                context = CommonContexts.order_details(request, pk)
            else:
                template = 'includes/kanban_columns.html'
                data['html_id'] = '#kanban-columns'
                context = CommonContexts.kanban()

            data['form_is_valid'] = True

        else:
            return HttpResponseServerError('The action was not found.')

        # When testing, display as a regular view in order to test variables
        # Create dummy templates and contexts so we can render the view
        if self.request.POST.get('test', None):
            if not template:
                template = 'includes/custom_forms/order.html'  # dummy
            if not context:
                context = {  # dummy
                    'form': form, 'modal_title': modal_title, 'data': data}
            return render(request, template, context=context)

        if context and template:
            data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)


class ItemsCRUD(View):
    """Process all the CRUD actions called by AJAX on Item model.

    This is the new version for AJAX calls since Actions class became really
    huge to be clear. Eventually each model will have their CRUD AJAX Actions
    to work with.
    """

    def get(self, request):
        """Load a form to save items."""
        data = dict()
        item_pk = request.GET.get('item_pk', None)
        item = Item.objects.get(pk=item_pk) if item_pk else None
        action = request.GET.get('action', None)

        # The main action: create/edit the item as a whole
        if action == 'main':
            pass  # pragma: no cover

        # Edit stock value on stock manager
        elif action == 'edit-stock':
            if not item:
                raise Http404('No item was especified')
            form = ItemForm(instance=item)
            template = 'includes/custom_forms/edit_stock.html'
            modal_title = 'Editar stock'
            context = {
                'item': item, 'form': form, 'modal_title': modal_title, }

        else:
            return HttpResponseServerError('Action was not recogniced.')

        if request.GET.get('test', None):
            return render(request, template, context=context)

        data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)

    def post(self, request):
        """Process the form to save the element."""
        data = dict()
        item_pk = request.POST.get('item_pk', None)
        item = Item.objects.get(pk=item_pk) if item_pk else None
        action = request.POST.get('action', None)

        # The main action: create/edit the item as a whole
        if action == 'main':
            pass

        # Edit stock value on stock manager
        elif action == 'edit-stock':
            if not item:
                raise Http404('No item was especified')
            form = ItemForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                template = 'includes/stock_tabs.html'
                context = CommonContexts.stock_tabs()
                data['html_id'] = '#stock-tabs'
                data['form_is_valid'] = True
            else:
                data['form_is_valid'] = False
                template = 'includes/custom_forms/edit_stock.html'
                modal_title = 'Editar stock'
                context = {
                    'item': item, 'form': form, 'modal_title': modal_title}

        else:
            return HttpResponseServerError('Action was not recogniced')

        if request.GET.get('test', None):
            return render(request, template, context=context)

        data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)


class OrderItemsCRUD(View):
    """Process all the CRUD actions on comment model.

    This is the new version for AJAX calls since Actions class became really
    huge to be clear. Eventually each model will have their CRUD AJAX Actions
    to work with.
    """

    def get(self, request):
        """Get the modal's content to perform CRUD on OrderItems."""
        data = dict()
        order_pk = request.GET.get('reference', None)
        if not order_pk:
            return HttpResponseServerError('No order was supplied')
        order = Order.objects.get(pk=order_pk)

        # Determine whether we're creating or editing/deleting
        base_item = request.GET.get('element', None)
        base_item = Item.objects.get(pk=base_item)
        order_item = request.GET.get('order_item', None)

        # Creating and editing use the same template
        template = 'includes/custom_forms/order_item.html'

        if order_item:  # we're editing/deleting
            order_item = OrderItem.objects.get(pk=order_item)
            form = OrderItemForm(instance=order_item)
            modal_title = 'Editar prenda en pedido.'
            if request.GET.get('delete', None):
                template = 'includes/delete_dialogs/order_item.html'
        else:  # we're creating
            form = OrderItemForm()
            modal_title = 'Añadir prenda.'

        context = {'form': form,
                   'base_item': base_item,
                   'order_item': order_item,
                   'order': order,
                   'modal_title': modal_title,
                   }

        if request.POST.get('test', None):
            return render(
                request, template, context=context)  # pragma: no cover

        data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)

    def post(self, request):
        """Create or update the model.

        The main action process all the fields in the model so they should be
        supplied by the form, whereas the other actions perform updates on
        certain fields.

        Eventually, we should get rid of those partial models (and therefore
        the parameter action) by adding hidden fields to their forms.

        There's also an option to update base_item price.
        """
        data = dict()
        action = request.POST.get('action', None)
        if not action:
            return HttpResponseServerError('No action was given.')

        # Determine whether we're creating or editing/deleting
        order_item_pk = request.POST.get('order_item_pk', None)
        if order_item_pk:  # we're editing/deleting
            order_item = OrderItem.objects.get(pk=order_item_pk)
            form = OrderItemForm(request.POST, instance=order_item)
            modal_title = 'Editar prenda en pedido.'

        else:  # we're creating
            form = OrderItemForm(request.POST)
            modal_title = 'Añadir prenda.'
            order_item = None

        if action == 'main':  # Create & update
            base_item = Item.objects.get(pk=request.POST.get('element', None))
            order = Order.objects.get(pk=request.POST.get('reference', None))
            order_est_total = prettify_times(sum(order.estimated_time))

            if form.is_valid():
                # perfrom db actions
                item = form.save()
                if request.POST.get('set-default-price', None):
                    base_item.price = request.POST.get('set-default-price')
                    base_item.notes = (
                        base_item.notes + ' Cambio de precio desde pedido')
                    base_item.full_clean()
                    base_item.save()
                template = 'includes/item_quick_list.html'
                data['form_is_valid'] = True

                # Render the view depending the order type
                if item.reference.ref_name == 'Quick':
                    data['html_id'] = '#ticket-wrapper'
                    template = 'includes/ticket.html'
                else:
                    data['html_id'] = '#quick-list'
                    template = 'includes/item_quick_list.html'

            # not valid form
            else:
                data['form_is_valid'] = False
                template = 'includes/custom_forms/order_item.html'

            context = {'form': form,
                       'invoice_form': InvoiceForm(),
                       'base_item': base_item,
                       'order_item': order_item,
                       'order': order,
                       'order_est_total': order_est_total,
                       'modal_title': modal_title,
                       }

        elif action == 'delete':
            # TODO: once got rid of partial editing methods, this code below
            # can be refactored with the main action one
            if not order_item_pk:
                return HttpResponseServerError('No item pk was provided.')
            order = Order.objects.get(pk=request.POST.get('reference', None))

            # perfrom db actions
            order_item.delete()
            data['form_is_valid'] = True

            order_est_total = prettify_times(sum(order.estimated_time))

            # Render the view depending the order type
            if order.ref_name == 'Quick':
                data['html_id'] = '#ticket-wrapper'
                template = 'includes/ticket.html'
            else:
                data['html_id'] = '#quick-list'
                template = 'includes/item_quick_list.html'
            context = {'form': form,
                       'order_item': order_item,
                       'order': order,
                       'order_est_total': order_est_total,
                       'modal_title': modal_title,
                       }

        elif action == 'edit-times':
            # Edit the times int the order view
            pk = request.POST.get('pk', None)
            if not pk:
                return HttpResponseServerError('No pk was given.')
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

        elif action == 'edit-notes':
            # Edit/add notes in the pqueue
            pk = request.POST.get('pk', None)
            if not pk:
                return HttpResponseServerError('No pk was given.')
            item = get_object_or_404(OrderItem, pk=pk)
            form = OrderItemNotes(request.POST, instance=item)
            form.save()
            data['form_is_valid'] = True  # this form is always valid
            data['html_id'] = '#item-details-{}'.format(item.pk)
            template = 'includes/pqueue_element_details.html'
            item = dict(item=item)
            context = dict(item=item)  # a bit recursive to match the for loop

        else:
            return HttpResponseServerError('The action was not found.')

        data['html'] = render_to_string(template, context, request=request)

        # When testing, display as a regular view in order to test variables
        if request.POST.get('test', None):
            context['form'] = form
            context['data'] = data
            return render(request, template, context=context)
        else:
            return JsonResponse(data)


class CommentsCRUD(View):
    """Process all the CRUD actions on comment model.

    This is the new version for AJAX calls since Actions class became really
    huge to be clear. Eventually each model will have their CRUD AJAX Actions
    to work with.
    """

    def get(self, request):
        pass  # pragma: no cover

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


class CashFlowIOCRUD(View):
    """Create, update and delete CashFlowIO instances"""
    def get(self, request):
        pass  # pragma: no cover

    def post(self, request):
        action = self.request.POST.get('action', None)

        if not action:
            return HttpResponseServerError('No action was given.')

        if action == 'add-prepaid':
            form = CashFlowIOForm(request.POST)
            if form.is_valid():
                form.save()
                data = {'reload': True, 'form_is_valid': True}
            else:
                first = list(form.errors.values())[0][0]
                data = {'errors': first, 'form_is_valid': False}
        else:
            return HttpResponseServerError('The action was not found.')

        return JsonResponse(data)


def changelog(request):
    """Display the changelog."""
    if request.method != 'GET':
        raise Http404('The filter should go in a get request')
    data = dict()
    with open('orders/docs/changelog.md') as md:
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
        to_queue.clean()
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
        item.up()
        data['is_valid'] = True

    elif action == 'down':
        item = get_object_or_404(PQueue, pk=pk)
        item.down()
        data['is_valid'] = True

    elif action == 'top':
        item = get_object_or_404(PQueue, pk=pk)
        item.top()
        data['is_valid'] = True

    elif action == 'bottom':
        item = get_object_or_404(PQueue, pk=pk)
        item.bottom()
        data['is_valid'] = True

    elif action == 'complete' or action == 'tb-complete':
        item = get_object_or_404(PQueue, pk=pk)
        item.complete()
        data['is_valid'] = True

    elif action == 'uncomplete' or action == 'tb-uncomplete':
        item = get_object_or_404(PQueue, pk=pk)
        item.uncomplete()
        data['is_valid'] = True

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

    context['available_items'] = items[:15]
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


@require_GET
def customer_hints(request):
    """Provide hints on customers when adding/editing an order."""
    search_str = request.GET.get('search')
    if not search_str:
        raise Http404('No string selected')

    customers = Customer.objects.exclude(provider=True)
    starts = customers.filter(name__istartswith=search_str)

    if not starts:
        outcomes = customers.filter(name__icontains=search_str)
    else:
        outcomes = starts

    resp = dict()
    if outcomes:
        for n, c in enumerate(outcomes):
            resp[n] = dict(id=c.id, name=c.name, )
    else:
        resp[0] = dict(id='void', name='No hay coincidencias...', )

    if request.GET.get('test', None):
        template = 'tz/base.html'  # Just a dummy
        return render(request, template, resp)

    return JsonResponse(resp)


@require_GET
def group_hints(request):
    """Provide hints on groups when adding/editing an order."""
    search_str = request.GET.get('search')
    if not search_str:
        raise Http404('No string selected')

    groups = Customer.objects.filter(group=True)
    starts = groups.filter(name__istartswith=search_str)

    if not starts:
        outcomes = groups.filter(name__icontains=search_str)
    else:
        outcomes = starts

    resp = dict()
    if outcomes:
        for n, c in enumerate(outcomes):
            resp[n] = dict(id=c.id, name=c.name, )
    else:
        resp[0] = dict(id='void', name='No hay coincidencias...', )

    if request.GET.get('test', None):
        template = 'tz/base.html'  # Just a dummy
        return render(request, template, resp)

    return JsonResponse(resp)


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
