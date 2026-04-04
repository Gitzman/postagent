"""Tests for client-side replay protection."""

import time

from postagent.client.replay import ReplayGuard


def test_accept_fresh_message():
    guard = ReplayGuard(max_age_seconds=300)
    msg_id = ReplayGuard.generate_id()
    assert guard.check(msg_id, time.time()) is None


def test_reject_duplicate():
    guard = ReplayGuard(max_age_seconds=300)
    msg_id = ReplayGuard.generate_id()
    assert guard.check(msg_id, time.time()) is None
    err = guard.check(msg_id, time.time())
    assert err is not None
    assert "duplicate" in err


def test_reject_old_message():
    guard = ReplayGuard(max_age_seconds=300)
    msg_id = ReplayGuard.generate_id()
    old_ts = time.time() - 600  # 10 minutes ago
    err = guard.check(msg_id, old_ts)
    assert err is not None
    assert "too old" in err


def test_reject_future_message():
    guard = ReplayGuard(max_age_seconds=300)
    msg_id = ReplayGuard.generate_id()
    future_ts = time.time() + 120  # 2 minutes in the future
    err = guard.check(msg_id, future_ts)
    assert err is not None
    assert "future" in err


def test_generate_id_unique():
    ids = {ReplayGuard.generate_id() for _ in range(100)}
    assert len(ids) == 100


def test_prune_evicts_expired():
    guard = ReplayGuard(max_age_seconds=1)
    msg_id = ReplayGuard.generate_id()
    # Force an entry with old receive time
    guard._seen[msg_id] = time.time() - 2
    guard._prune()
    assert msg_id not in guard._seen


def test_max_entries_cap():
    guard = ReplayGuard(max_age_seconds=300, max_entries=5)
    for i in range(10):
        guard.check(f"msg-{i}", time.time())
    assert len(guard._seen) <= 5
