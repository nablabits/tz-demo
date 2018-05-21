from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    # the root view
    path('', views.main, name='main'),
    path('orders', views.orderlist, name='orderlist'),
    path('customers', views.customerlist, name='customerlist'),
    path('new_customer/', views.new_customer, name='new_customer'),
    path('new_order/', views.new_order, name='new_order'),
    re_path(r'^(?P<pk>[0-9]+)/customer/$',
            views.customer_edit, name='customer_edit'),
    re_path(r'^(?P<pk>[0-9]+)/order/$',
            views.order_edit, name='order_edit'),
    re_path(r'^orderview/(?P<pk>[0-9]+)$',
            views.order_view, name='order_view'),
    re_path(r'^customerview/(?P<pk>[0-9]+)$',
            views.customer_view, name='customer_view'),
    path('accounts/login/', auth_views.login, name='login'),
    path('accounts/logout/', auth_views.logout, name='logout'),
]
