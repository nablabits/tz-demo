from django.shortcuts import render
from .models import Comment, Customer, Order, CommentCheck
from .forms import CustomerForm
from django.contrib.auth.decorators import login_required
from datetime import datetime


# First check is a valid User
@login_required()
def main(request):
    """Create the root view."""
    # Query all active orders
    orders = Order.objects.exclude(status=7).order_by('-inbox_date')

    # Query last commnents on active orders
    comments = Comment.objects.filter(reference__in=orders)
    comments = comments.order_by('-creation')

    cur_user = request.user
    now = datetime.now()

    dict4view = {'orders': orders,
                 'comments': comments,
                 'user': cur_user,
                 'now': now,
                 }

    return render(request, 'tz/main.html', dict4view)


@login_required()
def new_customer(request):
    """Create new customers with a form view."""
    form = CustomerForm()
    now = datetime.now()
    return render(request, 'tz/new_customer.html',
                  {'form': form, 'now': now})


@login_required()
def form_valid(request):
    """Display a congrat page if form is valid."""
    pass
    # if request.method == "POST":
    #     """ When coming from edit view, save the changes (if they are valid)
    #     and jump to weekly list"""
    #     form = PostForm(request.POST)
    #
    #     if form.is_valid():
    #         week = form.save(commit=False)
    #         week.published_date = timezone.now()
    #         week.save()
    #         return redirect('week_edit', pk=week.pk)
