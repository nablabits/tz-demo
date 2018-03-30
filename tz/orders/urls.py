from django.urls import path
from . import views


urlpatterns = [
    # the root view
    path('', views.main, name='main'),
]
