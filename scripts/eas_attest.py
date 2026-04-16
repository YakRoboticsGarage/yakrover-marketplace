#!/usr/bin/env python3
"""
EAS (Ethereum Attestation Service) robot attestation tool.

Registers a schema and creates attestations for robots on Base Sepolia.

Schema: "uint256 agentId, uint256 chainId, string fleetType, string fleetName, string attestorRole, string notes"

Fleet taxonomy:
  live_production  — Real physical robots (Tumbller, future real operators)
  demo_fleet       — The 100-robot test fleet for demo/testing
  legacy           — Old FakeRover-Berlin etc. to be filtered out

Attestor roles:
  platform_admin   — YAK Robotics platform team
  operator         — Robot operator self-attestation
  auditor          — Third-party verification
  community        — Community member vouching

Usage:
  python scripts/eas_attest.py register-schema              # One-time schema registration
  python scripts/eas_attest.py attest --agent-id 4292 --fleet demo_fleet
  python scripts/eas_attest.py attest-batch --fleet demo_fleet   # All is_test robots
  python scripts/eas_attest.py revoke --uid 0xabc123...
  python scripts/eas_attest.py list --fleet demo_fleet

Requires .env with SIGNER_PVT_KEY.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import eth_abi
import httpx
from dotenv import load_dotenv
from web3 import Web3

# ── Config ────────────────────────────────────────────────────────

from auction.contracts import (
    EAS_ADDRESS,
    EAS_SCHEMA_REGISTRY as SCHEMA_REGISTRY,
    IDENTITY_REGISTRY,
    RPC_URLS,
    SUBGRAPH_URLS,
    YAKROVER_HEX,
)

CHAIN_ID = 84532
RPC_URL = RPC_URLS[CHAIN_ID]
SUBGRAPH_URL = SUBGRAPH_URLS[CHAIN_ID]

# Schema string — defines what data is in each attestation
SCHEMA_STRING = "uint256 agentId,uint256 chainId,string fleetType,string fleetName,string attestorRole,string notes"

# Valid fleet types
FLEET_TYPES = {
    "live_production": "Real physical robot verified operational",
    "demo_fleet": "Test/demo robot for marketplace demonstration",
    "legacy": "Deprecated robot, should be filtered from active discovery",
}

# Valid attestor roles
ATTESTOR_ROLES = ["platform_admin", "operator", "auditor", "community"]

# Schema registry ABI (just register and getSchema)
SCHEMA_REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "schema", "type": "string"},
            {"name": "resolver", "type": "address"},
            {"name": "revocable", "type": "bool"},
        ],
        "name": "register",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "uid", "type": "bytes32"}],
        "name": "getSchema",
        "outputs": [
            {
                "components": [
                    {"name": "uid", "type": "bytes32"},
                    {"name": "resolver", "type": "address"},
                    {"name": "revocable", "type": "bool"},
                    {"name": "schema", "type": "string"},
                ],
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

# EAS ABI (attest, revoke, getAttestation)
EAS_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "schema", "type": "bytes32"},
                    {
                        "components": [
                            {"name": "recipient", "type": "address"},
                            {"name": "expirationTime", "type": "uint64"},
                            {"name": "revocable", "type": "bool"},
                            {"name": "refUID", "type": "bytes32"},
                            {"name": "data", "type": "bytes"},
                            {"name": "value", "type": "uint256"},
                        ],
                        "name": "data",
                        "type": "tuple",
                    },
                ],
                "name": "request",
                "type": "tuple",
            }
        ],
        "name": "attest",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"name": "schema", "type": "bytes32"},
                    {
                        "components": [
                            {"name": "uid", "type": "bytes32"},
                            {"name": "value", "type": "uint256"},
                        ],
                        "name": "data",
                        "type": "tuple",
                    },
                ],
                "name": "request",
                "type": "tuple",
            }
        ],
        "name": "revoke",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
]

# State file for tracking schema UID
STATE_FILE = Path(__file__).resolve().parent.parent / ".eas_state.json"


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Schema registration ──────────────────────────────────────────


def register_schema(w3, signer_key):
    """Register the attestation schema on EAS. One-time operation."""
    state = load_state()
    if state.get("schema_uid"):
        print(f"Schema already registered: {state['schema_uid']}")
        print(f"Schema: {SCHEMA_STRING}")
        return state["schema_uid"]

    registry = w3.eth.contract(
        address=Web3.to_checksum_address(SCHEMA_REGISTRY), abi=SCHEMA_REGISTRY_ABI
    )
    account = w3.eth.account.from_key(signer_key)

    print(f"Registering schema: {SCHEMA_STRING}")
    print(f"  Resolver: none (0x0)")
    print(f"  Revocable: true")

    tx = registry.functions.register(
        SCHEMA_STRING,
        "0x0000000000000000000000000000000000000000",  # no resolver
        True,  # revocable
    ).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gasPrice": w3.eth.gas_price,
            "chainId": CHAIN_ID,
        }
    )
    signed = w3.eth.account.sign_transaction(tx, signer_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    if receipt["status"] != 1:
        print("FAILED — tx reverted")
        return None

    # Extract schema UID from Registered event
    # event Registered(bytes32 indexed uid, address indexed registerer, SchemaRecord schema)
    schema_uid = None
    for log in receipt["logs"]:
        if log["address"].lower() == SCHEMA_REGISTRY.lower() and len(log["topics"]) > 1:
            schema_uid = "0x" + log["topics"][1].hex()
            break

    if not schema_uid:
        print("WARNING: could not extract schema UID from logs. Check EAS explorer.")
        schema_uid = "unknown"
    else:
        print(f"Schema UID: {schema_uid}")
        print(f"Explorer: https://base-sepolia.easscan.org/schema/view/{schema_uid}")

    state["schema_uid"] = schema_uid
    state["schema_string"] = SCHEMA_STRING
    state["registered_at"] = time.time()
    state["registered_by"] = account.address
    state["chain_id"] = CHAIN_ID
    save_state(state)

    print(f"Saved to {STATE_FILE}")
    return schema_uid


# ── Create attestation ────────────────────────────────────────────


def create_attestation(
    w3, signer_key, schema_uid, agent_id, chain_id, fleet_type, fleet_name,
    attestor_role="platform_admin", notes="", recipient="0x0000000000000000000000000000000000000000",
):
    """Create an EAS attestation for a robot."""
    eas = w3.eth.contract(address=Web3.to_checksum_address(EAS_ADDRESS), abi=EAS_ABI)
    account = w3.eth.account.from_key(signer_key)

    # Encode attestation data
    encoded_data = eth_abi.encode(
        ["uint256", "uint256", "string", "string", "string", "string"],
        [agent_id, chain_id, fleet_type, fleet_name, attestor_role, notes],
    )

    tx = eas.functions.attest(
        (
            bytes.fromhex(schema_uid[2:]),  # schema UID
            (
                Web3.to_checksum_address(recipient),  # recipient
                0,  # expirationTime (0 = no expiry)
                True,  # revocable
                b"\x00" * 32,  # refUID (no reference)
                encoded_data,  # data
                0,  # value
            ),
        )
    ).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gasPrice": w3.eth.gas_price,
            "chainId": CHAIN_ID,
            "value": 0,
        }
    )

    signed = w3.eth.account.sign_transaction(tx, signer_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    if receipt["status"] != 1:
        return None

    # Extract attestation UID from Attested event
    # event Attested(address indexed recipient, address indexed attester, bytes32 uid, bytes32 indexed schemaUID)
    # uid is in the data field (non-indexed)
    uid = None
    for log in receipt["logs"]:
        if log["address"].lower() == EAS_ADDRESS.lower() and len(log["data"]) >= 32:
            uid = "0x" + log["data"].hex()[:64]
            break
    if not uid:
        uid = "unknown"

    return uid


# ── Batch attestation ─────────────────────────────────────────────


def get_fleet_robots(fleet_filter="is_test"):
    """Get robot agent IDs from subgraph."""
    query = (
        '{ agentMetadata_collection(where: {key: "fleet_provider", value: "'
        + YAKROVER_HEX
        + '"}, first: 200) { agent { agentId registrationFile { name } metadata(first: 20) { key value } } } }'
    )
    resp = httpx.post(SUBGRAPH_URL, json={"query": query}, timeout=10.0)
    data = resp.json()
    robots = []

    def decode_hex(v):
        if not v:
            return v
        try:
            h = v[2:] if v.startswith("0x") else v
            if len(h) % 2:
                return v
            d = bytes.fromhex(h).decode("utf-8", errors="replace")
            return d if all(0x20 <= ord(c) <= 0x7E for c in d) else v
        except:
            return v

    for entry in data.get("data", {}).get("agentMetadata_collection", []):
        agent = entry.get("agent", {})
        rf = agent.get("registrationFile") or {}
        meta = {m["key"]: decode_hex(m["value"]) for m in agent.get("metadata", [])}

        if fleet_filter == "is_test" and meta.get("is_test") != "true":
            continue
        if fleet_filter == "all":
            pass

        robots.append({
            "agent_id": int(agent["agentId"]),
            "name": rf.get("name", "?"),
            "is_test": meta.get("is_test") == "true",
        })

    return robots


def attest_batch(w3, signer_key, schema_uid, fleet_type, fleet_name, notes=""):
    """Attest all robots matching the fleet filter."""
    robots = get_fleet_robots("is_test" if fleet_type == "demo_fleet" else "all")
    print(f"Found {len(robots)} robots to attest as '{fleet_type}' in '{fleet_name}'")

    results = []
    for i, robot in enumerate(robots):
        print(f"[{i+1}/{len(robots)}] #{robot['agent_id']} {robot['name']:25s} ...", end=" ", flush=True)
        try:
            uid = create_attestation(
                w3, signer_key, schema_uid,
                agent_id=robot["agent_id"],
                chain_id=CHAIN_ID,
                fleet_type=fleet_type,
                fleet_name=fleet_name,
                attestor_role="platform_admin",
                notes=notes,
            )
            if uid:
                print(f"✓ {uid[:18]}...")
                results.append({"agent_id": robot["agent_id"], "name": robot["name"], "uid": uid})
            else:
                print("FAIL (tx reverted)")
        except Exception as e:
            print(f"FAIL: {str(e)[:80]}")
        time.sleep(3)

    # Save attestation log
    log_path = Path(__file__).resolve().parent.parent / "eas_attestation_log.json"
    existing = []
    if log_path.exists():
        with open(log_path) as f:
            existing = json.load(f)
    existing.extend(results)
    with open(log_path, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"\n{len(results)}/{len(robots)} attested. Log: {log_path}")
    return results


# ── Main ──────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="EAS robot attestation tool")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("register-schema", help="Register attestation schema (one-time)")

    attest_p = sub.add_parser("attest", help="Attest a single robot")
    attest_p.add_argument("--agent-id", type=int, required=True)
    attest_p.add_argument("--fleet", choices=FLEET_TYPES.keys(), required=True)
    attest_p.add_argument("--fleet-name", default="yakrover-demo-100")
    attest_p.add_argument("--notes", default="")

    batch_p = sub.add_parser("attest-batch", help="Attest all robots in a fleet")
    batch_p.add_argument("--fleet", choices=FLEET_TYPES.keys(), required=True)
    batch_p.add_argument("--fleet-name", default="yakrover-demo-100")
    batch_p.add_argument("--notes", default="")

    revoke_p = sub.add_parser("revoke", help="Revoke an attestation")
    revoke_p.add_argument("--uid", required=True)

    sub.add_parser("info", help="Show schema and attestation info")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")
    signer_key = os.environ.get("SIGNER_PVT_KEY")
    if not signer_key:
        print("ERROR: SIGNER_PVT_KEY not set")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    if args.command == "register-schema":
        register_schema(w3, signer_key)

    elif args.command == "attest":
        state = load_state()
        schema_uid = state.get("schema_uid")
        if not schema_uid:
            print("No schema registered. Run: register-schema first")
            sys.exit(1)
        uid = create_attestation(
            w3, signer_key, schema_uid,
            agent_id=args.agent_id, chain_id=CHAIN_ID,
            fleet_type=args.fleet, fleet_name=args.fleet_name,
            notes=args.notes,
        )
        print(f"Attestation UID: {uid}")

    elif args.command == "attest-batch":
        state = load_state()
        schema_uid = state.get("schema_uid")
        if not schema_uid:
            print("No schema registered. Run: register-schema first")
            sys.exit(1)
        attest_batch(w3, signer_key, schema_uid, args.fleet, args.fleet_name, args.notes)

    elif args.command == "revoke":
        state = load_state()
        schema_uid = state.get("schema_uid")
        if not schema_uid:
            print("No schema registered.")
            sys.exit(1)
        eas = w3.eth.contract(address=Web3.to_checksum_address(EAS_ADDRESS), abi=EAS_ABI)
        account = w3.eth.account.from_key(signer_key)
        tx = eas.functions.revoke(
            (bytes.fromhex(schema_uid[2:]), (bytes.fromhex(args.uid[2:]), 0))
        ).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gasPrice": w3.eth.gas_price,
            "chainId": CHAIN_ID,
            "value": 0,
        })
        signed = w3.eth.account.sign_transaction(tx, signer_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        print(f"Revoked: {'OK' if receipt['status'] == 1 else 'FAILED'}")

    elif args.command == "info":
        state = load_state()
        print("EAS Attestation State:")
        print(f"  Schema UID: {state.get('schema_uid', 'not registered')}")
        print(f"  Schema: {state.get('schema_string', 'n/a')}")
        print(f"  Chain: {state.get('chain_id', 'n/a')}")
        print(f"  Registered by: {state.get('registered_by', 'n/a')}")
        print(f"\nFleet types:")
        for ft, desc in FLEET_TYPES.items():
            print(f"  {ft}: {desc}")
        print(f"\nAttestor roles: {ATTESTOR_ROLES}")
        print(f"\nEAS explorer: https://base-sepolia.easscan.org")


if __name__ == "__main__":
    main()
