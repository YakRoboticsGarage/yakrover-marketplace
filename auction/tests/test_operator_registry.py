"""Tests for the operator registry module."""

from __future__ import annotations

import pytest

from auction.operator_registry import OperatorProfile, OperatorRegistry


@pytest.fixture
def registry() -> OperatorRegistry:
    return OperatorRegistry()


@pytest.fixture
def registered_op(registry: OperatorRegistry) -> OperatorProfile:
    """A registered operator with default settings."""
    return registry.register(
        company_name="SkyView Surveying LLC",
        contact_name="Maria Lopez",
        contact_email="maria@skyviewsurveying.com",
        location="Detroit, MI",
        coverage_states=["MI", "OH", "IN"],
        max_range_miles=150,
    )


class TestRegister:
    def test_register_creates_profile(self, registry: OperatorRegistry) -> None:
        profile = registry.register(
            company_name="TestCo",
            contact_name="Alice",
            contact_email="alice@testco.com",
            location="Austin, TX",
        )
        assert profile.operator_id.startswith("op_")
        assert profile.company_name == "TestCo"
        assert profile.contact_name == "Alice"
        assert profile.contact_email == "alice@testco.com"
        assert profile.location == "Austin, TX"
        assert profile.status == "pending"
        assert profile.equipment == []
        assert profile.sensors == []

    def test_register_with_coverage(self, registry: OperatorRegistry) -> None:
        profile = registry.register(
            company_name="TestCo",
            contact_name="Alice",
            contact_email="alice@testco.com",
            location="Austin, TX",
            coverage_states=["TX", "OK"],
            max_range_miles=300,
        )
        assert profile.coverage_states == ["TX", "OK"]
        assert profile.max_range_miles == 300

    def test_register_idempotent(self, registry: OperatorRegistry) -> None:
        p1 = registry.register("Co", "A", "a@co.com", "NY, NY")
        p2 = registry.register("Co", "A", "a@co.com", "NY, NY")
        assert p1.operator_id == p2.operator_id
        assert p1 is p2

    def test_register_different_emails_different_ids(self, registry: OperatorRegistry) -> None:
        p1 = registry.register("Co", "A", "a@co.com", "NY, NY")
        p2 = registry.register("Co", "B", "b@co.com", "NY, NY")
        assert p1.operator_id != p2.operator_id


class TestAddEquipment:
    def test_add_equipment(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        result = registry.add_equipment(
            registered_op.operator_id,
            "aerial_lidar",
            "DJI Matrice 350 RTK + Zenmuse L2",
            accuracy_cm=2.0,
        )
        assert result["total_equipment"] == 1
        assert result["equipment_added"]["type"] == "aerial_lidar"
        assert result["equipment_added"]["model"] == "DJI Matrice 350 RTK + Zenmuse L2"
        assert result["equipment_added"]["accuracy_cm"] == 2.0

    def test_add_multiple_equipment(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        registry.add_equipment(registered_op.operator_id, "aerial_lidar", "L2")
        result = registry.add_equipment(registered_op.operator_id, "gpr", "GSSI StructureScan Mini XT")
        assert result["total_equipment"] == 2
        assert registered_op.sensors == ["aerial_lidar", "gpr"]

    def test_add_equipment_same_type_no_duplicate_sensor(
        self, registry: OperatorRegistry, registered_op: OperatorProfile
    ) -> None:
        registry.add_equipment(registered_op.operator_id, "aerial_lidar", "L2")
        registry.add_equipment(registered_op.operator_id, "aerial_lidar", "L1")
        assert registered_op.sensors == ["aerial_lidar"]
        assert len(registered_op.equipment) == 2

    def test_add_equipment_unknown_operator(self, registry: OperatorRegistry) -> None:
        with pytest.raises(KeyError, match="Operator not found"):
            registry.add_equipment("op_nonexistent", "lidar", "model")


class TestSetPricing:
    def test_set_pricing(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        result = registry.set_pricing(
            registered_op.operator_id,
            min_daily_rate=1500.0,
            preferred_task_types=["aerial_topo", "progress_monitoring"],
            max_concurrent_tasks=2,
        )
        assert result["pricing"]["min_daily_rate"] == 1500.0
        assert result["pricing"]["preferred_task_types"] == ["aerial_topo", "progress_monitoring"]
        assert result["pricing"]["max_concurrent_tasks"] == 2

    def test_set_pricing_defaults(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        result = registry.set_pricing(registered_op.operator_id)
        assert result["pricing"]["min_daily_rate"] == 0
        assert result["pricing"]["preferred_task_types"] == []
        assert result["pricing"]["max_concurrent_tasks"] == 3


class TestSetPls:
    def test_set_pls(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        result = registry.set_pls(
            registered_op.operator_id,
            name="Maria Lopez, PLS",
            license_number="PLS-MI-12345",
            state="MI",
            expires="2027-06-30",
        )
        assert result["pls"]["name"] == "Maria Lopez, PLS"
        assert result["pls"]["license"] == "PLS-MI-12345"
        assert "pls_license" in registered_op.certifications

    def test_set_pls_no_duplicate_cert(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        registry.set_pls(registered_op.operator_id, "A", "1", "MI", "2027-01-01")
        registry.set_pls(registered_op.operator_id, "B", "2", "OH", "2028-01-01")
        assert registered_op.certifications.count("pls_license") == 1


class TestSetInsurance:
    def test_set_insurance(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        result = registry.set_insurance(
            registered_op.operator_id,
            cgl="$2M per occurrence / $4M aggregate",
            eo="$1M per claim",
            aviation="$5M hull + liability",
            carrier="Berkley Assurance",
        )
        assert result["insurance"]["cgl"] == "$2M per occurrence / $4M aggregate"
        assert result["insurance"]["carrier"] == "Berkley Assurance"

    def test_set_insurance_minimal(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        result = registry.set_insurance(registered_op.operator_id, cgl="$1M")
        assert result["insurance"]["cgl"] == "$1M"
        assert result["insurance"]["eo"] == ""


class TestActivate:
    def _prepare_for_activation(self, registry: OperatorRegistry, op: OperatorProfile) -> None:
        """Give operator everything needed for activation."""
        registry.add_equipment(op.operator_id, "aerial_lidar", "L2")
        op.certifications.append("faa_part_107")
        registry.set_insurance(op.operator_id, cgl="$2M")
        op.stripe_account_id = "acct_test_123"

    def test_activate_success(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        self._prepare_for_activation(registry, registered_op)
        result = registry.activate(registered_op.operator_id)
        assert result["status"] == "active"
        assert registered_op.status == "active"
        assert "now active" in result["message"]
        assert result["company_name"] == "SkyView Surveying LLC"

    def test_activate_no_equipment(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        registered_op.certifications.append("faa_part_107")
        registry.set_insurance(registered_op.operator_id, cgl="$2M")
        result = registry.activate(registered_op.operator_id)
        assert result["status"] == "pending"
        assert any("equipment" in i.lower() for i in result["issues"])

    def test_activate_no_part_107(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        registry.add_equipment(registered_op.operator_id, "aerial_lidar", "L2")
        registry.set_insurance(registered_op.operator_id, cgl="$2M")
        result = registry.activate(registered_op.operator_id)
        assert result["status"] == "pending"
        assert any("Part 107" in i for i in result["issues"])

    def test_activate_no_insurance(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        registry.add_equipment(registered_op.operator_id, "aerial_lidar", "L2")
        registered_op.certifications.append("faa_part_107")
        result = registry.activate(registered_op.operator_id)
        assert result["status"] == "pending"
        assert any("Insurance" in i for i in result["issues"])

    def test_activate_no_stripe(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        registry.add_equipment(registered_op.operator_id, "aerial_lidar", "L2")
        registered_op.certifications.append("faa_part_107")
        registry.set_insurance(registered_op.operator_id, cgl="$2M")
        result = registry.activate(registered_op.operator_id)
        assert result["status"] == "pending"
        assert any("Stripe" in i for i in result["issues"])

    def test_activate_multiple_issues(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        result = registry.activate(registered_op.operator_id)
        assert result["status"] == "pending"
        assert len(result["issues"]) == 4

    def test_activate_stripe_payouts_disabled_with_fallback(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        """When Stripe payouts not enabled, falls back to test account."""
        self._prepare_for_activation(registry, registered_op)

        class MockStripe:
            stub_mode = False
            def get_account(self, acct_id):
                return {"payouts_enabled": False, "requirements": {"disabled_reason": "pending_verification"}}

        result = registry.activate(registered_op.operator_id, stripe_service=MockStripe(), use_test_account_fallback=True)
        assert result["status"] == "active"
        assert "stripe_warning" in result
        assert "test account" in result["stripe_warning"].lower()
        assert registered_op.stripe_account_id == OperatorRegistry.TEST_STRIPE_ACCOUNT

    def test_activate_stripe_payouts_disabled_no_fallback(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        """When Stripe payouts not enabled and no fallback, blocks activation."""
        self._prepare_for_activation(registry, registered_op)

        class MockStripe:
            stub_mode = False
            def get_account(self, acct_id):
                return {"payouts_enabled": False, "requirements": {"disabled_reason": "pending_verification"}}

        result = registry.activate(registered_op.operator_id, stripe_service=MockStripe(), use_test_account_fallback=False)
        assert result["status"] == "pending"
        assert any("payouts not enabled" in i for i in result["issues"])

    def test_activate_stripe_error_with_fallback(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        """When Stripe API errors, falls back to test account."""
        self._prepare_for_activation(registry, registered_op)

        class MockStripe:
            stub_mode = False
            def get_account(self, acct_id):
                return {"error": "No such account", "error_type": "InvalidRequestError"}

        result = registry.activate(registered_op.operator_id, stripe_service=MockStripe(), use_test_account_fallback=True)
        assert result["status"] == "active"
        assert "stripe_warning" in result

    def test_activate_stripe_payouts_enabled(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        """When Stripe payouts enabled, activates normally with no warning."""
        self._prepare_for_activation(registry, registered_op)

        class MockStripe:
            stub_mode = False
            def get_account(self, acct_id):
                return {"payouts_enabled": True, "charges_enabled": True}

        result = registry.activate(registered_op.operator_id, stripe_service=MockStripe())
        assert result["status"] == "active"
        assert "stripe_warning" not in result


class TestListOperators:
    def test_list_empty(self, registry: OperatorRegistry) -> None:
        result = registry.list_operators()
        assert result["total"] == 0
        assert result["operators"] == []

    def test_list_all(self, registry: OperatorRegistry) -> None:
        registry.register("A", "a", "a@a.com", "NY, NY", ["NY"])
        registry.register("B", "b", "b@b.com", "LA, CA", ["CA"])
        result = registry.list_operators()
        assert result["total"] == 2

    def test_list_filter_by_status(self, registry: OperatorRegistry) -> None:
        op = registry.register("A", "a", "a@a.com", "NY, NY", ["NY"])
        registry.register("B", "b", "b@b.com", "LA, CA", ["CA"])
        # Manually activate one
        registry.add_equipment(op.operator_id, "lidar", "L2")
        op.certifications.append("faa_part_107")
        registry.set_insurance(op.operator_id, cgl="$2M")
        op.stripe_account_id = "acct_test_456"
        registry.activate(op.operator_id)

        active = registry.list_operators(status="active")
        assert active["total"] == 1
        assert active["operators"][0]["company_name"] == "A"

        pending = registry.list_operators(status="pending")
        assert pending["total"] == 1
        assert pending["operators"][0]["company_name"] == "B"

    def test_list_filter_by_state(self, registry: OperatorRegistry) -> None:
        registry.register("A", "a", "a@a.com", "NY, NY", ["NY", "NJ"])
        registry.register("B", "b", "b@b.com", "LA, CA", ["CA"])
        result = registry.list_operators(state="NJ")
        assert result["total"] == 1
        assert result["operators"][0]["company_name"] == "A"


class TestGetProfile:
    def test_get_profile(self, registry: OperatorRegistry, registered_op: OperatorProfile) -> None:
        profile = registry.get_profile(registered_op.operator_id)
        assert profile["operator_id"] == registered_op.operator_id
        assert profile["company_name"] == "SkyView Surveying LLC"
        assert profile["status"] == "pending"
        assert "registered_at" in profile

    def test_get_profile_not_found(self, registry: OperatorRegistry) -> None:
        with pytest.raises(KeyError, match="Operator not found"):
            registry.get_profile("op_nonexistent")
