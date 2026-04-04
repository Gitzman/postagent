"""Client-side replay protection — timestamp + nonce deduplication."""

import time
import uuid
from threading import Lock


class ReplayGuard:
    """Tracks seen message IDs to reject replayed messages.

    Messages older than ``max_age_seconds`` are rejected outright.
    Message IDs that have been seen within the window are also rejected.
    The seen-set is bounded to ``max_entries``; the oldest entries are
    evicted when the limit is reached.
    """

    def __init__(self, max_age_seconds: float = 300, max_entries: int = 10_000) -> None:
        self.max_age = max_age_seconds
        self.max_entries = max_entries
        self._seen: dict[str, float] = {}  # message_id -> receive_time
        self._lock = Lock()

    @staticmethod
    def generate_id() -> str:
        """Return a unique message ID (UUID4)."""
        return uuid.uuid4().hex

    def check(self, message_id: str, timestamp: float) -> str | None:
        """Validate a message.  Returns ``None`` if OK, or an error string."""
        now = time.time()
        age = now - timestamp
        if age > self.max_age:
            return f"message too old ({age:.0f}s > {self.max_age:.0f}s)"
        if age < -60:
            return f"message from the future ({-age:.0f}s ahead)"
        with self._lock:
            if message_id in self._seen:
                return "duplicate message_id (replay)"
            self._seen[message_id] = now
            self._prune()
        return None

    def _prune(self) -> None:
        """Evict expired entries and enforce the max-entries cap."""
        cutoff = time.time() - self.max_age
        expired = [k for k, v in self._seen.items() if v < cutoff]
        for k in expired:
            del self._seen[k]
        # If still over cap, drop oldest
        if len(self._seen) > self.max_entries:
            by_age = sorted(self._seen.items(), key=lambda kv: kv[1])
            for k, _ in by_age[: len(self._seen) - self.max_entries]:
                del self._seen[k]
