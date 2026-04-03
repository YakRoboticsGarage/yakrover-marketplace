"""Tests for the event log system (v1.0.2).

Covers: EventEmitter, event creation, filtering, SQLite persistence,
engine integration, and progress updates.
"""

from __future__ import annotations

from auction.engine import AuctionEngine
from auction.events import VALID_PROGRESS_STATES, EventEmitter, make_event
from auction.store import SyncTaskStore

# ---------------------------------------------------------------------------
# EventEmitter unit tests
# ---------------------------------------------------------------------------


class TestEventEmitter:
    def test_emit_creates_event(self):
        emitter = EventEmitter()
        event = emitter.emit("task.posted", request_id="req_001")
        assert event["event_type"] == "task.posted"
        assert event["request_id"] == "req_001"
        assert event["event_id"].startswith("evt_")
        assert event["timestamp"]

    def test_emit_with_actor(self):
        emitter = EventEmitter()
        event = emitter.emit(
            "task.progress_update",
            request_id="req_001",
            actor_id="robot_apex",
            actor_role="operator",
            data={"progress_state": "capturing", "percent_complete": 40},
        )
        assert event["actor_id"] == "robot_apex"
        assert event["actor_role"] == "operator"
        assert event["data"]["percent_complete"] == 40

    def test_event_count(self):
        emitter = EventEmitter()
        emitter.emit("task.posted")
        emitter.emit("task.awarded")
        emitter.emit("task.delivered")
        assert emitter.event_count == 3

    def test_get_events_no_filter(self):
        emitter = EventEmitter()
        emitter.emit("task.posted", request_id="req_001")
        emitter.emit("task.awarded", request_id="req_001")
        emitter.emit("task.posted", request_id="req_002")
        events = emitter.get_events()
        assert len(events) == 3

    def test_get_events_by_request_id(self):
        emitter = EventEmitter()
        emitter.emit("task.posted", request_id="req_001")
        emitter.emit("task.awarded", request_id="req_001")
        emitter.emit("task.posted", request_id="req_002")
        events = emitter.get_events(request_id="req_001")
        assert len(events) == 2
        assert all(e["request_id"] == "req_001" for e in events)

    def test_get_events_by_actor(self):
        emitter = EventEmitter()
        emitter.emit("task.bid_received", actor_id="robot_a")
        emitter.emit("task.bid_received", actor_id="robot_b")
        events = emitter.get_events(actor_id="robot_a")
        assert len(events) == 1

    def test_get_events_by_type(self):
        emitter = EventEmitter()
        emitter.emit("task.posted")
        emitter.emit("task.awarded")
        emitter.emit("task.posted")
        events = emitter.get_events(event_type="task.posted")
        assert len(events) == 2

    def test_get_events_with_limit(self):
        emitter = EventEmitter()
        for i in range(10):
            emitter.emit("task.posted", request_id=f"req_{i}")
        events = emitter.get_events(limit=3)
        assert len(events) == 3


# ---------------------------------------------------------------------------
# SQLite persistence tests
# ---------------------------------------------------------------------------


class TestEventPersistence:
    def test_save_and_query_events(self):
        store = SyncTaskStore(":memory:")
        store.initialize()
        emitter = EventEmitter(store=store)

        emitter.emit("task.posted", request_id="req_001", data={"budget": "5000"})
        emitter.emit("task.awarded", request_id="req_001", actor_id="robot_a")
        emitter.emit("task.posted", request_id="req_002")

        # Query from store directly
        events = store.query_events(request_id="req_001")
        assert len(events) == 2
        assert events[0]["event_type"] == "task.posted"
        assert events[0]["data"]["budget"] == "5000"

    def test_query_by_type(self):
        store = SyncTaskStore(":memory:")
        store.initialize()
        emitter = EventEmitter(store=store)

        emitter.emit("task.posted")
        emitter.emit("task.awarded")
        emitter.emit("payment.escrow_reserved")

        events = store.query_events(event_type="payment.escrow_reserved")
        assert len(events) == 1

    def test_query_with_limit(self):
        store = SyncTaskStore(":memory:")
        store.initialize()
        emitter = EventEmitter(store=store)

        for _i in range(20):
            emitter.emit("task.posted")

        events = store.query_events(limit=5)
        assert len(events) == 5


# ---------------------------------------------------------------------------
# Engine integration tests
# ---------------------------------------------------------------------------


class TestEngineEvents:
    def _make_engine(self):
        """Create a minimal engine with events enabled."""
        from auction.mock_fleet import create_construction_fleet

        fleet = create_construction_fleet()
        emitter = EventEmitter()
        engine = AuctionEngine(fleet, events=emitter)
        return engine, emitter

    def test_post_task_emits_events(self):
        engine, emitter = self._make_engine()
        result = engine.post_task(
            {
                "description": "Topo survey",
                "task_category": "site_survey",
                "capability_requirements": {
                    "hard": {"sensors_required": ["aerial_lidar"]},
                    "payload": {"format": "json", "fields": ["data"]},
                },
                "budget_ceiling": 5000,
                "sla_seconds": 86400,
            }
        )
        assert result["state"] == "bidding"
        # Should have posted + bidding_opened events
        events = emitter.get_events(request_id=result["request_id"])
        event_types = [e["event_type"] for e in events]
        assert "task.posted" in event_types
        assert "task.bidding_opened" in event_types

    def test_full_lifecycle_emits_events(self):
        engine, emitter = self._make_engine()
        # Post
        result = engine.post_task(
            {
                "description": "Topo survey",
                "task_category": "site_survey",
                "capability_requirements": {
                    "hard": {"sensors_required": ["aerial_lidar"]},
                    "payload": {"format": "json", "fields": ["data"]},
                },
                "budget_ceiling": 50000,
                "sla_seconds": 86400,
            }
        )
        rid = result["request_id"]

        # Get bids
        bids = engine.get_bids(rid)
        assert bids["bid_count"] > 0

        # Accept
        winner = bids["recommended_winner"]
        engine.accept_bid(rid, winner)

        events = emitter.get_events(request_id=rid)
        event_types = [e["event_type"] for e in events]
        assert "task.posted" in event_types
        assert "task.bidding_opened" in event_types
        assert "task.awarded" in event_types


# ---------------------------------------------------------------------------
# Progress state validation
# ---------------------------------------------------------------------------


class TestProgressStates:
    def test_valid_progress_states(self):
        assert "mobilizing" in VALID_PROGRESS_STATES
        assert "en_route" in VALID_PROGRESS_STATES
        assert "on_site" in VALID_PROGRESS_STATES
        assert "capturing" in VALID_PROGRESS_STATES
        assert "processing" in VALID_PROGRESS_STATES
        assert "uploading" in VALID_PROGRESS_STATES
        assert "invalid_state" not in VALID_PROGRESS_STATES

    def test_make_event(self):
        event = make_event(
            "task.progress_update",
            request_id="req_001",
            actor_id="robot_a",
            actor_role="operator",
            data={"progress_state": "capturing", "percent_complete": 60},
        )
        assert event["event_type"] == "task.progress_update"
        assert event["data"]["percent_complete"] == 60
