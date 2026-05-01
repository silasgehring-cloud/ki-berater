"""HMAC sign/verify round-trip + tamper detection."""
from backend.core.security import (
    generate_webhook_secret,
    sign_payload,
    verify_signature,
)


def test_signature_round_trip() -> None:
    secret = generate_webhook_secret()
    body = b'{"topic":"product.updated"}'
    sig = sign_payload(secret, body)
    assert verify_signature(secret, body, sig) is True


def test_signature_rejects_tampered_body() -> None:
    secret = generate_webhook_secret()
    sig = sign_payload(secret, b'{"a":1}')
    assert verify_signature(secret, b'{"a":2}', sig) is False


def test_signature_rejects_wrong_secret() -> None:
    body = b"hello"
    sig = sign_payload("secret-A", body)
    assert verify_signature("secret-B", body, sig) is False


def test_webhook_secret_is_64_hex_chars() -> None:
    s = generate_webhook_secret()
    assert len(s) == 64
    int(s, 16)  # valid hex


def test_webhook_secrets_are_unique() -> None:
    secrets_set = {generate_webhook_secret() for _ in range(20)}
    assert len(secrets_set) == 20
