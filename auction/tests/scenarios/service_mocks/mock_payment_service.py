"""Mock payment services for end-to-end testing.

Simulates: Plaid bank connection, escrow funding, payment processing,
and operator payout. No real money moves.
"""

from datetime import UTC, datetime
from decimal import Decimal


class MockPlaidConnection:
    """Simulates Plaid bank account linking for ACH transfers."""

    def __init__(self, account_name: str = "Dan's Excavating Operating Account"):
        self.account_name = account_name
        self.account_id = "plaid_acct_test_" + account_name[:8].lower().replace(" ", "_")
        self.routing_number = "072000326"  # Test routing
        self.account_type = "checking"
        self.connected = True

    def initiate_ach_transfer(self, amount: Decimal, memo: str = "") -> dict:
        return {
            "transfer_id": f"ach_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            "amount": str(amount),
            "status": "pending",
            "estimated_arrival": "2-3 business days",
            "source_account": self.account_id,
            "memo": memo,
        }


class MockEscrowAccount:
    """Simulates escrow holding for task payments."""

    def __init__(self):
        self._balances: dict[str, Decimal] = {}
        self._holds: dict[str, dict] = {}

    def fund(self, account_id: str, amount: Decimal, source: str = "ach") -> dict:
        self._balances[account_id] = self._balances.get(account_id, Decimal("0")) + amount
        return {
            "escrow_id": account_id,
            "funded": str(amount),
            "balance": str(self._balances[account_id]),
            "source": source,
        }

    def hold(self, account_id: str, request_id: str, amount: Decimal) -> dict:
        if self._balances.get(account_id, Decimal("0")) < amount:
            return {"error": "Insufficient escrow balance"}
        self._balances[account_id] -= amount
        self._holds[request_id] = {"amount": amount, "account_id": account_id}
        return {
            "hold_id": f"hold_{request_id}",
            "amount": str(amount),
            "remaining_balance": str(self._balances[account_id]),
        }

    def release_to_operator(self, request_id: str, operator_account: str) -> dict:
        hold = self._holds.pop(request_id, None)
        if not hold:
            return {"error": f"No hold found for {request_id}"}
        return {
            "release_id": f"rel_{request_id}",
            "amount": str(hold["amount"]),
            "recipient": operator_account,
            "status": "completed",
        }


class MockOperatorPayout:
    """Simulates operator payment via Stripe Connect or ACH."""

    def __init__(self):
        self._payouts: list[dict] = []

    def payout(self, operator_id: str, amount: Decimal, method: str = "stripe_connect") -> dict:
        record = {
            "payout_id": f"po_{operator_id}_{len(self._payouts)}",
            "operator_id": operator_id,
            "amount": str(amount),
            "method": method,
            "status": "completed",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._payouts.append(record)
        return record


class MockMediationService:
    """Simulates dispute mediation for rejected deliverables."""

    def open_dispute(self, request_id: str, buyer_id: str, operator_id: str, reason: str) -> dict:
        return {
            "dispute_id": f"disp_{request_id}",
            "status": "open",
            "parties": {"buyer": buyer_id, "operator": operator_id},
            "reason": reason,
            "next_step": "Direct negotiation (14 calendar days)",
            "escalation_path": ["negotiation", "mediation", "arbitration"],
        }

    def resolve(self, dispute_id: str, resolution: str, refund_pct: int = 0) -> dict:
        return {
            "dispute_id": dispute_id,
            "status": "resolved",
            "resolution": resolution,
            "refund_percentage": refund_pct,
        }
