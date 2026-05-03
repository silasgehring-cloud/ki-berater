<?php
/**
 * Top-level plugin orchestrator.
 *
 * Funktioniert mit ODER ohne WooCommerce:
 * - Mit WC: Produkt-Sync, Bulk-Sync, Conversion-Tracking aktiv
 * - Ohne WC: nur Chat-Widget + Settings (Plugin verhaelt sich als
 *   generischer Chatbot ohne Shop-Kontext)
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

namespace KI_Berater;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class Plugin {
	private static ?Plugin $instance = null;

	public static function instance(): self {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}
		return self::$instance;
	}

	private function __construct() {}

	public function boot(): void {
		// Immer aktiv — funktionieren auch ohne WooCommerce.
		( new Settings() )->register();
		( new Widget() )->register();
		( new Update_Checker() )->register();

		// Nur wenn WooCommerce aktiv: Produkt- und Bestell-Hooks registrieren.
		if ( self::has_woocommerce() ) {
			( new Product_Sync() )->register();
			( new Bulk_Sync() )->register();
			( new Conversion_Tracker() )->register();
		} else {
			add_action( 'admin_notices', array( $this, 'render_no_wc_notice' ) );
		}

		register_activation_hook( KIB_PLUGIN_FILE, array( $this, 'on_activate' ) );
		register_deactivation_hook( KIB_PLUGIN_FILE, array( $this, 'on_deactivate' ) );
	}

	public static function has_woocommerce(): bool {
		return class_exists( 'WooCommerce' );
	}

	public function render_no_wc_notice(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			return;
		}
		// Nicht auf jeder Admin-Seite spammen — nur auf Plugins-, Settings-, KI-Berater-Page.
		$screen = function_exists( 'get_current_screen' ) ? get_current_screen() : null;
		if ( null !== $screen && ! in_array( $screen->id, array( 'plugins', 'settings_page_ki-berater' ), true ) ) {
			return;
		}
		echo '<div class="notice notice-info is-dismissible"><p>';
		echo esc_html__(
			'KI-Verkaufsberater laeuft im Universal-Modus. WooCommerce ist nicht aktiv — Produkt-Sync und Conversion-Tracking sind deaktiviert. Der Chat funktioniert ohne Produkt-Kontext.',
			'ki-berater'
		);
		echo '</p></div>';
	}

	public function on_activate(): void {
		add_option( 'kib_widget_enabled', '1' );
	}

	public function on_deactivate(): void {
		$timestamp = wp_next_scheduled( 'kib_bulk_sync_run' );
		if ( $timestamp ) {
			wp_unschedule_event( $timestamp, 'kib_bulk_sync_run' );
		}
	}
}
