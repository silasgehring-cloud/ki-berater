# Demo-Shop

Statische HTML-Seite, die einen Online-Shop simuliert — mit eingebettetem
Chat-Widget. Kein WordPress noetig. Praktisch fuer:

- Eigene Tests waehrend der Plugin-Entwicklung
- Demo-Aufnahmen / Screenshots
- Schnell-Vorschau ohne WP-Setup

## Voraussetzungen

1. Backend laeuft (`start-dev.bat` im Projekt-Root)
2. Test-Shop angelegt (`bash scripts/create-test-shop.sh`)
3. `.local-shop` existiert mit gueltigen Werten

## Starten

Im Projekt-Root: **Doppelklick `start-demo.bat`**

Was passiert:
1. `scripts/generate_demo_config.py` liest `.local-shop` → schreibt
   `demo/config.js` mit deinem API-Key
2. Python startet `http.server` auf Port 5000
3. Du oeffnest `http://localhost:5000`

Manuell:
```bash
.venv/Scripts/python.exe scripts/generate_demo_config.py
cd demo && ../.venv/Scripts/python.exe -m http.server 5000
```

## Was du siehst

- 6 Demo-Produkte (Trail Master, Cloud Runner, Storm Shell, Beanie, ...)
- Chat-Widget unten rechts mit deinem Branding
- Klick auf Bubble → Chat oeffnet sich
- Frage stellen → echte Gemini-Antwort wenn `GOOGLE_API_KEY` gesetzt,
  sonst Mock-Antwort

## Was NICHT funktioniert

- **In den Warenkorb / Bestellung** — nur Optik, keine echte Cart-Logik
- **Bulk-Sync** — die Demo-Produkte sind im HTML hardcoded und nicht
  im Backend indexiert. Wenn du echte Produkt-Empfehlungen vom KI willst:
  via Plugin-Settings-Page → "Alle Produkte synchronisieren" oder
  `POST /v1/products` API-Call mit den Demo-Daten.
- **Conversion-Tracking** — kein echtes Checkout, keine Conversions.

Fuer den vollen End-to-End-Flow → echtes WordPress + WooCommerce.

## Aenderungen am Plugin sind sofort live

Die Demo laedt das Widget direkt aus
`../plugin/ki-berater/assets/{js,css}/widget.{js,css}`. Wenn du etwas am
Plugin-CSS oder -JS aenderst, einfach Browser-Refresh — Aenderung ist da.

## Files

| Datei | Zweck |
|---|---|
| `index.html` | Shop-Layout mit 6 Produkt-Cards |
| `styles.css` | Shop-Styling (nicht das Widget — das kommt aus `../plugin/`) |
| `config.js` | API-Key + Branding (gitignored, auto-generated) |
| `config.example.js` | Vorlage fuer manuelle Konfiguration |
