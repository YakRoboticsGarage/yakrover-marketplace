"""Legal terms comparison module.

Vertical: construction (ConsensusDocs 750, AIA, anti-indemnity statutes)

Compares operator standard terms vs. GC subcontract terms across 12 dimensions.
Wraps the logic from the legal-terms-compare Claude Code skill.
"""

from __future__ import annotations

# The 12 comparison dimensions from the legal-terms-compare skill
COMPARISON_DIMENSIONS = [
    "indemnification",
    "limitation_of_liability",
    "insurance_requirements",
    "payment_terms",
    "retainage",
    "data_ownership",
    "standard_of_care",
    "consequential_damages",
    "dispute_resolution",
    "termination",
    "change_orders",
    "pls_responsibility",
]

# Michigan anti-indemnity statute reference
ANTI_INDEMNITY_STATES = {
    "MI": {
        "statute": "MCL 691.991",
        "type": "broad_form",
        "note": "Michigan prohibits broad-form indemnification in construction contracts",
    },
    "OH": {"statute": "ORC 2305.31", "type": "broad_form", "note": "Ohio prohibits broad-form indemnification"},
    "AZ": {
        "statute": "ARS 34-226",
        "type": "broad_form",
        "note": "Arizona prohibits broad-form indemnification in construction",
    },
    "TX": {
        "statute": "Chapter 151 CPRC",
        "type": "broad_form",
        "note": "Texas prohibits broad-form indemnification in construction",
    },
}

# Marketplace baseline terms (ConsensusDocs 750 aligned)
BASELINE_TERMS = {
    "indemnification": "Intermediate form — each party indemnifies for own negligence",
    "limitation_of_liability": "1x contract value",
    "insurance_requirements": "CGL $1M/$2M, Professional E&O $1M/$2M, Aviation $5M",
    "payment_terms": "Net 30 from delivery acceptance",
    "retainage": "10% until final acceptance",
    "data_ownership": "Client owns deliverables upon payment; operator retains methodology",
    "standard_of_care": "Professional standard of care for licensed surveyors",
    "consequential_damages": "Mutual waiver of consequential damages",
    "dispute_resolution": "Negotiation → mediation → binding arbitration",
    "termination": "Either party with 14 days notice; payment for work completed",
    "change_orders": "Written approval required; equitable adjustment to price and schedule",
    "pls_responsibility": "Operator provides PLS supervision; stamps deliverables",
}


def compare_terms(
    operator_terms: str,
    gc_terms: str,
    project_state: str = "MI",
) -> dict:
    """Compare operator and GC terms across 12 dimensions.

    Returns a structured comparison with deviations flagged and
    risk assessments for each dimension.
    """
    op_lower = operator_terms.lower()
    gc_lower = gc_terms.lower()

    comparisons = []
    flags = []

    for dim in COMPARISON_DIMENSIONS:
        baseline = BASELINE_TERMS[dim]
        op_clause = _find_clause(op_lower, dim)
        gc_clause = _find_clause(gc_lower, dim)

        deviation = "none"
        risk = "low"
        note = f"Baseline: {baseline}"

        # Check for red flags by dimension
        if dim == "indemnification":
            if "broad form" in gc_lower or "hold harmless" in gc_lower:
                anti_indem = ANTI_INDEMNITY_STATES.get(project_state)
                if anti_indem:
                    deviation = "gc_exceeds_baseline"
                    risk = "high"
                    note = f"GC terms may contain broad-form indemnification. {anti_indem['note']} ({anti_indem['statute']})"
                    flags.append(f"INDEMNIFICATION: Broad-form language detected — may violate {anti_indem['statute']}")

        elif dim == "limitation_of_liability":
            if "unlimited" in gc_lower or "no limit" in gc_lower:
                deviation = "gc_exceeds_baseline"
                risk = "high"
                note = "GC terms may remove limitation of liability"
                flags.append("LOL: Unlimited liability language detected")

        elif dim == "payment_terms":
            if "net 60" in gc_lower or "net 90" in gc_lower or "pay when paid" in gc_lower:
                deviation = "gc_exceeds_baseline"
                risk = "medium"
                note = "GC payment terms exceed baseline Net 30"
                flags.append("PAYMENT: Extended payment terms or pay-when-paid clause detected")

        elif dim == "retainage":
            if "20%" in gc_lower or "15%" in gc_lower:
                deviation = "gc_exceeds_baseline"
                risk = "medium"
                note = "GC retainage exceeds baseline 10%"

        elif dim == "consequential_damages":
            if "consequential" not in gc_lower or "waiv" not in gc_lower:
                deviation = "gc_missing_protection"
                risk = "medium"
                note = "GC terms may not include mutual waiver of consequential damages"

        elif dim == "data_ownership":
            if "all data" in gc_lower and "methodology" in gc_lower:
                deviation = "gc_exceeds_baseline"
                risk = "medium"
                note = "GC may claim ownership of operator methodology, not just deliverables"

        elif dim == "dispute_resolution":
            if "litigation" in gc_lower and "arbitration" not in gc_lower:
                deviation = "gc_differs"
                risk = "low"
                note = "GC terms specify litigation instead of arbitration"

        comparisons.append(
            {
                "dimension": dim,
                "baseline": baseline,
                "operator_clause_found": op_clause is not None,
                "gc_clause_found": gc_clause is not None,
                "deviation": deviation,
                "risk": risk,
                "note": note,
            }
        )

    high_risk = sum(1 for c in comparisons if c["risk"] == "high")
    medium_risk = sum(1 for c in comparisons if c["risk"] == "medium")

    return {
        "dimensions_compared": len(comparisons),
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": sum(1 for c in comparisons if c["risk"] == "low"),
        "flags": flags,
        "overall_risk": "high" if high_risk > 0 else "medium" if medium_risk > 0 else "low",
        "project_state": project_state,
        "anti_indemnity_statute": ANTI_INDEMNITY_STATES.get(project_state),
        "comparisons": comparisons,
        "note": "Legal terms comparison is automated analysis. It does not constitute legal advice. Attorney review recommended before execution.",
    }


def _find_clause(text: str, dimension: str) -> str | None:
    """Find a clause related to a dimension in text."""
    keywords = {
        "indemnification": ["indemnif", "hold harmless", "defend"],
        "limitation_of_liability": ["limitation of liability", "limit of liability", "liability cap"],
        "insurance_requirements": ["insurance", "coverage", "cgl", "e&o"],
        "payment_terms": ["payment", "net 30", "net 60", "invoice"],
        "retainage": ["retainage", "retention", "holdback"],
        "data_ownership": ["data ownership", "intellectual property", "deliverables"],
        "standard_of_care": ["standard of care", "professional standard", "workmanlike"],
        "consequential_damages": ["consequential", "indirect", "special damages"],
        "dispute_resolution": ["dispute", "arbitration", "mediation", "litigation"],
        "termination": ["terminat", "cancel"],
        "change_orders": ["change order", "modification", "amendment"],
        "pls_responsibility": ["surveyor", "pls", "licensed professional"],
    }
    for kw in keywords.get(dimension, []):
        if kw in text:
            return kw
    return None
