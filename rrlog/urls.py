from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('call/<str:call>/', views.v_call, name='call'),
    path('contest/<str:contest>/', views.v_contest, name='contest'),
    path('cty/<str:cty>/', views.v_cty, name='cty'),
    path('grid/<str:grid>/', views.v_grid, name='grid'),
    path('month/<int:year>-<int:month>/', views.v_month, name='month'),
    path('year/<int:year>/', views.v_year, name='year'),
    path('upload/', views.v_upload, name='upload'),
    path('download/<int:id>/', views.v_download, name='download'),
]

