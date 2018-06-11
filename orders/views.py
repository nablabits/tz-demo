from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import Comment, Customer, Order, Document, OrderItem
from django.utils import timezone
from .forms import CustomerForm, OrderForm, CommentForm, DocumentForm
from .forms import OrderCloseForm, OrderItemForm
from django.contrib.auth.decorators import login_required
from datetime import datetime


# Root View
@login_required()
def main(request):
    """Create the root view."""
    # Query all active orders
    orders = Order.objects.exclude(status=7).order_by('delivery')
    orders_count = len(orders)

    # Query last comments on active orders
    comments = Comment.objects.filter(reference__in=orders)
    comments = comments.order_by('-creation')

    cur_user = request.user
    now = datetime.now()

    settings = {'orders': orders,
                'orders_count': orders_count,
                'comments': comments,
                'user': cur_user,
                'now': now,
                'title': 'TrapuZarrak · Inicio',
                'footer': True,
                }

    return render(request, 'tz/main.html', settings)


# Order related views
@login_required
def orderlist(request):
    """Display all orders or search'em."""
    orders = Order.objects.all().order_by('delivery')
    active = orders.exclude(status=7).order_by('delivery')
    delivered = orders.filter(status=7).order_by('delivery')

    cur_user = request.user
    now = datetime.now()

    settings = {'active': active,
                'delivered': delivered,
                'user': cur_user,
                'now': now,
                'title': 'TrapuZarrak · Pedidos',
                'footer': True,
                }

    return render(request, 'tz/orders.html', settings)


@login_required
def order_view(request, pk):
    """Show all details for an specific order."""
    order = get_object_or_404(Order, pk=pk)
    comments = Comment.objects.filter(reference=order).order_by('-creation')
    files = Document.objects.filter(order=order)
    items = OrderItem.objects.filter(reference=order)

    cur_user = request.user
    now = datetime.now()
    settings = {'order': order,
                'items': items,
                'comments': comments,
                'files': files,
                'user': cur_user,
                'now': now,
                'title': 'TrapuZarrak · Ver Pedido',
                'footer': True,
                }

    return render(request, 'tz/order_view.html', settings)


@login_required()
def order_new(request):
    """Create new orders with a form view."""
    if request.method == "POST":
        """ When coming from edit view, save the changes (if they are valid)
        and jump to main page
        """
        form = OrderForm(request.POST)

        if form.is_valid():
            customer = form.save(commit=False)
            customer.creation = timezone.now()
            customer.user = request.user
            customer.save()
            return redirect('main')
    else:
        form = OrderForm()
        now = datetime.now()
        settings = {'form': form,
                    'now': now,
                    'title': 'TrapuZarrak · Nuevo Pedido',
                    'footer': False,
                    }
        return render(request, 'tz/order_new.html', settings)


class OrderActions(View):
    """Unify all the AJAX actions in a single view.

    With this view we'll be able to edit, upload & delete files, add comments
    or close the order.
    """

    def get(self, request):
        data = dict()
        pk = self.request.GET.get('pk', None)
        action = self.request.GET.get('action', None)

        if not pk or not action:
            raise ValueError('Unexpected GET data')

        # Edit the order (GET)
        if action == 'order-edit':
            order = get_object_or_404(Order, pk=pk)
            form = OrderForm(instance=order)
            context = {'order': order, 'form': form}
            template = 'includes/edit/edit_order.html'

        # Add item (GET)
        elif action == 'order-add-item':
            order = get_object_or_404(Order, pk=pk)
            form = OrderItemForm()
            context = {'order': order, 'form': form}
            template = 'includes/add/add_item.html'

        # Edit item (GET)
        elif action == 'order-edit-item':
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            order = item.reference
            form = OrderItemForm(instance=item)
            context = {'item': item, 'form': form}
            template = 'includes/edit/edit_item.html'

        # Delete item (GET)
        elif action == 'order-delete-item':
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            context = {'item': item}
            template = 'includes/delete/delete_item.html'

        # Close order (GET)
        elif action == 'order-close':
            order = get_object_or_404(Order, pk=pk)
            form = OrderCloseForm(instance=order)
            context = {'order': order, 'form': form}
            template = 'includes/edit/close_order.html'

        # Add a comment (GET)
        elif action == 'order-add-comment':
            order = get_object_or_404(Order, pk=pk)
            form = CommentForm()
            context = {'order': order, 'form': form}
            template = 'includes/add/add_comment.html'

        # Upload a file (GET)
        elif action == 'order-add-file':
            order = get_object_or_404(Order, pk=pk)
            form = DocumentForm()
            context = {'order': order, 'form': form}
            template = 'includes/add/add_file.html'

        # Delete file (GET)
        elif action == 'order-delete-file':
            file = get_object_or_404(Document, pk=pk)
            context = {'file': file}
            template = 'includes/delete/delete_file.html'

        else:
            raise NameError('Action was not recogniced')

        data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)

    def post(self, request):
        data = dict()
        pk = self.request.POST.get('pk', None)
        action = self.request.POST.get('action', None)

        if not pk or not action:
            raise ValueError('POST data was poor')

        # Edit the order (POST)
        if action == 'order-edit':
            order = get_object_or_404(Order, pk=pk)
            form = OrderForm(request.POST, instance=order)
            if form.is_valid():
                form.save()
                data['form_is_valid'] = True
                data['html_id'] = '#order-details'
                items = OrderItem.objects.filter(reference=order)
                context = {'form': form, 'order': order, 'items': items}
                template = 'includes/order_details.html'
            else:
                data['form_is_valid'] = False

        # Add item (POST)
        elif action == 'order-add-item':
            order = get_object_or_404(Order, pk=pk)
            form = OrderItemForm(request.POST)
            template = 'includes/order_details.html'
            items = OrderItem.objects.filter(reference=order)
            context = {'form': form, 'order': order, 'items': items}
            if form.is_valid():
                add_item = form.save(commit=False)
                add_item.reference = order
                add_item.save()
                data['form_is_valid'] = True
                data['html_id'] = '#order-details'
            else:
                data['form_is_valid'] = False

        # Edit item (POST)
        elif action == 'order-edit-item':
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            order = item.reference
            form = OrderItemForm(request.POST, instance=item)
            template = 'includes/order_details.html'
            items = OrderItem.objects.filter(reference=order)
            context = {'form': form, 'order': order, 'items': items}
            if form.is_valid():
                form.save()
                data['form_is_valid'] = True
                data['html_id'] = '#order-details'
            else:
                data['form_is_valid'] = False

        # Delete item (POST) define
        elif action == 'order-delete-item':
            item = OrderItem.objects.select_related('reference').get(pk=pk)
            order = item.reference
            items = OrderItem.objects.filter(reference=order)
            item.delete()
            data['form_is_valid'] = True
            data['html_id'] = '#order-details'
            context = {'order': order, 'items': items}
            template = 'includes/order_details.html'

        # Close order (POST)
        elif action == 'order-close':
            order = get_object_or_404(Order, pk=pk)
            form = OrderCloseForm(request.POST, instance=order)
            if form.is_valid():
                close = form.save(commit=False)
                close.status = 7
                close.save()
                data['form_is_valid'] = True
                data['html_id'] = '#order-status'
                template = 'includes/order_status.html'
                context = {'form': form, 'order': order}

        # Add a comment (POST)
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

        # Upload a file (POST)
        elif action == 'order-add-file':
            order = get_object_or_404(Order, pk=pk)
            form = DocumentForm(request.POST, request.FILES)
            if form.is_valid():
                upload = form.save(commit=False)
                upload.order = order
                upload.save()
                data['form_is_valid'] = True
                return redirect('order_view', pk=pk)
            else:
                data['form_is_valid'] = False

        # Delete file (POST)
        elif action == 'order-delete-file':
            file = Document.objects.select_related('order').get(pk=pk)
            order = file.order
            files = Document.objects.filter(order=order)
            file.delete()
            data['form_is_valid'] = True
            data['html_id'] = '#file-list'
            context = {'files': files}
            template = 'includes/file_list.html'

        # Update status (POST)
        elif action == 'update-status':
            status = self.request.POST.get('status', None)
            order = get_object_or_404(Order, pk=pk)
            order.status = status
            order.save()
            data['form_is_valid'] = True
            data['html_id'] = '#order-status'
            template = 'includes/order_status.html'
            context = {'order': order}

        else:
            raise NameError('Action was not recogniced')

        data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)


# Customer related views
@login_required
def customerlist(request):
    """Display all customers or search'em."""
    customers = Customer.objects.all().order_by('name')

    cur_user = request.user
    now = datetime.now()
    # count_orders = Customer.orders_made

    settings = {'customers': customers,
                'user': cur_user,
                'now': now,
                'title': 'TrapuZarrak · Clientes',
                'footer': True,
                }

    return render(request, 'tz/customers.html', settings)


@login_required
def customer_view(request, pk):
    """Display details for an especific customer."""
    customer = get_object_or_404(Customer, pk=pk)
    orders = Order.objects.filter(customer=customer)
    active = orders.exclude(status=7).order_by('delivery')
    delivered = orders.filter(status=7).order_by('delivery')

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
                'pending': pending,
                'user': cur_user,
                'now': now,
                'title': 'TrapuZarrak · Ver cliente',
                'footer': True,
                }
    return render(request, 'tz/customer_view.html', settings)


# Login related views
@login_required()
def customer_new(request):
    """Create new customers with a form view."""
    if request.method == "POST":
        """ When coming from edit view, save the changes (if they are valid)
        and jump to main page
        """
        form = CustomerForm(request.POST)

        if form.is_valid():
            customer = form.save(commit=False)
            customer.creation = timezone.now()
            customer.save()
            return redirect('main')
    else:
        form = CustomerForm()
        now = datetime.now()
        return render(request, 'tz/customer_new.html',
                      {'form': form,
                       'now': now,
                       'title': 'TrapuZarrak · Nuevo Cliente',
                       'footer': False,
                       })


@login_required
def customer_edit(request, pk):
    """Edit or update a customer's data."""
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('customer_view')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'tz/customer_new.html',
                  {'form': form,
                   'edit': True,
                   })
