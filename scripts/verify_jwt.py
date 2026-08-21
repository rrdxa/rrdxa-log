#!/usr/bin/env python3
"""Smoke-test the WordPress OIDC IdP at rrdxa.org and verify a JWT against it.

Three checks, each callable standalone:

  * D — Fetch and parse ``/.well-known/openid-configuration`` against the
    settings ``mozilla-django-oidc`` actually reads.
  * E — Fetch and parse ``/.well-known/jwks.json``, verify the signing key
    matches the advertised algorithm.
  * C — Decode and verify a JWT against the JWKS. The token must come from
    a real authorization-code exchange against the live IdP — see
    AGENTS.md "Tier 2 → F1" for how to obtain one. This function is the
    canary for "did the plugin emit what we expect".

Exit status: 0 on success, 1 on any check failure.

Usage:
    scripts/verify_jwt.py              # D + E (live IdP smoke)
    scripts/verify_jwt.py <token>      # D + E + C (full JWT verification)

Designed to be readable, not performant. Not for production use.
"""
import json
import sys
import textwrap
import time
from urllib.parse import urlparse

import requests
from jwt import PyJWK, decode
from jwt.exceptions import InvalidTokenError


# Settings the OIDC RP (mozilla-django-oidc) needs from the discovery doc.
# Verified against mozilla_django_oidc/auth.py + views.py v5.0.2.
REQUIRED_DISCOVERY_KEYS = [
    "issuer",
    "authorization_endpoint",
    "token_endpoint",
    "jwks_uri",
    "id_token_signing_alg_values_supported",
    "response_types_supported",
]


def fetch_discovery(issuer):
    """D: Fetch and validate the OIDC discovery document.

    Returns the parsed document as a dict. Raises AssertionError if any
    required key is missing, or if any URL in the doc points to a
    different host than the issuer (defensive against the plugin
    returning relative paths).
    """
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    print(f"  GET {url}")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    doc = r.json()

    for key in REQUIRED_DISCOVERY_KEYS:
        assert key in doc, f"discovery doc missing required key: {key!r}"

    issuer_host = urlparse(issuer).netloc
    for endpoint in ("authorization_endpoint", "token_endpoint",
                     "userinfo_endpoint", "jwks_uri"):
        if endpoint not in doc:
            continue
        endpoint_host = urlparse(doc[endpoint]).netloc
        assert endpoint_host == issuer_host, (
            f"{endpoint} host {endpoint_host!r} != issuer host {issuer_host!r}"
        )

    # Note the quirk: this IdP's discovery doc advertises
    # authorization_endpoint = /wp-json/openid-connect/authorize, but the
    # actual browser flow uses wp-login.php?action=openid-authenticate.
    # We report it but don't fail — the RP's settings.py uses the
    # wp-login URL explicitly (see AGENTS.md "Phase 2").
    print(f"  issuer:                {doc['issuer']}")
    print(f"  authorization_endpoint:{doc['authorization_endpoint']}")
    print(f"  token_endpoint:        {doc['token_endpoint']}")
    print(f"  userinfo_endpoint:     {doc.get('userinfo_endpoint', '<absent>')}")
    print(f"  jwks_uri:              {doc['jwks_uri']}")
    print(f"  scopes_supported:      {doc.get('scopes_supported')}")
    print(f"  response_types:        {doc['response_types_supported']}")
    print(f"  id_token_signing_algs: {doc['id_token_signing_alg_values_supported']}")

    if "email" not in (doc.get("scopes_supported") or []):
        print("  ⚠ scopes_supported does NOT include 'email' — the RP must")
        print("    not rely on the email scope to receive the email claim.")
        print("    See AGENTS.md Phase 2 for the workaround.")

    return doc


def fetch_jwks(discovery):
    """E: Fetch and validate the JWKS.

    Returns (jwks_dict, signing_jwk) where signing_jwk is the first key
    suitable for token verification (kty=RSA, use=sig, alg in the
    advertised list).
    """
    url = discovery["jwks_uri"]
    print(f"  GET {url}")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    jwks = r.json()

    assert "keys" in jwks and len(jwks["keys"]) >= 1, "JWKS has no keys"

    signing_jwk = None
    for jwk in jwks["keys"]:
        if jwk.get("kty") != "RSA":
            continue
        if jwk.get("use") and jwk["use"] != "sig":
            continue
        if "alg" in jwk and jwk["alg"] not in discovery["id_token_signing_alg_values_supported"]:
            continue
        signing_jwk = jwk
        break

    assert signing_jwk is not None, (
        "no RSA signing key found that matches id_token_signing_alg_values_supported"
    )

    print(f"  keys:                  {len(jwks['keys'])} (using first RSA/sig key)")
    print(f"  kid:                   {signing_jwk.get('kid', '<none>')}")
    print(f"  alg:                   {signing_jwk.get('alg', '<none>')}")
    print(f"  kty:                   {signing_jwk.get('kty')}")

    return jwks, signing_jwk


def verify_jwt(token, issuer, audience, jwk):
    """C: Decode and verify a JWT against the JWKS.

    Returns the decoded claims dict. Raises on any failure (invalid
    signature, wrong issuer/audience, expired).

    Note: ``mozilla-django-oidc`` accepts tokens whose ``aud`` matches
    ``OIDC_RP_CLIENT_ID`` but does not require ``aud`` validation by
    default (``options={"verify_aud": False}`` in auth.py). We DO verify
    aud here because we know what we expect.
    """
    key = PyJWK(jwk).key
    alg = jwk.get("alg", "RS256")

    claims = decode(
        token,
        key=key,
        algorithms=[alg],
        audience=audience,
        issuer=issuer,
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )
    return claims


def main():
    issuer = "https://rrdxa.org"
    # The client_id we registered for the Django web client.
    audience = "logbook.rrdxa.org"

    print("D: Fetch + parse discovery doc")
    print("-" * 60)
    discovery = fetch_discovery(issuer)

    print()
    print("E: Fetch + parse JWKS")
    print("-" * 60)
    jwks, jwk = fetch_jwks(discovery)

    if len(sys.argv) < 2:
        print()
        print("=" * 60)
        print("D and E passed. No JWT supplied — skipping C.")
        print("Pass an id_token as argv[1] to verify it against this IdP.")
        print("See AGENTS.md 'Tier 2 → F1' for how to obtain one.")
        return 0

    token = sys.argv[1]
    print()
    print("C: Verify JWT")
    print("-" * 60)
    print(f"  token (first 40 chars): {token[:40]}...")

    try:
        claims = verify_jwt(token, issuer, audience, jwk)
    except InvalidTokenError as e:
        print(f"  ✗ JWT verification failed: {e}")
        return 1

    # Note the claim shape we expect from the plugin's UserClaimsStorage.php:
    #   sub, username (== sub), email, email_verified, name, given_name,
    #   family_name, nickname, picture, scope, iss, aud, iat, exp, nonce?
    print(f"  ✓ JWT signature + iss + aud + exp validated")
    print(f"  iss:                   {claims.get('iss')}")
    print(f"  aud:                   {claims.get('aud')}")
    print(f"  sub:                   {claims.get('sub')}")
    print(f"  username:              {claims.get('username', '<absent>')}")
    print(f"  email:                 {claims.get('email', '<absent>')}")
    print(f"  email_verified:        {claims.get('email_verified', '<absent>')}")
    print(f"  name:                  {claims.get('name', '<absent>')}")
    print(f"  given_name:            {claims.get('given_name', '<absent>')}")
    print(f"  family_name:           {claims.get('family_name', '<absent>')}")
    print(f"  nickname:              {claims.get('nickname', '<absent>')}")
    print(f"  picture:               {claims.get('picture', '<absent>')}")
    print(f"  iat / exp:             {claims.get('iat')} / {claims.get('exp')}")
    print(f"  lifetime:              {claims.get('exp', 0) - claims.get('iat', 0)}s")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, requests.RequestException) as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(1)
