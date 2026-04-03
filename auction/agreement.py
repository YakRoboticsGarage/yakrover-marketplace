"""Agreement generation module.

Generates structured subcontract agreements from task specs, winning bids,
and compliance data using ConsensusDocs 750 or AIA A401 templates.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal


def generate_agreement(record: object, template: str = "consensusdocs_750") -> dict:
    """Generate a subcontract agreement from a task record.

    Args:
        record: TaskRecord with task, winning_bid, and metadata.
        template: Agreement template name.

    Returns structured agreement dict with all terms populated.
    """
    task = record.task
    bid = record.winning_bid

    if bid is None:
        raise ValueError("Cannot generate agreement without a winning bid")

    now = datetime.now(UTC)

    # Build terms from task spec and bid
    terms = {
        "scope": {
            "description": task.description,
            "task_category": task.task_category,
            "deliverables": _get_deliverables(task),
            "accuracy_requirements": _get_accuracy(task),
            "survey_type": task.project_metadata.get("survey_type", task.task_category),
        },
        "fee": {
            "contract_price": str(bid.price),
            "payment_method": task.payment_method,
            "billing": "milestone" if bid.price > Decimal("10000") else "lump_sum",
            "currency": "USD",
        },
        "schedule": {
            "sla_seconds": task.sla_seconds,
            "sla_days": task.sla_seconds // 86400,
            "start_condition": "Upon execution of this agreement",
            "completion": f"Within {task.sla_seconds // 86400} calendar days of notice to proceed",
        },
        "insurance": {
            "cgl": "$1,000,000/$2,000,000",
            "professional_eo": "$1,000,000/$2,000,000",
            "aviation_liability": "$5,000,000",
            "workers_comp": "Statutory limits",
            "additional_insured": "Required — naming buyer as additional insured",
        },
        "pls_supervision": {
            "required": True,
            "state": task.project_metadata.get("jurisdiction", "MI"),
            "responsibility": "Operator provides PLS supervision and stamps all deliverables",
        },
        "limitation_of_liability": {
            "cap": f"1x contract value (${bid.price})",
            "exclusions": "Gross negligence, willful misconduct, IP infringement",
        },
        "retainage": {
            "percentage": "10%",
            "release_condition": "Final acceptance of all deliverables",
            "amount": str((bid.price * Decimal("0.10")).quantize(Decimal("0.01"))),
        },
        "indemnification": {
            "form": "intermediate",
            "description": "Each party indemnifies the other for claims arising from its own negligence",
            "state_statute": task.project_metadata.get("jurisdiction", "MI"),
        },
        "data_ownership": {
            "deliverables": "Client owns all deliverables upon payment",
            "methodology": "Operator retains proprietary methods and software",
            "raw_data": "Raw sensor data retained by operator for 2 years",
        },
        "consequential_damages": {
            "waiver": "Mutual waiver of consequential, incidental, and indirect damages",
        },
        "dispute_resolution": {
            "steps": [
                "Direct negotiation (14 days)",
                "Mediation (30 days)",
                "Binding arbitration (AAA Construction Rules)",
            ],
            "governing_law": task.project_metadata.get("jurisdiction", "MI"),
            "venue": f"State of {task.project_metadata.get('jurisdiction', 'Michigan')}",
        },
        "termination": {
            "for_convenience": "Either party with 14 calendar days written notice",
            "for_cause": "Material breach with 7 calendar days cure period",
            "payment_on_termination": "Payment for work completed and accepted prior to termination",
        },
        "change_orders": {
            "process": "Written approval required from both parties",
            "pricing": "Equitable adjustment to contract price and schedule",
            "authority": "Buyer's authorized representative",
        },
    }

    agreement = {
        "request_id": task.request_id,
        "template": template,
        "generated_at": now.isoformat(),
        "status": "draft",
        "parties": {
            "buyer": {
                "role": "General Contractor",
                "note": "To be filled with buyer company details",
            },
            "operator": {
                "robot_id": bid.robot_id,
                "role": "Survey Subcontractor",
                "note": "To be filled with operator company details",
            },
        },
        "terms": terms,
        "task_decomposition": task.task_decomposition,
        "project_metadata": task.project_metadata,
        "signatures": {
            "buyer_signed": False,
            "operator_signed": False,
            "execution_date": None,
        },
        "note": f"Generated from {template} template. Review all terms before execution. This does not constitute a binding agreement until signed by both parties.",
    }

    return agreement


def _get_deliverables(task) -> list[str]:
    """Extract deliverable formats from task spec."""
    cap = task.capability_requirements
    soft = cap.get("soft", {})
    payload = cap.get("payload", {})
    deliverables = soft.get("preferred_deliverables", [])
    if not deliverables:
        deliverables = payload.get("fields", [])
    return deliverables


def _get_accuracy(task) -> dict:
    """Extract accuracy requirements from task spec."""
    cap = task.capability_requirements
    hard = cap.get("hard", {})
    return hard.get("accuracy_required", {})
