<?php
/**
 * HMAC-SHA256 hex signing — must match backend/core/security.py::sign_payload.
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

namespace KI_Berater;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class Webhook_Signer {
	public static function sign( string $secret, string $body ): string {
		return hash_hmac( 'sha256', $body, $secret );
	}
}
