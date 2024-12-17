"""rrdxa URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include, path
from django.views.generic.base import TemplateView
#from django.contrib import admin

urlpatterns = [
    path('', TemplateView.as_view(template_name="root.html")),
    #path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('cluster/', include('cluster.urls')),
    path('contestchallenge/', include('contestchallenge.urls')),
    path('dxchallenge/', include('dxchallenge.urls')),
    path('log/', include('rrlog.urls')),
    path('member/', include('rrmember.urls')),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]
