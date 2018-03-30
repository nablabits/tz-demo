from django.shortcuts import render
from .models import Comment, Customer, Order, CommentCheck

def main(request):
    """The root view."""

    # Query all active orders
    orders = Order.objects.exclude(status=7).order_by('-inbox_date')

    # Query last commnents on active orders
    comments = Comment.objects.filter(reference__in=orders)
    comments = comments.order_by('-creation')

    dict4view = {'orders': orders,
                 'comments': comments,
                 }

    return render(request, 'tz/main.html', dict4view)
