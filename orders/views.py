"""Define all the views for the app."""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse, Http404, HttpResponseBadRequest
from django.template.loader import render_to_string
from .models import Comment, Customer, Order, OrderItem, Timing, Item
from .utils import TimeLenght
from django.utils import timezone
from .forms import (CustomerForm, OrderForm, CommentForm, ItemForm,
                    OrderCloseForm, OrderItemForm, EditDateForm)
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Count, Sum, F
from datetime import datetime
from . import settings
import markdown2


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
    pending_total = budgets['budget__sum'] - prepaid['prepaid__sum']

    cur_user = request.user

    # Query last comments on active orders
    comments = Comment.objects.exclude(user=cur_user)
    comments = comments.exclude(read=True)
    comments = comments.order_by('-creation')

    now = datetime.now()

    view_settings = {'orders': orders,
                     'orders_count': len(orders),
                     'comments': comments,
                     'comments_count': len(comments),
                     'pending': pending,
                     'pending_total': pending_total,
                     'pending_count': len(pending),
                     'user': cur_user,
                     'now': now,
                     'version': settings.VERSION,
                     'search_on': 'orders',
                     'placeholder': 'Buscar pedido (referencia)',
                     'title': 'TrapuZarrak · Inicio',
                     'footer': True,
                     }

    return render(request, 'tz/main.html', view_settings)


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
        tz_active = tz_orders.exclude(status__in=[7, 8]).order_by('delivery')
        tz_delivered = tz_orders.filter(status=7).order_by('-delivery')[:10]

        # And the attr collection for them
        tz_active = tz_active.annotate(Count('orderitem', distinct=True),
                                       Count('comment', distinct=True),
                                       Count('timing', distinct=True))
        tz_delivered = tz_delivered.annotate(Count('orderitem', distinct=True),
                                             Count('comment', distinct=True),
                                             Count('timing', distinct=True))

        # Finally, exclude tz customer for further queries and sort
        orders = orders.exclude(customer=tz)

    # If tz customer doesn't exist, these vars should be none
    else:
        tz_active = None
        tz_delivered = None

    delivered = orders.filter(status=7).order_by('-delivery')[:10]
    active = orders.exclude(status__in=[7, 8])
    cancelled = orders.filter(status=8).order_by('-inbox_date')[:10]
    pending = orders.exclude(status=8).filter(budget__gt=F('prepaid'))
    pending = pending.order_by('inbox_date')

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

    view_settings = {'active': active,
                     'delivered': delivered,
                     'user': cur_user,
                     'now': now,
                     'version': settings.VERSION,
                     'active_stock': tz_active,
                     'delivered_stock': tz_delivered,
                     'cancelled': cancelled,
                     'pending': pending,
                     'pending_total': pending_total,
                     'order_by': orderby,
                     'placeholder': 'Buscar pedido (referencia o nº)',
                     'search_on': 'orders',
                     'title': 'TrapuZarrak · Pedidos',
                     'colors': settings.WEEK_COLORS,
                     'footer': True,
                     }

    return render(request, 'tz/orders.html', view_settings)


@login_required
def customerlist(request):
    """Display all customers or search'em."""
    customers = Customer.objects.all().order_by('name')
    customers = customers.annotate(num_orders=Count('order'))
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

    view_settings = {'customers': customers,
                     'user': cur_user,
                     'now': now,
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
                     'footer': True,
                     }

    return render(request, 'tz/list_view.html', view_settings)


@login_required
def itemslist(request):
    """Show the different item objects."""
    items = Item.objects.all()
    cur_user = request.user
    now = datetime.now()

    view_settings = {'items': items,
                     'user': cur_user,
                     'now': now,
                     'version': settings.VERSION,
                     'search_on': 'items',
                     'title': 'TrapuZarrak · Prendas',
                     'h3': 'Todas las prendas',
                     'table_id': 'item_objects_list',
                     'item_types': settings.ITEM_TYPE[1:],
                     'item_classes': settings.ITEM_CLASSES,
                     'add_to_order': True,

                     # CRUD Actions
                     'btn_title_add': 'Añadir prenda',
                     'js_action_add': 'object-item-add',
                     'js_action_edit': 'object-item-edit',
                     'js_action_delete': 'object-item-delete',
                     'js_action_send_to': 'send-to-order',
                     'js_data_pk': '0',

                     'include_template': 'includes/items_list.html',
                     'footer': True,
                     }

    return render(request, 'tz/list_view.html', view_settings)


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
        total_time = TimeLenght(float_time).convert()  # pragma: no cover

    if order.status == '7' and order.budget == order.prepaid:
        closed = True
    else:
        closed = False

    cur_user = request.user
    now = datetime.now()
    view_settings = {'order': order,
                     'items': items,
                     'comments': comments,
                     'times': times,
                     'total_time': total_time,
                     'closed': closed,
                     'user': cur_user,
                     'now': now,
                     'version': settings.VERSION,
                     'title': 'TrapuZarrak · Ver Pedido',

                     # CRUD Actions
                     'btn_title_add': 'Añadir prenda',
                     'js_action_add': 'order-item-add',
                     'js_action_edit': 'order-item-edit',
                     'js_action_delete': 'order-item-delete',
                     'js_data_pk': order.pk,
                     'footer': True,
                     }

    return render(request, 'tz/order_view.html', view_settings)


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
    view_settings = {'customer': customer,
                     'orders_active': active,
                     'orders_delivered': delivered,
                     'orders_cancelled': cancelled,
                     'pending': pending,
                     'orders_made': len(orders),
                     'user': cur_user,
                     'now': now,
                     'version': settings.VERSION,
                     'title': 'TrapuZarrak · Ver cliente',
                     'footer': True,
                     }
    return render(request, 'tz/customer_view.html', view_settings)


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

        # Add customer (GET)
        elif action == 'customer-add':
            form = CustomerForm()
            context = {'form': form,
                       'modal_title': 'Añadir Cliente',
                       'pk': '0',
                       'action': 'customer-new',
                       'submit_btn': 'Añadir',
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
            context = {'orders': Order.objects.exclude(status__in=[7, 8]),
                       'modal_title': 'Añadir prenda a pedido',
                       'pk': pk,
                       'action': 'send-to-order',
                       'submit_btn': 'Añadir a pedido',
                       'custom_form': custom_form,
                       }
            template = 'includes/regular_form.html'

        # Add order item (GET)
        elif action == 'order-item-add':
            order = get_object_or_404(Order, pk=pk)
            form = OrderItemForm()
            context = {'form': form,
                       'order': order,
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
                       }
            template = 'includes/regular_form.html'

        # Collect order (GET)
        elif action == 'order-pay-now':
            order = get_object_or_404(Order, pk=pk)
            context = {'modal_title': 'Cobrar Pedido',
                       'msg': ('Marcar el pedido como cobrado (%s€)?'
                               % order.budget),
                       'pk': order.pk,
                       'action': 'order-pay-now',
                       'submit_btn': 'Sí, cobrar'}
            template = 'includes/confirmation.html'

        # Close order (GET)
        elif action == 'order-close':
            order = get_object_or_404(Order, pk=pk)
            form = OrderCloseForm(instance=order)
            context = {'form': form,
                       'order': order,
                       'modal_title': 'Cerrar pedido',
                       'pk': order.pk,
                       'action': 'order-close',
                       'submit_btn': 'Cerrar pedido',
                       'custom_form': 'includes/custom_forms/close_order.html'
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

        # logout
        elif action == 'logout':
            context = dict()
            template = 'registration/logout.html'

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
                context = {'form': form,
                           'modal_title': 'Añadir Pedido',
                           'pk': '0',
                           'action': 'order-new',
                           'submit_btn': 'Añadir',
                           'custom_form': 'includes/custom_forms/order.html',
                           }
                template = 'includes/regular_form.html'

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
                context = {'form': form, 'comments': comments}
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
            return redirect('main')

        # Add new item Objects (POST)
        elif action == 'object-item-add':
            form = ItemForm(request.POST)
            if form.is_valid():
                add_item = form.save()
                items = Item.objects.all()
                data['html_id'] = '#item_objects_list'
                data['form_is_valid'] = True
                context = {'items': items,
                           'js_action_edit': 'object-item-edit',
                           'js_action_delete': 'object-item-delete',
                           'js_action_send_to': 'send-to-order',
                           }
                template = 'includes/items_list.html'
            else:
                data['form_is_valid'] = False
                context = {'form': form,
                           'modal_title': 'Añadir prenda',
                           'pk': '0',
                           'action': 'object-item-add',
                           'submit_btn': 'Añadir',
                           }
                template = 'includes/regular_form.html'

        # Send item to order (POST)
        elif action == 'send-to-order':
            item = get_object_or_404(Item,
                                     pk=self.request.POST.get('pk', None))
            order = get_object_or_404(Order,
                                      pk=self.request.POST.get('order', None))
            if self.request.POST.get('isfit', None) == '1':
                is_fit = True
            elif self.request.POST.get('isfit', None) == '0':
                is_fit = False
            else:
                raise Http404('No info given abot fit')
            OrderItem.objects.create(element=item, reference=order, fit=is_fit)
            return redirect('order_view', pk=order.pk)

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
                           }
                template = 'includes/regular_form.html'

        # Edit item objects (POST)
        elif action == 'object-item-edit':
            item = get_object_or_404(Item, pk=pk)
            form = ItemForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                items = Item.objects.all()
                data['html_id'] = '#item_objects_list'
                data['form_is_valid'] = True
                context = {'items': items,
                           'js_action_edit': 'object-item-edit',
                           'js_action_delete': 'object-item-delete',
                           'js_action_send_to': 'send-to-order',
                           }
                template = 'includes/items_list.html'
            else:
                data['form_is_valid'] = False
                context = {'form': form,
                           'modal_title': 'Editar prenda',
                           'pk': item.pk,
                           'action': 'object-item-edit',
                           'submit_btn': 'Guardar',
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
                template = 'includes/order_details.html'
                form.save()
                data['form_is_valid'] = True
                data['html_id'] = '#order-details'
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

        # Collect order (POST)
        elif action == 'order-pay-now':
            order = get_object_or_404(Order, pk=pk)
            order.prepaid = order.budget
            try:
                order.save()
            except ValidationError:  # pragma: no cover
                data['form_is_valid'] = False
                context = {'modal_title': 'Cobrar Pedido',
                           'msg': 'Algo ha ido mal, reintentar?',
                           'pk': order.pk,
                           'action': 'order-pay-now',
                           'submit_btn': 'Sí, reintentar'}
                template = 'includes/confirmation.html'
            else:
                data['form_is_valid'] = True
                data['reload'] = True
                return JsonResponse(data)

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
                custom_form = 'includes/custom_forms/close_order.html'
                context = {'form': form,
                           'order': order,
                           'modal_title': 'Cerrar pedido',
                           'pk': order.pk,
                           'action': 'order-close',
                           'submit_btn': 'Cerrar pedido',
                           'custom_form': custom_form,
                           }
                template = 'includes/regular_form.html'

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

        # Delete object Item
        elif action == 'object-item-delete':
            item = get_object_or_404(Item, pk=pk)
            item.delete()
            items = Item.objects.all()
            data['html_id'] = '#item_objects_list'
            data['form_is_valid'] = True
            context = {'items': items,
                       'js_action_edit': 'object-item-edit',
                       'js_action_delete': 'object-item-delete',
                       'js_action_send_to': 'send-to-order',
                       }
            template = 'includes/items_list.html'

        # Delete item (POST)
        elif action == 'order-item-delete':
            get_object_or_404(OrderItem, pk=pk)
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            order = item.reference
            items = OrderItem.objects.filter(reference=order)
            item.delete()
            data['form_is_valid'] = True
            data['html_id'] = '#order-details'
            context = {'items': items,
                       'order': order,
                       'btn_title_add': 'Añadir prenda',
                       'js_action_add': 'order-item-add',
                       'js_action_edit': 'order-item-edit',
                       'js_action_delete': 'order-item-delete',
                       'js_data_pk': order.pk,
                       }
            template = 'includes/order_details.html'

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
            raise NameError('Action was not recogniced', action)

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


def filter_items(request):
    """Filter the item objects list."""
    if request.method != 'GET':
        raise Http404('The filter should go in a get request')
    data = dict()
    items = Item.objects.all()
    by_name = request.GET.get('search-obj')
    by_type = request.GET.get('item-type')
    by_class = request.GET.get('item-class')

    if not by_name and not by_type and not by_class:
        filter_on = False
    else:
        filter_on = 'Filtrando'
        if by_name:
            items = items.filter(name__istartswith=by_name)
            if items:
                filter_on = '%s %s' % (filter_on, by_name)
        else:
            filter_on = '%s elementos' % filter_on
        if by_type and by_type != 'all':
            items = items.filter(item_type=by_type)
            if items:
                display = items[0].get_item_type_display()
                filter_on = '%s en %ss' % (filter_on, display)
        if by_class and by_class != 'all':
            items = items.filter(item_class=by_class)
            if items:
                display = items[0].get_item_class_display()
                filter_on = '%s con acabado %s' % (filter_on, display)

        if not items:
            filter_on = 'El filtro no devolvió ningún resultado'

    context = {'items': items,
               'item_types': settings.ITEM_TYPE[1:],
               'item_classes': settings.ITEM_CLASSES,
               'add_to_order': True,
               'filter_on': filter_on,
               'js_action_send_to': 'send-to-order',
               'js_action_edit': 'object-item-edit',
               'js_action_delete': 'object-item-delete',
               }
    template = 'includes/items_list.html'
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
        data['filter_on'] = filter_on
        data['len_items'] = len(items)

    return JsonResponse(data)
