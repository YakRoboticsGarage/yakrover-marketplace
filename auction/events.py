"""Event log for the auction engine.

Captures every meaningful state change with timestamp, actor, and context.
Foundation for buyer/operator/admin dashboards.

See docs/research/ANALYSIS_TRACKING_DASHBOARDS.md for the full spec.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Valid execution progress states (operator-reported, not engine-enforced)
# ---------------------------------------------------------------------------

VALID_PROGRESS_STATES = frozenset(
    [
        "mobilizing",  # Reviewing specs, planning flight
        "en_route",  # Traveling to site
        "on_site",  # Arrived, setting up equipment
        "capturing",  # Data capture in progress
        "processing",  # Post-processing data
        "uploading",  # Preparing deliverables
    ]
)


def make_event(
    event_type: str,
    *,
    request_id: str | None = None,
    actor_id: str | None = None,
    actor_role: str = "system",
    data: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Create a structured event dict."""
    return {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "event_type": event_type,
        "request_id": request_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "data": data or {},
        "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
    }


class EventEmitter:
    """Collects and stores events. Wire into AuctionEngine and WalletLedger."""

    def __init__(self, store: Any = None) -> None:
        self._events: list[dict[str, Any]] = []
        self._store = store  # SyncTaskStore or None

    def emit(
        self,
        event_type: str,
        *,
        request_id: str | None = None,
        actor_id: str | None = None,
        actor_role: str = "system",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create and store an event. Returns the event dict."""
        event = make_event(
            event_type,
            request_id=request_id,
            actor_id=actor_id,
            actor_role=actor_role,
            data=data,
        )
        self._events.append(event)

        # Persist to SQLite if store is available
        if self._store is not None and hasattr(self._store, "save_event"):
            self._store.save_event(event)

        return event

    def get_events(
        self,
        *,
        request_id: str | None = None,
        actor_id: str | None = None,
        event_type: str | None = None,
        since: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query events with optional filters.

        If a store with query_events is available, delegates to it.
        Otherwise queries the in-memory list.
        """
        if self._store is not None and hasattr(self._store, "query_events"):
            return self._store.query_events(
                request_id=request_id,
                actor_id=actor_id,
                event_type=event_type,
                since=since,
                limit=limit,
            )

        results = self._events
        if request_id:
            results = [e for e in results if e["request_id"] == request_id]
        if actor_id:
            results = [e for e in results if e["actor_id"] == actor_id]
        if event_type:
            results = [e for e in results if e["event_type"] == event_type]
        if since:
            results = [e for e in results if e["timestamp"] > since]
        return results[-limit:]

    @property
    def event_count(self) -> int:
        return len(self._events)
