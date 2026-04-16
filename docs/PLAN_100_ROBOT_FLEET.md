# Plan: 100-Robot Fleet Registration for Demo Testing

**Date:** 2026-04-11
**Status:** Planning
**Goal:** Register ~100 test robots representing real commercial platforms, distributed across Michigan, with realistic operator fleets, reputation scores, and MCP capabilities. Enable multi-task RFP decomposition testing against 50 real MDOT RFPs.

---

## 1. Robot Models (Cross-referenced with DroneDeploy + industry)

### Tier 1 — Primary platforms (DroneDeploy-supported, high volume)

| # | Model | Manufacturer | Category | Sensors | Task Types | Price Range | Count |
|---|-------|-------------|----------|---------|------------|-------------|-------|
| 1 | Matrice 350 RTK + Zenmuse L2 | DJI | Aerial LiDAR | LiDAR (5 pts/m²), RTK GPS | Topo survey, volumetric, corridor | $10K drone + $5K sensor | 15 |
| 2 | Matrice 350 RTK + Zenmuse P1 | DJI | Aerial Photogrammetry | 45MP full-frame, RTK | Orthomosaic, progress monitoring, as-built | $10K + $6K | 12 |
| 3 | Matrice 350 RTK + Zenmuse H30T | DJI | Aerial Thermal + Visual | Thermal 640×512, wide + zoom | Thermal inspection, roof, envelope | $10K + $5K | 6 |
| 4 | Mavic 3 Enterprise RTK | DJI | Aerial (compact) | 20MP wide, 12MP tele, RTK | Small-site topo, visual inspection, progress | $5K | 10 |
| 5 | Matrice 4 Enterprise | DJI | Aerial (next-gen) | 20MP wide, 48MP tele, thermal option | General survey, inspection | $8K | 8 |
| 6 | Skydio X10 | Skydio | Aerial (US-made) | Visual, thermal, RTK, autonomy | Bridge inspection, close-range, BVLOS | $20K | 8 |
| 7 | Spot + Leica BLK ARC | Boston Dynamics | Ground LiDAR | 360° LiDAR, 5 cameras | Tunnel, interior, confined space, as-built | $75K + $40K | 6 |

### Tier 2 — Specialty platforms

| # | Model | Manufacturer | Category | Sensors | Task Types | Price Range | Count |
|---|-------|-------------|----------|---------|------------|-------------|-------|
| 8 | WingtraOne Gen 2 | Wingtra | Fixed-wing VTOL | Sony 61MP + LiDAR option | Large-area corridor, highway, statewide | $20K | 5 |
| 9 | Freefly Astro | Freefly | Aerial (US-made) | 61MP Sony, LiDAR, multispectral | Medium survey, US-manufactured req | $20K | 5 |
| 10 | Autel EVO II Pro RTK | Autel | Aerial (budget) | 20MP 1-inch, RTK | Small site, visual, budget topo | $4K | 8 |
| 11 | Flyability ELIOS 3 | Flyability | Confined-space | LiDAR, 4K camera, collision-tolerant | Tunnel interior, tank, bridge underside | $60K | 4 |
| 12 | Anzu Raptor RTK | Anzu Robotics | Aerial (no geofence) | Visual, thermal, RTK | Unrestricted airspace, no DJI geofence | $8K | 5 |
| 13 | Inspired Flight IF1200 | Inspired Flight | Heavy-lift (US-made) | LiDAR, GPR, custom payloads | Heavy payload, GPR-capable, NDAA-compliant | $29K | 4 |
| 14 | Spot + GSSI StructureScan | Boston Dynamics | Ground GPR | GPR 1600MHz + 400MHz | Subsurface utility, rebar, void detection | $75K + $25K | 4 |

**Total: 100 robots across 14 models**

### Distribution rationale
- DJI M350 variants dominate (33 units) — matches real market share for construction survey
- Mavic 3E (10) — budget entry, common for small operators
- Skydio X10 (8) — US-made requirement for government projects (Blue UAS)
- Spot variants (10) — ground capabilities for tunnel/interior (MDOT I-94 tunnel program)
- Specialty (18) — fixed-wing, confined-space, GPR for diverse RFP types

---

## 2. Operator Fleets (Michigan-based)

### Large fleets (5-10 robots each)

| Operator | Location | Fleet Size | Models | Coverage Radius | Profile |
|----------|----------|-----------|--------|----------------|---------|
| Great Lakes Aerial Survey | Troy, MI | 8 | 3× M350+L2, 3× M350+P1, 2× Mavic 3E | 240 km | Full-service, MDOT experienced |
| Motor City Drones | Detroit, MI | 7 | 2× M350+L2, 2× Skydio X10, 2× M4E, 1× M350+H30T | 160 km | Tech-forward, Blue UAS compliant |
| Peninsular Survey Systems | Lansing, MI | 8 | 3× M350+P1, 2× WingtraOne, 2× Mavic 3E, 1× Freefly Astro | 320 km | Statewide corridor specialist |
| Wolverine Robotics | Ann Arbor, MI | 10 | 3× Spot+BLK, 2× Spot+GPR, 2× ELIOS 3, 3× M350+L2 | 160 km | Ground + confined space specialist |

### Mid fleets (3-5 robots)

| Operator | Location | Fleet Size | Models | Coverage Radius | Profile |
|----------|----------|-----------|--------|----------------|---------|
| Copper Country UAS | Houghton, MI | 4 | 2× M350+L2, 1× Freefly Astro, 1× Autel EVO II | 400 km | Upper Peninsula, mining/forestry |
| Saginaw Valley Mapping | Saginaw, MI | 5 | 2× M350+P1, 2× Mavic 3E, 1× Anzu Raptor | 190 km | Agricultural + construction |
| Lakeshore Inspections | Grand Haven, MI | 4 | 2× Skydio X10, 1× M350+H30T, 1× M4E | 130 km | Coastal, bridge, marine |
| I-94 Corridor Services | Kalamazoo, MI | 5 | 2× M350+L2, 1× M350+P1, 1× IF1200, 1× Spot+GPR | 160 km | Highway corridor, GPR |
| DroneScan MI | Port Huron, MI | 3 | 1× M350+P1, 1× Mavic 3E, 1× Autel EVO II | 130 km | Small projects, cost-focused |
| Blue Water Survey | Midland, MI | 4 | 2× M4E, 1× M350+H30T, 1× Anzu Raptor | 160 km | Infrastructure, thermal |

### Solo operators (1-2 robots)

| Operator | Location | Fleet Size | Models | Coverage Radius | Profile |
|----------|----------|-----------|--------|----------------|---------|
| Jake Mitchell Aerial | Traverse City, MI | 2 | 1× M350+L2, 1× Mavic 3E | 100 km | Solo operator, new to marketplace |
| Northern Drones LLC | Gaylord, MI | 1 | 1× Autel EVO II | 65 km | Budget, rural northern MI |
| River Rouge Robotics | Dearborn, MI | 2 | 1× Spot+BLK, 1× M350+P1 | 80 km | Urban, building scan |
| Mackinac Survey Co. | St. Ignace, MI | 2 | 1× WingtraOne, 1× Mavic 3E | 160 km | Bridge, Mackinac region |
| UP Drone Works | Marquette, MI | 2 | 1× Freefly Astro, 1× Autel EVO II | 240 km | Upper Peninsula remote sites |
| Campus Robotics | East Lansing, MI | 2 | 1× Skydio X10, 1× Mavic 3E | 50 km | MSU-adjacent, student-founded |
| Flint Aerial Solutions | Flint, MI | 2 | 1× M350+L2, 1× M350+H30T | 100 km | Infrastructure, thermal |
| Drone Sisters | Livonia, MI | 2 | 1× M350+P1, 1× Autel EVO II | 80 km | Residential, commercial |

**Total: 18 operators, 100 robots**
**Geography:** Detroit metro (30), Lansing/Ann Arbor (18), West MI (8), Saginaw/Midland (9), Kalamazoo (5), Northern LP (7), UP (7), Port Huron/Thumb (5), Traverse/Mackinac (4), Flint (7)

**Naming rhymes (inspired by real Michigan operators):**
- SSI → Peninsular Survey Systems (statewide survey partner)
- DroneView Technologies → DroneScan MI (tech-focused, Bloomfield Hills area → Port Huron)
- Drone Brothers → Drone Sisters (large network, Livonia area)

---

## 3. Reputation & Pricing Distribution

| Profile | Count | Reputation Score | Bid Strategy | Availability |
|---------|-------|-----------------|--------------|-------------|
| Established (high rep, premium price) | 15 | 4.2–4.9 | 85–95% of budget | 90% online |
| Experienced (good rep, competitive) | 35 | 3.0–4.2 | 75–85% of budget | 85% online |
| Growing (moderate rep, aggressive) | 25 | 1.5–3.0 | 65–80% of budget | 80% online |
| New entrants (no rep, lowest price) | 15 | 0.0–1.5 | 55–70% of budget | 75% online |
| Offline / busy | 10 | varies | N/A | 0% (offline) |

Reputation is seeded based on operator tier:
- Large fleets start with higher reputation (more history)
- Solo operators start with low/zero reputation
- 10 robots are marked offline at any given time (rotated)

---

## 4. MCP Servers (one per robot category)

Each robot category gets a FakeRover-style MCP server on Fly.io that simulates realistic capabilities.

| Server | Robot Models | MCP Tools | Fly.io App |
|--------|------------|-----------|-----------|
| `yakrover-aerial-lidar` | M350+L2, Freefly Astro, IF1200 | `fly_waypoint`, `capture_lidar_scan`, `get_gps_position`, `check_battery`, `return_to_home`, `set_flight_altitude`, `get_wind_speed` | New |
| `yakrover-aerial-photo` | M350+P1, Mavic 3E, M4E, Autel EVO II, Anzu Raptor | `fly_waypoint`, `capture_photo`, `capture_video`, `get_gps_position`, `check_battery`, `return_to_home`, `set_camera_params` | New |
| `yakrover-aerial-thermal` | M350+H30T, Skydio X10 (thermal) | `fly_waypoint`, `capture_thermal`, `capture_photo`, `get_surface_temp`, `get_gps_position`, `check_battery`, `return_to_home` | New |
| `yakrover-fixedwing` | WingtraOne Gen 2 | `launch_vtol`, `fly_corridor`, `capture_photo`, `get_gps_position`, `check_battery`, `land_vtol`, `set_flight_plan` | New |
| `yakrover-ground-lidar` | Spot+BLK ARC | `walk_to`, `scan_360_lidar`, `capture_photo`, `get_position`, `check_battery`, `dock`, `navigate_stairs` | New |
| `yakrover-ground-gpr` | Spot+GSSI | `walk_to`, `deploy_gpr`, `scan_gpr_line`, `get_position`, `check_battery`, `dock`, `mark_utility` | New |
| `yakrover-confined` | ELIOS 3 | `fly_indoor`, `capture_lidar_scan`, `capture_photo`, `detect_obstacle`, `get_position`, `check_battery`, `return_to_pilot` | New |
| `yakrover-skydio` | Skydio X10 (visual) | `fly_waypoint`, `fly_orbit`, `capture_photo`, `capture_thermal`, `autonomous_inspect`, `get_gps_position`, `check_battery` | New |

**8 new Fly.io apps**, each a FastMCP server returning simulated sensor data appropriate to the robot type.

---

## 5. Registration Flow Changes

### Current state
- `FakeRover-` prefix required unless admin
- No `is_test` metadata
- No geographic coordinates (location is free text)
- No service radius
- No reputation seeding

### Required changes

**Registration form (`demo/marketplace/index.html`):**
- Add `is_test` checkbox (admin-only, hidden for regular operators)
- Add lat/lng fields (auto-populated from location text via geocoding, or manual entry)
- Add service radius field (km, default 100)
- Add reputation seed field (admin-only, 0.0–5.0)

**Backend (`auction/mcp_tools.py` — `auction_register_robot_onchain`):**
- Accept `is_test`, `latitude`, `longitude`, `service_radius_km`, `initial_reputation` parameters
- Write `is_test` to on-chain metadata
- Write `latitude`, `longitude`, `service_radius_km` to on-chain metadata
- Seed reputation score in `ReputationTracker` if `initial_reputation` provided

**On-chain metadata additions:**

| Key | Type | Example | Purpose |
|-----|------|---------|---------|
| `is_test` | bool | `true` | Filter test robots from production |
| `latitude` | float | `42.3314` | Home base latitude |
| `longitude` | float | `-83.0458` | Home base longitude |
| `service_radius_km` | int | `100` | Maximum travel distance for tasks |
| `home_type` | string | `garage` or `docked` | Whether robot travels or executes in-place |

**Frontend fleet filter:**
- Add "Hide test robots" toggle (reads `is_test` metadata)
- Deprecate `FakeRover-` prefix convention (keep for backward compat)

**Bid engine update (`auction/engine.py` or `mock_fleet.py`):**
- Geographic filtering: **hard cutoff** — robots do not bid on tasks outside their `service_radius_km`
- Haversine distance calculation from robot home (lat/lng) to task location
- This requires task location (lat/lng) — already partially supported in task spec as `survey_area`
- Busy/offline filtering: robots track `busy_until` timestamp after winning a task. Bid engine excludes robots where `busy_until > now()`. Task durations are realistic (minutes to hours per task type).

---

## 6. Batch Registration Script

**Script:** `scripts/register_fleet.py`

```
Usage: uv run python scripts/register_fleet.py --fleet-file fleet_manifest.yaml --chain base-mainnet --dry-run
```

**Fleet manifest format (`fleet_manifest.yaml`):**
```yaml
operators:
  - name: "Great Lakes Aerial Survey"
    company: "Great Lakes Aerial Survey LLC"
    location: "Troy, MI"
    latitude: 42.6064
    longitude: -83.1498
    service_radius_km: 240
    stripe_connect_id: "acct_test_greatlakes"
    robots:
      - name: "GL-LiDAR-01"
        model: "DJI Matrice 350 RTK + Zenmuse L2"
        equipment_type: "aerial_lidar"
        sensors: ["aerial_lidar", "rtk_gps"]
        mcp_endpoint: "https://yakrover-aerial-lidar.fly.dev/mcp"
        bid_pct: 0.85
        initial_reputation: 4.5
        home_type: "garage"
        is_test: true
      - name: "GL-LiDAR-02"
        ...
```

**Script behavior:**
1. Load manifest
2. For each operator → for each robot:
   - Call `auction_register_robot_onchain` via HTTP to MCP server
   - Wait for confirmation (tx mined)
   - Rate limit: 1 registration per 5 seconds (avoid nonce collision)
   - Log results to `fleet_registration_log.json`
3. Dry-run mode: validate manifest, estimate gas cost, print plan
4. Resume mode: skip already-registered robots (check by name in subgraph)

**Estimated cost:** 100 registrations × ~$0.005 gas = ~$0.50 on Base mainnet

---

## 7. RFP Test Corpus (50 MDOT-derived tasks)

We already have 43 Michigan RFPs documented in `docs/research/market/RESEARCH_MICHIGAN_RFP_EXAMPLES.md`. Expand to 50 and decompose each into auction tasks.

### Task type distribution (derived from RFP analysis)

| Task Type | Count | Required Sensors | Example RFP |
|-----------|-------|-----------------|-------------|
| Aerial topo survey (LiDAR) | 12 | aerial_lidar, rtk_gps | I-94 reconstruction, M-14 rebuild |
| Aerial photogrammetry / orthomosaic | 10 | photogrammetry, rtk_gps | Progress monitoring, as-built |
| Bridge inspection (aerial) | 8 | photogrammetry, thermal | 70+ bridges on I-94, Forest Ave |
| Subsurface / GPR scan | 5 | gpr | Utility detection, drainage tunnel |
| Tunnel / confined space | 4 | terrestrial_lidar | I-94 drainage tunnel, Spot interior |
| Thermal inspection | 3 | thermal_camera | Roof, envelope, MEP |
| Highway corridor (fixed-wing) | 3 | aerial_lidar, photogrammetry | MiSAIL, long corridors |
| Volumetric / stockpile | 3 | aerial_lidar | Cut/fill, aggregate |
| Dam / hydraulic survey | 2 | aerial_lidar, photogrammetry | EGLE dam program |

**Multi-task RFPs:** ~20 of the 50 RFPs decompose into 2-3 tasks each (e.g., I-94 = topo + tunnel + bridge inspection). Total auction tasks: ~80.

**Robot-task eligibility matrix:** Each task type maps to specific sensor requirements. The 100-robot fleet is designed so every task type has 8-15 eligible bidders, ensuring competitive auctions.

---

## 8. Chain, Gas & Wallet (Tactical)

**Chain:** Base Sepolia (testnet). Mainnet registration deferred until fleet testing is validated.

**Platform signer wallet:** `0xc69bc0c54901532f0b39acce94d66eaac8156d57` (from `SIGNER_PVT_KEY`)
- Current balance: **0.1 ETH** on Base Sepolia
- Role: funds operator wallets, writes platform attestation, serves as faucet

**Operator wallets (18 total):**
Each operator gets their own deployer address. This simulates real-world conditions where operators register robots from their own wallets — not from the platform.

- **Generation:** batch script derives 18 wallets (deterministic from a seed or random keypairs stored in `fleet_manifest.yaml`)
- **Funding:** platform signer sends 0.003 ETH to each operator wallet (0.054 ETH total, well within 0.1 ETH balance). Each operator wallet has enough for ~6 robot registrations.
- **Registration flow:** each robot is minted by its operator's wallet, not the platform
- **Platform attestation:** after operator registers a robot, platform signer writes `attested_by` and `attestation_status` metadata via a separate transaction. This models the real flow: operator registers → platform verifies → platform attests.
- **Ownership:** robots are owned by their operator wallet on-chain. No `transferFrom` needed.

**Gas estimate (revised):**
- 18 funding transactions (platform → operators): ~18 × 21K gas = negligible
- 100 robot registrations from operator wallets: ~0.0005 ETH total across all wallets
- 100 attestation transactions from platform wallet: ~0.0003 ETH
- **Total: ~0.001 ETH. No faucet top-up needed.**

**Subgraph:** Base Sepolia subgraph at `4yYAvQLFjBhBtdRCY7eUWo181VNoTSLLFd5M7FXQAi6u` — already used for discovery. Handles `fleet_provider: yakrover` filter.

---

## 9. Platform Attestation

Robots registered directly on the ERC-8004 contract by third parties should not appear in marketplace discovery unless the platform has verified them. Attestation is the gate.

### Design

**On registration:**
- Platform writes `attested_by` metadata key with value = signer wallet address (`0xc69b...d57`)
- Platform writes `attestation_status` metadata key with value = `active`

**On revocation:**
- Platform calls `setMetadata` to update `attestation_status` to `revoked`
- Revocation reasons: failed verification, fraud, operator request, compliance issue

**Discovery filter:**
- Subgraph query adds: filter for `attestation_status == active` (hex-encoded)
- Robots without `attested_by` or with `attestation_status == revoked` are excluded from discovery
- Unattested robots are invisible to the marketplace — they exist on-chain but don't bid

**Backend changes:**
- `auction_register_robot_onchain`: writes `attested_by` and `attestation_status: active` in metadata
- New MCP tool: `auction_revoke_attestation(agent_id, chain, reason)` — updates `attestation_status` to `revoked`
- New MCP tool: `auction_reinstate_attestation(agent_id, chain)` — sets `attestation_status` back to `active`

**Frontend changes:**
- Discovery query filters for `attestation_status` metadata
- Operator profile popup shows attestation status: "Verified by platform" or "Not verified"

### Why this matters
- Third parties can register robots on ERC-8004 freely — it's a public registry
- Without attestation, a spam robot could appear in marketplace discovery
- Attestation is the marketplace's editorial layer on top of the open registry
- Revocability means the platform can remove bad actors without touching the on-chain registration

---

## 10. Robot Naming Convention

Each operator uses their own in-house naming standard. The marketplace does NOT enforce a naming convention — operators name robots however they want. The platform may later standardize a display name or alias for the interface, but the registered name reflects the operator's internal system.

**Examples of varied naming conventions across operators:**

| Operator | Convention | Examples |
|----------|-----------|---------|
| Great Lakes Aerial Survey | `GLAS-{type}-{seq:02d}` | GLAS-LIDAR-01, GLAS-PHOTO-03, GLAS-SCOUT-02 |
| Motor City Drones | `MCD {model} #{seq}` | MCD Matrice #1, MCD Skydio #2, MCD M4E #1 |
| Peninsular Survey Systems | `PSS-{region}-{seq:03d}` | PSS-EAST-001, PSS-WEST-005, PSS-CORR-002 |
| Wolverine Robotics | `{animal}-{seq}` | Badger-01, Wolverine-03, Mole-02 |
| Copper Country UAS | `CC-{seq}` | CC-01, CC-02, CC-03, CC-04 |
| Saginaw Valley Mapping | `SVM {nickname}` | SVM Hawk, SVM Falcon, SVM Osprey |
| Lakeshore Inspections | `Shore {seq}` | Shore 1, Shore 2, Shore 3 |
| I-94 Corridor Services | `I94-{type}{seq}` | I94-L1, I94-P1, I94-G1 |
| DroneScan MI | `DS-{seq:03d}` | DS-001, DS-002, DS-003 |
| Blue Water Survey | `BW-{color}` | BW-Blue, BW-Teal, BW-Aqua, BW-Navy |
| Jake Mitchell Aerial | `Jake's {model}` | Jake's Matrice, Jake's Mavic |
| Northern Drones LLC | `North-1` | North-1 |
| River Rouge Robotics | `RRR-{type}-{seq}` | RRR-SPOT-01, RRR-AIR-01 |
| Mackinac Survey Co. | `MAC-{seq}` | MAC-01, MAC-02 |
| UP Drone Works | `Yooper-{seq}` | Yooper-1, Yooper-2 |
| Campus Robotics | `Sparty-{seq}` | Sparty-1, Sparty-2 |
| Flint Aerial Solutions | `FAS-{type}{seq}` | FAS-L1, FAS-T1 |
| Drone Sisters | `Sister-{name}` | Sister-Ada, Sister-Grace |

This diversity is intentional — it tests that the marketplace handles heterogeneous naming without breaking discovery, bidding, or display.

---

## 11. Implementation Sequence (Comprehensive)

### Current state (as of 2026-04-12)

**Completed:**
- Fleet simulator: 9 standalone Fly.io apps (one per category) in `infra/fleet-sim/`, always-on, each with `robot_submit_bid`/`robot_execute_task`/`robot_get_pricing` + category-specific tools ✅
- `data/fleet_manifest.yaml` complete — 100 robots, 18 operators, varied naming ✅
- Demo discovers Base Sepolia (84532 added to DISCOVERY_CHAINS) and shows all chains ✅
- Registration backend accepts `is_test`, `latitude`, `longitude`, `service_radius_km`, `home_type` — written as on-chain metadata ✅
- MCP server discovery queries both Base mainnet + Base Sepolia (was mainnet only) ✅
- 18 operator wallets generated (`.fleet_wallets.json`, gitignored) and funded (0.003 ETH each on Base Sepolia) ✅
- 5 test robots (#4292-4296) updated and transferred to operator wallets ✅
- EAS attestation: 100 demo_fleet (Base Sepolia) + 1 live_production Tumbller (Base mainnet) ✅
- EAS-based discovery filtering on both server and frontend ✅
- Geographic hard cutoff filter (haversine distance > service_radius_km) ✅
- Busy state tracking (task-type-specific durations, 15s to 2hr) ✅
- 8 category-specific delivery schemas (`auction/delivery_schemas.py`) ✅
- Category servers return schema-matching delivery data ✅
- Mole-04B (#4419) retired — is_test=false, deactivated, attestation revoked ✅
- Repo restructured: `demo/marketplace/`, `infra/fleet-sim/`, `data/`, `docs/architecture/` ✅

**Not started:**
- Multi-task RFP decomposition (Phase 8)
- RFP corpus expansion to 50 (Phase 9, currently 43)
- End-to-end verification of all 9 RFP presets through QA (Phase 11)

### Phase 1 — Backend registration updates ✅
1. ✅ Add `is_test` parameter to `auction_register_robot_onchain` — write as on-chain metadata
2. ✅ Add `latitude`, `longitude` parameters — write as on-chain metadata
3. ✅ Add `service_radius_km` parameter — write as on-chain metadata
4. ✅ Add `home_type` parameter (`garage` or `docked`) — write as on-chain metadata
5. ~~Add `attested_by` metadata write~~ — removed, EAS planned instead
6. ~~Add `attestation_status` metadata write~~ — removed, EAS planned instead
7. ~~Add `auction_revoke_attestation` MCP tool~~ — removed, EAS planned instead
8. ~~Add `auction_reinstate_attestation` MCP tool~~ — removed, EAS planned instead
9. ✅ Update `discover_and_swap_fleet()` — queries Base mainnet + Sepolia, hex metadata decoding
10. ✅ Deploy updated MCP server to Fly.io (yakrover-marketplace)

### Phase 2 — Fix the 5 test robots ✅
11. ✅ Updated #4292-4296: MCP endpoint → `yakrover-fleet-sim.fly.dev/mcp`, geo/equipment/sensor metadata added. Still owned by platform signer (pre-date operator wallets). Functional for demo.

### Phase 3 — Operator wallets ✅
12. ✅ Funded 18 operator wallets (0.003 ETH each, 0.054 ETH total, block 40069529)
13. ✅ All 18 verified via RPC balance check
14. ✅ Tx hashes logged to `fleet_funding_log.json`

### Phase 4 — Batch registration script ✅
15. Write `scripts/register_fleet.py`:
    - Reads `fleet_manifest.yaml` and `.fleet_wallets.json`
    - For each operator → for each robot:
      a. Registers robot from operator's wallet with correct MCP endpoint per category (`yakrover-fleet-sim.fly.dev/mcp`)
      b. Includes all metadata: `is_test: true`, lat/lng, service_radius_km, home_type, attested_by, attestation_status
    - Rate limited: 1 registration per 5 seconds
    - Resume mode: skip already-registered robots (check by name in subgraph)
    - Dry-run mode: validate manifest, estimate gas, print plan
    - Logs results to `fleet_registration_log.json`
16. Test dry-run mode
17. Test with 5 robots from different operators — verify ownership, endpoint, metadata, attestation, IPFS tools

### Phase 5 — Full registration (100 robots) ✅
18. Run batch registration for all 100 robots on Base Sepolia
19. Verify all 100 appear in subgraph with correct metadata
20. Verify IPFS agent cards have correct category-specific tools
21. Verify robot ownership matches operator wallets (not platform signer)
22. Verify attestation filter: only attested robots in marketplace discovery
23. Verify geo metadata: lat/lng and service_radius readable from subgraph

### Phase 6 — Demo UI updates ✅
24. Replace `FakeRover-` / `Tumbller` name-based filter in `getFilteredRobots()` with `is_test` metadata check
25. "Demo fleet only" toggle shows `is_test: true` robots; unchecked shows all attested robots
26. Add "Hide test robots" toggle (new) — for when real operators coexist with test fleet
27. Verify 100 robots render in sidebar without performance issues (may need virtual scroll or pagination)
28. Verify operator profile popup shows correct equipment model, location, category-specific tools for each robot type
29. Verify IPFS enrichment completes for 100 robots without timeout (may need batch/cache)

### Phase 7 — Bid engine updates ✅
30. Add haversine distance calculation utility
31. Add geographic hard cutoff filter: robot does not bid if task location > service_radius_km
32. Extend `auction_post_task` to require `latitude`/`longitude` for the job site
33. Add `busy_until` timestamp tracking to robot state (MCPRobotAdapter / RuntimeRegisteredRobot)
34. Add busy filter: robot does not bid while `busy_until > now()`
35. Set `busy_until` when robot wins auction (duration from task duration model in Section 10)
36. Test: post task in Detroit → verify only robots within range bid
37. Test: robot wins → excluded from next auction → re-available after task duration

### Phase 8 — Multi-task RFP decomposition
38. Update Claude system prompt to decompose RFPs into multiple tasks when appropriate
39. Build decomposition preview UI: Claude presents breakdown ("This project requires 3 tasks: ..."), user confirms or edits
40. Build parallel auction execution: `auction_post_task` called N times with shared `rfp_id`
41. Build multi-result display: N winner cards shown in the feed
42. Each task settles independently (no bundled payment)
43. Test with 3 MDOT RFPs that decompose into 2-3 tasks each

### Phase 9 — RFP corpus
44. Expand MDOT RFP research to 50 entries (currently 43)
45. Decompose each into structured task specs with lat/lng coordinates
46. Verify every task type has 8-15 eligible bidders in the 100-robot fleet
47. Create 5 sample RFPs as demo presets (selectable in UI dropdown)

### Phase 10 — Realistic delivery payloads
48. Update `robot_execute_task` in each category server to return delivery data that matches what the real robot model produces — correct file formats, sizes, and structure
49. **Aerial LiDAR:** LAS 1.4 point cloud metadata (point count, density, bounding box, CRS), classified ground/non-ground, contour generation summary. Realistic file sizes: 50-500 MB per flight.
50. **Aerial Photo:** Orthomosaic metadata (GSD, pixel dimensions, GeoTIFF bounds), photo count + overlap stats, 3D point cloud summary. Realistic: 200-2000 photos per flight, 1-10 GB orthomosaic.
51. **Ground GPR:** DZT scan file metadata (antenna frequency, scan length, depth, trace count), utility detection table (type, depth, lat/lng, confidence), APWA color-coded map reference. Realistic: 10-100 MB per scan line.
52. **Aerial Thermal:** Radiometric thermal mosaic metadata (resolution, temp range, emissivity), anomaly table (location, severity, delta-T), visual reference photo pairs. Realistic: 50-200 MB thermal mosaic.
53. **Skydio/Bridge:** Inspection photo set metadata (image count, resolution, coverage %), element-level condition coding (NBI format for bridges), 3D model summary. Realistic: 200-500 photos, 2-5 GB.
54. Delivery payloads should help answer: how does the marketplace handle large files? What gets uploaded to IPFS vs stored off-chain? How does the buyer download and verify deliverables?

### Phase 11 — End-to-end verification
55. Run 10 diverse auctions across different task types and Michigan locations
56. Verify geographic filtering: UP robot (Copper Country, 400km) bids on Houghton task but not Detroit
57. Verify busy exclusion: winning robot excluded, re-available after task duration
58. Verify docked in-situ tasks complete in seconds (not minutes)
59. Verify reputation-weighted scoring: established operators win more than new entrants
60. Verify multi-task RFP: I-94 project decomposes into topo + tunnel + bridge → 3 parallel auctions → 3 different winners
61. Verify 100-robot sidebar: no performance lag, scroll works, popup loads correctly
62. Verify all 100 robots show correct category-specific tools via IPFS enrichment

---

## 9. Design Decisions (Resolved)

1. **Geographic filtering: hard cutoff.** Robot will NOT bid on any task outside its `service_radius_km`. This is a hard constraint in the bid engine filter (same layer as sensor capability filtering). Requires task location (lat/lng) in the task spec — already partially supported via `survey_area`. Need to add haversine distance calculation to the filter.

2. **Busy/offline: dynamic simulation.** Robots go offline after winning a task. Task duration is realistic — minutes for small tasks, hours for large survey tasks. While a robot is executing, it cannot bid on other tasks. This creates natural competition dynamics: if the best robot just won a task, the second-best gets the next one. Implementation: `MCPRobotAdapter` or `RuntimeRegisteredRobot` tracks `busy_until` timestamp. Bid engine checks `busy_until > now()` as a hard filter alongside geographic radius.

3. **Multi-task RFP UI: user confirms decomposition.** Claude decomposes the RFP and presents the task breakdown to the user ("This project requires 3 separate survey tasks: aerial topo, GPR subsurface, bridge inspection. Each will be auctioned independently."). User confirms or edits before auctions begin. Tasks run as independent auctions — no cross-task scheduling constraints in v1.4/v1.5 (that's v2.0 per IMR-LLM research, R-051).

4. **Fly.io: always-on (~$16/mo).** 8 MCP servers at $2/mo each for stable demo. No scale-to-zero cold starts during live demos.

5. **Operator names: fictional but rhyming.** SSI → Peninsular Survey Systems, DroneView → DroneScan MI, Drone Brothers → Drone Sisters. All other names are original Michigan-themed fiction.

## 10. Task Duration Model (Resolved)

Robots go busy for a realistic duration after winning a task. Duration depends on task type and whether the robot is docked (in-situ) or garage-deployed (travel + execute).

| Task Type | Home Type | Duration | Example |
|-----------|-----------|----------|---------|
| In-situ sensor reading | Docked | 5–15 seconds | Temp/humidity check from dock |
| In-situ photo capture | Docked | 10–30 seconds | Single photo or thermal snapshot from dock |
| Small aerial survey (<5 acres) | Garage | 5–15 minutes | Parking lot topo, roof inspection |
| Medium aerial survey (5–50 acres) | Garage | 30–90 minutes | Construction site topo, progress monitoring |
| Large corridor survey (>50 acres) | Garage | 2–4 hours | Highway corridor, pipeline |
| Ground LiDAR scan (interior) | Garage | 1–3 hours | Building interior, tunnel segment |
| GPR subsurface scan | Garage | 1–2 hours | Utility detection, rebar mapping |
| Confined space inspection | Garage | 30–60 minutes | Tank interior, bridge box girder |
| Bridge inspection (exterior) | Garage | 45–90 minutes | Deck, substructure, bearings |

Docked robots executing in-situ tasks (seconds) become available almost immediately. Garage-deployed robots include implicit travel time in the duration.

## 11. Multi-Task Auction Model (Resolved)

When an RFP decomposes into multiple tasks, **all auctions run in parallel**. Each task is an independent auction with its own set of eligible bidders (filtered by sensor capability and geographic radius). A single robot can only win one task from the same RFP (it goes busy after winning).

**Demo UI flow:**
1. User enters RFP description
2. Claude decomposes into N tasks and presents breakdown: "This project requires 3 survey tasks: (1) Aerial LiDAR topo — 12 acres, (2) GPR subsurface — utilities, (3) Bridge inspection — 2 structures"
3. User confirms or edits
4. All N auctions run simultaneously
5. Results shown as N winner cards, each with its own operator, bid, and payment

**Implementation:**
- `auction_post_task` called N times with a shared `rfp_id` linking the tasks
- Each auction runs independently in the engine
- Demo feed shows all auctions interleaved: "Task 1: 8 bids received... Task 2: 5 bids received..."
- Payment: each task settles independently (no bundled payment in v1.5)

## 12. Remaining Open Question

1. **Reputation decay** — seeded reputation is static for initial fleet test. Decay mechanism (reputation decreases if robot is inactive for >30 days) designed but not active until v2.0.
