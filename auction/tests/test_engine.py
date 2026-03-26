"""Integration tests for AuctionEngine.

Tests the full task lifecycle state machine, bid scoring, hard-constraint
filtering, and edge cases. All tests that touch execute() mock the httpx
call to the fakerover simulator.

v0.5 additions: wallet integration, timeout/abandonment, re-pooling,
bad payload handling, and auto-accept timer tests.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auction.core import Task, TaskState, verify_bid
from auction.engine import AuctionEngine
from auction.mock_fleet import (
    BadPayloadRobot,
    FakeRoverBay3,
    FakeRoverBay7,
    MockDrone01,
    TimeoutRobot,
    create_demo_fleet,
    create_scenario3_fleet,
)
from auction.reputation import ReputationTracker
from auction.wallet import WalletLedger


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VALID_TASK_SPEC = {
    "description": "Measure temperature and humidity in warehouse bay 3",
    "task_category": "env_sensing",
    "capability_requirements": {
        "hard": {
            "sensors_required": ["temperature", "humidity"],
            "indoor_capable": True,
        },
        "payload": {
            "format": "json",
            "fields": ["temperature_celsius", "humidity_percent"],
        },
    },
    "budget_ceiling": 1.00,
    "sla_seconds": 600,
}

WELDING_TASK_SPEC = {
    "description": "Inspect welding seam quality on assembly line",
    "task_category": "visual_inspection",
    "capability_requirements": {
        "hard": {
            "sensors_required": ["welding_sensor"],
        },
        "payload": {
            "format": "json",
            "fields": [],
        },
    },
    "budget_ceiling": 2.00,
    "sla_seconds": 300,
}


def _mock_httpx_patch():
    """Return a context manager that patches httpx.AsyncClient with a canned response.

    The mock intercepts ``async with httpx.AsyncClient() as client`` and
    makes ``client.get(...)`` return a response whose ``.json()`` yields
    ``{"temperature": 22.5, "humidity": 45.0}``.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"temperature": 22.5, "humidity": 45.0}
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    # httpx.AsyncClient() is used as an async context manager
    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    return patch("auction.mock_fleet.httpx.AsyncClient", mock_client_cls)


def _build_engine_at_bidding(fleet=None, task_spec=None):
    """Helper: create engine, post task, return (engine, result)."""
    if fleet is None:
        fleet = create_demo_fleet()
    if task_spec is None:
        task_spec = VALID_TASK_SPEC
    engine = AuctionEngine(fleet)
    result = engine.post_task(task_spec)
    return engine, result


def _build_engine_at_bids(fleet=None, task_spec=None):
    """Helper: create engine, post task, get bids, return (engine, post_result, bids_result)."""
    engine, post_result = _build_engine_at_bidding(fleet, task_spec)
    bids_result = engine.get_bids(post_result["request_id"])
    return engine, post_result, bids_result


def _build_engine_with_wallet(fleet=None, task_spec=None):
    """Helper: create engine with WalletLedger + ReputationTracker.

    Creates a WalletLedger, creates and funds a "buyer" wallet with $10.00,
    creates a ReputationTracker, and builds an AuctionEngine with the
    provided fleet (defaults to create_demo_fleet()).

    Returns (engine, wallet, reputation).
    """
    if fleet is None:
        fleet = create_demo_fleet()

    wallet = WalletLedger()
    wallet.create_wallet("buyer")
    wallet.fund_wallet("buyer", Decimal("10.00"), note="Initial funding")

    reputation = ReputationTracker()

    engine = AuctionEngine(fleet, wallet=wallet, reputation=reputation)
    return engine, wallet, reputation


# ---------------------------------------------------------------------------
# State transition tests
# ---------------------------------------------------------------------------


class TestStateTransitions:
    """Tests for individual state transitions in the auction lifecycle."""

    def test_post_task_transitions_to_bidding(self):
        """post_task returns state 'bidding' for valid task with eligible robots."""
        engine, result = _build_engine_at_bidding()

        assert result["state"] == "bidding"
        assert result["eligible_robots"] >= 1
        assert "request_id" in result

    def test_post_task_no_eligible_transitions_to_withdrawn(self):
        """post_task with welding sensor requirement transitions to 'withdrawn'."""
        fleet = create_demo_fleet()
        engine = AuctionEngine(fleet)
        result = engine.post_task(WELDING_TASK_SPEC)

        assert result["state"] == "withdrawn"
        assert result["eligible_robots"] == 0

    def test_get_bids_returns_scored_bids(self):
        """get_bids returns bids with scores and recommended_winner."""
        engine, post_result, bids_result = _build_engine_at_bids()

        assert bids_result["bid_count"] >= 1
        assert len(bids_result["scores"]) >= 1
        assert bids_result["recommended_winner"] is not None
        # Every bid has a score
        for robot_id in bids_result["scores"]:
            assert isinstance(bids_result["scores"][robot_id], float)
            assert 0.0 <= bids_result["scores"][robot_id] <= 1.0

    def test_accept_bid_transitions_to_bid_accepted(self):
        """accept_bid returns state 'bid_accepted'."""
        engine, post_result, bids_result = _build_engine_at_bids()

        winner = bids_result["recommended_winner"]
        accept_result = engine.accept_bid(post_result["request_id"], winner)

        assert accept_result["state"] == "bid_accepted"
        assert accept_result["winning_robot"] == winner

    def test_accept_bid_invalid_state(self):
        """Calling accept_bid on a task not in BIDDING state raises an error."""
        engine, post_result, bids_result = _build_engine_at_bids()
        request_id = post_result["request_id"]
        winner = bids_result["recommended_winner"]

        # Accept once (BIDDING -> BID_ACCEPTED)
        engine.accept_bid(request_id, winner)

        # Accept again should fail (state is BID_ACCEPTED, not BIDDING)
        with pytest.raises(ValueError, match="accept_bid requires state BIDDING"):
            engine.accept_bid(request_id, winner)

    @pytest.mark.asyncio
    async def test_confirm_delivery_transitions_to_settled(self):
        """Full lifecycle ending in 'settled'."""
        engine, post_result, bids_result = _build_engine_at_bids()
        request_id = post_result["request_id"]
        winner = bids_result["recommended_winner"]

        engine.accept_bid(request_id, winner)

        with _mock_httpx_patch():
            await engine.execute(request_id)

        settle_result = engine.confirm_delivery(request_id)
        assert settle_result["state"] == "settled"

    @pytest.mark.asyncio
    async def test_reject_delivery_transitions_to_re_pooled(self):
        """reject_delivery re-pools the task in v0.5 (REJECTED -> RE_POOLED -> BIDDING)."""
        engine, post_result, bids_result = _build_engine_at_bids()
        request_id = post_result["request_id"]
        winner = bids_result["recommended_winner"]

        engine.accept_bid(request_id, winner)

        with _mock_httpx_patch():
            await engine.execute(request_id)

        reject_result = engine.reject_delivery(request_id, reason="data looks wrong")
        # v0.5: rejection re-pools the task back to bidding
        assert reject_result["state"] == "bidding"
        assert reject_result["reason"] == "data looks wrong"
        assert reject_result["re_pooled"] is True


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """End-to-end integration tests with mocked simulator."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, capsys):
        """Async test: post -> get_bids -> accept -> execute -> confirm.

        Assert every intermediate state. Mock the httpx call to the simulator.
        """
        fleet = create_demo_fleet()
        engine = AuctionEngine(fleet)

        # 1. Post task -> BIDDING
        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]
        assert post_result["state"] == "bidding"

        # 2. Get bids (still BIDDING)
        bids_result = engine.get_bids(request_id)
        assert bids_result["state"] == "bidding"
        assert bids_result["bid_count"] >= 1
        winner = bids_result["recommended_winner"]
        assert winner is not None

        # 3. Accept bid -> BID_ACCEPTED
        accept_result = engine.accept_bid(request_id, winner)
        assert accept_result["state"] == "bid_accepted"

        # 4. Execute -> IN_PROGRESS -> DELIVERED (mocked)
        with _mock_httpx_patch():
            exec_result = await engine.execute(request_id)
        assert exec_result["state"] == "delivered"
        assert exec_result["delivery"]["sla_met"] is True

        # 5. Confirm -> VERIFIED -> SETTLED
        settle_result = engine.confirm_delivery(request_id)
        assert settle_result["state"] == "settled"

        # Verify log output contains expected tags
        captured = capsys.readouterr()
        assert "[STATE" in captured.out
        assert "[BID" in captured.out
        assert "[VERIFY" in captured.out
        assert "[SCORE" in captured.out
        assert "[PAYMENT" in captured.out

        # Verify state transition sequence in output
        assert "bidding" in captured.out
        assert "bid_accepted" in captured.out
        assert "in_progress" in captured.out
        assert "delivered" in captured.out
        assert "verified" in captured.out
        assert "settled" in captured.out

    def test_bid_signature_verified_at_acceptance(self):
        """accept_bid re-verifies the HMAC signature."""
        engine, post_result, bids_result = _build_engine_at_bids()
        request_id = post_result["request_id"]
        winner = bids_result["recommended_winner"]

        # The accept_bid method calls verify_bid internally.
        # If we tamper with the signing key, acceptance should fail.
        record = engine._get_record(request_id)
        winning_bid = None
        for b in record.bids:
            if b.robot_id == winner:
                winning_bid = b
                break

        # Verify the bid is valid with the correct key
        robot = engine._robots_by_id[winner]
        assert verify_bid(winning_bid, robot.signing_key) is True

        # Tamper with the signing key -> acceptance should fail
        original_key = robot.signing_key
        robot.signing_key = "tampered_key"
        with pytest.raises(ValueError, match="Bid signature verification failed"):
            engine.accept_bid(request_id, winner)

        # Restore and verify acceptance works
        robot.signing_key = original_key
        accept_result = engine.accept_bid(request_id, winner)
        assert accept_result["state"] == "bid_accepted"

    def test_hard_filter_excludes_drone(self):
        """Drone with rgb_camera only is excluded for temperature/humidity task."""
        fleet = create_demo_fleet()
        engine = AuctionEngine(fleet)
        result = engine.post_task(VALID_TASK_SPEC)

        # Drone should be filtered out
        assert "mock-drone-01" in result["filter_reasons"]
        reasons = result["filter_reasons"]["mock-drone-01"]
        assert any("missing_sensor" in r for r in reasons)

        # Two ground rovers should be eligible
        assert result["eligible_robots"] == 2

    def test_scenario3_cheapest_loses(self):
        """Robot X ($0.40) loses to Robot Y ($0.60). Cheapest doesn't always win."""
        fleet = create_scenario3_fleet()
        engine = AuctionEngine(fleet)

        result = engine.post_task(VALID_TASK_SPEC)
        request_id = result["request_id"]

        bids_result = engine.get_bids(request_id)

        # Robot Y should be recommended despite costing more
        assert bids_result["recommended_winner"] == "robot-y"

        # Verify robot-x scored lower
        assert bids_result["scores"]["robot-y"] > bids_result["scores"]["robot-x"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and negative tests."""

    def test_post_task_budget_below_minimum(self):
        """Budget ceiling $0.49 raises ValueError."""
        fleet = create_demo_fleet()
        engine = AuctionEngine(fleet)

        bad_spec = {**VALID_TASK_SPEC, "budget_ceiling": 0.49}
        with pytest.raises(ValueError, match="budget_ceiling must be >= \\$0.50"):
            engine.post_task(bad_spec)

    def test_accept_nonexistent_robot(self):
        """accept_bid with unknown robot_id raises error."""
        engine, post_result, bids_result = _build_engine_at_bids()
        request_id = post_result["request_id"]

        with pytest.raises(ValueError, match="No bid found from robot"):
            engine.accept_bid(request_id, "nonexistent-robot-42")


# ---------------------------------------------------------------------------
# v0.5 Wallet integration tests
# ---------------------------------------------------------------------------


class TestWalletIntegration:
    """Wallet debit/credit/refund tests for the 25%/75% split."""

    @pytest.mark.asyncio
    async def test_accept_bid_debits_wallet(self):
        """accept_bid debits 25% reservation from buyer wallet."""
        engine, wallet, reputation = _build_engine_with_wallet()
        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]

        balance_before = wallet.get_balance("buyer")
        engine.accept_bid(request_id, winner)
        balance_after = wallet.get_balance("buyer")

        # Find the winning bid price
        record = engine._get_record(request_id)
        agreed_price = record.winning_bid.price
        reservation = (agreed_price * Decimal("0.25")).quantize(Decimal("0.01"))

        assert balance_before - balance_after == reservation

    @pytest.mark.asyncio
    async def test_confirm_delivery_debits_wallet(self):
        """confirm_delivery debits 75% delivery payment from buyer wallet."""
        engine, wallet, reputation = _build_engine_with_wallet()
        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        record = engine._get_record(request_id)
        agreed_price = record.winning_bid.price
        delivery_payment = (agreed_price * Decimal("0.75")).quantize(Decimal("0.01"))

        with _mock_httpx_patch():
            await engine.execute(request_id)

        balance_before = wallet.get_balance("buyer")
        engine.confirm_delivery(request_id)
        balance_after = wallet.get_balance("buyer")

        assert balance_before - balance_after == delivery_payment

    @pytest.mark.asyncio
    async def test_confirm_delivery_credits_operator(self):
        """confirm_delivery credits full agreed price to operator wallet."""
        engine, wallet, reputation = _build_engine_with_wallet()
        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        record = engine._get_record(request_id)
        agreed_price = record.winning_bid.price

        with _mock_httpx_patch():
            await engine.execute(request_id)

        engine.confirm_delivery(request_id)

        # Operator wallet should have been created and credited
        operator_balance = wallet.get_balance(winner)
        assert operator_balance == agreed_price

    @pytest.mark.asyncio
    async def test_reject_refunds_reservation(self):
        """reject_delivery refunds 25% reservation to buyer wallet."""
        engine, wallet, reputation = _build_engine_with_wallet()
        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        record = engine._get_record(request_id)
        agreed_price = record.winning_bid.price
        reservation = (agreed_price * Decimal("0.25")).quantize(Decimal("0.01"))

        # Balance after accept (25% debited)
        balance_after_accept = wallet.get_balance("buyer")

        with _mock_httpx_patch():
            await engine.execute(request_id)

        engine.reject_delivery(request_id, reason="bad data")

        # Reservation should be refunded
        balance_after_reject = wallet.get_balance("buyer")
        assert balance_after_reject == balance_after_accept + reservation


# ---------------------------------------------------------------------------
# v0.5 Timeout / abandonment tests
# ---------------------------------------------------------------------------


class TestTimeoutAbandonment:
    """Tests for SLA timeout triggering abandonment and re-pooling."""

    @pytest.mark.asyncio
    async def test_execute_timeout_abandons(self):
        """TimeoutRobot with sla_seconds=1 triggers ABANDONED -> RE_POOLED -> BIDDING."""
        # Fleet: TimeoutRobot + a good robot (bay3)
        fleet = [TimeoutRobot(), FakeRoverBay3()]
        engine, wallet, reputation = _build_engine_with_wallet(fleet=fleet)

        task_spec = {**VALID_TASK_SPEC, "sla_seconds": 1}
        post_result = engine.post_task(task_spec)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        # Accept the timeout robot specifically
        engine.accept_bid(request_id, "timeout-robot")

        # Execute will timeout after 1 second
        exec_result = await engine.execute(request_id)

        assert exec_result["timeout"] is True
        # After timeout: ABANDONED -> RE_POOLED -> BIDDING
        record = engine._get_record(request_id)
        assert record.state == TaskState.BIDDING

    @pytest.mark.asyncio
    async def test_timeout_refunds_wallet(self):
        """SLA timeout refunds 25% reservation to buyer wallet."""
        fleet = [TimeoutRobot(), FakeRoverBay3()]
        engine, wallet, reputation = _build_engine_with_wallet(fleet=fleet)

        task_spec = {**VALID_TASK_SPEC, "sla_seconds": 1}
        post_result = engine.post_task(task_spec)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        engine.accept_bid(request_id, "timeout-robot")

        # Get the reservation amount
        record = engine._get_record(request_id)
        agreed_price = record.winning_bid.price
        reservation = (agreed_price * Decimal("0.25")).quantize(Decimal("0.01"))

        balance_after_accept = wallet.get_balance("buyer")

        # Execute will timeout
        await engine.execute(request_id)

        # 25% should be refunded
        balance_after_timeout = wallet.get_balance("buyer")
        assert balance_after_timeout == balance_after_accept + reservation

    @pytest.mark.asyncio
    async def test_timeout_records_reputation(self):
        """SLA timeout records 'abandoned' outcome in reputation tracker."""
        fleet = [TimeoutRobot(), FakeRoverBay3()]
        engine, wallet, reputation = _build_engine_with_wallet(fleet=fleet)

        task_spec = {**VALID_TASK_SPEC, "sla_seconds": 1}
        post_result = engine.post_task(task_spec)
        request_id = post_result["request_id"]

        engine.get_bids(request_id)
        engine.accept_bid(request_id, "timeout-robot")

        await engine.execute(request_id)

        # Check reputation was recorded
        rep = reputation.get_reputation("timeout-robot")
        assert rep["tasks_completed"] == 0
        # There should be at least one record (the abandonment)
        assert rep["completion_rate"] == 0.0


# ---------------------------------------------------------------------------
# v0.5 Re-pooling tests
# ---------------------------------------------------------------------------


class TestRePooling:
    """Tests for re-pooling after rejection/abandonment."""

    @pytest.mark.asyncio
    async def test_repool_increments_bid_round(self):
        """Re-pooling increments bid_round from 1 to 2."""
        engine, wallet, reputation = _build_engine_with_wallet()
        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        assert bids_result["bid_round"] == 1

        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        with _mock_httpx_patch():
            await engine.execute(request_id)

        engine.reject_delivery(request_id, reason="bad quality")

        record = engine._get_record(request_id)
        assert record.bid_round == 2

    @pytest.mark.asyncio
    async def test_repool_excludes_previous_winner(self):
        """Previous winner is filtered from next bid round."""
        engine, wallet, reputation = _build_engine_with_wallet()
        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        with _mock_httpx_patch():
            await engine.execute(request_id)

        engine.reject_delivery(request_id, reason="bad quality")

        record = engine._get_record(request_id)
        assert winner in record.previous_winners

        # Get new bids — previous winner should not appear
        bids_result_2 = engine.get_bids(request_id)
        for bid_info in bids_result_2["bids"]:
            assert bid_info["robot_id"] != winner

    @pytest.mark.asyncio
    async def test_repool_after_rejection(self):
        """Full reject -> repool -> new bid -> accept flow."""
        engine, wallet, reputation = _build_engine_with_wallet()
        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        # Round 1: first robot wins
        bids_result = engine.get_bids(request_id)
        winner_1 = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner_1)

        with _mock_httpx_patch():
            await engine.execute(request_id)

        # Reject -> re-pool
        engine.reject_delivery(request_id, reason="bad quality")

        # Round 2: get new bids, accept a new winner
        bids_result_2 = engine.get_bids(request_id)
        assert bids_result_2["bid_count"] >= 1
        winner_2 = bids_result_2["recommended_winner"]
        assert winner_2 != winner_1

        engine.accept_bid(request_id, winner_2)

        with _mock_httpx_patch():
            await engine.execute(request_id)

        # Confirm delivery in round 2 -> settled
        settle_result = engine.confirm_delivery(request_id)
        assert settle_result["state"] == "settled"


# ---------------------------------------------------------------------------
# v0.5 Bad payload tests
# ---------------------------------------------------------------------------


class TestBadPayload:
    """Tests for BadPayloadRobot delivering invalid data."""

    @pytest.mark.asyncio
    async def test_bad_payload_rejected(self):
        """BadPayloadRobot delivers None temperature; confirm_delivery raises ValueError."""
        fleet = [BadPayloadRobot(), FakeRoverBay3()]
        engine, wallet, reputation = _build_engine_with_wallet(fleet=fleet)

        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        engine.get_bids(request_id)
        engine.accept_bid(request_id, "badpayload-robot")

        # BadPayloadRobot.execute() returns invalid data (no httpx call needed)
        await engine.execute(request_id)

        # confirm_delivery should raise because temperature_celsius is None
        with pytest.raises(ValueError):
            engine.confirm_delivery(request_id)

    @pytest.mark.asyncio
    async def test_reject_then_repool_succeeds(self):
        """Reject bad payload, repool, good robot wins and settles."""
        fleet = [BadPayloadRobot(), FakeRoverBay3()]
        engine, wallet, reputation = _build_engine_with_wallet(fleet=fleet)

        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        engine.get_bids(request_id)
        engine.accept_bid(request_id, "badpayload-robot")

        # Execute bad robot
        await engine.execute(request_id)

        # Reject the bad delivery
        engine.reject_delivery(request_id, reason="invalid temperature data")

        # Round 2: good robot should win
        bids_result_2 = engine.get_bids(request_id)
        assert bids_result_2["recommended_winner"] == "fakerover-bay3"

        engine.accept_bid(request_id, "fakerover-bay3")

        with _mock_httpx_patch():
            await engine.execute(request_id)

        settle_result = engine.confirm_delivery(request_id)
        assert settle_result["state"] == "settled"


# ---------------------------------------------------------------------------
# v0.5 Auto-accept timer test
# ---------------------------------------------------------------------------


class TestAutoAccept:
    """Tests for the auto-accept timer (AD-7)."""

    @pytest.mark.asyncio
    async def test_auto_accept_timer(self):
        """auto_accept_seconds=1: deliver, wait 1.5s, verify state is SETTLED."""
        engine, wallet, reputation = _build_engine_with_wallet()

        task_spec = {**VALID_TASK_SPEC, "auto_accept_seconds": 1}
        post_result = engine.post_task(task_spec)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        with _mock_httpx_patch():
            await engine.execute(request_id)

        # State should be DELIVERED right after execute
        record = engine._get_record(request_id)
        assert record.state == TaskState.DELIVERED

        # Wait for auto-accept timer to fire (1s + 0.5s buffer)
        await asyncio.sleep(1.5)

        # Timer should have auto-confirmed delivery -> SETTLED
        assert record.state == TaskState.SETTLED
