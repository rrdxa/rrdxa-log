from django.urls import path

from . import views

urlpatterns = [
    path('', views.v_index, name='index'),
    path('membership_certificate/', views.v_membership_certificate, name='membership_certificate'),
    path('list/', views.v_list, name='list'),
]
