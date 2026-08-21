<?php
/**
 * Plugin Name: RRDXA OIDC Clients
 * Description: Registers the RRDXA Logbook Django site as an OIDC client of
 *              this WordPress install. Pairs with the Automattic
 *              "OpenID Connect Server" plugin. Standard claims only — no
 *              custom claim filter, so no theme/PHP changes beyond this file.
 *
 * Client secret is stored as a constant in wp-config.php so it can be
 * rotated without touching this file:
 *
 *   define( 'OIDC_LOGBOOK_WEB_SECRET', '<random 64 hex chars>' );
 *
 * Only the browser client is registered. The curl upload endpoint keeps
 * using HTTP Basic against the FDW-backed materialized view; see AGENTS.md
 * "Decisions locked in" → `curl upload auth`.
 *
 * If curl auth is ever migrated to OAuth, add a second client entry here
 * with the appropriate `grant_types`. Note the Automattic plugin v2.0.0
 * does NOT support password grant (no UserCredentialsInterface storage),
 * so any non-auth-code client must use `authorization_code` + PKCE with a
 * local browser callback — see AGENTS.md "Future work" for the three
 * candidate paths.
 *
 * Capability gate: the plugin defaults to requiring `edit_posts`
 * (`OIDC_DEFAULT_MINIMAL_CAPABILITY` in
 * src/Http/Handlers/AuthorizeHandler.php) which excludes WP subscribers
 * — and our members are subscribers by default. We lower the bar to
 * `level_0`, which every WP logged-in user is guaranteed to have regardless
 * of role-cap customization. (`read` would have been the obvious choice,
 * but this site's Subscriber role has been customized via the Members
 * plugin to drop `read`. See AGENTS.md "Tier-5 quirks".)
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_filter( 'oidc_registered_clients', function () {
	return array(
		'logbook.rrdxa.org' => array(
			'name'         => 'RRDXA Logbook',
			'secret'       => defined( 'OIDC_LOGBOOK_WEB_SECRET' ) ? OIDC_LOGBOOK_WEB_SECRET : '',
			'redirect_uri' => 'https://logbook.rrdxa.org/oidc/callback/',
			'grant_types'  => array( 'authorization_code', 'refresh_token' ),
			'scope'        => 'openid profile email',
		),
	);
} );

// Lower the plugin's "must have at least this WP capability" gate from
// `edit_posts` to `level_0`. With WP's default role mapping, every logged-in
// user has `level_0`; only Editor / Author / Contributor / Administrator
// have `edit_posts`. Our members register as subscribers and never need
// write access to WP, so `edit_posts` would block every one of them.
//
// Why `level_0` and not `read`: this site's Subscriber role has been
// customized via the Members plugin (members_user_has_cap_filter at
// priority 10) to *remove* the `read` capability. `level_0` is the universal
// "this user has any WP role" capability that WP_User::init() guarantees
// for every logged-in user, and it survives role-cap customization.
// Discovered 2026-08-21 — see AGENTS.md "Tier-5 quirks".
add_filter( 'oidc_minimal_capability', function () {
	return 'level_0';
} );

