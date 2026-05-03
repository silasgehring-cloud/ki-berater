"""Dev-Server-Orchestrator — Backend ohne Docker.

Bootet embedded Postgres (`pgserver`), setzt die DATABASE_URL als env-Var,
laesst Alembic die Migrationen laufen und startet uvicorn im Vordergrund.

Postgres-Daten persistieren in `.pgsrv/` (gitignored). Qdrant laeuft
in-memory (Default in `settings`), Redis-Rate-Limit ebenfalls.

Erster Run laedt Postgres-Binaries einmalig (~50 MB).

Stop: Ctrl+C in diesem Fenster. pgserver shuttet via atexit ab.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PGDATA = ROOT / ".pgsrv"


def main() -> int:
    PGDATA.mkdir(exist_ok=True)

    print("[1/3] Boote embedded Postgres (erster Run laedt ~50 MB Binaries)...")
    try:
        import pgserver
    except ImportError:
        print("FEHLER: pgserver nicht installiert.")
        print("  .venv/Scripts/pip install -e \".[dev]\"")
        return 1

    try:
        srv = pgserver.get_server(str(PGDATA), cleanup_mode="stop")
    except Exception as exc:
        print(f"FEHLER beim Postgres-Boot: {exc}")
        print("Tipp: reset-dev.bat ausfuehren um .pgsrv/ neu anzulegen.")
        return 1

    sync_uri = srv.get_uri()
    async_uri = sync_uri.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"      Postgres ready ({async_uri.split('@')[1]})")

    env = os.environ.copy()
    env["DATABASE_URL"] = async_uri
    env.setdefault("QDRANT_MODE", ":memory:")
    env.setdefault("RATE_LIMIT_STORAGE_URI", "")
    env.setdefault("ENVIRONMENT", "development")
    # Im No-Docker-Dev-Mode laeuft kein Redis. Leerer Wert sorgt dafuer dass
    # /ready Redis als "skipped" meldet statt "fail".
    env["REDIS_URL"] = ""

    print("[2/3] Migrationen (alembic upgrade head)...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(ROOT / "backend"),
        env=env,
    )
    if result.returncode != 0:
        print("FEHLER beim alembic upgrade.")
        return result.returncode

    print()
    print("============================================")
    print("  Backend startet auf http://localhost:8000")
    print("============================================")
    print("  Ctrl+C in diesem Fenster stoppt alles.")
    print("  Postgres-Daten in .pgsrv/ bleiben erhalten.")
    print("  Test-Shop anlegen: bash scripts/create-test-shop.sh")
    print()

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=str(ROOT),
            env=env,
        )
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt empfangen.")

    print("Shutdown abgeschlossen. Daten in .pgsrv/ bleiben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
