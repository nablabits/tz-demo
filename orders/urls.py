"""Set the url for the views."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from . import views

# API urls generator
router = DefaultRouter()
router.register(r'customer', views.CustomerAPIList)
router.register(r'order', views.OrderAPIList)
router.register(r'item', views.ItemAPIList)
router.register(r'order_item', views.OrderItemAPIList)
router.register(r'invoice', views.InvoiceAPIList)
router.register(r'expense', views.ExpenseAPIList)
router.register(r'bank_movement', views.BankMovementAPIList)

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
    path('pqueue/tablet',
         views.pqueue_tablet, name='pqueue_tablet'),
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
    path('item-selector/', views.item_selector, name='item-selector'),
    path('queue-actions/', views.pqueue_actions, name='queue-actions'),

    # Loging related urls
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    # The API url
    path('API/', include(router.urls)),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
