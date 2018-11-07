"""Define all the views for the app."""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse, Http404, HttpResponseBadRequest
from django.template.loader import render_to_string
from .models import Comment, Customer, Order, OrderItem, Timing, Item
from .utils import TimeLenght
from django.utils import timezone
from .forms import CustomerForm, OrderForm, CommentForm, ItemForm
from .forms import OrderCloseForm, OrderItemForm, TimeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Count, Sum, F
from datetime import datetime


# Root View
@login_required()
def main(request):
    """Create the root view."""
    # Query all active orders
    orders = Order.objects.exclude(status__in=[7, 8]).order_by('delivery')
    pending = Order.objects.exclude(status=8).filter(budget__gt=F('prepaid'))

    # Pending orders should avoid tz orders
    try:
        tz = Customer.objects.get(name__iexact='trapuzarrak')
    except ObjectDoesNotExist:
        tz = None
    else:
        pending = pending.exclude(customer=tz)

    # Total pending amount
    budgets = pending.aggregate(Sum('budget'))
    prepaid = pending.aggregate(Sum('prepaid'))
    try:
        pending_total = budgets['budget__sum'] - prepaid['prepaid__sum']
    except TypeError:
        pending_total = 0

    cur_user = request.user

    # Query last comments on active orders
    comments = Comment.objects.exclude(user=cur_user)
    comments = comments.exclude(read=True)
    comments = comments.order_by('-creation')

    now = datetime.now()

    settings = {'orders': orders,
                'orders_count': len(orders),
                'comments': comments,
                'comments_count': len(comments),
                'pending': pending,
                'pending_total': pending_total,
                'pending_count': len(pending),
                'user': cur_user,
                'now': now,
                'search_on': 'orders',
                'placeholder': 'Buscar pedido (referencia)',
                'title': 'TrapuZarrak · Inicio',
                'footer': True,
                }

    return render(request, 'tz/main.html', settings)


def search(request):
    """Perform a search on orders or custmers."""
    if request.method == 'POST':
        data = dict()
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
            table = Customer.objects.all()
            try:
                int(search_obj)
            except ValueError:
                query_result = table.filter(name__icontains=search_obj)
            else:
                query_result = table.filter(phone__icontains=search_obj)
            model = 'customers'
        else:
            raise ValueError('Search on undefined')
        template = 'includes/search_results.html'
        context = {'query_result': query_result, 'model': model}

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
        try:
            order.full_clean()
        except ValidationError:
            return HttpResponseBadRequest()
        else:
            order.save()

    orders = Order.objects.all()

    try:
        tz = Customer.objects.get(name__iexact='trapuzarrak')
    except ObjectDoesNotExist:
        tz = None

    # Get the orders for each tab when tz customer exists
    if tz:
        # First query the stock, tz related queries
        tz_orders = orders.filter(customer=tz)
        tz_active = tz_orders.exclude(status__in=[7, 8])
        tz_delivered = tz_orders.filter(status=7)[:10]

        # And the attr collection for them
        tz_active = tz_active.annotate(Count('orderitem', distinct=True),
                                       Count('comment', distinct=True),
                                       Count('timing', distinct=True))
        tz_delivered = tz_delivered.annotate(Count('orderitem', distinct=True),
                                             Count('comment', distinct=True),
                                             Count('timing', distinct=True))

        # Finally, exclude tz customer for further queries
        orders = orders.exclude(customer=tz)

    # If tz customer doesn't exist, these vars should be none
    else:
        tz_active = None
        tz_delivered = None

    delivered = orders.filter(status=7)
    active = orders.exclude(status__in=[7, 8])
    cancelled = orders.filter(status=8)
    pending = orders.exclude(status=8).filter(budget__gt=F('prepaid'))
    pending = pending.order_by('status')

    # Active & delivered orders show some attr at glance
    active = active.annotate(Count('orderitem', distinct=True),
                             Count('comment', distinct=True),
                             Count('timing', distinct=True))

    delivered = delivered.annotate(Count('orderitem', distinct=True),
                                   Count('comment', distinct=True),
                                   Count('timing', distinct=True))
    # Total pending amount
    budgets = pending.aggregate(Sum('budget'))
    prepaid = pending.aggregate(Sum('prepaid'))
    try:
        pending_total = budgets['budget__sum'] - prepaid['prepaid__sum']
    except TypeError:
        pending_total = 0

    # Finally, set the sorting method on view
    if orderby == 'date':
        active = active.order_by('delivery')
    elif orderby == 'status':
        active = active.order_by('status')
    elif orderby == 'priority':
        active = active.order_by('priority')
    else:
        raise Http404('Required sorting method')

    cur_user = request.user
    now = datetime.now()

    settings = {'active': active,
                'delivered': delivered,
                'user': cur_user,
                'now': now,
                'active_stock': tz_active,
                'delivered_stock': tz_delivered,
                'cancelled': cancelled,
                'pending': pending,
                'pending_total': pending_total,
                'order_by': orderby,
                'placeholder': 'Buscar pedido (referencia)',
                'search_on': 'orders',
                'title': 'TrapuZarrak · Pedidos',
                'footer': True,
                }

    return render(request, 'tz/orders.html', settings)


@login_required
def customerlist(request):
    """Display all customers or search'em."""
    # customers = Customer.objects.annotate(num_orders=Count('order'))
    customers = Customer.objects.all().order_by('name')
    page = request.GET.get('page', 1)
    paginator = Paginator(customers, 5)
    try:
        customers = paginator.page(page)
    except PageNotAnInteger:
        customers = paginator.page(1)
    except EmptyPage:
        customers = paginator.page(paginator.num_pages)

    cur_user = request.user
    now = datetime.now()

    settings = {'customers': customers,
                'user': cur_user,
                'now': now,
                'search_on': 'customers',
                'placeholder': 'Buscar cliente',
                'title': 'TrapuZarrak · Clientes',
                'h3': 'Todos los clientes',

                # CRUD actions
                'btn_title_add': 'Nuevo cliente',
                'js_class_add': 'js-customer-add',
                'js_action_add': 'customer-add',
                'js_data_pk': '0',

                'include_template': 'includes/customer_list.html',
                'footer': True,
                }

    return render(request, 'tz/list_view.html', settings)


@login_required
def itemslist(request):
    """Show the different item objects."""
    items = Item.objects.all()
    cur_user = request.user
    now = datetime.now()

    settings = {'items': items,
                'user': cur_user,
                'now': now,
                'placeholder': 'Buscar item',
                'search_on': 'items',
                'title': 'TrapuZarrak · Prendas',
                'h3': 'Todos los items',
                'table_id': 'item_objects_list',

                # CRUD Actions
                'btn_title_add': 'Añadir prenda',
                'js_class_add': 'js-item-add',
                'js_action_add': 'item-add',
                'js_action_edit': 'item-edit-item',
                'js_action_delete': 'item-edit-delete',
                'js_data_pk': '0',

                'include_template': 'includes/items_list.html',
                'footer': True,
                }

    return render(request, 'tz/list_view.html', settings)


# Object views
@login_required
def order_view(request, pk):
    """Show all details for an specific order."""
    order = get_object_or_404(Order, pk=pk)
    comments = Comment.objects.filter(reference=order).order_by('-creation')
    items = OrderItem.objects.filter(reference=order)
    times = Timing.objects.filter(reference=order)
    total_time = times.aggregate(Sum('time'))
    try:
        float_time = float(total_time['time__sum'])
    except TypeError:
        total_time = '0:00'
    else:
        total_time = TimeLenght(float_time).convert()

    if order.status == '7' and order.budget == order.prepaid:
        closed = True
    else:
        closed = False

    cur_user = request.user
    now = datetime.now()
    settings = {'order': order,
                'items': items,
                'comments': comments,
                'times': times,
                'total_time': total_time,
                'closed': closed,
                'user': cur_user,
                'now': now,
                'title': 'TrapuZarrak · Ver Pedido',
                'footer': True,
                }

    return render(request, 'tz/order_view.html', settings)


@login_required
def customer_view(request, pk):
    """Display details for an especific customer."""
    customer = get_object_or_404(Customer, pk=pk)
    orders = Order.objects.filter(customer=customer)
    active = orders.exclude(status__in=[7, 8]).order_by('delivery')
    delivered = orders.filter(status=7).order_by('delivery')
    cancelled = orders.filter(status=8).order_by('delivery')

    # Evaluate pending orders
    pending = []
    for order in orders:
        if order.pending < 0:
            pending.append(order)

    cur_user = request.user
    now = datetime.now()
    settings = {'customer': customer,
                'orders_active': active,
                'orders_delivered': delivered,
                'orders_cancelled': cancelled,
                'pending': pending,
                'orders_made': len(orders),
                'user': cur_user,
                'now': now,
                'title': 'TrapuZarrak · Ver cliente',
                'footer': True,
                }
    return render(request, 'tz/customer_view.html', settings)


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
            context = {'form': form}
            template = 'includes/add/add_order.html'

        # Add order from customer (GET)
        elif action == 'order-from-customer':
            customer = get_object_or_404(Customer, pk=pk)
            form = OrderForm(initial={'customer': customer})
            context = {'form': form}
            template = 'includes/add/add_order.html'

        # Add customer (GET)
        elif action == 'customer-add':
            form = CustomerForm()
            context = {'form': form}
            template = 'includes/add/add_customer.html'

        # Add item object (GET)
        elif action == 'item-add':
            form = ItemForm()
            context = {'form': form,
                       'modal_title': 'Añadir prenda',
                       'pk': '0',
                       'action': 'item-object-add',
                       'submit_btn': 'Añadir',
                       }
            template = 'includes/regular_form.html'

        # Add item (GET)
        elif action == 'order-add-item':
            order = get_object_or_404(Order, pk=pk)
            form = OrderItemForm()
            context = {'order': order, 'form': form}
            template = 'includes/add/add_item_to_order.html'

        # Add a comment (GET)
        elif action == 'order-add-comment':
            order = get_object_or_404(Order, pk=pk)
            form = CommentForm()
            context = {'order': order, 'form': form}
            template = 'includes/add/add_comment.html'

        # Add time from order (GET)
        elif action == 'time-from-order':
            order = get_object_or_404(Order, pk=pk)
            form = TimeForm(initial={'reference': order})
            context = {'form': form, 'order': order}
            template = 'includes/add/add_time.html'

        # Edit the order (GET)
        elif action == 'order-edit':
            order = get_object_or_404(Order, pk=pk)
            form = OrderForm(instance=order)
            context = {'order': order, 'form': form}
            template = 'includes/edit/edit_order.html'

        # Edit the date (GET)
        elif action == 'order-edit-date':
            order = get_object_or_404(Order, pk=pk)
            context = {'order': order}
            template = 'includes/edit/edit_date.html'

        # Edit customer (GET)
        elif action == 'customer-edit':
            customer = get_object_or_404(Customer, pk=pk)
            form = CustomerForm(instance=customer)
            context = {'customer': customer, 'form': form}
            template = 'includes/edit/edit_customer.html'

        # Collect order (GET)
        elif action == 'order-pay-now':
            order = get_object_or_404(Order, pk=pk)
            context = {'order': order}
            template = 'includes/edit/pay_order.html'

        # Close order (GET)
        elif action == 'order-close':
            order = get_object_or_404(Order, pk=pk)
            form = OrderCloseForm(instance=order)
            context = {'order': order, 'form': form}
            template = 'includes/edit/close_order.html'

        # Edit Item Object (GET)
        elif action == 'object-item-edit':
            item = get_object_or_404(Item, pk=pk)
            form = ItemForm(instance=item)
            context = {'form': form,
                       'modal_title': 'Editar prenda',
                       'pk': item.pk,
                       'action': 'object-item-edit',
                       'submit_btn': 'Guardar',
                       }
            template = 'includes/regular_form.html'
        # Edit item (GET)
        elif action == 'order-edit-item':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            order = item.reference
            form = OrderItemForm(instance=item)
            context = {'item': item, 'form': form}
            template = 'includes/edit/edit_item.html'

        # Edit time (GET)
        elif action == 'order-edit-time':
            get_object_or_404(Timing, pk=pk)
            time = Timing.objects.select_related('reference').get(pk=pk)
            form = TimeForm(instance=time)
            context = {'time': time, 'form': form}
            template = 'includes/edit/edit_time.html'

        # Delete item (GET)
        elif action == 'order-delete-item':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            context = {'item': item}
            template = 'includes/delete/delete_item.html'

        # Delete Customer (GET)
        elif action == 'customer-delete':
            customer = get_object_or_404(Customer, pk=pk)
            context = {'customer': customer}
            template = 'includes/delete/delete_customer.html'

        # Delete Time
        elif action == 'time-delete':
            time = get_object_or_404(Timing, pk=pk)
            context = {'time': time}
            template = 'includes/delete/delete_time.html'

        # logout
        elif action == 'logout':
            context = dict()
            template = 'registration/logout.html'

        else:
            raise NameError('Action was not recogniced')

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
                return redirect('order_view', pk=order.pk)
            else:
                data['form_is_valid'] = False
                context = {'form': form}
                template = 'includes/add/add_order.html'

        # Add Customer (POST)
        elif action == 'customer-new':
            form = CustomerForm(request.POST)
            if form.is_valid():
                customer = form.save(commit=False)
                customer.creation = timezone.now()
                customer.save()
                return redirect('customer_view', pk=customer.pk)
            else:
                data['form_is_valid'] = False
                context = {'form': form}
                template = 'includes/add/add_customer.html'

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
                context = {'form': form, 'comments': comments}
                template = 'includes/comment_list.html'
            else:
                data['form_is_valid'] = False
                context = {'order': order, 'form': form}
                template = 'includes/add/add_comment.html'

        # Mark comment as read
        elif action == 'comment-read':
            comment = get_object_or_404(Comment, pk=pk)
            comment.read = True
            comment.save()
            return redirect('main')

        # Add new item Objects
        elif action == 'item-object-add':
            form = ItemForm(request.POST)
            if form.is_valid():
                add_item = form.save()
                items = Item.objects.all()
                data['html_id'] = '#item_objects_list'
                data['form_is_valid'] = True
                context = {'form': form,
                           'items': items,
                           'js_action_edit': 'item-edit-item',
                           'js_action_delete': 'item-edit-delete',
                           }
                template = 'includes/items_list.html'

        # Attach item to order (POST)
        elif action == 'order-add-item':
            order = get_object_or_404(Order, pk=pk)
            form = OrderItemForm(request.POST)
            if form.is_valid():
                add_item = form.save(commit=False)
                add_item.reference = order
                add_item.save()
                items = OrderItem.objects.filter(reference=order)
                template = 'includes/order_details.html'
                context = {'form': form, 'order': order, 'items': items}
                data['form_is_valid'] = True
                data['html_id'] = '#order-details'
            else:
                context = {'order': order, 'form': form}
                template = 'includes/add/add_item_to_order.html'
                data['form_is_valid'] = False

        # Add time (POST)
        elif action == 'time-new':
            order = get_object_or_404(Order, pk=pk)
            form = TimeForm(request.POST)
            if form.is_valid():
                new_time = form.save(commit=False)
                duration_str = request.POST.get('time')
                new_time.time = TimeLenght(duration_str).convert()
                new_time.save()
                times = Timing.objects.filter(reference=order)
                template = 'includes/timing_list.html'
                context = {'times': times, 'order': order}
                data['form_is_valid'] = True
                data['html_id'] = '#timing-list'
            else:
                data['form_is_valid'] = False
                context = {'form': form}
                template = 'includes/add/add_time.html'

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
                context = {'order': order, 'form': form}
                template = 'includes/add/add_order.html'

        # Edit date (POST)
        elif action == 'order-edit-date':
            order = get_object_or_404(Order, pk=pk)
            new_date = self.request.POST.get('delivery', None)
            order.delivery = new_date
            try:
                order.save()
            except ValidationError:
                data['form_is_valid'] = False
            else:
                data['form_is_valid'] = True
                data['reload'] = True
            return JsonResponse(data)

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
                context = {'customer': customer, 'form': form}
                template = 'includes/edit/edit_customer.html'

        # Edit item objects (POST)
        elif action == 'object-item-edit':
            item = get_object_or_404(Item, pk=pk)
            form = ItemForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                items = Item.objects.all()
                data['html_id'] = '#item_objects_list'
                data['form_is_valid'] = True
                context = {'form': form,
                           'items': items,
                           'js_action_edit': 'object-item-edit',
                           'js_action_delete': 'object-item-delete',
                           }
                template = 'includes/items_list.html'
        # Edit item (POST)
        elif action == 'order-edit-item':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            order = item.reference
            form = OrderItemForm(request.POST, instance=item)
            items = OrderItem.objects.filter(reference=order)
            if form.is_valid():
                # DEBUG: get rid of 'form'
                context = {'form': form, 'order': order, 'items': items}
                template = 'includes/order_details.html'
                form.save()
                data['form_is_valid'] = True
                data['html_id'] = '#order-details'
            else:
                context = {'item': item, 'form': form}
                template = 'includes/edit/edit_item.html'
                data['form_is_valid'] = False

        # Edit time (POST)
        elif action == 'time-edit':
            time = get_object_or_404(Timing, pk=pk)
            time = Timing.objects.select_related('reference').get(pk=pk)
            order = time.reference
            times = Timing.objects.filter(reference=order)
            try:
                form_time = TimeLenght(request.POST.get('time')).convert()
            except ValueError:
                form_time = False
            form = TimeForm(request.POST, instance=time)
            if form.is_valid() and form_time:
                context = {'order': order, 'times': times}
                template = 'includes/timing_list.html'
                new_time = form.save(commit=False)
                new_time.time = form_time
                new_time.save()
                data['form_is_valid'] = True
                data['html_id'] = '#timing-list'
            else:
                context = {'time': time, 'form': form}
                template = 'includes/edit/edit_time.html'
                data['form_is_valid'] = False

        # Collect order (POST)
        elif action == 'order-pay-now':
            order = get_object_or_404(Order, pk=pk)
            order.prepaid = order.budget
            try:
                order.save()
            except ValidationError:  # pragma: no cover
                data['form_is_valid'] = False
            else:
                data['form_is_valid'] = True
                data['html_id'] = '#order-status'
                template = 'includes/order_status.html'
                context = {'order': order}

        # Close order (POST)
        elif action == 'order-close':
            order = get_object_or_404(Order, pk=pk)
            form = OrderCloseForm(request.POST, instance=order)
            if form.is_valid():
                close = form.save(commit=False)
                close.status = 7
                close.delivery = timezone.now()
                close.save()
                data['form_is_valid'] = True
                data['reload'] = True
                return JsonResponse(data)
            else:
                data['form_is_valid'] = False
                context = {'order': order, 'form': form}
                template = 'includes/edit/close_order.html'

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
                order.save()
                data['form_is_valid'] = True
                data['html_id'] = '#order-status'
                template = 'includes/order_status.html'
                context = {'order': order}

        # Delete item (POST)
        elif action == 'order-delete-item':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            order = item.reference
            items = OrderItem.objects.filter(reference=order)
            item.delete()
            data['form_is_valid'] = True
            data['html_id'] = '#order-details'
            context = {'order': order, 'items': items}
            template = 'includes/order_details.html'

        # delete time (POST)
        elif action == 'time-delete':
            get_object_or_404(Timing, pk=pk)
            time = Timing.objects.select_related('reference').get(pk=pk)
            times = Timing.objects.filter(reference=time.reference)
            order = time.reference
            time.delete()
            data['form_is_valid'] = True
            data['html_id'] = '#timing-list'
            context = {'times': times, 'order': order}
            template = 'includes/timing_list.html'

        # Delete customer (POST)
        elif action == 'customer-delete':
            customer = get_object_or_404(Customer, pk=pk)
            customer.delete()
            return redirect('customerlist')

        # logout (POST)
        elif action == 'logout':
            logout(request)
            return redirect('login')

        else:
            raise NameError('Action was not recogniced')

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

        # Now render_to_string the html for JSON response
        data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)
