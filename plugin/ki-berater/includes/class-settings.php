<?php
/**
 * Admin settings page under Settings → KI-Berater.
 *
 * @package KI_Berater
 */

declare( strict_types=1 );

namespace KI_Berater;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class Settings {
	public const MENU_SLUG = 'ki-berater';
	public const NONCE     = 'kib_settings_nonce';

	public function register(): void {
		add_action( 'admin_menu', array( $this, 'add_menu' ) );
		add_action( 'admin_init', array( $this, 'register_settings' ) );
		add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_admin_assets' ) );
		add_action( 'wp_ajax_kib_test_connection', array( $this, 'ajax_test_connection' ) );
		add_action( 'wp_ajax_kib_analytics_overview', array( $this, 'ajax_analytics_overview' ) );
	}

	public function add_menu(): void {
		add_options_page(
			__( 'KI-Berater', 'ki-berater' ),
			__( 'KI-Berater', 'ki-berater' ),
			'manage_woocommerce',
			self::MENU_SLUG,
			array( $this, 'render_page' )
		);
	}

	public function register_settings(): void {
		register_setting(
			'kib_settings',
			'kib_backend_url',
			array(
				'type'              => 'string',
				'sanitize_callback' => 'esc_url_raw',
				'default'           => 'http://localhost:8000',
			)
		);
		register_setting(
			'kib_settings',
			'kib_api_key',
			array(
				'type'              => 'string',
				'sanitize_callback' => 'sanitize_text_field',
			)
		);
		register_setting(
			'kib_settings',
			'kib_webhook_secret',
			array(
				'type'              => 'string',
				'sanitize_callback' => 'sanitize_text_field',
			)
		);
		register_setting(
			'kib_settings',
			'kib_widget_enabled',
			array(
				'type'              => 'string',
				'sanitize_callback' => array( $this, 'sanitize_bool' ),
				'default'           => '1',
			)
		);
	}

	public function sanitize_bool( mixed $value ): string {
		return $value ? '1' : '0';
	}

	public function enqueue_admin_assets( string $hook ): void {
		if ( 'settings_page_' . self::MENU_SLUG !== $hook ) {
			return;
		}
		wp_enqueue_style(
			'kib-admin',
			KIB_PLUGIN_URL . 'assets/css/admin.css',
			array(),
			KIB_VERSION
		);
		wp_enqueue_script(
			'kib-admin',
			KIB_PLUGIN_URL . 'assets/js/admin.js',
			array(),
			KIB_VERSION,
			true
		);
		wp_localize_script(
			'kib-admin',
			'KIB_ADMIN',
			array(
				'ajaxUrl' => admin_url( 'admin-ajax.php' ),
				'nonce'   => wp_create_nonce( self::NONCE ),
				'i18n'    => array(
					'testing'    => __( 'Teste …', 'ki-berater' ),
					'okFor'      => __( 'OK — verbunden mit Shop %s', 'ki-berater' ),
					'authFailed' => __( 'Auth fehlgeschlagen — API-Key prüfen', 'ki-berater' ),
					'noConn'     => __( 'Keine Verbindung — URL prüfen', 'ki-berater' ),
					'syncing'    => __( 'Synchronisiere …', 'ki-berater' ),
					'syncDone'   => __( 'Sync abgeschlossen: %d Produkte', 'ki-berater' ),
					'syncFailed' => __( 'Sync fehlgeschlagen: %s', 'ki-berater' ),
				),
			)
		);
	}

	public function render_page(): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_die( esc_html__( 'Zugriff verweigert.', 'ki-berater' ) );
		}
		$backend  = (string) get_option( 'kib_backend_url', 'http://localhost:8000' );
		$api_key  = (string) get_option( 'kib_api_key', '' );
		$secret   = (string) get_option( 'kib_webhook_secret', '' );
		$enabled  = '1' === (string) get_option( 'kib_widget_enabled', '1' );

		// Mask secrets so they aren't shoulder-surfed on the settings page.
		$api_key_display = '' === $api_key ? '' : substr( $api_key, 0, 6 ) . str_repeat( '•', 16 );
		$secret_display  = '' === $secret ? '' : str_repeat( '•', 16 );

		?>
		<div class="wrap kib-settings">
			<h1><?php esc_html_e( 'KI-Verkaufsberater', 'ki-berater' ); ?></h1>
			<form method="post" action="options.php">
				<?php settings_fields( 'kib_settings' ); ?>
				<table class="form-table">
					<tr>
						<th><label for="kib_backend_url"><?php esc_html_e( 'Backend-URL', 'ki-berater' ); ?></label></th>
						<td>
							<input type="url" id="kib_backend_url" name="kib_backend_url" class="regular-text"
								value="<?php echo esc_attr( $backend ); ?>" required>
							<p class="description"><?php esc_html_e( 'z.B. https://api.ki-berater.de', 'ki-berater' ); ?></p>
						</td>
					</tr>
					<tr>
						<th><label for="kib_api_key"><?php esc_html_e( 'API-Key', 'ki-berater' ); ?></label></th>
						<td>
							<input type="password" id="kib_api_key" name="kib_api_key" class="regular-text"
								value="<?php echo esc_attr( $api_key ); ?>" autocomplete="off"
								placeholder="<?php echo esc_attr( $api_key_display ); ?>">
						</td>
					</tr>
					<tr>
						<th><label for="kib_webhook_secret"><?php esc_html_e( 'Webhook-Secret', 'ki-berater' ); ?></label></th>
						<td>
							<input type="password" id="kib_webhook_secret" name="kib_webhook_secret" class="regular-text"
								value="<?php echo esc_attr( $secret ); ?>" autocomplete="off"
								placeholder="<?php echo esc_attr( $secret_display ); ?>">
							<p class="description"><?php esc_html_e( 'Wird einmalig bei Shop-Erstellung im Backend ausgegeben.', 'ki-berater' ); ?></p>
						</td>
					</tr>
					<tr>
						<th><?php esc_html_e( 'Widget aktiv', 'ki-berater' ); ?></th>
						<td>
							<label><input type="checkbox" name="kib_widget_enabled" value="1" <?php checked( $enabled ); ?>>
								<?php esc_html_e( 'Chat-Widget im Shop-Frontend anzeigen', 'ki-berater' ); ?>
							</label>
						</td>
					</tr>
				</table>
				<?php submit_button(); ?>
			</form>

			<hr>
			<h2><?php esc_html_e( 'Diagnose', 'ki-berater' ); ?></h2>
			<p>
				<button type="button" class="button button-secondary" id="kib-test-connection">
					<?php esc_html_e( 'Verbindung testen', 'ki-berater' ); ?>
				</button>
				<button type="button" class="button button-primary" id="kib-bulk-sync" style="margin-left:8px;">
					<?php esc_html_e( 'Alle Produkte synchronisieren', 'ki-berater' ); ?>
				</button>
				<span id="kib-status-msg" class="kib-status-msg" aria-live="polite"></span>
			</p>

			<hr>
			<h2><?php esc_html_e( 'Letzte 30 Tage', 'ki-berater' ); ?></h2>
			<p class="description">
				<?php esc_html_e( 'Bestellungen aus Chat-Sessions (Cookie-basiert, 30-Tage-Attribution).', 'ki-berater' ); ?>
			</p>
			<table class="widefat striped kib-overview" id="kib-overview-table">
				<tbody>
					<tr><th><?php esc_html_e( 'Gespräche', 'ki-berater' ); ?></th>
						<td id="kib-stat-total">–</td></tr>
					<tr><th><?php esc_html_e( 'Conversions', 'ki-berater' ); ?></th>
						<td id="kib-stat-converted">–</td></tr>
					<tr><th><?php esc_html_e( 'Conversion-Rate', 'ki-berater' ); ?></th>
						<td id="kib-stat-rate">–</td></tr>
					<tr><th><?php esc_html_e( 'Umsatz', 'ki-berater' ); ?></th>
						<td id="kib-stat-revenue">–</td></tr>
					<tr><th><?php esc_html_e( 'LLM-Kosten', 'ki-berater' ); ?></th>
						<td id="kib-stat-llm">–</td></tr>
				</tbody>
			</table>
		</div>
		<?php
	}

	public function ajax_analytics_overview(): void {
		check_ajax_referer( self::NONCE );
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_send_json_error( array( 'message' => 'forbidden' ), 403 );
		}
		$result = API_Client::get( '/v1/analytics/overview' );
		if ( null !== $result['error'] ) {
			wp_send_json_error( array( 'message' => $result['error'] ), $result['status'] ?: 502 );
		}
		wp_send_json_success( $result['body'] ?? array() );
	}

	public function ajax_test_connection(): void {
		check_ajax_referer( self::NONCE );
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_send_json_error( array( 'message' => 'forbidden' ), 403 );
		}
		$result = API_Client::get( '/v1/shops/me' );
		if ( null !== $result['error'] ) {
			wp_send_json_error( array( 'message' => $result['error'] ), $result['status'] ?: 502 );
		}
		$body = $result['body'] ?? array();
		wp_send_json_success(
			array(
				'domain' => isset( $body['domain'] ) ? (string) $body['domain'] : '',
				'plan'   => isset( $body['plan'] ) ? (string) $body['plan'] : '',
			)
		);
	}
}
