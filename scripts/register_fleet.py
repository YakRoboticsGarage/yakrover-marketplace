#!/usr/bin/env python3
"""
Batch register robots from fleet_manifest.yaml onto Base Sepolia.

Usage:
  uv run python scripts/register_fleet.py --dry-run          # Validate only
  uv run python scripts/register_fleet.py --count 10          # Register next 10
  uv run python scripts/register_fleet.py --count 0           # Register all remaining
  uv run python scripts/register_fleet.py --operator "Drone Sisters"  # One operator only

Requires .env with SIGNER_PVT_KEY and PINATA_JWT.
Requires .fleet_wallets.json with operator wallet keypairs.

Registration process per robot:
  1. SDK register() — mints token with all metadata (one tx)
  2. SDK IPFS upload — agent card with discovered tools
  3. SDK setAgentURI — links IPFS card on-chain
  4. Raw web3 setMetadata — writes is_test=true (separate tx from owner wallet)

Already-registered robots are skipped (checked via subgraph).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import eth_abi
import httpx
import yaml
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

# ── Config ────────────────────────────────────────────────────────

from auction.contracts import (
    IDENTITY_REGISTRY as REGISTRY,
    RPC_URLS,
    SUBGRAPH_URLS,
    YAKROVER_HEX,
)

CHAIN_ID = 84532
RPC_URL = RPC_URLS[CHAIN_ID]
SUBGRAPH_URL = SUBGRAPH_URLS[CHAIN_ID]

MODEL_TO_MCP = {
    "M350+L2": "https://yakrover-aerial-lidar.fly.dev/mcp",
    "M350+P1": "https://yakrover-aerial-photo.fly.dev/mcp",
    "M350+H30T": "https://yakrover-aerial-thermal.fly.dev/mcp",
    "Mavic3E": "https://yakrover-aerial-photo.fly.dev/mcp",
    "M4E": "https://yakrover-aerial-photo.fly.dev/mcp",
    "SkydioX10": "https://yakrover-skydio.fly.dev/mcp",
    "Spot+BLK": "https://yakrover-ground-lidar.fly.dev/mcp",
    "WingtraOne": "https://yakrover-fixedwing.fly.dev/mcp",
    "Astro": "https://yakrover-aerial-lidar.fly.dev/mcp",
    "AutelEVO": "https://yakrover-aerial-photo.fly.dev/mcp",
    "ELIOS3": "https://yakrover-confined.fly.dev/mcp",
    "AnzuRaptor": "https://yakrover-aerial-photo.fly.dev/mcp",
    "IF1200": "https://yakrover-aerial-lidar.fly.dev/mcp",
    "Spot+GPR": "https://yakrover-ground-gpr.fly.dev/mcp",
}

SENSOR_TO_CAT = {
    "aerial_lidar": "env_sensing",
    "terrestrial_lidar": "env_sensing",
    "gpr": "env_sensing",
    "rtk_gps": "env_sensing",
    "photogrammetry": "visual_inspection",
    "thermal_camera": "visual_inspection",
    "temperature": "env_sensing",
    "humidity": "env_sensing",
}

ACCEPT_HEADERS = {"Accept": "application/json, text/event-stream"}


# ── Tool discovery ────────────────────────────────────────────────

_tool_cache: dict[str, list[str]] = {}


def discover_tools(mcp_url: str) -> list[str]:
    if mcp_url in _tool_cache:
        return _tool_cache[mcp_url]
    tools = []
    try:
        r1 = httpx.post(
            mcp_url,
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "registrar", "version": "1.0"},
                },
                "id": 1,
            },
            headers=ACCEPT_HEADERS,
            timeout=10.0,
        )
        session = r1.headers.get("mcp-session-id", "")
        r2 = httpx.post(
            mcp_url,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2},
            headers={**ACCEPT_HEADERS, "Mcp-Session-Id": session},
            timeout=10.0,
        )
        for line in r2.text.splitlines():
            if line.startswith("data: "):
                for t in json.loads(line[6:]).get("result", {}).get("tools", []):
                    if isinstance(t, dict) and "name" in t:
                        tools.append(t["name"])
    except Exception as e:
        print(f"  WARNING: tool discovery failed for {mcp_url}: {e}")
    _tool_cache[mcp_url] = tools
    return tools


# ── Subgraph: find already-registered names ───────────────────────


def get_registered_names() -> set[str]:
    """Query subgraph for all yakrover robot names on Base Sepolia."""
    query = (
        '{ agentMetadata_collection(where: {key: "fleet_provider", value: "'
        + YAKROVER_HEX
        + '"}, first: 200) { agent { registrationFile { name } } } }'
    )
    try:
        resp = httpx.post(SUBGRAPH_URL, json={"query": query}, timeout=10.0)
        data = resp.json()
        names = set()
        for entry in data.get("data", {}).get("agentMetadata_collection", []):
            rf = entry.get("agent", {}).get("registrationFile") or {}
            name = rf.get("name")
            if name:
                names.add(name)
        return names
    except Exception as e:
        print(f"WARNING: subgraph query failed: {e}")
        return set()


# ── Register one robot ────────────────────────────────────────────


def register_robot(
    robot: dict,
    operator: dict,
    wallet_key: str,
    pinata_jwt: str,
    w3: Web3,
    dry_run: bool = False,
) -> dict:
    """Register a single robot. Returns result dict."""
    mcp_url = MODEL_TO_MCP.get(robot["model_key"])
    if not mcp_url:
        return {"name": robot["name"], "status": "skip", "reason": f"no MCP for {robot['model_key']}"}

    tools = discover_tools(mcp_url)
    if not tools:
        return {"name": robot["name"], "status": "skip", "reason": "no tools discovered"}

    cats = list(set(SENSOR_TO_CAT.get(s, "env_sensing") for s in robot["sensors"]))

    if dry_run:
        return {
            "name": robot["name"],
            "status": "dry_run",
            "mcp": mcp_url.split("yakrover-")[1].split(".fly")[0],
            "tools": len(tools),
            "sensors": robot["sensors"],
        }

    from agent0_sdk import SDK

    try:
        sdk = SDK(
            chainId=CHAIN_ID,
            rpcUrl=RPC_URL,
            signer=wallet_key,
            ipfs="pinata",
            pinataJwt=pinata_jwt,
        )

        agent = sdk.createAgent(
            name=robot["name"],
            description=f"{robot['model']} survey robot",
            image="",
        )
        agent.setMCP(mcp_url, auto_fetch=False)

        mcp_ep = next(
            (
                ep
                for ep in agent.registration_file.endpoints
                if hasattr(ep, "type") and str(ep.type).lower().endswith("mcp")
            ),
            None,
        )
        if mcp_ep:
            mcp_ep.meta["mcpTools"] = tools

        agent.setTrust(reputation=True)
        agent.setActive(True)

        metadata = {
            "category": "robot",
            "robot_type": "survey_platform",
            "fleet_provider": "yakrover",
            "fleet_domain": "yakrobot.bid",
            "min_bid_price": "50",
            "accepted_currencies": "usd,usdc",
            "task_categories": ",".join(cats),
            "operator_company": operator["company"],
            "operator_location": operator["location"],
            "equipment_model": robot["model"],
            "sensors": ",".join(robot["sensors"]),
        }
        if robot.get("latitude"):
            metadata["latitude"] = str(robot["latitude"])
        if robot.get("longitude"):
            metadata["longitude"] = str(robot["longitude"])
        if robot.get("service_radius_km"):
            metadata["service_radius_km"] = str(robot["service_radius_km"])
        if robot.get("home_type"):
            metadata["home_type"] = robot["home_type"]

        agent.setMetadata(metadata)

        # Step 1: Mint
        metadata_entries = agent._collectMetadataForRegistration()
        tx1 = sdk.web3_client.transact_contract(
            sdk.identity_registry, "register", "", metadata_entries
        )
        receipt = sdk.web3_client.wait_for_transaction(tx1, timeout=120)
        agent_id_int = agent._extractAgentIdFromReceipt(receipt)

        # Step 2: IPFS + setAgentURI
        time.sleep(3)
        agent.registration_file.agentId = f"{CHAIN_ID}:{agent_id_int}"
        agent.registration_file.updatedAt = int(time.time())

        ipfs_cid = sdk.ipfs_client.addRegistrationFile(
            agent.registration_file,
            chainId=CHAIN_ID,
            identityRegistryAddress=sdk.identity_registry.address,
        )
        tx2 = sdk.web3_client.transact_contract(
            sdk.identity_registry,
            "setAgentURI",
            agent_id_int,
            f"ipfs://{ipfs_cid}",
        )
        sdk.web3_client.wait_for_transaction(tx2, timeout=60)

        # Step 3: is_test via raw web3 (from owner wallet)
        time.sleep(2)
        registry_addr = Web3.to_checksum_address(REGISTRY)
        selector = w3.keccak(text="setMetadata(uint256,string,bytes)")[:4]
        encoded = eth_abi.encode(
            ["uint256", "string", "bytes"], [agent_id_int, "is_test", b"true"]
        )
        op_account = Account.from_key(wallet_key)
        nonce = w3.eth.get_transaction_count(op_account.address)
        tx3 = w3.eth.account.sign_transaction(
            {
                "nonce": nonce,
                "to": registry_addr,
                "data": (selector + encoded).hex(),
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
                "chainId": CHAIN_ID,
            },
            wallet_key,
        )
        w3.eth.send_raw_transaction(tx3.raw_transaction)

        del sdk
        return {
            "name": robot["name"],
            "agent_id": agent_id_int,
            "status": "ok",
            "tools": len(tools),
            "ipfs": ipfs_cid[:20],
        }

    except Exception as e:
        return {"name": robot["name"], "status": "failed", "error": str(e)[:120]}


# ── Main ──────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Batch register fleet robots")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no transactions")
    parser.add_argument("--count", type=int, default=10, help="Number to register (0=all)")
    parser.add_argument("--operator", type=str, help="Register only this operator's robots")
    parser.add_argument("--delay", type=int, default=5, help="Seconds between registrations")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")

    pinata_jwt = os.environ.get("PINATA_JWT")
    if not pinata_jwt:
        print("ERROR: PINATA_JWT not set in .env")
        sys.exit(1)

    with open(root / "data" / "fleet_manifest.yaml") as f:
        manifest = yaml.safe_load(f)
    with open(root / ".fleet_wallets.json") as f:
        wallets = {w["name"]: w for w in json.load(f)}

    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    # Get already-registered names
    print("Checking subgraph for already-registered robots...")
    registered_names = get_registered_names()
    print(f"  {len(registered_names)} already registered\n")

    # Build queue of robots to register
    queue = []
    for op in manifest["operators"]:
        if args.operator and op["name"] != args.operator:
            continue
        wallet = wallets.get(op["name"])
        if not wallet:
            print(f"WARNING: no wallet for operator '{op['name']}' — skipping")
            continue
        for robot in op["robots"]:
            if robot["name"] in registered_names:
                continue
            if robot.get("availability") == "offline":
                continue
            queue.append((robot, op, wallet["private_key"]))

    total = len(queue)
    if args.count > 0:
        queue = queue[: args.count]

    print(f"{'DRY RUN — ' if args.dry_run else ''}Registering {len(queue)} of {total} remaining robots\n")

    # Check name uniqueness in queue
    names_in_queue = [r["name"] for r, _, _ in queue]
    dupes = [n for n in names_in_queue if names_in_queue.count(n) > 1]
    if dupes:
        print(f"WARNING: duplicate names in queue: {set(dupes)}")
        # Dedupe by appending suffix
        seen = {}
        for i, (robot, op, key) in enumerate(queue):
            name = robot["name"]
            if name in seen:
                seen[name] += 1
                new_name = f"{name}-{seen[name]}"
                print(f"  Renaming duplicate: {name} → {new_name}")
                queue[i][0]["name"] = new_name
            else:
                seen[name] = 1

    results = []
    for i, (robot, op, wallet_key) in enumerate(queue):
        print(f"[{i+1}/{len(queue)}] {robot['name']:25s} ({op['name'][:25]}) ...", end=" ", flush=True)
        result = register_robot(robot, op, wallet_key, pinata_jwt, w3, dry_run=args.dry_run)

        if result["status"] == "ok":
            print(f"#{result['agent_id']} ({result['tools']} tools) ✓")
        elif result["status"] == "dry_run":
            print(f"[dry] {result['mcp']} ({result['tools']} tools)")
        elif result["status"] == "skip":
            print(f"SKIP: {result['reason']}")
        else:
            print(f"FAIL: {result.get('error', '?')}")

        results.append(result)

        if not args.dry_run and result["status"] == "ok":
            time.sleep(args.delay)

    # Summary
    ok = [r for r in results if r["status"] == "ok"]
    fail = [r for r in results if r["status"] == "failed"]
    skip = [r for r in results if r["status"] == "skip"]
    dry = [r for r in results if r["status"] == "dry_run"]

    print(f"\n{'='*50}")
    print(f"DONE: {len(ok)} registered, {len(fail)} failed, {len(skip)} skipped, {len(dry)} dry-run")
    if fail:
        print("\nFailed:")
        for r in fail:
            print(f"  {r['name']}: {r.get('error', '?')}")

    # Save log
    log_path = root / "fleet_registration_log.json"
    existing = []
    if log_path.exists():
        with open(log_path) as f:
            existing = json.load(f)
    existing.extend(results)
    with open(log_path, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"\nLog: {log_path}")


if __name__ == "__main__":
    main()
