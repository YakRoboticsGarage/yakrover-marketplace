"""v1.0 integration tests — SQLite persistence, Stripe settlement, Ed25519 signing.

Tests the full lifecycle with:
- SyncTaskStore (in-memory SQLite)
- Mocked Stripe SDK
- Ed25519 signing mode
- Backward compatibility (no store, no stripe)
- All 15 MCP tools registered

All httpx calls are mocked. All Stripe SDK calls are mocked.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auction.core import Task, TaskState, sign_bid, verify_bid
from auction.engine import AuctionEngine
from auction.mock_fleet import (
    FakeRoverBay3,
    FakeRoverBay7,
    MockDrone01,
    create_demo_fleet,
)
from auction.reputation import ReputationTracker
from auction.store import SyncTaskStore
from auction.stripe_service import StripeService
from auction.wallet import StripeWalletService, WalletLedger


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
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


def _mock_httpx_patch():
    """Return a context manager that patches httpx.AsyncClient with a canned response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"temperature": 22.5, "humidity": 45.0}
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    return patch("auction.mock_fleet.httpx.AsyncClient", mock_client_cls)


def _make_store() -> SyncTaskStore:
    """Create an in-memory SyncTaskStore."""
    store = SyncTaskStore(":memory:")
    store.initialize()
    return store


def _make_wallet() -> WalletLedger:
    """Create a WalletLedger with a funded buyer wallet."""
    wallet = WalletLedger()
    wallet.create_wallet("buyer")
    wallet.fund_wallet("buyer", Decimal("10.00"), note="Test funding")
    return wallet


def _make_engine(
    fleet=None,
    wallet=None,
    reputation=None,
    store=None,
    stripe_service=None,
):
    """Build an AuctionEngine with optional v1.0 params."""
    if fleet is None:
        fleet = create_demo_fleet()
    return AuctionEngine(
        fleet,
        wallet=wallet,
        reputation=reputation,
        store=store,
        stripe_service=stripe_service,
    )


# ---------------------------------------------------------------------------
# Test 1: Full lifecycle with SQLite
# ---------------------------------------------------------------------------

class TestFullLifecycleWithSQLite:
    """post -> bid -> accept -> execute -> confirm, verify task persisted in store."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_sqlite(self):
        store = _make_store()
        wallet = _make_wallet()
        reputation = ReputationTracker()

        engine = _make_engine(
            wallet=wallet, reputation=reputation, store=store,
        )

        # 1. Post task
        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]
        assert post_result["state"] == "bidding"

        # Verify persisted after post
        stored = store.load_task(request_id)
        assert stored is not None
        assert stored["state"] == "bidding"

        # 2. Get bids
        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]

        # 3. Accept bid
        engine.accept_bid(request_id, winner)
        stored = store.load_task(request_id)
        assert stored["state"] == "bid_accepted"

        # 4. Execute (mocked)
        with _mock_httpx_patch():
            exec_result = await engine.execute(request_id)
        assert exec_result["state"] == "delivered"
        stored = store.load_task(request_id)
        assert stored["state"] == "delivered"

        # 5. Confirm delivery
        confirm_result = engine.confirm_delivery(request_id)
        assert confirm_result["state"] == "settled"
        stored = store.load_task(request_id)
        assert stored["state"] == "settled"

        store.close()


# ---------------------------------------------------------------------------
# Test 2: Restart recovery
# ---------------------------------------------------------------------------

class TestRestartRecovery:
    """Save mid-flow, create new engine from same store, verify state restored."""

    @pytest.mark.asyncio
    async def test_restart_recovery(self):
        store = _make_store()
        wallet = _make_wallet()

        # Engine 1: post task, get bids, accept bid
        engine1 = _make_engine(wallet=wallet, store=store)

        post_result = engine1.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]
        bids_result = engine1.get_bids(request_id)
        winner = bids_result["recommended_winner"]
        engine1.accept_bid(request_id, winner)

        # Verify state in store
        stored = store.load_task(request_id)
        assert stored["state"] == "bid_accepted"

        # Engine 2: create from same store — should restore the task
        engine2 = _make_engine(wallet=wallet, store=store)

        # The task should be in _tasks
        assert request_id in engine2._tasks
        record = engine2._get_record(request_id)
        assert record.state == TaskState.BID_ACCEPTED
        assert record.winning_bid is not None
        assert record.winning_bid.robot_id == winner

        store.close()


# ---------------------------------------------------------------------------
# Test 3: Stripe settlement (mocked)
# ---------------------------------------------------------------------------

class TestStripeSettlement:
    """confirm_delivery triggers mocked stripe.Transfer.create."""

    @pytest.mark.asyncio
    async def test_stripe_settlement_mocked(self):
        store = _make_store()
        wallet = _make_wallet()

        # Create a StripeService in stub mode
        stripe_svc = StripeService(api_key=None)  # stub mode

        engine = _make_engine(
            wallet=wallet, store=store, stripe_service=stripe_svc,
        )

        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        with _mock_httpx_patch():
            await engine.execute(request_id)

        confirm_result = engine.confirm_delivery(request_id)
        assert confirm_result["state"] == "settled"

        # Stripe transfer should be in the settlement
        settlement = confirm_result["settlement"]
        assert "stripe_transfer_id" in settlement
        assert "stripe_transfer" in settlement
        # In stub mode, the transfer result has "stub": True
        assert settlement["stripe_transfer"]["stub"] is True

        store.close()

    @pytest.mark.asyncio
    async def test_stripe_settlement_with_mock_sdk(self):
        """Mock the actual stripe.Transfer.create call."""
        store = _make_store()
        wallet = _make_wallet()

        # Create a real-ish StripeService but mock the stripe SDK
        stripe_svc = StripeService(api_key="sk_test_fake")

        mock_transfer = MagicMock()
        mock_transfer.to_dict_recursive.return_value = {
            "id": "tr_test_123",
            "amount": 35,
            "currency": "usd",
            "destination": "acct_fakerover-bay3",
        }

        with patch("stripe.Transfer.create", return_value=mock_transfer):
            engine = _make_engine(
                wallet=wallet, store=store, stripe_service=stripe_svc,
            )

            post_result = engine.post_task(VALID_TASK_SPEC)
            request_id = post_result["request_id"]

            bids_result = engine.get_bids(request_id)
            winner = bids_result["recommended_winner"]
            engine.accept_bid(request_id, winner)

            with _mock_httpx_patch():
                await engine.execute(request_id)

            confirm_result = engine.confirm_delivery(request_id)
            assert confirm_result["state"] == "settled"
            assert confirm_result["settlement"]["stripe_transfer_id"] == "tr_test_123"

        store.close()


# ---------------------------------------------------------------------------
# Test 4: Wallet topup (mocked)
# ---------------------------------------------------------------------------

class TestWalletTopup:
    """Mock Stripe PaymentIntent, verify wallet funded."""

    def test_wallet_topup_mocked(self):
        wallet = _make_wallet()
        stripe_svc = StripeService(api_key=None)  # stub mode

        stripe_wallet = StripeWalletService(ledger=wallet, stripe_service=stripe_svc)

        balance_before = wallet.get_balance("buyer")
        result = stripe_wallet.fund_wallet("buyer", Decimal("5.00"))

        balance_after = wallet.get_balance("buyer")
        assert balance_after == balance_before + Decimal("5.00")
        assert "payment_intent" in result
        assert result["payment_intent"]["stub"] is True
        assert result["balance"] == str(balance_after)

    def test_wallet_topup_with_mock_sdk(self):
        """Mock the actual stripe.PaymentIntent.create call."""
        wallet = _make_wallet()
        stripe_svc = StripeService(api_key="sk_test_fake")

        mock_pi = MagicMock()
        mock_pi.to_dict_recursive.return_value = {
            "id": "pi_test_456",
            "amount": 500,
            "currency": "usd",
            "status": "succeeded",
        }

        with patch("stripe.PaymentIntent.create", return_value=mock_pi):
            stripe_wallet = StripeWalletService(ledger=wallet, stripe_service=stripe_svc)
            result = stripe_wallet.fund_wallet("buyer", Decimal("5.00"))

            assert wallet.get_balance("buyer") == Decimal("15.00")
            assert result["payment_intent"]["id"] == "pi_test_456"


# ---------------------------------------------------------------------------
# Test 5: Backward compatibility — no store, no stripe
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """AuctionEngine(fleet) with no store, no stripe still works (v0.5 mode)."""

    @pytest.mark.asyncio
    async def test_backward_compat_no_store_no_stripe(self):
        fleet = create_demo_fleet()
        engine = AuctionEngine(fleet)  # v0.5 style — no extra args

        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]
        assert post_result["state"] == "bidding"

        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        with _mock_httpx_patch():
            exec_result = await engine.execute(request_id)
        assert exec_result["state"] == "delivered"

        confirm_result = engine.confirm_delivery(request_id)
        assert confirm_result["state"] == "settled"

        # No stripe_transfer_id in settlement (stripe not configured)
        assert "stripe_transfer_id" not in confirm_result["settlement"]

    @pytest.mark.asyncio
    async def test_backward_compat_with_wallet_only(self):
        """v0.5 mode with wallet and reputation but no store/stripe."""
        wallet = _make_wallet()
        reputation = ReputationTracker()
        engine = AuctionEngine(
            create_demo_fleet(), wallet=wallet, reputation=reputation,
        )

        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]
        bids_result = engine.get_bids(request_id)
        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        with _mock_httpx_patch():
            await engine.execute(request_id)

        confirm_result = engine.confirm_delivery(request_id)
        assert confirm_result["state"] == "settled"


# ---------------------------------------------------------------------------
# Test 6: Ed25519 full lifecycle
# ---------------------------------------------------------------------------

class TestEd25519Lifecycle:
    """Full lifecycle with SIGNING_MODE=ed25519."""

    @pytest.mark.asyncio
    async def test_ed25519_full_lifecycle(self, monkeypatch):
        """Set SIGNING_MODE=ed25519, generate keypair, full lifecycle."""
        # Import core and set signing mode
        import auction.core as core

        # Check if eth_account is available
        if not core._HAS_ETH_ACCOUNT:
            pytest.skip("eth_account not installed")

        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")

        # Generate key pairs for each robot
        from auction.core import generate_keypair

        fleet = create_demo_fleet()
        for robot in fleet:
            private_key, address = generate_keypair()
            robot.signing_key = private_key
            robot._signer_address = address

        # We need verify_bid to use the address, not the private key.
        # In Ed25519 mode, signing_key for bid_engine is the private key,
        # but verify_bid needs the address. The engine calls verify_bid
        # with robot.signing_key. So we need signing_key to be the
        # private key for sign_bid and the address for verify_bid.
        #
        # The current architecture uses robot.signing_key for both.
        # In Ed25519 mode, sign_bid uses private key, verify_bid uses address.
        # So we need to adjust: after bid generation, set signing_key to address
        # for verification.
        #
        # Actually, looking at the flow: bid_engine calls sign_bid with signing_key
        # (needs private key), then get_bids calls verify_bid with signing_key
        # (needs address). We need to swap between calls.
        #
        # The simplest approach: override bid_engine to sign with private key,
        # then set signing_key to address for verification.

        # Store private keys separately
        private_keys = {}
        for robot in fleet:
            private_keys[robot.robot_id] = robot.signing_key
            # For bid generation, signing_key must be private key (already set)

        store = _make_store()
        wallet = _make_wallet()

        engine = _make_engine(wallet=wallet, store=store, fleet=fleet)

        post_result = engine.post_task(VALID_TASK_SPEC)
        request_id = post_result["request_id"]

        # Before get_bids, robots need private keys for signing
        for robot in fleet:
            robot.signing_key = private_keys[robot.robot_id]

        bids_result = engine.get_bids(request_id)

        # After bids are generated, set signing_key to address for verification
        # (accept_bid re-verifies)
        for robot in fleet:
            robot.signing_key = robot._signer_address

        winner = bids_result["recommended_winner"]
        engine.accept_bid(request_id, winner)

        with _mock_httpx_patch():
            exec_result = await engine.execute(request_id)
        assert exec_result["state"] == "delivered"

        confirm_result = engine.confirm_delivery(request_id)
        assert confirm_result["state"] == "settled"

        # Restore original signing mode
        store.close()


# ---------------------------------------------------------------------------
# Test 7: All 15 MCP tools registered
# ---------------------------------------------------------------------------

class TestMCPToolsRegistered:
    """Verify all 15 tools register on FastMCP."""

    def test_new_mcp_tools_registered(self):
        from mcp.server.fastmcp import FastMCP
        from auction.mcp_tools import register_auction_tools

        mcp = FastMCP("test-auction")
        engine = _make_engine()
        stripe_svc = StripeService(api_key=None)
        wallet = _make_wallet()
        stripe_wallet = StripeWalletService(ledger=wallet, stripe_service=stripe_svc)

        register_auction_tools(
            mcp, engine,
            stripe_wallet_service=stripe_wallet,
            stripe_service=stripe_svc,
        )

        # Get registered tool names
        tools = mcp._tool_manager._tools
        tool_names = sorted(tools.keys())

        expected = sorted([
            "auction_post_task",
            "auction_get_bids",
            "auction_accept_bid",
            "auction_execute",
            "auction_confirm_delivery",
            "auction_reject_delivery",
            "auction_cancel_task",
            "auction_get_task_schema",
            "auction_get_status",
            # v1.0 new tools
            "auction_fund_wallet",
            "auction_get_wallet_balance",
            "auction_onboard_operator",
            "auction_get_operator_status",
            # Convenience tools (REC-16b, REC-19)
            "auction_accept_and_execute",
            "auction_quick_hire",
        ])

        assert tool_names == expected, f"Expected {expected}, got {tool_names}"
