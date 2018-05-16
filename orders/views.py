from django.shortcuts import render, redirect
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
    orders = Order.objects.exclude(status=7).order_by('-inbox_date')
    orders_count = len(orders)

    # Query last commnents on active orders
    comments = Comment.objects.filter(reference__in=orders)
    comments = comments.order_by('-creation')

    cur_user = request.user
    now = datetime.now()

    dict4view = {'orders': orders,
                 'orders_count': orders_count,
                 'comments': comments,
                 'user': cur_user,
                 'now': now,
                 'title': 'TrapuZarrak · Inicio',
                 'footer': True,
                 }

    return render(request, 'tz/main.html', dict4view)


@login_required
def orderlist(request):
    """A view to display active orders."""
    pass

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
