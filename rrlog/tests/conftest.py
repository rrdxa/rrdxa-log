"""pytest configuration for the rrlog test suite.

Mirrors ``rrmember/tests/conftest.py``. rrlog's ``auth.py`` imports
``django.contrib.auth.views.redirect_to_login`` at module level, so
``django.contrib.auth`` must be in INSTALLED_APPS before that module
loads. The ``auth_required`` decorator also reads
``settings.OIDC_ENABLED`` at request time, so individual tests set that
via ``override_settings`` (or the test fixtures below) when needed.

No tests in this suite touch the database — ``basic_auth`` is mocked,
and the OIDC backend is never imported. The sqlite-in-memory database
is configured for the sake of any future view-level test that needs
the ORM.

``ROOT_URLCONF`` points at a tiny stub urlconf so ``reverse(...)``
works for the URL name the wrapper resolves at request time.

Settings idempotency: pytest may load this conftest after a sibling
package's conftest (e.g. ``rrmember/tests/conftest.py``) has already
called ``settings.configure(...)``. We only configure if no settings
are loaded yet, and we only set the keys this suite needs on top of
whatever's already there.
"""
import django
from django.conf import settings


if not settings.configured:
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
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            },
        ],
        ROOT_URLCONF="rrlog.tests.test_urls",
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        SECRET_KEY="test-only-not-secret",
    )
    django.setup()
else:
    # A previous conftest (e.g. rrmember/tests/conftest.py) already set
    # up Django. Make sure the keys rrlog's tests need are present,
    # otherwise ``reverse('oidc_authentication_init')`` and the
    # template loader will fail.
    settings.ROOT_URLCONF = getattr(
        settings, "ROOT_URLCONF", "rrlog.tests.test_urls",
    )
    if not getattr(settings, "TEMPLATES", None):
        settings.TEMPLATES = [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            },
        ]
    if "django.contrib.auth" not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + [
            "django.contrib.auth",
        ]
