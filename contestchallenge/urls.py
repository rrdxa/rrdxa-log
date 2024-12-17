from django.urls import path

from . import views

urlpatterns = [
    path('', views.v_contestchallenge, name='contestchallenge'),
    path('<int:year>/', views.v_contestchallenge, name='contestchallenge'),
]
