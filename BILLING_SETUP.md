# Stripe-Setup-Anleitung

Schritt-für-Schritt, was im Stripe-Dashboard angelegt werden muss, bevor das
Backend Subscriptions verwalten kann. ~30 Minuten Aufwand wenn du alle Felder
parat hast.

---

## 1. Stripe-Account anlegen + verifizieren

1. Account auf https://dashboard.stripe.com erstellen.
2. Geschäftsdaten ausfüllen (Name, Steuer-ID, Bankverbindung) — Stripe braucht
   das für die Auszahlungen.
3. **Stripe Tax aktivieren** (DACH-Markt = MwSt-Pflicht):
   `Settings → Tax → Get Started`. Stripe handhabt EU-Reverse-Charge dann
   automatisch und stellt korrekte Rechnungen aus.

---

## 2. Subscription-Products anlegen

`Products → Add product` für jeden der drei kostenpflichtigen Pläne
(Enterprise wird individuell gepricet, kein public Price).

| Product | Pricing | Billing |
|---|---|---|
| KI-Berater Starter | **39,00 EUR / month** | Recurring |
| KI-Berater Growth  | **129,00 EUR / month** | Recurring |
| KI-Berater Pro     | **349,00 EUR / month** | Recurring |

Bei jedem Product:
- **Name** wie oben
- **Statement descriptor**: `KI-BERATER` (max 22 Zeichen)
- **Tax behavior**: `Exclusive` (Stripe rechnet die MwSt drauf)
- **Recurring**, monthly billing
- **Tax category**: "SaaS - Software as a Service"

Nach Speichern: jeder Plan hat eine `price_xxx`-ID. Notiere die.

---

## 3. Backend `.env` füllen

Im `.env` auf dem Server:

```bash
# Live-Mode-Key, NICHT der Test-Mode-Key
STRIPE_API_KEY=sk_live_...

# Webhook-Secret kommt aus Schritt 4
STRIPE_WEBHOOK_SECRET=whsec_...

# Price-IDs aus Schritt 2
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_GROWTH=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_ENTERPRISE=price_...   # leer lassen wenn keiner

# URLs für Stripe-Checkout-Redirects
STRIPE_SUCCESS_URL=https://api.ki-berater.de/billing/success
STRIPE_CANCEL_URL=https://api.ki-berater.de/billing/cancel
```

`make prod-deploy` neu starten, damit die ENVs gelesen werden.

---

## 4. Webhook-Endpoint registrieren

`Developers → Webhooks → Add endpoint`:

- **Endpoint URL**: `https://api.ki-berater.de/v1/webhooks/stripe`
- **API version**: aktuelle (default).
- **Events to listen for**: NUR diese fünf (sonst Noise im Backend):
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_failed` _(optional, für Email-Benachrichtigung später)_

Nach dem Speichern zeigt Stripe ein **Signing Secret** (`whsec_...`).
Das ist der Wert für `STRIPE_WEBHOOK_SECRET` in `.env`.

**Test-Send**: in der Webhook-Detail-View → `Send test webhook` →
`checkout.session.completed`. Im Backend-Log muss erscheinen:
```
"event":"billing.webhook","type":"checkout.session.completed","handled":true
```

---

## 5. Customer Portal aktivieren

`Settings → Customer portal → Activate test link`:

- **Plan changes**: Allow customers to switch plans → ja, alle drei Pläne
  zueinander schaltbar
- **Cancellation**: Allow customers to cancel — `At period end` (kein
  Sofort-Cancel — wir behalten den Customer bis Periodenende)
- **Customer information**: Email, Name editierbar
- **Tax IDs**: Customers can add tax IDs — ja
- **Invoice history**: Show invoices — ja
- **Branding**: Logo + Farbe wie auf der Landing-Page

Nach dem Speichern: das Backend-Endpoint `POST /v1/billing/portal` erzeugt
Sessions, die Stripe richtig verarbeitet.

---

## 6. Test-Lauf in Test-Mode

Bevor live geschaltet wird, einmal im Test-Mode durchspielen:

1. Stripe-Dashboard auf **"Viewing test data"** umschalten (oben rechts Toggle).
2. Test-Products + Test-Webhook anlegen wie oben (eigene Keys).
3. `STRIPE_API_KEY=sk_test_...` und Test-Price-IDs ins `.env`.
4. Backend lokal hochfahren (oder Staging).
5. Demo-Shop anlegen via `POST /v1/shops`.
6. `POST /v1/billing/checkout` mit Test-Shop-API-Key → URL aufrufen.
7. Stripe-Test-Card: `4242 4242 4242 4242`, beliebiges Datum + CVC.
8. Webhook-Log prüfen: `customer.subscription.created` muss durchgekommen sein,
   `shop.subscription_status="active"` muss in der DB stehen.
9. `GET /v1/billing/quota` mit dem Shop-Key sollte den Plan korrekt anzeigen.
10. Im Customer-Portal Plan-Wechsel testen → `subscription.updated` Webhook
    muss die `plan`-Spalte am Shop aktualisieren.

Wenn das alles klappt: zurück auf Live-Mode umschalten, neue Products + Webhook
anlegen (Test- und Live-Mode haben getrennte Resources), `.env` mit Live-Keys
aktualisieren.

---

## 7. Steuerliche Einstellungen (DACH)

- **Tax Code** für SaaS in DE: `txcd_10000000` (general — services)
- **VAT ID des eigenen Unternehmens**: in Stripe-Settings → Business details
- **Reverse-Charge-Logik**: Stripe Tax handhabt das automatisch wenn du Stripe
  Tax aktiviert hast. EU-B2B-Kunden mit gültiger USt-ID werden automatisch ohne
  MwSt abgerechnet.
- **Rechnungs-PDFs**: Stripe generiert sie automatisch im Customer Portal.
  Konfiguriere in `Settings → Branding`: Logo + Adresse + USt-ID.

---

## 8. Häufige Fallstricke

- **Test-Webhook funktioniert, Live nicht** → Live-Mode hat eigenes
  `whsec_...`. Doppelt-prüfen welcher Key in `.env` steht.
- **Subscription wird nie active** → `shop.stripe_subscription_id` muss von
  `checkout.session.completed` gesetzt werden, BEVOR `subscription.updated`
  versucht zu syncen. Wenn das nicht klappt: Webhook-Reihenfolge prüfen
  (Stripe sendet `checkout.session.completed` zuerst).
- **`construct_event` wirft `InvalidPayloadError`** → Caddy/Reverse-Proxy
  ändert den Body-Charset oder fügt Whitespace ein. Lösung: Caddy hat keinen
  Body-Filter aktiviert, das passt out-of-the-box. Andere Reverse-Proxies
  (nginx mit `proxy_request_buffering`) können das brechen.
- **Currency mismatch** — `order_total_eur` in Conversion-Endpoint vs.
  Stripe-Price ist EUR-basiert. Wenn Shop USD verkauft, klappt das System
  auch, aber die Stats zeigen "EUR" obwohl es USD ist. Phase-4-Item.
