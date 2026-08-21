# RRDXA Logbook — Agent Notes

Notes for AI assistants and human contributors working on this repo.

## Project context

- Django site: **logbook.rrdxa.org** (ham-radio QSO logbook for RRDXA, a German DX
  association).
- Companion site: **rrdxa.org** (WordPress + BuddyPress — canonical user store
  with `L7l2a_users`, `L7l2a_usermeta`, `L7l2a_bp_xprofile_data`).
- Django lives in this repo; WP plugins/themes are managed elsewhere.
- See `README.md` for install + runtime dependencies.

## Architecture: current auth path (as of this writing)

```
WordPress MySQL                          PostgreSQL
┌────────────────┐   mysql_fdw    ┌──────────────────────────┐
│ L7l2a_users    │ ─────────────► │ rrdxa.members (matview)   │
│ L7l2a_usermeta │                │ rrdxa.rrcalls  (matview)  │
│ L7l2a_xprofile │                │ wordpress.*       (FDW)   │
└────────────────┘                └──────────────────────────┘
                                              │
                          ┌───────────────────┴──────────────┐
                          ▼                                  ▼
              rrmember/auth.py                     rrlog/auth.py
              WordpressAuthBackend                 basic_auth()
              (Django session login)               (HTTP Basic on /log/upload/)
```

Key files today:

- `rrmember/auth.py` — `WordpressAuthBackend` verifies password against WP
  `user_pass` via passlib (bcrypt `$2y$` after the `password-hash` WP plugin
  normalised the WP 6.8 `$wp$2y$` hashes, or phpass `$P$` otherwise).
- `rrmember/management/commands/sync_users.py` — refreshes the materialized
  views and mirrors WP users into Django `auth_user` + `Vereinsmitglied`.
- `rrlog/auth.py` — same verification, inline SQL, for the `curl` upload API.
- `sql/wp_fdw.sql` — defines the FDW server, user mapping, imported foreign
  schemas, and the materialized views.

## Architecture: target (OAuth/OIDC migration)

```
WordPress rrdxa.org                        Django logbook.rrdxa.org
┌────────────────────────┐                 ┌────────────────────────┐
│ WordPress + BuddyPress │                 │ mozilla-django-oidc    │
│ + OpenID Connect       │  OIDC discovery │ + OIDCAuthentication   │
│   Server plugin        │ ──────────────► │   Backend (RP)         │
│   (Automattic,         │  Auth Code+PKCE │                        │
│    wordpress.org/      │  /oauth/token   │ Browser sessions only. │
│    plugins/openid-     │  /jwks          │ Curl uploads keep      │
│    connect-server/)    │  /userinfo      │ HTTP Basic + FDW as    │
│                        │                 │ before.                │
│ 1 MU-plugin: register  │                 │                        │
│ the Django web client.│                 │ FDW + sync_users stay  │
│ Zero theme edits.      │                 │ for Vereinsverwaltung  │
│ Zero custom claims.    │                 │ and full call list     │
│                        │                 │ (also powers basic_auth)│
└────────────────────────┘                 └────────────────────────┘
                                                       ▲
                                                       │ standard OIDC client
                                                       │ (any language)
                                              ┌────────┴────────┐
                                              │ Future 3rd party│
                                              │ sites / apps    │
                                              └─────────────────┘
```

## Decisions locked in

| Topic              | Decision                                                                 |
| ------------------ | ------------------------------------------------------------------------ |
| Canonical users    | WP stays the source of truth (BuddyPress + xprofile stay).               |
| IdP                | WordPress via `Automattic/wp-openid-connect-server` (v2.0.0).            |
| RP on Django       | `mozilla-django-oidc`.                                                   |
| Browser login UX   | Redirect to WP login (Auth Code + PKCE).                                 |
| curl upload auth   | **Out of scope for this migration.** HTTP Basic + `rrlog/basic_auth` +    |
|                    | FDW + bcrypt/phpass verification stays indefinitely. The OIDC migration  |
|                    | touches the browser path only.                                          |
| Cutover            | Hard cutover on a chosen date, browser path only. `WordpressAuthBackend`  |
|                    | is removed; `rrlog/basic_auth` and the FDW stay.                         |
| OIDC claims used   | **Standard only**, but with caveats (see Tier-2 quirks, 2026-08-21):  |
|                    | `sub`, `name`, `given_name`, `family_name`, `nickname`, `picture`.     |
|                    | **No `email`** — the Automattic plugin's `UserClaimsStorage` doesn't  |
|                    | emit it, and its discovery doc's `scopes_supported` is                 |
|                    | `["openid", "profile"]` (no `email` scope). We chose to drop the      |
|                    | email requirement in Django rather than add a WP-side filter.         |
| `sub` semantics    | WP `user_login` (callsign) — per `UserClaimsStorage.php` in the plugin.  |
| `is_staff` mapping | **Manual** — promote the 4 admins (`DF7CB`, `DF7EE`, `DK2DQ`, `DL9DAN`)   |
|                    | once in Django shell after their first OIDC login. WP roles are ignored. |
| FDW future         | **Kept**. Powers Vereinsverwaltung + full call-sign highlighting **and**  |
|                    | `rrlog/basic_auth` for curl uploads. Token only carries the *logged-in   |
|                    | user's* profile; system-wide data and upload-time password verify still   |
|                    | come from the materialized view.                                        |
| `sync_users`       | **Kept** — still creates `Vereinsmitglied` rows for new WP users.         |

## Phases

### Phase 1 — WordPress side (no Django changes yet)

Files touched on the WP host (not in this repo):

1. Install `OpenID Connect Server` via WP admin (Plugins → Add New → search
   "OpenID Connect Server", install, activate).
2. Generate RSA keypair. **Where it lives depends on host access:**

   - **Shell access** (`/etc/rrdxa/` reachable):
     ```
     sudo install -d -m 0750 -o www-data /etc/rrdxa
     sudo -u www-data openssl genrsa -out /etc/rrdxa/oidc.key 4096
     sudo -u www-data openssl rsa  -in /etc/rrdxa/oidc.key -pubout -out /etc/rrdxa/oidc.pub
     sudo chmod 0640 /etc/rrdxa/oidc.{key,pub}
     ```
   - **FTP-only shared host** (no shell, no `/etc/rrdxa/`): generate keys
     **on your laptop**, then upload them above webroot via FTP. The
     "above webroot" location is what your chrooted FTP client shows when you
     click "up one level" out of `wp-content/`. Reference the keys in
     `wp-config.php` via `dirname( ABSPATH ) . '/oidc/oidc.<ext>'` so PHP
     resolves the absolute path without you needing to know it.

   Keep an offline copy of the private key on your laptop — the on-host copy
   is the only one that exists if you lose local access, and you can't
   re-issue tokens without rotating keys.

3. Add to `wp-config.php`:

   - **Shell-access path** (`/etc/rrdxa/`):
     ```php
     define( 'OIDC_PUBLIC_KEY',  file_get_contents( '/etc/rrdxa/oidc.pub' ) );
     define( 'OIDC_PRIVATE_KEY', file_get_contents( '/etc/rrdxa/oidc.key' ) );
     ```
   - **FTP-only path** (keys above webroot):
     ```php
     define( 'OIDC_PUBLIC_KEY',  file_get_contents( dirname( ABSPATH ) . '/oidc/oidc.pub' ) );
     define( 'OIDC_PRIVATE_KEY', file_get_contents( dirname( ABSPATH ) . '/oidc/oidc.key' ) );
     ```

   Plus in both cases:
   ```php
   define( 'OIDC_LOGBOOK_WEB_SECRET', '<random 64 hex chars>' );
   ```

   **Placement gotcha:** the `OIDC_*` `define()` calls must appear *after*
   the `define( 'ABSPATH', ... )` line at the bottom of `wp-config.php`,
   not before the `/* That's all, stop editing! */` comment. PHP resolves
   `define()`s in source order; if ABSPATH isn't defined yet, the
   `file_get_contents()` calls fire with an undefined constant and return
   `false`, leaving the key constants empty (the plugin then silently bails
   out and registers no REST routes — manifests as 404 on `/wp-json/...`,
   no helpful error). `ABSPATH` must be the last `define()` block, and the
   OIDC defines must come after it (but not inside the conditional
   `if ( ! defined( 'ABSPATH' ) ) { ... }` block — set them unconditionally).

4. Create `wp-content/mu-plugins/rrdxa-oidc-clients.php` — the full file is the
   ~20-line snippet in this repo at `docs/snippets/rrdxa-oidc-clients.php`
   (mirror, do not symlink, the MU-plugins dir is on the WP host).
5. Smoke test: `curl -fsS https://rrdxa.org/.well-known/openid-configuration |
   jq .` should return JSON with all the OIDC endpoints. `curl` the `/jwks`
   endpoint to confirm the public key is served. Browser-test the
   authorization-code flow with `httpbin.org/get` as a placeholder redirect.

Acceptance: discovery doc is reachable, JWKS endpoint returns a valid key set,
`/oauth/token` rejects a bad client_secret, authorization-code flow against a
browser returns a usable id_token with standard claims.

#### Phase 1 — quirks discovered during smoke testing (2026-08-21)

The Automattic `OpenID Connect Server` plugin (v2.0.0) has two quirks that
the README does not document. Worth recording so we don't relearn them
when the plugin is upgraded.

1. **Token endpoint requires `code` + `redirect_uri` for all grants.**
   `src/OpenIDConnectServer.php::expected_arguments_specification('token')`
   declares `code` and `redirect_uri` as `required: true`. These args are
   passed straight to WP's `register_rest_route()`, which enforces them
   *before* the OAuth2 server sees the request. Result: every grant type
   except `authorization_code` gets a `400 rest_missing_callback_param`
   from WP REST. If ROPG / client_credentials / etc. are ever added, the
   curl command must include `--data-urlencode "code=dummy"
   --data-urlencode "redirect_uri=https://localhost/callback"`. The
   underlying `league/oauth2-server` library ignores those params for
   non-auth-code grants, so they're harmless once past pre-validation.
   Tracked upstream in PR #117 (the change that introduced this).
   Re-test on plugin upgrade; remove the dummy params if/when fixed.

2. **Password grant is not supported.** The plugin only registers
   `AuthorizationCodeStorage` on the OAuth2 server
   (`src/OpenIDConnectServer.php` constructor). The `UserCredentialsInterface`
   storage needed for `grant_type=password` is missing, so the server
   legitimately responds with `{"error":"unsupported_grant_type"}`. The
   plugin's docs and example client config only mention
   `authorization_code`. Implication for *this* migration: moot — we
   decided to keep HTTP Basic for the curl upload endpoint indefinitely
   (see "Decisions locked in" → `curl upload auth`). Recording the
   limitation here in case anyone later wants to revisit curl auth.

#### Tier-2 quirks discovered during live IdP smoke testing (2026-08-21)

After the plugin was activated on `rrdxa.org`, we fetched the discovery
doc and JWKS directly and inspected the plugin source. Two more quirks
worth recording before phase 2 lands.

1. **`email` claim is not emitted by the plugin.** Reading
   `Storage/UserClaimsStorage.php::getUserClaims()`: the field map is
   ```php
   array(
       'username'    => 'user_login',
       'name'        => 'display_name',
       'given_name'  => 'first_name',
       'family_name' => 'last_name',
       'nickname'    => 'user_nicename',
   );
   ```
   plus a `picture` claim from `get_avatar_url()`. `email` is never
   set. The underlying `bshaffer/oauth2-server-php` library delegates
   to this storage and adds nothing else. The discovery doc
   (`/.well-known/openid-configuration`) confirms: `"scopes_supported"`
   is `["openid", "profile"]` — `email` is not even advertised as a
   scope. **Decision (locked in 2026-08-21):** drop the `email`
   requirement in the Django backend rather than add a WP-side
   `oidc_user_claims` filter. `OIDC_RP_SCOPES = "openid profile"` (no
   `email`), `verify_claims()` requires only `sub`, `create_user()` does
   not pass `email`, `update_user()` does not touch `User.email`.
   Django users end up with empty `email` fields; this is accepted
   because email is only used for password resets, which happen in WP.
   If we ever need email, options are: (a) add an `oidc_user_claims`
   filter in the MU-plugin to inject `email` from `$user->user_email`,
   or (b) fetch `/wp-json/wp/v2/users?search=<sub>` after login (no
   auth needed; WP REST allows public reads of usernames).

2. **JWKS omits `kid`.** The plugin's JWKS returns a single key with
   `kty`, `use`, `alg`, `n`, `e` — no `kid`. `mozilla-django-oidc`
   v5.0.2 `auth.py::retrieve_matching_jwk()` does
   `if jwk["kid"] != smart_str(jws["kid"]): continue` (with
   `OIDC_VERIFY_KID=True` as the default). This `KeyError`s on every
   JWKS entry. Fix: set `OIDC_VERIFY_KID = False` in `settings.py`.
   Verification falls back to the alg check (the next line in the loop),
   which matches `RS256` correctly. If/when the plugin adds a `kid` to
   its JWKS, we can drop the override.

#### Tier-3 quirks discovered during end-to-end browser test (2026-08-21)

With OIDC_ENABLED=True on production and `WSGIApplicationGroup %{GLOBAL}`
in Apache, the Django side now redirects browsers through the OIDC flow.
But the first browser test with user DA0RR ended not at the Django
callback but on a WP-styled "no permission" page. Diagnosed via curl:

```
$ curl -i -X POST https://rrdxa.org/wp-login.php \
    -d "log=DA0RR&pwd=...&redirect_to=...&wp-submit=Anmelden&testcookie=1"
HTTP/2 302
location: https://rrdxa.org/wp-login.php?action=openid-authenticate&client_id=...
$ curl -i "https://rrdxa.org/wp-login.php?action=openid-authenticate&..." \
    -b cookies-from-previous
HTTP/2 200
<title>OIDC Connect ‹ Rhein Ruhr DX Association – RRDXA – WordPress</title>
<p>Du hast nicht die erforderlichen Rechte, um OpenID Connect zu verwenden.</p>
```

That body is `src/Http/Handlers/AuthenticateHandler.php`'s
`render_no_permission_screen()`. Looking at `handle()`:

```php
$has_permission = current_user_can( apply_filters(
    'oidc_minimal_capability', OIDC_DEFAULT_MINIMAL_CAPABILITY
) );
```

`OIDC_DEFAULT_MINIMAL_capability` is `'edit_posts'`. WP's default role
mapping gives `edit_posts` to Editor / Author / Contributor /
Administrator only — *not* Subscriber. RRDXA members register as
subscribers (we don't need WP write access for anyone) so every one
of them would hit this gate.

**Decision (locked in 2026-08-21):** lower the bar to `read` via the
`oidc_minimal_capability` filter in our MU-plugin
(`docs/snippets/rrdxa-oidc-clients.php`). `'read'` is held by every
logged-in user; since WP auth *is* our membership check, this is the
correct gate. No theme/source edits; no DB changes. The Cancel button
on the no-permission screen redirects back to Django's
`/oidc/callback/?error=access_denied&...`, which is why the browser
appeared to "end on WP admin" (the styling matches wp-admin) rather
than completing the round-trip.

#### Tier-4 quirks discovered during live flow test (2026-08-21)

After the Tier-3 fix was applied (capability filter lowered to `read`),
end-to-end browser login *still* failed — the user got logged in to WP
but never reached Django. Diagnosed by tracing the full chain with
curl + cookies. The smoking gun was in `Location:` header from
`/oidc/authenticate/`:

```
Location: https://rrdxa.org/wp-login.php?action=openid-authenticate?response_type=code&scope=openid+profile&client_id=logbook.rrdxa.org&redirect_uri=…&state=…&nonce=…&code_challenge=…&code_challenge_method=S256
```

**Two `?`s.** The previous setting was
`OIDC_OP_AUTHORIZATION_ENDPOINT = "https://rrdxa.org/wp-login.php?action=openid-authenticate"`.
`mozilla_django_oidc.views.OIDCAuthenticationRequestView.get()` builds
the redirect URL as:

```python
redirect_url = "{url}?{query}".format(url=self.OIDC_OP_AUTH_ENDPOINT, query=query)
```

Appending `?` to a URL that already ends in `?` produces `??`. WP's
`wp-login.php` then sees `$_REQUEST['action'] = 'openid-authenticate?response_type=code'`
(not matching any registered action), falls through to the default
`login` action, shows the standard login form with
`redirect_to` *unset*, and after successful login redirects to the
default — `https://rrdxa.org/wp-admin/`. Hence "logged in to WP".

**Fix (locked in 2026-08-21):** point
`OIDC_OP_AUTHORIZATION_ENDPOINT` at the REST endpoint the discovery doc
already advertises:
`https://rrdxa.org/wp-json/openid-connect/authorize`. That URL has no
`?` in its path, so the concatenation is clean. The plugin's
`AuthorizeHandler::handle()` already handles the "not logged in"
branch by `wp_safe_redirect()`-ing to
`wp-login.php?action=openid-authenticate&…` with all OIDC params
preserved — i.e. exactly the flow we wanted, just reached via the REST
endpoint instead of starting there directly. This matches the OIDC
spec's discovery doc and removes the need to special-case wp-login.php.

The capability filter from Tier-3 is still required: when the
AuthorizeHandler redirects to `wp-login.php?action=openid-authenticate&…`
the `AuthenticateHandler::handle()` permission gate still runs, and
without the filter `current_user_can('edit_posts')` still fails for
subscribers.

### Phase 2 — Django, OIDC RP alongside existing backend

In this repo:

1. `pip install --user mozilla-django-oidc` (apt doesn't package it; matches
   the existing `opuslib`/`pymumble` user-site pattern).
2. `rrdxa/settings.py`:
   - Add `"mozilla_django_oidc"` to `INSTALLED_APPS`.
   - Add the OIDC config block. **`mozilla-django-oidc` does not auto-discover
      endpoints** from the IdP's `.well-known/openid-configuration` doc — every
      `OIDC_OP_*` endpoint must be set explicitly. We use the REST endpoint
      that the discovery doc itself advertises (`/wp-json/openid-connect/authorize`).
      That endpoint handles both branches: logged-in users go straight through,
      not-logged-in users get redirected by `AuthorizeHandler` to
      `wp-login.php?action=openid-authenticate&…` so WP can authenticate them
      first. (Earlier we configured the `wp-login.php` URL directly, which
      mozilla-django-oidc would concatenate with `?response_type=…&state=…` —
      producing a malformed URL with two `?` and breaking the round-trip; see
      "Tier-4 quirks" for the full story.) Required settings:
     ```python
     OIDC_RP_CLIENT_ID = "logbook.rrdxa.org"
     OIDC_RP_CLIENT_SECRET = ...   # from OIDC_LOGBOOK_WEB_SECRET
     OIDC_RP_SIGN_ALGO = "RS256"
      OIDC_OP_AUTHORIZATION_ENDPOINT = "https://rrdxa.org/wp-json/openid-connect/authorize"
      OIDC_OP_TOKEN_ENDPOINT         = "https://rrdxa.org/wp-json/openid-connect/token"
      OIDC_OP_USER_ENDPOINT          = "https://rrdxa.org/wp-json/openid-connect/userinfo"
      OIDC_OP_JWKS_ENDPOINT          = "https://rrdxa.org/.well-known/jwks.json"
      OIDC_RP_SCOPES                 = "openid profile"  # not "openid email" — plugin doesn't support email scope; see Tier-2 quirks
      OIDC_VERIFY_KID               = False             # JWKS omits kid field; mozilla-django-oidc's kid-check would KeyError; see Tier-2 quirks
      OIDC_USE_NONCE = True
      OIDC_USE_PKCE   = True   # recommended for security; plugin supports it
      OIDC_CREATE_USER = True  # default; explicit for clarity
      LOGIN_REDIRECT_URL         = "/"
      LOGIN_REDIRECT_URL_FAILURE = "/login-failed/"
      ```
   - Add `OIDC_ENABLED = False` flag.
   - Switch `AUTHENTICATION_BACKENDS` based on the flag:
     ```python
     AUTHENTICATION_BACKENDS = (
         ["mozilla_django_oidc.auth.OIDCAuthenticationBackend"]
         if OIDC_ENABLED
         else ["rrmember.auth.WordpressAuthBackend"]
     )
     ```
3. `rrdxa/urls.py`: add
   `path("oidc/", include("mozilla_django_oidc.urls"))`. This mounts three
   routes — `oidc/authenticate/`, `oidc/callback/`, `oidc/logout/` — that
   match the `redirect_uri` registered with the WP IdP.
4. `rrmember/oidc_auth.py` (new file — keep separate from `rrmember/auth.py`
   so the class can be imported for unit testing without dragging in
   `passlib` or the `Member` materialized view model): add the
   `OIDCRPAuthenticationBackend` subclass. Must override **four** methods
   (not just `create_user`/`update_user` as a casual reading of the docs
   would suggest — verified by reading `mozilla_django_oidc/auth.py` v5.0.2):
    - `filter_users_by_claims(claims)` — default filters by `email`; we filter
      by `username=claims["sub"].upper()` so returning users are matched on
      call sign, not email.
    - `verify_claims(claims)` — default only asserts `email` is present; we
      require only `sub` (the Automattic plugin does NOT emit `email`; see
      Tier-2 quirks).
    - `create_user(claims)` — default uses `SHA224(email)` as username, which
      is nonsense for us; we build the `User` directly from `sub` and the
      standard profile claims. `email` is intentionally not set — the plugin
      doesn't emit it and Django's default `User.email=""` is correct.
    - `update_user(user, claims)` — refresh `first_name` and `last_name` on
      each login so BuddyPress profile changes propagate. `email` is left
      alone (we don't manage it).

   Reference implementation: see "Custom backend" code block in the report
   from step A (kept here for posterity):
   ```python
   from mozilla_django_oidc.auth import OIDCAuthenticationBackend


   class OIDCRPAuthenticationBackend(OIDCAuthenticationBackend):
       def filter_users_by_claims(self, claims):
           sub = claims.get("sub")
           if not sub:
               return self.UserModel.objects.none()
           return self.UserModel.objects.filter(username=sub.upper())

       def verify_claims(self, claims):
           return bool(claims.get("sub"))

       def create_user(self, claims):
           return self.UserModel.objects.create_user(
               username=claims["sub"].upper(),
               first_name=claims.get("given_name", ""),
               last_name=claims.get("family_name", ""),
           )

       def update_user(self, user, claims):
           user.first_name = claims.get("given_name", user.first_name or "")
           user.last_name = claims.get("family_name", user.last_name or "")
           user.save()
           return user
   ```

   `is_staff` defaults to `False`; admins are promoted manually in phase 3.
   `AUTHENTICATION_BACKENDS` references `rrmember.oidc_auth.OIDCRPAuthenticationBackend`
   when OIDC is enabled.
5. **Template change: none required for the current site.** Searched all
   `*.html` templates — there is no Django-session Login link anywhere.
   The site uses `@rrlog.auth.auth_required` (a Basic-auth decorator from
   `rrlog/auth.py`) on every member-facing view, not Django's
   `@login_required`. So there is no place to redirect to
   `{% url 'oidc_authentication_init' %}` today. If a future template
   ever needs a Login link, the URL name to use is
   `oidc_authentication_init` (resolved by `mozilla_django_oidc.urls`).
   When that happens, also consider whether the existing `auth_required`
   decorator should be replaced with `@login_required` (which honours
   `LOGIN_URL`); that's a bigger refactor, separate from this migration.
6. `AUTHENTICATION_BACKENDS` stays at `WordpressAuthBackend` while
   `OIDC_ENABLED=False`. The `OIDCRPAuthenticationBackend` is wired but only
   active when the flag flips.
7. `mozilla_django_oidc.middleware.SessionRefresh` is added to
   `MIDDLEWARE`. Re-auths users silently via `prompt=none` once the
   id_token expires (default `OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS=900`,
   i.e. 15 min after expiry). id_tokens are 1 h, and without this users
   would get bumped every hour. Trade-off: the middleware requires
   `SessionMiddleware` (already present) and stores the id_token in the
   user's session — a tiny memory cost.

Acceptance: with `OIDC_ENABLED=False`, the site behaves identically to today
(verified `manage.py check` against both branches). A dev branch can flip
the flag and exercise the OIDC flow end-to-end without disturbing
production.

### Phase 2.5 — Auth-required bridge (2026-08-21)

When `OIDC_ENABLED=True` was first enabled in production, the OIDC
backend was active but **every member view still used the homebrew
`@auth_required` decorator** (`rrlog/auth.py`), which only consulted
HTTP Basic headers. Net effect: OIDC login worked in the background
but no member view actually checked the resulting session. The user
got the HTTP Basic prompt anyway.

This phase makes `@auth_required` consult OIDC sessions first. The
key insight: **the presence of an `Authorization` header is the
signal for "programmatic client"**. A curl user opts in to Basic by
sending `-u user:pass` (or equivalent); a browser user doesn't send
the header at all. No `User-Agent` sniffing needed.

#### Behaviour (`rrlog/auth.py::auth_required`)

| `Authorization` header | OIDC session | `OIDC_ENABLED` | Result                          |
| ---------------------- | ------------ | -------------- | ------------------------------- |
| Valid Basic            | (any)        | (any)          | page served, `request.username` from Basic |
| Invalid Basic          | (any)        | (any)          | `401 + WWW-Authenticate: Basic` — curl knows creds are wrong |
| Absent                 | Present      | True           | page served, `request.username = request.user.username` |
| Absent                 | Absent       | True           | `302 → /oidc/authenticate/?next=<orig>` |
| Absent                 | (any)        | False          | `401 + WWW-Authenticate: Basic` (legacy mode, unchanged) |

When **both** a Basic header and a session are present, Basic wins.
A programmatic client explicitly opts in to credential-based auth by
sending the header; honouring that header keeps the response
consistent with what the client asked for (and avoids subtle
impersonation if the session belongs to a different user).

`basic_auth()` itself is unchanged — still the source of truth for
Basic verification.

#### `/log/whoami/` diagnostic endpoint

`rrlog/views.py::v_whoami` (urlpattern `path('whoami/', ...)`) is a
JSON probe gated by the same `@auth_required`. Returns:

```json
{"username": "<callsign>", "auth_method": "basic|session"}
```

curl smokes (post-cutover, OIDC on):

```
$ curl -i https://logbook.rrdxa.org/log/whoami/        # no auth
HTTP/1.1 302 Found
Location: /oidc/authenticate/?next=/log/whoami/

$ curl -u DL1ABC:secret https://logbook.rrdxa.org/log/whoami/
{"username": "DL1ABC", "auth_method": "basic"}

$ curl -i -u DL1ABC:wrong https://logbook.rrdxa.org/log/whoami/
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Basic realm="RRDXA Log Upload"

$ curl --cookie sessionid=…  https://logbook.rrdxa.org/log/whoami/
{"username": "DL1ABC", "auth_method": "session"}
```

This is the only honest way to verify both auth paths without
rendering a full member page, and it survives future refactors of
the views.

#### `v_events` simplification

`rrlog/views.py::v_events` previously called `basic_auth` a second
time inside its POST branch, which was dead code (the `@auth_required`
decorator already verified the Basic header) **and** would have 401'd
any browser POST without a Basic header — defeating the OIDC flow.
Removed the redundant call; the POST handler now reads
`request.username` set by the decorator.

#### Trade-off: browser POST with expired session

If a browser user's OIDC session expires between GETting the events
form and POSTing it, the `@auth_required` redirect kicks the browser
to OIDC login, lands them back on `/log/event/` as a GET, and the
POST data is lost. The user refills the form. SessionRefresh
middleware normally keeps the session alive across GETs, so this only
happens in the rare "form sits open across an id_token expiry"
scenario. Acceptable for now; would need a "save POST to session and
restore on callback" mechanism (mozilla-django-oidc does not provide
one) to fix properly. Out of scope for this migration.

#### Tests

12 cases in `rrlog/tests/test_auth_required.py`:

- 5 cases for the truth table above
- 1 case for "Basic takes precedence over session" (priority)
- 6 parametrised cases for `_has_basic_auth` (case-insensitivity,
  Bearer ignored, empty/missing header)

Plus a `rrlog/tests/test_urls.py` stub urlconf that mounts
`/oidc/authenticate/`, `/oidc/callback/`, `/oidc/logout/` under the
names `mozilla_django_oidc.urls` would use — needed so the wrapper's
`reverse('oidc_authentication_init')` resolves in tests without
loading the real OIDC settings.

### Phase 3 — Hard cutover (the chosen date)

Browser login only. `rrlog/basic_auth` and the FDW stay.

1. `OIDC_ENABLED = True`.
2. Remove `"rrmember.auth.WordpressAuthBackend"` from
   `AUTHENTICATION_BACKENDS`. Delete `rrmember/auth.py`'s
   `WordpressAuthBackend` class. Drop the `passlib` import there too.
3. `rrlog/auth.py` is **untouched** — `basic_auth` keeps working as today.
4. One-off `manage.py shell` snippet to promote the 4 admins after their
   first OIDC login. Suggested (run interactively per admin):
   ```python
   from django.contrib.auth import get_user_model
   U = get_user_model()
   for call in ("DF7CB", "DF7EE", "DK2DQ", "DL9DAN"):
       u = U.objects.get(username=call)
       u.is_staff = True
       u.is_superuser = (call == "DL9DAN")  # pick the actual superuser; adjust
       u.save()
   ```
   Run after each admin has logged in once via OIDC so the `User` row exists.
5. Bump version, write member-facing announcement with the cutover date and
   the new login URL.

Acceptance: browser login uses OIDC end-to-end; HTTP Basic on `/log/upload/`
still works (unchanged); the 4 admins retain `/admin/` access.

### Phase 4 — 3rd-party readiness

Not implementation, just docs:

- Page on `rrdxa.org` describing:
  - How to register a client (`client_id`, redirect URI, allowed grant types,
    scopes) — initially manual via the `oidc_registered_clients` filter.
  - Discovery URL: `https://rrdxa.org/.well-known/openid-configuration`.
  - JWKS URL: `https://rrdxa.org/.well-known/jwks.json`.
  - Available claims and what each means.
  - Worked examples: `authlib` in Python, `oidc-client-ts` in JS,
    `league/oauth2-client` in PHP.

### Future work (no phase number) — optional curl auth migration

If the user community ever wants OAuth on the curl upload path too, the
options at that point would be:

- Patch the plugin to add a `UserCredentialsInterface` storage so ROPG
  works (~30 lines via FTP edit, re-apply on plugin upgrades).
- Switch to auth-code + PKCE with a local browser callback (zero WP
  edits, requires a browser on the upload machine at first-login).
- Add a Django-side `/api/token` endpoint that does username/password
  verification via the existing FDW and returns a short-lived JWT signed
  by Django. Bypasses OAuth entirely on the curl side, but couples curl
  auth to Django's signing key rather than the IdP's.

This is explicitly **not** part of the current migration.

## Open questions for the human

- [ ] **Cutover date** (≥2 weeks out, ideally when most uploaders are around).
- [ ] **Python install path** — apt `python3-django` system Python or a venv I
      haven't seen? Determines `mozilla-django-oidc` install method.

## Inventory of WP-side changes (for reference)

Total WP host footprint:

- 1 plugin (Automattic OIDC Server) installed via WP admin.
- 1 RSA keypair. Location depends on host:
  - Shell access: `/etc/rrdxa/oidc.{key,pub}`, mode 0640, owned by `www-data`.
  - FTP-only: `dirname( ABSPATH ) . '/oidc/oidc.{key,pub}'`, mode 0600/0644.
- ~3 lines added to `wp-config.php` (after the `ABSPATH` define — see
  placement gotcha in Phase 1).
- 1 must-use plugin file (~30 lines, see `docs/snippets/rrdxa-oidc-clients.php`).

Nothing else. BuddyPress, themes, custom PHP, the existing
`daggerhart-openid-connect-generic` client (deactivated), the `password-hash`
plugin — all untouched.

## Conventions for code added in this migration

- User said comments are welcome. Use them to explain *why* something non-obvious
  is being done, especially:
  - The OIDC claim → Django field mapping rationale.
  - The JWKS caching policy.
  - Why we keep the FDW even after auth moves to OAuth.
- Keep code style consistent with the existing repo (PEP 8, no unnecessary
  comments elsewhere).
- Do not introduce new dependencies beyond `mozilla-django-oidc` and
  `requests` (already a system dep per README) without asking.
- Do not change `rrmember/management/commands/sync_users.py` or `sql/wp_fdw.sql`
  in this migration — both stay.
