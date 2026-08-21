"""OIDC Relying Party authentication backend for Django.

Lives in its own module (rather than ``rrmember.auth``) so that it can be
imported standalone for unit testing without dragging in the
``WordpressAuthBackend``'s dependencies on ``passlib`` and the
``Member`` materialized view model. ``AUTHENTICATION_BACKENDS`` references
this class directly when OIDC login is enabled.

The Automattic ``OpenID Connect Server`` plugin (v2.0.0) does NOT emit
an ``email`` claim — its ``UserClaimsStorage`` field map is
``{username, name, given_name, family_name, nickname}`` plus ``picture``,
and the plugin's discovery doc advertises ``scopes_supported`` as
``["openid", "profile"]`` with no ``email`` scope. We therefore do not
require ``email`` from the ID token and do not set ``User.email``.
Django users will have empty emails after OIDC login; this is accepted
because email is only used for password resets, which happen in WP.

Four methods are overridden; the defaults are wrong for our setup:

- ``filter_users_by_claims`` defaults to filtering by ``email``. We
  filter by ``username`` so returning users match on call sign.
- ``verify_claims`` defaults to asserting only ``email`` is present. We
  require only ``sub`` (the plugin's UserClaimsStorage sets ``sub`` to
  WP ``user_login``, which equals the user's callsign).
- ``create_user`` defaults to using ``SHA224(email)`` as the username,
  which is nonsense for us. We build the User from ``sub`` and the
  standard profile claims.
- ``update_user`` is a no-op by default. We refresh ``first_name`` and
  ``last_name`` on every login so BuddyPress profile changes propagate
  to Django.

``is_staff`` defaults to ``False``; admins are promoted manually in
``manage.py shell`` after their first OIDC login (see AGENTS.md
"Phase 3 — Hard cutover").
"""
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class OIDCRPAuthenticationBackend(OIDCAuthenticationBackend):

    def filter_users_by_claims(self, claims):
        sub = claims.get("sub")
        if not sub:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(username=sub.upper())

    def verify_claims(self, claims):
        # Only `sub` is required. The Automattic plugin emits `sub`
        # (= WP `user_login` = callsign) for every authenticated user,
        # but does NOT emit `email`. Requiring `email` would reject
        # every login. Standard OIDC says `sub` is always present.
        return bool(claims.get("sub"))

    def create_user(self, claims):
        # `email` is intentionally omitted: the plugin doesn't emit it,
        # and Django's default value for `User.email` is the empty
        # string, which is what we want.
        return self.UserModel.objects.create_user(
            username=claims["sub"].upper(),
            first_name=claims.get("given_name", ""),
            last_name=claims.get("family_name", ""),
        )

    def update_user(self, user, claims):
        # Only overwrite a name field when the IdP supplied one.
        # `claims.get(key, user.first_name or "")` ensures we never
        # blank out a name that was set in a previous login but happens
        # to be missing from the current claim set.
        user.first_name = claims.get("given_name", user.first_name or "")
        user.last_name = claims.get("family_name", user.last_name or "")
        user.save()
        return user
