"""Scenario 1: Dan's Excavating — Multi-Task Highway RFP (Happy Path)

Tests the full agent workflow: RFP → decompose → bid → review → bond →
award → agreement → execute → deliver → settle.
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from auction.agreement import generate_agreement
from auction.bond_verifier import verify_bond
from auction.compliance import ComplianceChecker
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
    print("SCENARIO 1: Dan's Excavating — Multi-Task Highway RFP")
    print("=" * 60)

    # Load documents
    rfp_text = (PROFILE_DIR / "rfp.txt").read_text()
    bond_text = (PROFILE_DIR / "bond.txt").read_text()
    gc_terms = (PROFILE_DIR / "gc_terms.txt").read_text()

    # Setup
    wallet = WalletLedger()
    wallet.create_wallet("buyer", Decimal("0"))
    wallet.fund_wallet("buyer", Decimal("200000"), note="Dan's Excavating prepaid credits")
    reputation = ReputationTracker()
    fleet = create_construction_fleet()
    engine = AuctionEngine(fleet, wallet=wallet, reputation=reputation)
    compliance = ComplianceChecker()

    print("\n[1] Fund wallet")
    balance = wallet.get_balance("buyer")
    step("Wallet funded $200,000", balance, balance == Decimal("200000"))

    print("\n[2] Process RFP")
    site_info = {
        "project_name": "US-131 Resurfacing, Kalamazoo County",
        "location": "Kalamazoo County, MI — US-131 from MM 36.2 to 42.8",
        "coordinates": {"lat": 42.2917, "lon": -85.5872},
        "survey_area": {"type": "corridor", "acres": 160, "length_miles": 6.6, "width_ft": 200},
        "agency": "MDOT",
        "project_id": "CS-39042",
        "letting_date": "2026-06-15",
        "terrain": "corridor",
        "access_restrictions": ["highway_traffic"],
        "airspace_class": "G",
        "reference_standards": ["MDOT Section 104.09", "NCHRP 748"],
    }
    specs = process_rfp(rfp_text, "MI", site_info)
    step(f"RFP decomposed into {len(specs)} tasks", specs, len(specs) >= 2)
    for i, s in enumerate(specs):
        print(f"    Task {i}: {s['task_category']} — ${s['budget_ceiling']:,}")

    print("\n[3] Validate task specs")
    validation = validate_task_specs(specs)
    step("All specs valid", validation, validation["all_valid"])

    print("\n[4] Site reconnaissance")
    recon = get_site_recon(rfp_text, specs)
    step(f"Terrain: {recon['terrain']['type']}", recon, recon["terrain"]["type"] == "corridor")
    step(f"Airspace: {recon['airspace']['class']}", recon, True)

    print("\n[5] Post tasks")
    request_ids = []
    for i, spec in enumerate(specs):
        try:
            result = engine.post_task(spec)
            request_ids.append(result["request_id"])
            step(
                f"Task {i} posted: {result['state']} ({result['eligible_robots']} eligible)",
                result,
                result["state"] == "bidding" and result["eligible_robots"] > 0,
            )
        except Exception as e:
            step(f"Task {i} FAILED to post", str(e), False)

    print("\n[6] Collect bids")
    for i, rid in enumerate(request_ids):
        bids = engine.get_bids(rid)
        step(f"Task {i}: {bids['bid_count']} bids received", bids, bids["bid_count"] > 0)

    print("\n[7] Review bids")
    for i, rid in enumerate(request_ids):
        review = engine.review_bids(rid)
        rec = review.get("recommendation", {})
        step(
            f"Task {i}: recommended {rec.get('robot_id', 'none')}",
            review,
            rec is not None and rec.get("robot_id") is not None,
        )

    print("\n[8] Verify operator compliance")
    for i, rid in enumerate(request_ids):
        review = engine.review_bids(rid)
        rec = review.get("recommendation") or {}
        robot_id = rec.get("robot_id")
        if robot_id:
            result = compliance.verify_operator(robot_id)
            step(f"Operator {robot_id}: {result['verified']}/{result['total_checks']} verified", result, True)
        else:
            step(f"Task {i}: no eligible bids (all over budget)", review, False)

    print("\n[9] Verify payment bond")
    bond_result = verify_bond(bond_text, request_ids)
    step(f"Bond status: {bond_result['status']}", bond_result, bond_result["status"] in ("VERIFIED", "PARTIAL"))
    step(f"Bond surety: {bond_result.get('surety', 'unknown')}", bond_result, True)

    print("\n[10] Compare terms")
    # Use SSI operator terms as a stand-in
    operator_terms = "Standard operator terms with limitation of liability at 1x contract value and mutual waiver of consequential damages."
    terms_result = compare_terms(operator_terms, gc_terms, "MI")
    step(f"Risk level: {terms_result['overall_risk']}", terms_result, True)
    step(f"Flags: {len(terms_result['flags'])}", terms_result, True)

    print("\n[11] Award tasks")
    awarded_ids = []
    for i, rid in enumerate(request_ids):
        review = engine.review_bids(rid)
        rec = review.get("recommendation") or {}
        robot_id = rec.get("robot_id")
        if robot_id:
            result = engine.accept_bid(rid, robot_id)
            awarded_ids.append(rid)
            step(f"Task {i} awarded to {robot_id}: {result['state']}", result, result["state"] == "bid_accepted")
        else:
            step(f"Task {i}: cannot award — no eligible bids", review, False)

    print("\n[12] Generate agreements")
    for rid in awarded_ids:
        record = engine._get_record(rid)
        agreement = generate_agreement(record, "consensusdocs_750")
        step(
            f"Agreement for {record.winning_bid.robot_id}: {agreement['status']}",
            agreement,
            agreement["status"] == "draft",
        )
        step(f"  Fee: ${agreement['terms']['fee']['contract_price']}", agreement, True)

    print("\n[13] Execute tasks")

    async def run_execution():
        for rid in awarded_ids:
            result = await engine.execute(rid)
            step(f"Execution {rid[:12]}: {result.get('state', 'unknown')}", result, result.get("state") == "delivered")

    asyncio.run(run_execution())

    print("\n[14] Confirm deliveries")
    for rid in awarded_ids:
        result = engine.confirm_delivery(rid)
        step(f"Settled {rid[:12]}: {result['state']}", result, result["state"] == "settled")

    print("\n[15] List project tasks")
    rfp_id = specs[0]["task_decomposition"]["rfp_id"]
    listing = engine.list_tasks({"rfp_id": rfp_id})
    step(
        f"Project tasks: {listing['total']} (posted {len(request_ids)}, awarded {len(awarded_ids)})",
        listing,
        listing["total"] == len(request_ids),
    )

    print("\n[16] Final wallet balance")
    final_balance = wallet.get_balance("buyer")
    step(f"Remaining balance: ${final_balance}", final_balance, final_balance < Decimal("200000"))

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
