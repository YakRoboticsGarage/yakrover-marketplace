"""Tests for construction task schema extensions (Phase 1) and RFP processing (Phase 2)."""

import pytest
from decimal import Decimal

from auction.core import (
    Task,
    VALID_TASK_CATEGORIES,
    validate_task_spec,
    infer_task_category,
    ComplianceRecord,
    Agreement,
)


class TestConstructionCategories:
    """Phase 1: Construction task categories."""

    def test_original_categories_preserved(self):
        for cat in ["env_sensing", "visual_inspection", "mapping", "delivery_ground", "aerial_survey"]:
            assert cat in VALID_TASK_CATEGORIES

    def test_construction_categories_added(self):
        for cat in ["site_survey", "bridge_inspection", "progress_monitoring", "as_built",
                     "subsurface_scan", "environmental_survey", "control_survey"]:
            assert cat in VALID_TASK_CATEGORIES

    def test_create_construction_task(self):
        task = Task(
            description="Pre-construction topographic survey",
            task_category="site_survey",
            capability_requirements={
                "hard": {"sensors_required": ["aerial_lidar", "rtk_gps"]},
                "payload": {"format": "multi_file", "fields": ["LandXML", "DXF"]},
            },
            budget_ceiling=Decimal("50000"),
            sla_seconds=14 * 86400,
        )
        assert task.task_category == "site_survey"
        assert task.budget_ceiling == Decimal("50000")

    def test_task_decomposition_field(self):
        task = Task(
            description="Survey task",
            task_category="site_survey",
            capability_requirements={"hard": {"sensors_required": ["aerial_lidar"]}},
            budget_ceiling=Decimal("10000"),
            sla_seconds=86400,
            task_decomposition={"rfp_id": "rfp_abc123", "task_index": 0, "total_tasks": 3},
        )
        assert task.task_decomposition["rfp_id"] == "rfp_abc123"
        assert task.task_decomposition["task_index"] == 0

    def test_project_metadata_field(self):
        task = Task(
            description="Survey task",
            task_category="site_survey",
            capability_requirements={"hard": {"sensors_required": ["aerial_lidar"]}},
            budget_ceiling=Decimal("10000"),
            sla_seconds=86400,
            project_metadata={"jurisdiction": "MI", "agency": "MDOT"},
        )
        assert task.project_metadata["jurisdiction"] == "MI"

    def test_infer_aerial_lidar(self):
        cat = infer_task_category({"hard": {"sensors_required": ["aerial_lidar"]}})
        assert cat == "site_survey"

    def test_infer_gpr(self):
        cat = infer_task_category({"hard": {"sensors_required": ["gpr"]}})
        assert cat == "subsurface_scan"

    def test_infer_terrestrial_lidar(self):
        cat = infer_task_category({"hard": {"sensors_required": ["terrestrial_lidar"]}})
        assert cat == "site_survey"

    def test_infer_total_station(self):
        cat = infer_task_category({"hard": {"sensors_required": ["robotic_total_station"]}})
        assert cat == "control_survey"

    def test_validate_construction_spec(self):
        spec = {
            "description": "Topo survey",
            "task_category": "site_survey",
            "capability_requirements": {
                "hard": {
                    "sensors_required": ["aerial_lidar"],
                    "accuracy_required": {"horizontal_cm": 2.0, "vertical_cm": 5.0},
                    "certifications_required": ["faa_part_107"],
                },
                "soft": {
                    "preferred_deliverables": ["LandXML", "DXF"],
                },
                "payload": {"format": "multi_file", "fields": ["LandXML"]},
            },
            "budget_ceiling": 50000,
            "sla_seconds": 86400 * 14,
        }
        errors = validate_task_spec(spec)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_validate_standards_aligned_spec(self):
        """Validate a full standards-aligned task spec with ASPRS, EPSG, deliverables, MRTA."""
        spec = {
            "description": "Topographic LiDAR survey — US-131 corridor",
            "task_category": "site_survey",
            "capability_requirements": {
                "hard": {
                    "sensors_required": ["aerial_lidar", "rtk_gps"],
                    "accuracy_required": {"vertical_ft": 0.05, "horizontal_ft": 0.05},
                    "accuracy_standard": "asprs_ed2",
                    "asprs_horizontal_class": "5cm",
                    "asprs_vertical_class": "5cm",
                    "usgs_quality_level": "QL1",
                    "crs_epsg": 2113,
                    "vertical_datum_epsg": 5703,
                    "certifications_required": ["faa_part_107", "licensed_surveyor"],
                    "area_acres": 96,
                    "terrain": "highway_corridor",
                    "standards_compliance": ["MDOT_104.09"],
                },
                "deliverables": [
                    {"format": "LAS", "version": "1.4", "point_record_format": 6,
                     "classification_standard": "asprs", "min_point_density_ppsm": 8},
                    {"format": "GeoTIFF", "type": "orthomosaic", "gsd_cm": 2.5},
                    {"format": "LandXML", "version": "1.2", "content": ["surface"]},
                    {"format": "DXF", "content": ["contours", "breaklines"]},
                ],
                "regulatory": {
                    "faa_remote_id_required": True,
                    "faa_part_107_required": True,
                    "airspace_class": "G",
                    "laanc_authorization": "not_required",
                    "state_pls_required": True,
                    "pls_jurisdiction": "MI",
                },
                "mrta_class": {
                    "robot_type": "ST",
                    "task_type": "SR",
                    "allocation": "IA",
                    "dependency": "ND",
                },
                "payload": {"format": "multi_file", "fields": ["point_cloud", "topo_surface"]},
            },
            "budget_ceiling": 45000,
            "sla_seconds": 86400 * 14,
        }
        errors = validate_task_spec(spec)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_validate_invalid_asprs_class(self):
        spec = {
            "description": "Test",
            "task_category": "site_survey",
            "capability_requirements": {
                "hard": {"asprs_horizontal_class": "99cm"},
            },
            "budget_ceiling": 1000,
            "sla_seconds": 3600,
        }
        errors = validate_task_spec(spec)
        assert any("asprs_horizontal_class" in e for e in errors)

    def test_validate_invalid_usgs_ql(self):
        spec = {
            "description": "Test",
            "task_category": "site_survey",
            "capability_requirements": {
                "hard": {"usgs_quality_level": "QL9"},
            },
            "budget_ceiling": 1000,
            "sla_seconds": 3600,
        }
        errors = validate_task_spec(spec)
        assert any("usgs_quality_level" in e for e in errors)

    def test_validate_invalid_epsg(self):
        spec = {
            "description": "Test",
            "task_category": "site_survey",
            "capability_requirements": {
                "hard": {"crs_epsg": "not_a_number"},
            },
            "budget_ceiling": 1000,
            "sla_seconds": 3600,
        }
        errors = validate_task_spec(spec)
        assert any("crs_epsg" in e for e in errors)

    def test_validate_invalid_deliverable_format(self):
        spec = {
            "description": "Test",
            "task_category": "site_survey",
            "capability_requirements": {
                "deliverables": [{"format": "FAKE_FORMAT"}],
            },
            "budget_ceiling": 1000,
            "sla_seconds": 3600,
        }
        errors = validate_task_spec(spec)
        assert any("FAKE_FORMAT" in e for e in errors)

    def test_validate_invalid_mrta(self):
        spec = {
            "description": "Test",
            "task_category": "site_survey",
            "capability_requirements": {
                "mrta_class": {"robot_type": "ZZ"},
            },
            "budget_ceiling": 1000,
            "sla_seconds": 3600,
        }
        errors = validate_task_spec(spec)
        assert any("mrta_class.robot_type" in e for e in errors)


class TestComplianceRecord:
    """Phase 4: ComplianceRecord dataclass."""

    def test_create_compliance_record(self):
        record = ComplianceRecord(
            robot_id="robot_001",
            doc_type="faa_part_107",
            status="VERIFIED",
        )
        assert record.robot_id == "robot_001"
        assert record.status == "VERIFIED"

    def test_compliance_record_defaults(self):
        record = ComplianceRecord(
            robot_id="robot_001",
            doc_type="insurance_coi",
            status="MISSING",
        )
        assert record.expires_at is None
        assert record.details == {}


class TestAgreement:
    """Phase 5: Agreement dataclass."""

    def test_create_agreement(self):
        agreement = Agreement(
            request_id="req_abc123",
            template="consensusdocs_750",
        )
        assert agreement.status == "draft"
        assert agreement.buyer_signed is False
        assert agreement.operator_signed is False


class TestRFPProcessor:
    """Phase 2: RFP processing."""

    def test_process_topographic_rfp(self):
        from auction.rfp_processor import process_rfp
        specs = process_rfp("This project requires a topographic survey of the highway corridor.")
        assert len(specs) >= 1
        assert specs[0]["task_category"] == "site_survey"
        assert specs[0]["budget_ceiling"] > 0

    def test_process_multi_task_rfp(self):
        from auction.rfp_processor import process_rfp
        specs = process_rfp(
            "The project requires: topographic survey of the corridor, "
            "subsurface GPR utility detection, and monthly progress monitoring."
        )
        assert len(specs) == 3
        categories = {s["task_category"] for s in specs}
        assert "site_survey" in categories
        assert "subsurface_scan" in categories
        assert "progress_monitoring" in categories

    def test_task_decomposition_populated(self):
        from auction.rfp_processor import process_rfp
        specs = process_rfp("Topographic survey needed for highway widening.")
        assert "task_decomposition" in specs[0]
        assert specs[0]["task_decomposition"]["rfp_id"].startswith("rfp_")
        assert specs[0]["task_decomposition"]["task_index"] == 0

    def test_validate_task_specs(self):
        from auction.rfp_processor import process_rfp, validate_task_specs
        specs = process_rfp("Topographic survey of the interstate corridor.")
        result = validate_task_specs(specs)
        assert result["all_valid"] is True

    def test_get_site_recon(self):
        from auction.rfp_processor import process_rfp, get_site_recon
        specs = process_rfp("Topographic survey for Michigan highway project along I-94.")
        recon = get_site_recon("Michigan highway project along I-94 corridor", specs)
        assert recon["location"]["value"] == "Michigan"
        assert recon["terrain"]["type"] == "corridor"


class TestComplianceChecker:
    """Phase 4: Compliance verification."""

    def test_verify_empty_operator(self):
        from auction.compliance import ComplianceChecker
        checker = ComplianceChecker()
        result = checker.verify_operator("robot_001")
        assert result["verified"] == 0
        assert result["missing"] == 6
        assert result["compliant"] is False

    def test_upload_and_verify(self):
        from auction.compliance import ComplianceChecker
        checker = ComplianceChecker()
        checker.upload_document("robot_001", "faa_part_107", "cert_content")
        result = checker.verify_operator("robot_001")
        assert result["verified"] == 1
        assert result["missing"] == 5

    def test_invalid_doc_type(self):
        from auction.compliance import ComplianceChecker
        checker = ComplianceChecker()
        with pytest.raises(ValueError, match="doc_type must be one of"):
            checker.upload_document("robot_001", "invalid_type", "content")


class TestBondVerifier:
    """Phase 4: Bond verification."""

    def test_verify_valid_bond(self):
        from auction.bond_verifier import verify_bond
        bond_text = """
        PAYMENT BOND
        Bond No: PB-2024-12345
        Surety: Travelers Casualty and Surety Company of America
        Principal: Great Lakes Construction Co.
        Obligee: Michigan Department of Transportation
        Penal Sum: $250,000.00
        Effective Date: January 15, 2024
        """
        result = verify_bond(bond_text, ["req_001", "req_002"])
        assert result["status"] in ("VERIFIED", "PARTIAL")
        assert result["bond_number"] == "PB-2024-12345"
        assert "travelers" in result["surety"].lower()

    def test_verify_empty_bond(self):
        from auction.bond_verifier import verify_bond
        result = verify_bond("This is not a bond document.", ["req_001"])
        assert result["status"] == "FAILED"


class TestTermsComparator:
    """Phase 4: Legal terms comparison."""

    def test_compare_baseline_terms(self):
        from auction.terms_comparator import compare_terms
        result = compare_terms(
            "Standard operator terms with limitation of liability at 1x contract value.",
            "Standard GC subcontract with net 30 payment terms.",
            "MI",
        )
        assert result["dimensions_compared"] == 12
        assert result["overall_risk"] in ("low", "medium", "high")

    def test_flag_broad_form_indemnification(self):
        from auction.terms_comparator import compare_terms
        result = compare_terms(
            "Standard terms.",
            "The subcontractor shall indemnify and hold harmless using broad form indemnification.",
            "MI",
        )
        assert result["high_risk_count"] >= 1
        assert any("INDEMNIFICATION" in f for f in result["flags"])


class TestAgreementGeneration:
    """Phase 5: Agreement generation."""

    def test_generate_agreement(self):
        from auction.agreement import generate_agreement
        from auction.core import Task, Bid
        from decimal import Decimal
        from unittest.mock import MagicMock

        # Create a mock record
        record = MagicMock()
        record.task = Task(
            description="Topographic survey",
            task_category="site_survey",
            capability_requirements={
                "hard": {"sensors_required": ["aerial_lidar"], "accuracy_required": {"horizontal_cm": 2.0}},
                "soft": {"preferred_deliverables": ["LandXML", "DXF"]},
                "payload": {"format": "multi_file", "fields": ["LandXML"]},
            },
            budget_ceiling=Decimal("50000"),
            sla_seconds=14 * 86400,
            task_decomposition={"rfp_id": "rfp_test123"},
            project_metadata={"jurisdiction": "MI"},
        )
        record.winning_bid = Bid(
            request_id=record.task.request_id,
            robot_id="robot_001",
            price=Decimal("45000"),
            sla_commitment_seconds=12 * 86400,
            ai_confidence=0.95,
            capability_metadata={},
            reputation_metadata={"completion_rate": 0.99},
            bid_hash="abc123",
        )

        agreement = generate_agreement(record, "consensusdocs_750")
        assert agreement["template"] == "consensusdocs_750"
        assert agreement["status"] == "draft"
        assert agreement["terms"]["fee"]["contract_price"] == "45000"
        assert agreement["terms"]["scope"]["task_category"] == "site_survey"
        assert agreement["terms"]["retainage"]["percentage"] == "10%"
        assert len(agreement["terms"]["dispute_resolution"]["steps"]) == 3


class TestConstructionFleet:
    """Construction mock fleet tests."""

    def test_create_construction_fleet(self):
        from auction.mock_fleet import create_construction_fleet
        fleet = create_construction_fleet()
        assert len(fleet) == 7
        ids = {r.robot_id for r in fleet}
        assert "great-lakes-aerial" in ids
        assert "wolverine-survey-tech" in ids
        assert "midwest-gpr" in ids

    def test_create_full_fleet(self):
        from auction.mock_fleet import create_full_fleet
        fleet = create_full_fleet()
        assert len(fleet) == 10  # 3 original + 7 construction

    def test_construction_robot_bids_on_survey_task(self):
        from auction.mock_fleet import GreatLakesAerial
        from auction.core import Task
        robot = GreatLakesAerial()
        task = Task(
            description="Topographic survey",
            task_category="site_survey",
            capability_requirements={"hard": {"sensors_required": ["aerial_lidar", "rtk_gps"]}},
            budget_ceiling=Decimal("100000"),
            sla_seconds=14 * 86400,
        )
        bid = robot.bid_engine(task)
        assert bid is not None
        assert bid.robot_id == "great-lakes-aerial"
        assert bid.price == Decimal("82000")  # 82% of $100K budget

    def test_construction_robot_declines_wrong_sensors(self):
        from auction.mock_fleet import MidwestGPR
        from auction.core import Task
        robot = MidwestGPR()
        task = Task(
            description="Aerial LiDAR survey",
            task_category="site_survey",
            capability_requirements={"hard": {"sensors_required": ["aerial_lidar"]}},
            budget_ceiling=Decimal("50000"),
            sla_seconds=86400,
        )
        bid = robot.bid_engine(task)
        assert bid is None  # GPR robot can't do aerial LiDAR

    def test_construction_robot_has_detailed_metadata(self):
        from auction.mock_fleet import GreatLakesAerial
        robot = GreatLakesAerial()
        assert "equipment" in robot.capability_metadata
        assert "coverage_area" in robot.capability_metadata
        assert "certifications" in robot.capability_metadata
        assert "pls_info" in robot.capability_metadata
        assert "insurance" in robot.capability_metadata
        assert robot.capability_metadata["coverage_area"]["states"] == ["MI", "OH", "IN"]

    def test_rfp_with_site_info(self):
        from auction.rfp_processor import process_rfp
        specs = process_rfp(
            "Topographic survey for the I-94 corridor widening project.",
            jurisdiction="MI",
            site_info={
                "project_name": "I-94 Modernization Phase 2",
                "location": "Detroit, MI — I-94 from Conner Ave to Cadieux Rd",
                "coordinates": {"lat": 42.3736, "lon": -82.9553},
                "survey_area": {"type": "corridor", "acres": 45, "length_miles": 3.2, "width_ft": 200},
                "agency": "MDOT",
                "project_id": "CS-12345",
                "terrain": "corridor",
                "airspace_class": "G",
                "reference_standards": ["MDOT Section 104.09", "NCHRP 748"],
            },
        )
        assert len(specs) >= 1
        meta = specs[0]["project_metadata"]
        assert meta["project_name"] == "I-94 Modernization Phase 2"
        assert meta["coordinates"] == {"lat": 42.3736, "lon": -82.9553}
        assert meta["survey_area"]["acres"] == 45
        assert meta["agency"] == "MDOT"
        assert meta["terrain"] == "corridor"

    def test_engine_with_construction_fleet(self):
        from auction.mock_fleet import create_construction_fleet
        from auction.engine import AuctionEngine
        from auction.wallet import WalletLedger

        wallet = WalletLedger()
        wallet.create_wallet("buyer", Decimal("0"))
        wallet.fund_wallet("buyer", Decimal("200000"))

        fleet = create_construction_fleet()
        engine = AuctionEngine(fleet, wallet=wallet)

        result = engine.post_task({
            "description": "Topographic survey for highway corridor",
            "task_category": "site_survey",
            "capability_requirements": {
                "hard": {"sensors_required": ["aerial_lidar", "rtk_gps"]},
                "payload": {"format": "multi_file", "fields": ["LandXML", "DXF"]},
            },
            "budget_ceiling": 100000,
            "sla_seconds": 14 * 86400,
        })
        assert result["state"] == "bidding"
        assert result["eligible_robots"] >= 2  # Great Lakes + Petoskey + Meridian

        bids = engine.get_bids(result["request_id"])
        assert bids["bid_count"] >= 2


class TestPDFBondExtraction:
    """PDF bond extraction and verification."""

    def test_create_and_verify_pdf_bond(self):
        import fitz
        from auction.bond_verifier import extract_text_from_pdf, verify_bond
        from pathlib import Path

        # Create PDF from text
        bond_text = Path("auction/tests/scenarios/gc_profiles/01_dans_excavating/bond.txt").read_text()
        pdf_path = Path("auction/data/sample_deliverables/test_bond.pdf")

        doc = fitz.open()
        page = doc.new_page()
        rect = fitz.Rect(72, 72, 540, 720)
        page.insert_textbox(rect, bond_text, fontsize=9, fontname="helv")
        doc.save(str(pdf_path))
        doc.close()

        # Extract and verify
        extracted = extract_text_from_pdf(str(pdf_path))
        assert len(extracted) > 100
        assert "Travelers" in extracted or "travelers" in extracted.lower()

        result = verify_bond(extracted, ["req_test"], "MI")
        assert result["surety_circular_570"] is True
        assert result["status"] in ("VERIFIED", "PARTIAL")

        # Cleanup
        pdf_path.unlink(missing_ok=True)
