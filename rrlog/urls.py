from django.urls import path

from . import views

urlpatterns = [
    path('', views.v_index, name='index'),
    path('logbook/', views.v_logbook),
    path('call/<str:call>/', views.v_call, name='call'),
    path('challenge/', views.v_challenge, name='challenge'),
    path('challenge/<int:year>/', views.v_challenge, name='challenge'),
    path('contest/<str:contest>/', views.v_contest, name='contest'),
    path('dxcc/<str:dxcc>/', views.v_dxcc, name='dxcc'),
    path('event/', views.v_events, name='events'),
    path('event/<str:event>/', views.v_event, name='event'),
    path('grid/<str:grid>/', views.v_grid, name='grid'),
    path('log/<int:log>/', views.v_log, name='log'),
    path('mao/', views.v_mao, name='mao'),
    path('month/<int:year>-<int:month>/', views.v_month, name='month'),
    path('rrdxa60/', views.v_rrdxa60, name='challenge'),
    path('year/<int:year>/', views.v_year, name='year'),

    path('upload/', views.v_upload, name='upload'),
    path('adif-upload/', views.v_upload, name='upload'),
    path('cabrillo-upload/', views.v_upload, name='upload'),
    path('download/<int:upload_id>/', views.v_download, name='download'),
    path('summary/<int:upload_id>/', views.v_summary, name='summary'),
    path('edit/<int:upload_id>/', views.v_edit, name='edit'),

    path('members/', views.v_members, name='members'),
]

