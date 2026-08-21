from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.db import connection
from django.shortcuts import render
import base64
from passlib.hash import bcrypt, phpass
import functools


def _has_basic_auth(request):
    """True if the request carries an HTTP Basic Authorization header.

    Used by ``auth_required`` to distinguish a programmatic client
    (curl, scripting) from a browser. The presence of the header — not
    its validity — is the signal: a curl user opts in to Basic by
    sending ``-u user:pass`` (or equivalent); a browser user simply
    doesn't send the header. We never want to redirect a programmatic
    client to the OIDC login page.
    """
    return request.META.get("HTTP_AUTHORIZATION", "").lower().startswith("basic ")


def basic_auth(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return False, "Login required"

    token_type, _, credentials = auth_header.partition(' ')
    if token_type.lower() != "basic":
        return False, "Only Basic auth supported"

    username, _, password = base64.b64decode(credentials).decode("utf-8").partition(':')

    with connection.cursor() as cursor:
        cursor.execute("select call, user_pass from members where call = %s or user_email = %s", [username.upper(), username.lower()])
        userdata = cursor.fetchone()

    if not userdata:
        print(f"user {username} not found in database")
        return False, "Login failed"

    username, user_password = userdata

    # Wordpress 6.8 switched from phpass ($P$) to custom sha256+bcrypt ($wp$2y$).
    # Since that isn't supported by passlib yet, we deploy
    # https://wordpress.org/plugins/password-hash/ on the Wordpress side so
    # it's writing standard bcrypt ($2y$) now.
    if user_password[:2] == '$2':
        hash_method = bcrypt
    elif user_password[:3] == '$P$':
        hash_method = phpass
    else:
        print(f"unknown password hash scheme for user {username} {user_password}")
        return False, "Login failed, please reset your password at rrdxa.org"

    if not hash_method.verify(password, user_password):
        print(f"wrong password for user {username}")
        return False, "Login failed"

    return True, username


def auth_required(func):
    """Gate a member view on either HTTP Basic or an OIDC session.

    Order of preference on every request:

    1. ``Authorization: Basic …`` header present → treat as a
       programmatic client. Verify credentials; on success set
       ``request.username`` and serve the page; on failure return
       ``401 + WWW-Authenticate: Basic`` so the client knows its creds
       are wrong. Never redirect a programmatic client to OIDC.

    2. No Authorization header → treat as a browser. If OIDC is enabled
       and ``request.user`` is authenticated (the session cookie from a
       previous ``/oidc/callback/``), set ``request.username`` from
       ``request.user.username`` and serve the page.

    3. Otherwise (OIDC enabled, no session) → 302 to ``/oidc/authenticate/``
       with the original URL as ``?next=…``.

    4. OIDC disabled and no Authorization header → 401 Basic (legacy
       behaviour, unchanged from the pre-OIDC era).

    On success, ``request.username`` is always set to the user's callsign
    in upper case, matching what ``basic_auth`` and the OIDC backend both
    produce. Views can read it as today — no view-level changes needed.
    """

    @functools.wraps(func)
    def wrapper_auth_required(request, *args, **kwargs):
        # (1) Programmatic client: Basic header present.
        if _has_basic_auth(request):
            status, message = basic_auth(request)
            if status:
                request.username = message
                return func(request, *args, **kwargs)
            # Bad creds. 401 Basic — do NOT redirect; the client knows
            # it sent bad creds and should retry, not chase an OIDC flow.
            response = render(
                request, 'rrlog/generic.html', {'message': message}, status=401,
            )
            response['WWW-Authenticate'] = 'Basic realm="RRDXA Log Upload"'
            return response

        # (2/3) Browser path: no Authorization header.
        oidc_enabled = getattr(settings, 'OIDC_ENABLED', False)

        if oidc_enabled and request.user.is_authenticated:
            # Session from /oidc/callback/. AuthenticationMiddleware
            # already populated request.user from the session cookie.
            request.username = request.user.username
            return func(request, *args, **kwargs)

        if oidc_enabled:
            # No session → kick off the OIDC login dance. The redirect
            # target is /oidc/authenticate/ which is itself unauth'd
            # (mozilla_django_oidc.urls.mounts it as a public view), so
            # no infinite loop. After login the callback lands the
            # browser back on `next` and the user gets the page they
            # were trying to load.
            from django.urls import reverse
            return redirect_to_login(
                request.get_full_path(),
                login_url=reverse('oidc_authentication_init'),
            )

        # (4) Legacy mode (OIDC disabled). Browser with no Basic header.
        response = render(
            request, 'rrlog/generic.html', {'message': 'Login required'}, status=401,
        )
        response['WWW-Authenticate'] = 'Basic realm="RRDXA Log Upload"'
        return response

    return wrapper_auth_required
