=== KI-Verkaufsberater ===
Contributors: kiberater
Tags: ai, chatbot, sales, advisor, woocommerce
Requires at least: 6.0
Tested up to: 6.7
Requires PHP: 8.0
Stable tag: 0.3.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

KI-Chatbot für WordPress-Sites. Optional mit WooCommerce: berät Endkunden auf Basis des Produktkatalogs.

== Description ==

KI-Verkaufsberater ergänzt deine WordPress-Site um einen KI-gestützten Chatbot.

**Mit WooCommerce:** Endkunden stellen Beratungsfragen ("Welcher Laufschuh für
Plattfüße?"), die KI antwortet im Stil deines Shops und empfiehlt passende
Produkte aus deinem Katalog. Conversions werden automatisch gemessen.

**Ohne WooCommerce:** Generischer Chatbot ohne Produkt-Kontext — auch nutzbar
auf Blogs, Service-Seiten oder Landing-Pages.

* Echtzeit-Sync der Produkte via WooCommerce-Hooks (wenn aktiv).
* Multi-LLM-Routing (Gemini, Claude) im Backend für gute Marge.
* DSGVO-konformes Hosting in Deutschland.
* Streaming-Antworten — Wörter erscheinen live wie bei ChatGPT.
* Branding pro Shop: Name, Begrüßung, Primärfarbe konfigurierbar.

Ein aktives Abo unter https://ki-berater.de wird benötigt.

== Installation ==

1. Plugin hochladen und aktivieren.
2. Unter "Einstellungen → KI-Berater" Backend-URL, API-Key und Webhook-Secret
   eintragen (du bekommst diese bei der Registrierung).
3. "Verbindung testen" klicken.
4. Mit WC: "Alle Produkte synchronisieren" einmalig ausführen.
5. Fertig — der Chat erscheint im Shop-Frontend.

== Changelog ==

= 0.3.0 =
* Plugin funktioniert jetzt auch OHNE WooCommerce (Universal-Modus).
* Settings-Page erkennt WC-Status und zeigt Sync-Sektion nur wenn relevant.
* Admin-Notice informiert wenn WC fehlt — Plugin läuft trotzdem im Chat-Modus.

= 0.2.0 =
* Widget-Redesign: Header mit Avatar + Brand-Name + Online-Status, weisser Hintergrund, runder Send-Button.
* Branding-Settings: Brand-Name, Begruessungstext, Primaerfarbe pro Shop konfigurierbar.
* Color-Picker im WP-Admin via wp-color-picker.

= 0.1.0 =
* Initial release: Settings-Page, Chat-Widget, Produkt-Sync via Webhook + Bulk.
