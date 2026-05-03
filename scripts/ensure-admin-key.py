"""Ensure `ADMIN_API_KEY` is set in `.env`.

Run by `start-dev.bat` on every dev startup. Idempotent — only generates
a new key if the slot is empty.
"""
from __future__ import annotations

import re
import secrets
import sys
from pathlib import Path


def main() -> int:
    env_path = Path(".env")
    if not env_path.exists():
        print("ERROR: .env not found in current directory", file=sys.stderr)
        return 1

    text = env_path.read_text(encoding="utf-8")
    pattern = re.compile(r"^ADMIN_API_KEY=(.*)$", flags=re.MULTILINE)
    match = pattern.search(text)

    if match and match.group(1).strip():
        print("ADMIN_API_KEY already set - keeping existing value")
        return 0

    new_key = secrets.token_hex(32)
    if match:
        text = pattern.sub(f"ADMIN_API_KEY={new_key}", text, count=1)
    else:
        text = text.rstrip("\n") + f"\nADMIN_API_KEY={new_key}\n"

    env_path.write_text(text, encoding="utf-8")
    print("ADMIN_API_KEY generated and written to .env")
    return 0


if __name__ == "__main__":
    sys.exit(main())
