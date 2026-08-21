"""Unit tests for ``rrlog.auth.auth_required``.

Covers the 5-row truth table from AGENTS.md "Phase 2.5 — auth-required
bridge":

| Authorization header | OIDC session | OIDC_ENABLED | Result                          |
| -------------------- | ------------ | ------------ | ------------------------------- |
| Valid Basic          | (any)        | (any)        | page served (Basic)             |
| Invalid Basic        | (any)        | (any)        | 401 + WWW-Authenticate: Basic   |
| Absent               | Present      | True         | page served (session)           |
| Absent               | Absent       | True         | 302 → /oidc/authenticate/       |
| Absent               | (any)        | False        | 401 + WWW-Authenticate: Basic   |

``basic_auth`` is mocked — its DB query never runs. ``redirect_to_login``
is mocked so we can assert the OIDC login URL without standing up a
full URL conf.
"""
from unittest.mock import MagicMock

import pytest
from django.test import override_settings

from rrlog import auth as rrlog_auth


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(*, auth_header=None, user_authenticated=False, username=""):
    """Build a stand-in HttpRequest for ``auth_required``.

    MagicMock lets us set arbitrary attributes (``request.username``)
    and inspect what the wrapper wrote to them. We only need enough of
    the real HttpRequest interface for the wrapper's code paths.
    """
    request = MagicMock()
    request.META = {}
    if auth_header is not None:
        request.META["HTTP_AUTHORIZATION"] = auth_header
    user = MagicMock()
    user.is_authenticated = user_authenticated
    user.username = username
    request.user = user
    request.get_full_path.return_value = "/log/whoami/"
    return request


def _wrap(sentinel="page-rendered"):
    """Return a view stub wrapped by ``auth_required``."""
    view = MagicMock(return_value=sentinel)
    return rrlog_auth.auth_required(view), view


# ---------------------------------------------------------------------------
# 1. Valid Basic header
# ---------------------------------------------------------------------------


def test_valid_basic_header_serves_page(monkeypatch):
    monkeypatch.setattr(rrlog_auth, "basic_auth", lambda req: (True, "DL1ABC"))
    request = _make_request(auth_header="Basic ZGw6c2VjcmV0")
    wrapped, view = _wrap()

    result = wrapped(request)

    view.assert_called_once_with(request)
    assert request.username == "DL1ABC"
    assert result == "page-rendered"


# ---------------------------------------------------------------------------
# 2. Invalid Basic header
# ---------------------------------------------------------------------------


def test_invalid_basic_header_returns_401_basic(monkeypatch):
    """A curl client with bad creds must get 401 Basic, NOT an OIDC redirect."""
    monkeypatch.setattr(
        rrlog_auth, "basic_auth", lambda req: (False, "Login failed"),
    )
    # Stub render() so we don't depend on rrlog/generic.html being on disk.
    fake_response = MagicMock(status_code=401)
    monkeypatch.setattr(rrlog_auth, "render", lambda *a, **kw: fake_response)

    request = _make_request(auth_header="Basic ZGw6d3Jvbmc=")
    wrapped, view = _wrap()

    response = wrapped(request)

    view.assert_not_called()
    assert response is fake_response
    # The wrapper sets the WWW-Authenticate header AFTER calling render(),
    # so we have to look at the patched response (which is what render()
    # returned) for the header it would have set in production.
    fake_response.__setitem__.assert_any_call(
        "WWW-Authenticate", 'Basic realm="RRDXA Log Upload"',
    )


# ---------------------------------------------------------------------------
# 3. No Authorization header, OIDC session present
# ---------------------------------------------------------------------------


@override_settings(OIDC_ENABLED=True)
def test_oidc_session_serves_page(monkeypatch):
    monkeypatch.setattr(rrlog_auth, "basic_auth", lambda req: pytest.fail("not called"))
    request = _make_request(user_authenticated=True, username="dl1abc")
    wrapped, view = _wrap()

    result = wrapped(request)

    view.assert_called_once_with(request)
    # request.user.username is passed through; views upper-case at use time
    # via Member.objects.get(call=request.username). The OIDC backend creates
    # users with username already upper-cased, but the wrapper itself does
    # not re-upper-case — that's the backend's job.
    assert request.username == "dl1abc"
    assert result == "page-rendered"


# ---------------------------------------------------------------------------
# 4. No Authorization header, no OIDC session, OIDC_ENABLED → redirect
# ---------------------------------------------------------------------------


@override_settings(OIDC_ENABLED=True)
def test_browser_without_session_redirects_to_oidc(monkeypatch):
    monkeypatch.setattr(rrlog_auth, "basic_auth", lambda req: pytest.fail("not called"))
    sentinel_redirect = MagicMock(status_code=302)
    # Use a MagicMock so we can assert_called_once. The lambda trick from
    # earlier doesn't expose the assert_* helpers.
    redirect_mock = MagicMock(return_value=sentinel_redirect)
    monkeypatch.setattr(rrlog_auth, "redirect_to_login", redirect_mock)
    request = _make_request(user_authenticated=False)
    wrapped, view = _wrap()

    result = wrapped(request)

    view.assert_not_called()
    assert result is sentinel_redirect
    redirect_mock.assert_called_once()
    args, kwargs = redirect_mock.call_args
    # The OIDC login URL — resolved from the URL name — must be passed
    # through. The stub test_urls.py mounts /oidc/authenticate/ under that
    # name; the wrapper resolves it via reverse().
    assert kwargs["login_url"] == "/oidc/authenticate/"
    # And the original path must be preserved as `next` (positional arg).
    assert args[0] == "/log/whoami/"


# ---------------------------------------------------------------------------
# 5. No Authorization header, OIDC disabled → 401 Basic (legacy)
# ---------------------------------------------------------------------------


@override_settings(OIDC_ENABLED=False)
def test_legacy_no_header_returns_401_basic(monkeypatch):
    monkeypatch.setattr(rrlog_auth, "basic_auth", lambda req: pytest.fail("not called"))
    fake_response = MagicMock(status_code=401)
    monkeypatch.setattr(rrlog_auth, "render", lambda *a, **kw: fake_response)
    request = _make_request(user_authenticated=False)
    wrapped, view = _wrap()

    response = wrapped(request)

    view.assert_not_called()
    assert response is fake_response
    fake_response.__setitem__.assert_any_call(
        "WWW-Authenticate", 'Basic realm="RRDXA Log Upload"',
    )


# ---------------------------------------------------------------------------
# Bonus: Basic header present BUT OIDC session also present
# ---------------------------------------------------------------------------


@override_settings(OIDC_ENABLED=True)
def test_basic_header_takes_precedence_over_session(monkeypatch):
    """When both Basic and a session exist, Basic wins.

    Rationale: a programmatic client sending -u explicitly opts in to
    credential-based auth; honouring that header keeps the response
    consistent with what the client asked for (and avoids subtle
    impersonation if the session belongs to a different user).
    """
    monkeypatch.setattr(rrlog_auth, "basic_auth", lambda req: (True, "DL1ABC"))
    request = _make_request(
        auth_header="Basic ZGw6c2VjcmV0",
        user_authenticated=True,
        username="dl9dan",  # different user
    )
    wrapped, view = _wrap()

    wrapped(request)

    view.assert_called_once_with(request)
    assert request.username == "DL1ABC"


# ---------------------------------------------------------------------------
# Bonus: _has_basic_auth helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("header,expected", [
    ("Basic ZGw6c2VjcmV0", True),
    ("basic ZGw6c2VjcmV0", True),  # case-insensitive
    ("BASIC ZGw6c2VjcmV0", True),
    ("Bearer xyz", False),
    ("", False),
    (None, False),  # missing entirely
])
def test_has_basic_auth(header, expected):
    request = MagicMock()
    request.META = {} if header is None else {"HTTP_AUTHORIZATION": header}
    assert rrlog_auth._has_basic_auth(request) is expected
