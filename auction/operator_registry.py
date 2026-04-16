"""Operator registry — manages operator profiles and onboarding.

Handles the full operator lifecycle:
1. Register (company info, contact, coverage area)
2. List equipment (sensors, models, certifications)
3. Upload compliance docs (Part 107, COI, PLS, etc.)
4. Set pricing preferences
5. Activate for bidding

Storage: in-memory (v1.0), SQLite persistence (v2.0).

On-chain integration (v2.0+): when an operator activates, their profile
should also mint an ERC-8004 agent card on Base via the discovery_bridge
module (see yakrover-8004-mcp repo). The agent card includes:
- sensor_capabilities (from equipment list)
- coverage_area (GeoJSON from coverage_states + max_range_miles)
- min_price, accepted_currencies, reputation_score
This enables on-chain robot discovery alongside marketplace registration.
See: auction/discovery_bridge.py for the PluginRobotAdapter interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class OperatorProfile:
    """Registered operator on the marketplace."""

    operator_id: str
    company_name: str
    contact_name: str
    contact_email: str
    location: str  # City, State
    coverage_states: list[str] = field(default_factory=list)
    max_range_miles: int = 200
    equipment: list[dict] = field(default_factory=list)  # [{type, model, accuracy_cm, ...}]
    sensors: list[str] = field(default_factory=list)  # Flat list derived from equipment
    certifications: list[str] = field(default_factory=list)  # faa_part_107, pls_license, etc.
    pricing: dict = field(default_factory=dict)  # {min_daily_rate, preferred_task_types, ...}
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "pending"  # pending, active, suspended
    compliance_status: dict = field(default_factory=dict)  # From ComplianceChecker
    pls_info: dict | None = None  # {name, license, state, expires}
    insurance: dict = field(default_factory=dict)  # {cgl, eo, aviation, carrier}
    stripe_account_id: str | None = None  # Stripe Connect Express account ID


class OperatorRegistry:
    """Manages operator registration and profile lifecycle."""

    def __init__(self) -> None:
        self._operators: dict[str, OperatorProfile] = {}

    def register(
        self,
        company_name: str,
        contact_name: str,
        contact_email: str,
        location: str,
        coverage_states: list[str] | None = None,
        max_range_miles: int = 200,
    ) -> OperatorProfile:
        """Register a new operator. Returns the profile with a generated operator_id."""
        import hashlib

        operator_id = f"op_{hashlib.sha256(f'{company_name}:{contact_email}'.encode()).hexdigest()[:12]}"

        if operator_id in self._operators:
            return self._operators[operator_id]

        profile = OperatorProfile(
            operator_id=operator_id,
            company_name=company_name,
            contact_name=contact_name,
            contact_email=contact_email,
            location=location,
            coverage_states=coverage_states or [],
            max_range_miles=max_range_miles,
            status="pending",
        )
        self._operators[operator_id] = profile
        return profile

    def add_equipment(
        self,
        operator_id: str,
        equipment_type: str,
        model: str,
        **specs: Any,
    ) -> dict:
        """Add a piece of equipment to an operator's profile."""
        profile = self._get(operator_id)
        entry = {"type": equipment_type, "model": model, **specs}
        profile.equipment.append(entry)
        if equipment_type not in profile.sensors:
            profile.sensors.append(equipment_type)
        return {"operator_id": operator_id, "equipment_added": entry, "total_equipment": len(profile.equipment)}

    def set_pricing(
        self,
        operator_id: str,
        min_daily_rate: float = 0,
        preferred_task_types: list[str] | None = None,
        max_concurrent_tasks: int = 3,
    ) -> dict:
        """Set operator pricing preferences."""
        profile = self._get(operator_id)
        profile.pricing = {
            "min_daily_rate": min_daily_rate,
            "preferred_task_types": preferred_task_types or [],
            "max_concurrent_tasks": max_concurrent_tasks,
        }
        return {"operator_id": operator_id, "pricing": profile.pricing}

    def set_pls(
        self,
        operator_id: str,
        name: str,
        license_number: str,
        state: str,
        expires: str,
    ) -> dict:
        """Set PLS information for an operator."""
        profile = self._get(operator_id)
        profile.pls_info = {
            "name": name,
            "license": license_number,
            "state": state,
            "expires": expires,
        }
        if "pls_license" not in profile.certifications:
            profile.certifications.append("pls_license")
        return {"operator_id": operator_id, "pls": profile.pls_info}

    def set_insurance(
        self,
        operator_id: str,
        cgl: str,
        eo: str = "",
        aviation: str = "",
        carrier: str = "",
    ) -> dict:
        """Set insurance information for an operator."""
        profile = self._get(operator_id)
        profile.insurance = {
            "cgl": cgl,
            "eo": eo,
            "aviation": aviation,
            "carrier": carrier,
        }
        return {"operator_id": operator_id, "insurance": profile.insurance}

    # Default test account for demo/fallback when Stripe account is invalid
    TEST_STRIPE_ACCOUNT = "acct_test_demo_fallback"

    def activate(
        self,
        operator_id: str,
        stripe_service: Any | None = None,
        use_test_account_fallback: bool = True,
    ) -> dict:
        """Activate an operator for bidding.

        Checks: at least 1 equipment item, Part 107 cert, insurance on file,
        and Stripe Connect account linked with payouts enabled.

        Args:
            operator_id: The operator to activate.
            stripe_service: Optional StripeService instance. If provided,
                verifies payouts_enabled on the Stripe account. If None
                (demo/stub mode), skips the Stripe API check.
            use_test_account_fallback: If True and the Stripe account is
                invalid or payouts not enabled, fall back to a test account
                so the operator can still activate in demo mode.
        """
        profile = self._get(operator_id)
        issues = []
        if not profile.equipment:
            issues.append("No equipment listed — add at least 1 via add_equipment")
        if "faa_part_107" not in profile.certifications:
            issues.append("FAA Part 107 certification not on file")
        if not profile.insurance.get("cgl"):
            issues.append("Insurance COI not on file — set via set_insurance")
        if not profile.stripe_account_id:
            issues.append("Stripe Connect account not linked — complete payment onboarding")

        if issues:
            return {
                "operator_id": operator_id,
                "status": "pending",
                "issues": issues,
                "message": "Fix the issues above before activation",
            }

        # Verify Stripe payouts_enabled if a StripeService is available
        stripe_warning = None
        if stripe_service and not stripe_service.stub_mode:
            account_data = stripe_service.get_account(profile.stripe_account_id)
            if account_data.get("error"):
                if use_test_account_fallback:
                    stripe_warning = f"Stripe account lookup failed ({account_data['error']}). Using test account for demo."
                    profile.stripe_account_id = self.TEST_STRIPE_ACCOUNT
                else:
                    issues.append(f"Stripe account error: {account_data['error']}")
            elif not account_data.get("payouts_enabled", False):
                disabled_reason = account_data.get("requirements", {}).get("disabled_reason", "unknown")
                if use_test_account_fallback:
                    stripe_warning = f"Stripe payouts not enabled (reason: {disabled_reason}). Using test account for demo."
                    profile.stripe_account_id = self.TEST_STRIPE_ACCOUNT
                else:
                    issues.append(
                        f"Stripe payouts not enabled — reason: {disabled_reason}. "
                        "Complete identity verification in the Stripe Express Dashboard."
                    )

        if issues:
            return {
                "operator_id": operator_id,
                "status": "pending",
                "issues": issues,
                "message": "Fix the issues above before activation",
            }

        profile.status = "active"
        result = {
            "operator_id": operator_id,
            "status": "active",
            "company_name": profile.company_name,
            "sensors": profile.sensors,
            "coverage_states": profile.coverage_states,
            "equipment_count": len(profile.equipment),
            "message": f"{profile.company_name} is now active and eligible for bidding",
        }
        if stripe_warning:
            result["stripe_warning"] = stripe_warning
            result["stripe_account_id"] = self.TEST_STRIPE_ACCOUNT
        return result

    def update_profile(self, operator_id: str, **fields: Any) -> dict:
        """Update an existing operator profile. Only provided fields are changed."""
        profile = self._get(operator_id)
        allowed = {
            "company_name", "contact_name", "contact_email", "location",
            "coverage_states", "max_range_miles", "stripe_account_id",
        }
        updated = []
        for k, v in fields.items():
            if v is None:
                continue
            if k not in allowed:
                continue
            setattr(profile, k, v)
            updated.append(k)
        return {
            "operator_id": operator_id,
            "updated_fields": updated,
            "profile": self.get_profile(operator_id),
        }

    def get_profile(self, operator_id: str) -> dict:
        """Get full operator profile."""
        profile = self._get(operator_id)
        return {
            "operator_id": profile.operator_id,
            "company_name": profile.company_name,
            "contact_name": profile.contact_name,
            "contact_email": profile.contact_email,
            "location": profile.location,
            "coverage_states": profile.coverage_states,
            "max_range_miles": profile.max_range_miles,
            "equipment": profile.equipment,
            "sensors": profile.sensors,
            "certifications": profile.certifications,
            "pricing": profile.pricing,
            "pls_info": profile.pls_info,
            "insurance": profile.insurance,
            "status": profile.status,
            "registered_at": profile.registered_at.isoformat(),
        }

    def list_operators(self, status: str | None = None, state: str | None = None) -> dict:
        """List registered operators with optional filters."""
        results = []
        for op in self._operators.values():
            if status and op.status != status:
                continue
            if state and state not in op.coverage_states:
                continue
            results.append(
                {
                    "operator_id": op.operator_id,
                    "company_name": op.company_name,
                    "location": op.location,
                    "status": op.status,
                    "sensors": op.sensors,
                    "equipment_count": len(op.equipment),
                }
            )
        return {"total": len(results), "operators": results}

    def _get(self, operator_id: str) -> OperatorProfile:
        if operator_id not in self._operators:
            raise KeyError(f"Operator not found: {operator_id}")
        return self._operators[operator_id]
