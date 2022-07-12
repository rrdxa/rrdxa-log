from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('call/<str:call>/', views.v_call, name='call'),
]

