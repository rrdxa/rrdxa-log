"""Minimal urlconf used only by the rrlog test suite.

The wrapper under test calls ``reverse('oidc_authentication_init')``
when it needs to redirect a browser to OIDC login. We don't want to
mount the real ``mozilla_django_oidc.urls`` (it requires the full
OIDC_* settings), so we provide a stub URL with the same name and the
same fixed path ``/oidc/authenticate/`` that production uses.
"""
from django.urls import path
from django.http import HttpResponse


def _stub_oidc_view(request):
    return HttpResponse(b"stub")


urlpatterns = [
    path("oidc/authenticate/", _stub_oidc_view, name="oidc_authentication_init"),
    path("oidc/callback/", _stub_oidc_view, name="oidc_authentication_callback"),
    path("oidc/logout/", _stub_oidc_view, name="oidc_logout"),
]
