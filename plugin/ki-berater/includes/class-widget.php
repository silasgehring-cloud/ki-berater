<?php
/**
 * Frontend chat widget injection.
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

namespace KI_Berater;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class Widget {
	public function register(): void {
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_assets' ) );
		add_action( 'wp_footer', array( $this, 'render_container' ) );
	}

	public function enqueue_assets(): void {
		if ( ! $this->should_render() ) {
			return;
		}
		wp_enqueue_style(
			'kib-widget',
			KIB_PLUGIN_URL . 'assets/css/widget.css',
			array(),
			KIB_VERSION
		);
		wp_enqueue_script(
			'kib-widget',
			KIB_PLUGIN_URL . 'assets/js/widget.js',
			array(),
			KIB_VERSION,
			true
		);
		wp_localize_script(
			'kib-widget',
			'KIB_WIDGET',
			array(
				'backendUrl'   => API_Client::backend_url(),
				'apiKey'       => API_Client::api_key(),
				'brandName'    => (string) get_option( 'kib_brand_name', 'WoCom' ),
				'greeting'     => (string) get_option(
					'kib_greeting',
					'Looking for something specific? Happy to help.'
				),
				'primaryColor' => (string) get_option( 'kib_primary_color', '#7c3aed' ),
				'i18n'         => array(
					'open'        => __( 'Beratung starten', 'ki-berater' ),
					'close'       => __( 'Schließen', 'ki-berater' ),
					'placeholder' => __( 'Antworten…', 'ki-berater' ),
					'send'        => __( 'Senden', 'ki-berater' ),
					'thinking'    => __( 'Berater denkt nach…', 'ki-berater' ),
					'error'       => __( 'Es ist ein Fehler aufgetreten.', 'ki-berater' ),
					'status'      => __( 'Online · antwortet sofort', 'ki-berater' ),
				),
			)
		);
	}

	public function render_container(): void {
		if ( ! $this->should_render() ) {
			return;
		}
		echo '<div id="kib-widget-root"></div>';
	}

	private function should_render(): bool {
		if ( '1' !== (string) get_option( 'kib_widget_enabled', '1' ) ) {
			return false;
		}
		if ( ! API_Client::is_configured() ) {
			return false;
		}
		if ( is_admin() ) {
			return false;
		}
		return true;
	}
}
