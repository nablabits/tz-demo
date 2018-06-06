from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views


urlpatterns = [
    # The root url
    path('', views.main, name='main'),

    # Order related urls
    path('orders', views.orderlist, name='orderlist'),
    re_path(r'^order_view/(?P<pk>[0-9]+)$',
            views.order_view, name='order_view'),
    path('order_new/', views.order_new, name='order_new'),
    re_path(r'^order_edit/(?P<pk>[0-9]+)$',
            views.order_edit, name='order_edit'),

    # Order related urls (AJAX implementation)
    path('order/get_status/', views.order_get_status, name='order_get_status'),
    path('order/update_status/', views.order_update_status,
         name='order_update_status'),
    path('comment/add/', views.comment_add, name='comment_add'),
    path('upload/file/', views.order_upload_file, name='order_upload'),
    path('delete/file/', views.order_delete_file, name='order_file_delete'),
    path('order/close/', views.order_close, name='order_close'),
    # Great unification
    path('order/action/', views.OrderActions.as_view(), name='order_actions'),

    # Customer related urls
    path('customers', views.customerlist, name='customerlist'),
    re_path(r'^customer_view/(?P<pk>[0-9]+)$',
            views.customer_view, name='customer_view'),
    path('customer_new/', views.customer_new, name='customer_new'),
    re_path(r'^customer/(?P<pk>[0-9]+)$',
            views.customer_edit, name='customer_edit'),

    # Loging related urls
    path('accounts/login/', auth_views.login, name='login'),
    path('accounts/logout/', auth_views.logout, name='logout'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
