"""Unit tests for rrmember.oidc_auth.OIDCRPAuthenticationBackend.

The four overridden methods (``filter_users_by_claims``,
``verify_claims``, ``create_user``, ``update_user``) are exercised with
mocked ``UserModel`` so we can run without a real database. The parent
class ``__init__`` reads ``OIDC_*`` settings from Django settings, which
we don't want to require for unit tests; we bypass it via
``object.__new__``.

The corresponding integration test (a real ``auth.authenticate()`` round
trip against the live WP IdP) is out of scope for this file — see
AGENTS.md "Tier 3" in the testing plan.
"""
from unittest.mock import MagicMock

import pytest

from rrmember.oidc_auth import OIDCRPAuthenticationBackend


def _backend():
    """Construct OIDCRPAuthenticationBackend without invoking __init__.

    The real ``__init__`` reads OIDC_RP_* settings, which are not
    configured under pytest. The unit tests only exercise our four
    overrides, none of which call into the parent ``__init__`` machinery.
    """
    backend = object.__new__(OIDCRPAuthenticationBackend)
    backend.UserModel = MagicMock()
    return backend


# ---------------------------------------------------------------------------
# filter_users_by_claims
# ---------------------------------------------------------------------------


def test_filter_users_by_claims_finds_existing_user():
    """A returning user with the right username is matched."""
    backend = _backend()
    backend.UserModel.objects.filter.return_value = ["matched-user"]
    result = backend.filter_users_by_claims({"sub": "df7cb"})
    backend.UserModel.objects.filter.assert_called_once_with(username="DF7CB")
    assert result == ["matched-user"]


def test_filter_users_by_claims_uppercases_callsign():
    """Callsigns are case-insensitive: 'df7cb' and 'DF7CB' must match."""
    backend = _backend()
    backend.UserModel.objects.filter.return_value = []
    backend.filter_users_by_claims({"sub": "df7cb"})
    backend.UserModel.objects.filter.assert_called_once_with(username="DF7CB")


def test_filter_users_by_claims_missing_sub_returns_empty():
    """Without sub we return an empty queryset without touching .filter()."""
    backend = _backend()
    backend.UserModel.objects.none.return_value = "<empty qs>"
    result = backend.filter_users_by_claims({"name": "Alice"})
    backend.UserModel.objects.none.assert_called_once_with()
    backend.UserModel.objects.filter.assert_not_called()
    assert result == "<empty qs>"


# ---------------------------------------------------------------------------
# verify_claims
# ---------------------------------------------------------------------------


def test_verify_claims_accepts_sub_only():
    """The Automattic plugin doesn't emit email; sub alone is enough."""
    backend = _backend()
    assert backend.verify_claims({"sub": "df7cb"}) is True


def test_verify_claims_accepts_full_claim_set():
    """Extra claims (email, name, picture, etc.) don't change the verdict."""
    backend = _backend()
    assert (
        backend.verify_claims(
            {
                "sub": "df7cb",
                "email": "df7cb@example.org",  # plugin doesn't actually emit this
                "name": "Alice Smith",
                "given_name": "Alice",
                "family_name": "Smith",
                "nickname": "Alice",
                "picture": "https://example.org/avatar.png",
            }
        )
        is True
    )


def test_verify_claims_rejects_missing_sub():
    """Defensive: sub is always present in a valid OIDC token, but if it's
    missing we should refuse to authenticate rather than crash or accept."""
    backend = _backend()
    assert backend.verify_claims({"email": "x@example.org"}) is False


def test_verify_claims_rejects_empty_sub():
    """An empty-string sub is treated as absent."""
    backend = _backend()
    assert backend.verify_claims({"sub": ""}) is False


def test_verify_claims_rejects_empty_claims():
    backend = _backend()
    assert backend.verify_claims({}) is False


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


def test_create_user_basic_claims():
    backend = _backend()
    claims = {
        "sub": "df7cb",
        "name": "Alice Smith",
        "given_name": "Alice",
        "family_name": "Smith",
    }
    backend.create_user(claims)
    backend.UserModel.objects.create_user.assert_called_once_with(
        username="DF7CB",
        first_name="Alice",
        last_name="Smith",
    )


def test_create_user_does_not_pass_email():
    """The plugin doesn't emit email. We must not pass an email kwarg to
    create_user() — Django's User.email defaults to "" which is correct."""
    backend = _backend()
    backend.create_user(
        {
            "sub": "df7cb",
            "given_name": "Alice",
            "family_name": "Smith",
        }
    )
    kwargs = backend.UserModel.objects.create_user.call_args.kwargs
    assert "email" not in kwargs


def test_create_user_uppercases_callsign():
    backend = _backend()
    backend.create_user({"sub": "df7cb"})
    kwargs = backend.UserModel.objects.create_user.call_args.kwargs
    assert kwargs["username"] == "DF7CB"


def test_create_user_handles_missing_optional_profile_claims():
    """given_name/family_name absent → empty strings, not None, no crash."""
    backend = _backend()
    backend.create_user({"sub": "df7cb"})
    kwargs = backend.UserModel.objects.create_user.call_args.kwargs
    assert kwargs["first_name"] == ""
    assert kwargs["last_name"] == ""


def test_create_user_returns_created_user():
    """Whatever UserModel.objects.create_user returns is what we return."""
    backend = _backend()
    sentinel = object()
    backend.UserModel.objects.create_user.return_value = sentinel
    result = backend.create_user({"sub": "df7cb"})
    assert result is sentinel


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------


def test_update_user_refreshes_profile_fields():
    backend = _backend()
    user = MagicMock()
    user.first_name = "OldFirst"
    user.last_name = "OldLast"
    claims = {
        "sub": "df7cb",
        "given_name": "NewFirst",
        "family_name": "NewLast",
    }
    result = backend.update_user(user, claims)
    assert user.first_name == "NewFirst"
    assert user.last_name == "NewLast"
    user.save.assert_called_once()
    assert result is user


def test_update_user_does_not_touch_email():
    """Email is no longer managed by the OIDC backend. We must not write
    to user.email, even if some future claim set accidentally includes it."""
    backend = _backend()
    user = MagicMock()
    user.first_name = "OldFirst"
    user.last_name = "OldLast"
    user.email = "keep@example.org"
    claims = {
        "sub": "df7cb",
        "email": "should-be-ignored@example.org",
        "given_name": "NewFirst",
        "family_name": "NewLast",
    }
    backend.update_user(user, claims)
    assert user.email == "keep@example.org"


def test_update_user_preserves_existing_when_claim_missing():
    """If claims omit given_name/family_name, don't blank out the stored value.

    BuddyPress xprofile fields can be temporarily empty. Refreshing the
    session shouldn't lose the previously-stored name. The
    ``user.first_name or ""`` default only kicks in when the stored
    value is also falsy.
    """
    backend = _backend()
    user = MagicMock()
    user.first_name = "Existing"
    user.last_name = "ExistingLast"
    backend.update_user(user, {"sub": "df7cb"})
    assert user.first_name == "Existing"
    assert user.last_name == "ExistingLast"


def test_update_user_saves_even_when_no_fields_changed():
    """save() is called unconditionally — the auth flow depends on a fresh
    last_login; even no-op profile updates should persist it."""
    backend = _backend()
    user = MagicMock()
    user.first_name = "Same"
    user.last_name = "Same"
    backend.update_user(user, {"sub": "df7cb"})
    user.save.assert_called_once()
