"""
End-to-end integration test with a real robot fleet.

This is the "smoke test that matters" — it verifies the entire pipeline:
agent posts task → robots bid → auction scores → robot executes → payment settles.

Run: uv run pytest auction/tests/integration/test_e2e_real_fleet.py -m fleet -v
Requires:
    FLEET_URL=http://localhost:8001 (or ngrok URL)
    MCP_BEARER_TOKEN=...
    STRIPE_SECRET_KEY=sk_test_...
    STRIPE_OPERATOR_ACCOUNT=acct_...
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.fleet
@pytest.mark.stripe
class TestEndToEndRealFleet:
    """Full lifecycle test against a running fleet with real robots."""

    @pytest.fixture
    def mcp_client(self, fleet_url: str, fleet_bearer_token: str) -> httpx.AsyncClient:
        """HTTP client configured for fleet MCP server."""
        return httpx.AsyncClient(
            base_url=fleet_url,
            headers={"Authorization": f"Bearer {fleet_bearer_token}"},
            timeout=60.0,
        )

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(
        self,
        mcp_client: httpx.AsyncClient,
        stripe_api_key: str,
        stripe_operator_account: str,
    ) -> None:
        """
        End-to-end: post task → collect bids → accept → execute → verify → settle.

        This test requires:
        - A running fleet server with at least 1 robot (fakerover is fine)
        - A funded Stripe test-mode buyer wallet
        - A Stripe Connect Express test operator account
        """
        # 1. Post task
        post_resp = await mcp_client.post(
            "/fleet/mcp",
            json={
                "method": "auction_post_task",
                "params": {
                    "description": "Integration test: temperature reading",
                    "capability_requirements": {
                        "hard": {"sensors_required": ["temperature", "humidity"]},
                        "soft": {},
                        "payload": {
                            "type": "sensor_reading",
                            "fields": ["temperature_celsius", "humidity_percent"],
                            "format": "json",
                        },
                    },
                    "budget_ceiling": "2.00",
                    "sla_seconds": 300,
                },
            },
        )
        assert post_resp.status_code == 200, f"Post task failed: {post_resp.text}"
        task = post_resp.json()
        request_id = task.get("result", {}).get("request_id") or task.get("request_id")
        assert request_id, f"No request_id in response: {task}"

        # 2. Collect bids (wait for robots to respond)
        import asyncio

        await asyncio.sleep(2)  # Give robots time to bid

        bids_resp = await mcp_client.post(
            "/fleet/mcp",
            json={
                "method": "auction_get_bids",
                "params": {"request_id": request_id},
            },
        )
        assert bids_resp.status_code == 200
        bids = bids_resp.json()
        bid_list = bids.get("result", {}).get("bids", []) or bids.get("bids", [])
        assert len(bid_list) >= 1, f"No bids received from fleet: {bids}"

        # 3. Accept best bid
        accept_resp = await mcp_client.post(
            "/fleet/mcp",
            json={
                "method": "auction_accept_bid",
                "params": {"request_id": request_id},
            },
        )
        assert accept_resp.status_code == 200

        # 4. Execute task (robot reads sensor)
        exec_resp = await mcp_client.post(
            "/fleet/mcp",
            json={
                "method": "auction_execute",
                "params": {"request_id": request_id},
            },
        )
        assert exec_resp.status_code == 200

        # 5. Confirm delivery
        confirm_resp = await mcp_client.post(
            "/fleet/mcp",
            json={
                "method": "auction_confirm_delivery",
                "params": {"request_id": request_id},
            },
        )
        assert confirm_resp.status_code == 200

        # 6. Verify final state
        status_resp = await mcp_client.post(
            "/fleet/mcp",
            json={
                "method": "auction_get_status",
                "params": {"request_id": request_id},
            },
        )
        assert status_resp.status_code == 200
        status = status_resp.json()
        final_state = status.get("result", {}).get("state") or status.get("state")
        assert final_state in ("settled", "verified"), f"Unexpected final state: {final_state}"

        await mcp_client.aclose()
