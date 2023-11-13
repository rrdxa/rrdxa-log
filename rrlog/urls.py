from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('logbook/', views.v_logbook),
    path('call/<str:call>/', views.v_call, name='call'),
    path('contest/<str:contest>/', views.v_contest, name='contest'),
    path('dxcc/<str:dxcc>/', views.v_dxcc, name='dxcc'),
    path('event/<str:event>/', views.v_event, name='event'),
    path('grid/<str:grid>/', views.v_grid, name='grid'),
    path('log/<int:log>/', views.v_log, name='log'),
    path('month/<int:year>-<int:month>/', views.v_month, name='month'),
    path('year/<int:year>/', views.v_year, name='year'),

    path('upload/', views.v_upload, name='upload'),
    path('download/<int:upload_id>/', views.v_download, name='download'),
    path('summary/<int:upload_id>/', views.v_summary, name='summary'),

    path('members/', views.v_members, name='members'),
]

