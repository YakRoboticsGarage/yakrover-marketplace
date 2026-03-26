"""Runnable demo script for the robot task auction v1.0.

Runs five scenarios sequentially:
  1. Happy Path — full lifecycle with wallet debits, reputation, and Stripe settlement
  2. No Capable Robots — all robots filtered, task withdrawn
  3. Cheapest Doesn't Win — scoring favors reliability over price
  4. Robot Timeout — TimeoutRobot times out, task re-pools to FakeRoverBay3
  5. Bad Payload — BadPayloadRobot delivers garbage, rejected, re-pools

v1.0 additions over v0.5:
  - SQLite persistence (in-memory for demo, or file path from AUCTION_DB_PATH)
  - Stripe settlement (stub mode if STRIPE_SECRET_KEY not set)
  - Wallet top-up via StripeWalletService
  - Shows Stripe transfer on settlement

Usage:
    python auction/demo.py
    uv run python auction/demo.py

    # With real Stripe test key:
    STRIPE_SECRET_KEY=sk_test_xxx python auction/demo.py
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal

from dotenv import load_dotenv
load_dotenv()

from auction.core import log
from auction.engine import AuctionEngine
from auction.mock_fleet import (
    BadPayloadRobot,
    FakeRoverBay3,
    TimeoutRobot,
    create_demo_fleet,
    create_scenario3_fleet,
)
from auction.reputation import ReputationTracker
from auction.store import SyncTaskStore
from auction.stripe_service import StripeService
from auction.wallet import StripeWalletService, WalletLedger


# ---------------------------------------------------------------------------
# Task specs reused across scenarios
# ---------------------------------------------------------------------------

TEMP_HUMIDITY_TASK = {
    "description": "Read temperature and humidity in warehouse Bay 3",
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
    "budget_ceiling": 2.00,
    "sla_seconds": 900,
}


def banner(title: str) -> None:
    """Print a scenario separator banner."""
    print()
    print("=" * 40)
    print(f"  {title}")
    print("=" * 40)
    print()


# ---------------------------------------------------------------------------
# Scenario 1: Happy Path
# ---------------------------------------------------------------------------

async def scenario_1(
    wallet: WalletLedger,
    reputation: ReputationTracker,
    store: SyncTaskStore,
    stripe_svc: StripeService,
    stripe_wallet: StripeWalletService,
) -> None:
    """Full auction lifecycle with real HTTP to fakerover simulator."""
    banner("SCENARIO 1: Happy Path")

    engine = AuctionEngine(
        create_demo_fleet(),
        wallet=wallet,
        reputation=reputation,
        store=store,
        stripe_service=stripe_svc,
    )

    # 0. Fund wallet via Stripe (stub or real)
    log("WALLET", "Funding wallet via Stripe...")
    topup_result = stripe_wallet.fund_wallet("buyer", Decimal("5.00"))
    log("WALLET", f"Top-up result: balance=${topup_result['balance']}, "
        f"stripe={'stub' if topup_result['payment_intent'].get('stub') else 'live'}")

    # 1. Post task
    post_result = engine.post_task(TEMP_HUMIDITY_TASK)
    request_id = post_result["request_id"]

    # 2. Get bids
    bid_result = engine.get_bids(request_id)
    recommended = bid_result["recommended_winner"]

    # 3. Accept the recommended bid
    accept_result = engine.accept_bid(request_id, recommended)

    # 4. Execute — real HTTP to simulator
    try:
        exec_result = await engine.execute(request_id)
    except Exception as exc:
        # Handle simulator not running
        print()
        log("ERROR", f"Execution failed: {exc}")
        log("HINT", "Is the fakerover simulator running? Start it with:")
        log("HINT", "  uv run python -m robots.fakerover.simulator")
        log("HINT", "Scenario 1 requires the simulator at localhost:8080.")
        return

    delivery = exec_result["delivery"]

    # 5. Confirm delivery (triggers Stripe transfer)
    confirm_result = engine.confirm_delivery(request_id)

    # 6. Final result
    log("RESULT", f"Task {request_id} completed successfully.")
    log("RESULT", f"  State: {confirm_result['state']}")
    log("RESULT", f"  Robot: {confirm_result['delivery']['robot_id']}")
    log("RESULT", f"  Temperature: {delivery['data']['temperature_celsius']}C")
    log("RESULT", f"  Humidity: {delivery['data']['humidity_percent']}%")
    log("RESULT", f"  SLA met: {delivery['sla_met']}")
    log("RESULT", f"  Settlement: {confirm_result['settlement']['status']}")
    if "stripe_transfer_id" in confirm_result.get("settlement", {}):
        log("STRIPE", f"  Transfer ID: {confirm_result['settlement']['stripe_transfer_id']}")
    log("RESULT", f"  Buyer wallet balance: ${wallet.get_balance('buyer')}")

    # Verify SQLite persistence
    stored = store.load_task(request_id)
    if stored:
        log("STORE", f"  Task persisted in SQLite: state={stored['state']}")


# ---------------------------------------------------------------------------
# Scenario 2: No Capable Robots
# ---------------------------------------------------------------------------

async def scenario_2(
    wallet: WalletLedger,
    reputation: ReputationTracker,
    store: SyncTaskStore,
    stripe_svc: StripeService,
) -> None:
    """Task requiring a welding sensor — no robots qualify."""
    banner("SCENARIO 2: No Capable Robots")

    engine = AuctionEngine(
        create_demo_fleet(),
        wallet=wallet,
        reputation=reputation,
        store=store,
        stripe_service=stripe_svc,
    )

    welding_task = {
        "description": "Weld joint B7 on assembly line 3",
        "task_category": "env_sensing",
        "capability_requirements": {
            "hard": {
                "sensors_required": ["welding"],
            },
            "payload": {
                "format": "json",
                "fields": ["weld_quality"],
            },
        },
        "budget_ceiling": 5.00,
        "sla_seconds": 600,
    }

    post_result = engine.post_task(welding_task)
    request_id = post_result["request_id"]

    log("RESULT", f"Task {request_id} state: {post_result['state']}")
    log("RESULT", f"No robots available with 'welding' capability.")


# ---------------------------------------------------------------------------
# Scenario 3: Cheapest Doesn't Win
# ---------------------------------------------------------------------------

async def scenario_3(
    wallet: WalletLedger,
    reputation: ReputationTracker,
    store: SyncTaskStore,
    stripe_svc: StripeService,
) -> None:
    """Demonstrate that scoring rewards reliability over price."""
    banner("SCENARIO 3: Cheapest Doesn't Win")

    engine = AuctionEngine(
        create_scenario3_fleet(),
        wallet=wallet,
        reputation=reputation,
        store=store,
        stripe_service=stripe_svc,
    )

    # Post the same temperature+humidity task
    post_result = engine.post_task(TEMP_HUMIDITY_TASK)
    request_id = post_result["request_id"]

    # Get bids — scoring math is logged by the engine
    bid_result = engine.get_bids(request_id)
    recommended = bid_result["recommended_winner"]

    # Show the key insight
    scores = bid_result["scores"]
    log("RESULT", f"Winner: {recommended} — reliability beats cheapness!")
    for robot_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        bid_info = next(b for b in bid_result["bids"] if b["robot_id"] == robot_id)
        log("RESULT", f"  {robot_id}: score={score:.4f}, price=${bid_info['price']}")

    # Accept the bid (but do NOT execute — scoring demo only)
    accept_result = engine.accept_bid(request_id, recommended)
    log("RESULT", f"Accepted {recommended} @ ${accept_result['agreed_price']} (scoring demo — no execution)")


# ---------------------------------------------------------------------------
# Scenario 4: Robot Timeout
# ---------------------------------------------------------------------------

async def scenario_4(
    wallet: WalletLedger,
    reputation: ReputationTracker,
    store: SyncTaskStore,
    stripe_svc: StripeService,
) -> None:
    """TimeoutRobot wins but times out. Task re-pools to FakeRoverBay3."""
    banner("SCENARIO 4: Robot Timeout")

    fleet = [TimeoutRobot(), FakeRoverBay3()]
    engine = AuctionEngine(
        fleet,
        wallet=wallet,
        reputation=reputation,
        store=store,
        stripe_service=stripe_svc,
    )

    # Use a short SLA so the timeout fires quickly
    timeout_task = {
        "description": "Read temperature and humidity in warehouse Bay 3",
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
        "budget_ceiling": 2.00,
        "sla_seconds": 2,  # Very short — forces TimeoutRobot to fail
    }

    # Round 1: Force-accept TimeoutRobot to demonstrate the timeout flow
    post_result = engine.post_task(timeout_task)
    request_id = post_result["request_id"]

    bid_result = engine.get_bids(request_id)
    log("RESULT", f"Accepting timeout-robot to demonstrate timeout flow")

    engine.accept_bid(request_id, "timeout-robot")

    # Execute — TimeoutRobot times out, engine auto-abandons and re-pools
    try:
        exec_result = await engine.execute(request_id)
    except Exception as exc:
        log("ERROR", f"Execution failed unexpectedly: {exc}")
        log("HINT", "Is the fakerover simulator running? Start it with:")
        log("HINT", "  uv run python -m robots.fakerover.simulator")
        return

    log("RESULT", f"Round 1 result: timeout={exec_result.get('timeout', False)}")
    log("RESULT", f"  State after timeout: {exec_result['state']}")
    log("RESULT", f"  Re-pool: {exec_result.get('re_pool', {})}")

    # Round 2: FakeRoverBay3 wins (TimeoutRobot excluded)
    bid_result_2 = engine.get_bids(request_id)
    recommended_2 = bid_result_2["recommended_winner"]
    log("RESULT", f"Round 2 winner: {recommended_2}")

    engine.accept_bid(request_id, recommended_2)

    try:
        exec_result_2 = await engine.execute(request_id)
    except Exception as exc:
        log("ERROR", f"Round 2 execution failed: {exc}")
        log("HINT", "Is the fakerover simulator running? Start it with:")
        log("HINT", "  uv run python -m robots.fakerover.simulator")
        return

    delivery = exec_result_2["delivery"]

    confirm_result = engine.confirm_delivery(request_id)

    log("RESULT", f"Task {request_id} completed after re-pool.")
    log("RESULT", f"  State: {confirm_result['state']}")
    log("RESULT", f"  Robot: {confirm_result['delivery']['robot_id']}")
    log("RESULT", f"  Temperature: {delivery['data']['temperature_celsius']}C")
    log("RESULT", f"  Humidity: {delivery['data']['humidity_percent']}%")
    log("RESULT", f"  Settlement: {confirm_result['settlement']['status']}")
    log("RESULT", f"  Buyer wallet balance: ${wallet.get_balance('buyer')}")


# ---------------------------------------------------------------------------
# Scenario 5: Bad Payload
# ---------------------------------------------------------------------------

async def scenario_5(
    wallet: WalletLedger,
    reputation: ReputationTracker,
    store: SyncTaskStore,
    stripe_svc: StripeService,
) -> None:
    """BadPayloadRobot delivers garbage. Rejected, re-pools to FakeRoverBay3."""
    banner("SCENARIO 5: Bad Payload")

    fleet = [BadPayloadRobot(), FakeRoverBay3()]
    engine = AuctionEngine(
        fleet,
        wallet=wallet,
        reputation=reputation,
        store=store,
        stripe_service=stripe_svc,
    )

    # Round 1: Force-accept BadPayloadRobot
    post_result = engine.post_task(TEMP_HUMIDITY_TASK)
    request_id = post_result["request_id"]

    bid_result = engine.get_bids(request_id)
    log("RESULT", f"Accepting badpayload-robot to demonstrate rejection flow")

    engine.accept_bid(request_id, "badpayload-robot")

    try:
        exec_result = await engine.execute(request_id)
    except Exception as exc:
        log("ERROR", f"Execution failed unexpectedly: {exc}")
        log("HINT", "Is the fakerover simulator running? Start it with:")
        log("HINT", "  uv run python -m robots.fakerover.simulator")
        return

    delivery = exec_result["delivery"]
    log("RESULT", f"Round 1 delivery: {delivery['data']}")

    # Try to confirm — verification should fail on bad data
    try:
        engine.confirm_delivery(request_id)
        log("RESULT", "Unexpected: confirm_delivery succeeded on bad data!")
    except ValueError as exc:
        log("RESULT", f"Verification failed (expected): {exc}")

    # Agent rejects the delivery — triggers re-pool
    reject_result = engine.reject_delivery(request_id, "temperature reading is NaN, humidity is negative")
    log("RESULT", f"Rejected: re_pooled={reject_result.get('re_pooled', False)}")

    # Round 2: FakeRoverBay3 wins (BadPayloadRobot excluded)
    bid_result_2 = engine.get_bids(request_id)
    recommended_2 = bid_result_2["recommended_winner"]
    log("RESULT", f"Round 2 winner: {recommended_2}")

    engine.accept_bid(request_id, recommended_2)

    try:
        exec_result_2 = await engine.execute(request_id)
    except Exception as exc:
        log("ERROR", f"Round 2 execution failed: {exc}")
        log("HINT", "Is the fakerover simulator running? Start it with:")
        log("HINT", "  uv run python -m robots.fakerover.simulator")
        return

    delivery_2 = exec_result_2["delivery"]

    confirm_result = engine.confirm_delivery(request_id)

    log("RESULT", f"Task {request_id} completed after re-pool.")
    log("RESULT", f"  State: {confirm_result['state']}")
    log("RESULT", f"  Robot: {confirm_result['delivery']['robot_id']}")
    log("RESULT", f"  Temperature: {delivery_2['data']['temperature_celsius']}C")
    log("RESULT", f"  Humidity: {delivery_2['data']['humidity_percent']}%")
    log("RESULT", f"  Settlement: {confirm_result['settlement']['status']}")
    log("RESULT", f"  Buyer wallet balance: ${wallet.get_balance('buyer')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run all five demo scenarios."""
    print()
    print("YakRover Auction Explorer — v1.0 Demo")
    print("=" * 40)

    # Check Stripe configuration
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    stripe_mode = "live (test)" if stripe_key else "stub"
    log("CONFIG", f"Stripe mode: {stripe_mode}")

    # SQLite store
    db_path = os.environ.get("AUCTION_DB_PATH", ":memory:")
    store = SyncTaskStore(db_path)
    store.initialize()
    log("CONFIG", f"SQLite store: {db_path}")

    # Stripe service (stub if no key)
    stripe_svc = StripeService(api_key=stripe_key)

    # Set up shared wallet and reputation tracker
    wallet = WalletLedger()
    wallet.create_wallet("buyer", Decimal("0"))
    wallet.fund_wallet("buyer", Decimal("10.00"), note="Initial demo funding")
    log("WALLET", f"Buyer wallet created and funded: ${wallet.get_balance('buyer')}")

    # StripeWalletService wraps wallet + stripe
    stripe_wallet = StripeWalletService(ledger=wallet, stripe_service=stripe_svc)

    reputation = ReputationTracker()

    await scenario_1(wallet, reputation, store, stripe_svc, stripe_wallet)
    await scenario_2(wallet, reputation, store, stripe_svc)
    await scenario_3(wallet, reputation, store, stripe_svc)
    await scenario_4(wallet, reputation, store, stripe_svc)
    await scenario_5(wallet, reputation, store, stripe_svc)

    # Final summary
    print()
    print("=" * 40)
    print("  Final Summary")
    print("=" * 40)
    print()

    log("CONFIG", f"Stripe mode: {stripe_mode}")
    log("CONFIG", f"SQLite store: {db_path}")
    log("WALLET", f"Final buyer balance: ${wallet.get_balance('buyer')}")

    all_reps = reputation.get_all_reputations()
    if all_reps:
        log("REPUTATION", "Robot reputation summary:")
        for robot_id, rep in all_reps.items():
            log("REPUTATION", f"  {robot_id}: "
                f"completed={rep['tasks_completed']}, "
                f"completion_rate={rep['completion_rate']:.2f}, "
                f"on_time_rate={rep['on_time_rate']:.2f}, "
                f"rejection_rate={rep['rejection_rate']:.2f}")
    else:
        log("REPUTATION", "No reputation data recorded.")

    # Show persisted tasks summary
    active = store.load_active_tasks()
    log("STORE", f"Active tasks in SQLite: {len(active)}")

    store.close()

    print()
    print("=" * 40)
    print("  v1.0 Demo complete.")
    print("=" * 40)
    print()


if __name__ == "__main__":
    asyncio.run(main())
