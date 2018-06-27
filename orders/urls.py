from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views


urlpatterns = [
    # The root url
    path('', views.main, name='main'),
    path('search', views.search, name='search'),

    # Order related urls
    path('orders', views.orderlist, name='orderlist'),
    re_path(r'^order/view/(?P<pk>[0-9]+)$',
            views.order_view, name='order_view'),

    # Order related urls (AJAX implementation)
    path('actions/', views.Actions.as_view(), name='actions'),

    # Customer related urls
    path('customers', views.customerlist, name='customerlist'),
    re_path(r'^customer_view/(?P<pk>[0-9]+)$',
            views.customer_view, name='customer_view'),

    # Loging related urls
    path('accounts/login/', auth_views.login, name='login'),
    path('accounts/logout/', auth_views.logout, name='logout'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
