<?php
/**
 * Self-hosted update checker via GitHub releases.
 *
 * Uses YahnisElsts' Plugin Update Checker (PUC) — the de-facto standard for
 * non-WP.org plugins.
 *
 * Two modes are supported:
 *
 *  PUBLIC repo (recommended):
 *    No setup needed. PUC polls the GitHub releases API anonymously every 12h.
 *
 *  PRIVATE repo:
 *    Define a fine-grained Personal Access Token in wp-config.php:
 *      define('KIB_UPDATE_CHECKER_TOKEN', 'github_pat_...');
 *    Token must have read-only access to "Contents" on the plugin repo.
 *    NOTE: the token is stored on the shop's WordPress server and is
 *    fetched on every update check — treat it as a credential.
 *
 * Override the repo URL per-site via:
 *    define('KIB_UPDATE_CHECKER_REPO', 'https://github.com/your-fork/repo/');
 *
 * Distribution workflow:
 *  1. bump KIB_VERSION + plugin-header `Version:` + readme.txt `Stable tag:`
 *  2. git tag plugin-v0.2.0 && git push --tags
 *  3. GitHub Action builds the release zip (with vendor/) and attaches it
 *  4. PUC polls the releases API and surfaces the update in WP-Admin
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

namespace KI_Berater;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class Update_Checker {
	/**
	 * Default GitHub repo URL where releases are published. Override per-site
	 * via `define('KIB_UPDATE_CHECKER_REPO', '...')` in wp-config.php.
	 */
	private const DEFAULT_REPO = 'https://github.com/silasgehring-cloud/ki-berater/';

	/**
	 * Plugin slug — must match the directory name (`ki-berater`).
	 */
	private const PLUGIN_SLUG = 'ki-berater';

	public function register(): void {
		$puc_loader = KIB_PLUGIN_DIR . 'vendor/yahnis-elsts/plugin-update-checker/plugin-update-checker.php';
		if ( ! file_exists( $puc_loader ) ) {
			// Dev environment — composer install hasn't run. Auto-update is off.
			return;
		}

		require_once $puc_loader;

		$factory = '\\YahnisElsts\\PluginUpdateChecker\\v5\\PucFactory';
		if ( ! class_exists( $factory ) ) {
			return;
		}

		$repo = defined( 'KIB_UPDATE_CHECKER_REPO' )
			? (string) constant( 'KIB_UPDATE_CHECKER_REPO' )
			: self::DEFAULT_REPO;

		$checker = $factory::buildUpdateChecker(
			$repo,
			KIB_PLUGIN_FILE,
			self::PLUGIN_SLUG
		);

		// Private-repo support: only set if KIB_UPDATE_CHECKER_TOKEN is defined.
		if ( defined( 'KIB_UPDATE_CHECKER_TOKEN' ) ) {
			$token = (string) constant( 'KIB_UPDATE_CHECKER_TOKEN' );
			if ( '' !== $token ) {
				$checker->setAuthentication( $token );
			}
		}

		// Use GitHub Releases (with attached zip), not branch HEAD — predictable
		// versioning + clean rollback by re-tagging.
		$checker->getVcsApi()->enableReleaseAssets();

		// Cache update lookups for 12 hours; admin can force-check anytime.
		$checker->setCheckPeriod( 12 );
	}
}
