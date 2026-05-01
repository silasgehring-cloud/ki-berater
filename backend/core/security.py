"""API key generation, hashing, verification, webhook HMAC signing.

Plain API keys are returned once at shop creation. Only Argon2id hashes are
stored. The 8-char prefix is stored separately for human-readable identification.
"""
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_API_KEY_BYTES = 32
_API_KEY_PREFIX_LEN = 8

_hasher = PasswordHasher()


def generate_api_key() -> tuple[str, str, str]:
    """Return (plain_key, prefix, hash). Plain key shown once, never persisted."""
    plain = secrets.token_urlsafe(_API_KEY_BYTES)
    prefix = plain[:_API_KEY_PREFIX_LEN]
    hashed = _hasher.hash(plain)
    return plain, prefix, hashed


def verify_api_key(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def generate_webhook_secret() -> str:
    """64-hex-char shared secret used for HMAC-SHA256 signing of webhook bodies."""
    return secrets.token_hex(32)


def sign_payload(secret: str, body: bytes) -> str:
    """HMAC-SHA256 of `body` with `secret`. Hex-encoded."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_signature(secret: str, body: bytes, provided: str) -> bool:
    """Constant-time comparison of HMAC-SHA256 against the provided signature."""
    expected = sign_payload(secret, body)
    return hmac.compare_digest(expected, provided)
