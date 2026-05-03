"""Dev-Server-Orchestrator — Backend ohne Docker.

Bootet embedded Postgres (`pgserver`), setzt die DATABASE_URL als env-Var,
laesst Alembic die Migrationen laufen und startet uvicorn im Vordergrund.

Postgres-Daten persistieren in `.pgsrv/` (gitignored). Qdrant laeuft
in-memory (Default in `settings`), Redis-Rate-Limit ebenfalls.

Erster Run laedt Postgres-Binaries einmalig (~50 MB) und startet pg_ctl —
beides kann auf Windows wegen Defender-Scan langsam sein. Wir patchen
deshalb pgserver's hartcodierte 10s-Timeouts auf 60s und retry'n bei
Time-out.

Stop: Ctrl+C in diesem Fenster. pgserver shuttet via atexit ab.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PGDATA = ROOT / ".pgsrv"

# Windows-Defender-Scan beim ersten pg_ctl-Aufruf braucht oft >10s.
# pgserver hat einen hartcodierten 10s-Timeout in seinem subprocess.run-
# Wrapper. Wir patchen subprocess.run BEVOR pgserver importiert wird, damit
# die kurzen Timeouts auf einen sinnvollen Wert hochgesetzt werden.
_PGCTL_TIMEOUT_SECONDS = 60

_orig_subprocess_run = subprocess.run


def _patched_subprocess_run(*args, **kwargs):  # type: ignore[no-untyped-def]
    timeout = kwargs.get("timeout")
    if isinstance(timeout, (int, float)) and timeout < _PGCTL_TIMEOUT_SECONDS:
        kwargs["timeout"] = _PGCTL_TIMEOUT_SECONDS
    return _orig_subprocess_run(*args, **kwargs)


def main() -> int:
    PGDATA.mkdir(exist_ok=True)

    print("[1/3] Boote embedded Postgres (erster Run kann 30-60s dauern)...")

    # Patch BEFORE importing pgserver so its module-level subprocess.run
    # references see the patched version.
    subprocess.run = _patched_subprocess_run  # type: ignore[assignment]

    try:
        import pgserver
    except ImportError:
        print("FEHLER: pgserver nicht installiert.")
        print("  .venv/Scripts/pip install -e \".[dev]\"")
        return 1

    last_exc: Exception | None = None
    srv = None
    for attempt in range(1, 4):
        try:
            srv = pgserver.get_server(str(PGDATA), cleanup_mode="stop")
            break
        except Exception as exc:
            last_exc = exc
            print(f"      Versuch {attempt}/3 fehlgeschlagen: {exc}")
            if attempt < 3:
                print("      Retry...")

    if srv is None:
        print()
        print(f"FEHLER beim Postgres-Boot nach 3 Versuchen: {last_exc}")
        print("Tipps:")
        print("  - reset-dev.bat ausfuehren um .pgsrv/ neu anzulegen")
        print("  - Antivirus/Defender pausieren waehrend des ersten Boots")
        print("  - Prozess-Manager: alte postgres.exe Prozesse killen")
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
