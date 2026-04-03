"""Operator 03: Emmet Drones — Solo operator, NO PLS.

Key test case for PLS-as-a-service flow. Kurtis Damerow is a competent
drone pilot but has no Professional Land Surveyor license. When he bids
on survey tasks that require PLS stamp, the system must detect the gap
and recommend a PLS-as-a-service provider.

Scenario flow:
    1. Upload Part 107 and insurance COI (no PLS to upload)
    2. System verifies documents:
       - Part 107: VALID
       - Insurance: VALID (but flags E&O as MISSING)
       - PLS: MISSING
    3. Kurtis bids on progress monitoring task (may not require PLS)
    4. Kurtis bids on GC 04 Task B (GPR utility detection)
    5. System flags: PLS MISSING for Task B deliverables
    6. PLS-as-a-service recommendation: Jennifer Chen (PLS 01)
    7. If Kurtis accepts PLS-as-a-service, bid proceeds with PLS cost added

Key assertions:
    - PLS shows MISSING in compliance check
    - E&O shows MISSING in insurance verification
    - Can still bid on tasks that don't require PLS stamp
    - PLS-as-a-service gap correctly identified
    - PLS-as-a-service cost factored into bid economics
    - Aviation insurance ($1M) flagged if GC requires higher ($5M)
"""

from pathlib import Path

SCENARIO_DIR = Path(__file__).parent

OPERATOR_PROFILE = {
    "id": "03_emmet_drones",
    "name": "Emmet Drones",
    "location": "Petoskey, MI",
    "contact": "Kurtis Damerow, Owner/Pilot",
    "has_pls": False,
    "has_part_107": True,
    "has_insurance": True,  # Partial — no E&O
    "has_confined_space": False,
    "operator_type": "solo_drone_no_pls",
}

COMPLIANCE_DOCS = {
    "faa_part_107": SCENARIO_DIR / "faa_part_107.txt",
    "insurance_coi": SCENARIO_DIR / "insurance_coi.txt",
    # No pls_license.txt — this is the point
}

EXPECTED_COMPLIANCE = {
    "pls_license": "MISSING",
    "faa_part_107": "VALID",
    "insurance_coi": "VALID",
    "insurance_eo": "MISSING",
    "overall": "PARTIAL — PLS REQUIRED",
}

PLS_SERVICE_NEEDED = True
RECOMMENDED_PLS = "01_jennifer_chen"

ELIGIBLE_TASK_TYPES = [
    "progress_monitoring",  # May not require PLS
    "photogrammetry",  # Depends on deliverable requirements
]

INELIGIBLE_WITHOUT_PLS = [
    "aerial_lidar_topo",  # Requires PLS stamp
    "control_survey",  # Requires PLS stamp
    "terrestrial_lidar_tunnel",  # Requires PLS stamp
]
