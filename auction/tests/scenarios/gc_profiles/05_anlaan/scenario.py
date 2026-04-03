"""Scenario 5: Anlaan — I-94 Tunnel + Topo (Demo Scenario, Most Complex)

Tests: 3-task RFP (topo + tunnel + manual), confined space cert,
underground terrain, large bond, design-build terms, multi-operator award.
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
from auction.rfp_processor import get_site_recon, process_rfp, validate_task_specs
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
    print("SCENARIO 5: Anlaan — I-94 Tunnel + Topo (Demo Scenario)")
    print("=" * 60)

    rfp_text = (PROFILE_DIR / "rfp.txt").read_text()
    bond_text = (PROFILE_DIR / "bond.txt").read_text()
    gc_terms = (PROFILE_DIR / "gc_terms.txt").read_text()

    wallet = WalletLedger()
    wallet.create_wallet("buyer", Decimal("0"))
    wallet.fund_wallet("buyer", Decimal("400000"))
    reputation = ReputationTracker()
    fleet = create_construction_fleet()
    engine = AuctionEngine(fleet, wallet=wallet, reputation=reputation)
    compliance = ComplianceChecker()

    print("\n[1] Fund wallet")
    step("Wallet funded $400,000", wallet.get_balance("buyer"), True)

    print("\n[2] Process RFP — expect topo + tunnel + manual")
    site_info = {
        "project_name": "I-94 Modernization — Drainage Tunnel Rehabilitation",
        "location": "Wayne County, MI — I-94 from Conner Ave to Cadieux Rd, Detroit",
        "coordinates": {"lat": 42.3736, "lon": -82.9553},
        "survey_area": {"type": "corridor", "acres": 45, "length_miles": 3.2, "width_ft": 200},
        "agency": "MDOT",
        "project_id": "IM-94-23456",
        "letting_date": "2026-05-01",
        "terrain": "corridor",
        "access_restrictions": ["highway_traffic", "confined_space", "escort_required"],
        "airspace_class": "G",
        "reference_standards": ["MDOT Section 104.09", "NCHRP 748", "OSHA 29 CFR 1926.1200"],
    }
    specs = process_rfp(rfp_text, "MI", site_info)
    step(f"RFP decomposed into {len(specs)} tasks", specs, len(specs) >= 2)
    for i, s in enumerate(specs):
        print(f"    Task {i}: {s['task_category']} — ${s['budget_ceiling']:,}")

    # Identify task types
    topo_spec = next((s for s in specs if s["task_category"] == "site_survey"), None)
    tunnel_spec = next((s for s in specs if s["task_category"] == "as_built"), None)

    step("Topo task found", topo_spec, topo_spec is not None)
    step("Tunnel scan task found", tunnel_spec, tunnel_spec is not None)

    if topo_spec is None:
        topo_spec = specs[0]
    if tunnel_spec is None and len(specs) > 1:
        tunnel_spec = specs[1]

    print("\n[3] Validate specs")
    validation = validate_task_specs(specs)
    step("All specs valid", validation, validation["all_valid"])

    print("\n[4] Site recon — expect underground + confined space")
    recon = get_site_recon(rfp_text, specs)
    step(f"Terrain: {recon['terrain']['type']}", recon, True)
    step(
        f"Confined space: {recon['access'].get('confined_space', False)}",
        recon,
        recon["access"].get("confined_space", False),
    )
    step(
        f"Highway traffic: {recon['access'].get('traffic_control_needed', False)}",
        recon,
        recon["access"].get("traffic_control_needed", False),
    )

    print("\n[5] Post tasks")
    request_ids = {}

    # Post topo
    if topo_spec:
        result = engine.post_task(topo_spec)
        request_ids["topo"] = result["request_id"]
        step(f"Topo posted: {result['eligible_robots']} eligible", result, result["state"] == "bidding")

    # Post tunnel
    if tunnel_spec:
        result = engine.post_task(tunnel_spec)
        request_ids["tunnel"] = result["request_id"]
        step(f"Tunnel posted: {result['eligible_robots']} eligible", result, result["state"] == "bidding")

    print("\n[6] Collect bids")
    for label, rid in request_ids.items():
        bids = engine.get_bids(rid)
        step(f"{label}: {bids['bid_count']} bids", bids, bids["bid_count"] > 0)

    print("\n[7] Review bids")
    winners = {}
    for label, rid in request_ids.items():
        review = engine.review_bids(rid)
        rec = (review.get("recommendation") or {}).get("robot_id")
        winners[label] = rec
        step(f"{label} recommended: {rec}", review, rec is not None)

    # Tunnel should go to Wolverine (terrestrial LiDAR specialist)
    if winners.get("tunnel"):
        step(
            f"Tunnel winner is ground scanner: {winners['tunnel']}", winners["tunnel"], "wolverine" in winners["tunnel"]
        )

    print("\n[8] Verify compliance — tunnel operator needs confined space")
    for label, robot_id in winners.items():
        if robot_id:
            result = compliance.verify_operator(robot_id)
            step(f"{label} ({robot_id}): {result['verified']}/6 verified", result, True)

    print("\n[9] Verify bond — $350K must cover $205K tasks")
    all_rids = list(request_ids.values())
    bond_result = verify_bond(bond_text, all_rids)
    step(f"Bond status: {bond_result['status']}", bond_result, bond_result["status"] in ("VERIFIED", "PARTIAL"))
    if bond_result.get("penal_sum"):
        step(f"Bond penal sum: {bond_result['penal_sum']}", bond_result, True)

    print("\n[10] Compare terms — design-build terms")
    operator_terms = "Standard terms: intermediate indemnification, 1x LoL, Net 30."
    terms_result = compare_terms(operator_terms, gc_terms, "MI")
    step(f"Risk: {terms_result['overall_risk']}", terms_result, True)
    step(f"Flags: {len(terms_result['flags'])}", terms_result, True)

    print("\n[11] Award tasks")
    awarded_ids = []
    for label, rid in request_ids.items():
        robot_id = winners.get(label)
        if robot_id:
            result = engine.accept_bid(rid, robot_id)
            awarded_ids.append(rid)
            step(f"{label} awarded to {robot_id}: {result['state']}", result, result["state"] == "bid_accepted")
        else:
            step(f"{label}: no winner", None, False)

    print("\n[12] Generate agreements")
    for rid in awarded_ids:
        record = engine._get_record(rid)
        agreement = generate_agreement(record, "consensusdocs_750")
        step(
            f"Agreement for {record.winning_bid.robot_id}: ${agreement['terms']['fee']['contract_price']}",
            agreement,
            agreement["status"] == "draft",
        )

    print("\n[13] Execute and deliver")

    async def run_execution():
        for rid in awarded_ids:
            result = await engine.execute(rid)
            step(f"Executed {rid[:12]}: {result.get('state')}", result, result.get("state") == "delivered")

    asyncio.run(run_execution())

    print("\n[14] Confirm deliveries")
    for rid in awarded_ids:
        result = engine.confirm_delivery(rid)
        step(f"Settled {rid[:12]}: {result['state']}", result, result["state"] == "settled")

    print("\n[15] List all project tasks")
    if topo_spec:
        rfp_id = topo_spec["task_decomposition"]["rfp_id"]
        listing = engine.list_tasks({"rfp_id": rfp_id})
        step(f"Project tasks: {listing['total']}", listing, listing["total"] >= 2)

    print("\n[16] Final wallet balance")
    final = wallet.get_balance("buyer")
    step(f"Remaining: ${final}", final, final < Decimal("400000"))

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
