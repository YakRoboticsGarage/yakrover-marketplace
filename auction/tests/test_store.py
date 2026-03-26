"""Tests for auction.store — SQLite persistence layer.

Every test uses an in-memory SQLite database (no filesystem side effects).
Requires pytest-asyncio.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

from auction.store import TaskStore, _dumps, _loads


# ---------------------------------------------------------------------------
# Fixture: fresh in-memory store per test
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def store():
    """Create and initialise an in-memory TaskStore, tear down after test."""
    s = TaskStore(":memory:")
    await s.initialize()
    yield s
    await s.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_task_dict() -> dict:
    return {
        "description": "Read temperature in warehouse",
        "task_category": "env_sensing",
        "capability_requirements": {
            "hard": {"sensors_required": ["temperature"]},
            "payload": {"format": "json", "fields": ["temperature_celsius"]},
        },
        "budget_ceiling": Decimal("1.00"),
        "sla_seconds": 300,
        "request_id": "req_test123",
        "posted_at": datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc),
    }


def _sample_bid_dict(request_id: str = "req_test123") -> dict:
    return {
        "request_id": request_id,
        "robot_id": "tumbller-01",
        "price": Decimal("0.35"),
        "sla_commitment_seconds": 180,
        "ai_confidence": 0.92,
        "capability_metadata": {"sensors": ["temperature", "humidity"]},
        "reputation_metadata": {"completion_rate": 0.95},
        "bid_hash": "abc123deadbeef",
    }


def _sample_delivery_dict() -> dict:
    return {
        "request_id": "req_test123",
        "robot_id": "tumbller-01",
        "data": {"temperature_celsius": 22.5, "humidity_percent": 45.0},
        "delivered_at": datetime(2026, 3, 24, 12, 2, 30, tzinfo=timezone.utc),
        "sla_met": True,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_creates_tables(store: TaskStore):
    """Verify that initialize() creates all expected tables."""
    db = await store._conn()

    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ) as cur:
        rows = await cur.fetchall()

    table_names = {row["name"] for row in rows}

    assert "tasks" in table_names
    assert "bids" in table_names
    assert "wallet_balances" in table_names
    assert "ledger_entries" in table_names
    assert "reputation_records" in table_names


@pytest.mark.asyncio
async def test_save_and_load_task(store: TaskStore):
    """Round-trip a task through save_task / load_task."""
    task_dict = _sample_task_dict()

    await store.save_task(
        request_id="req_test123",
        task_dict=task_dict,
        state="posted",
        bid_round=1,
    )

    loaded = await store.load_task("req_test123")
    assert loaded is not None
    assert loaded["request_id"] == "req_test123"
    assert loaded["state"] == "posted"
    assert loaded["task"]["description"] == "Read temperature in warehouse"
    assert loaded["bid_round"] == 1


@pytest.mark.asyncio
async def test_update_state(store: TaskStore):
    """update_state changes only the state column."""
    await store.save_task(
        request_id="req_s1",
        task_dict=_sample_task_dict(),
        state="posted",
    )

    await store.update_state("req_s1", "bidding")

    loaded = await store.load_task("req_s1")
    assert loaded is not None
    assert loaded["state"] == "bidding"


@pytest.mark.asyncio
async def test_load_active_tasks_filters_terminal(store: TaskStore):
    """Active tasks excludes settled and withdrawn states."""
    base = _sample_task_dict()

    # Active tasks
    await store.save_task("req_active1", base, state="bidding")
    await store.save_task("req_active2", base, state="in_progress")
    await store.save_task("req_active3", base, state="delivered")

    # Terminal tasks
    await store.save_task("req_done1", base, state="settled")
    await store.save_task("req_done2", base, state="withdrawn")

    active = await store.load_active_tasks()
    active_ids = {t["request_id"] for t in active}

    assert "req_active1" in active_ids
    assert "req_active2" in active_ids
    assert "req_active3" in active_ids
    assert "req_done1" not in active_ids
    assert "req_done2" not in active_ids


@pytest.mark.asyncio
async def test_save_and_load_bids(store: TaskStore):
    """Bids are stored and can be loaded back via the task's bids_json column."""
    bid = _sample_bid_dict()

    # Save bid to the bids table
    await store.save_bid(bid)

    # Also save task with bids_list
    await store.save_task(
        request_id="req_test123",
        task_dict=_sample_task_dict(),
        state="bidding",
        bids_list=[bid],
    )

    loaded = await store.load_task("req_test123")
    assert loaded is not None
    assert len(loaded["bids"]) == 1
    assert loaded["bids"][0]["robot_id"] == "tumbller-01"


@pytest.mark.asyncio
async def test_save_and_load_delivery(store: TaskStore):
    """Delivery data round-trips through save_delivery / load_task."""
    await store.save_task(
        request_id="req_test123",
        task_dict=_sample_task_dict(),
        state="delivered",
    )

    delivery = _sample_delivery_dict()
    await store.save_delivery("req_test123", delivery)

    loaded = await store.load_task("req_test123")
    assert loaded is not None
    assert loaded["delivery"] is not None
    assert loaded["delivery"]["data"]["temperature_celsius"] == 22.5
    assert loaded["delivery"]["sla_met"] is True


@pytest.mark.asyncio
async def test_save_and_load_wallet_balance(store: TaskStore):
    """Wallet balances survive save / load round-trip."""
    await store.save_wallet_balance("buyer", Decimal("25.00"))
    await store.save_wallet_balance("tumbller-01", Decimal("0.35"))

    balances = await store.load_wallet_balances()

    assert balances["buyer"] == Decimal("25.00")
    assert balances["tumbller-01"] == Decimal("0.35")


@pytest.mark.asyncio
async def test_save_and_load_ledger_entries(store: TaskStore):
    """Ledger entries round-trip and can be filtered by wallet_id and request_id."""
    entry1 = {
        "entry_id": "le_001",
        "wallet_id": "buyer",
        "entry_type": "fund",
        "amount": Decimal("25.00"),
        "balance_after": Decimal("25.00"),
        "request_id": "",
        "note": "Wallet funded",
        "timestamp": datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc),
    }
    entry2 = {
        "entry_id": "le_002",
        "wallet_id": "buyer",
        "entry_type": "reservation_25",
        "amount": Decimal("-0.09"),
        "balance_after": Decimal("24.91"),
        "request_id": "req_test123",
        "note": "25% reservation",
        "timestamp": datetime(2026, 3, 24, 12, 1, 0, tzinfo=timezone.utc),
    }
    entry3 = {
        "entry_id": "le_003",
        "wallet_id": "tumbller-01",
        "entry_type": "credit",
        "amount": Decimal("0.35"),
        "balance_after": Decimal("0.35"),
        "request_id": "req_test123",
        "note": "Operator payment",
        "timestamp": datetime(2026, 3, 24, 12, 5, 0, tzinfo=timezone.utc),
    }

    await store.save_ledger_entry(entry1)
    await store.save_ledger_entry(entry2)
    await store.save_ledger_entry(entry3)

    # All entries
    all_entries = await store.load_ledger_entries()
    assert len(all_entries) == 3

    # Filter by wallet_id
    buyer_entries = await store.load_ledger_entries(wallet_id="buyer")
    assert len(buyer_entries) == 2

    # Filter by request_id
    req_entries = await store.load_ledger_entries(request_id="req_test123")
    assert len(req_entries) == 2

    # Filter by both
    combined = await store.load_ledger_entries(wallet_id="buyer", request_id="req_test123")
    assert len(combined) == 1
    assert combined[0]["entry_type"] == "reservation_25"


@pytest.mark.asyncio
async def test_save_and_load_reputation_records(store: TaskStore):
    """Reputation records round-trip and filter by robot_id."""
    rec1 = {
        "robot_id": "tumbller-01",
        "request_id": "req_001",
        "outcome": "completed",
        "sla_met": True,
        "timestamp": datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc),
    }
    rec2 = {
        "robot_id": "tumbller-01",
        "request_id": "req_002",
        "outcome": "abandoned",
        "sla_met": False,
        "timestamp": datetime(2026, 3, 24, 13, 0, 0, tzinfo=timezone.utc),
    }
    rec3 = {
        "robot_id": "fakerover-01",
        "request_id": "req_003",
        "outcome": "completed",
        "sla_met": True,
        "timestamp": datetime(2026, 3, 24, 14, 0, 0, tzinfo=timezone.utc),
    }

    await store.save_reputation_record(rec1)
    await store.save_reputation_record(rec2)
    await store.save_reputation_record(rec3)

    # All records
    all_recs = await store.load_reputation_records()
    assert len(all_recs) == 3

    # Filter by robot_id
    tumbller_recs = await store.load_reputation_records(robot_id="tumbller-01")
    assert len(tumbller_recs) == 2
    assert all(r["robot_id"] == "tumbller-01" for r in tumbller_recs)

    # Check sla_met comes back as bool
    assert tumbller_recs[0]["sla_met"] is True
    assert tumbller_recs[1]["sla_met"] is False


@pytest.mark.asyncio
async def test_decimal_precision_roundtrip(store: TaskStore):
    """Decimal('0.35') survives a JSON serialize/deserialize round-trip through SQLite."""
    task_dict = _sample_task_dict()
    task_dict["budget_ceiling"] = Decimal("0.35")

    await store.save_task(
        request_id="req_dec",
        task_dict=task_dict,
        state="posted",
    )

    loaded = await store.load_task("req_dec")
    assert loaded is not None
    budget = loaded["task"]["budget_ceiling"]
    assert isinstance(budget, Decimal)
    assert budget == Decimal("0.35")
    # Ensure no float approximation — string repr must match exactly
    assert str(budget) == "0.35"

    # Also test via wallet balance
    await store.save_wallet_balance("test_wallet", Decimal("0.35"))
    balances = await store.load_wallet_balances()
    assert balances["test_wallet"] == Decimal("0.35")
    assert str(balances["test_wallet"]) == "0.35"


@pytest.mark.asyncio
async def test_datetime_roundtrip(store: TaskStore):
    """UTC datetime values survive JSON round-trip through SQLite."""
    original_dt = datetime(2026, 3, 24, 15, 30, 45, tzinfo=timezone.utc)

    task_dict = _sample_task_dict()
    task_dict["posted_at"] = original_dt

    await store.save_task(
        request_id="req_dt",
        task_dict=task_dict,
        state="posted",
    )

    loaded = await store.load_task("req_dt")
    assert loaded is not None
    posted_at = loaded["task"]["posted_at"]
    assert isinstance(posted_at, datetime)
    assert posted_at == original_dt
    assert posted_at.tzinfo is not None


@pytest.mark.asyncio
async def test_empty_database_returns_none(store: TaskStore):
    """Queries against an empty database return None / empty lists gracefully."""
    assert await store.load_task("nonexistent") is None
    assert await store.load_active_tasks() == []
    assert await store.load_wallet_balances() == {}
    assert await store.load_ledger_entries() == []
    assert await store.load_reputation_records() == []


@pytest.mark.asyncio
async def test_save_task_upsert(store: TaskStore):
    """Saving a task with the same request_id updates the existing row."""
    task_dict = _sample_task_dict()

    await store.save_task("req_up", task_dict, state="posted")
    await store.save_task("req_up", task_dict, state="bidding", bid_round=2)

    loaded = await store.load_task("req_up")
    assert loaded is not None
    assert loaded["state"] == "bidding"
    assert loaded["bid_round"] == 2


@pytest.mark.asyncio
async def test_wallet_balance_upsert(store: TaskStore):
    """Saving a wallet balance twice updates the existing row."""
    await store.save_wallet_balance("buyer", Decimal("10.00"))
    await store.save_wallet_balance("buyer", Decimal("25.00"))

    balances = await store.load_wallet_balances()
    assert balances["buyer"] == Decimal("25.00")


@pytest.mark.asyncio
async def test_json_helpers_roundtrip():
    """Internal _dumps/_loads helpers preserve Decimal and datetime exactly."""
    data = {
        "price": Decimal("1.23"),
        "timestamp": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "name": "test",
        "count": 42,
    }

    serialized = _dumps(data)
    restored = _loads(serialized)

    assert restored["price"] == Decimal("1.23")
    assert isinstance(restored["price"], Decimal)
    assert restored["timestamp"] == datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert isinstance(restored["timestamp"], datetime)
    assert restored["name"] == "test"
    assert restored["count"] == 42


@pytest.mark.asyncio
async def test_save_task_with_winning_bid_and_previous_winners(store: TaskStore):
    """Task with winning bid and previous winners round-trips correctly."""
    task_dict = _sample_task_dict()
    bid_dict = _sample_bid_dict()

    await store.save_task(
        request_id="req_full",
        task_dict=task_dict,
        state="bid_accepted",
        bid_round=2,
        winning_bid_dict=bid_dict,
        bids_list=[bid_dict],
        previous_winners=["fakerover-01"],
    )

    loaded = await store.load_task("req_full")
    assert loaded is not None
    assert loaded["winning_bid"]["robot_id"] == "tumbller-01"
    assert loaded["previous_winners"] == ["fakerover-01"]
    assert loaded["bid_round"] == 2
    assert len(loaded["bids"]) == 1
