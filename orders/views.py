from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import Comment, Customer, Order, CommentCheck
from django.utils import timezone
from .forms import CustomerForm, OrderForm, CommentForm
from django.contrib.auth.decorators import login_required
from datetime import datetime


# Root View
@login_required()
def main(request):
    """Create the root view."""
    # Query all active orders
    orders = Order.objects.exclude(status=7).order_by('delivery')
    orders_count = len(orders)

    # Query last commnents on active orders
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

    cur_user = request.user
    now = datetime.now()
    settings = {'order': order,
                'comments': comments,
                'user': cur_user,
                'now': now,
                'title': 'TrapuZarrak · Ver Pedido',
                'footer': True,
                }

    return render(request, 'tz/order_view.html', settings)


@login_required()
def order_new(request):
    """Create new customers with a form view."""
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


@login_required
def order_edit(request, pk):
    """Edit an already created order."""
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('order_view', pk=order.pk)
    else:
        form = OrderForm(instance=order)
        return render(request, 'tz/order_new.html',
                      {'form': form,
                       'edit': True,
                       })


# Order related views (JSON for ajax)
def order_get_status(request):
    """Return order status in JSON mode so Ajax can implement."""
    data = dict()
    pk = request.GET.get('pk', None)
    order = get_object_or_404(Order, pk=pk)
    template = 'includes/order_status.html'
    data['html_status'] = render_to_string(template)
    data['status'] = order.status
    data['pending'] = order.pending
    return JsonResponse(data)


def order_update_status(request):
    data = dict()
    pk = request.GET.get('pk', None)
    order = get_object_or_404(Order, pk=pk)
    status = request.GET.get('status')
    print('status is:', status)
    order.status = status
    order.save()
    template = 'includes/order_status.html'
    data['html_status'] = render_to_string(template)
    data['status'] = order.status
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


# Comment related views
def comment_add(request):
    data = dict()

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.creation = timezone.now()
            comment.user = request.user
            comment.save()
            data['form_is_valid'] = True
            comments = Comment.objects.all().order_by('-creation')
            template = 'includes/comment_list.html'
            data['html_comment_list'] = render_to_string(template,
                                                         {'comments': comments}
                                                         )
        else:
            data['form_is_valid'] = False
    else:
        form = CommentForm()

    context = {'form': form}
    data['html_form'] = render_to_string('includes/comment_add.html',
                                         context,
                                         request=request,
                                         )
    return JsonResponse(data)


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
