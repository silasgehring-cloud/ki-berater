# Deployment-Guide — KI-Verkaufsberater Backend

Production-Stack auf Hetzner Cloud. Single-Server, Docker-Compose.
Skaliert sauber bis ein paar hundert Shops; danach: Load-Balancer +
mehrere Backend-Replicas + extern gemanagter Postgres.

---

## 1. Server provisionieren (Hetzner Cloud)

| Komponente | Empfehlung |
|---|---|
| Region | Falkenstein (Deutschland — DSGVO) oder Nürnberg |
| Server-Typ | **CX22** für Pilot (2 vCPU, 4 GB RAM, 40 GB SSD, 4,15 €/Monat) |
| OS | Ubuntu 24.04 LTS |
| Firewall | nur `22/tcp` (SSH), `80/tcp`, `443/tcp` |
| IPv4 | mit (für Caddy/Let's Encrypt) |
| Backup | aktivieren (Hetzner-Snapshot ~20% Aufpreis) |

```bash
# Beispiel via hcloud CLI:
hcloud server create \
  --name ki-berater-prod-1 \
  --type cx22 \
  --image ubuntu-24.04 \
  --location fsn1 \
  --ssh-key your-key
```

DNS: A-Record auf die Server-IP setzen, z.B.
`api.ki-berater.de → 1.2.3.4`. Vor dem ersten `prod-deploy` propagiert lassen.

---

## 2. Server vorbereiten

```bash
ssh root@your-server-ip

# Updates + Docker
apt-get update && apt-get -y upgrade
apt-get install -y ca-certificates curl git

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | tee /etc/apt/keyrings/docker.asc > /dev/null
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Non-root deploy user
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh

# UFW
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

---

## 3. Code deployen

```bash
su - deploy
git clone https://github.com/<user>/ki-berater.git
cd ki-berater
cp .env.production.example .env
nano .env  # Domain, Email, Postgres-Passwort, ADMIN_API_KEY, LLM-Keys
```

`.env`-Pflichtfelder (alle mit `CHANGE_ME` markiert):
- `PUBLIC_DOMAIN` — exakt wie der DNS-Record
- `LETSENCRYPT_EMAIL`
- `POSTGRES_PASSWORD` — `openssl rand -hex 32`
- `ADMIN_API_KEY` — `openssl rand -hex 32`
- `ANTHROPIC_API_KEY` und/oder `GOOGLE_API_KEY`

---

## 4. Erster Start

```bash
make prod-deploy   # baut Image, startet Stack im Hintergrund
make prod-ps       # alle 5 Container "Up (healthy)"?
make prod-logs     # tail
```

Caddy holt automatisch das Let's Encrypt Zertifikat (Port 80 muss erreichbar
sein). Beim ersten Aufruf von `https://api.ki-berater.de/health` solltest du
`{"status":"ok"}` sehen.

`/ready` ist die tiefe Probe:

```bash
curl -s https://api.ki-berater.de/ready | python -m json.tool
# erwartet:
# {
#   "status": "ready",
#   "postgres": {"status": "ok"},
#   "redis":    {"status": "ok"},
#   "qdrant":   {"status": "ok"}
# }
```

---

## 5. Ersten Shop anlegen

```bash
ADMIN_KEY=$(grep ^ADMIN_API_KEY .env | cut -d= -f2)
curl -s https://api.ki-berater.de/v1/shops \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"domain":"shop.example.com","plan":"starter"}' | python -m json.tool
```

Antwort enthält `api_key` und `webhook_secret` — beide einmalig zeigen lassen
und an den Shop-Betreiber weitergeben. Plain-Werte werden nirgends nochmal
ausgegeben.

---

## 6. Updates rollen

```bash
cd ~/ki-berater
git pull
make prod-deploy   # rebuild + replace-on-update
```

Migrations laufen automatisch beim Backend-Container-Start
(`docker-entrypoint.sh` → `alembic upgrade head`). Down-Zeit pro Update: ~10–15 s.

Rollback: vorigen Git-Commit auschecken, `make prod-deploy` nochmal.

---

## 7. Backups

Manueller Backup-Trigger:
```bash
make prod-backup
```

Automatisiert via cron (auf dem Host):
```bash
crontab -e
# 0 3 * * * cd /home/deploy/ki-berater && /usr/bin/make prod-backup >> /var/log/ki-backup.log 2>&1
```

Backups landen in `postgres_data:/var/lib/postgresql/backups/ki_*.dump`. Behalten
werden 14 Tage (`KEEP_DAYS` im Skript anpassbar). Off-Site-Kopie: rsync per cron
auf eine S3-kompatible Storage Box.

---

## 8. Monitoring

Sentry-Integration ist noch nicht im Code (Phase 4). Für jetzt:

```bash
# CPU/Mem
docker stats

# strukturierte Logs
make prod-logs | grep -i error
make prod-logs | grep -E '"event":"(retention|llm)\.'

# DB-Queries (manuell)
docker compose -f docker-compose.prod.yml exec postgres psql -U ki -d ki \
  -c "SELECT shop_id, model, count(*), sum(cost_eur) FROM llm_usage WHERE created_at > now() - interval '24 hours' GROUP BY 1,2;"
```

---

## 9. Skalieren

| Ab wann | Was |
|---|---|
| ~500 Shops oder >50 RPS sustained | Backend `--workers 2 → 4`, `cx22 → cx32` (4 vCPU/8 GB) |
| ~2000 Shops | Postgres extern (Hetzner Managed PG / Aiven), Backend horizontal mit 2× Replica + Caddy als Load-Balancer |
| ~5000+ Shops | Qdrant cluster mode, Read-Replicas auf Postgres, Redis-Cluster für Rate-Limit-Storage |

---

## 10. Troubleshooting

**Caddy bekommt kein Zertifikat**
- `make prod-logs | grep caddy` — meist falscher DNS-Record oder Port 80 zu
- Hetzner-Firewall prüfen, ufw prüfen
- DNS propagiert? `dig +short api.ki-berater.de`

**Backend `/ready` zeigt `degraded`**
- `make prod-ps` — welcher Container ungesund?
- `make prod-logs` — letzte Errors
- Postgres voll? `docker exec ... df -h /var/lib/postgresql/data`

**Migration scheitert beim Deploy**
- Container restart-loopt → `docker compose -f docker-compose.prod.yml logs backend`
- Notfall-Override: `SKIP_MIGRATIONS=1` in `.env`, dann manuell rollen
- Rollback: `alembic downgrade -1` über `make prod-shell`
