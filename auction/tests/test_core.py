"""Unit tests for auction.core — the foundation module.

19 required tests covering: creation, signing, hard constraints, scoring, logging.
Plus 2 optional property-based tests via hypothesis (skipped if not installed).

See docs/BUILD_PLAN.md Iteration 6 for the full test inventory.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from auction.core import (
    VALID_TASK_CATEGORIES,
    Bid,
    LedgerEntry,
    ReputationRecord,
    Task,
    TaskState,
    check_hard_constraints,
    log,
    score_bids,
    sign_bid,
    verify_bid,
)


# ---------------------------------------------------------------------------
# Helpers — reusable factory functions to avoid repetition
# ---------------------------------------------------------------------------

def make_task(
    description: str = "Measure temperature in warehouse zone A",
    task_category: str = "env_sensing",
    capability_requirements: dict | None = None,
    budget_ceiling: Decimal = Decimal("2.00"),
    sla_seconds: int = 900,
    **kwargs,
) -> Task:
    if capability_requirements is None:
        capability_requirements = {
            "hard": {
                "sensors_required": ["temperature"],
            }
        }
    return Task(
        description=description,
        task_category=task_category,
        capability_requirements=capability_requirements,
        budget_ceiling=budget_ceiling,
        sla_seconds=sla_seconds,
        **kwargs,
    )


_SIGNING_KEY = "test-secret-key-1234"


def make_bid(
    request_id: str = "req_abc123",
    robot_id: str = "rover_bay3",
    price: Decimal = Decimal("0.75"),
    sla_commitment_seconds: int = 300,
    ai_confidence: float = 0.92,
    capability_metadata: dict | None = None,
    reputation_metadata: dict | None = None,
    key: str = _SIGNING_KEY,
) -> Bid:
    if capability_metadata is None:
        capability_metadata = {"sensors": ["temperature", "humidity"]}
    if reputation_metadata is None:
        reputation_metadata = {"completion_rate": 0.95}

    bid_hash = sign_bid(robot_id, request_id, price, key)
    return Bid(
        request_id=request_id,
        robot_id=robot_id,
        price=price,
        sla_commitment_seconds=sla_commitment_seconds,
        ai_confidence=ai_confidence,
        capability_metadata=capability_metadata,
        reputation_metadata=reputation_metadata,
        bid_hash=bid_hash,
    )


# ===================================================================
# Basic creation (tests 1–5)
# ===================================================================


class TestBasicCreation:
    """Tests 1–5: Task and Bid dataclass construction."""

    def test_task_creation(self):
        """Task with valid fields creates successfully."""
        task = make_task()
        assert task.description == "Measure temperature in warehouse zone A"
        assert task.task_category == "env_sensing"
        assert task.budget_ceiling == Decimal("2.00")
        assert task.sla_seconds == 900
        assert task.request_id.startswith("req_")
        assert task.posted_at is not None

    def test_task_budget_floor(self):
        """budget_ceiling < $0.50 raises ValueError (TC-1)."""
        with pytest.raises(ValueError, match="budget_ceiling must be >= \\$0.50"):
            make_task(budget_ceiling=Decimal("0.49"))

    def test_task_budget_exact_minimum(self):
        """budget_ceiling == $0.50 succeeds — boundary value."""
        task = make_task(budget_ceiling=Decimal("0.50"))
        assert task.budget_ceiling == Decimal("0.50")

    def test_task_invalid_category(self):
        """Invalid task_category raises ValueError."""
        with pytest.raises(ValueError, match="task_category must be one of"):
            make_task(task_category="teleportation")

    def test_bid_creation(self):
        """Bid with all fields creates successfully."""
        bid = make_bid()
        assert bid.robot_id == "rover_bay3"
        assert bid.price == Decimal("0.75")
        assert bid.ai_confidence == 0.92
        assert bid.sla_commitment_seconds == 300
        assert len(bid.bid_hash) == 64  # SHA-256 hex digest


# ===================================================================
# Signing (tests 6–9)
# ===================================================================


class TestSigning:
    """Tests 6–9: HMAC-SHA256 bid signing and verification."""

    def test_sign_bid_deterministic(self):
        """Same inputs always produce the same hash."""
        sig1 = sign_bid("rover_1", "req_001", Decimal("1.50"), "key123")
        sig2 = sign_bid("rover_1", "req_001", Decimal("1.50"), "key123")
        assert sig1 == sig2

    def test_verify_bid_valid(self):
        """Valid signature passes verification."""
        bid = make_bid()
        assert verify_bid(bid, _SIGNING_KEY) is True

    def test_verify_bid_tampered_price(self):
        """Changing price by 1 cent fails verification."""
        bid = make_bid(price=Decimal("0.75"))
        # Create a tampered bid with price changed by 1 cent
        tampered = Bid(
            request_id=bid.request_id,
            robot_id=bid.robot_id,
            price=Decimal("0.76"),  # tampered: +$0.01
            sla_commitment_seconds=bid.sla_commitment_seconds,
            ai_confidence=bid.ai_confidence,
            capability_metadata=bid.capability_metadata,
            reputation_metadata=bid.reputation_metadata,
            bid_hash=bid.bid_hash,  # original hash — won't match
        )
        assert verify_bid(tampered, _SIGNING_KEY) is False

    def test_verify_bid_wrong_key(self):
        """Wrong key fails verification."""
        bid = make_bid(key=_SIGNING_KEY)
        assert verify_bid(bid, "wrong-key-entirely") is False


# ===================================================================
# Hard constraints (tests 10–13)
# ===================================================================


class TestHardConstraints:
    """Tests 10–13: Hard constraint filtering (AD-5)."""

    def test_check_hard_constraints_pass(self):
        """Robot with required sensors passes."""
        task = make_task(
            capability_requirements={
                "hard": {"sensors_required": ["temperature", "humidity"]}
            }
        )
        robot_caps = {"sensors": ["temperature", "humidity", "lidar"]}
        eligible, reasons = check_hard_constraints(task, robot_caps)
        assert eligible is True
        assert reasons == []

    def test_check_hard_constraints_missing_sensor(self):
        """Missing sensor returns rejection reason."""
        task = make_task(
            capability_requirements={
                "hard": {"sensors_required": ["temperature", "lidar"]}
            }
        )
        robot_caps = {"sensors": ["temperature"]}
        eligible, reasons = check_hard_constraints(task, robot_caps)
        assert eligible is False
        assert "missing_sensor:lidar" in reasons

    def test_check_hard_constraints_indoor(self):
        """Indoor requirement checked correctly."""
        task = make_task(
            capability_requirements={
                "hard": {"indoor_capable": True}
            }
        )
        # Robot that is NOT indoor capable
        robot_caps = {"sensors": [], "indoor_capable": False}
        eligible, reasons = check_hard_constraints(task, robot_caps)
        assert eligible is False
        assert "not_indoor_capable" in reasons

        # Robot that IS indoor capable
        robot_caps_ok = {"sensors": [], "indoor_capable": True}
        eligible_ok, reasons_ok = check_hard_constraints(task, robot_caps_ok)
        assert eligible_ok is True
        assert reasons_ok == []

    def test_check_hard_constraints_battery(self):
        """min_battery_percent checked."""
        task = make_task(
            capability_requirements={
                "hard": {"min_battery_percent": 50}
            }
        )
        # Low battery
        robot_low = {"sensors": [], "battery_percent": 30}
        eligible, reasons = check_hard_constraints(task, robot_low)
        assert eligible is False
        assert any("battery_too_low" in r for r in reasons)

        # Sufficient battery
        robot_ok = {"sensors": [], "battery_percent": 80}
        eligible_ok, reasons_ok = check_hard_constraints(task, robot_ok)
        assert eligible_ok is True
        assert reasons_ok == []


# ===================================================================
# Scoring (tests 14–18)
# ===================================================================


class TestScoring:
    """Tests 14–18: Four-factor weighted scoring (AD-6)."""

    def test_score_bids_ordering(self):
        """Higher-scored bid sorts first."""
        task = make_task(budget_ceiling=Decimal("2.00"), sla_seconds=900)
        # Bid A: cheap, fast, confident, good reputation
        bid_a = make_bid(
            robot_id="good_bot",
            price=Decimal("0.60"),
            sla_commitment_seconds=120,
            ai_confidence=0.95,
            reputation_metadata={"completion_rate": 0.98},
        )
        # Bid B: expensive, slow, less confident, worse reputation
        bid_b = make_bid(
            robot_id="meh_bot",
            price=Decimal("1.80"),
            sla_commitment_seconds=800,
            ai_confidence=0.60,
            reputation_metadata={"completion_rate": 0.70},
        )
        results = score_bids(task, [bid_b, bid_a])  # pass in wrong order
        assert len(results) == 2
        assert results[0][0].robot_id == "good_bot"
        assert results[0][1] > results[1][1]

    def test_score_bids_over_budget_excluded(self):
        """Bid above budget_ceiling excluded."""
        task = make_task(budget_ceiling=Decimal("1.00"), sla_seconds=600)
        bid_over = make_bid(robot_id="expensive_bot", price=Decimal("1.50"))
        bid_under = make_bid(robot_id="cheap_bot", price=Decimal("0.80"))
        results = score_bids(task, [bid_over, bid_under])
        assert len(results) == 1
        assert results[0][0].robot_id == "cheap_bot"

    def test_score_bids_empty_list(self):
        """Empty bids returns empty."""
        task = make_task()
        results = score_bids(task, [])
        assert results == []

    def test_score_bids_single_bid(self):
        """Single bid returns single result."""
        task = make_task()
        bid = make_bid(price=Decimal("1.00"))
        results = score_bids(task, [bid])
        assert len(results) == 1
        assert results[0][0] is bid
        assert results[0][1] > 0

    def test_score_cheapest_does_not_win(self):
        """Cheaper bid loses to more reliable one (Scenario 3 from spec).

        Robot X: price=$0.40, SLA=600s, confidence=0.70, completion_rate=0.80
        Robot Y: price=$0.60, SLA=120s, confidence=0.97, completion_rate=0.99
        Budget ceiling: $2.00, SLA: 900s
        Expected: Robot Y wins (score ~0.840 vs ~0.663)
        """
        task = make_task(budget_ceiling=Decimal("2.00"), sla_seconds=900)

        robot_x = make_bid(
            robot_id="robot_x",
            price=Decimal("0.40"),
            sla_commitment_seconds=600,
            ai_confidence=0.70,
            reputation_metadata={"completion_rate": 0.80},
        )
        robot_y = make_bid(
            robot_id="robot_y",
            price=Decimal("0.60"),
            sla_commitment_seconds=120,
            ai_confidence=0.97,
            reputation_metadata={"completion_rate": 0.99},
        )

        results = score_bids(task, [robot_x, robot_y])
        assert len(results) == 2

        winner = results[0]
        loser = results[1]

        assert winner[0].robot_id == "robot_y", (
            f"Expected robot_y to win, got {winner[0].robot_id}"
        )
        assert loser[0].robot_id == "robot_x"

        # Verify approximate scores from the spec
        assert abs(winner[1] - 0.840) < 0.01, f"Robot Y score {winner[1]} not ~0.840"
        assert abs(loser[1] - 0.663) < 0.01, f"Robot X score {loser[1]} not ~0.663"


# ===================================================================
# Logging (test 19)
# ===================================================================


class TestLogging:
    """Test 19: Console log format."""

    def test_log_format(self, capsys):
        """log() output matches expected format: '[TAG     ] message'."""
        log("AUCTION", "Task posted successfully")
        captured = capsys.readouterr()
        # Tag is left-padded to 8 chars inside brackets
        assert captured.out.startswith("[AUCTION ")
        assert "Task posted successfully" in captured.out
        assert captured.out.strip() == "[AUCTION ] Task posted successfully"


# ===================================================================
# v0.5 additions (tests 20–23)
# ===================================================================


class TestV05Additions:
    """Tests 20–23: v0.5 core.py additions."""

    def test_wot_td_capability_metadata_structure(self):
        """WoT TD sensor list-of-dicts is accepted and parsed correctly."""
        task = make_task(
            capability_requirements={
                "hard": {"sensors_required": ["temperature"]}
            }
        )
        # WoT TD format: list of dicts with "type" key
        robot_caps = {
            "sensors": [
                {"type": "temperature", "unit": "celsius", "range": [-40, 125]},
                {"type": "humidity", "unit": "percent"},
            ]
        }
        eligible, reasons = check_hard_constraints(task, robot_caps)
        assert eligible is True
        assert reasons == []

    def test_check_hard_constraints_wot_td_sensors(self):
        """Sensor matching works with WoT TD list-of-dicts; missing sensor detected."""
        task = make_task(
            capability_requirements={
                "hard": {"sensors_required": ["temperature", "lidar"]}
            }
        )
        robot_caps = {
            "sensors": [
                {"type": "temperature", "unit": "celsius"},
            ]
        }
        eligible, reasons = check_hard_constraints(task, robot_caps)
        assert eligible is False
        assert "missing_sensor:lidar" in reasons

    def test_check_hard_constraints_backward_compat(self):
        """Flat string list (v0.1 format) still works after WoT TD changes."""
        task = make_task(
            capability_requirements={
                "hard": {"sensors_required": ["temperature", "humidity"]}
            }
        )
        robot_caps = {"sensors": ["temperature", "humidity", "lidar"]}
        eligible, reasons = check_hard_constraints(task, robot_caps)
        assert eligible is True
        assert reasons == []

    def test_provider_cancelled_state_exists(self):
        """PROVIDER_CANCELLED is a valid TaskState value."""
        assert TaskState.PROVIDER_CANCELLED == "provider_cancelled"
        assert TaskState.PROVIDER_CANCELLED.value == "provider_cancelled"
        # Ensure it's actually in the enum members
        assert "PROVIDER_CANCELLED" in TaskState.__members__


# ===================================================================
# Property-based tests (optional — skipped if hypothesis not installed)
# ===================================================================

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import assume, given
from hypothesis import strategies as st


class TestPropertyBased:
    """Two property-based tests using hypothesis."""

    @given(
        completion_rate_low=st.floats(min_value=0.01, max_value=1.0),
        completion_rate_high=st.floats(min_value=0.01, max_value=1.0),
    )
    def test_score_monotonicity_reputation(
        self, completion_rate_low, completion_rate_high
    ):
        """Higher reputation never decreases score (all else equal)."""
        assume(completion_rate_high > completion_rate_low)

        task = make_task(budget_ceiling=Decimal("2.00"), sla_seconds=900)

        bid_low = make_bid(
            robot_id="low_rep",
            price=Decimal("1.00"),
            sla_commitment_seconds=300,
            ai_confidence=0.85,
            reputation_metadata={"completion_rate": completion_rate_low},
        )
        bid_high = make_bid(
            robot_id="high_rep",
            price=Decimal("1.00"),
            sla_commitment_seconds=300,
            ai_confidence=0.85,
            reputation_metadata={"completion_rate": completion_rate_high},
        )

        results = score_bids(task, [bid_low, bid_high])
        scores = {r[0].robot_id: r[1] for r in results}
        assert scores["high_rep"] >= scores["low_rep"]

    @given(
        robot_id=st.text(min_size=1, max_size=50),
        request_id=st.text(min_size=1, max_size=50),
        price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("9999.99"), places=2),
        key=st.text(min_size=1, max_size=100),
    )
    def test_sign_verify_roundtrip(self, robot_id, request_id, price, key):
        """sign then verify always returns True."""
        sig = sign_bid(robot_id, request_id, price, key)
        bid = Bid(
            request_id=request_id,
            robot_id=robot_id,
            price=price,
            sla_commitment_seconds=300,
            ai_confidence=0.90,
            capability_metadata={},
            reputation_metadata={},
            bid_hash=sig,
        )
        assert verify_bid(bid, key) is True
