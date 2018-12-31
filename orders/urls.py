"""Set the url for the views."""

from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views


urlpatterns = [
    # The root url
    path('', views.main, name='main'),
    path('search', views.search, name='search'),

    # List related urls
    re_path(r'^orders&orderby=(?P<orderby>\D+)/',
            views.orderlist, name='orderlist'),
    path('customers', views.customerlist, name='customerlist'),
    path('items', views.itemslist, name='itemslist'),
    path('pqueue/manager', views.pqueue_manager, name='pqueue_manager'),
    path('invoices', views.invoiceslist, name='invoiceslist'),

    # Object related urls
    re_path(r'^order/view/(?P<pk>[0-9]+)$',
            views.order_view, name='order_view'),
    re_path(r'^order/express/(?P<pk>[0-9]+)$',
            views.order_express_view, name='order_express'),
    re_path(r'^customer_view/(?P<pk>[0-9]+)$',
            views.customer_view, name='customer_view'),

    # AJAX related urls
    path('actions/', views.Actions.as_view(), name='actions'),
    path('changelog/', views.changelog, name='changelog'),
    path('filter-items/', views.filter_items, name='filter-items'),
    path('queue-actions/', views.pqueue_actions, name='queue-actions'),

    # Loging related urls
    path('accounts/login/', auth_views.login, name='login'),
    path('accounts/logout/', auth_views.logout, name='logout'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
