from django.urls import path

from . import views

urlpatterns = [
    path('', views.v_index, name='index'),
]
