<?php
/**
 * Cleanup on plugin uninstall.
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}

$kib_options = array(
	'kib_backend_url',
	'kib_api_key',
	'kib_webhook_secret',
	'kib_widget_enabled',
	'kib_bulk_sync_status',
);

foreach ( $kib_options as $kib_option ) {
	delete_option( $kib_option );
}

// Clear scheduled bulk-sync events.
$timestamp = wp_next_scheduled( 'kib_bulk_sync_run' );
if ( $timestamp ) {
	wp_unschedule_event( $timestamp, 'kib_bulk_sync_run' );
}
