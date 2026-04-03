"""Compliance verification for robot operators.

Stores and checks operator compliance documents: FAA Part 107,
insurance COI, PLS license, SAM.gov registration, DOT prequalification,
and DBE certification.

SAM.gov Exclusions API integration: when a SAM_GOV_API_KEY env var is set,
check_sam_exclusion() calls the real SAM.gov v4 API to verify an entity
is not debarred from federal contracting. Without a key, it returns
a WARN status indicating manual verification is needed.

Get an API key: register at https://sam.gov, go to Account Details,
request a Personal API Key (public data).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx

from auction.core import ComplianceRecord

SAM_GOV_API_KEY = os.environ.get("SAM_GOV_API_KEY", "")


VALID_DOC_TYPES = frozenset(
    [
        "faa_part_107",
        "insurance_coi",
        "pls_license",
        "sam_registration",
        "dot_prequalification",
        "dbe_certification",
    ]
)

VALID_STATUSES = frozenset(["VERIFIED", "MISSING", "EXPIRED", "NOT_REQUIRED"])


class ComplianceChecker:
    """Manages operator compliance documents and verification checks."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, ComplianceRecord]] = {}  # robot_id -> {doc_type -> record}

    def upload_document(
        self,
        robot_id: str,
        doc_type: str,
        content: str,
        expires_at: datetime | None = None,
        details: dict | None = None,
    ) -> ComplianceRecord:
        """Store a compliance document for an operator.

        The document is marked as VERIFIED upon upload. In a production system,
        this would trigger async verification against external APIs.
        """
        if doc_type not in VALID_DOC_TYPES:
            raise ValueError(f"doc_type must be one of {sorted(VALID_DOC_TYPES)}, got {doc_type!r}")

        record = ComplianceRecord(
            robot_id=robot_id,
            doc_type=doc_type,
            status="VERIFIED",
            verified_at=datetime.now(UTC),
            expires_at=expires_at,
            details=details or {"content_length": len(content), "uploaded": True},
        )

        if robot_id not in self._records:
            self._records[robot_id] = {}
        self._records[robot_id][doc_type] = record
        return record

    def verify_operator(self, robot_id: str) -> dict:
        """Run all compliance checks for an operator.

        Returns a checklist with status for each document type.
        """
        records = self._records.get(robot_id, {})
        now = datetime.now(UTC)

        checklist = []
        for doc_type in sorted(VALID_DOC_TYPES):
            record = records.get(doc_type)
            if record is None:
                checklist.append(
                    {
                        "doc_type": doc_type,
                        "status": "MISSING",
                        "verified_at": None,
                        "expires_at": None,
                        "details": {},
                    }
                )
            else:
                # Check expiration
                status = record.status
                if record.expires_at is not None and record.expires_at < now:
                    status = "EXPIRED"
                checklist.append(
                    {
                        "doc_type": record.doc_type,
                        "status": status,
                        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
                        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                        "details": record.details,
                    }
                )

        verified_count = sum(1 for c in checklist if c["status"] == "VERIFIED")

        return {
            "robot_id": robot_id,
            "total_checks": len(checklist),
            "verified": verified_count,
            "missing": sum(1 for c in checklist if c["status"] == "MISSING"),
            "expired": sum(1 for c in checklist if c["status"] == "EXPIRED"),
            "compliant": verified_count == len(checklist),
            "checklist": checklist,
        }

    def get_record(self, robot_id: str, doc_type: str) -> ComplianceRecord | None:
        """Get a specific compliance record."""
        return self._records.get(robot_id, {}).get(doc_type)


# ---------------------------------------------------------------------------
# SAM.gov Exclusions API — real federal debarment check
# ---------------------------------------------------------------------------


def check_sam_exclusion(entity_name: str) -> dict:
    """Check if an entity is excluded (debarred) via the SAM.gov Exclusions API.

    Uses the real SAM.gov v4 API when SAM_GOV_API_KEY is set.
    Without a key, returns a WARN result indicating manual verification needed.

    API docs: https://open.gsa.gov/api/exclusions-api/
    Get a key: https://sam.gov → Account Details → Personal API Key

    Returns:
        dict with status (CLEAR, EXCLUDED, WARN, ERROR), details, and source.
    """
    if not SAM_GOV_API_KEY:
        return {
            "status": "WARN",
            "entity_name": entity_name,
            "message": "SAM.gov API key not configured. Set SAM_GOV_API_KEY env var.",
            "source": "not_checked",
            "action": "Register at sam.gov and request a Personal API Key, then set SAM_GOV_API_KEY.",
        }

    url = "https://api.sam.gov/entity-information/v4/exclusions"
    params = {
        "api_key": SAM_GOV_API_KEY,
        "q": entity_name,
        "size": 5,
    }

    try:
        response = httpx.get(url, params=params, timeout=15.0)

        if response.status_code == 404:
            return {
                "status": "ERROR",
                "entity_name": entity_name,
                "message": "SAM.gov API returned 404 — API key may be invalid or expired.",
                "source": "sam.gov",
                "http_status": 404,
            }

        if response.status_code != 200:
            return {
                "status": "ERROR",
                "entity_name": entity_name,
                "message": f"SAM.gov API returned HTTP {response.status_code}",
                "source": "sam.gov",
                "http_status": response.status_code,
            }

        data = response.json()
        total = data.get("totalRecords", 0)
        exclusions = data.get("excludedEntity", [])

        if total == 0 or not exclusions:
            return {
                "status": "CLEAR",
                "entity_name": entity_name,
                "message": f"No exclusions found for '{entity_name}' in SAM.gov",
                "total_records": 0,
                "source": "sam.gov Exclusions API v4 (real)",
            }

        # Found exclusion records — check if any are active
        active = []
        for exc in exclusions:
            actions = exc.get("exclusionActions", {}).get("listOfActions", [])
            for action in actions:
                if action.get("recordStatus") == "Active":
                    active.append(
                        {
                            "entity": exc.get("exclusionIdentification", {}).get("entityName", ""),
                            "type": exc.get("exclusionDetails", {}).get("exclusionType", ""),
                            "agency": exc.get("exclusionDetails", {}).get("excludingAgencyName", ""),
                            "activate_date": action.get("activateDate"),
                            "termination_date": action.get("terminationDate"),
                            "termination_type": action.get("terminationType"),
                        }
                    )

        if active:
            return {
                "status": "EXCLUDED",
                "entity_name": entity_name,
                "message": f"DEBARRED: {len(active)} active exclusion(s) found in SAM.gov",
                "active_exclusions": active,
                "total_records": total,
                "source": "sam.gov Exclusions API v4 (real)",
            }

        return {
            "status": "CLEAR",
            "entity_name": entity_name,
            "message": f"Found {total} record(s) but none are currently active",
            "total_records": total,
            "source": "sam.gov Exclusions API v4 (real)",
        }

    except httpx.TimeoutException:
        return {
            "status": "ERROR",
            "entity_name": entity_name,
            "message": "SAM.gov API request timed out (15s)",
            "source": "sam.gov",
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "entity_name": entity_name,
            "message": f"SAM.gov API error: {str(e)}",
            "source": "sam.gov",
        }
