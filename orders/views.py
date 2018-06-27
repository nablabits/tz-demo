from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import Comment, Customer, Order, Document, OrderItem
from django.utils import timezone
from .forms import CustomerForm, OrderForm, CommentForm, DocumentForm
from .forms import OrderCloseForm, OrderItemForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime


# Root View
@login_required()
def main(request):
    """Create the root view."""
    # Query all active orders
    orders = Order.objects.exclude(status=7).order_by('delivery')
    orders = orders.exclude(status=8)
    orders_count = len(orders)

    cur_user = request.user

    # Query last comments on active orders
    comments = Comment.objects.exclude(user=cur_user)
    comments = comments.exclude(read=True)
    comments = comments.order_by('-creation')
    comments_count = len(comments)

    now = datetime.now()

    settings = {'orders': orders,
                'orders_count': orders_count,
                'comments': comments,
                'comments_count': comments_count,
                'user': cur_user,
                'now': now,
                'search_on': 'orders',
                'placeholder': 'Buscar pedido',
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
        if search_on == 'orders':
            table = Order.objects.all()
            query_result = table.filter(ref_name__icontains=search_obj)
            model = 'orders'
        elif search_on == 'customers':
            table = Customer.objects.all()
            query_result = table.filter(name__icontains=search_obj)
            model = 'customers'
        else:
            raise ValueError('Search on undefined')
        template = 'includes/search_results.html'
        context = {'query_result': query_result, 'model': model}
        data['html'] = render_to_string(template, context, request=request)
        return JsonResponse(data)
    else:
        raise TypeError('Invalid request method')


# Order related views
@login_required
def orderlist(request):
    """Display all orders or search'em."""
    orders = Order.objects.all().order_by('delivery')
    active = orders.exclude(status=7).order_by('delivery')
    delivered = orders.filter(status=7).order_by('delivery')
    page = request.GET.get('page', 1)
    paginator = Paginator(delivered, 3)
    try:
        delivered = paginator.page(page)
    except PageNotAnInteger:
        delivered = paginator.page(1)
    except EmptyPage:
        delivered = paginator.page(paginator.num_pages)

    cur_user = request.user
    now = datetime.now()

    settings = {'active': active,
                'delivered': delivered,
                'user': cur_user,
                'now': now,
                'placeholder': 'Buscar pedido',
                'search_on': 'orders',
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


class Actions(View):
    """Unify all the AJAX actions in a single view.

    With this view we'll be able to edit, upload & delete files, add comments
    or close orders. While let CRUD with customers
    """

    def get(self, request):
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

        # Add item (GET)
        elif action == 'order-add-item':
            order = get_object_or_404(Order, pk=pk)
            form = OrderItemForm()
            context = {'order': order, 'form': form}
            template = 'includes/add/add_item.html'

        # Add a comment (GET)
        elif action == 'order-add-comment':
            order = get_object_or_404(Order, pk=pk)
            form = CommentForm()
            context = {'order': order, 'form': form}
            template = 'includes/add/add_comment.html'

        # Add file (GET)
        elif action == 'order-add-file':
            order = get_object_or_404(Order, pk=pk)
            form = DocumentForm()
            context = {'order': order, 'form': form}
            template = 'includes/add/add_file.html'

        # Edit the order (GET)
        elif action == 'order-edit':
            order = get_object_or_404(Order, pk=pk)
            form = OrderForm(instance=order)
            context = {'order': order, 'form': form}
            template = 'includes/edit/edit_order.html'

        # Edit customer (GET)
        elif action == 'customer-edit':
            customer = get_object_or_404(Customer, pk=pk)
            form = CustomerForm(instance=customer)
            context = {'customer': customer, 'form': form}
            template = 'includes/edit/edit_customer.html'

        # Close order (GET)
        elif action == 'order-close':
            order = get_object_or_404(Order, pk=pk)
            form = OrderCloseForm(instance=order)
            context = {'order': order, 'form': form}
            template = 'includes/edit/close_order.html'

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

        # Delete file (GET)
        elif action == 'order-delete-file':
            file = get_object_or_404(Document, pk=pk)
            context = {'file': file}
            template = 'includes/delete/delete_file.html'

        # Delete Customer (GET)
        elif action == 'customer-delete':
            customer = get_object_or_404(Customer, pk=pk)
            context = {'customer': customer}
            template = 'includes/delete/delete_customer.html'

        # logout
        elif action == 'logout':
            context = dict()
            template = 'registration/logout.html'

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

        # Add Order (POST)
        if action == 'order-new':
            form = OrderForm(request.POST)
            if form.is_valid():
                order = form.save(commit=False)
                order.creation = timezone.now()
                order.user = request.user
                order.save()
                return redirect('order_view', pk=order.pk)

        # Add Customer (POST)
        elif action == 'customer-new':
            form = CustomerForm(request.POST)
            if form.is_valid():
                customer = form.save(commit=False)
                customer.creation = timezone.now()
                customer.save()
                return redirect('customer_view', pk=customer.pk)

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

        # Mark comment as read
        elif action == 'comment-read':
            comment = get_object_or_404(Comment, pk=pk)
            comment.read = True
            comment.save()
            return redirect('main')

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

        # Add file (POST)
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
                raise ValueError('form is not valid')
                context = {'order': order, 'form': form}
                template = 'includes/add/add_file.html'
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

        # Update status (POST)
        elif action == 'update-status':
            status = self.request.POST.get('status', None)
            order = get_object_or_404(Order, pk=pk)
            order.status = status
            order.save()
            if status in ('1', '8'):
                data['reload'] = True
                return JsonResponse(data)
            else:
                data['form_is_valid'] = True
                data['html_id'] = '#order-status'
                template = 'includes/order_status.html'
                context = {'order': order}

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

        # Delete customer (POST)
        elif action == 'customer-delete':
            customer = get_object_or_404(Customer, pk=pk)
            customer.delete()
            return redirect('customerlist')

        # logout (POST)
        elif action == 'logout':
            template = ''
            context = ''
            logout(request)

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
                'search_on': 'customers',
                'placeholder': 'Buscar cliente',
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
