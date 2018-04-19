from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    # the root view
    path('', views.main, name='main'),
    path('new_customer/', views.new_customer, name='new_customer'),
    path('accounts/login/', auth_views.login, name='login'),
    path('accounts/logout/', auth_views.logout, name='logout'),
]
