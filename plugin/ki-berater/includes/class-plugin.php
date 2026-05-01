<?php
/**
 * Top-level plugin orchestrator.
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
		( new Settings() )->register();
		( new Widget() )->register();
		( new Product_Sync() )->register();
		( new Bulk_Sync() )->register();
		( new Conversion_Tracker() )->register();
		( new Update_Checker() )->register();

		register_activation_hook( KIB_PLUGIN_FILE, array( $this, 'on_activate' ) );
		register_deactivation_hook( KIB_PLUGIN_FILE, array( $this, 'on_deactivate' ) );
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
