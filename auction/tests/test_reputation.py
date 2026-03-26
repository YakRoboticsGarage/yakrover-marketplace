"""Unit tests for auction.reputation — the reputation tracking module.

8 tests covering: defaults, recording, completion/on-time/rejection rates,
rolling window, multi-robot queries, and invalid outcome handling.

See docs/BUILD_PLAN_V05.md Phase B-3 and PRODUCT_SPEC_V05.md Section 10.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from auction.reputation import ReputationTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _ts(days_ago: int = 0) -> datetime:
    """Return a timezone-aware UTC timestamp *days_ago* days in the past."""
    return _NOW - timedelta(days=days_ago)


# ---------------------------------------------------------------------------
# 1. test_no_history_defaults
# ---------------------------------------------------------------------------

def test_no_history_defaults():
    """An unknown robot gets default reputation (completion_rate=0.5)."""
    tracker = ReputationTracker()
    rep = tracker.get_reputation("unknown_bot")

    assert rep["tasks_completed"] == 0
    assert rep["completion_rate"] == 0.5
    assert rep["on_time_rate"] == 0.0
    assert rep["rejection_rate"] == 0.0
    assert rep["rolling_window_days"] == 30


# ---------------------------------------------------------------------------
# 2. test_record_and_get
# ---------------------------------------------------------------------------

def test_record_and_get():
    """Recording one completed task and retrieving reputation works."""
    tracker = ReputationTracker()
    tracker.record_outcome(
        robot_id="bot_1",
        request_id="req_001",
        outcome="completed",
        sla_met=True,
        timestamp=_ts(0),
    )

    rep = tracker.get_reputation("bot_1")
    assert rep["tasks_completed"] == 1
    assert rep["completion_rate"] == 1.0
    assert rep["on_time_rate"] == 1.0
    assert rep["rejection_rate"] == 0.0


# ---------------------------------------------------------------------------
# 3. test_completion_rate
# ---------------------------------------------------------------------------

def test_completion_rate():
    """8 completed + 2 rejected = 0.8 completion rate."""
    tracker = ReputationTracker()

    for i in range(8):
        tracker.record_outcome(
            robot_id="bot_2",
            request_id=f"req_c_{i}",
            outcome="completed",
            sla_met=True,
            timestamp=_ts(i),
        )
    for i in range(2):
        tracker.record_outcome(
            robot_id="bot_2",
            request_id=f"req_r_{i}",
            outcome="rejected",
            sla_met=False,
            timestamp=_ts(i),
        )

    rep = tracker.get_reputation("bot_2")
    assert rep["tasks_completed"] == 8
    assert rep["completion_rate"] == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# 4. test_on_time_rate
# ---------------------------------------------------------------------------

def test_on_time_rate():
    """6 of 8 completed tasks met SLA = 0.75 on_time_rate."""
    tracker = ReputationTracker()

    # 6 completed with SLA met
    for i in range(6):
        tracker.record_outcome(
            robot_id="bot_3",
            request_id=f"req_on_{i}",
            outcome="completed",
            sla_met=True,
            timestamp=_ts(i),
        )
    # 2 completed with SLA missed
    for i in range(2):
        tracker.record_outcome(
            robot_id="bot_3",
            request_id=f"req_late_{i}",
            outcome="completed",
            sla_met=False,
            timestamp=_ts(i),
        )

    rep = tracker.get_reputation("bot_3")
    assert rep["tasks_completed"] == 8
    assert rep["on_time_rate"] == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 5. test_rejection_rate
# ---------------------------------------------------------------------------

def test_rejection_rate():
    """2 rejected of 10 total = 0.2 rejection_rate."""
    tracker = ReputationTracker()

    for i in range(8):
        tracker.record_outcome(
            robot_id="bot_4",
            request_id=f"req_ok_{i}",
            outcome="completed",
            sla_met=True,
            timestamp=_ts(i),
        )
    for i in range(2):
        tracker.record_outcome(
            robot_id="bot_4",
            request_id=f"req_rej_{i}",
            outcome="rejected",
            sla_met=False,
            timestamp=_ts(i),
        )

    rep = tracker.get_reputation("bot_4")
    assert rep["rejection_rate"] == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# 6. test_rolling_window
# ---------------------------------------------------------------------------

def test_rolling_window():
    """Records older than the rolling window are excluded."""
    tracker = ReputationTracker(rolling_window_days=7)

    # Old record — 10 days ago, outside the 7-day window
    tracker.record_outcome(
        robot_id="bot_5",
        request_id="req_old",
        outcome="rejected",
        sla_met=False,
        timestamp=_ts(days_ago=10),
    )
    # Recent record — 1 day ago, inside the window
    tracker.record_outcome(
        robot_id="bot_5",
        request_id="req_new",
        outcome="completed",
        sla_met=True,
        timestamp=_ts(days_ago=1),
    )

    rep = tracker.get_reputation("bot_5")
    # Only the recent record counts
    assert rep["tasks_completed"] == 1
    assert rep["completion_rate"] == 1.0
    assert rep["rejection_rate"] == 0.0


# ---------------------------------------------------------------------------
# 7. test_get_all_reputations
# ---------------------------------------------------------------------------

def test_get_all_reputations():
    """get_all_reputations returns a dict keyed by robot_id."""
    tracker = ReputationTracker()

    tracker.record_outcome(
        robot_id="alpha",
        request_id="req_a1",
        outcome="completed",
        sla_met=True,
        timestamp=_ts(0),
    )
    tracker.record_outcome(
        robot_id="beta",
        request_id="req_b1",
        outcome="rejected",
        sla_met=False,
        timestamp=_ts(0),
    )

    all_reps = tracker.get_all_reputations()
    assert set(all_reps.keys()) == {"alpha", "beta"}
    assert all_reps["alpha"]["tasks_completed"] == 1
    assert all_reps["alpha"]["completion_rate"] == 1.0
    assert all_reps["beta"]["tasks_completed"] == 0
    assert all_reps["beta"]["rejection_rate"] == 1.0


# ---------------------------------------------------------------------------
# 8. test_invalid_outcome
# ---------------------------------------------------------------------------

def test_invalid_outcome():
    """An invalid outcome string raises ValueError."""
    tracker = ReputationTracker()

    with pytest.raises(ValueError, match="Invalid outcome"):
        tracker.record_outcome(
            robot_id="bot_bad",
            request_id="req_bad",
            outcome="exploded",
            sla_met=False,
            timestamp=_ts(0),
        )
