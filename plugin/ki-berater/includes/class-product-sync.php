<?php
/**
 * Real-time product sync to the backend via signed webhook.
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

namespace KI_Berater;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class Product_Sync {
	public function register(): void {
		add_action( 'woocommerce_new_product', array( $this, 'on_create_or_update' ), 10, 1 );
		add_action( 'woocommerce_update_product', array( $this, 'on_create_or_update' ), 10, 1 );
		add_action( 'woocommerce_delete_product', array( $this, 'on_delete' ), 10, 1 );
		add_action( 'woocommerce_trash_product', array( $this, 'on_delete' ), 10, 1 );
	}

	public function on_create_or_update( int $product_id ): void {
		if ( ! function_exists( 'wc_get_product' ) ) {
			return;
		}
		$product = wc_get_product( $product_id );
		if ( ! $product ) {
			return;
		}
		$payload = self::wc_product_to_payload( $product );
		if ( null === $payload ) {
			return;
		}
		$this->send_webhook( 'product.updated', $payload );
	}

	public function on_delete( int $product_id ): void {
		// We don't have the WC_Product after deletion — but `external_id`
		// matches the WC product ID, which we still have.
		$payload = array(
			'external_id'  => (string) $product_id,
			'name'         => '',
			'description'  => '',
			'categories'   => array(),
			'price'        => null,
			'currency'     => 'EUR',
			'stock_status' => 'outofstock',
		);
		$this->send_webhook( 'product.deleted', $payload );
	}

	/**
	 * Translate a WC_Product into the wire format the backend expects.
	 *
	 * @param \WC_Product $product
	 * @return array<string, mixed>|null
	 */
	public static function wc_product_to_payload( $product ): ?array {
		$cat_ids = (array) $product->get_category_ids();
		$cats    = array();
		foreach ( $cat_ids as $cid ) {
			$term = get_term( (int) $cid, 'product_cat' );
			if ( $term && ! is_wp_error( $term ) ) {
				$cats[] = $term->name;
			}
		}
		$price_raw = (string) $product->get_price();
		$price     = '' === $price_raw ? null : (string) wc_format_decimal( $price_raw, 2 );
		$image_url = null;
		$image_id  = (int) $product->get_image_id();
		if ( $image_id > 0 ) {
			$src = wp_get_attachment_image_url( $image_id, 'medium' );
			if ( is_string( $src ) ) {
				$image_url = $src;
			}
		}
		return array(
			'external_id'  => (string) $product->get_id(),
			'name'         => (string) $product->get_name(),
			'description'  => wp_strip_all_tags( (string) $product->get_description() ),
			'categories'   => $cats,
			'price'        => $price,
			'currency'     => function_exists( 'get_woocommerce_currency' ) ? (string) get_woocommerce_currency() : 'EUR',
			'stock_status' => (string) $product->get_stock_status(),
			'url'          => (string) get_permalink( $product->get_id() ),
			'image_url'    => $image_url,
			'sku'          => (string) $product->get_sku(),
		);
	}

	/**
	 * @param array<string, mixed> $product_payload
	 */
	private function send_webhook( string $topic, array $product_payload ): void {
		if ( ! API_Client::is_configured() ) {
			return;
		}
		$secret = API_Client::webhook_secret();
		if ( '' === $secret ) {
			return;
		}
		$body = wp_json_encode(
			array(
				'topic'   => $topic,
				'product' => $product_payload,
			)
		);
		if ( false === $body ) {
			return;
		}
		$signature = Webhook_Signer::sign( $secret, $body );
		API_Client::post_raw(
			'/v1/webhooks/products',
			$body,
			array( 'X-Webhook-Signature' => $signature )
		);
	}
}
