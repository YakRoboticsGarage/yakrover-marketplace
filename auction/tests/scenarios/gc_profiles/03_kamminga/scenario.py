"""Scenario 3: Kamminga & Roodvoets — Progress Monitoring RFP (Budget Tier)

Tests: Small budget task handling, budget operator matching,
recurring monthly agreement generation.
"""

import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from auction.agreement import generate_agreement
from auction.engine import AuctionEngine
from auction.mock_fleet import create_construction_fleet
from auction.reputation import ReputationTracker
from auction.rfp_processor import get_site_recon, process_rfp, validate_task_specs
from auction.terms_comparator import compare_terms
from auction.wallet import WalletLedger

PROFILE_DIR = Path(__file__).parent
PASS = "\u2713"
FAIL = "\u2717"
gaps = []


def step(name: str, result: dict | bool, check: bool = True):
    status = PASS if check else FAIL
    print(f"  {status} {name}")
    if not check:
        gaps.append(f"FAIL: {name} — {result}")
    return result


def main():
    print("\n" + "=" * 60)
    print("SCENARIO 3: Kamminga & Roodvoets — Progress Monitoring (Budget)")
    print("=" * 60)

    # Load documents
    rfp_text = (PROFILE_DIR / "rfp.txt").read_text()
    gc_terms = (PROFILE_DIR / "gc_terms.txt").read_text()

    # Setup — smaller budget for progress monitoring
    wallet = WalletLedger()
    wallet.create_wallet("buyer", Decimal("0"))
    wallet.fund_wallet("buyer", Decimal("80000"), note="K&R prepaid credits — 14-month program")
    reputation = ReputationTracker()
    fleet = create_construction_fleet()
    engine = AuctionEngine(fleet, wallet=wallet, reputation=reputation)

    print("\n[1] Fund wallet")
    balance = wallet.get_balance("buyer")
    step("Wallet funded $80,000", balance, balance == Decimal("80000"))

    print("\n[2] Process RFP")
    site_info = {
        "project_name": "Stadium Blvd Reconstruction Phase 2 — Progress Monitoring",
        "location": "Ann Arbor, MI — Stadium Blvd, S. Main to S. State",
        "coordinates": {"lat": 42.2650, "lon": -83.7430},
        "survey_area": {"type": "corridor", "acres": 18, "length_miles": 1.2, "width_ft": 120},
        "agency": "City of Ann Arbor",
        "project_id": "AA-PW-2026-018",
        "letting_date": "2026-04-01",
        "terrain": "urban_corridor",
        "access_restrictions": ["city_traffic"],
        "airspace_class": "G",
        "reference_standards": ["FAA Part 107"],
        "recurring": {"visits": 14, "interval": "monthly", "period": "April 2026 — May 2027"},
    }
    specs = process_rfp(rfp_text, "MI", site_info)
    step(f"RFP decomposed into {len(specs)} task(s)", specs, len(specs) >= 1)
    for i, s in enumerate(specs):
        print(f"    Task {i}: {s['task_category']} — ${s['budget_ceiling']:,}")

    print("\n[3] Validate task specs")
    validation = validate_task_specs(specs)
    step("All specs valid", validation, validation["all_valid"])

    print("\n[4] Site reconnaissance")
    recon = get_site_recon(rfp_text, specs)
    step(f"Terrain: {recon['terrain']['type']}", recon, True)
    step(f"Airspace: {recon['airspace']['class']}", recon, recon["airspace"]["class"] == "G")

    print("\n[5] Post task (single progress monitoring task)")
    spec = specs[0]
    result = engine.post_task(spec)
    request_id = result["request_id"]
    step(
        f"Task posted: {result['state']} ({result['eligible_robots']} eligible)",
        result,
        result["state"] == "bidding" and result["eligible_robots"] > 0,
    )

    print("\n[6] Collect bids — expect budget-tier operators")
    bids = engine.get_bids(request_id)
    step(f"{bids['bid_count']} bids received", bids, bids["bid_count"] > 0)

    # Check that at least one bid is in the budget range
    bid_prices = [float(b.get("price", 0)) for b in bids.get("bids", [])]
    budget_bids = [p for p in bid_prices if 1000 <= p <= 6000]
    step(f"Budget-range bids ($1K-$6K): {len(budget_bids)}", bid_prices, len(budget_bids) > 0)

    print("\n[7] Review bids")
    review = engine.review_bids(request_id)
    rec = review.get("recommendation", {})
    robot_id = rec.get("robot_id", "none")
    rec_price = rec.get("price", rec.get("amount", "unknown"))
    step(f"Recommended: {robot_id} at ${rec_price}", review, rec is not None and rec.get("robot_id") is not None)

    print("\n[8] Compare terms — expect low/no risk (standard terms)")
    operator_terms = (
        "Standard operator terms: limitation of liability at 1x contract value, "
        "intermediate form indemnification, mutual waiver of consequential damages, "
        "Net 30 payment, operator retains methodology."
    )
    terms_result = compare_terms(operator_terms, gc_terms, "MI")
    step(f"Risk level: {terms_result['overall_risk']}", terms_result, terms_result["overall_risk"] in ("low", "medium"))
    step(f"Flags: {len(terms_result['flags'])}", terms_result, True)

    print("\n[9] Award task")
    result = engine.accept_bid(request_id, robot_id)
    step(f"Awarded to {robot_id}: {result['state']}", result, result["state"] == "bid_accepted")

    print("\n[10] Generate agreement — monthly recurring")
    record = engine._get_record(request_id)
    agreement = generate_agreement(record, "consensusdocs_750")
    step(f"Agreement status: {agreement['status']}", agreement, agreement["status"] == "draft")
    step(f"Fee: ${agreement['terms']['fee']['contract_price']}", agreement, True)

    # Verify recurring structure if present
    terms = agreement.get("terms", {})
    has_recurring = (
        terms.get("recurring") is not None
        or terms.get("schedule", {}).get("visits") is not None
        or "monthly" in str(terms).lower()
    )
    step("Agreement includes recurring/schedule terms", terms, has_recurring)

    print("\n[11] Final wallet balance")
    final_balance = wallet.get_balance("buyer")
    step(f"Remaining balance: ${final_balance}", final_balance, True)

    # Gap report
    print("\n" + "=" * 60)
    if gaps:
        print(f"GAPS FOUND: {len(gaps)}")
        for g in gaps:
            print(f"  {g}")
    else:
        print("ALL STEPS PASSED — No gaps found")
    print("=" * 60)
    return len(gaps)


if __name__ == "__main__":
    sys.exit(main())
