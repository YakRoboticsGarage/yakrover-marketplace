"""SQLite-backed persistent store for the robot task auction.

Provides both async (TaskStore) and sync (SyncTaskStore) CRUD operations
for tasks, bids, wallet balances, ledger entries, and reputation records.

TaskStore uses aiosqlite for non-blocking I/O.
SyncTaskStore uses stdlib sqlite3 for use in synchronous engine code.

Both use WAL journal mode and the same schema/serialization.

All dict/Decimal/datetime columns are stored as JSON text with a custom
serializer that round-trips Decimal and datetime values exactly.

See PRODUCT_SPEC_V10.md Section 5 and BUILD_PLAN_V10.md Track A.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import aiosqlite

# ---------------------------------------------------------------------------
# JSON helpers — Decimal and datetime round-trip safely
# ---------------------------------------------------------------------------


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for types that stdlib json cannot handle."""
    if isinstance(obj, Decimal):
        return {"__decimal__": str(obj)}
    if isinstance(obj, datetime):
        return {"__datetime__": obj.isoformat()}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _json_object_hook(dct: dict) -> Any:
    """Reconstruct Decimal and datetime from tagged dicts."""
    if "__decimal__" in dct:
        return Decimal(dct["__decimal__"])
    if "__datetime__" in dct:
        s = dct["__datetime__"]
        # Handle both aware and naive ISO strings
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    return dct


def _dumps(obj: Any) -> str:
    """Serialize *obj* to JSON with Decimal/datetime support."""
    return json.dumps(obj, default=_json_serializer)


def _loads(s: str | None) -> Any:
    """Deserialize JSON with Decimal/datetime support.  Returns None for None input."""
    if s is None:
        return None
    return json.loads(s, object_hook=_json_object_hook)


# ---------------------------------------------------------------------------
# Terminal task states — tasks in these states are not "active"
# ---------------------------------------------------------------------------

_TERMINAL_STATES = frozenset({"settled", "withdrawn"})


# ---------------------------------------------------------------------------
# TaskStore
# ---------------------------------------------------------------------------


class TaskStore:
    """Async SQLite persistence layer for the auction system.

    Parameters
    ----------
    db_path : str
        File path for the SQLite database, or ``":memory:"`` for an
        ephemeral in-memory database (useful in tests).
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def _conn(self) -> aiosqlite.Connection:
        """Return the (lazily-opened) connection."""
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode=WAL")
        return self._db

    async def close(self) -> None:
        """Close the underlying database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create all tables and indexes if they do not already exist.

        Safe to call multiple times (fully idempotent).
        """
        db = await self._conn()

        await db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                request_id TEXT PRIMARY KEY,
                task_json TEXT NOT NULL,
                state TEXT NOT NULL,
                winning_bid_json TEXT,
                delivery_json TEXT,
                bids_json TEXT DEFAULT '[]',
                bid_round INTEGER DEFAULT 1,
                previous_winners_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                robot_id TEXT NOT NULL,
                bid_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wallet_balances (
                wallet_id TEXT PRIMARY KEY,
                balance TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ledger_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT,
                wallet_id TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                amount TEXT NOT NULL,
                balance_after TEXT NOT NULL,
                request_id TEXT,
                note TEXT DEFAULT '',
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reputation_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                sla_met INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_state
                ON tasks(state);
            CREATE INDEX IF NOT EXISTS idx_bids_request
                ON bids(request_id);
            CREATE INDEX IF NOT EXISTS idx_ledger_wallet
                ON ledger_entries(wallet_id);
            CREATE INDEX IF NOT EXISTS idx_ledger_request
                ON ledger_entries(request_id);
            CREATE INDEX IF NOT EXISTS idx_reputation_robot
                ON reputation_records(robot_id);

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                request_id TEXT,
                actor_id TEXT,
                actor_role TEXT DEFAULT 'system',
                data_json TEXT DEFAULT '{}',
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_events_request
                ON events(request_id);
            CREATE INDEX IF NOT EXISTS idx_events_type
                ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_actor
                ON events(actor_id);
            CREATE INDEX IF NOT EXISTS idx_events_ts
                ON events(timestamp);
        """)

        await db.commit()

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    async def save_task(
        self,
        request_id: str,
        task_dict: dict,
        state: str,
        bid_round: int = 1,
        *,
        winning_bid_dict: dict | None = None,
        delivery_dict: dict | None = None,
        bids_list: list[dict] | None = None,
        previous_winners: list[str] | None = None,
    ) -> None:
        """Upsert a task record.

        Inserts if the *request_id* does not exist, otherwise updates all
        mutable columns.
        """
        db = await self._conn()
        now = datetime.now(UTC).isoformat()

        await db.execute(
            """
            INSERT INTO tasks
                (request_id, task_json, state, winning_bid_json, delivery_json,
                 bids_json, bid_round, previous_winners_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(request_id) DO UPDATE SET
                task_json = excluded.task_json,
                state = excluded.state,
                winning_bid_json = excluded.winning_bid_json,
                delivery_json = excluded.delivery_json,
                bids_json = excluded.bids_json,
                bid_round = excluded.bid_round,
                previous_winners_json = excluded.previous_winners_json,
                updated_at = excluded.updated_at
            """,
            (
                request_id,
                _dumps(task_dict),
                state,
                _dumps(winning_bid_dict),
                _dumps(delivery_dict),
                _dumps(bids_list or []),
                bid_round,
                _dumps(previous_winners or []),
                now,
                now,
            ),
        )
        await db.commit()

    async def save_bid(self, bid_dict: dict) -> None:
        """Insert a bid record into the bids table."""
        db = await self._conn()
        now = datetime.now(UTC).isoformat()

        await db.execute(
            "INSERT INTO bids (request_id, robot_id, bid_json, created_at) VALUES (?, ?, ?, ?)",
            (
                bid_dict.get("request_id", ""),
                bid_dict.get("robot_id", ""),
                _dumps(bid_dict),
                now,
            ),
        )
        await db.commit()

    async def save_delivery(self, request_id: str, delivery_dict: dict) -> None:
        """Update the task row with delivery data."""
        db = await self._conn()
        now = datetime.now(UTC).isoformat()

        await db.execute(
            "UPDATE tasks SET delivery_json = ?, updated_at = ? WHERE request_id = ?",
            (_dumps(delivery_dict), now, request_id),
        )
        await db.commit()

    async def update_state(self, request_id: str, state: str) -> None:
        """Update the state column of an existing task."""
        db = await self._conn()
        now = datetime.now(UTC).isoformat()

        await db.execute(
            "UPDATE tasks SET state = ?, updated_at = ? WHERE request_id = ?",
            (state, now, request_id),
        )
        await db.commit()

    async def load_task(self, request_id: str) -> dict | None:
        """Load a full task record by *request_id*, or ``None`` if missing."""
        db = await self._conn()

        async with db.execute("SELECT * FROM tasks WHERE request_id = ?", (request_id,)) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        return _row_to_task_dict(row)

    async def load_active_tasks(self) -> list[dict]:
        """Return all tasks whose state is not in a terminal state."""
        db = await self._conn()
        placeholders = ",".join("?" for _ in _TERMINAL_STATES)

        async with db.execute(
            f"SELECT * FROM tasks WHERE state NOT IN ({placeholders})",
            tuple(_TERMINAL_STATES),
        ) as cursor:
            rows = await cursor.fetchall()

        return [_row_to_task_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Wallet persistence
    # ------------------------------------------------------------------

    async def save_wallet_balance(self, wallet_id: str, balance: Decimal) -> None:
        """Upsert a wallet balance."""
        db = await self._conn()
        now = datetime.now(UTC).isoformat()

        await db.execute(
            """
            INSERT INTO wallet_balances (wallet_id, balance, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(wallet_id) DO UPDATE SET
                balance = excluded.balance,
                updated_at = excluded.updated_at
            """,
            (wallet_id, str(balance), now),
        )
        await db.commit()

    async def load_wallet_balances(self) -> dict[str, Decimal]:
        """Return all wallet balances as ``{wallet_id: Decimal}``."""
        db = await self._conn()

        async with db.execute("SELECT wallet_id, balance FROM wallet_balances") as cur:
            rows = await cur.fetchall()

        return {row["wallet_id"]: Decimal(row["balance"]) for row in rows}

    async def save_ledger_entry(self, entry_dict: dict) -> None:
        """Insert a single ledger entry."""
        db = await self._conn()

        await db.execute(
            """
            INSERT INTO ledger_entries
                (entry_id, wallet_id, entry_type, amount, balance_after,
                 request_id, note, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_dict.get("entry_id", ""),
                entry_dict["wallet_id"],
                entry_dict["entry_type"],
                str(entry_dict["amount"]),
                str(entry_dict["balance_after"]),
                entry_dict.get("request_id", ""),
                entry_dict.get("note", ""),
                entry_dict.get("timestamp", datetime.now(UTC)).isoformat()
                if isinstance(entry_dict.get("timestamp"), datetime)
                else str(entry_dict.get("timestamp", "")),
            ),
        )
        await db.commit()

    async def load_ledger_entries(
        self,
        wallet_id: str | None = None,
        request_id: str | None = None,
    ) -> list[dict]:
        """Load ledger entries, optionally filtered by wallet and/or request."""
        db = await self._conn()

        query = "SELECT * FROM ledger_entries"
        conditions: list[str] = []
        params: list[str] = []

        if wallet_id is not None:
            conditions.append("wallet_id = ?")
            params.append(wallet_id)
        if request_id is not None:
            conditions.append("request_id = ?")
            params.append(request_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id"

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "entry_id": row["entry_id"],
                "wallet_id": row["wallet_id"],
                "entry_type": row["entry_type"],
                "amount": Decimal(row["amount"]),
                "balance_after": Decimal(row["balance_after"]),
                "request_id": row["request_id"],
                "note": row["note"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Reputation persistence
    # ------------------------------------------------------------------

    async def save_reputation_record(self, record_dict: dict) -> None:
        """Insert a reputation outcome record."""
        db = await self._conn()

        ts = record_dict.get("timestamp", datetime.now(UTC))
        ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)

        await db.execute(
            """
            INSERT INTO reputation_records
                (robot_id, request_id, outcome, sla_met, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record_dict["robot_id"],
                record_dict["request_id"],
                record_dict["outcome"],
                int(record_dict["sla_met"]),
                ts_str,
            ),
        )
        await db.commit()

    async def load_reputation_records(self, robot_id: str | None = None) -> list[dict]:
        """Load reputation records, optionally filtered by *robot_id*."""
        db = await self._conn()

        if robot_id is not None:
            query = "SELECT * FROM reputation_records WHERE robot_id = ? ORDER BY id"
            params: tuple = (robot_id,)
        else:
            query = "SELECT * FROM reputation_records ORDER BY id"
            params = ()

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "robot_id": row["robot_id"],
                "request_id": row["request_id"],
                "outcome": row["outcome"],
                "sla_met": bool(row["sla_met"]),
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_task_dict(row) -> dict:
    """Convert a tasks table row to a plain dict with deserialized JSON.

    Works with both aiosqlite.Row and sqlite3.Row objects.
    """
    return {
        "request_id": row["request_id"],
        "task": _loads(row["task_json"]),
        "state": row["state"],
        "winning_bid": _loads(row["winning_bid_json"]),
        "delivery": _loads(row["delivery_json"]),
        "bids": _loads(row["bids_json"]),
        "bid_round": row["bid_round"],
        "previous_winners": _loads(row["previous_winners_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------------------------
# Schema DDL — shared between async and sync stores
# ---------------------------------------------------------------------------

_SCHEMA_DDL = """
    CREATE TABLE IF NOT EXISTS tasks (
        request_id TEXT PRIMARY KEY,
        task_json TEXT NOT NULL,
        state TEXT NOT NULL,
        winning_bid_json TEXT,
        delivery_json TEXT,
        bids_json TEXT DEFAULT '[]',
        bid_round INTEGER DEFAULT 1,
        previous_winners_json TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        robot_id TEXT NOT NULL,
        bid_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS wallet_balances (
        wallet_id TEXT PRIMARY KEY,
        balance TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ledger_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id TEXT,
        wallet_id TEXT NOT NULL,
        entry_type TEXT NOT NULL,
        amount TEXT NOT NULL,
        balance_after TEXT NOT NULL,
        request_id TEXT,
        note TEXT DEFAULT '',
        timestamp TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reputation_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        robot_id TEXT NOT NULL,
        request_id TEXT NOT NULL,
        outcome TEXT NOT NULL,
        sla_met INTEGER NOT NULL,
        timestamp TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_tasks_state
        ON tasks(state);
    CREATE INDEX IF NOT EXISTS idx_bids_request
        ON bids(request_id);
    CREATE INDEX IF NOT EXISTS idx_ledger_wallet
        ON ledger_entries(wallet_id);
    CREATE INDEX IF NOT EXISTS idx_ledger_request
        ON ledger_entries(request_id);
    CREATE INDEX IF NOT EXISTS idx_reputation_robot
        ON reputation_records(robot_id);

    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        request_id TEXT,
        actor_id TEXT,
        actor_role TEXT DEFAULT 'system',
        data_json TEXT DEFAULT '{}',
        timestamp TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_events_request
        ON events(request_id);
    CREATE INDEX IF NOT EXISTS idx_events_type
        ON events(event_type);
    CREATE INDEX IF NOT EXISTS idx_events_actor
        ON events(actor_id);
    CREATE INDEX IF NOT EXISTS idx_events_ts
        ON events(timestamp);
"""


# ---------------------------------------------------------------------------
# SyncTaskStore — synchronous sqlite3 store for use in AuctionEngine
# ---------------------------------------------------------------------------


class SyncTaskStore:
    """Synchronous SQLite persistence layer for the auction engine.

    Uses stdlib ``sqlite3`` so it can be called from synchronous code
    (e.g. ``AuctionEngine._transition``).  Provides the same task CRUD
    as :class:`TaskStore` but without ``async``/``await``.

    Parameters
    ----------
    db_path : str
        File path for the SQLite database, or ``":memory:"`` for an
        ephemeral in-memory database (useful in tests).
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._db: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        """Return the (lazily-opened) connection."""
        if self._db is None:
            self._db = sqlite3.connect(self.db_path)
            self._db.row_factory = sqlite3.Row
            self._db.execute("PRAGMA journal_mode=WAL")
        return self._db

    def close(self) -> None:
        """Close the underlying database connection."""
        if self._db is not None:
            self._db.close()
            self._db = None

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Create all tables and indexes if they do not already exist."""
        db = self._conn()
        db.executescript(_SCHEMA_DDL)
        db.commit()

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    def save_task(
        self,
        request_id: str,
        task_dict: dict,
        state: str,
        bid_round: int = 1,
        *,
        winning_bid_dict: dict | None = None,
        delivery_dict: dict | None = None,
        bids_list: list[dict] | None = None,
        previous_winners: list[str] | None = None,
    ) -> None:
        """Upsert a task record (synchronous)."""
        db = self._conn()
        now = datetime.now(UTC).isoformat()

        db.execute(
            """
            INSERT INTO tasks
                (request_id, task_json, state, winning_bid_json, delivery_json,
                 bids_json, bid_round, previous_winners_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(request_id) DO UPDATE SET
                task_json = excluded.task_json,
                state = excluded.state,
                winning_bid_json = excluded.winning_bid_json,
                delivery_json = excluded.delivery_json,
                bids_json = excluded.bids_json,
                bid_round = excluded.bid_round,
                previous_winners_json = excluded.previous_winners_json,
                updated_at = excluded.updated_at
            """,
            (
                request_id,
                _dumps(task_dict),
                state,
                _dumps(winning_bid_dict),
                _dumps(delivery_dict),
                _dumps(bids_list or []),
                bid_round,
                _dumps(previous_winners or []),
                now,
                now,
            ),
        )
        db.commit()

    def load_task(self, request_id: str) -> dict | None:
        """Load a full task record by *request_id*, or ``None`` if missing."""
        db = self._conn()
        cursor = db.execute("SELECT * FROM tasks WHERE request_id = ?", (request_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_task_dict(row)

    def load_active_tasks(self) -> list[dict]:
        """Return all tasks whose state is not in a terminal state."""
        db = self._conn()
        placeholders = ",".join("?" for _ in _TERMINAL_STATES)
        cursor = db.execute(
            f"SELECT * FROM tasks WHERE state NOT IN ({placeholders})",
            tuple(_TERMINAL_STATES),
        )
        rows = cursor.fetchall()
        return [_row_to_task_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    def save_event(self, event: dict) -> None:
        """Persist a structured event to the events table."""
        import json as _json

        db = self._conn()
        db.execute(
            """INSERT INTO events
               (event_id, event_type, request_id, actor_id, actor_role, data_json, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                event["event_id"],
                event["event_type"],
                event.get("request_id"),
                event.get("actor_id"),
                event.get("actor_role", "system"),
                _json.dumps(event.get("data", {})),
                event["timestamp"],
            ),
        )
        db.commit()

    def query_events(
        self,
        *,
        request_id: str | None = None,
        actor_id: str | None = None,
        event_type: str | None = None,
        since: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Query events with optional filters."""
        import json as _json

        db = self._conn()
        clauses: list[str] = []
        params: list[str] = []

        if request_id:
            clauses.append("request_id = ?")
            params.append(request_id)
        if actor_id:
            clauses.append("actor_id = ?")
            params.append(actor_id)
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if since:
            clauses.append("timestamp > ?")
            params.append(since)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cursor = db.execute(
            f"SELECT * FROM events {where} ORDER BY timestamp ASC LIMIT ?",
            (*params, limit),
        )
        rows = cursor.fetchall()
        return [
            {
                "event_id": r["event_id"],
                "event_type": r["event_type"],
                "request_id": r["request_id"],
                "actor_id": r["actor_id"],
                "actor_role": r["actor_role"],
                "data": _json.loads(r["data_json"]),
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]
