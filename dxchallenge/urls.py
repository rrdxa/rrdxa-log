from django.urls import path

from . import views

urlpatterns = [
    path('', views.v_dxchallenge, name='dxchallenge'),
    path('<int:year>/', views.v_dxchallenge, name='dxchallenge'),
]
