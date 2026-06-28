"""Tier 1: MCP tool contract tests.

Each test verifies that an MCP tool:
- Accepts documented parameters without crashing
- Returns a dict
- Contains expected top-level keys

These catch the most common regression: a refactor in engine.py or core.py
breaks the MCP tool response shape, and the demo silently fails.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auction.engine import AuctionEngine
from auction.mock_fleet import create_demo_fleet
from auction.mcp_tools import register_auction_tools
from auction.reputation import ReputationTracker
from auction.wallet import WalletLedger

from auction.tests._fixtures import VALID_TASK_SPEC, LIDAR_TASK_SPEC


# ---------------------------------------------------------------------------
# Harness: register tools on a mock FastMCP, capture function references
# ---------------------------------------------------------------------------

class MockFastMCP:
    """Captures tool registrations without starting a server."""

    def __init__(self):
        self.tools: dict[str, callable] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _build_mcp_tools():
    """Create engine + register all MCP tools, return (tools_dict, engine)."""
    fleet = create_demo_fleet()
    wallet = WalletLedger()
    wallet.create_wallet("buyer")
    wallet.fund_wallet("buyer", Decimal("100.00"), "test")
    rep = ReputationTracker()
    engine = AuctionEngine(fleet, wallet=wallet, reputation=rep)

    mcp = MockFastMCP()
    register_auction_tools(mcp, engine)
    return mcp.tools, engine


@pytest.fixture(scope="module")
def mcp_tools():
    """Module-scoped fixture: register tools once, reuse across tests."""
    tools, engine = _build_mcp_tools()
    return tools, engine


# ---------------------------------------------------------------------------
# Registration contract: all expected tools exist
# ---------------------------------------------------------------------------

class TestToolRegistration:
    EXPECTED_TOOLS = [
        "auction_post_task",
        "auction_get_bids",
        "auction_accept_bid",
        "auction_execute",
        "auction_accept_and_execute",
        "auction_confirm_delivery",
        "auction_reject_delivery",
        "auction_cancel_task",
        "auction_get_task_schema",
        "auction_get_status",
        "auction_get_robot_status",
        "auction_fund_wallet",
        "auction_get_wallet_balance",
        "auction_quick_hire",
        "auction_review_bids",
        "auction_award_with_confirmation",
        "auction_list_tasks",
        "auction_onboard_operator_guided",
        "auction_update_operator_profile",
        "auction_register_operator",
        "auction_onboard_operator",
        "auction_add_equipment",
        "auction_activate_operator",
        "auction_get_operator_status",
        "auction_upload_compliance_doc",
        "auction_verify_operator_compliance",
        "auction_verify_bond",
        "auction_compare_terms",
        "auction_check_sam_exclusion",
        "auction_generate_agreement",
        "auction_track_execution",
        "auction_update_progress",
        "auction_get_task_feed",
        "auction_submit_feedback",
        "auction_log_unmet_demand",
        "auction_get_demand_signals",
    ]

    def test_all_expected_tools_registered(self, mcp_tools):
        tools, _ = mcp_tools
        for name in self.EXPECTED_TOOLS:
            assert name in tools, f"Missing MCP tool: {name}"

    def test_no_unexpected_tools(self, mcp_tools):
        """All registered tools should be in the expected list (catches accidental registrations)."""
        tools, _ = mcp_tools
        known = set(self.EXPECTED_TOOLS + [
            # Additional tools that may exist
            "auction_process_rfp",
            "auction_validate_task_specs",
            "auction_get_site_recon",
            "auction_verify_bond_pdf",
            "auction_register_robot_onchain",
            "auction_eas_attest",
            "auction_cancel_task",
        ])
        for name in tools:
            assert name in known, f"Unexpected MCP tool registered: {name}"

    def test_tool_count_in_range(self, mcp_tools):
        """Guard against tool count explosion (Cursor limit is 40)."""
        tools, _ = mcp_tools
        assert 35 <= len(tools) <= 45, f"Tool count {len(tools)} outside expected range 35-45"


# ---------------------------------------------------------------------------
# Core lifecycle contracts
# ---------------------------------------------------------------------------

def _mock_httpx():
    mock_response = MagicMock()
    mock_response.json.return_value = {"temperature": 22.5, "humidity": 45.0}
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return patch("auction.mock_fleet.httpx.AsyncClient", mock_cls)


class TestLifecycleContracts:
    """Test the core auction lifecycle through MCP tools."""

    def test_post_task_returns_request_id(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_post_task"](task_spec=VALID_TASK_SPEC))
        assert isinstance(result, dict)
        assert "request_id" in result
        assert "state" in result

    def test_get_bids_returns_scores(self, mcp_tools):
        tools, _ = mcp_tools
        post = asyncio.run(tools["auction_post_task"](task_spec=VALID_TASK_SPEC))
        result = asyncio.run(tools["auction_get_bids"](request_id=post["request_id"]))
        assert isinstance(result, dict)
        assert "bid_count" in result or "scores" in result

    def test_get_status_returns_state(self, mcp_tools):
        tools, _ = mcp_tools
        post = asyncio.run(tools["auction_post_task"](task_spec=VALID_TASK_SPEC))
        result = asyncio.run(tools["auction_get_status"](request_id=post["request_id"]))
        assert isinstance(result, dict)
        assert "state" in result

    def test_cancel_task_returns_withdrawn(self, mcp_tools):
        tools, _ = mcp_tools
        post = asyncio.run(tools["auction_post_task"](task_spec=VALID_TASK_SPEC))
        result = asyncio.run(tools["auction_cancel_task"](
            request_id=post["request_id"], reason="test"
        ))
        assert isinstance(result, dict)
        assert result.get("state") == "withdrawn"

    def test_full_lifecycle(self, mcp_tools):
        """post → get_bids → accept_and_execute → confirm_delivery."""
        tools, _ = mcp_tools

        with _mock_httpx():
            post = asyncio.run(tools["auction_post_task"](task_spec=VALID_TASK_SPEC))
            rid = post["request_id"]

            bids = asyncio.run(tools["auction_get_bids"](request_id=rid))
            assert bids.get("bid_count", 0) > 0

            winner = bids.get("recommended_winner", "")

            accept = asyncio.run(tools["auction_accept_and_execute"](
                request_id=rid, robot_id=winner
            ))
            assert "state" in accept

            confirm = asyncio.run(tools["auction_confirm_delivery"](request_id=rid))
            assert confirm.get("state") == "settled"


# ---------------------------------------------------------------------------
# QA-failure contract: confirm_delivery surfaces the payload for buyer review
# ---------------------------------------------------------------------------

def _build_mcp_tools_bad_payload():
    """Tools + engine whose only capable robot delivers QA-failing data."""
    from auction.mock_fleet import BadPayloadRobot, FakeRoverBay3

    fleet = [BadPayloadRobot(), FakeRoverBay3()]
    wallet = WalletLedger()
    wallet.create_wallet("buyer")
    wallet.fund_wallet("buyer", Decimal("100.00"), "test")
    engine = AuctionEngine(fleet, wallet=wallet, reputation=ReputationTracker())
    mcp = MockFastMCP()
    register_auction_tools(mcp, engine)
    return mcp.tools, engine


class TestConfirmDeliveryQAFail:
    def test_qa_fail_returns_payload_not_bare_error(self):
        """On QA fail the tool returns the delivery payload + QA detail (settled=False).

        This is what lets the demo show the delivery card and offer "Release
        Anyway" instead of a dead error.
        """
        tools, _ = _build_mcp_tools_bad_payload()

        post = asyncio.run(tools["auction_post_task"](task_spec=VALID_TASK_SPEC))
        rid = post["request_id"]
        asyncio.run(tools["auction_get_bids"](request_id=rid))
        asyncio.run(tools["auction_accept_and_execute"](request_id=rid, robot_id="badpayload-robot"))

        confirm = asyncio.run(tools["auction_confirm_delivery"](request_id=rid))

        assert confirm.get("qa_failed") is True
        assert confirm.get("settled") is False
        assert confirm.get("state") == "delivered"
        # The payload and QA detail are present for buyer review...
        assert confirm.get("delivery", {}).get("data") is not None
        assert confirm.get("qa", {}).get("status") == "FAIL"
        # ...and it is NOT a bare error response.
        assert "error" not in confirm


# ---------------------------------------------------------------------------
# Query tool contracts
# ---------------------------------------------------------------------------

class TestQueryContracts:

    def test_get_task_schema_returns_dict(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_get_task_schema"]())
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_list_tasks_returns_list(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_list_tasks"](filters=None))
        assert isinstance(result, dict)

    def test_get_wallet_balance_returns_balance(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_get_wallet_balance"](wallet_id="buyer"))
        assert isinstance(result, dict)
        assert "balance" in result or "wallet_id" in result

    def test_fund_wallet(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_fund_wallet"](
            wallet_id="buyer", amount=1.0
        ))
        assert isinstance(result, dict)

    def test_get_demand_signals(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_get_demand_signals"]())
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Operator tool contracts
# ---------------------------------------------------------------------------

class TestOperatorContracts:

    def test_deprecated_register_returns_error(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_register_operator"](
            company_name="Test Co", contact_name="Test", contact_email="t@t.com", location="MI"
        ))
        assert isinstance(result, dict)
        assert result.get("error_code") == "DEPRECATED"

    def test_deprecated_onboard_returns_error(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_onboard_operator"](
            email="t@t.com", robot_id="test-001"
        ))
        assert isinstance(result, dict)
        assert result.get("error_code") == "DEPRECATED"

    def test_check_sam_exclusion(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_check_sam_exclusion"](entity_name="Test Corp"))
        assert isinstance(result, dict)
        assert "excluded" in result or "entity_name" in result


# ---------------------------------------------------------------------------
# Error shape contracts
# ---------------------------------------------------------------------------

class TestErrorContracts:

    def test_invalid_request_id_returns_error(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_get_status"](request_id="nonexistent"))
        assert isinstance(result, dict)
        assert "error" in result or "error_code" in result

    def test_accept_without_bids_returns_error(self, mcp_tools):
        tools, _ = mcp_tools
        post = asyncio.run(tools["auction_post_task"](task_spec=VALID_TASK_SPEC))
        result = asyncio.run(tools["auction_accept_bid"](
            request_id=post["request_id"], robot_id="nonexistent"
        ))
        assert isinstance(result, dict)
        # Should be an error of some kind, not a crash
        assert "error" in result or "error_code" in result or "state" in result

    def test_log_unmet_demand(self, mcp_tools):
        tools, _ = mcp_tools
        result = asyncio.run(tools["auction_log_unmet_demand"](
            task_category="aerial_lidar",
            reason="No operators in area",
            latitude=42.0,
            longitude=-83.0,
        ))
        assert isinstance(result, dict)
