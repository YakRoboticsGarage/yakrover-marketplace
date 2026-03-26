"""Reputation tracking for robot agents. See PRODUCT_SPEC_V05.md DM-5."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from auction.core import ReputationRecord

VALID_OUTCOMES = frozenset({"completed", "rejected", "abandoned", "cancelled"})


class ReputationTracker:
    """Compute reputation_metadata from task history. See DM-5."""

    def __init__(self, rolling_window_days: int = 30) -> None:
        self.rolling_window_days = rolling_window_days
        self._records: list[ReputationRecord] = []

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        robot_id: str,
        request_id: str,
        outcome: str,
        sla_met: bool,
        timestamp: datetime | None = None,
    ) -> None:
        """Append a task outcome to the history."""
        if outcome not in VALID_OUTCOMES:
            raise ValueError(
                f"Invalid outcome {outcome!r}; must be one of {sorted(VALID_OUTCOMES)}"
            )
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        self._records.append(
            ReputationRecord(
                robot_id=robot_id,
                request_id=request_id,
                outcome=outcome,
                sla_met=sla_met,
                timestamp=timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_reputation(self, robot_id: str) -> dict:
        """Return DM-5 reputation_metadata dict computed from history."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.rolling_window_days)
        records = [
            r
            for r in self._records
            if r.robot_id == robot_id and r.timestamp >= cutoff
        ]

        total = len(records)

        if total == 0:
            return {
                "tasks_completed": 0,
                "completion_rate": 0.5,
                "on_time_rate": 0.0,
                "rejection_rate": 0.0,
                "rolling_window_days": self.rolling_window_days,
            }

        tasks_completed = sum(1 for r in records if r.outcome == "completed")
        completion_rate = tasks_completed / total

        if tasks_completed > 0:
            on_time_rate = (
                sum(
                    1
                    for r in records
                    if r.outcome == "completed" and r.sla_met
                )
                / tasks_completed
            )
        else:
            on_time_rate = 0.0

        rejection_rate = sum(1 for r in records if r.outcome == "rejected") / total

        return {
            "tasks_completed": tasks_completed,
            "completion_rate": completion_rate,
            "on_time_rate": on_time_rate,
            "rejection_rate": rejection_rate,
            "rolling_window_days": self.rolling_window_days,
        }

    def get_all_reputations(self) -> dict[str, dict]:
        """Return reputation dicts for every robot that has at least one record."""
        robot_ids = {r.robot_id for r in self._records}
        return {rid: self.get_reputation(rid) for rid in sorted(robot_ids)}
