"""pytest configuration for the rrmember test suite.

Django settings must be configured *and* the app registry must be
populated before any module that imports ``django.contrib.auth`` (which
includes both ``rrmember.auth`` and ``mozilla_django_oidc.auth``) is
loaded. pytest loads this conftest before any test module in this
directory, so the configuration here runs first.

We use sqlite-in-memory for any test that actually touches the ORM
(none of the OIDC backend tests do, but if someone adds one later,
this keeps it self-contained). Tests that exercise the OIDC backend's
``__init__`` would also need the ``OIDC_*`` settings; the tests in
this directory bypass ``__init__`` via ``object.__new__`` and so do
not require them.
"""
import django
from django.conf import settings


settings.configure(
    DEBUG=False,
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.auth",
    ],
    DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    SECRET_KEY="test-only-not-secret",
)

django.setup()
