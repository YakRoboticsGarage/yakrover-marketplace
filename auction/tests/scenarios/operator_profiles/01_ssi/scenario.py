"""Operator 01: Surveying Solutions Inc. (SSI) — Full-service PLS firm.

The most complete operator profile. Has all compliance documents including
PLS license, Part 107, and confined space certification. Expected to win
the most complex tasks in test scenarios.

Scenario flow:
    1. Upload all compliance documents (PLS, Part 107, COI, operator terms)
    2. System verifies all documents — all pass
    3. SSI receives available task notifications
    4. SSI bids on aerial topo task (GC 04 Task A or GC 05 Task 1)
    5. SSI bids on tunnel scanning task (GC 05 Task 2) — confined space OK
    6. Scoring: SSI ranks high on compliance completeness
    7. SSI wins task(s) — escrow funded by GC
    8. SSI uploads deliverables
    9. PLS (Jackie Davis) stamps deliverables
   10. Deliverables accepted — escrow released to SSI

Key assertions:
    - All 5 compliance docs upload and verify successfully
    - PLS license validates (MI #39847, not expired)
    - Part 107 validates (cert #4287651)
    - Insurance meets all GC minimums
    - Confined space cert allows tunnel task bidding
    - Bid scoring reflects full compliance bonus
"""

from pathlib import Path

SCENARIO_DIR = Path(__file__).parent

OPERATOR_PROFILE = {
    "id": "01_ssi",
    "name": "Surveying Solutions Inc.",
    "location": "Standish, MI",
    "contact": "Jackie Davis, VP/PLS",
    "has_pls": True,
    "has_part_107": True,
    "has_insurance": True,
    "has_confined_space": True,
    "operator_type": "full_service_pls",
}

COMPLIANCE_DOCS = {
    "pls_license": SCENARIO_DIR / "pls_license.txt",
    "faa_part_107": SCENARIO_DIR / "faa_part_107.txt",
    "insurance_coi": SCENARIO_DIR / "insurance_coi.txt",
    "operator_terms": SCENARIO_DIR / "operator_terms.txt",
}

EXPECTED_COMPLIANCE = {
    "pls_license": "VALID",
    "faa_part_107": "VALID",
    "insurance_coi": "VALID",
    "operator_terms": "ACCEPTED",
    "overall": "FULLY_COMPLIANT",
}

ELIGIBLE_TASK_TYPES = [
    "aerial_lidar_topo",
    "terrestrial_lidar_tunnel",
    "gpr_subsurface",
    "photogrammetry",
    "control_survey",
]


def load_compliance_docs() -> dict[str, str]:
    """Load all compliance document contents."""
    return {name: path.read_text() for name, path in COMPLIANCE_DOCS.items()}


def verify_compliance(result: dict) -> bool:
    """Verify all compliance checks pass."""
    for doc_type, expected_status in EXPECTED_COMPLIANCE.items():
        actual = result.get(doc_type)
        assert actual == expected_status, f"{doc_type}: expected {expected_status}, got {actual}"
    return True
