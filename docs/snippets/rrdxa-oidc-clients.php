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
 * `read` so any logged-in WP user (= any RRDXA member) can complete the
 * flow. Discovered 2026-08-21 when DA0RR (subscriber) was bounced by
 * AuthenticateHandler::handle()'s `current_user_can()` check; see
 * AGENTS.md "Tier-3 quirks" for the full story.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_filter( 'oidc_registered_clients', function () {
	return array(
		'logbook.rrdxa.org' => array(
			'name'         => 'RRDXA Logbook (web)',
			'secret'       => defined( 'OIDC_LOGBOOK_WEB_SECRET' ) ? OIDC_LOGBOOK_WEB_SECRET : '',
			'redirect_uri' => 'https://logbook.rrdxa.org/oidc/callback/',
			'grant_types'  => array( 'authorization_code', 'refresh_token' ),
			'scope'        => 'openid profile email',
		),
	);
} );

// Lower the plugin's "must have at least this WP capability" gate from
// `edit_posts` to `read`. With WP's default role mapping, every logged-in
// user has `read`; only Editor / Author / Contributor / Administrator
// have `edit_posts`. Our members register as subscribers and never need
// write access to WP, so `edit_posts` would block every one of them.
add_filter( 'oidc_minimal_capability', function () {
	return 'read';
} );

