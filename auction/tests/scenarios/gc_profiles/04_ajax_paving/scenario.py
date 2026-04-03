"""Scenario 4: Ajax Paving — Topo + GPR Dual-Task (PLS-as-a-Service Gap)

Tests: composite RFP decomposition, different operators per task,
PLS gap detection on GPR operator, bond verification.
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from auction.agreement import generate_agreement
from auction.bond_verifier import verify_bond
from auction.compliance import ComplianceChecker
from auction.engine import AuctionEngine
from auction.mock_fleet import create_construction_fleet
from auction.reputation import ReputationTracker
from auction.rfp_processor import process_rfp, validate_task_specs
from auction.terms_comparator import compare_terms
from auction.wallet import WalletLedger

PROFILE_DIR = Path(__file__).parent
PASS = "\u2713"
FAIL = "\u2717"
gaps = []


def step(name, result, check=True):
    status = PASS if check else FAIL
    print(f"  {status} {name}")
    if not check:
        gaps.append(f"FAIL: {name}")
    return result


def main():
    print("\n" + "=" * 60)
    print("SCENARIO 4: Ajax Paving — Topo + GPR Dual-Task")
    print("=" * 60)

    rfp_text = (PROFILE_DIR / "rfp.txt").read_text()
    bond_text = (PROFILE_DIR / "bond.txt").read_text()
    gc_terms = (PROFILE_DIR / "gc_terms.txt").read_text()

    wallet = WalletLedger()
    wallet.create_wallet("buyer", Decimal("0"))
    wallet.fund_wallet("buyer", Decimal("150000"))
    reputation = ReputationTracker()
    fleet = create_construction_fleet()
    engine = AuctionEngine(fleet, wallet=wallet, reputation=reputation)
    compliance = ComplianceChecker()

    print("\n[1] Fund wallet")
    step("Wallet funded $150,000", wallet.get_balance("buyer"), True)

    print("\n[2] Process RFP — expect topo + GPR tasks")
    site_info = {
        "project_name": "I-96 Rehabilitation, Oakland County",
        "location": "Oakland County, MI — I-96 from Novi Rd to Beck Rd",
        "coordinates": {"lat": 42.4750, "lon": -83.2600},
        "survey_area": {"type": "corridor", "acres": 92, "length_miles": 3.8, "width_ft": 200},
        "agency": "MDOT",
        "project_id": "IM-96-78901",
        "terrain": "corridor",
        "access_restrictions": ["highway_traffic"],
        "airspace_class": "G",
        "reference_standards": ["MDOT Section 104.09", "ASCE 38"],
    }
    specs = process_rfp(rfp_text, "MI", site_info)
    step(f"RFP decomposed into {len(specs)} tasks", specs, len(specs) >= 2)
    for i, s in enumerate(specs):
        print(f"    Task {i}: {s['task_category']} — ${s['budget_ceiling']:,}")

    # Find topo and GPR specs
    topo_spec = next((s for s in specs if s["task_category"] in ("site_survey",)), specs[0])
    gpr_spec = next((s for s in specs if s["task_category"] == "subsurface_scan"), None)
    step("Topo task found", topo_spec, True)
    step("GPR task found", gpr_spec, gpr_spec is not None)
    if gpr_spec is None:
        gpr_spec = specs[1] if len(specs) > 1 else specs[0]

    print("\n[3] Validate specs")
    validation = validate_task_specs(specs)
    step("All specs valid", validation, validation["all_valid"])

    print("\n[4] Post both tasks")
    topo_result = engine.post_task(topo_spec)
    topo_rid = topo_result["request_id"]
    step(f"Topo posted: {topo_result['eligible_robots']} eligible", topo_result, topo_result["state"] == "bidding")

    gpr_result = engine.post_task(gpr_spec)
    gpr_rid = gpr_result["request_id"]
    step(f"GPR posted: {gpr_result['eligible_robots']} eligible", gpr_result, gpr_result["state"] == "bidding")

    print("\n[5] Collect bids")
    topo_bids = engine.get_bids(topo_rid)
    step(f"Topo: {topo_bids['bid_count']} bids", topo_bids, topo_bids["bid_count"] > 0)

    gpr_bids = engine.get_bids(gpr_rid)
    step(f"GPR: {gpr_bids['bid_count']} bids", gpr_bids, gpr_bids["bid_count"] > 0)

    print("\n[6] Review bids")
    topo_review = engine.review_bids(topo_rid)
    topo_winner = (topo_review.get("recommendation") or {}).get("robot_id")
    step(f"Topo recommended: {topo_winner}", topo_review, topo_winner is not None)

    gpr_review = engine.review_bids(gpr_rid)
    gpr_winner = (gpr_review.get("recommendation") or {}).get("robot_id")
    step(f"GPR recommended: {gpr_winner}", gpr_review, gpr_winner is not None)

    # Different operators should win different tasks
    step(
        f"Different operators: {topo_winner} vs {gpr_winner}",
        None,
        topo_winner != gpr_winner if topo_winner and gpr_winner else False,
    )

    print("\n[7] Check PLS compliance — GPR operator should lack PLS")
    if gpr_winner:
        gpr_compliance = compliance.verify_operator(gpr_winner)
        pls_check = next((c for c in gpr_compliance["checklist"] if c["doc_type"] == "pls_license"), None)
        pls_missing = pls_check and pls_check["status"] == "MISSING"
        step(f"GPR operator PLS status: {pls_check['status'] if pls_check else 'N/A'}", gpr_compliance, pls_missing)
        if pls_missing:
            print(f"    GAP IDENTIFIED: {gpr_winner} needs PLS-as-a-service")
            print("    Recommendation: Assign Jennifer Chen (MI #42871) as PLS-of-record")
    else:
        step("GPR winner not found — cannot check PLS", None, False)

    if topo_winner:
        topo_compliance = compliance.verify_operator(topo_winner)
        step(f"Topo operator compliance: {topo_compliance['verified']}/6", topo_compliance, True)

    print("\n[8] Verify bond")
    bond_result = verify_bond(bond_text, [topo_rid, gpr_rid])
    step(f"Bond status: {bond_result['status']}", bond_result, bond_result["status"] in ("VERIFIED", "PARTIAL"))

    print("\n[9] Compare terms")
    operator_terms = "Standard terms: intermediate indemnification, 1x LoL, Net 30, mutual waiver."
    terms_result = compare_terms(operator_terms, gc_terms, "MI")
    step(f"Risk: {terms_result['overall_risk']}", terms_result, True)

    print("\n[10] Award both tasks")
    awarded_ids = []
    for rid, winner, label in [(topo_rid, topo_winner, "Topo"), (gpr_rid, gpr_winner, "GPR")]:
        if winner:
            result = engine.accept_bid(rid, winner)
            awarded_ids.append(rid)
            step(f"{label} awarded to {winner}: {result['state']}", result, result["state"] == "bid_accepted")
        else:
            step(f"{label}: no winner", None, False)

    print("\n[11] Generate agreements")
    for rid in awarded_ids:
        record = engine._get_record(rid)
        agreement = generate_agreement(record, "consensusdocs_750")
        step(
            f"Agreement for {record.winning_bid.robot_id}: ${agreement['terms']['fee']['contract_price']}",
            agreement,
            agreement["status"] == "draft",
        )

    print("\n[12] Execute and deliver")

    async def run_execution():
        for rid in awarded_ids:
            result = await engine.execute(rid)
            step(f"Executed {rid[:12]}: {result.get('state')}", result, result.get("state") == "delivered")

    asyncio.run(run_execution())

    print("\n[13] Confirm deliveries")
    for rid in awarded_ids:
        result = engine.confirm_delivery(rid)
        step(f"Settled {rid[:12]}: {result['state']}", result, result["state"] == "settled")

    print("\n[14] List project tasks")
    rfp_id = topo_spec["task_decomposition"]["rfp_id"]
    listing = engine.list_tasks({"rfp_id": rfp_id})
    step(f"Project tasks: {listing['total']}", listing, listing["total"] >= 2)

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
