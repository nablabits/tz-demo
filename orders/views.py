from django.shortcuts import render, redirect, get_object_or_404
from .models import Comment, Customer, Order, CommentCheck
from django.utils import timezone
from .forms import CustomerForm, OrderForm
from django.contrib.auth.decorators import login_required
from datetime import datetime


# First check is a valid User
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


@login_required
def orderlist(request):
    """Display active orders or search'em."""
    orders = Order.objects.all().order_by('delivery')

    cur_user = request.user
    now = datetime.now()

    settings = {'orders': orders,
                'user': cur_user,
                'now': now,
                'title': 'TrapuZarrak · Pedidos',
                'footer': True,
                }

    return render(request, 'tz/orders.html', settings)


@login_required()
def new_customer(request):
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
        return render(request, 'tz/new_customer.html',
                      {'form': form,
                       'now': now,
                       'title': 'TrapuZarrak · Nuevo Cliente',
                       'footer': False,
                       })


@login_required
def customer_edit(request, pk):
    """Edit an already created customer."""
    order = get_object_or_404(Order, pk=pk)
    customer = get_object_or_404(Customer, name=order.customer)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'tz/new_customer.html',
                  {'form': form,
                   'edit': True,
                   })


@login_required
def customerlist(request):
    """A view to display customers or search'em."""
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


@login_required()
def new_order(request):
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
        return render(request, 'tz/new_order.html',
                      {'form': form,
                       'now': now,
                       'title': 'TrapuZarrak · Nuevo Pedido',
                       'footer': False,
                       })


@login_required
def order_view(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'tz/order_view.html', {'order': order})


@login_required
def order_edit(request, pk):
    """Edit an already created order."""
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
    else:
        form = OrderForm(instance=order)
    return render(request, 'tz/new_order.html',
                  {'form': form,
                   'edit': True,
                   })
