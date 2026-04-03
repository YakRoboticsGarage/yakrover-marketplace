"""Tests for deliverable QA system (IMP-004, IMP-006)."""

from auction.deliverable_qa import check_delivery, get_qa_level, QAResult


class TestQALevelSelection:

    def test_explicit_override(self):
        spec = {"capability_requirements": {"qa_level": 0}, "task_category": "site_survey"}
        assert get_qa_level(spec) == 0

    def test_env_sensing_defaults_to_0(self):
        assert get_qa_level({"task_category": "env_sensing"}) == 0

    def test_site_survey_defaults_to_2(self):
        assert get_qa_level({"task_category": "site_survey"}) == 2

    def test_unknown_category_defaults_to_1(self):
        assert get_qa_level({"task_category": "unknown_thing"}) == 1

    def test_clamp_to_range(self):
        spec = {"capability_requirements": {"qa_level": 99}}
        assert get_qa_level(spec) == 3
        spec2 = {"capability_requirements": {"qa_level": -5}}
        assert get_qa_level(spec2) == 0


class TestLevel0:

    def test_always_passes(self):
        result = check_delivery({}, {}, qa_level=0)
        assert result.status == "PASS"
        assert result.level == 0

    def test_empty_data_passes(self):
        result = check_delivery({}, {"task_category": "env_sensing"})
        assert result.status == "PASS"


class TestLevel1:

    def test_basic_valid_delivery(self):
        data = {"temperature_c": 22.5, "humidity_pct": 45.0}
        spec = {
            "task_category": "env_sensing",
            "capability_requirements": {
                "qa_level": 1,
                "payload": {"format": "json", "fields": ["temperature_c", "humidity_pct"]},
            },
        }
        result = check_delivery(data, spec)
        assert result.status == "PASS"
        assert result.level == 1

    def test_missing_required_field_fails(self):
        data = {"temperature_c": 22.5}
        spec = {
            "capability_requirements": {
                "qa_level": 1,
                "payload": {"fields": ["temperature_c", "humidity_pct"]},
            },
        }
        result = check_delivery(data, spec)
        assert result.status == "FAIL"
        assert any("humidity_pct" in i for i in result.issues)

    def test_empty_data_fails(self):
        result = check_delivery({}, {"capability_requirements": {"qa_level": 1}})
        assert result.status == "FAIL"

    def test_readings_array_valid(self):
        data = {
            "readings": [
                {"waypoint": 1, "temperature_c": 22.4, "humidity_pct": 45.2},
                {"waypoint": 2, "temperature_c": 23.1, "humidity_pct": 43.8},
            ],
            "summary": "All good",
        }
        spec = {"capability_requirements": {"qa_level": 1, "payload": {"fields": ["readings"]}}}
        result = check_delivery(data, spec)
        assert result.status == "PASS"
        assert result.details["reading_count"] == 2

    def test_temperature_out_of_range_warns(self):
        data = {"temperature_c": 200.0}
        spec = {"capability_requirements": {"qa_level": 1}}
        result = check_delivery(data, spec)
        assert result.status == "WARN"
        assert any("plausible range" in i for i in result.issues)

    def test_readings_plausibility(self):
        data = {"readings": [{"temperature_c": -50}]}
        spec = {"capability_requirements": {"qa_level": 1}}
        result = check_delivery(data, spec)
        assert any("plausible range" in i for i in result.issues)


class TestLevel2:

    def test_passes_with_all_standards_data(self):
        data = {
            "readings": [{"temperature_c": 22.0}],
            "coordinate_system": "EPSG:2113",
            "accuracy": {"horizontal_rmse_cm": 3.2, "vertical_rmse_cm": 4.1},
            "point_density_ppsm": 10.5,
            "files": [{"name": "scan.las", "format": "LAS"}],
        }
        spec = {
            "task_category": "site_survey",
            "capability_requirements": {
                "hard": {
                    "crs_epsg": 2113,
                    "asprs_vertical_class": "5cm",
                    "usgs_quality_level": "QL1",
                },
                "deliverables": [{"format": "LAS"}],
                "payload": {"fields": ["readings"]},
            },
        }
        result = check_delivery(data, spec)
        assert result.status == "PASS"
        assert result.level == 2

    def test_missing_crs_warns(self):
        data = {"readings": [{"temperature_c": 22.0}]}
        spec = {
            "capability_requirements": {
                "qa_level": 2,
                "hard": {"crs_epsg": 2113},
                "payload": {"fields": ["readings"]},
            },
        }
        result = check_delivery(data, spec)
        assert any("coordinate reference" in i.lower() for i in result.issues)

    def test_low_density_fails(self):
        data = {"readings": [{}], "point_density_ppsm": 1.0}
        spec = {
            "capability_requirements": {
                "qa_level": 2,
                "hard": {"usgs_quality_level": "QL1"},
                "payload": {"fields": ["readings"]},
            },
        }
        result = check_delivery(data, spec)
        assert result.status == "FAIL"
        assert any("density" in i.lower() for i in result.issues)

    def test_missing_accuracy_warns(self):
        data = {"readings": [{}]}
        spec = {
            "capability_requirements": {
                "qa_level": 2,
                "hard": {"asprs_vertical_class": "5cm"},
                "payload": {"fields": ["readings"]},
            },
        }
        result = check_delivery(data, spec)
        assert any("accuracy" in i.lower() for i in result.issues)


class TestLevel3:

    def test_pls_approved_passes(self):
        data = {"readings": [{}], "pls_review_status": "APPROVED"}
        spec = {"capability_requirements": {"qa_level": 3, "payload": {"fields": ["readings"]}}}
        result = check_delivery(data, spec)
        assert result.status == "PASS"
        assert result.level == 3

    def test_pls_pending_warns(self):
        data = {"readings": [{}], "pls_review_status": "PENDING"}
        spec = {"capability_requirements": {"qa_level": 3, "payload": {"fields": ["readings"]}}}
        result = check_delivery(data, spec)
        assert result.status == "WARN"

    def test_pls_missing_warns(self):
        data = {"readings": [{}]}
        spec = {"capability_requirements": {"qa_level": 3, "payload": {"fields": ["readings"]}}}
        result = check_delivery(data, spec)
        assert any("pls" in i.lower() for i in result.issues)

    def test_pls_rejected_fails(self):
        data = {"readings": [{}], "pls_review_status": "REJECTED"}
        spec = {"capability_requirements": {"qa_level": 3, "payload": {"fields": ["readings"]}}}
        result = check_delivery(data, spec)
        assert result.status == "FAIL"


class TestServerRoomDemo:
    """Verify the Tumbller server room demo passes QA at the right level."""

    def test_env_sensing_auto_selects_level_0(self):
        spec = {"task_category": "env_sensing", "capability_requirements": {}}
        assert get_qa_level(spec) == 0

    def test_tumbller_delivery_passes(self):
        data = {
            "readings": [
                {"waypoint": 1, "temperature_c": 22.4, "humidity_pct": 45.2},
                {"waypoint": 2, "temperature_c": 23.1, "humidity_pct": 43.8},
                {"waypoint": 3, "temperature_c": 21.9, "humidity_pct": 46.5},
            ],
            "summary": "All readings within spec.",
            "duration_seconds": 180,
            "robot_id": "989",
            "robot_name": "Tumbller Self-Balancing Robot",
        }
        spec = {
            "task_category": "env_sensing",
            "capability_requirements": {
                "payload": {"format": "json", "fields": ["readings", "summary"]},
            },
        }
        result = check_delivery(data, spec)
        assert result.passed
        assert result.level == 0  # env_sensing defaults to no QA


class TestQAResult:

    def test_to_dict(self):
        r = QAResult(status="PASS", level=1, checks_run=["data_exists"], details={"field_count": 3})
        d = r.to_dict()
        assert d["status"] == "PASS"
        assert d["level_name"] == "basic"
        assert d["passed"] is True

    def test_fail_not_passed(self):
        r = QAResult(status="FAIL", level=2, issues=["bad data"])
        assert not r.passed

    def test_warn_is_passed(self):
        r = QAResult(status="WARN", level=1, issues=["minor concern"])
        assert r.passed
