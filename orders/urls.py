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
router.register(r'expense_category', views.ExpenseCategoryAPIList)
router.register(r'cashflowio', views.CashFlowIOAPIList)
router.register(r'bank_movement', views.BankMovementAPIList)
router.register(r'status_shift', views.StatusShiftAPIList)
router.register(r'timetable', views.TimetableAPIList)

urlpatterns = [
    # The root url
    path('', views.main, name='main'),
    path('search', views.search, name='search'),

    # Populate database
    path('populate', views.populate_trigger, name='populate'),

    # List related urls
    path('kanban', views.kanban, name='kanban'),
    path('customers', views.customerlist, name='customerlist'),
    path('items', views.itemslist, name='itemslist'),
    path('pqueue/manager', views.pqueue_manager, name='pqueue_manager'),
    path('pqueue/tablet',
         views.pqueue_tablet, name='pqueue_tablet'),
    path('invoices', views.invoiceslist, name='invoiceslist'),
    path('stock_manager', views.stock_manager, name='stock_manager'),

    # Object related urls
    re_path(r'^order/view/(?P<pk>[0-9]+)$',
            views.order_view, name='order_view'),
    re_path(r'^order/express/(?P<pk>[0-9]+)$',
            views.order_express_view, name='order_express'),
    re_path(r'^customer_view/(?P<pk>[0-9]+)$',
            views.customer_view, name='customer_view'),

    # Printer view
    re_path(r'^ticket_print&invoice_no=(?P<invoice_no>[0-9]+)$',
            views.printable_ticket, name='ticket_print'),

    # Generic views
    path('timetables/', views.TimetableList.as_view(), name='timetables'),

    # AJAX related urls
    path('actions/', views.Actions.as_view(), name='actions'),
    path('orders-CRUD/', views.OrdersCRUD.as_view(), name='orders-CRUD'),
    path('items-CRUD/', views.ItemsCRUD.as_view(), name='items-CRUD'),
    path('orderitems-CRUD/',
         views.OrderItemsCRUD.as_view(), name='orderitems-CRUD'),
    path('comments-CRUD/', views.CommentsCRUD.as_view(), name='comments-CRUD'),
    path('cashflowio-CRUD/', views.CashFlowIOCRUD.as_view(),
         name='cashflowio-CRUD', ),
    path('changelog/', views.changelog, name='changelog'),
    path('item-selector/', views.item_selector, name='item-selector'),
    path('queue-actions/', views.pqueue_actions, name='queue-actions'),

    # AJAX Hints
    path('customer-hints/', views.customer_hints, name='customer-hints'),
    path('group-hints/', views.group_hints, name='group-hints'),

    # Loging related urls
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('add-hours', views.add_hours, name='add_hours'),

    # The API url
    path('API/', include(router.urls)),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
