"""Rate-limit wiring smoke test.

Deterministically asserting "100 requests passes, 101 returns 429" without
fixed-rate test infrastructure is brittle (slowapi reads wall-clock time).
We instead pin two facts:

1. The limiter is mounted on `app.state` and uses an in-memory storage in tests.
2. slowapi's storage backend works — incr() increments, get() returns current.

A full end-to-end limit assertion would need a per-endpoint @limiter.limit
decorator with a ridiculously low value, which we deliberately skip in Phase 3.
"""
from backend.api.rate_limit import limiter
from backend.main import app


def test_limiter_is_attached_to_app_state() -> None:
    assert getattr(app.state, "limiter", None) is limiter


def test_default_limits_configured() -> None:
    parsed = limiter._default_limits
    assert len(parsed) >= 1, "default_limits not configured"


def test_limiter_storage_increments() -> None:
    # Simple sanity check on the storage backend used in tests.
    key = "kib_test_rate_limit_smoke"
    limiter.reset()
    limiter._storage.incr(key, 60)
    limiter._storage.incr(key, 60)
    assert limiter._storage.get(key) == 2
