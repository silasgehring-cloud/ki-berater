#!/usr/bin/env bash
# Quick-helper: legt einen Test-Shop via Admin-Endpoint an und schreibt
# API-Key + Webhook-Secret in eine lokale Datei (.local-shop) — fertig
# zum Copy-Paste in die Plugin-Settings-Page.
#
# Usage:
#   ADMIN_KEY=... DOMAIN=mysite.local BACKEND=http://localhost:8000 \
#     bash scripts/create-test-shop.sh
#
# Defaults:
#   BACKEND   = http://localhost:8000
#   ADMIN_KEY = aus .env (ADMIN_API_KEY)
#   DOMAIN    = wird abgefragt wenn nicht gesetzt

set -euo pipefail

BACKEND="${BACKEND:-http://localhost:8000}"

# Versuche ADMIN_KEY aus .env zu lesen wenn nicht im Environment.
if [[ -z "${ADMIN_KEY:-}" ]] && [[ -f .env ]]; then
    ADMIN_KEY="$(grep -E '^ADMIN_API_KEY=' .env | head -1 | cut -d= -f2- || true)"
fi

if [[ -z "${ADMIN_KEY:-}" ]]; then
    echo "FEHLER: ADMIN_KEY nicht gesetzt und nicht in .env gefunden."
    echo "Setze entweder:"
    echo "  export ADMIN_KEY=<dein-32-char-key>"
    echo "Oder schreibe ADMIN_API_KEY=<dein-32-char-key> in deine .env."
    exit 1
fi

if [[ -z "${DOMAIN:-}" ]]; then
    read -rp "Shop-Domain (z.B. ki-berater-test.local): " DOMAIN
fi

if [[ -z "${DOMAIN:-}" ]]; then
    echo "FEHLER: Domain ist Pflicht."
    exit 1
fi

echo
echo "Lege Shop an gegen $BACKEND..."
echo "  Domain: $DOMAIN"
echo

RESPONSE="$(curl -fsS -X POST "$BACKEND/v1/shops" \
    -H "X-Admin-Key: $ADMIN_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"domain\":\"$DOMAIN\",\"plan\":\"starter\"}" 2>&1)" || {
    echo "FEHLER: Shop konnte nicht angelegt werden."
    echo "$RESPONSE"
    exit 1
}

# Mit Python parsen — bash JSON-Parse ist fragil.
SHOP_ID="$(echo "$RESPONSE" | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
API_KEY="$(echo "$RESPONSE" | python -c 'import sys,json;print(json.load(sys.stdin)["api_key"])')"
WEBHOOK_SECRET="$(echo "$RESPONSE" | python -c 'import sys,json;print(json.load(sys.stdin)["webhook_secret"])')"
PLAN="$(echo "$RESPONSE" | python -c 'import sys,json;print(json.load(sys.stdin)["plan"])')"

# In .local-shop ablegen — gitignored, nur fuer dich.
cat > .local-shop <<EOF
# Created: $(date)
# Diese Datei NICHT committen (siehe .gitignore).

SHOP_ID=$SHOP_ID
DOMAIN=$DOMAIN
PLAN=$PLAN
BACKEND=$BACKEND

# Diese beiden Werte in die WP-Plugin-Settings einfuegen:
API_KEY=$API_KEY
WEBHOOK_SECRET=$WEBHOOK_SECRET
EOF

echo "============================================"
echo "  Shop angelegt:"
echo "============================================"
echo "  Domain:         $DOMAIN"
echo "  Plan:           $PLAN"
echo "  Shop-ID:        $SHOP_ID"
echo
echo "  Backend-URL:    $BACKEND"
echo "  API-Key:        $API_KEY"
echo "  Webhook-Secret: $WEBHOOK_SECRET"
echo
echo "Werte stehen in .local-shop — bereit zum Copy-Paste in Plugin-Settings."
echo "============================================"
