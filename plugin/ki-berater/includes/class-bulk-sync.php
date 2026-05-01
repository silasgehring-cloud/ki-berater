<?php
/**
 * Bulk-import all WC products into the backend.
 *
 * Pattern:
 *  - AJAX click → register a job in `kib_bulk_sync_status` option, schedule a
 *    one-shot wp_cron event with batch number 1.
 *  - Each cron tick: pull a 50-product page from WC, send each to the backend
 *    SYNCHRONOUSLY via `POST /v1/products` (the synchronous single-product
 *    upsert), increment `processed`/`failed` per response, then schedule the
 *    next page.
 *
 * Why per-product sync calls instead of /v1/products/sync batches:
 *  - /v1/products/sync returns 202 + a backend job_id but processes async.
 *    Plugin never learned the actual final state, so "complete" was reported
 *    too early. Per-product calls block until each upsert is done — slower
 *    (wall-clock seconds per 100 products) but the status is honest.
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

namespace KI_Berater;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class Bulk_Sync {
	private const BATCH_SIZE = 50;
	private const HOOK       = 'kib_bulk_sync_run';

	public function register(): void {
		add_action( 'wp_ajax_kib_bulk_sync_start', array( $this, 'ajax_start' ) );
		add_action( 'wp_ajax_kib_bulk_sync_status', array( $this, 'ajax_status' ) );
		add_action( self::HOOK, array( $this, 'process_batch' ), 10, 1 );
	}

	public function ajax_start(): void {
		check_ajax_referer( Settings::NONCE );
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_send_json_error( array( 'message' => 'forbidden' ), 403 );
		}
		if ( ! API_Client::is_configured() ) {
			wp_send_json_error( array( 'message' => 'plugin not configured' ), 400 );
		}

		$total = $this->count_products();
		update_option(
			'kib_bulk_sync_status',
			array(
				'status'    => 'running',
				'total'     => $total,
				'processed' => 0,
				'failed'    => 0,
				'page'      => 1,
				'error'     => null,
				'started'   => time(),
			)
		);
		wp_schedule_single_event( time(), self::HOOK, array( 1 ) );
		wp_send_json_success( array( 'total' => $total ) );
	}

	public function ajax_status(): void {
		check_ajax_referer( Settings::NONCE );
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_send_json_error( array( 'message' => 'forbidden' ), 403 );
		}
		$status = (array) get_option( 'kib_bulk_sync_status', array() );
		wp_send_json_success(
			array(
				'status'    => $status['status'] ?? 'idle',
				'total'     => (int) ( $status['total'] ?? 0 ),
				'processed' => (int) ( $status['processed'] ?? 0 ),
				'failed'    => (int) ( $status['failed'] ?? 0 ),
				'error'     => $status['error'] ?? null,
			)
		);
	}

	public function process_batch( int $page ): void {
		if ( ! function_exists( 'wc_get_products' ) ) {
			return;
		}
		$state = (array) get_option( 'kib_bulk_sync_status', array() );
		if ( ( $state['status'] ?? '' ) !== 'running' ) {
			return;
		}

		$products = wc_get_products(
			array(
				'limit'    => self::BATCH_SIZE,
				'page'     => $page,
				'paginate' => false,
				'status'   => 'publish',
				'orderby'  => 'ID',
				'order'    => 'ASC',
			)
		);

		if ( empty( $products ) ) {
			$state['status'] = ( (int) ( $state['failed'] ?? 0 ) > 0 ) ? 'failed' : 'complete';
			update_option( 'kib_bulk_sync_status', $state );
			return;
		}

		$processed_now = 0;
		$failed_now    = 0;
		$last_error    = null;

		foreach ( $products as $product ) {
			$payload = Product_Sync::wc_product_to_payload( $product );
			if ( null === $payload ) {
				++$failed_now;
				continue;
			}
			$response = API_Client::post( '/v1/products', $payload );
			if ( null !== $response['error'] ) {
				++$failed_now;
				$last_error = $response['error'];
			} else {
				++$processed_now;
			}
		}

		$state['processed'] = (int) ( $state['processed'] ?? 0 ) + $processed_now;
		$state['failed']    = (int) ( $state['failed'] ?? 0 ) + $failed_now;
		if ( null !== $last_error ) {
			$state['error'] = $last_error;
		}
		$state['page'] = $page + 1;
		update_option( 'kib_bulk_sync_status', $state );

		// Schedule next page; small delay to avoid hot-looping the WC DB.
		wp_schedule_single_event( time() + 5, self::HOOK, array( $page + 1 ) );
	}

	private function count_products(): int {
		if ( ! function_exists( 'wp_count_posts' ) ) {
			return 0;
		}
		$counts = wp_count_posts( 'product' );
		return (int) ( $counts->publish ?? 0 );
	}
}
