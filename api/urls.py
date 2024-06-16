from django.urls import path

from . import views

urlpatterns = [
    path('lookup/<str:call>', views.lookup, name='lookup'),
    path('spots/<str:channel>', views.spots, name='spots'),
]

