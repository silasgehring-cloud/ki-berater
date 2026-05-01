<?php
/**
 * Thin wrapper around wp_remote_* with automatic X-Api-Key headers.
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

namespace KI_Berater;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class API_Client {
	public static function backend_url(): string {
		$url = (string) get_option( 'kib_backend_url', '' );
		return rtrim( $url, '/' );
	}

	public static function api_key(): string {
		return (string) get_option( 'kib_api_key', '' );
	}

	public static function webhook_secret(): string {
		return (string) get_option( 'kib_webhook_secret', '' );
	}

	public static function is_configured(): bool {
		return '' !== self::backend_url() && '' !== self::api_key();
	}

	/**
	 * @param array<string, mixed>  $body
	 * @param array<string, string> $extra_headers
	 * @return array{status:int, body:array<mixed>|null, error:?string}
	 */
	public static function post( string $path, array $body, array $extra_headers = array() ): array {
		return self::request( 'POST', $path, $body, $extra_headers );
	}

	/**
	 * @return array{status:int, body:array<mixed>|null, error:?string}
	 */
	public static function get( string $path ): array {
		return self::request( 'GET', $path, null );
	}

	/**
	 * Send a raw signed body (no JSON re-encoding). Used for webhook calls so
	 * the HMAC signature matches exactly what hits the wire.
	 *
	 * @param array<string, string> $extra_headers
	 * @return array{status:int, body:array<mixed>|null, error:?string}
	 */
	public static function post_raw( string $path, string $raw_body, array $extra_headers = array() ): array {
		$url     = self::backend_url() . $path;
		$headers = self::default_headers();
		$headers = array_merge( $headers, $extra_headers );

		$response = wp_remote_post(
			$url,
			array(
				'method'  => 'POST',
				'headers' => $headers,
				'body'    => $raw_body,
				'timeout' => 15,
			)
		);
		return self::parse_response( $response );
	}

	/**
	 * @param array<string, mixed>|null $body
	 * @param array<string, string>     $extra_headers
	 * @return array{status:int, body:array<mixed>|null, error:?string}
	 */
	private static function request( string $method, string $path, ?array $body, array $extra_headers = array() ): array {
		if ( ! self::is_configured() ) {
			return array(
				'status' => 0,
				'body'   => null,
				'error'  => 'plugin not configured (backend_url or api_key missing)',
			);
		}
		$url  = self::backend_url() . $path;
		$args = array(
			'method'  => $method,
			'headers' => array_merge( self::default_headers(), $extra_headers ),
			'timeout' => 15,
		);
		if ( null !== $body ) {
			$args['body'] = wp_json_encode( $body );
		}
		$response = wp_remote_request( $url, $args );
		return self::parse_response( $response );
	}

	/**
	 * @return array<string, string>
	 */
	private static function default_headers(): array {
		return array(
			'Content-Type' => 'application/json',
			'Accept'       => 'application/json',
			'X-Api-Key'    => self::api_key(),
			'User-Agent'   => 'KI-Berater-WP/' . KIB_VERSION,
		);
	}

	/**
	 * @param \WP_Error|array<string, mixed> $response
	 * @return array{status:int, body:array<mixed>|null, error:?string}
	 */
	private static function parse_response( $response ): array {
		if ( is_wp_error( $response ) ) {
			return array(
				'status' => 0,
				'body'   => null,
				'error'  => $response->get_error_message(),
			);
		}
		$status = (int) wp_remote_retrieve_response_code( $response );
		$raw    = wp_remote_retrieve_body( $response );
		$decoded = json_decode( $raw, true );
		$body    = is_array( $decoded ) ? $decoded : null;

		$error = null;
		if ( $status >= 400 ) {
			$detail = is_array( $body ) && isset( $body['detail'] ) ? (string) $body['detail'] : 'request failed';
			$error  = sprintf( 'HTTP %d: %s', $status, $detail );
		}
		return array(
			'status' => $status,
			'body'   => $body,
			'error'  => $error,
		);
	}
}
