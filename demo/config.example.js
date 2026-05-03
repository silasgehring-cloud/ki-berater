/* Demo-Konfiguration — Vorlage.
 *
 * Wenn du `start-demo.bat` benutzt, wird `config.js` automatisch aus deiner
 * .local-shop-Datei generiert. Diese Vorlage hier ist nur eine Referenz.
 *
 * Falls du manuell konfigurieren willst:
 *   cp config.example.js config.js
 *   ... und Werte unten eintragen.
 */
window.KIB_WIDGET = {
  backendUrl: 'http://localhost:8000',
  apiKey: 'PASTE_YOUR_API_KEY_HERE',
  brandName: 'WoCom',
  greeting: 'Looking for something specific? Happy to help.',
  primaryColor: '#7c3aed',
  i18n: {
    open: 'Beratung starten',
    close: 'Schliessen',
    placeholder: 'Antworten...',
    send: 'Senden',
    thinking: 'Berater denkt nach...',
    error: 'Es ist ein Fehler aufgetreten.',
    status: 'Online · antwortet sofort',
  },
};
