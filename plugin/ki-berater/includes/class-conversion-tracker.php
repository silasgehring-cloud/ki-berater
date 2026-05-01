<?php
/**
 * Conversion tracker — fires after WC checkout completes.
 *
 * Reads the `kib_conv` cookie set by the widget, sends a conversion event to
 * the backend with order_id + order_total + currency. Strictly no PII leaves
 * the shop — only those three fields.
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

namespace KI_Berater;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class Conversion_Tracker {
	private const COOKIE = 'kib_conv';
	private const UUID_RE = '/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i';

	public function register(): void {
		add_action( 'woocommerce_thankyou', array( $this, 'on_thankyou' ), 20, 1 );
	}

	public function on_thankyou( int $order_id ): void {
		if ( ! function_exists( 'wc_get_order' ) ) {
			return;
		}
		$cookie = isset( $_COOKIE[ self::COOKIE ] ) ? sanitize_text_field( wp_unslash( $_COOKIE[ self::COOKIE ] ) ) : '';
		if ( '' === $cookie || 1 !== preg_match( self::UUID_RE, $cookie ) ) {
			return;
		}
		if ( ! API_Client::is_configured() ) {
			return;
		}
		$order = wc_get_order( $order_id );
		if ( ! $order ) {
			return;
		}

		// Strict-Attribution: send the WC product IDs of all line items.
		$line_items = array();
		foreach ( $order->get_items() as $item ) {
			if ( ! method_exists( $item, 'get_product_id' ) ) {
				continue;
			}
			$pid = (int) $item->get_product_id();
			if ( $pid > 0 ) {
				$line_items[] = (string) $pid;
			}
		}

		$payload = array(
			'order_id'              => (string) $order->get_id(),
			'order_total_eur'       => (string) wc_format_decimal( (string) $order->get_total(), 2 ),
			'currency'              => function_exists( 'get_woocommerce_currency' )
				? (string) get_woocommerce_currency()
				: 'EUR',
			'line_item_external_ids' => array_values( array_unique( $line_items ) ),
		);
		$result = API_Client::post(
			'/v1/conversations/' . rawurlencode( $cookie ) . '/conversion',
			$payload
		);

		if ( null === $result['error'] ) {
			// Clear cookie so a follow-up purchase isn't double-attributed.
			setcookie( self::COOKIE, '', time() - 3600, '/' );
			unset( $_COOKIE[ self::COOKIE ] );
		}
	}
}
