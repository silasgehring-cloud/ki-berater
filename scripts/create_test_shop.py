"""Legt einen Test-Shop via Admin-Endpoint an und schreibt
API-Key + Webhook-Secret in `.local-shop` zum Copy-Paste in
Plugin-Settings.

Plattform-portabel (Windows/macOS/Linux). Aufgerufen von:
- create-test-shop.bat (Windows-Doppelklick)
- bash scripts/create-test-shop.sh (Mac/Linux — separater Pfad)

Usage:
  python scripts/create_test_shop.py [domain] [--plan starter]

ENV:
  ADMIN_KEY  -- override fuer ADMIN_API_KEY aus .env
  BACKEND    -- override fuer Backend-URL (default http://localhost:8000)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
LOCAL_SHOP = ROOT / ".local-shop"


def read_env_var(name: str) -> str | None:
    """Liest eine einzelne Variable aus .env. Returns None wenn fehlt."""
    if not ENV_FILE.exists():
        return None
    pattern = re.compile(rf"^{re.escape(name)}=(.*)$", flags=re.MULTILINE)
    match = pattern.search(ENV_FILE.read_text(encoding="utf-8"))
    if match:
        value = match.group(1).strip()
        return value or None
    return None


def resolve_admin_key() -> str:
    key = os.environ.get("ADMIN_KEY") or read_env_var("ADMIN_API_KEY")
    if not key:
        print("FEHLER: ADMIN_API_KEY nicht gefunden.", file=sys.stderr)
        print("  Setze ADMIN_API_KEY in .env oder ADMIN_KEY als env var.",
              file=sys.stderr)
        sys.exit(1)
    return key


def resolve_backend() -> str:
    return os.environ.get("BACKEND", "http://localhost:8000").rstrip("/")


def resolve_domain(cli_domain: str | None) -> str:
    if cli_domain:
        return cli_domain
    try:
        domain = input("Shop-Domain (z.B. demo.local): ").strip()
    except EOFError:
        domain = ""
    if not domain:
        print("FEHLER: Domain ist Pflicht.", file=sys.stderr)
        sys.exit(1)
    return domain


def post_shop(backend: str, admin_key: str, domain: str, plan: str) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:
        print("FEHLER: httpx nicht installiert (sollte in .venv sein).",
              file=sys.stderr)
        sys.exit(1)

    url = f"{backend}/v1/shops"
    try:
        response = httpx.post(
            url,
            headers={
                "X-Admin-Key": admin_key,
                "Content-Type": "application/json",
            },
            json={"domain": domain, "plan": plan},
            timeout=15.0,
        )
    except httpx.ConnectError:
        print(f"FEHLER: Backend unter {backend} nicht erreichbar.",
              file=sys.stderr)
        print("  Laeuft start-dev.bat?", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as exc:
        print(f"FEHLER beim HTTP-Request: {exc}", file=sys.stderr)
        sys.exit(1)

    if response.status_code == 401:
        print("FEHLER: Admin-Auth fehlgeschlagen — falscher ADMIN_API_KEY?",
              file=sys.stderr)
        sys.exit(1)
    if response.status_code == 422:
        print(f"FEHLER: Domain ungueltig: {response.text}", file=sys.stderr)
        sys.exit(1)
    if response.status_code != 201:
        print(f"FEHLER: Backend antwortete {response.status_code}: "
              f"{response.text[:300]}", file=sys.stderr)
        sys.exit(1)

    body: dict[str, Any] = response.json()
    return body


def write_local_shop(
    *,
    backend: str,
    domain: str,
    plan: str,
    body: dict[str, Any],
) -> None:
    contents = (
        f"# Created: {datetime.now().isoformat(timespec='seconds')}\n"
        "# Diese Datei NICHT committen (siehe .gitignore).\n"
        "\n"
        f"SHOP_ID={body['id']}\n"
        f"DOMAIN={domain}\n"
        f"PLAN={plan}\n"
        f"BACKEND={backend}\n"
        "\n"
        "# Diese beiden Werte in die WP-Plugin-Settings einfuegen:\n"
        f"API_KEY={body['api_key']}\n"
        f"WEBHOOK_SECRET={body['webhook_secret']}\n"
    )
    LOCAL_SHOP.write_text(contents, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test-Shop anlegen")
    parser.add_argument("domain", nargs="?", default=None,
                        help="Shop-Domain (interaktiv abgefragt wenn nicht gesetzt)")
    parser.add_argument("--plan", default="starter",
                        choices=["starter", "growth", "pro", "enterprise"])
    args = parser.parse_args()

    admin_key = resolve_admin_key()
    backend = resolve_backend()
    domain = resolve_domain(args.domain)

    print()
    print(f"Lege Shop an gegen {backend}...")
    print(f"  Domain: {domain}")
    print(f"  Plan:   {args.plan}")
    print()

    body = post_shop(backend, admin_key, domain, args.plan)
    write_local_shop(backend=backend, domain=domain, plan=args.plan, body=body)

    print("============================================")
    print("  Shop angelegt:")
    print("============================================")
    print(f"  Domain:         {domain}")
    print(f"  Plan:           {args.plan}")
    print(f"  Shop-ID:        {body['id']}")
    print()
    print(f"  Backend-URL:    {backend}")
    print(f"  API-Key:        {body['api_key']}")
    print(f"  Webhook-Secret: {body['webhook_secret']}")
    print()
    print(f"Werte stehen in {LOCAL_SHOP.relative_to(ROOT)} -- "
          "bereit zum Copy-Paste in Plugin-Settings.")
    print("============================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
