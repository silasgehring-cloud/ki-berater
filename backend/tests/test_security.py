"""Pure-logic tests for backend/core/security.py — no DB required."""
from backend.core.security import generate_api_key, verify_api_key


def test_generated_key_has_prefix() -> None:
    plain, prefix, hashed = generate_api_key()
    assert plain.startswith(prefix)
    assert len(prefix) == 8
    assert hashed.startswith("$argon2")


def test_verify_accepts_correct_key() -> None:
    plain, _prefix, hashed = generate_api_key()
    assert verify_api_key(plain, hashed) is True


def test_verify_rejects_wrong_key() -> None:
    _plain, _prefix, hashed = generate_api_key()
    assert verify_api_key("totally-wrong-key", hashed) is False


def test_each_key_is_unique() -> None:
    keys = {generate_api_key()[0] for _ in range(20)}
    assert len(keys) == 20


def test_verify_rejects_garbage_hash() -> None:
    assert verify_api_key("anything", "not-a-real-argon2-hash") is False
