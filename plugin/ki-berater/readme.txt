=== KI-Verkaufsberater ===
Contributors: kiberater
Tags: woocommerce, ai, chatbot, sales, advisor
Requires at least: 6.0
Tested up to: 6.7
Requires PHP: 8.0
Stable tag: 0.2.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

KI-Chatbot für WooCommerce. Berät Endkunden in Echtzeit auf Basis des Produktkatalogs.

== Description ==

KI-Verkaufsberater ergänzt deinen WooCommerce-Shop um einen KI-gestützten Chatbot.
Endkunden stellen Beratungsfragen ("Welcher Laufschuh für Plattfüße?"), die KI
antwortet im Stil deines Shops und empfiehlt passende Produkte aus deinem
Katalog.

* Echtzeit-Sync der Produkte via WooCommerce-Hooks (kein manuelles Aktualisieren).
* Multi-LLM-Routing (Gemini, Claude) im Backend für gute Marge.
* DSGVO-konformes Hosting in Deutschland.

Ein aktives Abo unter https://ki-berater.de wird benötigt.

== Installation ==

1. Plugin hochladen und aktivieren.
2. Unter "Einstellungen → KI-Berater" Backend-URL, API-Key und Webhook-Secret
   eintragen (du bekommst diese bei der Registrierung).
3. "Verbindung testen" klicken.
4. "Alle Produkte synchronisieren" einmalig ausführen.
5. Fertig — der Chat erscheint im Shop-Frontend.

== Changelog ==

= 0.2.0 =
* Widget-Redesign: Header mit Avatar + Brand-Name + Online-Status, weisser Hintergrund, runder Send-Button.
* Branding-Settings: Brand-Name, Begruessungstext, Primaerfarbe pro Shop konfigurierbar.
* Color-Picker im WP-Admin via wp-color-picker.

= 0.1.0 =
* Initial release: Settings-Page, Chat-Widget, Produkt-Sync via Webhook + Bulk.
