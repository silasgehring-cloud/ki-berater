"""Generiert demo/config.js aus .local-shop.

Liest die `.local-shop`-Datei (geschrieben von scripts/create-test-shop.sh)
und schreibt eine bereit-zum-Laden Demo-Konfig nach demo/config.js.

Wird von start-demo.bat automatisch aufgerufen.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_SHOP = ROOT / ".local-shop"
DEMO_CONFIG = ROOT / "demo" / "config.js"


def parse_local_shop() -> dict[str, str]:
    if not LOCAL_SHOP.exists():
        return {}
    out: dict[str, str] = {}
    for line in LOCAL_SHOP.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Z_]+)=(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def main() -> int:
    info = parse_local_shop()
    if not info or "API_KEY" not in info:
        print("FEHLER: .local-shop fehlt oder enthaelt keinen API_KEY.")
        print("  bash scripts/create-test-shop.sh  -- erst Test-Shop anlegen")
        print(f"  (erwartet unter: {LOCAL_SHOP})")
        return 1

    backend = info.get("BACKEND", "http://localhost:8000")
    api_key = info["API_KEY"]

    config_js = f"""\
/* AUTO-GENERATED von scripts/generate_demo_config.py
 * Diese Datei NICHT committen — siehe demo/.gitignore.
 * Quelle: .local-shop
 */
window.KIB_WIDGET = {{
  backendUrl: {backend!r},
  apiKey: {api_key!r},
  brandName: 'WoCom',
  greeting: 'Looking for something specific? Happy to help.',
  primaryColor: '#7c3aed',
  i18n: {{
    open: 'Beratung starten',
    close: 'Schliessen',
    placeholder: 'Antworten...',
    send: 'Senden',
    thinking: 'Berater denkt nach...',
    error: 'Es ist ein Fehler aufgetreten.',
    status: 'Online \\u00b7 antwortet sofort',
  }},
}};
"""

    DEMO_CONFIG.parent.mkdir(exist_ok=True)
    DEMO_CONFIG.write_text(config_js, encoding="utf-8")
    print(f"OK: demo/config.js geschrieben (Backend: {backend})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
