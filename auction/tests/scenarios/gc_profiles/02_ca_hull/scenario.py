"""Scenario 2: C.A. Hull — Bridge Inspection RFP (Compliance-Heavy)

Tests: RFP → decompose → compliance upload → verify operator →
post task → bid → review → terms comparison (expect flags) →
award → agreement.
"""

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
    print("SCENARIO 2: C.A. Hull — Bridge Inspection (Compliance-Heavy)")
    print("=" * 60)

    # Load documents
    rfp_text = (PROFILE_DIR / "rfp.txt").read_text()
    bond_text = (PROFILE_DIR / "bond.txt").read_text()
    gc_terms = (PROFILE_DIR / "gc_terms.txt").read_text()

    # Setup
    wallet = WalletLedger()
    wallet.create_wallet("buyer", Decimal("0"))
    wallet.fund_wallet("buyer", Decimal("400000"), note="C.A. Hull prepaid credits")
    reputation = ReputationTracker()
    fleet = create_construction_fleet()
    engine = AuctionEngine(fleet, wallet=wallet, reputation=reputation)
    compliance = ComplianceChecker()

    print("\n[1] Fund wallet")
    balance = wallet.get_balance("buyer")
    step("Wallet funded $400,000", balance, balance == Decimal("400000"))

    print("\n[2] Process RFP")
    site_info = {
        "project_name": "Biennial Bridge Inspection Program 2026-2027",
        "location": "Wayne County, MI — 47 bridge structures",
        "coordinates": {"lat": 42.3314, "lon": -83.0458},
        "survey_area": {"type": "structures", "count": 47, "scan_count": 8},
        "agency": "Wayne County Road Commission",
        "project_id": "WC-BR-2026-041",
        "letting_date": "2026-04-01",
        "terrain": "urban_bridge",
        "access_restrictions": ["highway_traffic", "waterway", "dtw_airspace"],
        "airspace_class": "C",
        "reference_standards": ["23 CFR 650", "AASHTO Manual", "MDOT Bridge Inspection Standards"],
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
    step(f"Terrain: {recon['terrain']['type']}", recon, True)
    step(f"Airspace: {recon['airspace']['class']}", recon, True)
    step(
        "DTW restriction detected",
        recon,
        "dtw_airspace" in recon.get("access_restrictions", []) or recon["airspace"]["class"] in ("B", "C"),
    )

    print("\n[5] Upload compliance docs for operators")
    # Simulate uploading compliance docs for each operator in the fleet
    compliance_docs = {
        "faa_part_107": {
            "doc_type": "faa_part_107",
            "certificate_number": "FA4-107-2024-88321",
            "holder": "David Kroll",
            "expiration": "2027-03-15",
            "status": "current",
        },
        "insurance_coi": {
            "doc_type": "insurance_coi",
            "carrier": "Tokio Marine HCC",
            "policy_number": "AVN-2026-55219",
            "cgl_limit": 2_000_000,
            "eo_limit": 2_000_000,
            "aviation_limit": 10_000_000,
            "expiration": "2027-01-01",
            "status": "current",
        },
        "pls_license": {
            "doc_type": "pls_license",
            "state": "MI",
            "license_number": "PLS-MI-40012",
            "holder": "Sarah Ostrowski, PLS",
            "expiration": "2027-06-30",
            "status": "current",
        },
    }
    # Upload docs for Trident Inspection (likely bridge inspector)
    target_robot = "trident-inspection"
    for doc_name, doc in compliance_docs.items():
        import json

        record = compliance.upload_document(target_robot, doc["doc_type"], json.dumps(doc))
        step(f"Uploaded {doc_name} for {target_robot}: {record.status}", record, record.status == "VERIFIED")

    print("\n[6] Verify operator compliance")
    result = compliance.verify_operator(target_robot)
    step(
        f"Operator {target_robot}: {result['verified']}/{result['total_checks']} checks",
        result,
        result["verified"] >= 3,
    )

    print("\n[7] Post tasks")
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

    print("\n[8] Collect bids")
    for i, rid in enumerate(request_ids):
        bids = engine.get_bids(rid)
        step(f"Task {i}: {bids['bid_count']} bids received", bids, bids["bid_count"] > 0)

    print("\n[9] Review bids")
    for i, rid in enumerate(request_ids):
        review = engine.review_bids(rid)
        rec = review.get("recommendation", {})
        step(
            f"Task {i}: recommended {rec.get('robot_id', 'none')}",
            review,
            rec is not None and rec.get("robot_id") is not None,
        )

    print("\n[10] Compare terms — expect flags for broad-form indemnification")
    operator_terms = (
        "Standard operator terms: limitation of liability at 1x contract value, "
        "intermediate form indemnification for own negligence only, "
        "mutual waiver of consequential damages, Net 30 payment."
    )
    terms_result = compare_terms(operator_terms, gc_terms, "MI")
    step(
        f"Risk level: {terms_result['overall_risk']}", terms_result, terms_result["overall_risk"] in ("high", "medium")
    )
    step(f"Flags: {len(terms_result['flags'])}", terms_result, len(terms_result["flags"]) > 0)

    # Check for specific red flags (flags are strings like "INDEMNIFICATION: ...")
    flags_text = " ".join(terms_result["flags"]).lower()
    step("Broad-form indemnification flagged", terms_result["flags"], "indemnif" in flags_text)
    step(
        "Pay-when-paid or payment issue flagged", terms_result["flags"], "payment" in flags_text or "pay" in flags_text
    )

    print("\n[11] Verify payment bond")
    bond_result = verify_bond(bond_text, request_ids)
    step(f"Bond status: {bond_result['status']}", bond_result, bond_result["status"] in ("VERIFIED", "PARTIAL"))

    print("\n[12] Award tasks")
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
            step(f"Task {i}: no eligible bids", review, False)

    print("\n[13] Generate agreements")
    for rid in awarded_ids:
        record = engine._get_record(rid)
        agreement = generate_agreement(record, "consensusdocs_750")
        step(
            f"Agreement for {record.winning_bid.robot_id}: {agreement['status']}",
            agreement,
            agreement["status"] == "draft",
        )
        step(f"  Fee: ${agreement['terms']['fee']['contract_price']}", agreement, True)

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
