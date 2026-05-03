<?php
/**
 * Plugin Name:       KI-Verkaufsberater
 * Plugin URI:        https://ki-berater.de
 * Description:       KI-Chatbot fuer WordPress. Mit WooCommerce: Berater auf Basis des Produktkatalogs. Ohne WC: generischer Chat-Bot.
 * Version:           0.3.0
 * Requires at least: 6.0
 * Requires PHP:      8.0
 * Author:            KI-Berater
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       ki-berater
 * Domain Path:       /languages
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

const KIB_VERSION       = '0.3.0';
const KIB_MIN_PHP       = '8.0';
const KIB_PLUGIN_FILE   = __FILE__;
define( 'KIB_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'KIB_PLUGIN_URL', plugin_dir_url( __FILE__ ) );

// Bail-out before loading any typed code if PHP is too old.
if ( version_compare( PHP_VERSION, KIB_MIN_PHP, '<' ) ) {
	add_action(
		'admin_notices',
		static function (): void {
			echo '<div class="notice notice-error"><p>';
			echo esc_html(
				sprintf(
					/* translators: %1$s = required version, %2$s = current version. */
					__( 'KI-Verkaufsberater benötigt PHP %1$s oder neuer. Aktuell läuft %2$s. Plugin wurde nicht geladen.', 'ki-berater' ),
					KIB_MIN_PHP,
					PHP_VERSION
				)
			);
			echo '</p></div>';
		}
	);
	return;
}

require_once KIB_PLUGIN_DIR . 'includes/class-api-client.php';
require_once KIB_PLUGIN_DIR . 'includes/class-webhook-signer.php';
require_once KIB_PLUGIN_DIR . 'includes/class-settings.php';
require_once KIB_PLUGIN_DIR . 'includes/class-widget.php';
require_once KIB_PLUGIN_DIR . 'includes/class-product-sync.php';
require_once KIB_PLUGIN_DIR . 'includes/class-bulk-sync.php';
require_once KIB_PLUGIN_DIR . 'includes/class-conversion-tracker.php';
require_once KIB_PLUGIN_DIR . 'includes/class-update-checker.php';
require_once KIB_PLUGIN_DIR . 'includes/class-plugin.php';

\KI_Berater\Plugin::instance()->boot();
